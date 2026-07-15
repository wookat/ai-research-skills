# Content Patterns Catalog

A library of CSS widgets the LLM **must** use to break up wall-of-text monotony. All poster layouts — landscape `layouts/{full,half,3col}.html` **and** portrait `layouts_portrait/{full,half}.html` — ship these classes built-in (they land in every composed `poster.html`), so just use the markup below. **This catalog applies to portrait posters exactly as it does to landscape** — a portrait poster of plain `<p>`+`<ul>` sections is the same failure mode.

> **When to read:** During Step 3 (template substitution) when filling section bodies. **Every section MUST use at least one pattern** — plain `<p>` + `<ul>` only across a whole section is the failure mode this catalog exists to prevent. Match the widget to the content's shape (see the "Shape of content it suits" column in the index).
>
> **Across the full poster:** use at least **5 distinct pattern types**. Using `.p-callout-soft` 9 times still reads as monotonous — adjacent sections should look visually different.
>
> **Per-section cap:** 2 patterns. Don't stack 4 patterns in one section — that's just a different kind of clutter.
>
> **Portrait (A0) note:** the narrow 2-column A0 body favors *vertical / compact* widgets — `p-steps`,
> `p-timeline-cards`, `arch`, `p-chips`, `p-key-stat`, `p-callout-*`, `p-banner`, `p-table`. Avoid the *wide*
> ones (`p-vs` needs width > height) unless the column is genuinely wide (a
> full-width band in `portrait_full`). The ≥5-distinct-types rule still holds — portrait is where sections most
> easily collapse to plain bullets/tables, so it needs this catalog **more**, not less.

---

## Pattern Index

| # | Pattern | Shape of content it suits | CSS class |
|---|---------|---------------------------|-----------|
| P1 | callout-primary | Single mic-drop line (max 1 per section) | `.p-callout-primary` |
| P2 | callout-soft | Sub-takeaway, "so what" line | `.p-callout-soft` |
| P3 | callout-bar | Pull-quote insight, italic | `.p-callout-bar` |
| P5 | key-stat | One number defines the section | `.p-key-stat` |
| P6 | stat-strip | 3–5 supporting metrics side-by-side | `.p-stat-strip` |
| P7 | vs (compare) | Theirs vs Ours / Before vs After — **wide-and-short only** (width > height); ≤ ~14 words per side | `.p-vs` |
| P8 | numbered-steps | Pipeline, recipe, "how it works" | `.p-steps` |
| P10 | chips | Tag cloud: datasets, baselines, taxonomy | `.p-chips` |
| P12 | highlight-table | Compact comparison; winning row tinted; **prefer 3+ columns** | `.p-table` |
| P15 | equation | THE signature formula + caption | `.p-eq` |
| P16a-d | timeline | 4 variants — see below | `.p-timeline-{railroad,cards,pills,stepcards}` |
| P17 | banner | Full-width tag-and-text sticker (FIRST / WARNS / REQUIRES) | `.p-banner` |

(P4 — emoji-icon callout — intentionally removed. Looked clip-art-y on a printed poster.)
(P13 — pullquote — intentionally removed 2026-06-13. The `::before`/`::after` pseudo-element quote marks didn't render reliably in the html→pptx walker. For a mic-drop line use P1 callout-primary or P17 banner.)
(P14 — bento — RETIRED 2026-07-04. The "one big feature tile on the left spanning both rows + two small cells on the right" grid left the tall feature column visibly empty whenever the two small cells filled up — an unbalanced, half-empty look. For paired/contrast content use **P7 vs** (short pairs) or **P12 highlight-table**; for a feature-plus-supporting shape use **P6 stat-strip** or **P17 banner**. The `.p-bento` CSS now degrades any legacy markup to a balanced equal-cell grid so it can't reproduce the empty-big-box look, but do not reach for it in new posters.)

---

## Markup recipes

### P1 — callout-primary
```html
<div class="p-callout-primary">At 50% pruning, TFDP beats every baseline at 30% pruning — throw away half the data, still win.</div>
```

### P2 — callout-soft
```html
<div class="p-callout-soft">Shape complexity proxies sample difficulty — already in the mask.</div>
```

### P3 — callout-bar
```html
<div class="p-callout-bar">Boundary complexity is sitting right in the mask annotations — score without a model.</div>
```

### P5 — key-stat
```html
<div class="p-key-stat">
  <div class="num">1349×</div>
  <div class="label">faster sample ranking on COCO</div>
</div>
```

### P6 — stat-strip
```html
<div class="p-stat-strip">
  <div class="cell"><div class="v">+9.7</div><div class="l">mask AP<sub>50</sub> VOC 50%</div></div>
  <div class="cell"><div class="v">62.8%</div><div class="l">AP<sub>50</sub> Cityscapes</div></div>
  <div class="cell"><div class="v">3×3+</div><div class="l">datasets × backbones</div></div>
  <div class="cell"><div class="v">20-90%</div><div class="l">pruning rates tested</div></div>
</div>
```

> Constraint: `.v` content **must stay short enough not to wrap** (the CSS pins `white-space: nowrap`, but if you write `99.999×` it'll just overflow). Keep .v ≤ 6 chars; if you need more, round (`76.04%` → `76%` or `76.0%`).

### P7 — vs / compare

```html
<div class="p-vs">
  <div class="side bad"><h4>Adapted Classification Pruners</h4><p>Train Mask R-CNN per pruning rate; ~20 h on COCO.</p></div>
  <div class="sep">vs.</div>
  <div class="side good"><h4>TFDP (Ours)</h4><p>Reads mask boundary, ranks — done. 0.014 h.</p></div>
</div>
```

> **HARD RULE — wide-and-short only.** The rendered `.p-vs` block MUST be wider than tall (width > height). Each `.side` is capped at 2–3 short lines (≤ ~14 words). If a single side wraps past 3 lines, the column-wise stretch makes the block taller than the column width and the layout looks awkward. When content is longer, switch to **P12 highlight-table** (with column headers).
>
> Good fit: paired terms, theirs-vs-ours headlines, before/after states with 1–2 short clauses each.
> Bad fit: long paragraphs, deep bullet lists, side-by-side tables (those need P12).
>
> Markup notes:
> - Wrap each side's body text in `<p>` after the `<h4>` — bare text nodes directly inside `.side` are dropped by the html→pptx walker (the walker only emits text from elements whose children are ALL inline, and `<h4>` is block).
> - `.side.bad` paints a red border, `.side.good` paints an accent-2 border + soft tint. Use them for clear contrast; omit both for a neutral pair.

### P8 — numbered-steps
```html
<div class="p-steps">
  <div class="step"><strong>Compute</strong> perimeter & area of each mask → <strong>SCS</strong>.</div>
  <div class="step">Divide by SCS of a same-area circle → <strong>SI-SCS</strong>.</div>
  <div class="step">Normalize within class → <strong>CB-SCS</strong>.</div>
  <div class="step">Sum per image, rank, prune. <em>No model.</em></div>
</div>
```
> Markup notes:
> - Each `.step` is a flowing paragraph led by a circular number badge. Put the sentence directly inside `.step`; inline `<strong>`/`<em>` are fine and stay inline.
> - `.step` is block flow, **NOT** `display:flex` (fixed 2026-06-17). A flex `.step` split `::before` + every `<strong>` + each text run into separate flex items — fine in wide landscape columns, badly shattered into ragged mini-columns in narrow portrait ones (the same bug that retired `.p-iconlist`). A `<div>`-wrapped body still renders but is no longer needed.

### P9 — icon-list  (REMOVED 2026-06-11)

The `.p-iconlist` flex-bullet list was removed. Its `display: flex` rule
made `::before` (the ▸ icon), any `<strong>` element, and the trailing
text node render as 3 separate flex items — producing a table-like
3-column layout that broke wrapping and visual hierarchy. For an icon-
bullet list, use a plain `<ul><li>` — the browser's default bullet is
fine and the text wraps inline. Example:

```html
<ul>
  <li><strong>Heavy on hardware.</strong> Deep CNNs ship millions of parameters / billions of FLOPs.</li>
  <li><strong>Sparse ≠ fast.</strong> Weight pruning leaves unstructured sparsity; dense kernels ignore it.</li>
</ul>
```

### P10 — chips
```html
<div class="p-chips">
  <span>Mask R-CNN</span><span>SOLO-v2</span><span>QueryInst</span>
  <span>VOC</span><span>Cityscapes</span><span>COCO</span>
</div>
```

**Color-coding by category (REQUIRED when chips span >1 semantic group).**
A single-color chip dump (e.g. listing CIFAR-10 + DREAM + AUM all in the
same accent color) looks like an undifferentiated tag pile — the reader
can't tell which token is a *dataset*, which is a *method*, which is a
*baseline*. Two variant modifier classes are available on the chips:
- `.alt`   → uses `--callout` / `--accent-2` accent (secondary color)
- `.muted` → uses `--muted` gray (tertiary / less important)

When the chip list represents multiple categories, group them visually
by applying the variants per category. Example for a "Setup" section
listing datasets, condensation methods, and pruning baselines:

```html
<div class="p-chips">
  <!-- datasets: default accent -->
  <span>CIFAR-10</span><span>CIFAR-100</span><span>ImageNet-10</span>
  <!-- condensation methods: .alt secondary color -->
  <span class="alt">IDC</span><span class="alt">DREAM</span><span class="alt">MTT</span><span class="alt">KIP</span>
  <!-- pruning baselines: .muted gray -->
  <span class="muted">Random</span><span class="muted">SSP</span><span class="muted">AUM</span><span class="muted">Forgetting</span>
</div>
```

Single-category lists keep the default (no variant class needed).

### P11 — definition  (REMOVED 2026-06-11)

The `.p-def` term-definition list (`<dl class="p-def">`) was removed
from the catalog. The `<dl>/<dt>/<dd>` two-column layout is hard to
size predictably inside the poster grid (text on the right wraps
unpredictably, the dt accent color competes with the section heading,
and the html→pptx walker doesn't render the dt/dd layout cleanly).
For glossary-shaped content, use plain `<ul>` with `<strong>Term</strong> —
definition` per item.

### P12 — highlight-table
```html
<table class="p-table">
  <tr><th>VOC · 50% · variant</th><th>mask AP<sub>50</sub></th></tr>
  <tr><td>SCS (raw)</td><td>28.8</td></tr>
  <tr><td>+ SI-SCS only</td><td>32.4</td></tr>
  <tr><td>+ CB-SCS only</td><td>30.7</td></tr>
  <tr class="best"><td>+ SI + CB (full TFDP)</td><td>33.4</td></tr>
</table>
```

> The `tr.best` class tints + bolds the winning row. Pick exactly one.
>
> **Prefer 3+ columns.** A two-column `Method | Metric` table stretched to the
> section width leaves a wide empty gutter down the middle and reads sparse. If
> the paper reports more than one metric (accuracy AND F1, two datasets, main
> AND ablation), give the table a column per metric so it holds more and fills
> its width — e.g. `Method | VOC AP | Cityscapes AP | COCO AP`. Only fall back to
> two columns when the paper genuinely has a single headline number. Keep cells
> terse (a value, not a sentence); a dense 3-column table beats a sparse 2-column one.

### P13 — pullquote  (REMOVED 2026-06-13)

The `.p-pullquote` big-italic-centered quote widget was removed because the `::before` / `::after` pseudo-element quote marks (`content: '"'`) did not render reliably in the html→pptx walker — the pseudo-decorations got dropped or doubled in PowerPoint output, and even when they rendered, they collided with the text on cross-platform Office. For a mic-drop line use P1 (callout-primary) or P17 (banner) instead.

### P14 — bento  (RETIRED 2026-07-04)

The `.p-bento` "one big feature tile (left, spanning both rows) + two small
cells (right)" grid was retired: whenever the two small cells filled with
content they grew tall, but the big feature tile stayed at its own content
height, leaving the tall left column visibly half-empty (an unbalanced look).
Replacements by content shape:
- paired / contrast (theirs vs ours, before/after) → **P7 vs** (short pairs) or **P12 highlight-table**
- one feature idea + supporting facts → **P6 stat-strip**, **P17 banner**, or plain `<p>` + `<ul>`

The CSS still ships as a safety fallback (it degrades any legacy `.p-bento`
markup to a balanced equal-cell grid), but do not author new `.p-bento` blocks.

### P15 — equation
```html
<div class="p-eq">
  SCS(m) = perimeter(m) / area(m)
  <span class="where">where m is an instance mask; high SCS ⇒ harder sample</span>
</div>
```

### P16 — timeline (4 variants)

Same content shape (a 3–5 step pipeline), four visual treatments — pick whichever fits the section's tone.

#### P16a — `.p-timeline-railroad` (continuous track, labels below)
```html
<div class="p-timeline-railroad">
  <div class="track"></div>
  <div class="nodes">
    <div class="step"><span class="node">1</span><span class="label">Read masks</span><span class="sub">per-instance</span></div>
    <div class="step"><span class="node">2</span><span class="label">Compute SCS</span><span class="sub">perimeter ÷ area</span></div>
    <div class="step"><span class="node">3</span><span class="label">Normalize</span><span class="sub">SI-SCS, CB-SCS</span></div>
    <div class="step"><span class="node">4</span><span class="label">Rank & prune</span><span class="sub">drop low-scoring</span></div>
  </div>
</div>
```
Best for: infographic-style method overviews where each step gets a one-word title + tiny caption.

#### P16b — `.p-timeline-cards` (tinted cards + chevron)
```html
<div class="p-timeline-cards">
  <div class="card"><div class="n">1</div><div class="l">Read masks</div><div class="s">per-instance</div></div>
  <div class="arrow">›</div>
  <div class="card"><div class="n">2</div><div class="l">Compute SCS</div><div class="s">perimeter ÷ area</div></div>
  <div class="arrow">›</div>
  <div class="card"><div class="n">3</div><div class="l">Normalize</div><div class="s">SI-SCS, CB-SCS</div></div>
  <div class="arrow">›</div>
  <div class="card"><div class="n">4</div><div class="l">Rank & prune</div><div class="s">drop low-scoring</div></div>
</div>
```
Best for: equal-weight discrete steps with short titles.

#### P16c — `.p-timeline-pills` (badges on a horizontal rail)
```html
<div class="p-timeline-pills">
  <div class="rail"></div>
  <div class="pills">
    <div class="pill"><span class="badge">Read masks</span><span class="l">per-instance</span></div>
    <div class="pill"><span class="badge">Compute SCS</span><span class="l">perimeter ÷ area</span></div>
    <div class="pill"><span class="badge">Normalize</span><span class="l">scale + class balance</span></div>
    <div class="pill"><span class="badge">Rank & prune</span><span class="l">drop the easy ones</span></div>
  </div>
</div>
```
Best for: cleanest "modern marketing" look. Step name lives inside the pill (no number).

#### P16d — `.p-timeline-stepcards` (numbered card + chevron, one tight row)
```html
<div class="p-timeline-stepcards">
  <div class="step"><div class="n">1</div><div class="l">Read masks</div></div>
  <div class="gap">›</div>
  <div class="step"><div class="n">2</div><div class="l">Compute SCS</div></div>
  <div class="gap">›</div>
  <div class="step"><div class="n">3</div><div class="l">Normalize</div></div>
  <div class="gap">›</div>
  <div class="step"><div class="n">4</div><div class="l">Rank & prune</div></div>
</div>
```
Best for: densest, fits a narrower row. No sub-captions.

### P17 — banner
```html
<div class="p-banner">
  <div class="tag">First</div>
  <div>The first dataset pruning method for instance segmentation that does not need to train a model.</div>
</div>
```
Tag examples: `First`, `Warns`, `Requires`, `Note`, `Try it`.

---

## Sizing notes

All pattern CSS uses `em`/`%` units, so widgets inherit the surrounding section's `font-size`. A pattern dropped in a `.section` with `font-size: 22pt` will scale proportionally vs. the same pattern in a `.section` with `font-size: 16pt`. No hardcoded `pt` sizes — that means the patterns survive the global `slide-scale` and per-block `font-scale` from `staged_fill`.

## Section-by-section recipe guide

A rough starting map for which patterns fit which section types. Not a rule — feel free to deviate when content demands.

| Section | Recommended | Avoid |
|---------|-------------|-------|
| Problem | P3 (pull-quote), P17 (banner if there's a "first"), or plain `<ul>` | P5 (key-stat — save for results) |
| Motivation | P3 (pull-quote), P7 (vs — short paired terms, wide-and-short only) | P12 (table) |
| Method | P8 (numbered steps), P16 (timeline), P15 (equation if 1 signature formula) | — |
| Key Results | P5 (key-stat), P6 (stat-strip), P12 (table, prefer 3+ cols) | — |
| Headline Numbers | already uses `.headline-hero` (a custom variant of P5+P6); leave it | — |
| Ablation Study | P12 (table with `tr.best`), P7 (vs — for a single before/after headline) | — |
| Takeaway | P1 (callout-primary) for the mic-drop, P17 (banner) | P12 (table) |
| Contribution (optional) | P10 (chips), or plain `<ol>` for numbered items | — |
| Dataset / Benchmark (optional) | P10 (chips for dataset names), P6 (stat-strip) | — |

## Don't do this

- **Three of the same pattern in a row.** If Method, Key Results, and Takeaway all use P1 callout-primary, the poster looks like a Q1-OKR slide. Vary.
- **A pattern that exceeds the section's height.** P16 timeline needs horizontal room; in a narrow `.col` it'll overflow. Check the section's column ratio before reaching for a wide pattern.
- **Use a pattern just to fill space.** If the content is genuinely a single short paragraph, leave it as `<p>` — that's also a valid visual rhythm. Mixing prose paragraphs WITH patterns is what creates rhythm.

## Maintenance

The actual CSS for all patterns lives in the `<style>` block of each layout, wrapped in a marked comment region (`/* ════ CONTENT PATTERNS ════ */`). To edit any pattern, search for that marker in `layouts/full.html` (the canonical version), edit, then mirror to the other layouts (`layouts/{half,3col}.html`, `layouts_portrait/{full,half}.html`). Changes here should be reflected in this doc.
