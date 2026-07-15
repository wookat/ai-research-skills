"""Vision-based PPT vs HTML render comparison → structured corrections.

Replaces PIL-based L2 height prediction with Claude vision diff.
Pipeline:
1. Render HTML to PNG (truth) + PPT to PNG (current attempt)
2. Build a compact block-index summary (idx, tag, bbox, text preview)
3. Send both PNGs + DOM summary to Claude vision
4. Model returns JSON list of corrections, each tied to a block_idx
5. Caller merges into corrections dict, rebuilds PPT, optionally iterates

Three modes:
- full: one vision call comparing both full images
- patch: NxN grid; each cell compared independently; corrections deduped
- hybrid: full call returns suspect regions; zoom into each at full-res

Constrained action space (model can only choose from these):
- font_scale: float in [0.7, 1.1] — multiply text font size
- letter_spacing_delta: float in [-0.05, 0.05] em — tighten/loosen tracking
- width_scale: float in [0.9, 1.2] — widen/narrow text box
- x_shift_px: int in [-30, 30] — nudge horizontally

Mapping to html_to_pptx.build_pptx's corrections format:
  {block_idx_str: {"font_scale": 0.95, "letter_spacing_delta": -0.01, ...}}
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Literal


# ── Action space (must stay in sync with html_to_pptx.build_pptx) ────────
# MVP: only font_scale is wired into build_pptx. The other properties below
# are documented for future expansion but the vision prompt restricts the
# model to font_scale to keep the action space tractable + matching what
# the renderer can actually apply.
VALID_PROPS = {
    "font_scale": (0.70, 1.10),
}


def _b64(p: Path) -> str:
    return base64.standard_b64encode(p.read_bytes()).decode()


def _block_summary(dom: dict, max_blocks: int = 60) -> list[dict]:
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


def _system_prompt() -> str:
    return """You are a visual-fidelity diff judge. You receive two renderings of the same poster:
- IMAGE_A: ground truth (HTML render in a browser at print viewport)
- IMAGE_B: current attempt (the .pptx rendering of the same poster)

You also receive a JSON list of text blocks the .pptx is built from. Each block has an `idx` (integer), `tag`, bbox (x/y/w/h in CSS px on the HTML), and a short `text` preview so you can identify which block is which.

Your job: identify text blocks where IMAGE_B visibly differs from IMAGE_A in a way that hurts fidelity, and propose ONE correction per affected block from this constrained action space:

| property | range | what it does |
|---|---|---|
| font_scale | [0.70, 1.10] | multiply text font-size. Use to fix wrap count mismatch, text overflow, density differences. Reduce when IMAGE_B's text wraps to MORE lines than IMAGE_A (text too big); increase when fewer lines (text too small). |

DO NOT report:
- Tiny rendering differences (anti-aliasing, sub-pixel kerning, color drift < 5%)
- Differences in figures or images (only text blocks are correctable)
- Layout differences caused by background gradients/shadows
- Anything you can't map to a specific block_idx

If IMAGE_B looks faithful (≥ 95% match in text blocks), return an empty list. Don't invent corrections just to fill the response.

Return ONLY valid JSON, no prose:
{
  "corrections": [
    {"block_idx": <int>, "property": "<one of the 4>", "value": <number>, "reason": "<one short sentence>"}
  ]
}
"""


def _call_claude(prompt: str, html_png: Path, pptx_png: Path,
                 block_summary: list[dict],
                 model: str = "claude-sonnet-4-6",
                 max_tokens: int = 4096) -> dict:
    """One vision call. Returns parsed JSON dict from the model."""
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    if not token:
        raise RuntimeError("ANTHROPIC_AUTH_TOKEN/API_KEY not set")
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": _system_prompt(),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "IMAGE_A (ground truth, HTML render):"},
                {"type": "image", "source": {"type": "base64",
                                              "media_type": "image/png",
                                              "data": _b64(html_png)}},
                {"type": "text", "text": "IMAGE_B (current .pptx render):"},
                {"type": "image", "source": {"type": "base64",
                                              "media_type": "image/png",
                                              "data": _b64(pptx_png)}},
                {"type": "text",
                 "text": f"Text block index (JSON):\n```json\n{json.dumps(block_summary)}\n```\n\n{prompt}"},
            ],
        }],
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": token,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read())
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    # Strip ```json fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("`\n ")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"[vision] model returned non-JSON:\n{text[:500]}", file=sys.stderr)
        return {"corrections": []}


def _validate_corrections(raw: list[dict], n_blocks: int) -> list[dict]:
    """Drop anything out-of-range or referencing unknown block."""
    clean = []
    for c in raw:
        idx = c.get("block_idx")
        prop = c.get("property")
        val = c.get("value")
        if not isinstance(idx, int) or not (0 <= idx < n_blocks):
            continue
        if prop not in VALID_PROPS:
            continue
        if not isinstance(val, (int, float)):
            continue
        lo, hi = VALID_PROPS[prop]
        if not (lo <= val <= hi):
            val = max(lo, min(hi, val))
        clean.append({"block_idx": idx, "property": prop,
                      "value": val, "reason": c.get("reason", "")[:200]})
    return clean


def compare_full(html_png: Path, pptx_png: Path, dom: dict,
                 model: str = "claude-sonnet-4-6") -> list[dict]:
    """Mode 1: one vision call on both full images."""
    summary = _block_summary(dom)
    resp = _call_claude(
        "Compare the two images and return corrections per the system prompt.",
        html_png, pptx_png, summary, model=model)
    return _validate_corrections(resp.get("corrections", []), len(summary))


def compare_patch(html_png: Path, pptx_png: Path, dom: dict,
                  grid: int = 3,
                  model: str = "claude-sonnet-4-6") -> list[dict]:
    """Mode 2: NxN grid; one call per cell."""
    from PIL import Image
    A = Image.open(html_png); B = Image.open(pptx_png)
    if A.size != B.size:
        # Resize pptx to html size for cell-aligned comparison
        B = B.resize(A.size)
    W, H = A.size
    cw, ch = W // grid, H // grid
    summary = _block_summary(dom)
    # Scale block bboxes from HTML CSS-px to image-px (assume html_png is at design viewport)
    sx, sy = W / dom["body_w"], H / dom["body_h"]
    seen_by_block = {}  # dedup, keep strongest |delta|
    for gy in range(grid):
        for gx in range(grid):
            x0, y0 = gx * cw, gy * ch
            x1, y1 = x0 + cw, y0 + ch
            # Filter blocks whose center falls in this cell
            cell_blocks = [b for b in summary
                           if x0 <= (b["x"] + b["w"]/2) * sx < x1
                           and y0 <= (b["y"] + b["h"]/2) * sy < y1]
            if not cell_blocks:
                continue
            ap = html_png.with_suffix(f".cell_{gy}{gx}.A.png")
            bp = html_png.with_suffix(f".cell_{gy}{gx}.B.png")
            A.crop((x0, y0, x1, y1)).save(ap)
            B.crop((x0, y0, x1, y1)).save(bp)
            resp = _call_claude(
                f"Compare these crops (region: x{x0}-{x1}, y{y0}-{y1} of full poster). "
                "Only flag blocks listed below; ignore visual cutoff at crop edges.",
                ap, bp, cell_blocks, model=model)
            for c in _validate_corrections(resp.get("corrections", []), len(summary)):
                cur = seen_by_block.get(c["block_idx"])
                if cur is None or abs(c["value"] - 1.0) > abs(cur["value"] - 1.0):
                    seen_by_block[c["block_idx"]] = c
            # Clean up cell crops
            ap.unlink(missing_ok=True); bp.unlink(missing_ok=True)
    return list(seen_by_block.values())


def compare_hybrid(html_png: Path, pptx_png: Path, dom: dict,
                   model: str = "claude-sonnet-4-6") -> list[dict]:
    """Mode 3: full pass first, then zoom into model-flagged regions."""
    # Round 1: full pass
    first = compare_full(html_png, pptx_png, dom, model=model)
    if not first:
        return []
    # Round 2: zoom into the bboxes of every flagged block (group by proximity)
    from PIL import Image
    A = Image.open(html_png); B = Image.open(pptx_png)
    if A.size != B.size:
        B = B.resize(A.size)
    W, H = A.size
    sx, sy = W / dom["body_w"], H / dom["body_h"]
    text_blocks = sorted(dom["text_blocks"],
                         key=lambda t: (t["depth"], t["y"], t["x"]))
    refined = []
    for c in first:
        b = text_blocks[c["block_idx"]]
        # Zoom in: 1.5x padding around the block
        pad_x = b["w"] * 0.5; pad_y = b["h"] * 0.5
        x0 = max(0, int((b["x"] - pad_x) * sx))
        y0 = max(0, int((b["y"] - pad_y) * sy))
        x1 = min(W, int((b["x"] + b["w"] + pad_x) * sx))
        y1 = min(H, int((b["y"] + b["h"] + pad_y) * sy))
        ap = html_png.with_suffix(f".zoom_{c['block_idx']}.A.png")
        bp = html_png.with_suffix(f".zoom_{c['block_idx']}.B.png")
        A.crop((x0, y0, x1, y1)).save(ap)
        B.crop((x0, y0, x1, y1)).save(bp)
        # Only ask about this one block
        summary = [b for b in _block_summary(dom) if b["idx"] == c["block_idx"]]
        resp = _call_claude(
            f"Zoomed-in comparison of block #{c['block_idx']}. Confirm or refine the round-1 "
            f"suggestion (was: {c['property']}={c['value']}). Return AT MOST 1 correction.",
            ap, bp, summary, model=model)
        clean = _validate_corrections(resp.get("corrections", []), len(text_blocks))
        if clean:
            refined.append(clean[0])
        ap.unlink(missing_ok=True); bp.unlink(missing_ok=True)
    return refined


def to_corrections_dict(items: list[dict]) -> dict:
    """Convert list-of-corrections to {idx_str: {prop: val, ...}} for build_pptx."""
    out: dict[str, dict] = {}
    for c in items:
        key = str(c["block_idx"])
        out.setdefault(key, {})[c["property"]] = c["value"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-png", required=True, type=Path)
    ap.add_argument("--pptx-png", required=True, type=Path)
    ap.add_argument("--dom-json", required=True, type=Path)
    ap.add_argument("--mode", choices=["full", "patch", "hybrid"], default="full")
    ap.add_argument("--grid", type=int, default=3, help="patch mode: NxN grid")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--out", required=True, type=Path,
                    help="JSON: list-of-corrections AND merged dict")
    a = ap.parse_args()

    dom = json.loads(a.dom_json.read_text())
    if a.mode == "full":
        items = compare_full(a.html_png, a.pptx_png, dom, model=a.model)
    elif a.mode == "patch":
        items = compare_patch(a.html_png, a.pptx_png, dom, grid=a.grid, model=a.model)
    else:
        items = compare_hybrid(a.html_png, a.pptx_png, dom, model=a.model)

    merged = to_corrections_dict(items)
    a.out.write_text(json.dumps({"mode": a.mode, "items": items,
                                  "corrections": merged}, indent=2))
    print(f"[vision-{a.mode}] {len(items)} corrections → {a.out}", file=sys.stderr)
    for c in items[:10]:
        print(f"   block #{c['block_idx']}: {c['property']}={c['value']:.3f}  "
              f"({c['reason'][:80]})", file=sys.stderr)


if __name__ == "__main__":
    main()
