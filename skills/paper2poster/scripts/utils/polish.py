"""Soft visual-polish gate — runs at Step 6.

Three gates the hard alignment gate cannot see:

  - **Gate A: figure fill floor.** Every card figure should paint at
    90-100% of its section (card) on at least ONE axis -- either width
    OR height -- so it reads as part of the section, not a narrow stamp
    marooned in a gutter. One rule for all aspect ratios: warn only when
    ``rendered_w / card_w < --fig-min-ratio`` AND
    ``rendered_h / card_h < --fig-min-ratio`` (default 0.90). A wide
    figure satisfies the floor on width; a tall figure satisfies it on
    height. Replaces the older width-only floor that forced portrait
    figures up to 90% width by trading away vertical room.
  - **Gate B: typography orphans.** ``1.18-1.30× ↑`` whose ``↑``
    wrapped alone onto its own line. Detected on elements with
    ``[class*="stat"]`` / ``[class*="num"]`` / ``.takeaway-num`` /
    ``.headline-num`` that end with a known orphan-prone glyph but
    lack ``white-space: nowrap``.
  - **Gate C: space-between fill.** ``justify-content: space-between``
    on a column with one short card produces a giant whitespace gap
    that reads as "this column ran out of things to say". Detected
    when the largest inter-card gap exceeds the column's stated
    ``row-gap`` by > 5% of column height.

Warns by default; ``--strict`` to exit non-zero. Hard-fails if the
poster has no ``[data-measure-role]`` markup at all — a polish PASS on
"0 figures, 0 columns, 0 stat elements" would be misleading.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from . import canvas as _canvas
from . import preflight as _preflight
from . import render as _render
from .cli_common import eprint as _eprint, import_playwright
from .textutil import ascii_safe

# Gate thresholds at their CLI defaults. Kept here (not just in the argparse
# `default=`) so callers without a polish arg namespace -- e.g.
# `check_poster.py slack --with-polish`, which runs the polish gates on the
# SAME rendered page instead of launching a second browser -- can reuse the
# exact same defaults via ``default_polish_args()``. The `slack` sub-parser in
# check_poster.py also points its `default=` at these constants so the two
# entry points can never drift.
DEFAULT_FIG_MIN_RATIO = float(os.environ.get("POSTER_FIG_MIN_RATIO", "0.90"))
DEFAULT_MAX_SPACE_BETWEEN_FILL = 0.05
DEFAULT_MAX_CARD_TRAILING = 0.05
DEFAULT_MAX_WIDOW_FRACTION = 0.20


# Trailing glyphs that orphan when wrapped: arrows, multiplicative
# cross, division, plus-minus, footnote markers, degree, percent.
ORPHAN_GLYPHS = "↑↓↔×÷±§¶†‡*°%"


_POLISH_JS = r"""
() => {
  // ---- 1) Figure sizing ----
  // For each card, list every <img> with rendered size, the card's
  // bounding width (the "budget"), and natural dimensions for AR.
  const figures = [];
  // Derive the painted image dimensions under `object-fit: contain`.
  // The <img>'s bounding box can be much larger than the actual painted
  // pixels (the rest is empty letterbox / pillarbox), so a naive
  // `r.width / card_w` reads OK while the eye sees a stamp marooned in
  // whitespace. Compute the true painted box from naturalAR vs boxAR
  // and use that for the fill check. Falls back to the bbox when
  // natural dims are unavailable (e.g. SVG with no intrinsic size).
  const paintedDims = (img, boxW, boxH) => {
    const nw = img.naturalWidth  || 0;
    const nh = img.naturalHeight || 0;
    if (nw <= 0 || nh <= 0 || boxW <= 0 || boxH <= 0) {
      return { w: boxW, h: boxH };
    }
    const boxAR = boxW / boxH;
    const natAR = nw / nh;
    if (natAR > boxAR) {
      return { w: boxW, h: boxW / natAR };
    }
    return { w: boxH * natAR, h: boxH };
  };
  document.querySelectorAll('[data-measure-role="card"]')
    .forEach((card, ci) => {
      const cw = card.getBoundingClientRect().width;
      card.querySelectorAll('img').forEach(img => {
        const r = img.getBoundingClientRect();
        if (r.width < 50) return;  // skip inline icons
        const painted = paintedDims(img, r.width, r.height);
        figures.push({
          card_index: ci,
          role: 'card',
          src: img.getAttribute('src') || '',
          alt: img.getAttribute('alt') || '',
          fig_layout: img.getAttribute('data-fig-layout') || '',
          rendered_w: painted.w,
          rendered_h: painted.h,
          box_w: r.width,
          box_h: r.height,
          card_w: cw,
          card_h: card.getBoundingClientRect().height,
          natural_w: img.naturalWidth || 0,
          natural_h: img.naturalHeight || 0,
        });
      });
    });
  // Hero-panel images (the main figure of a hero-layout poster) get the
  // broken-image check too -- a blank centerpiece is the worst failure
  // mode and the card-only scan used to miss it. AR sizing gates are
  // skipped for these on the Python side (they are framed as % of card
  // width, which the full-bleed hero panel doesn't have).
  document.querySelectorAll('[data-measure-role="hero"]')
    .forEach(hero => {
      const hw = hero.getBoundingClientRect().width;
      hero.querySelectorAll('img').forEach(img => {
        const r = img.getBoundingClientRect();
        if (r.width < 50) return;  // skip venue badges / inline icons
        const painted = paintedDims(img, r.width, r.height);
        figures.push({
          card_index: -1,
          role: 'hero',
          src: img.getAttribute('src') || '',
          alt: img.getAttribute('alt') || '',
          fig_layout: img.getAttribute('data-fig-layout') || '',
          rendered_w: painted.w,
          rendered_h: painted.h,
          box_w: r.width,
          box_h: r.height,
          card_w: hw,
          card_h: hero.getBoundingClientRect().height,
          natural_w: img.naturalWidth || 0,
          natural_h: img.naturalHeight || 0,
        });
      });
    });

  // ---- 2) Orphan-prone text elements ----
  const sel = '[class*="stat"], [class*="num"], .num, .takeaway-num,'
            + ' .headline-num';
  const seen = new Set();
  const orphans = [];
  document.querySelectorAll(sel).forEach(el => {
    if (seen.has(el)) return;
    seen.add(el);
    const txt = (el.innerText || '').replace(/\s+$/, '');
    if (!txt || txt.length > 80) return;
    const cs = window.getComputedStyle(el);
    orphans.push({
      tag: el.tagName.toLowerCase(),
      cls: el.className || '',
      text: txt,
      ws: cs.whiteSpace || '',
    });
  });

  // ---- 3) Space-between fill ----
  const cols = [];
  document.querySelectorAll('[data-measure-role="column"]')
    .forEach((col, ci) => {
      const cs = window.getComputedStyle(col);
      if (cs.justifyContent !== 'space-between') return;
      const colR = col.getBoundingClientRect();
      const children = Array.from(col.children).map(c => {
        const r = c.getBoundingClientRect();
        return {top: r.top, bottom: r.bottom, h: r.height};
      }).filter(c => c.h > 0);
      if (children.length < 2) return;
      const gapPx = parseFloat(cs.rowGap || cs.gap || '0') || 0;
      let maxExcess = 0;
      let pairIdx = -1;
      for (let i = 1; i < children.length; i++) {
        const actual = children[i].top - children[i - 1].bottom;
        const excess = actual - gapPx;
        if (excess > maxExcess) {
          maxExcess = excess;
          pairIdx = i;
        }
      }
      cols.push({
        column_index: ci,
        column_h: colR.height,
        stated_gap_px: gapPx,
        max_excess_px: maxExcess,
        pair_idx: pairIdx,
      });
    });

  // ---- 4) Card trailing whitespace (single stretched card) ----
  // A card with flex:1 (or any stretch-to-fill) whose content is top-
  // packed leaves blank space below the last line. `measure` only checks
  // the card's bottom edge so it passes; Gate C only looks BETWEEN cards.
  // Skip cards that distribute space on purpose (space-* / center / end)
  // -- that is Gate C's territory or an intentional layout.
  const cards = [];
  document.querySelectorAll('[data-measure-role="card"]')
    .forEach((card, ci) => {
      const cs = window.getComputedStyle(card);
      const jc = cs.justifyContent || '';
      if (jc.indexOf('space') !== -1 || jc === 'center'
          || jc === 'end' || jc === 'flex-end') return;
      const cr = card.getBoundingClientRect();
      if (cr.height <= 0) return;
      const padB = parseFloat(cs.paddingBottom) || 0;
      const padT = parseFloat(cs.paddingTop) || 0;
      const borderB = parseFloat(cs.borderBottomWidth) || 0;

      // Is `node` inside an absolutely/fixed-positioned subtree within the
      // card? A corner badge / QR / watermark sits at the card bottom but
      // is NOT the normal-flow content bottom -- counting it would mask a
      // top-packed void above it (false negative). Walk parents to card.
      const inAbs = (node) => {
        let el = node.nodeType === 1 ? node : node.parentElement;
        while (el && el !== card) {
          const pos = window.getComputedStyle(el).position;
          if (pos === 'absolute' || pos === 'fixed') return true;
          el = el.parentElement;
        }
        return false;
      };

      // Bottom-most rendered CONTENT = max over three sources (each kept
      // via `maxB`, so adding a source can only RAISE the content bottom,
      // never hide a void):
      //   (1) TEXT, via Range -- a plain-text tail that wraps onto a line
      //       BELOW an inline <span>/<b>/<code> is invisible to an element
      //       scan (its parent <p> has element children so it's skipped,
      //       and the inline leaf sits on an earlier line) -> undershoot.
      //   (2) REPLACED media (img/svg/canvas/...) -- even when it has child
      //       nodes (e.g. <svg> wrapping <path>s) and so isn't a leaf.
      //   (3) LEAF element boxes (no element children) -- re-covers a pure-
      //       CSS diagram node (an empty <div> bar/box) that carries no
      //       text and isn't replaced, which (1)+(2) alone would miss.
      // Non-leaf, non-replaced CONTAINERS are skipped: a stretched wrapper
      // box would over-measure to the card bottom and mask the void.
      let maxB = cr.top + padT;
      const bump = (r) => {
        if (r && r.height > 0 && r.bottom > maxB) maxB = r.bottom;
      };
      const walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT);
      for (let tn = walker.nextNode(); tn; tn = walker.nextNode()) {
        if (!tn.nodeValue || !tn.nodeValue.trim()) continue;
        if (inAbs(tn)) continue;
        const rng = document.createRange();
        rng.selectNodeContents(tn);
        const rects = rng.getClientRects();
        for (let i = 0; i < rects.length; i++) bump(rects[i]);
      }
      const REPLACED = /^(IMG|SVG|CANVAS|VIDEO|IFRAME|HR|OBJECT|EMBED)$/;
      card.querySelectorAll('*').forEach(el => {
        if (inAbs(el)) return;
        // tagName is upper-case for HTML, but case-preserved (lower) for
        // SVG elements -- normalise before the replaced-tag test.
        if (!REPLACED.test(el.tagName.toUpperCase()) && el.children.length) {
          return;  // a non-replaced container: skip (only leaves + media)
        }
        bump(el.getBoundingClientRect());
      });

      cards.push({
        card_index: ci,
        card_h: cr.height,
        trailing_px: (cr.bottom - padB - borderB) - maxB,
      });
    });

  // ---- 5) <br> as a direct child of a flex container ----
  // A <br> that is an in-flow child of display:flex|inline-flex is
  // blockified into a flex ITEM and stops creating a line break -- so
  // intended multi-line content (e.g. an icon + label stacked with <br>)
  // silently collapses onto one row. `measure` can't see it (card bottom
  // is unchanged); only the eye catches it. Report each offending flex
  // parent once. Even in flex-direction:column the <br> does nothing (the
  // text runs already stack as separate items); row is where it visibly
  // breaks, so we report the direction to make the fix obvious.
  const flexbr = [];
  const seenFlexBr = new Set();
  document.querySelectorAll('br').forEach(br => {
    const parent = br.parentElement;
    if (!parent || seenFlexBr.has(parent)) return;
    const cs = window.getComputedStyle(parent);
    if (cs.display === 'flex' || cs.display === 'inline-flex') {
      seenFlexBr.add(parent);
      flexbr.push({
        tag: parent.tagName.toLowerCase(),
        cls: parent.className || '',
        dir: cs.flexDirection || 'row',
      });
    }
  });

  // ---- 6) Widow lines (last line < N% of element width) ----
  // A multi-line <p> / <li> whose last line wraps to only 1-2 words
  // reads as broken typography even when the layout gates pass -- the
  // trailing word sits stranded in whitespace. Detectable via Range
  // getClientRects() which returns one rect per line; if the last
  // rect's width is a tiny fraction of the element's content width,
  // it's a widow. The fix is editorial (rephrase to fill or cut to
  // one fewer line), not algorithmic, so this only emits warnings.
  // Skip semantic blocks where a short last "line" is intentional:
  //   .callout / .conclusion / .stat-mini / .hero-label / .hero-note
  //   .arch-row / table cells / figcaption — these are display chrome
  //   sized to their content, not flowing paragraphs.
  const widows = [];
  const widowSkipSel =
    '.callout, .conclusion, .stat-mini, .hero-label, .hero-note, ' +
    '.arch-row, .arch-label, .arch-body, table, figcaption, h1, h2, h3, ' +
    '.titlebar, .venue-badge, .author-legend, .listen-btn';
  const widowSel =
    '[data-measure-role="card"] p, [data-measure-role="card"] li';
  document.querySelectorAll(widowSel).forEach(el => {
    if (el.closest(widowSkipSel)) return;
    // Skip if the element itself has no text node descendants (just
    // wraps other blocks).
    const tx = (el.innerText || '').trim();
    if (!tx) return;
    const elR = el.getBoundingClientRect();
    const cs = window.getComputedStyle(el);
    const padL = parseFloat(cs.paddingLeft) || 0;
    const padR = parseFloat(cs.paddingRight) || 0;
    const contentW = elR.width - padL - padR;
    if (contentW <= 0) return;
    // Range over element contents — one rect per visual line.
    const rng = document.createRange();
    rng.selectNodeContents(el);
    const rects = rng.getClientRects();
    if (rects.length < 2) return;  // single-line has no widow
    const last = rects[rects.length - 1];
    const frac = last.width / contentW;
    // Tail snippet for the warning message.
    const tail = tx.slice(-48);
    widows.push({
      tag: el.tagName.toLowerCase(),
      cls: el.className || '',
      n_lines: rects.length,
      last_line_fraction: frac,
      tail_text: tail,
    });
  });

  return {figures, orphans, cols, cards, flexbr, widows};
}
"""


def collect_polish_data(page) -> dict:
    """Run the two read-only polish measurement passes on an already-open,
    already-settled page and return their raw results.

    Split out of :func:`cmd_polish` so the same measurement can run on a
    SHARED slack page (``check_poster.py slack --with-polish``) instead of
    launching a second browser. Both evaluations are pure DOM geometry
    reads -- they mutate nothing -- so running them after slack's own
    measurement on the same page yields identical numbers.
    """
    injected = _render.inject_class_fallback_roles(page)
    if injected:
        print("[polish] no data-measure-role found; "
              "using class fallback (.poster/.col/.section)")
    data = page.evaluate(_POLISH_JS)
    # ---- Gate F: mid-wide structural integrity ----
    # The merged-middle layout requires Method as the only direct .section
    # child of .mid-wide, with all other sub-cards (Dataset, Key Result,
    # etc.) wrapped in .mid-sub. LLMs sometimes "fix" the layout by
    # dropping .mid-sub and putting Key Result as a direct child of
    # .mid-wide -- that makes Key Result span both middle columns
    # (the old broken-looking layout). Detect both violation modes here:
    #   - .mid-wide > .section with data-section != "method"
    #   - .mid-wide exists but no .mid-sub child
    mid_data = page.evaluate(r"""
    () => {
      const out = {wrong_direct: [], missing_midsub: false, midsub_count: -1,
                   headline_hero_missing: false, headline_present: false};
      const mw = document.querySelector('.mid-wide');
      if (mw) {
        const midsub = mw.querySelector(':scope > .mid-sub');
        // The method-driven layout replaces .mid-sub with a .method-wrap
        // holding a .msubs subsection grid — that is a valid merged-middle
        // structure, so don't flag it as "missing .mid-sub".
        const methodDriven = !!mw.querySelector('.msubs');
        if (!midsub && !methodDriven) {
          out.missing_midsub = true;
        } else if (midsub) {
          out.midsub_count = midsub.querySelectorAll(':scope > .section').length;
        }
        mw.querySelectorAll(':scope > .section').forEach(s => {
          const ds = s.getAttribute('data-section') || '';
          if (ds !== 'method') out.wrong_direct.push(ds || '(unnamed)');
        });
      }
      // Headline Numbers must render as hero+supporting layout, NOT a
      // plain <ul>. The template ships a `.headline-hero` div with
      // `.hero-val` + `.supporting` row of `.stat-mini` tiles; the LLM
      // sometimes bypasses this and substitutes generic bullets, which
      // strips the section of its visual identity (the whole point is
      // ONE big number the eye locks onto). Also tracks whether the
      // supporting tile row is present, since the LLM sometimes adds
      // .headline-hero with only the hero parts and drops .supporting,
      // leaving a giant solo number on an otherwise-empty card.
      const hn = document.querySelector('[data-section="headline-numbers"]');
      if (hn) {
        out.headline_present = true;
        out.headline_hero_missing = !hn.querySelector('.headline-hero');
        out.headline_stat_mini_count = hn.querySelectorAll('.stat-mini').length;
      }
      return out;
    }
    """)
    return {"data": data, "mid_data": mid_data}


def default_polish_args() -> argparse.Namespace:
    """Polish gate thresholds at their CLI defaults, for callers that run the
    gates without owning a polish arg namespace (e.g. ``slack --with-polish``).
    ``strict`` is left off here; the caller sets it (the merged path inherits
    slack's own ``--strict``)."""
    return argparse.Namespace(
        fig_min_ratio=DEFAULT_FIG_MIN_RATIO,
        max_space_between_fill=DEFAULT_MAX_SPACE_BETWEEN_FILL,
        max_card_trailing=DEFAULT_MAX_CARD_TRAILING,
        max_widow_fraction=DEFAULT_MAX_WIDOW_FRACTION,
        strict=False,
    )


def cmd_polish(args: argparse.Namespace) -> int:
    pw = import_playwright()
    if pw is None:
        return 2
    sync_playwright, PWTimeoutError = pw

    html_path = Path(args.html).resolve()
    if not html_path.exists():
        _eprint(f"ERROR: HTML not found: {ascii_safe(html_path)}")
        return 2

    # Hard-fail if there's no measurement markup at all. A polish PASS
    # on "0 figures, 0 columns, 0 stat-like elements" would be silent
    # success on a file the tool can't reason about.
    role_counts = _preflight.has_required_roles_in_html(html_path)
    must_have = ("poster", "card", "column")
    missing = [r for r in must_have if role_counts.get(r, 0) == 0]
    if missing:
        _eprint(
            f"ERROR: polish requires data-measure-role markup on the "
            f"poster, columns, and cards. Missing or zero-count: "
            f"{missing}. Either add the roles or use a different tool."
        )
        return 2

    resolved = _canvas.resolve_canvas(
        html_path, args.canvas, label="[polish]"
    )
    if resolved is None:
        _eprint(
            "ERROR: could not find `@page { size: <W> <H> }` in HTML; "
            "pass `--canvas <W>x<H>in` or `--canvas 'A0 portrait'`."
        )
        return 2
    canvas, viewport = resolved

    with sync_playwright() as p:
        browser, _ctx, page = _render.open_print_emulated_page(p, viewport)
        nav_timed_out = False
        try:
            page.goto(html_path.as_uri(), wait_until="networkidle",
                      timeout=args.mathjax_timeout_ms)
        except PWTimeoutError:
            # Don't raw-traceback on a hung/slow resource. Record it and
            # let settle_page surface a MathJax-specific failure first;
            # otherwise fail-fast below. polish must NOT sample a poster
            # that never finished loading -- a blocked remote image or web
            # font would otherwise sneak through as a false PASS.
            nav_timed_out = True

        settle = _render.settle_page(
            page,
            mathjax_timeout_ms=args.mathjax_timeout_ms,
            settle_ms=args.settle_ms,
        )
        fail = _render.hard_fail_on_settle_problems(
            settle, mathjax_timeout_ms=args.mathjax_timeout_ms,
        )
        if fail is not None:
            browser.close()
            _eprint(f"FAIL: {fail}")
            return 1
        if nav_timed_out:
            browser.close()
            _eprint(
                "FAIL: page did not reach network-idle within "
                f"{args.mathjax_timeout_ms} ms; refusing to polish a "
                "partially loaded poster. A blocked/slow remote resource "
                "(CDN image, web font, MathJax) is the usual cause -- "
                "inline assets, or raise --mathjax-timeout-ms."
            )
            return 1

        collected = collect_polish_data(page)
        browser.close()

    return report_polish(collected, args, html_path)


def report_polish(collected: dict, args: argparse.Namespace,
                  html_path: Path) -> int:
    """Apply the visual-polish gates (A-G) to data gathered by
    :func:`collect_polish_data` and emit warnings. Page-free, so the same
    report runs both for standalone ``polish`` and for the merged
    ``slack --with-polish`` path (which shares one rendered page)."""
    data = collected["data"]
    mid_data = collected["mid_data"]
    warns: list[str] = []

    # ---- Gate A: figure sizing by AR ----
    for f in data.get("figures", []):
        rw = float(f["rendered_w"])
        rh = float(f["rendered_h"])
        cw = float(f["card_w"])
        ch = float(f.get("card_h", 0) or 0)
        nw = float(f["natural_w"])
        nh = float(f["natural_h"])
        role = f.get("role", "card")
        src_l = str(f["src"]).lower()
        # A vector image (SVG) can legitimately report zero natural size
        # while rendering fine, so never flag it broken. Match the path
        # extension (after stripping any ?query / #fragment) plus inline
        # SVG data URIs. Imperfect: an SVG behind an extensionless URL
        # still slips through; an `img.decode()`-based JS probe would be
        # exact. Covers both card and hero <img> (see _POLISH_JS).
        src_path = src_l.split("?", 1)[0].split("#", 1)[0]
        is_svg = (
            src_path.endswith((".svg", ".svgz"))
            or src_l.startswith("data:image/svg")
        )
        if (nw <= 0 or nh <= 0) and not is_svg:
            warns.append(
                f"FIG/BROKEN: '{ascii_safe(f['src'])}' has zero natural "
                "size -- the image failed to load (missing file, 404, or "
                "an unreachable remote URL); it will be blank in print."
            )
            continue
        # Hero figures get the broken-image check above, but the AR sizing
        # gates below are framed as "% of card width" and don't apply to
        # the full-bleed hero panel. Skip them.
        if role == "hero":
            continue
        # Author opt-out for a DELIBERATE image-left/text-right card: a
        # wide figure that shares its card width with a meaningful text
        # column is sized below the AR thresholds on purpose. Marking the
        # <img> with `data-fig-layout="beside-text"` records that intent
        # in the markup -- so a later edit (human or agent) reads "this is
        # intentionally beside text" and leaves the layout alone instead
        # of widening the figure to silence the warning. It skips only the
        # AR width gates below; the FIG/BROKEN check above still applies
        # (a blank image is a bug regardless of layout). The gate stays
        # strict on the accidental case: a lone wide figure shrunk into a
        # gray margin has no such attribute and still warns.
        #
        # HOWEVER — the opt-out is dangerous if an LLM-driven fill loop
        # reaches for it as a "silence the warning" lever instead of
        # actually fixing the figure size. Before honouring the opt-out,
        # apply a pathology guard: if the image is rendering at less than
        # 20% of card on BOTH width AND height, no human ever intended
        # that — it's a tiny stamp, period. Emit FIG/BROKEN (the harder
        # error variant) rather than the soft FIG/NARROW so it bites even
        # when polish runs in soft mode, and surface the opt-out attr so
        # the reader knows to remove it.
        if str(f.get("fig_layout", "")).strip() == "beside-text":
            if cw > 0 and ch > 0 and rw > 0 and rh > 0 \
                    and (rw / cw) < 0.20 and (rh / ch) < 0.20:
                warns.append(
                    f"FIG/BROKEN: '{ascii_safe(f['src'])}' renders at "
                    f"{rw / cw * 100:.0f}% width / {rh / ch * 100:.0f}% "
                    f"height of its card despite carrying "
                    f"`data-fig-layout=\"beside-text\"`. The opt-out is "
                    f"for sized-down-but-still-meaningful figures (~50% "
                    f"width beside text), NOT for pathologically tiny "
                    f"stamps. Remove the attribute and fix the underlying "
                    f"figure sizing (see Step 7 in SKILL.md, or the "
                    f"figure cap rules in references/visual_polish.md)."
                )
            continue
        if cw <= 0 or rw <= 0 or nw <= 0 or nh <= 0:
            continue
        ar = nw / nh
        ratio = rw / cw
        # Unified fill floor: every card figure should paint at 90-100% of its
        # section on at LEAST ONE axis -- either width (rendered_w / card_w) OR
        # height (rendered_h / card_h). Note: rendered_w / rendered_h are the
        # PAINTED image dimensions (derived from naturalAR vs boxAR), not the
        # <img> bounding box. With `object-fit: contain` the box can be much
        # larger than the painted pixels -- a 3.6 AR figure box housing a 2.5
        # AR image fills only ~70% of the box width visually, even though the
        # bbox is 100%. Measuring the bbox would silently pass figures the
        # reviewer sees as marooned stamps; measuring painted dims matches
        # the eye and stays in sync with `slack`'s figure verdict. A wide figure satisfies it on width; a
        # tall figure satisfies it on height (and may sit narrow horizontally,
        # which is fine now). This replaces the older width-only floor that
        # forced portrait figures up to 70% width by trading vertical room.
        # The figure only warns when it fills neither axis to the floor -- a
        # genuinely small stamp marooned in its card. (>100% on an axis would
        # mean the image overflows its card -- a separate alignment bug the
        # hard gate catches.)
        h_ratio = (rh / ch) if ch > 0 else 0.0
        if ratio < args.fig_min_ratio and h_ratio < args.fig_min_ratio:
            shape = (
                "wide" if ar > 1.3 else "tall" if ar < 0.8 else "square"
            )
            # The Method figure has an HTML-level safety net -- the templates'
            # fit() script floors `budgetH` at 24% of canvas height for
            # Method-section figures so a wide banner still lands above the
            # 90% width threshold even when the section doesn't carry .grow.
            # If FIG/NARROW fires for what looks like a Method figure
            # ('method' in the alt or src), the floor likely regressed (the
            # `.method-body > figure { min-height: 14cqh }` rule or the
            # `MIN_METHOD_FIG_BUDGET` JS block was removed). Surface that
            # diagnosis in the warning text so the fix lands in the template,
            # not in the spec.
            looks_like_method = (
                "method" in (f.get("alt") or "").lower()
                or "method" in (f.get("src") or "").lower()
            )
            method_hint = ""
            if looks_like_method:
                method_hint = (
                    " (Method figure: check that `.method-body > figure "
                    "{ min-height: 14cqh }` and the `MIN_METHOD_FIG_BUDGET` "
                    "block in the fit() script are intact in the template; "
                    "those enforce a hard 24cqh budget floor for Method "
                    "figures and should prevent this failure.)"
                )
            warns.append(
                f"FIG/NARROW: '{ascii_safe(f['src'])}' ({shape}, "
                f"AR={ar:.2f}) at {ratio * 100:.0f}% of card width / "
                f"{h_ratio * 100:.0f}% of card height -- "
                f"figures should fill {args.fig_min_ratio * 100:.0f}-100% on "
                f"at least one axis. Widen it (raise the Method figure "
                f"max-height cap so the figure box gets more room, or drop an "
                f"image-left/text-right wrapper that is squeezing it)."
                f"{method_hint}"
            )

    # ---- Gate B: typography orphans ----
    for n in data.get("orphans", []):
        txt: str = n["text"]
        if not txt:
            continue
        last = txt[-1]
        if last not in ORPHAN_GLYPHS:
            continue
        if not re.search(r"\s", txt[:-1]):
            continue
        ws = (n["ws"] or "").lower()
        if "nowrap" in ws or "pre" in ws:
            continue
        warns.append(
            f"ORPHAN: <{ascii_safe(n['tag'])} class='{ascii_safe(n['cls'])}'> "
            f"text '{ascii_safe(txt[:48])}' ends with '{ascii_safe(last)}' "
            f"and may wrap alone. Apply `white-space: nowrap` or use &nbsp; "
            f"before the trailing glyph."
        )

    # ---- Gate C: space-between fill ----
    for c in data.get("cols", []):
        col_h = float(c["column_h"])
        excess = float(c["max_excess_px"])
        if col_h <= 0:
            continue
        fill = excess / col_h
        if fill > args.max_space_between_fill:
            warns.append(
                f"SPACE-BETWEEN: column {c['column_index']} has a "
                f"{excess:.0f} px inter-card gap "
                f"({fill * 100:.1f}% of column height, stated gap "
                f"{c['stated_gap_px']:.0f} px). Balance via "
                f"meaningful content, not justify-content. See "
                f"Gate C in SKILL.md."
            )

    # ---- Gate C (one card): trailing whitespace below the last line ----
    for c in data.get("cards", []):
        ch = float(c["card_h"])
        tr = float(c["trailing_px"])
        if ch <= 0 or tr <= 0:
            continue
        ratio = tr / ch
        if ratio > args.max_card_trailing:
            warns.append(
                f"CARD/TRAILING: card {c['card_index']} fills only "
                f"{100 - ratio * 100:.0f}% of its height -- {tr:.0f} px "
                f"({ratio * 100:.0f}%) blank below the last line. A card "
                f"stretched to align (flex:1) but padded with whitespace "
                f"clears the bottom-edge gate yet reads as unfinished. Fill "
                f"with real content, grow a figure, or shrink the canvas. "
                f"See Gate C in SKILL.md."
            )

    # ---- Gate D: <br> inside a flex container ----
    # A <br> that is a direct child of a flex container is blockified into
    # a flex item and creates NO line break, so intended multi-line text
    # collapses onto one row. Detectable only at render time (getComputed-
    # Style), which is why it lives here and not in preflight's static scan.
    for fb in data.get("flexbr", []):
        cls = str(fb.get("cls", ""))
        cls_attr = f' class="{ascii_safe(cls)}"' if cls else ""
        warns.append(
            f"LAYOUT/FLEX-BR: <{ascii_safe(fb['tag'])}{cls_attr}> is "
            f"display:flex (flex-direction:{fb['dir']}) with a direct <br> "
            f"child -- the <br> is blockified into a flex item and creates "
            f"NO line break, so intended multi-line content collapses onto "
            f"one row. Wrap each line in a <span> and use "
            f"flex-direction:column, or make the wrapper a plain block."
        )

    # ---- Gate E: Widow line ----
    # A paragraph/bullet whose last visual line wraps to a tiny fraction
    # of its content width (typically 1-2 words). Reads as broken
    # typography even when the layout gates pass. The fix is editorial:
    # rephrase the prose to add 1-2 words (push more text onto the last
    # line so it doesn't look stranded), or cut a couple of words upstream
    # so the entire text reflows into one fewer line. Either preserves
    # layout — only the wrapping shape changes.
    for w in data.get("widows", []):
        frac = float(w["last_line_fraction"])
        if frac > args.max_widow_fraction:
            continue
        cls_str = ascii_safe(str(w.get("cls", "")))[:40]
        cls_attr = f" class='{cls_str}'" if cls_str else ""
        warns.append(
            f"WIDOW: <{ascii_safe(w['tag'])}{cls_attr}> last line is only "
            f"{frac * 100:.0f}% of element width ({w['n_lines']} lines "
            f"total). Tail: '...{ascii_safe(w['tail_text'])}'. Rephrase to "
            f"add 1-2 words so the trailing line carries more weight, or "
            f"cut a couple words upstream so the text fits in one fewer "
            f"line. Layout unchanged either way."
        )

    # ---- Gate F: mid-wide structural integrity ----
    # (data gathered above via mid_data; emit warnings here)
    for ds in mid_data.get("wrong_direct", []):
        warns.append(
            f"MID/INVALID: section '{ds}' is a direct child of .mid-wide "
            f"(should be inside .mid-sub, or NOT in mid-wide at all). "
            f"This makes the section span both middle columns visually, "
            f"reproducing the old broken-looking layout. Fix: move it "
            f"into the <div class=\"mid-sub\"> wrapper. Only Method "
            f"belongs directly under .mid-wide."
        )
    if mid_data.get("missing_midsub"):
        warns.append(
            "MID/INVALID: .mid-wide exists but .mid-sub wrapper is missing. "
            "The merged-middle layout requires Method on top + .mid-sub "
            "below holding 2 sub-cards (Key Result + Dataset by default). "
            "Without .mid-sub the secondary cards span both middle columns."
        )
    midsub_n = mid_data.get("midsub_count", -1)
    if midsub_n == 0:
        warns.append(
            "MID/SUBFILL: .mid-sub exists but has 0 .section children. "
            "Fill it with at least Key Result + one of {Dataset, Headline "
            "Numbers, Ablation, a secondary figure}."
        )
    elif midsub_n == 1:
        warns.append(
            "MID/SUBFILL: .mid-sub has only 1 sub-card — the lone card "
            "visually spans both middle columns, reproducing the old "
            "broken-looking layout. Fill the second slot with one of: "
            "Headline Numbers, Ablation Study, a secondary results figure, "
            "or split the existing card into 2 sub-panes (e.g., Key Result "
            "table + Key Result chart). DO NOT relax .mid-sub's grid to "
            "auto-fit -- the empty slot is the signal that more content "
            "should live there."
        )

    # ---- Gate G: Headline Numbers hero+supporting integrity ----
    if mid_data.get("headline_present") and mid_data.get("headline_hero_missing"):
        warns.append(
            "HEADLINE/HERO: Headline Numbers section is missing the "
            "`.headline-hero` block. The template ships a hero + 3 "
            "supporting tiles layout (.hero-val + .hero-label + .hero-note "
            "+ .supporting > .stat-mini × N). When the LLM substitutes a "
            "plain <ul> of bullets, the section loses its visual identity "
            "-- the whole point is ONE big number the eye locks onto from "
            "10ft. Replace the <ul> with the template's <div class="
            "'headline-hero'> structure: pick the most impactful number as "
            "hero-val, demote the rest to .stat-mini tiles."
        )
    if (mid_data.get("headline_present")
            and not mid_data.get("headline_hero_missing")):
        smc = mid_data.get("headline_stat_mini_count", 0)
        if smc < 2:
            warns.append(
                "HEADLINE/SUPPORTING: Headline Numbers has .headline-hero "
                f"but only {smc} .stat-mini supporting tile(s). The hero "
                "is meant to anchor the eye while 2-3 .stat-mini tiles "
                "under a thin divider give SCANNABLE context (training "
                "cost, scale, params, throughput). A solo hero on an "
                "otherwise-empty card wastes the vertical real estate and "
                "leaves the section visually unbalanced. Add at least 2 "
                ".stat-mini tiles inside <div class='supporting'> -- pull "
                "secondary numbers from the spec's Additional field or "
                "from text.txt. NEVER invent values."
            )

    print(f"[polish] {ascii_safe(html_path.name)}")
    print(f"  figures checked     : {len(data.get('figures', []))}")
    print(f"  stat-like elements  : {len(data.get('orphans', []))}")
    print(f"  space-between cols  : {len(data.get('cols', []))}")
    print(f"  cards checked       : {len(data.get('cards', []))}")
    print(f"  flex/<br> parents   : {len(data.get('flexbr', []))}")
    print(f"  widow candidates    : {len(data.get('widows', []))}")
    print(f"  warnings            : {len(warns)}")
    for w in warns:
        print(f"  WARN: {w}")

    if args.strict and warns:
        _eprint("[polish] FAIL -- --strict and warnings present")
        return 1
    print("[polish] PASS" if not warns
          else "[polish] OK (warnings only)")
    return 0
