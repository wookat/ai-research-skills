"""Single-shot HTML → PPTX renderer + comparison PNG generator.

Pipeline:
1. Resolve canvas size (CSS @page > CLI > A0 default), cap to PPT 55" max
2. Detect + alias reference-PDF fonts (sibling poster.pdf), or auto-download from Google Fonts
3. Extract DOM via playwright (one-shot, cached as <name>_dom.json)
4. Build PPTX via html_to_pptx.build_pptx
5. Render PPTX → PDF → PNG via soffice for visual sanity-check
6. Also render HTML at print viewport + 1920×1080 browser viewport for side-by-side compare

History note: this script previously ran an "L2" closed-loop that re-measured
each text block with PIL after each round and shrank overflowing blocks. Audit
on 9 posters showed the PIL prediction was decoupled from soffice's actual
render: shrink rounds produced identical overflow counts (e.g. 17→17→17→17 on
paper_4_d), with occasional false-positive shrinks on body paragraphs that
weren't actually overflowing in the rendered output. The loop was removed
2026-06-05 — getting wrap detection right at DOM extraction time is the real
fix; cosmetic shrinking after-the-fact only hides the bug.

Usage:
  python -m scripts.auto_correct_loop \\
      --html /path/poster.html \\
      --outdir /tmp/
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

THIS = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS))
from html_to_pptx import (extract_dom, build_pptx,  # type: ignore
                          detect_canvas_size, cap_to_pptx_slide,
                          DEFAULT_W_INCH, DEFAULT_H_INCH, FONT_ALIASES)
from font_resolver import (detect_pdf_fonts, build_pdf_alias_map,
                            extract_font_families,
                            ensure_font_installed_simple,
                            write_runtime_aliases, clear_runtime_aliases)  # type: ignore


def render_pptx_to_png(pptx: Path, png_out: Path, dpi: int = 96) -> None:
    """soffice → PDF → PNG.

    Note: do NOT `pkill -f soffice` here — when this function runs in
    parallel (multiple posters at once), sibling processes will kill each
    others soffice mid-conversion. The headless soffice is single-process
    per invocation and exits on its own; no preemptive kill needed.
    Use a user-profile dir so concurrent invocations don't fight over
    the shared ~/.config/libreoffice lock.
    """
    pdf = pptx.with_suffix(".pdf")
    profile_dir = pptx.parent / f".soffice_profile_{pptx.stem}"
    subprocess.run(
        ["soffice", "--headless",
         f"-env:UserInstallation=file://{profile_dir}",
         "--convert-to", "pdf", "--outdir",
         str(pdf.parent), str(pptx)],
        capture_output=True, timeout=180
    )
    from pdf2image import convert_from_path
    imgs = convert_from_path(str(pdf), dpi=dpi)
    imgs[0].save(str(png_out))
    # Clean up the per-invocation profile dir
    import shutil
    shutil.rmtree(profile_dir, ignore_errors=True)


def render_html_to_png(html_path: Path, png_out: Path,
                       viewport_w: int, viewport_h: int,
                       full_page: bool = False) -> None:
    """Render HTML at a specific viewport via playwright. Used for side-by-side
    comparison: print/design viewport vs typical browser viewport (responsive
    posters wrap differently at each).

    full_page=False: clipped screenshot of viewport (matches print canvas).
    full_page=True: capture entire body (matches browser-view of overflow)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": viewport_w,
                                       "height": viewport_h}).new_page()
        page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
        page.wait_for_timeout(500)
        if full_page:
            page.screenshot(path=str(png_out), full_page=True)
        else:
            page.screenshot(path=str(png_out),
                            clip={"x": 0, "y": 0,
                                  "width": viewport_w, "height": viewport_h})
        b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True, type=Path)
    ap.add_argument("--outdir", type=Path, default=None,
                    help="Output directory. Defaults to ./output/<UTC_timestamp>/ "
                         "(e.g. ./output/20260605-094512/) so successive runs don't "
                         "clobber each other.")
    ap.add_argument("--name", default="poster",
                    help="output filename prefix -> <name>.pptx (default poster, "
                         "matching the input poster.html and auto_fix_loop)")
    ap.add_argument("--width-inch", type=float, default=None,
                    help="Slide width inches. Auto-detected from CSS @page if omitted.")
    ap.add_argument("--height-inch", type=float, default=None,
                    help="Slide height inches. Auto-detected from CSS @page if omitted.")
    ap.add_argument("--no-auto-fonts", action="store_true",
                    help="Skip auto-detecting + downloading fonts referenced by "
                         "the HTML from Google Fonts.")
    ap.add_argument("--reference-pdf", type=Path, default=None,
                    help="Path to a reference PDF whose font set the PPT "
                         "should match. Also auto-detected from <html_dir>/"
                         "poster.pdf if exists.")
    # Vision-audit is ON by default — it's the only signal that catches
    # structural fidelity bugs (missing logos, dropped spans, wrap drift)
    # the pipeline can't self-diagnose. Cost is ~1 vision call (~$0.02
    # Sonnet) and ~70s extra runtime. Silently skipped when auth env vars
    # missing (offline / CI / no key) so opt-out isn't required there.
    # Pass --no-vision-audit for batch automation where the extra call
    # would compound (100 posters = ~$2 + ~2hr extra).
    ap.add_argument("--vision-audit", action=argparse.BooleanOptionalAction,
                    default=True,
                    help="Run Claude vision fidelity diff after render. "
                         "ON by default. Writes <name>_audit.json with "
                         "structured issues (severity, category, block_idx, "
                         "where, description) and prints +/- delta vs prior "
                         "run. Auth: needs either ANTHROPIC_AUTH_TOKEN "
                         "(direct API) or ANTHROPIC_BASE_URL + AUTH_TOKEN "
                         "(corporate proxy / Vertex / Bedrock). Missing "
                         "auth → silent skip. Use --no-vision-audit to "
                         "explicitly disable.")
    ap.add_argument("--vision-model", default="claude-opus-4-8",
                    help="Vision model for --vision-audit. Default Opus 4.8 "
                         "(highest quality vision-diff). Override with e.g. "
                         "claude-sonnet-4-6 for ~5× cost savings if budget "
                         "matters more than catch-rate.")
    # Back-compat: accept and ignore old loop flags so existing call sites
    # don't break. These flags no longer do anything.
    ap.add_argument("--rounds", type=int, default=0, help=argparse.SUPPRESS)
    ap.add_argument("--shrink-step", type=float, default=0.95, help=argparse.SUPPRESS)
    ap.add_argument("--match-wrap", action=argparse.BooleanOptionalAction, default=True,
                    help="Force PPT to wrap at the same character positions Chrome "
                         "wrapped at. Default ON — preserves relative height "
                         "proportions across the poster (without it, the browser vs "
                         "PowerPoint font shaper disagrees on glyph widths, so PPT "
                         "fits more chars per line and multi-line callouts/paragraphs "
                         "collapse vertically, distorting how text blocks sit next to "
                         "each other). Disable with --no-match-wrap if a specific "
                         "poster hits a wrap-split edge case.")
    a = ap.parse_args()

    # Default outdir = ./output/<real-time UTC timestamp>/ — each run
    # gets its own dir so successive runs don't overwrite each other.
    # Resolve to absolute path so downstream subprocess calls with
    # different cwd (e.g. soffice, fix-loop's per-run copy) still locate it.
    if a.outdir is None:
        # Default convention (per teacher's spec, 2026-06-12): outputs
        # land in the input HTML's PARENT directory — co-located with
        # the source. For pipeline runs `<folder>/<stem>/poster.html`,
        # this puts poster.pptx beside poster.html at `<folder>/<stem>/`.
        # For standalone CLI runs, the user gets a .pptx next to the
        # HTML they passed in. Pass --outdir explicitly to override.
        a.outdir = a.html.parent
        print(f"[outdir] defaulting to input HTML's parent: {a.outdir.resolve()}",
              file=sys.stderr)
    a.outdir = a.outdir.resolve()

    a.outdir.mkdir(parents=True, exist_ok=True)

    # Resolve canvas: explicit CLI > CSS @page > A0 default
    design_w, design_h = a.width_inch, a.height_inch
    if design_w is None or design_h is None:
        detected = detect_canvas_size(a.html)
        if detected:
            print(f"[canvas] auto-detected from @page: {detected[0]:.1f}×{detected[1]:.1f}\"",
                  file=sys.stderr)
            design_w = design_w or detected[0]
            design_h = design_h or detected[1]
        else:
            print(f"[canvas] no @page in HTML — using A0 fallback {DEFAULT_W_INCH}×{DEFAULT_H_INCH}\"",
                  file=sys.stderr)
            design_w = design_w or DEFAULT_W_INCH
            design_h = design_h or DEFAULT_H_INCH
    slide_w, slide_h = cap_to_pptx_slide(design_w, design_h)
    if (slide_w, slide_h) != (design_w, design_h):
        print(f"[canvas] slide capped to {slide_w:.1f}×{slide_h:.1f}\" (PPT max 56\"); "
              f"viewport stays at design size", file=sys.stderr)

    # Reference-PDF alias mode
    ref_pdf = a.reference_pdf
    if ref_pdf is None:
        sibling = a.html.parent / "poster.pdf"
        if sibling.exists():
            ref_pdf = sibling
            print(f"[fonts] auto-detected sibling reference PDF: {ref_pdf}",
                  file=sys.stderr)
    if ref_pdf and ref_pdf.exists():
        pdf_fonts = detect_pdf_fonts(ref_pdf)
        if pdf_fonts:
            html_fams = extract_font_families(a.html)
            auto_aliases = build_pdf_alias_map(html_fams, pdf_fonts)
            if auto_aliases:
                print(f"[fonts] reference PDF uses: {pdf_fonts}",
                      file=sys.stderr)
                print(f"[fonts] applying alias map to match PDF render:",
                      file=sys.stderr)
                for css_name, pdf_name in auto_aliases.items():
                    print(f"          {css_name!r} → {pdf_name!r}",
                          file=sys.stderr)
                FONT_ALIASES.update(auto_aliases)
                for pdf_name in set(auto_aliases.values()):
                    ensure_font_installed_simple(pdf_name)
                write_runtime_aliases(auto_aliases)
                import atexit
                atexit.register(clear_runtime_aliases)

    if not a.no_auto_fonts:
        print(f"[fonts] auto-checking HTML font-family declarations...",
              file=sys.stderr)
        for fam in extract_font_families(a.html):
            target = FONT_ALIASES.get(fam, fam)
            ensure_font_installed_simple(target)

    print(f"[extract] DOM via playwright...", file=sys.stderr)
    dom = extract_dom(a.html, viewport_w=int(design_w * 96), viewport_h=int(design_h * 96))
    dom_cache = a.outdir / f"{a.name}_dom.json"
    dom_cache.write_text(json.dumps(dom))
    n_blocks = len(dom["text_blocks"])
    print(f"          {n_blocks} text blocks, body {dom['body_w']}×{dom['body_h']}px",
          file=sys.stderr)

    pptx = a.outdir / f"{a.name}.pptx"
    png = a.outdir / f"{a.name}.png"
    print(f"[build] PPTX → {pptx.name}", file=sys.stderr)
    build_pptx(dom, pptx, width_inch=slide_w, height_inch=slide_h, corrections={},
               match_wrap=a.match_wrap)
    print(f"[render] PPTX → PNG via soffice → {png.name}", file=sys.stderr)
    render_pptx_to_png(pptx, png, dpi=96)

    html_print = a.outdir / f"{a.name}_html_print.png"
    html_browser = a.outdir / f"{a.name}_html_browser.png"
    print(f"[compare] HTML print viewport "
          f"({int(design_w*96)}×{int(design_h*96)}) → {html_print.name}",
          file=sys.stderr)
    render_html_to_png(a.html, html_print, int(design_w * 96), int(design_h * 96),
                       full_page=False)
    print(f"[compare] HTML browser viewport (1920×1080, fullPage) → {html_browser.name}",
          file=sys.stderr)
    render_html_to_png(a.html, html_browser, 1920, 1080, full_page=True)

    print(f"\n[done] outputs in {a.outdir}", file=sys.stderr)
    print(f"  pptx          : {pptx.name}", file=sys.stderr)
    print(f"  pptx-render   : {png.name}", file=sys.stderr)
    print(f"  html-print    : {html_print.name}", file=sys.stderr)
    print(f"  html-browser  : {html_browser.name}", file=sys.stderr)

    # ── Optional vision-audit fidelity check ───────────────────────────
    # Drop-in replacement for the removed PIL-based L2 loop. Doesnt mutate
    # the PPT — just reports what fidelity issues remain. Code fixes happen
    # in html_to_pptx.py based on these reports (3-round revision = build →
    # audit → fix code → rebuild → audit → fix → audit; iterate until issues
    # plateau). Comparing successive audit JSONs is the dev signal.
    if a.vision_audit:
        # Auth precheck — silently skip when neither path is configured
        # (offline / CI / no key). Print a one-line hint so the user knows
        # WHY it didn't run. This makes default-on safe.
        has_token = bool(os.environ.get("ANTHROPIC_AUTH_TOKEN") or
                         os.environ.get("ANTHROPIC_API_KEY"))
        has_base = bool(os.environ.get("ANTHROPIC_BASE_URL"))
        if not has_token:
            print(f"\n[vision-audit] skipped: set ANTHROPIC_AUTH_TOKEN "
                  f"(or ANTHROPIC_API_KEY) to enable. Pass --no-vision-audit "
                  f"to silence this message.", file=sys.stderr)
        else:
            try:
                from vision_audit import audit  # type: ignore
            except ImportError as e:
                print(f"[vision-audit] vision_audit.py import failed: {e}", file=sys.stderr)
            else:
                audit_path = a.outdir / f"{a.name}_audit.json"
                prev_n = None
                if audit_path.exists():
                    try:
                        prev = json.loads(audit_path.read_text())
                        prev_n = prev.get("n_issues")
                        # Stash prior for delta computation
                        audit_path.rename(a.outdir / f"{a.name}_audit_prev.json")
                    except Exception:
                        pass
                auth_mode = "base-url" if has_base else "direct"
                print(f"\n[vision-audit] calling Claude vision "
                      f"({a.vision_model}, auth={auth_mode})...",
                      file=sys.stderr)
                try:
                    report = audit(html_print, png, dom, model=a.vision_model)
                    audit_path.write_text(json.dumps(report, indent=2))
                    n = report["n_issues"]
                    sev = report.get("by_severity", {})
                    delta = f"  ({n - prev_n:+d} vs previous)" if prev_n is not None else ""
                    print(f"[vision-audit] {n} issues  "
                          f"high={sev.get('high',0)} med={sev.get('medium',0)} "
                          f"low={sev.get('low',0)}{delta}  → {audit_path.name}",
                          file=sys.stderr)
                    for cat, ncount in sorted(report["by_category"].items(), key=lambda x: -x[1]):
                        print(f"   {ncount:>2d}× {cat}", file=sys.stderr)
                except Exception as e:
                    print(f"[vision-audit] FAILED ({type(e).__name__}): {e}",
                          file=sys.stderr)
                    print(f"[vision-audit] pass --no-vision-audit to disable",
                          file=sys.stderr)


if __name__ == "__main__":
    main()
