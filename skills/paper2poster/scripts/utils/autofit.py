"""Deterministic auto-fit — close continuous-lever fill gaps WITHOUT LLM rounds.

The staged-fill loop's `slack` report already prints the EXACT fix magnitude
per section (`needPx`) and the column's spare capacity (`capacitySlack`). The
LLM then hand-types a CSS value to close it, often bisecting across several
measure->edit rounds (real example: a QR height 285->320->340->330). This
module does that deterministically with two continuous levers:

  * **row-gap** — for an under-filled `.grow` card, grow its inner row-gaps by
    `needPx` so the content fills the fixed card height.
  * **qr-height** — for the scan-to-read section whose square QR (`.qr-img`,
    `aspect-ratio: 1/1`, height-driven) is too small, grow the QR height. This
    was the single most hand-tuned lever in practice.

Each pass RE-MEASURES, so no layout-transfer factor needs modelling: a section
still under-filled after a grow is simply grown more; one that overshoots to
SPILLAGE/OVERFLOW is backed off. (The chips scan variant centres its content,
so growing the QR by X only lowers the content bottom by ~X/2 — the QR growth
factor below compensates, and re-measurement finishes the job.) Results are
baked into `poster.html` as an idempotent ``<style id="poster-autofit-baked">``
block (gate-visible — a subsequent `slack` reads the section FULL).

Sections that need net-new content, a `fit()`-managed method figure, or
structural edits are UNTOUCHED and reported as residual for the LLM.

Safety: every grow is bounded by (a) the column's `capacitySlack`, (b) for
row-gap the section's bottom-padding ceiling, for qr the per-QR available width
(a square QR must not overflow its row), and (c) a re-measure gate with
back-off. `--max-passes` (default 4) caps the machine-side loop.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import canvas as _canvas
from . import render as _render
from .cli_common import eprint as _eprint, import_playwright
from .textutil import ascii_safe

_CHECK_POSTER = Path(__file__).resolve().parent.parent / "check_poster.py"
_BAKE_ID = "poster-autofit-baked"
# Chips scan variant centres its content (justify-content:center), so growing
# the QR by X lowers the content bottom by ~X/2. Over-grow to converge in fewer
# passes; the re-measure gate + back-off keep it safe if a variant isn't centred.
_QR_GROWTH = 1.9
# Last-mile ONLY. autofit exists to close the SMALL residual gaps the report
# already sized -- NOT to fill a genuinely under-filled card, which needs
# CONTENT (the LLM's job), not stretched spacing. Filling a big gap with row-gap
# spreads 2-3 rows hundreds of px apart (looks broken); blowing up the QR
# overflows its tile. So cap what a single lever will close; larger gaps are
# reported as residual "needs content" for the LLM.
_MAX_GAP_ADD = 60.0     # row-gap: max px added to ANY single inter-row gap
_MAX_QR_CLOSE = 260.0   # qr: max needPx the QR lever will attempt to close


def _measure(html_path: Path, args: argparse.Namespace) -> dict | None:
    """Run `check_poster.py slack --json-out <tmp> --max-iterations 0` and
    return the parsed report (max-iterations 0 keeps autofit's measurements off
    the loop's persistent circuit breaker)."""
    tmp = Path(tempfile.mkstemp(suffix="_autofit_slack.json")[1])
    cmd = [sys.executable, str(_CHECK_POSTER), "slack", str(html_path),
           "--json-out", str(tmp), "--json", "--max-iterations", "0",
           "--settle-ms", str(args.settle_ms),
           "--mathjax-timeout-ms", str(args.mathjax_timeout_ms)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(tmp.read_text(encoding="utf-8"))
    except Exception:
        _eprint("[autofit] could not measure (slack failed):")
        _eprint(proc.stderr[-800:] if proc.stderr else "(no stderr)")
        return None
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


# Probe the CURRENT lever state per target section (reflects any prior bake,
# since we re-open the baked HTML each pass).
_PROBE_JS = r"""
(sids) => {
  const out = {};
  for (const sid of sids) {
    const sec = document.querySelector('.section[data-section="'+sid+'"]');
    if (!sec) continue;
    const cs = getComputedStyle(sec);
    const s = sec.offsetHeight ? sec.getBoundingClientRect().height / sec.offsetHeight : 1;
    const kids = Array.from(sec.children).filter(k => k.classList
      && !k.classList.contains('listen-btn')
      && !k.classList.contains('dbg-badge')
      && !k.classList.contains('dbg-bbox'));
    const sb = sec.getBoundingClientRect();
    const bot = kids.length ? Math.max.apply(null, kids.map(k => k.getBoundingClientRect().bottom)) : sb.top;
    const padBot = parseFloat(cs.paddingBottom) || 0;
    const innerW = sb.width / (s||1)
      - (parseFloat(cs.paddingLeft)||0) - (parseFloat(cs.paddingRight)||0);
    const rec = {
      rowGap: parseFloat(cs.rowGap) || 0,
      nKids: kids.length,
      slackToPadding: Math.max(0, (sb.bottom - padBot*(s||1)) - bot) / (s||1),
    };
    const qr = sec.querySelector('.qr-img');
    if (qr) {
      const nq = Math.max(1, sec.querySelectorAll('.qr-img').length);
      // square QR side capped so nq QRs + gaps + card padding fit the section
      // width (conservative — horizontal overflow isn't caught by the vertical
      // back-off, so leave ~20% headroom for the card padding + inter-QR gaps).
      rec.qr = { height: qr.getBoundingClientRect().height / (s||1),
                 maxSquare: (innerW * 0.8) / nq };
    }
    out[sid] = rec;
  }
  return out;
}
"""


def _rule(lever: str, sid: str, mag: float) -> str:
    if lever == "qr":
        return (f'.section[data-section="{sid}"] .qr-img'
                f'{{ height: {round(mag, 1)}px !important; }}')
    return f'.section[data-section="{sid}"]{{ row-gap: {round(mag, 1)}px !important; }}'


def _bake(html_path: Path, rules: dict[str, str]) -> None:
    """Persist per-key CSS rule lines into poster.html as one idempotent
    ``<style id="poster-autofit-baked">`` block (distinct id from the render-time
    ``poster-expand-baked`` block, so the two compose)."""
    body = "\n".join(f"  {rules[k]}" for k in sorted(rules))
    block = f'<style id="{_BAKE_ID}">\n{body}\n</style>'
    txt = html_path.read_text(encoding="utf-8")
    if f'id="{_BAKE_ID}"' in txt:
        txt = re.sub(rf'<style id="{_BAKE_ID}">.*?</style>', block, txt, flags=re.S)
    elif "</body>" in txt:
        txt = txt.replace("</body>", block + "\n</body>", 1)
    else:
        txt += "\n" + block
    html_path.write_text(txt, encoding="utf-8")


def _lever(sec: dict) -> str | None:
    """Which continuous lever (if any) can deterministically close this
    section's gap: 'qr', 'row-gap', or None (residual for the LLM)."""
    if sec.get("verdict") not in ("SPARSE", "EMPTY"):
        return None
    if sec.get("needPx") is None or sec["needPx"] <= 0:
        return None
    if sec.get("suppress"):
        return None
    els = sec.get("elements") or []
    idx = sec.get("slackElementIdx")
    slack_el = els[idx] if (idx is not None and 0 <= idx < len(els)) else None
    need = float(sec["needPx"])
    if sec.get("id") == "scan-to-read" or (slack_el and "qr" in (slack_el.get("cls") or "").lower()):
        # Growing the QR only FILLS empty space in a `.grow` scan card. In a
        # non-grow (content-sized) scan card the card just grows with the QR and
        # the gap never closes -> content/relayout problem, not a bigger QR.
        if not sec.get("isGrow"):
            return None
        # Last-mile only: a big scan gap needs content/relayout, not a giant QR.
        if need > _MAX_QR_CLOSE:
            return None
        return "qr"
    if not sec.get("isGrow"):
        return None            # non-grow card sizes to content -> content problem
    if len(els) < 2:
        return None
    if slack_el and slack_el.get("isFigure"):
        return None            # fit()-managed method/secondary figure
    # Last-mile only: if closing the gap would need MORE than _MAX_GAP_ADD px on
    # any single inter-row gap, the card is genuinely under-filled -> content
    # problem for the LLM, not a spacing tweak (avoids the 400px-gap artefact).
    n_gaps = max(1, len(els) - 1)
    if need / n_gaps > _MAX_GAP_ADD:
        return None
    return "row-gap"


def _residual_reason(sec: dict) -> str:
    v = sec.get("verdict")
    els = sec.get("elements") or []
    idx = sec.get("slackElementIdx")
    slack_el = els[idx] if (idx is not None and 0 <= idx < len(els)) else None
    need = float(sec.get("needPx") or 0)
    if v == "OVERFLOW":
        return "OVERFLOW (needs content removal)"
    if v == "SPILLAGE":
        return "SPILLAGE (needs prose tightening)"
    if sec.get("id") != "scan-to-read" and slack_el and slack_el.get("isFigure"):
        return "figure-bound (fit()-managed method/secondary figure)"
    if sec.get("id") == "scan-to-read":
        if not sec.get("isGrow"):
            return "non-grow scan card (needs content/relayout, not a bigger QR)"
        if need > _MAX_QR_CLOSE:
            return f"scan gap too large ({need:.0f}px > {_MAX_QR_CLOSE:.0f}) — needs content/relayout, not a bigger QR"
        return "scan/QR at its width cap (can't grow further)"
    if not sec.get("isGrow"):
        return "non-grow card (needs content, not a continuous lever)"
    n_gaps = max(1, len(els) - 1)
    if need / n_gaps > _MAX_GAP_ADD:
        return f"gap too large ({need:.0f}px over {n_gaps} row(s)) — needs content, not stretched spacing"
    return "needs content/structural edit"


def cmd_autofit(args: argparse.Namespace) -> int:
    pw = import_playwright()
    if pw is None:
        return 2
    sync_playwright, PWTimeoutError = pw

    html_path = Path(args.html).resolve()
    if not html_path.exists():
        _eprint(f"ERROR: HTML not found: {ascii_safe(html_path)}")
        return 2
    resolved = _canvas.resolve_canvas(html_path, args.canvas, label="[autofit]")
    if resolved is None:
        _eprint("ERROR: could not resolve @page canvas from HTML; pass --canvas.")
        return 2
    _canvas_obj, viewport = resolved

    baked: dict[str, str] = {}          # key ("lever:sid") -> CSS rule line
    touched: set[str] = set()           # section ids we've applied a lever to
    max_passes = max(1, int(getattr(args, "max_passes", 4)))

    for _pass in range(max_passes):
        report = _measure(html_path, args)
        if report is None:
            return 1
        by_id = {s["id"]: (s, col) for col in report.get("columns", [])
                 for s in col.get("sections", [])}

        # Decide this pass's actions: grow new/under-filled closables; back off
        # overshoots. Collect the section ids to probe for current lever state.
        actions = []      # (sid, lever, mode)  mode in {"grow","backoff"}
        for sid, (sec, col) in by_id.items():
            key_q, key_r = f"qr:{sid}", f"row-gap:{sid}"
            already = key_q in baked or key_r in baked
            if already and sec.get("verdict") in ("SPILLAGE", "OVERFLOW"):
                lever = "qr" if key_q in baked else "row-gap"
                actions.append((sid, lever, "backoff"))
                continue
            budget = col.get("capacitySlack")
            if budget is not None and float(budget) <= 0 and not already:
                continue                     # over-packed column: don't start growing it
            lever = _lever(sec)
            if lever is None:
                continue
            if sec.get("verdict") == "FULL":
                continue
            actions.append((sid, lever, "grow"))

        if not actions:
            break

        sids = sorted({sid for sid, _, _ in actions})
        with sync_playwright() as p:
            browser, _ctx, page = _render.open_print_emulated_page(p, viewport)
            try:
                page.goto(html_path.as_uri(), wait_until="networkidle",
                          timeout=args.mathjax_timeout_ms)
            except PWTimeoutError:
                browser.close()
                _eprint("[autofit] page did not settle; aborting (soft).")
                return 0
            _render.settle_page(page, mathjax_timeout_ms=args.mathjax_timeout_ms,
                                 settle_ms=args.settle_ms)
            _render.inject_class_fallback_roles(page)
            probe = page.evaluate(_PROBE_JS, sids)
            browser.close()

        changed = False
        for sid, lever, mode in actions:
            info = probe.get(sid)
            if not info:
                continue
            sec = by_id[sid][0]
            need = abs(float(sec.get("needPx") or 0))
            key = f"{lever}:{sid}"
            if lever == "qr":
                qr = info.get("qr")
                if not qr:
                    continue
                cur = float(qr["height"])
                cap = float(qr["maxSquare"])
                if mode == "backoff":
                    new = max(0.0, cur - need)
                else:
                    new = min(cur + _QR_GROWTH * need, cap)
                if abs(new - cur) <= 1:
                    continue
                baked[key] = _rule("qr", sid, new)
            else:  # row-gap
                n_gaps = max(1, int(info["nKids"]) - 1)
                cur = float(info["rowGap"])
                if mode == "backoff":
                    new = max(0.0, cur - need / n_gaps)
                else:
                    ceiling = float(info["slackToPadding"])
                    add = min(need, ceiling) if ceiling > 0 else need
                    new = cur + add / n_gaps
                if abs(new - cur) <= 1:
                    continue
                baked[key] = _rule("row-gap", sid, new)
            touched.add(sid)
            changed = True

        if not changed:
            break
        _bake(html_path, baked)

    # Final report: what closed vs what remains for the LLM.
    final = _measure(html_path, args)
    off_band, residual = set(), []
    if final:
        for col in final.get("columns", []):
            for sec in col.get("sections", []):
                if sec.get("verdict") != "FULL":
                    off_band.add(sec["id"])
                    residual.append((sec["id"], _residual_reason(sec)))
    fixed = sorted(touched - off_band)

    print(f"[autofit] {ascii_safe(html_path.name)}")
    print(f"  closed deterministically: {len(fixed)}"
          + (f" -> {fixed}" if fixed else ""))
    if residual:
        print(f"  still needs LLM edits: {len(residual)}")
        for sid, why in residual:
            print(f"    - {sid}: {why}")
    else:
        print("  no residual — every section is FULL")
    return 0
