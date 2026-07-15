"""Vision-based fidelity auditor: HTML truth vs PPT render → structured diff report.

NOT a corrector. NOT a font-shrinker. The job is to identify every place the
PPT fails to be a 1:1 replica of the HTML, classify by category, and report
with enough specificity that a human (or downstream fixer) can act on it.

Categories (closed enum — needed for cross-poster aggregation):
- missing_element    : original has it, PPT doesn't (border, shape, badge, image)
- extra_element      : PPT has something not in original
- text_clipped       : text cut at box edge
- wrap_mismatch      : different line count or visibly different wrap point
- color_drift        : noticeable color difference (NOT anti-aliasing)
- position_shift     : block in wrong location (>~10px)
- size_mismatch      : block dimensions clearly off
- font_substitution  : visibly different typeface
- alignment_off      : text alignment differs (left/center/right)
- spacing_off        : padding/margin/gap differs
- z_order            : overlap order wrong
- other              : catch-all (describe in `description`)

Severity:
- high   : breaks fidelity (missing border, clipped text, wrong section color)
- medium : visible but acceptable (subtle wrap, 1-line shift)
- low    : subtle (small color drift, anti-aliasing) — model SHOULD usually skip

Output JSON:
{
  "n_issues": <int>,
  "by_category": {"missing_element": 3, "wrap_mismatch": 2, ...},
  "by_severity": {"high": 4, "medium": 2, "low": 0},
  "issues": [
    {"severity": "high", "category": "text_clipped",
     "block_idx": <int|null>, "where": "<short location string>",
     "description": "<one sentence>"}, ...
  ]
}
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path


CATEGORIES = {
    "missing_element", "extra_element", "text_clipped", "wrap_mismatch",
    "color_drift", "position_shift", "size_mismatch", "font_substitution",
    "alignment_off", "spacing_off", "z_order", "other",
}
SEVERITIES = {"high", "medium", "low"}


def _b64(p: Path) -> str:
    return base64.standard_b64encode(p.read_bytes()).decode()


def _block_summary(dom: dict, max_blocks: int = 80) -> list[dict]:
    """Compact block list the vision model can reference by idx."""
    text_blocks = sorted(dom["text_blocks"],
                         key=lambda t: (t["depth"], t["y"], t["x"]))
    out = []
    for idx, b in enumerate(text_blocks[:max_blocks]):
        preview = ""
        for r in b.get("runs", []):
            if r["text"] != "\n":
                preview = r["text"][:60]; break
        out.append({
            "idx": idx, "tag": b["tag"],
            "x": round(b["x"]), "y": round(b["y"]),
            "w": round(b["w"]), "h": round(b["h"]),
            "text": preview,
        })
    return out


SYSTEM_PROMPT = """You are a visual-fidelity auditor. You receive two renderings of the same poster:
- IMAGE_A: ground truth (HTML render in browser at print viewport)
- IMAGE_B: current attempt (the .pptx rendering of the same poster)

You also receive a JSON list of text blocks the .pptx is built from. Each block has an `idx` (integer), `tag`, bbox (x/y/w/h in CSS px on the HTML), and a short `text` preview so you can reference them by idx.

Your job: walk both images side by side, find every place IMAGE_B fails to be a 1:1 replica of IMAGE_A, and emit a structured diff report.

Categories (use EXACTLY one of these strings):
- missing_element    : IMAGE_A has it, IMAGE_B doesn't (e.g. colored vertical bar, border, badge, icon, section underline, image)
- extra_element      : IMAGE_B has something IMAGE_A doesn't
- text_clipped       : text cut off at the edge of its box in IMAGE_B
- wrap_mismatch      : same text wraps to a different number of lines, or wraps at a clearly different point
- color_drift        : noticeable color difference (NOT sub-pixel anti-aliasing — only flag when humans would call the color "wrong")
- position_shift     : a block is clearly in the wrong location (>~10px off)
- size_mismatch      : a block is clearly the wrong size
- font_substitution  : visibly different typeface (different letterforms, different serifs, monospace vs proportional, etc.)
- alignment_off      : text alignment differs (left vs center vs right)
- spacing_off        : padding/margin/gap visibly different
- z_order            : overlap order wrong (text behind shape instead of in front, etc.)
- other              : describe explicitly in `description`

Severity:
- high   : breaks fidelity — a reader would notice immediately and call it broken
- medium : visible but acceptable — a careful viewer notices
- low    : subtle — only relevant if pixel-perfect required. PREFER NOT TO REPORT low-severity issues unless they cluster.

Rules:
1. Do NOT report tiny rendering differences (anti-aliasing, sub-pixel kerning).
2. Do NOT compare figures/images for visual content (only check they're present and roughly same size).
3. Do NOT report color drift smaller than ~10% (these are often format/codec artifacts).
4. ONE issue per place. If the same paragraph has 2 different problems (e.g. wrap mismatch AND text clipped), emit 2 issues.
5. When you can tie an issue to a specific block_idx from the JSON, fill block_idx with that integer. When you can't (e.g. a missing decorative border that's not in the text block list), set block_idx to null and describe location precisely in `where`.
6. `where` is a short location string ("top-left corner near 'Heliyon' title", "Section 3 'Method', second paragraph"). Be specific enough that a human reading just `where` can find the spot.
7. `description` is ONE sentence explaining the difference, present tense, like "PPT lacks the orange vertical bar to the left of the title".
8. Return ONLY valid JSON, no prose.

Output schema:
{
  "issues": [
    {"severity": "high|medium|low",
     "category": "<one of the 12 above>",
     "block_idx": <int|null>,
     "where": "<short location>",
     "description": "<one sentence>"}
  ]
}
"""


def _call_claude(html_png: Path, pptx_png: Path, block_summary: list[dict],
                 model: str = "claude-opus-4-8",
                 max_tokens: int = 32768) -> dict:
    """Single vision call. Default Opus 4.8 because vision-diff quality
    is the primary value prop — under-detecting fidelity issues defeats
    the whole pipeline. Opus catches subtle wrap/spacing diffs Sonnet
    sometimes misses (~5× cost: ~$0.10/poster vs ~$0.02). Override via
    `--model` if budget-constrained.

    max_tokens=32768 because extended-thinking blocks burn lots of
    output tokens; old 8192 default truncated JSON mid-issue on complex
    posters (stop_reason=max_tokens), leaving us with unparseable text →
    0 issues silently."""
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    if not token:
        raise RuntimeError("ANTHROPIC_AUTH_TOKEN/API_KEY not set")
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": SYSTEM_PROMPT,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "IMAGE_A (ground truth, HTML browser render):"},
                {"type": "image", "source": {"type": "base64",
                                              "media_type": "image/png",
                                              "data": _b64(html_png)}},
                {"type": "text", "text": "IMAGE_B (current .pptx render):"},
                {"type": "image", "source": {"type": "base64",
                                              "media_type": "image/png",
                                              "data": _b64(pptx_png)}},
                {"type": "text",
                 "text": f"Text block index (JSON):\n```json\n{json.dumps(block_summary)}\n```\n\n"
                         "Walk both images side by side and emit the diff report per the system prompt."},
            ],
        }],
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/v1/messages",
        data=json.dumps(body).encode(),
        headers={"x-api-key": token,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=240) as r:
        resp = json.loads(r.read())
    stop = resp.get("stop_reason", "")
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text").strip()
    if stop == "max_tokens":
        # Model ran out of budget mid-response. Still try to salvage
        # partial JSON; warn so user knows results may be incomplete.
        usage = resp.get("usage", {})
        print(f"[vision] WARNING: hit max_tokens cap "
              f"(in={usage.get('input_tokens')}, out={usage.get('output_tokens')}). "
              f"Some issues may be missing from the report. Raise max_tokens "
              f"if this repeats.", file=sys.stderr)
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("`\n ")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Salvage: response was likely truncated. Find the last complete
        # `}` that closes a top-level "issues" array entry, snip there,
        # and try to close the JSON manually.
        salvaged = _salvage_truncated_json(text)
        if salvaged is not None:
            print(f"[vision] salvaged {len(salvaged.get('issues', []))} issues "
                  f"from truncated response", file=sys.stderr)
            return salvaged
        print(f"[vision] model returned non-JSON / unsalvageable:\n{text[:500]}...",
              file=sys.stderr)
        return {"issues": []}


def _salvage_truncated_json(text: str) -> dict | None:
    """When the model's JSON is truncated mid-issue (stop_reason=max_tokens),
    walk back to the last complete `}` inside the issues array, then close
    the array + outer object manually. Returns parsed dict, or None if
    the truncation is too severe to recover anything."""
    # Find the opening of the issues array
    issues_idx = text.find('"issues"')
    if issues_idx < 0:
        return None
    arr_start = text.find('[', issues_idx)
    if arr_start < 0:
        return None
    # Walk balanced braces inside the array, remembering the position
    # right after each top-level `}`. The last such position is where
    # we can safely truncate.
    depth = 0
    last_complete_end = -1
    i = arr_start + 1
    in_string = False
    escape = False
    while i < len(text):
        c = text[i]
        if escape:
            escape = False
        elif c == '\\':
            escape = True
        elif c == '"':
            in_string = not in_string
        elif not in_string:
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    last_complete_end = i + 1
        i += 1
    if last_complete_end < 0:
        # Not even one complete issue object — give up
        return None
    salvaged_text = text[:last_complete_end] + "]}"
    try:
        return json.loads(salvaged_text)
    except json.JSONDecodeError:
        return None


def _validate(issues: list[dict], n_blocks: int) -> list[dict]:
    clean = []
    for it in issues:
        sev = it.get("severity")
        cat = it.get("category")
        if sev not in SEVERITIES or cat not in CATEGORIES:
            continue
        idx = it.get("block_idx")
        if idx is not None and (not isinstance(idx, int) or not (0 <= idx < n_blocks)):
            idx = None
        clean.append({
            "severity": sev, "category": cat,
            "block_idx": idx,
            "where": str(it.get("where", ""))[:200],
            "description": str(it.get("description", ""))[:400],
        })
    return clean


def audit(html_png: Path, pptx_png: Path, dom: dict,
          model: str = "claude-opus-4-8") -> dict:
    summary = _block_summary(dom)
    resp = _call_claude(html_png, pptx_png, summary, model=model)
    issues = _validate(resp.get("issues", []), len(summary))
    by_cat: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for it in issues:
        by_cat[it["category"]] = by_cat.get(it["category"], 0) + 1
        by_sev[it["severity"]] = by_sev.get(it["severity"], 0) + 1
    return {
        "n_issues": len(issues),
        "by_category": by_cat,
        "by_severity": by_sev,
        "issues": issues,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-png", required=True, type=Path)
    ap.add_argument("--pptx-png", required=True, type=Path)
    ap.add_argument("--dom-json", required=True, type=Path)
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()

    dom = json.loads(a.dom_json.read_text())
    report = audit(a.html_png, a.pptx_png, dom, model=a.model)
    a.out.write_text(json.dumps(report, indent=2))
    print(f"[audit] {report['n_issues']} issues  "
          f"high={report['by_severity'].get('high',0)} "
          f"med={report['by_severity'].get('medium',0)} "
          f"low={report['by_severity'].get('low',0)}  → {a.out}",
          file=sys.stderr)
    for cat, n in sorted(report["by_category"].items(), key=lambda x: -x[1]):
        print(f"   {n:>2d}× {cat}", file=sys.stderr)


if __name__ == "__main__":
    main()
