"""Regression test for the canvas-clamp / design-viewport split.

Caused a real production bug on 2026-06-15: when the CSS @page size
exceeds OOXML's 56-inch per-axis cap (60×36 in NeurIPS / CVPR posters),
an earlier version of the clamp logic shrank the Playwright viewport to
the slide size — so the browser rendered the page in a smaller box than
its CSS designed for, AND build_pptx's `slide_scale` ratio (`slide_w /
design_w`) collapsed to 1.0. Net effect: PPT body fonts rendered at the
full designed pt size on a smaller canvas → sections looked cramped and
text overflowed lines.

The fix: keep Playwright at the original design viewport; clamp ONLY the
PPT slide. build_pptx's existing slide_scale machinery then auto-scales
fonts / line-spacing / borders down by the same factor.

These tests pin the contract:
  • >56" canvas → slide gets clamped, viewport stays at design size,
    slide_scale != 1.0
  • <=56" canvas → no clamp, viewport == slide, slide_scale ~= 1.0
  • Aspect ratio preserved through clamp (uniform scale by tighter axis)
  • 56" cap is OOXML-spec hard, NOT an arbitrary value — bumping it
    would make python-pptx reject the slide
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import tempfile

H2P = Path(__file__).resolve().parent.parent / "scripts" / "html_to_pptx.py"
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}

EMU_PER_INCH = 914400


def _make_html(width_inch: float, height_inch: float) -> str:
    """Minimal valid poster — single 44pt body line for fast Playwright runs."""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>
  @page {{ size: {width_inch}in {height_inch}in; margin: 0; }}
  html, body {{ width: {int(width_inch*96)}px; height: {int(height_inch*96)}px;
                margin: 0; padding: 40px; font-family: sans-serif; }}
  .body-text {{ font-size: 44pt; line-height: 1.45; }}
</style>
</head><body>
  <div class="body-text">Canvas clamp regression test.</div>
</body></html>"""


def _build(html_src: str) -> tuple[Path, str]:
    """Run the CLI on the given HTML; return (pptx_path, stderr)."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="canvas_clamp_test_"))
    html_path = tmp_dir / "in.html"
    pptx_path = tmp_dir / "out.pptx"
    html_path.write_text(html_src)
    proc = subprocess.run(
        [sys.executable, str(H2P), "--html", str(html_path), "--out", str(pptx_path)],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, f"build failed:\n{proc.stderr}"
    return pptx_path, proc.stderr


def _slide_dims_inch(pptx_path: Path) -> tuple[float, float]:
    """Read slide_width / slide_height from the generated PPTX (in inches)."""
    with zipfile.ZipFile(pptx_path) as z:
        pres_xml = z.read("ppt/presentation.xml")
    root = ET.fromstring(pres_xml)
    sld_sz = root.find("p:sldSz", NS)
    cx = int(sld_sz.attrib["cx"]); cy = int(sld_sz.attrib["cy"])
    return cx / EMU_PER_INCH, cy / EMU_PER_INCH


# --- tests ----------------------------------------------------------------


def test_landscape_over_cap_keeps_design_viewport():
    """60x36 (NeurIPS / CVPR landscape) — slide clamped 60->56, viewport stays 60."""
    pptx, stderr = _build(_make_html(60.0, 36.0))
    sw, sh = _slide_dims_inch(pptx)
    # Slide axis must be at-most the OOXML cap.
    assert sw <= 56.0 + 1e-3, f"slide width {sw} > OOXML 56 cap"
    assert sh <= 56.0 + 1e-3, f"slide height {sh} > OOXML 56 cap"
    # Aspect ratio preserved within float tolerance.
    assert abs(sw / sh - 60 / 36) < 1e-3, f"aspect drift {sw/sh} vs 5:3"
    # Clamp + design-viewport split must be logged so the bug stays visible.
    assert "clamping slide" in stderr
    assert "design viewport kept at 60.0×36.0" in stderr
    # Viewport line must show 5760x3456 px (design 60*96 x 36*96), NOT 5376x3225.
    m = re.search(r"\[viewport\] (\d+)x(\d+)px", stderr)
    assert m, f"no viewport log line in:\n{stderr}"
    vw, vh = int(m.group(1)), int(m.group(2))
    assert vw == 5760, f"viewport_w {vw} != 5760 — clamp leaked into Playwright"
    assert vh == 3456, f"viewport_h {vh} != 3456 — clamp leaked into Playwright"
    # slide_scale log must show non-trivial scale (was silently 1.0 before fix).
    m = re.search(r"\[scale\] design [\d.]+\" → slide [\d.]+\" = ([\d.]+)×", stderr)
    assert m, f"no [scale] line — slide_scale machinery didn't fire:\n{stderr}"
    scale = float(m.group(1))
    assert abs(scale - 56 / 60) < 1e-3, f"expected slide_scale 56/60={56/60:.4f}, got {scale}"


def test_portrait_a0_under_cap_no_clamp():
    """A0 portrait 33.1x46.8 in fits within 56" — no clamp, no scale, no [scale] log."""
    pptx, stderr = _build(_make_html(33.1, 46.8))
    sw, sh = _slide_dims_inch(pptx)
    assert abs(sw - 33.1) < 1e-2, f"slide width drift: {sw}"
    assert abs(sh - 46.8) < 1e-2, f"slide height drift: {sh}"
    assert "clamping slide" not in stderr, "false-positive clamp under cap"
    # slide_scale auto-log only fires for scale != 1.0; absent means scale == 1.0
    assert "[scale]" not in stderr, "spurious scale log when no clamp expected"


def test_tall_canvas_clamps_by_height_axis():
    """Width 30" (fits) + height 70" (over cap) -> height-driven scale, aspect preserved."""
    pptx, stderr = _build(_make_html(30.0, 70.0))
    sw, sh = _slide_dims_inch(pptx)
    assert sh <= 56.0 + 1e-3, f"slide height {sh} > OOXML 56 cap"
    # tighter axis is height -> scale = 56/70 = 0.8
    expected_w, expected_h = 30 * 0.8, 56.0
    assert abs(sw - expected_w) < 1e-2, f"expected slide_w {expected_w}, got {sw}"
    assert abs(sh - expected_h) < 1e-2, f"expected slide_h {expected_h}, got {sh}"
    assert abs(sw / sh - 30 / 70) < 1e-3, f"aspect drift"
    assert "clamping slide 30.0×70.0" in stderr
    # Design viewport stays at 30x70 in (= 2880x6720 px @ 96 dpi)
    m = re.search(r"\[viewport\] (\d+)x(\d+)px", stderr)
    assert m
    vw, vh = int(m.group(1)), int(m.group(2))
    assert vw == 2880 and vh == 6720, f"clamp leaked into viewport: {vw}x{vh}"


if __name__ == "__main__":
    for fn in (test_landscape_over_cap_keeps_design_viewport,
               test_portrait_a0_under_cap_no_clamp,
               test_tall_canvas_clamps_by_height_axis):
        print(f"-> {fn.__name__}", flush=True)
        fn()
        print(f"  PASS")
    print("\nall canvas-clamp regression tests pass")
