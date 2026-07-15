#!/usr/bin/env python3
"""Re-crop an extracted figure PNG in place, with a safety backup.

The figure extractor (extract_pdf.py) is heuristic and usually right, but a few
failure modes slip through: a uniform white margin that makes the figure paint
as a tiny stamp in the article, an orphaned caption strip or page-footer line
left inside the image, or a neighboring sub-figure bleeding in from the side.
This script is the corrective tool the figure-review step reaches for after it
has *looked* at a figure and named a specific defect.

Two modes, matched to the two defect classes:

  autotrim  — strip uniform near-white border margins. Use when the figure
              content is correct but floats in whitespace. Safe and reversible;
              it only ever removes border rows/cols that are within `--tol` of
              white, so it cannot eat into real content.

  box       — crop to an explicit pixel rectangle. Use when there is *content*
              to cut: an orphaned caption line, a bled-in neighbor panel, a
              footer/page number. You pass the box you read off the image.

  decaption — auto-detect and strip a baked-in caption band along the BOTTOM of
              the figure. The extractor's figure bbox often over-reaches into the
              paper's own "Figure N: ..." caption text. In the article that baked-in
              English caption strip then sits right above the Chinese <caption> the
              DOCX places under the figure — two captions stacked, the English one
              often half-clipped and ugly. This mode finds a short text band
              separated from the figure content by a clear horizontal whitespace
              gap and (with --apply) cuts it off. Report-only by default — pass
              --apply to crop.

The first three modes write `<file>.bak` (once — re-runs don't clobber the original) and,
if a figures.json is found alongside the image, update that entry's width/height
so downstream layout math stays consistent. Print the before/after dimensions so
the caller can sanity-check the result without re-opening the file.

Usage:
  crop_figure.py autotrim <image.png> [--tol 8] [--pad 4]
  crop_figure.py box <image.png> --box X0 Y0 X1 Y1
  crop_figure.py decaption <image.png> [--apply]   # detect/strip bottom caption band
  crop_figure.py inspect <image.png>          # print size + border-whitespace report

Coordinates are pixels in the saved PNG (origin top-left), the same frame you
see when you open the file. Use `inspect` first if you need the dimensions.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def _load(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def _backup(path: Path) -> None:
    """Write <file>.bak once, preserving the very first original."""
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        bak.write_bytes(path.read_bytes())


def _update_manifest(path: Path, w: int, h: int) -> bool:
    """If a sibling figures.json references this image, update its w/h.

    Returns True if an entry was updated. Searches the image's own directory
    and both legacy and v2 paper2assets manifest locations.
    """
    rel_names = {path.name, f"figures/{path.name}", f"assets/figures/{path.name}", str(path)}
    candidates = (
        path.parent / "figures.json",
        path.parent.parent / "figures.json",
        path.parent.parent / "meta" / "figures.json",
    )
    for cand in candidates:
        if not cand.exists():
            continue
        try:
            data = json.loads(cand.read_text())
        except Exception:
            continue
        changed = False
        for entry in data if isinstance(data, list) else []:
            f = entry.get("file", "")
            if f in rel_names or Path(f).name == path.name:
                entry["width"], entry["height"] = w, h
                changed = True
        if changed:
            cand.write_text(json.dumps(data, indent=2))
            return True
    return False


def _whitespace_report(arr: np.ndarray, tol: int):
    """Return how many border rows/cols (top, bottom, left, right) are near-white."""
    near_white = (arr >= 255 - tol).all(axis=2)  # H x W bool
    h, w = near_white.shape

    def count_leading(mask_1d):
        c = 0
        for v in mask_1d:
            if v:
                c += 1
            else:
                break
        return c

    row_white = near_white.all(axis=1)  # each row fully white?
    col_white = near_white.all(axis=0)
    top = count_leading(row_white)
    bottom = count_leading(row_white[::-1])
    left = count_leading(col_white)
    right = count_leading(col_white[::-1])
    return top, bottom, left, right


def cmd_inspect(path: Path, tol: int) -> int:
    img = _load(path)
    arr = np.asarray(img)
    h, w = arr.shape[:2]
    top, bottom, left, right = _whitespace_report(arr, tol)
    print(f"{path.name}: {w}x{h} px")
    print(f"  near-white border (tol={tol}): "
          f"top={top} bottom={bottom} left={left} right={right}")
    total_margin = top + bottom + left + right
    if total_margin == 0:
        print("  no trimmable border whitespace — crop looks tight")
    else:
        print(f"  autotrim would remove ~{top+bottom}px vertical, "
              f"{left+right}px horizontal")
    return 0


def cmd_autotrim(path: Path, tol: int, pad: int) -> int:
    img = _load(path)
    arr = np.asarray(img)
    h, w = arr.shape[:2]
    top, bottom, left, right = _whitespace_report(arr, tol)
    if top + bottom + left + right == 0:
        print(f"{path.name}: no border whitespace to trim ({w}x{h}) — left untouched")
        return 0

    x0 = max(0, left - pad)
    y0 = max(0, top - pad)
    x1 = min(w, w - right + pad)
    y1 = min(h, h - bottom + pad)
    if x1 - x0 < 8 or y1 - y0 < 8:
        print(f"{path.name}: autotrim would erase the image — refusing", file=sys.stderr)
        return 1

    _backup(path)
    cropped = img.crop((x0, y0, x1, y1))
    cropped.save(path)
    nw, nh = cropped.size
    upd = _update_manifest(path, nw, nh)
    print(f"{path.name}: autotrim {w}x{h} -> {nw}x{nh} "
          f"(removed L{left} R{right} T{top} B{bottom}, pad={pad})"
          + ("  [figures.json updated]" if upd else ""))
    return 0


def cmd_box(path: Path, box) -> int:
    img = _load(path)
    w, h = img.size
    x0, y0, x1, y1 = box
    # Clamp into bounds and sanity-check ordering.
    x0, x1 = sorted((max(0, min(x0, w)), max(0, min(x1, w))))
    y0, y1 = sorted((max(0, min(y0, h)), max(0, min(y1, h))))
    if x1 - x0 < 8 or y1 - y0 < 8:
        print(f"{path.name}: box {box} is too small after clamping — refusing",
              file=sys.stderr)
        return 1

    _backup(path)
    cropped = img.crop((x0, y0, x1, y1))
    cropped.save(path)
    nw, nh = cropped.size
    upd = _update_manifest(path, nw, nh)
    print(f"{path.name}: box crop {w}x{h} -> {nw}x{nh} "
          f"(kept x[{x0}:{x1}] y[{y0}:{y1}])"
          + ("  [figures.json updated]" if upd else ""))
    return 0


def _row_ink(arr: np.ndarray, tol: int) -> np.ndarray:
    """Per-row count of non-near-white pixels (the row's 'ink')."""
    non_white = (arr.min(axis=2) < 255 - tol)  # H x W bool
    return non_white.sum(axis=1)


def _detect_bottom_caption(arr: np.ndarray, tol: int):
    """Find a baked-in caption band along the figure's bottom edge.

    The signature we look for: the main figure content ends, then a band of
    near-blank rows (a clear horizontal gutter), then one or more short text
    bands (the 'Figure N: ...' caption, sometimes plus a page-footer line)
    before the image ends. We return the y at which to cut (keep rows [0:cut])
    plus a human-readable reason, or (None, reason) when no confident caption
    band is found.

    Approach: segment the image into vertical ink-blocks separated by blank
    gutters, take the tallest block as the figure body, and treat every block
    *below* the body that is short (caption-like) as caption/footer. Cut just
    above the topmost such trailing block. Conservative by design — it only
    fires when the trailing material is clearly shorter than the figure body,
    so a multi-panel figure or an in-figure legend is never mistaken for a
    caption.
    """
    h, w = arr.shape[:2]
    ink = _row_ink(arr, tol)
    # A row is a "gutter" (blank) row when almost nothing is drawn across it.
    # Use a LOW ABSOLUTE cutoff, not a fraction of the figure's own peak density:
    # a caption line spans most of the width and so carries a lot of ink even when
    # it renders faint (e.g. a 2px sliver at 12-16% coverage), whereas the margin
    # between the figure body and its caption is genuinely white (~0 ink). A
    # density-relative threshold scales with the figure and silently swallows a
    # faint caption on a low-density plot (the bug this replaces). The small
    # width-proportional term lets a faintly speckled gutter (stray anti-aliased
    # dots) still count as blank without ever masking a real text line.
    blank_thresh = max(3, int(0.02 * w))
    blank = ink <= blank_thresh

    gap_run_needed = max(6, int(0.012 * h))  # blank-row run that counts as a gutter

    # Segment into [start, end] ink-blocks separated by gutters of >= gap_run_needed.
    blocks = []
    y = 0
    while y < h:
        if blank[y]:
            y += 1
            continue
        start = y
        run = 0
        while y < h:
            if blank[y]:
                run += 1
                if run >= gap_run_needed:
                    break
            else:
                run = 0
            y += 1
        end = y - run  # last ink row of this block
        blocks.append((start, end))
    if len(blocks) < 2:
        return None, "single ink block — no caption band to separate"

    # Figure body = the tallest block.
    heights = [e - s + 1 for s, e in blocks]
    body_idx = max(range(len(blocks)), key=lambda i: heights[i])
    body_h = heights[body_idx]
    trailing = blocks[body_idx + 1:]
    if not trailing:
        return None, "no ink blocks below the figure body — bottom is clean"

    # High-precision guardrails. We would rather miss a caption (the agent still
    # eyeballs the figure in Step 5.6) than amputate real figure content, so we
    # only fire when the trailing material is unmistakably a caption:
    #   - the body is the dominant block (a real figure, not a stack of thin
    #     chart strips that got mis-segmented into many small blocks);
    #   - there are at most 3 trailing bands (a caption is 1-3 text lines);
    #   - the trailing bands are collectively thin vs the body and the image.
    # On any of these failing we leave the image untouched and say why.
    total_trailing = sum(heights[body_idx + 1:])
    if body_h < 0.40 * h:
        return None, (f"tallest block is only {body_h / h:.0%} of height — figure looks "
                      f"like stacked strips (e.g. a chart), not figure+caption (left intact)")
    if len(trailing) > 3:
        return None, (f"{len(trailing)} blocks below the body — too many to be a 1-3 line "
                      f"caption (likely chart/legend content, left intact)")
    if total_trailing > 0.15 * body_h or total_trailing > 0.15 * h:
        return None, (f"trailing blocks total {total_trailing}px "
                      f"({total_trailing / h:.0%} of height) — too tall to be a caption "
                      f"(left intact)")

    first_trailing_top = trailing[0][0]
    last_body_bottom = blocks[body_idx][1]
    # Cut at the middle of the gutter between the body and the first caption band.
    cut = (last_body_bottom + first_trailing_top) // 2 + 1
    reason = (f"{len(trailing)} trailing band(s) totalling {total_trailing}px below a "
              f"{first_trailing_top - last_body_bottom}px gutter "
              f"(figure body {body_h}px); cut at y={cut}")
    return cut, reason


def cmd_decaption(path: Path, tol: int, apply: bool) -> int:
    img = _load(path)
    arr = np.asarray(img)
    w, h = img.size
    cut, reason = _detect_bottom_caption(arr, tol)
    if cut is None:
        print(f"{path.name}: no bottom caption band detected — {reason}")
        return 0
    if not apply:
        print(f"{path.name}: DETECTED bottom caption band — {reason}")
        print(f"  re-run with --apply to crop to {w}x{cut} "
              f"(or use `box {path.name} --box 0 0 {w} <y>` for a custom cut)")
        return 0
    if cut < 8:
        print(f"{path.name}: caption cut would erase the figure — refusing",
              file=sys.stderr)
        return 1
    _backup(path)
    cropped = img.crop((0, 0, w, cut))
    cropped.save(path)
    nw, nh = cropped.size
    upd = _update_manifest(path, nw, nh)
    print(f"{path.name}: decaption {w}x{h} -> {nw}x{nh}  ({reason})"
          + ("  [figures.json updated]" if upd else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ins = sub.add_parser("inspect", help="report size + border whitespace")
    p_ins.add_argument("image")
    p_ins.add_argument("--tol", type=int, default=8)

    p_at = sub.add_parser("autotrim", help="strip near-white border margins")
    p_at.add_argument("image")
    p_at.add_argument("--tol", type=int, default=8,
                      help="how close to white (0-255) counts as background")
    p_at.add_argument("--pad", type=int, default=4,
                      help="px of margin to keep around trimmed content")

    p_box = sub.add_parser("box", help="crop to explicit pixel rectangle")
    p_box.add_argument("image")
    p_box.add_argument("--box", type=int, nargs=4, required=True,
                       metavar=("X0", "Y0", "X1", "Y1"))

    p_dc = sub.add_parser("decaption",
                          help="detect/strip a baked-in caption band at the bottom")
    p_dc.add_argument("image")
    p_dc.add_argument("--tol", type=int, default=8,
                      help="how close to white (0-255) counts as background")
    p_dc.add_argument("--apply", action="store_true",
                      help="actually crop (default: report only)")

    args = ap.parse_args()
    path = Path(args.image).resolve()
    if not path.exists():
        print(f"no such file: {path}", file=sys.stderr)
        return 1

    if args.cmd == "inspect":
        return cmd_inspect(path, args.tol)
    if args.cmd == "autotrim":
        return cmd_autotrim(path, args.tol, args.pad)
    if args.cmd == "box":
        return cmd_box(path, args.box)
    if args.cmd == "decaption":
        return cmd_decaption(path, args.tol, args.apply)
    return 1


if __name__ == "__main__":
    sys.exit(main())
