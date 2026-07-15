#!/usr/bin/env python3
"""
column_pack -- pre-fill column-packing feasibility check.

Run this ONCE after figures are placed and the initial poster is rendered, but
BEFORE the staged-fill loop. For each outer column it computes:

    slack = columnHeight - Sum(figure floor heights) - Sum(text minimum heights)

A figure's *floor* is the smallest height at which it still clears the 90% gate:
``floor = 0.90 * sectionWidth / AR``. A **negative slack** means the figures'
rigid floors plus the text's minimum content already exceed the column height --
the column is INFEASIBLE: no amount of filling can make every section FULL, so
the loop will *oscillate* there (the documented figure-vs-text / mid-sub
deadlock). The fix is to RE-PACK before the loop (move a text section to a looser
column, move / swap / shrink a figure, or cut content) instead of grinding dozens
of rounds. One opus run burned ~15 min on a single negative-slack column.

Exit codes: 0 = every column fits; 3 = at least one INFEASIBLE column (re-pack
first); 2 = usage / render error.
"""
from __future__ import annotations

import os

from pathlib import Path

from . import canvas as _canvas
from . import render as _render
from . import slack as _slack
from .cli_common import eprint as _eprint, import_playwright

FIG_MIN_RATIO = float(os.environ.get("POSTER_FIG_MIN_RATIO", "0.90"))
TIGHT_FRAC = 0.10  # slack below 10% of column height = tight (likely to fight)


def compute_pack(cols):
    """Per-column packing diagnostics from raw _SLACK_JS column geometry.

    Sections are first grouped into rows by vertical overlap. Side-by-side cards
    (e.g. a ``.mid-sub`` row holding two cards at the same y) SHARE vertical
    space, so a row's height demand is the **max** of its cards, not the sum;
    stacked rows are summed. (Summing side-by-side cards over-counts the column
    and falsely flags it INFEASIBLE.)
    """
    out = []
    for c in cols:
        secs = c.get("sections", [])
        col_h = c.get("innerH") or sum(s.get("h", 0.0) for s in secs)
        fig_floor = 0.0
        n_fig = 0
        ids = []
        items = []  # per-section min-height demand + vertical extent
        for s in secs:
            ids.append(s.get("id", "?"))
            card_h = s.get("h", 0.0)
            y = s.get("y", 0.0)
            cbox = s.get("content_bbox") or {}
            f = s.get("figure")
            if f and f.get("natural_h") and f.get("rendered_h"):
                n_fig += 1
                ar = (f.get("natural_w") or 1.0) / f["natural_h"]
                sec_w = s.get("w") or cbox.get("w", 0.0)  # section width
                floor = (FIG_MIN_RATIO * sec_w / ar) if ar else 0.0
                fig_floor += floor
                sec_min = floor + max(0.0, card_h - f["rendered_h"])
            else:
                sec_min = cbox.get("h", card_h)
            items.append({"y": y, "bot": y + card_h, "min": sec_min})
        # group into rows by vertical overlap: side-by-side -> max, stacked -> sum
        rows = []
        for it in sorted(items, key=lambda x: x["y"]):
            placed = False
            for row in rows:
                overlap = min(it["bot"], row["bot"]) - max(it["y"], row["y"])
                if overlap > 0.5 * min(it["bot"] - it["y"], row["bot"] - row["y"]):
                    row["min"] = max(row["min"], it["min"])
                    row["y"] = min(row["y"], it["y"])
                    row["bot"] = max(row["bot"], it["bot"])
                    placed = True
                    break
            if not placed:
                rows.append(dict(it))
        fixed_min = sum(r["min"] for r in rows)
        slack = col_h - fixed_min
        out.append({
            "index": c.get("index"),
            "height": round(col_h, 1),
            "figures": n_fig,
            "rows": len(rows),
            "figureFloor": round(fig_floor, 1),
            "fixedMin": round(fixed_min, 1),
            "slack": round(slack, 1),
            "rigidPct": round(fig_floor / col_h * 100, 1) if col_h else 0.0,
            "sections": ids,
        })
    return out


def cmd_pack(args) -> int:
    html_path = Path(args.html).resolve()
    if not html_path.exists():
        _eprint(f"ERROR: HTML not found: {html_path}")
        return 2
    resolved = _canvas.resolve_canvas(html_path, args.canvas, label="[pack]")
    if not resolved:
        return 2
    _canvas_obj, viewport = resolved

    sync_playwright, PWTimeoutError = import_playwright()
    with sync_playwright() as p:
        browser, _ctx, page = _render.open_print_emulated_page(p, viewport)
        try:
            page.goto(html_path.as_uri(), wait_until="networkidle",
                      timeout=args.mathjax_timeout_ms)
        except PWTimeoutError:
            pass
        _render.settle_page(
            page, mathjax_timeout_ms=args.mathjax_timeout_ms,
            settle_ms=args.settle_ms,
        )
        _render.inject_class_fallback_roles(page)
        cols = page.evaluate(_slack._SLACK_JS)
        browser.close()

    if not cols:
        _eprint("ERROR: no columns found (need .columns > .col / .mid-wide).")
        return 2

    diag = compute_pack(cols)
    infeasible = []
    print("column-pack feasibility  (slack = colHeight - Σ rowMin; side-by-side cards share a row)")
    for d in diag:
        if d["slack"] < 0:
            tag = "INFEASIBLE -> will oscillate"
            infeasible.append(d)
        elif d["slack"] < TIGHT_FRAC * d["height"]:
            tag = "tight"
        else:
            tag = "ok"
        print(f"  col{d['index']}: H={d['height']:.0f}  figs={d['figures']}  "
              f"rows={d['rows']}  figFloor={d['figureFloor']:.0f}  "
              f"fixedMin={d['fixedMin']:.0f}  slack={d['slack']:+.0f}  "
              f"rigid={d['rigidPct']:.0f}%  [{tag}]  {d['sections']}")

    total = sum(d["height"] for d in diag) - sum(d["fixedMin"] for d in diag)
    if total < 0:
        print(f"  TOTAL slack = {total:+.0f}  -> content EXCEEDS canvas: must "
              f"drop an optional section or cut text (re-pack alone won't fit it; figures are immovable).")
    else:
        print(f"  TOTAL slack = {total:+.0f}  -> fits overall; re-pack the tight "
              f"column(s).")

    if infeasible:
        print("\nACTION before the fill loop -- re-pack the INFEASIBLE column(s):")
        for d in infeasible:
            print(f"  - col{d['index']} over by {-d['slack']:.0f}px: move a text "
                  f"section to a looser column, move/swap a figure to a wider "
                  f"column or half-layout, or cut content. Do this NOW, not via "
                  f"20 fill rounds.")
        return 3
    return 0
