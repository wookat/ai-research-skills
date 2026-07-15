#!/usr/bin/env python3
"""render_preview - render a poster HTML to print-ready PDF + thumbnail.

Canvas-agnostic: reads ``@page { size: <W> <H> }`` from the input HTML
or accepts ``--canvas '<W>x<H>in'`` / ``--canvas 'A0 portrait'`` as
override. Print-emulates Chromium so MathJax typesets against the
``@media print`` layout from the start.

This is the SOFT path (vs the HARD ``measure`` gate): a MathJax
typeset timeout or a missing ``<mjx-container>`` warns and continues
— users would rather see raw ``$…$`` on the rendered PDF than a
silent abort.

Outputs:
    <stem>.pdf   exact-size PDF
    <stem>.png   scaled thumbnail (default 0.35×)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make `utils` importable when run directly.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from utils import canvas as _canvas  # noqa: E402
from utils import render as _render  # noqa: E402
from utils.cli_common import eprint as _eprint, import_playwright  # noqa: E402
from utils.textutil import ascii_safe  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0]
    )
    p.add_argument("html", help="poster HTML file")
    p.add_argument(
        "--pdf", default=None,
        help="output PDF path (default: <stem>.pdf)",
    )
    p.add_argument(
        "--png", default=None,
        help="output PNG thumbnail path (default: <stem>.png)",
    )
    p.add_argument(
        "--thumb-scale", type=float, default=0.35,
        help="thumbnail scale factor (default 0.35)",
    )
    p.add_argument(
        "--mathjax-timeout-ms", type=int, default=15000,
        help="timeout for MathJax typesetting (default 15000); "
             "render is the SOFT path; timeout warns, not fails",
    )
    p.add_argument(
        "--canvas", type=_canvas.parse_canvas_arg, default=None,
        help="override canvas (e.g. '60x36in' / 'A0 portrait'); "
             "by default we parse @page from the HTML",
    )
    return p


def _sync_bundled_fonts(html_path: Path) -> None:
    """Mirror the skill's bundled Inter webfonts into <html_dir>/assets/fonts/
    so the @font-face URLs in the template (relative `assets/fonts/Inter-*.woff2`)
    resolve when playwright loads the page. Idempotent — only copies missing
    or stale files. Silent no-op if the skill's fonts/ subdir doesn't exist
    (e.g. user editing a template that doesn't use bundled webfonts).

    Why mirror instead of symlink: the deliverable folder needs to be
    self-contained so a reviewer can zip + share it; a symlink into the
    skill assets would break once the folder leaves this machine.
    """
    import shutil
    skill_fonts = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    if not skill_fonts.is_dir():
        return
    out_fonts = html_path.parent / "assets" / "fonts"
    out_fonts.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in skill_fonts.glob("*.woff2"):
        dst = out_fonts / src.name
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dst)
            copied += 1
    if copied:
        _eprint(f"[render_preview] mirrored {copied} font file(s) -> "
                f"{out_fonts.relative_to(html_path.parent)}/")


def _bake_expand_into_html(html_path: Path, baked: list) -> None:
    """Persist the render-time expand into the deliverable poster.html.

    The expand pass grows each under-filled card's inner row-gaps in the live
    DOM before printing the PDF/PNG. To keep the editable poster.html (its `D`
    debug overlay, and the downstream html2pptx read) consistent with the
    rendered PDF/PNG, write the resulting row-gaps back as one
    <style id="poster-expand-baked"> block. Responsive-safe: the templates use a
    fixed internal layout scaled by an outer `transform: scale()`, so an inline
    px row-gap renders identically at any view size. Idempotent -- a re-render
    replaces the block instead of stacking duplicates. Written only at final
    render (after the fill loop), so the loop still measures the natural layout.
    """
    import re
    rules = "\n".join(
        f'  .section[data-section="{sid}"]{{ row-gap: {gap} !important; }}'
        for sid, gap in baked
    )
    block = f'<style id="poster-expand-baked">\n{rules}\n</style>'
    txt = html_path.read_text(encoding="utf-8")
    if 'id="poster-expand-baked"' in txt:
        txt = re.sub(r'<style id="poster-expand-baked">.*?</style>', block, txt, flags=re.S)
    elif "</body>" in txt:
        txt = txt.replace("</body>", block + "\n</body>", 1)
    else:
        txt += "\n" + block
    html_path.write_text(txt, encoding="utf-8")


def _bake_scan_suppress_into_html(html_path: Path) -> None:
    """Persist a render-time Scan-to-Read suppression into poster.html.

    When the aspect-ratio guard (below) decides the Scan-to-Read section is too
    elongated for its little QR + caption (the lone-QR-in-empty-space defect),
    it sets the section `display:none` on the live page before the expand pass,
    so the column reflows and the expand pass refills the freed space into the
    flex-grow neighbours. To keep the editable poster.html, its `D` overlay, and
    the downstream html2pptx read consistent with the rendered PDF/PNG, write the
    same suppression back as one idempotent <style> block (mirrors
    `_bake_expand_into_html`; `display:none !important` wins regardless of block
    position). This generalises the 3col layout's static scan suppression to any
    layout whose scan column came out as elongated as a 3-column even split.
    """
    block = ('<style id="poster-scan-suppress">\n'
             '  .section[data-section="scan-to-read"] { display: none !important; }\n'
             '</style>')
    txt = html_path.read_text(encoding="utf-8")
    if 'id="poster-scan-suppress"' in txt:
        return                                      # already suppressed (idempotent)
    if "</body>" in txt:
        txt = txt.replace("</body>", block + "\n</body>", 1)
    else:
        txt += "\n" + block
    html_path.write_text(txt, encoding="utf-8")


def _autopack_header_logos(html_path: Path) -> None:
    """Step 5.9 auto-run: pack the header institution logos so they FILL their
    zone (multi-row, grown to fit) instead of one tiny row. This is a manual
    step in the docs that the agent routinely skips, so run it here right before
    rendering. Soft: any failure just leaves the raw logos and never blocks the
    render (best-effort, like the render-time expand pass)."""
    import subprocess
    fit = Path(__file__).resolve().parent.parent / "references" / "fit_logos.py"
    if not fit.exists():
        return
    try:
        r = subprocess.run([sys.executable, str(fit), "--poster", str(html_path)],
                           capture_output=True, text=True, timeout=180)
        for line in (r.stdout or "").splitlines():
            if "baked" in line or "fit_logos" in line:
                print(f"[render_preview] {line.strip()}")
    except Exception as e:                       # noqa: BLE001 -- soft, never block render
        _eprint(f"[render_preview] fit_logos auto-pack skipped ({e})")


def main() -> int:
    args = build_parser().parse_args()

    html_path = Path(args.html).resolve()
    if not html_path.exists():
        _eprint(f"ERROR: HTML not found: {ascii_safe(html_path)}")
        return 2

    _sync_bundled_fonts(html_path)
    _autopack_header_logos(html_path)   # Step 5.9, auto-run so it's never skipped

    pdf_path = (
        Path(args.pdf) if args.pdf
        else html_path.with_name(html_path.stem + ".pdf")
    )
    png_path = (
        Path(args.png) if args.png
        else html_path.with_name(html_path.stem + ".png")
    )

    resolved = _canvas.resolve_canvas(
        html_path, args.canvas, label="[render_preview]"
    )
    if resolved is None:
        _eprint(
            "ERROR: could not find `@page { size: <W> <H> }` in HTML. "
            "Add an @page rule (units: in/mm/cm/pt) or pass "
            "`--canvas <W>x<H>in` / `--canvas 'A0 portrait'`. "
            "Refusing to silently fall back."
        )
        return 2
    canvas, viewport = resolved
    w_in, h_in = canvas

    pw = import_playwright()
    if pw is None:
        return 2
    sync_playwright, PWTimeoutError = pw

    with sync_playwright() as p_:
        browser, _ctx, page = _render.open_print_emulated_page(
            p_, viewport
        )
        # Soft path: a hung CDN (blocked MathJax fetch, unreachable
        # web font) must not hard-crash render. Playwright's default
        # `page.goto` waits for `load` (all subresources), which can
        # block ~30s on a single blocked CDN. settle_page below has
        # its own bounded waits; let it surface MathJax issues as
        # warnings, not tracebacks.
        try:
            page.goto(html_path.as_uri(), timeout=args.mathjax_timeout_ms)
        except PWTimeoutError:
            _eprint(
                f"[render_preview] WARN: page.goto did not reach `load` "
                f"within {args.mathjax_timeout_ms} ms; continuing with "
                f"whatever has loaded (a CDN or external resource is "
                f"likely blocked)."
            )
        try:
            page.wait_for_load_state(
                "networkidle", timeout=args.mathjax_timeout_ms,
            )
        except PWTimeoutError:
            _eprint(
                f"[render_preview] WARN: network never went idle within "
                f"{args.mathjax_timeout_ms} ms; continuing with whatever "
                f"loaded (likely a slow/blocked external resource)."
            )

        settle = _render.settle_page(
            page,
            mathjax_timeout_ms=args.mathjax_timeout_ms,
            settle_ms=1500,
        )
        # Render is soft path: warn but continue, even on MathJax
        # problems — the user can SEE raw $...$ on the resulting PDF.
        if settle.mathjax_status == "timeout":
            _eprint(
                f"[render_preview] WARN: MathJax typeset timed out "
                f"after {args.mathjax_timeout_ms} ms."
            )
        elif settle.mathjax_status == "error":
            _eprint(
                f"[render_preview] WARN: MathJax error: "
                f"{ascii_safe(settle.mathjax_error)}"
            )
        if settle.mathjax_intended and settle.tex_without_mathjax:
            _eprint(
                "[render_preview] WARN: page intended to load MathJax "
                "but no <mjx-container> rendered -- MathJax may have "
                "failed to load. PDF will show raw $...$ text."
            )

        # Scan-to-Read aspect guard (runs BEFORE the expand pass). A scan section
        # that came out wide and flat -- its own width many times its own height
        # -- holds just a small QR (and maybe a heading) marooned in horizontal
        # empty space. Poster #8 is the worst case: a grid column that blew out
        # to ~2x width (a wide unbreakable child forced the track wider) left the
        # directory scan variant a 730x156 px band with one 110 px QR filling
        # ~15% of the width. The metric is the section's OWN aspect ratio
        # (width / height) -- NOT relative to the canvas -- mirroring the 3col
        # layout's static suppression ("far more horizontal room than its little
        # content fills"). When width/height exceeds the threshold, hide the
        # section now so the column reflows and the expand pass below refills the
        # freed height into the flex-grow neighbours. Defensive: a scan section
        # that is the ONLY section in its column is never removed (would blank a
        # whole column). Tunable via POSTER_SCAN_SUPPRESS_WH (default 3.8 -- in
        # the v2 benchmark the offending #8 reads ~4.7 while well-filled scan
        # sections sit at 1.2-3.3; 0 disables).
        _scan_suppressed = False
        try:
            _scan_wh = float(os.environ.get("POSTER_SCAN_SUPPRESS_WH", "3.8"))
        except Exception:
            _scan_wh = 3.8
        if _scan_wh > 0:
            try:
                _sv = page.evaluate(
                    """(T) => {
                      const sec = document.querySelector('.section[data-section="scan-to-read"]');
                      if (!sec) return {act:false, why:'none'};
                      const r = sec.getBoundingClientRect();
                      if (r.width < 4 || r.height < 4) return {act:false, why:'hidden'};
                      const col = sec.closest('.col');
                      if (col && col.querySelectorAll('.section').length <= 1)
                        return {act:false, why:'alone'};        // never blank a whole column
                      const wh = r.width / r.height;            // the section's OWN aspect (width / height)
                      if (wh >= T) { sec.style.display = 'none';
                        return {act:true, why:'aspect', wh: wh}; }
                      return {act:false, why:'within', wh: wh};
                    }""",
                    _scan_wh,
                )
                if isinstance(_sv, dict) and _sv.get("wh") is not None:
                    _eprint(
                        "[render_preview] Scan-to-Read aspect (w/h) "
                        f"{round(float(_sv['wh']), 2)} "
                        f"(suppress at >= {_scan_wh}) -> "
                        f"{'SUPPRESSED' if _sv.get('act') else 'kept'}."
                    )
                if isinstance(_sv, dict) and _sv.get("act"):
                    _scan_suppressed = True
                    page.wait_for_timeout(120)          # let the column reflow before the expand pass measures it
            except Exception:
                pass

        # Expand deliverable: stretch each under-filled card's inner content to
        # ~POSTER_EXPAND_THRESHOLD of the card (default 0.98) by growing the
        # row-gaps BETWEEN its rows -- COLUMN bottoms stay aligned and FIGURES ARE
        # NEVER RESIZED. Figure cards are NOT skipped: growing the gaps between
        # rows only adds whitespace between rows; templates pin figures at
        # `flex:0 0 auto` (natural size), so the <img> keeps its exact aspect ratio
        # (verified: img w/h unchanged). Two guardrails: (a) the slack cap -- never
        # push content past the bottom padding; (b) the PARENT-height revert -- if
        # growing the gap changes the card's CONTAINER (column/grid) height, undo
        # it. (b) is deliberately on the parent, not the card: a flex:1 grow card
        # absorbs the fill inside its column (column height unchanged -> bottoms
        # stay put -> we DO fill that trailing space, which is the whole point),
        # whereas a grid/content card whose fill would grow its container (pushing
        # the fixed-canvas layout) is reverted. This is a render-time "expand"
        # pass separate from the staged-fill loop's FILL gate (POSTER_FULL_THRESHOLD,
        # default 0.90): the loop still measures the natural top-aligned layout via
        # check_poster.py so the fill gate stays correct; this only makes the final
        # deliverable read fuller. Configurable: POSTER_EXPAND_THRESHOLD (0 disables).
        try:
            _expand_t = float(os.environ.get("POSTER_EXPAND_THRESHOLD", "0.98"))
        except Exception:
            _expand_t = 0.98
        if _expand_t > 0:
            try:
                page.evaluate(
                    """(T) => {
                      document.querySelectorAll('.section').forEach(sec => {
                        // Figure cards are NOT skipped: growing the row-gaps BETWEEN
                        // rows never resizes a figure (figure{flex:0 0 auto}). The
                        // guardrails are the slack cap + the parent-height revert.
                        const kids = Array.from(sec.children).filter(k => k.classList
                          && !k.classList.contains('listen-btn')
                          && !k.classList.contains('dbg-badge')
                          && !k.classList.contains('dbg-bbox'));
                        if (kids.length < 2) return;                      // need >=2 rows to add a gap
                        const sb = sec.getBoundingClientRect();
                        const bot = Math.max.apply(null, kids.map(k => k.getBoundingClientRect().bottom));
                        const cur = (bot - sb.top) / sb.height;
                        if (cur >= T) return;                             // already at/above target
                        const cs = getComputedStyle(sec);
                        const padBot = parseFloat(cs.paddingBottom) || 0;
                        // getBoundingClientRect is post-transform (screen) px but
                        // paddingBottom is layout px; convert padding by the live
                        // scale so the slack cap is in the same coordinate frame.
                        const s = sec.offsetHeight ? sb.height / sec.offsetHeight : 1;
                        const slack = (sb.bottom - padBot * s) - bot;     // px before content hits padding
                        if (slack <= 1) return;
                        const add = Math.min((T - cur) * sb.height, slack);
                        const per = add / (kids.length - 1);
                        const curGap = parseFloat(cs.rowGap) || 0;
                        // Revert if the CONTAINER (column/grid) height changes: a
                        // grow card absorbs the fill in-column (no change -> keep);
                        // a card that would push its container taller is undone, so
                        // no column bottom ever moves and the poster never overflows.
                        const par = sec.parentElement;
                        const pH0 = par ? par.getBoundingClientRect().height : 0;
                        sec.style.rowGap = (curGap + per) + 'px';
                        if (par && Math.abs(par.getBoundingClientRect().height - pH0) > 1) {
                          sec.style.rowGap = curGap + 'px';
                        }
                      });
                    }""",
                    _expand_t,
                )
                page.wait_for_timeout(150)
                # Persist the expand into the deliverable html so poster.html,
                # its `D` overlay, the PDF/PNG, and the downstream html2pptx read
                # all show the same expanded layout (not the pre-expand one).
                _baked = page.evaluate(
                    """() => {
                      const o = [];
                      document.querySelectorAll('.section[data-section]').forEach(sec => {
                        if (sec.style && sec.style.rowGap)
                          o.push([sec.getAttribute('data-section'), sec.style.rowGap]);
                      });
                      return o;
                    }"""
                )
                if _baked:
                    _bake_expand_into_html(html_path, _baked)
            except Exception:
                pass

        # Persist the scan suppression into poster.html so the editable HTML,
        # the PDF/PNG, and the downstream html2pptx read all hide the section
        # (the live page already does; this makes it durable on disk).
        if _scan_suppressed:
            _bake_scan_suppress_into_html(html_path)

        # ---- PDF: exact poster size, print-emulated ----
        page.pdf(
            path=str(pdf_path),
            width=f"{w_in}in",
            height=f"{h_in}in",
            print_background=True,
            margin={"top": "0", "bottom": "0",
                    "left": "0", "right": "0"},
        )

        # ---- PNG: scaled thumbnail of `.poster` (or document body) ----
        # IMPORTANT: do NOT resize the viewport for the screenshot. The
        # poster CSS uses `width: min(100vw, calc(100vh * 5 / 3))`, so a
        # viewport change retriggers reflow and the scaled poster ends up
        # occupying only a fraction of the captured area. Instead, keep
        # the print viewport, apply the scale transform, and `clip` the
        # screenshot to the scaled region.
        s = args.thumb_scale
        page.evaluate(
            f"""() => {{
                const el = document.querySelector(
                       '[data-measure-role="poster"]')
                       || document.querySelector('.poster')
                       || document.body;
                el.style.transformOrigin = 'top left';
                el.style.transform = 'scale({s})';
                document.body.style.margin = '0';
                document.documentElement.style.margin = '0';
            }}"""
        )
        thumb_w = int(round(w_in * 96 * s))
        thumb_h = int(round(h_in * 96 * s))
        page.screenshot(
            path=str(png_path),
            full_page=False,
            clip={"x": 0, "y": 0,
                  "width": thumb_w, "height": thumb_h},
        )

        browser.close()

    print(
        f"[render_preview] PDF -> {ascii_safe(pdf_path)}  "
        f"({pdf_path.stat().st_size / 1024:.1f} KB)"
    )
    print(
        f"[render_preview] PNG -> {ascii_safe(png_path)}  "
        f"({png_path.stat().st_size / 1024:.1f} KB)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
