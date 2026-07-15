#!/usr/bin/env python3
"""Vision-L2 comparison harness.
Runs all 3 vision modes (full / patch / hybrid) on the same HTML, applies
corrections, re-renders, builds a 5-pane comparison gallery.

Usage:
    python -m scripts.vision_eval_harness \\
        --html /path/poster.html \\
        --outdir /tmp/vision_eval_<name>/
"""
import argparse, json, subprocess, sys, time, os
from pathlib import Path

THIS = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS))
from html_to_pptx import build_pptx, detect_canvas_size, cap_to_pptx_slide, DEFAULT_W_INCH, DEFAULT_H_INCH
from auto_correct_loop import render_pptx_to_png, render_html_to_png
from vision_compare import compare_full, compare_patch, compare_hybrid, to_corrections_dict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--baseline-dir", type=Path, default=None,
                    help="reuse existing single-shot output (poster_dom.json, "
                         "poster_html_print.png, poster_pptx.png) from this dir")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    # Stage baseline
    if args.baseline_dir and args.baseline_dir.exists():
        print(f"[setup] reusing baseline from {args.baseline_dir}", file=sys.stderr)
        for f in ["poster_dom.json", "poster_html_print.png", "poster_pptx.png", "poster.pptx"]:
            src = args.baseline_dir / f
            if src.exists():
                (args.outdir / f).write_bytes(src.read_bytes())
    else:
        sys.exit("Need --baseline-dir for now (build baseline via auto_correct_loop first)")

    dom = json.loads((args.outdir / "poster_dom.json").read_text())
    n_blocks = len(dom["text_blocks"])
    html_png = args.outdir / "poster_html_print.png"
    baseline_pptx_png = args.outdir / "poster_pptx.png"

    # Canvas size
    design = detect_canvas_size(args.html) or (DEFAULT_W_INCH, DEFAULT_H_INCH)
    slide_w, slide_h = cap_to_pptx_slide(*design)

    results = {}
    for mode_name, fn in [("full", compare_full), ("patch", compare_patch),
                           ("hybrid", compare_hybrid)]:
        print(f"\n[{mode_name}] running vision compare...", file=sys.stderr)
        t0 = time.time()
        items = fn(html_png, baseline_pptx_png, dom, model=args.model)
        elapsed = time.time() - t0
        corr_dict = to_corrections_dict(items)
        (args.outdir / f"vision_{mode_name}_corrections.json").write_text(
            json.dumps({"items": items, "corrections": corr_dict, "elapsed_s": elapsed}, indent=2))
        print(f"[{mode_name}] {len(items)} corrections in {elapsed:.1f}s", file=sys.stderr)

        # Apply + rebuild + re-render
        pptx_out = args.outdir / f"vision_{mode_name}.pptx"
        png_out = args.outdir / f"vision_{mode_name}.png"
        build_pptx(dom, pptx_out, width_inch=slide_w, height_inch=slide_h,
                   corrections=corr_dict)
        render_pptx_to_png(pptx_out, png_out, dpi=96)
        results[mode_name] = {
            "n_corrections": len(items), "elapsed_s": round(elapsed, 1),
            "pptx": str(pptx_out), "png": str(png_out),
        }

    # Summary
    (args.outdir / "vision_eval_summary.json").write_text(json.dumps(results, indent=2))
    print(f"\n[done] summary:", file=sys.stderr)
    for m, r in results.items():
        print(f"  {m:>7s}: {r['n_corrections']} corrections, {r['elapsed_s']}s", file=sys.stderr)
    print(f"\nCompare PNGs:", file=sys.stderr)
    print(f"  truth         : {html_png}", file=sys.stderr)
    print(f"  baseline      : {baseline_pptx_png}", file=sys.stderr)
    for m, r in results.items():
        print(f"  vision-{m:<7s}: {r['png']}", file=sys.stderr)


if __name__ == "__main__":
    main()
