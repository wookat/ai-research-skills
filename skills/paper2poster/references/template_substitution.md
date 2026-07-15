# Template substitution reference

How to fill `assets/poster_full_template.html` or `assets/poster_half_template.html` with values pulled from `paper_spec.md`. Read this when you reach **Step 6 — Render the HTML poster** in `SKILL.md`.

## Template selection

The choice is driven by the Method figure's column width recorded in the spec (`{column=full}` / `{column=half}`).

| Spec figure line | Template |
|---|---|
| `{column=half}` | `assets/poster_half_template.html` — 4-column grid: Problem/Motivation/Contribution \| Method (with half-width figure) \| Key Results \| Ablation/Headline Numbers/Takeaway |
| `{column=full}` | `assets/poster_full_template.html` — 3-column grid: Problem/Motivation/Contribution \| Wide middle column with Method (full-width figure) stacked above Key Results \| Ablation/Headline Numbers/Takeaway |
| `**Figure:** none` | `assets/poster_half_template.html`, and remove the Method `<figure>` block at render time |

Both templates share placeholder tokens, audio markup, keybinding scripts, and design tokens — only the layout differs. Shell-`cp` the chosen template to `<outdir>/poster.html`, then apply substitutions with the `Edit` tool (one `{{...}}` at a time) — **never `Write` the full file inline** (the ~100 KB template overflows the per-turn output-token cap `CLAUDE_CODE_MAX_OUTPUT_TOKENS` and aborts the run). For many substitutions at once, copy the **`build_poster.py` skeleton in this folder** to `<outdir>/assets/meta/build_poster.py` (it's a build-time helper — keep it under `assets/meta/`, out of the deliverable top level), fill its `SUBS` dict, and run it against the poster with an explicit target — `python <outdir>/assets/meta/build_poster.py <outdir>/poster.html` — same indirect principle, with a depth-aware optional-section drop and a leftover-placeholder check built in. Do not edit its CSS, JS, or structural markup.

## Placeholder map

Substitute every `{{...}}` token below. (Exception: `{{FIG_MIN_RATIO}}` is injected automatically by `compose_poster.py` from the `POSTER_FIG_MIN_RATIO` env var, default `0.90` — the client `fit()` figure-fill floor; never substitute it by hand.) Tokens that don't have a clean source — drop the surrounding `<li>`/`<div>` element instead of leaving placeholder text behind.

| Token | Source |
|---|---|
| `{{TITLE}}` (twice: `<title>` + `<h1>`) | Spec title |
| `{{AUTHORS}}` | Spec authors line. **Preserve affiliation indices and role markers**: numeric superscripts for affiliation (`¹`, `²`, `³`, comma-joined when multi-affiliated: `¹,²`), `*` for first/equal-contribution authors, `†` for the corresponding author. A single name can carry all three (e.g. `Jane Luo¹*†`). Render every superscript via `<sup>…</sup>` so they read as annotations, not punctuation. Order inside the `<sup>` is: digits → `*` → `†`. |
| `{{AUTHOR_LEGEND}}` | **Single line rendered directly below the authors line: the numbered institute list in spec order, prefixed by superscript indices, and NOTHING else.** Example: `<sup>1</sup> Microsoft Research Asia &nbsp;&nbsp; <sup>2</sup> UCSD &nbsp;&nbsp; <sup>3</sup> Tsinghua University`. Wrap in `<div class="institutes-line">…</div>`. **NEVER render a corresponding-author legend.** Do not spell out `*` / `†` / `‡` markers anywhere in `poster.html` — no "Equal contribution", no "Corresponding author", no "* First author", no "†: corresponding", no parenthetical glosses, no separate legend `<div>` / `<span>` / second line. The author-line superscripts stand on their own; the convention is universally recognized at poster distance, and spelling it out wastes scarce titlebar space and visually competes with the institutes line. The corresponding author's email is exposed by `{{CONTACT}}` (prefixed `Email: `) — that is the *only* surfacing of corresponding-author info in the rendered poster. If no institute indices were extracted, leave the placeholder empty — `.author-legend:empty { display: none }` hides the whole slot. |
| `{{VENUE}}` | Prefer `metadata.json` `venue` + `year` (e.g., `NeurIPS 2017`) when both are non-empty. If only one is present, render it alone. If both are empty, fall back to the spec's `Institutes` line. |
| `{{VENUE_LINK}}` | URL the venue badge clicks through to. **Priority order:** (1) `metadata.json` `code_url` if non-empty; (2) else `metadata.json` `paper_url` (which for arXiv papers is `https://arxiv.org/pdf/<arxiv_id>`); (3) else a web-searched paper landing page found by the paper title (use the WebSearch tool: search `"<paper title>" arxiv` or `"<paper title>" filetype:pdf` and take the first credible match — arXiv, OpenReview, ACL Anthology, conference proceedings, project page). If none of the three resolves, leave the placeholder empty — the `.vb-link[href=""]` rule disables the click affordance so the badge still renders as static text. **Never fabricate a URL** — only carry one through that actually exists in `metadata.json` or that the web search returned. |
| `{{CONTACT}}` | **The corresponding author's email only.** Pull from the spec's `**Corresponding author:**` line (`Name <email>` → `email`). Render prefixed with the literal text `Email: ` (e.g., `Email: xinzhang3@microsoft.com`) — NOT a `†` dagger (reads as a footnote marker and visually competes with the author-line `†`) and NOT an emoji (renders inconsistently across print/PDF). If the spec has no corresponding-author line, fall back to `metadata.json` `emails[0]`. If neither resolves, leave empty — the `.contact:empty { display: none }` rule hides the slot. **Never invent an email, and never dump the full `emails[]` array** — only the one corresponding-author address belongs here. |
| `{{LOGO_1..4}}` | Local path to each institute's official logo, in the same order as the spec's `Institutes` line. **Preferred sourcing:** run `scripts/fetch_logos.py --outdir <outdir> --from-spec <outdir>/assets/meta/paper_spec.md` (see SKILL.md Step 5.5). It opens each institute's Wikipedia page, scrapes the infobox logo/seal/wordmark, downloads to `<outdir>/assets/logos/<slug>.{png,svg}`, and prints a JSON manifest whose `path` field is exactly what to drop into `{{LOGO_N}}`. **Fallback:** if a name didn't resolve, WebSearch `"<institute name> logo png"` (or `svg`), pick the official mark from the institute's own site, Wikipedia/Wikimedia Commons, or a primary brand-resources page — skip stock-photo aggregators and third-party redrawings; download into `<outdir>/assets/logos/<slug>.png` (slug = lowercased institute name with non-alphanumerics replaced by `-`). If a logo can't be found for some institute, REMOVE that `<img class="logo">` element entirely (don't leave the placeholder string in `src` — it would render as a broken-image icon). If no logos resolve at all, the `.logo-block:has(no logos)` rule auto-hides the whole right zone. **Never fabricate** a logo (e.g., a colored box with initials); omission is always safer than a wrong mark. |
| `{{QR_PAPER}}` | Local path to the FIRST QR slot, rendered into the titlebar's right zone below the institute logos. **Sourcing:** run `scripts/make_qr.py --outdir <outdir> --from-metadata <outdir>/assets/meta/metadata.json` (see SKILL.md Step 5.7). make_qr now reads ALL of `paper_url` / `project_url` / `code_url` (with the `arxiv_id` fallback for paper), **classifies each by what it points to** (Paper / Code / Project), **de-duplicates by URL** (a paper whose only link is a project page yields ONE QR, never two identical tiles), and writes up to two slots `qr/paper.png` (slot 0) + `qr/code.png` (slot 1). Drop the manifest's slot-0 `path` verbatim into `{{QR_PAPER}}`; when the manifest has no slot 0, **leave it empty** (the `.qr-block .qr:has(.qr-img[src=""])` rule hides that tile, the whole-row rule collapses the row when neither tile shows). **Do NOT hand-write the caption** — `references/fit_logos.py` stamps each tile's caption (Paper/Code/Project) from the manifest automatically. **Never fabricate a URL.** |
| `{{QR_CODE}}` | Local path to the SECOND QR slot, beside `{{QR_PAPER}}`. Filled from the make_qr manifest's slot-1 `path`, which exists ONLY when the paper has a genuinely distinct second URL (after dedup). For a one-link paper this is **empty** — same auto-hide behavior as `{{QR_PAPER}}`. The slot filename (`code.png`) is just a template slot; its caption comes from the manifest `label`, so slot 0 (`paper.png`) can legitimately read "Project" and slot 1 need not be "Code". **Never fabricate a URL.** |
| `{{PROBLEM}}` | Problem **Necessary** |
| `{{MOTIVATION_1}}`, `{{MOTIVATION_2}}` | Motivation **Necessary** + **Additional** split into 2 short bullets (≤25 words each) |
| `{{CONTRIBUTION_1..3}}` | Contribution **Necessary** + **Additional** split into ≤3 short bullets (≤20 words each). If fewer exist, remove unused `<li>` items. |
| `{{TEASER_CAPTION}}` / `{{TEASER_FIGURE}}` | Motivation figure caption + path. If spec says `**Figure:** none` for Motivation, remove the entire Motivation `<figure>` block. **A kept figure always needs a non-empty one-line `<figcaption>`** (from `captions.json`) — never leave it blank; an unlabeled figure is a defect (`preflight` warns on it). |
| `{{METHOD_1..3}}` | Method **Necessary** + **Additional** split into 3 bullets covering key stages |
| `{{METHOD_FIGURE}}` / `{{METHOD_CAPTION}}` | Method figure path + caption. If `**Figure:** none`, remove the Method `<figure>` block. **When a Method / architecture figure IS kept, `{{METHOD_CAPTION}}` must be a non-empty one-line caption** (from `captions.json`) — never leave `<figcaption>` blank; a bare, unlabeled method figure is a recurring defect (`preflight` warns on it). In `poster_full_template.html` the bullets + figure sit in a `.method-body` wrapper that auto-orients by the figure's aspect ratio (wide → stacked, tall → bullets beside figure); just fill the tokens, the layout is automatic — if Method figure is `none`, remove the inner `<figure>` and the `.method-body` collapses to plain bullets. |
| `{{DATASET_1..2}}` | Dataset / Benchmark **Necessary** + **Additional** split into 1–2 short bullets (≤22 words each). Name datasets, scale, splits, or the new benchmark the paper introduces. If just 1 bullet is warranted, remove the `{{DATASET_2}}` `<li>`. If the paper uses only standard public benchmarks without elaboration, remove the entire Dataset / Benchmark `.section` block and drop `"dataset-benchmark"` from `PLAYLIST`. |
| `{{BASELINE}}`, `{{BASELINE_NUM}}`, `{{OURS}}`, `{{OURS_NUM}}` | Strongest baseline vs. ours on the headline metric. If no clean comparison exists, replace `<table class="results">` with a `<p>` containing Key Result **Necessary**. **Prefer a 3+ column table** whenever the paper reports more than one metric (e.g. `Method | Acc | F1` or `Method | VOC | COCO`): a 2-column `Method | Metric` table stretched to the column width leaves a wide empty gutter and reads sparse. **Staged-fill may also grow this table** to 3–6 rows and add metric columns when Key Result reads `SPARSE` / `EMPTY` (see `staged_fill.md` "Key Result growth ladder") — every extra row/column must be drawn verbatim from the full results table the synthesizer captured in the spec's Key Result `Additional`. Only keep it 2-column when the paper genuinely has a single headline number. |
| `{{HEADLINE_DELTA}}` | The single most striking delta (e.g., `+14.4 pts Acc@5 over OrcaLoca`). |
| `{{KEY_RESULT_CONCLUSION}}` | One sentence (≤22 words) explaining *what the numbers mean*, pulled from Key Result **Audio script** or **Additional**. Rendered as a `.conclusion` line under the table + delta. See "Why each conclusion line matters" below. |
| `{{ABLATION_1..2}}` | Top 1 or 2 ablation findings, each ≤20 words. **Hard cap: 2.** Pick the rows with the largest delta or the most decisive design lesson. If only 1, remove the `{{ABLATION_2}}` `<li>`. If no ablations exist, remove the entire Ablation Study `.section` block. |
| `{{ABLATION_CONCLUSION}}` | One sentence (≤22 words) summarizing what the ablation rows *prove about the design*. Omit (delete `<p class="conclusion">`) if Ablation Study was removed. |
| `{{HERO_VAL}}` + `{{HERO_LABEL}}` + `{{HERO_NOTE}}` | The signature headline number — hero of the new "hero + supporting" Headline Numbers layout. **HERO_VAL** = bare number + units (`22.8%`, `93.7%`, `23.2×`); **HERO_LABEL** = ≤6-word descriptor of what it measures (`Acc · IPC10 · ImageNet-1K`); **HERO_NOTE** = optional one-line italic punchline (`2× prior SOTA`) — set to empty string if not needed. This is the number a passerby should remember from 10 ft away — pick the paper's signature result, not a runner-up. |
| `{{STAT_2_VAL..4_VAL}}` + `{{STAT_2_LBL..4_LBL}}` | Up to 3 supporting numbers (under the hero, in a single row with a thin top divider). **Value** is bare number + units (`0 GB`, `>300×`); **Label** is ≤4-word descriptor (`soft labels`, `compression`, `mAP (VOC)`). Remove unused `<div class="stat-mini">` blocks if fewer than 3. Skip the supporting row entirely (delete `.supporting`) if the paper has only one headline number. Note: `STAT_1` is gone — that slot is the hero. |
| `{{TAKEAWAY}}` | Takeaway **Necessary** |

### Why each conclusion line matters

A passerby's eye lands on the numbers first — a table cell, a `+14.4 pts` callout, two ablation bullets — and then asks "so what?". Without an answer they walk away with a fact, not a thesis. `{{KEY_RESULT_CONCLUSION}}` and `{{ABLATION_CONCLUSION}}` supply that thesis: one sentence converting numbers into a *design lesson* or *capability claim*. Treat them like figure captions for numeric content. Pull wording from the section's **Audio script** (already in conclusion-voice) rather than re-paraphrasing the bullets.

## Visual identity — theme color (code-driven, do NOT hand-edit)

The theme color is applied **automatically and deterministically** — you do NOT pick or edit it. For landscape,
`compose_poster.py --theme random` rewrites the `:root` accent vars when it composes `poster.html`; for portrait,
run `python references/apply_theme.py <outdir>/poster.html --theme random` once after copying the monolith. Both
resolve `random` by hashing the output path (a reproducible spread across a wave), so **do not** replace the
`:root` `--accent` / `--accent-soft` / `--callout` lines by hand — that step is retired.

The chrome only (title bar, outer poster frame, card borders, `<h2>` text + underlines, Full Listen button)
picks up the theme. With the landscape **light-default header** (`--tb-bg: var(--accent-soft)`, dark title) each
theme reads as a pale-tint header + colored `<h2>` text on white cards — a light look, not a dark filled band.
The pool is **8 academic accents** (the gallery-recolor palette), each swapping `{--accent, --accent-soft}`; the
result-register `--callout` (crimson `#ae2622`) stays fixed across all themes. Single source of truth:
`references/apply_theme.py` (`THEMES`).

| Theme | `--accent` | `--accent-soft` (header tint) | Notes |
|---|---|---|---|
| blue     | `#1d3a87` | `#e8edf7` | Deep navy — neutral, formal. |
| teal     | `#0f6070` | `#e2eff1` | Deep teal — cool, modern. |
| green    | `#2d5f3e` | `#e6f0ea` | Forest green — calm, scientific. |
| burgundy | `#8f2437` | `#f6e7ea` | Deep burgundy — warm, editorial. |
| purple   | `#4b2e83` | `#ece7f4` | Royal purple. |
| rust     | `#a2521c` | `#f6ece1` | Burnt rust / ochre. |
| slate    | `#33415e` | `#e9ecf3` | Slate blue-grey — restrained. |
| plum     | `#7d2860` | `#f4e6ef` | Deep plum / magenta. |

Everything else inherits from `--accent` via CSS `var()`. To force one theme (e.g. a paper's brand color), pass
`--theme <name>` / `POSTER_THEME=<name>`; add or edit a bundle in `apply_theme.py` `THEMES`, not in the templates.

The per-section accents (Problem red, Motivation orange, etc.) are **separate** and fixed across themes — they only drive the per-section Listen button. See "Per-section accents" below.

## Per-section accents

Each `.section` carries a `data-section="..."` attribute wired to `--c-problem`, `--c-motivation`, etc. in `:root`. These bind to `--section-accent` / `--section-soft` per section and now drive **only the section's Listen button background**. The card border, `<h2>` text, and `<h2>` underline all use the theme `--accent` (one of 8 themes — see above) so the frame reads as one identity.

**Default palette** (warm-cool chord, WCAG AA on white):

| Section | Color |
|---|---|
| Problem | `#c0392b` |
| Motivation | `#d97706` |
| Contribution | `#4d7c0f` |
| Method | `#1d3a87` |
| Dataset / Benchmark | `#0369a1` |
| Key Result | `#0d9488` |
| Ablation Study | `#7c3aed` |
| Headline Numbers | `#ae2622` |
| Takeaway | `#334155` |

- **Keep `data-section` attributes intact** during substitution — they're the only mechanism wiring sections to colors.
- **Do not recolor per-paper.** The palette is a fixed rhythm across all posters this skill produces; varying it per paper hurts cross-poster recognition. The only randomness is the 1-in-8 theme on the chrome.
- If a paper omits an optional section, remove the whole `.section` block — no color cleanup needed.
- **Paper-specific custom sections** (Failure Modes, Task Formulation, Qualitative Results, etc., injected by the custom-section fill method) all share **one** neutral accent `#475569` (slate). They don't get individual named colors — staying uniform keeps the canonical 9 sections recognizable across posters and signals "supplementary" at a glance.

## Audio playlist

The template's `PLAYLIST` array must match what the audio synthesizer will produce. Default:

```js
["title", "problem", "motivation", "contribution", "method", "dataset-benchmark", "key-result", "ablation-study", "takeaway"]
```

`"title"` is always first — it drives the small Title Listen button tucked into the titlebar's bottom-right corner (opposite the Full Listen button, which sits bottom-left) that plays the paper's opening narration (~80 words: title + authors + one-sentence framing). Drop `"ablation-study"` if the paper has no ablations (and you removed the section). Drop `"contribution"` if it isn't rendered. Drop `"dataset-benchmark"` if the paper just uses standard public benchmarks and the section was omitted. Do not add `"headline-numbers"` unless an mp3 exists for it.

## Vertical sizing — only the bottom section grows

Every non-bottom `.section` sizes to its own content. The `.section.grow` class (`flex: 1 1 auto`) is reserved for **the single bottom-most section in each column**. The bundled templates already follow this rule.

Two things to watch when substituting:

1. **If you remove the bottom-most section** (e.g., Contribution is dropped), move `grow` onto the new bottom section so each column has exactly one growing child.
2. **Never add `grow` to a non-bottom section** to "make Method's figure bigger." The templates' fit() script already enforces a hard floor `budgetH >= 0.24 * canvasH` (~830px on 5760x3456) specifically for Method-section figures, backed by a soft `.method-body > figure { min-height: 14cqh }` CSS hint — so a wide Method figure is guaranteed to land at >=14% canvas height even when the Method section doesn't carry `.grow` and Key Results below it does. Trust the floor + the `.method-figure { max-height: 38cqh }` cap; if Method's figure still reads too small, tune the cap (see `staged_fill.md` "Method figure max-height tune"), don't reassign `.grow`.

Why: a passerby reads each column top-down. Content-sized non-bottom cards mean the eye lands on each at the density of its text and figure — no stretched whitespace. The single growing bottom card soaks up vertical slack so cards align flush with the page footer.

## Initial render = lean

The first pass of `poster.html` contains **only `Necessary` prose of the six core sections** (Problem, Motivation, Method, Key Result, Headline Numbers, Takeaway). All three canonical optional sections (Contribution, Dataset / Benchmark, Ablation Study), every `Additional` paragraph everywhere, and every paper-specific custom section (Limitations, Task Formulation, Qualitative Results, ...) are deliberately withheld. The fill loop (`staged_fill.md`) decides what to add back based on measured slack — the add-optional-section method for canonical optionals, the custom-section method for custom sections, the append-text method for `Additional` paragraphs.

- Omit Contribution, Dataset / Benchmark, and Ablation Study `.section` blocks at substitution time; drop `"contribution"` / `"dataset-benchmark"` / `"ablation-study"` from `PLAYLIST` correspondingly.
- Omit every paper-specific custom section recorded in the spec; the kebab-case ids (`failure-modes`, `task-formulation`, `qualitative-results`, `efficiency-complexity`, `training-recipe`, `scaling-behavior`, `released-artifacts`, `theoretical-analysis`) are added to `PLAYLIST` **only when** the custom-section fill method injects the section.
- Drop all `{{CONTRIBUTION_*}}` / `{{DATASET_*}}` / `{{ABLATION_*}}` placeholders so they never appear as unsubstituted tokens.
- **Exception — first-class dataset/benchmark.** If the paper *introduces* a new dataset or benchmark as a primary contribution, render Dataset / Benchmark in the lean initial pass (treat it like Method). Keep `"dataset-benchmark"` in `PLAYLIST`.
- For the six core sections, render only `Necessary`. No `Additional`, no continuation bullets, no callouts derived from `Additional`.
- The spec keeps everything — it's the source of truth for downstream TTS and future renders. The lean initial render is purely a `poster.html` concern.
- **`.mid-sub` slot — prefer a figure over a content-light text card (anti-mirror).** When the fill loop later adds Dataset / Benchmark into the `.mid-wide` block's `.mid-sub` (merged middle column) opposite a content-heavy Key Results, and the paper uses only **standard public benchmarks** (so the Dataset card is intrinsically short), put the **secondary-results figure** in that slot instead of a text card. A figure auto-fills its box, so the two `.mid-sub` siblings cannot mirror-oscillate (`SPARSE ⟺ SPILLAGE`) — this prevents the structural deadlock that `staged_fill.md` rule 4 otherwise has to break mid-loop (it cost a real opus run ~20 rounds).

## No fabrication

Every stat, delta, and table cell must trace back to the spec. If unsupported, omit the element rather than guessing.

## Reading `metadata.json`

`extract_pdf.py` writes `<outdir>/assets/meta/metadata.json` with cover-page fields: `{venue, year, emails, code_url, project_url, paper_url, arxiv_id, doi}`. Read it during template substitution and use it as follows:

- **`{{VENUE}}`** — `"<venue> <year>"` if both present (e.g., `NeurIPS 2017`); else whichever is present; else fall back to the spec's `Institutes`.
- **`{{VENUE_LINK}}`** — URL the venue badge clicks through to. Priority: `code_url` → `paper_url` (arXiv → `https://arxiv.org/pdf/<arxiv_id>`) → web-search by paper title (WebSearch the title with `arxiv` or `filetype:pdf`; take the first credible match — arXiv, OpenReview, ACL Anthology, conference proceedings, project page). If nothing resolves, leave empty — `.vb-link[href=""]` disables the click affordance. **Never fabricate.**
- **`{{CONTACT}}`** — **corresponding author's email only**, prefixed with the literal text `Email: ` (e.g., `Email: xinzhang3@microsoft.com`). Source from the spec's `**Corresponding author:**` line. Fall back to `metadata.json` `emails[0]` (un-prefixed) only when the spec doesn't carry a corresponding author. Empty → hidden by the `.contact:empty` rule.
- **`{{LOGO_1..6}}`** — institute logos shown in the titlebar's right zone, top row (headers expose six slots). Fill ONE slot per institute logo; leave unused slots `""`. Source from the spec's `Institutes` line, NOT `metadata.json` (which doesn't carry affiliations). **Preferred:** run `scripts/fetch_logos.py --outdir <outdir> --from-spec <outdir>/assets/meta/paper_spec.md` (paper2assets Step 6); it scrapes each institute's Wikipedia infobox, writes `<outdir>/assets/logos/<slug>.{png,svg}`, and prints a `"missing"` list of institutes that got no logo. **Mandatory fallback:** for every institute in `"missing"`, `WebSearch` its official logo and download it via `scripts/fetch_logos.py --outdir <outdir> --add-logo "<Institute>=<image URL>"` (autotrims + slugs like the Wikimedia path). **You do NOT have to place all logos by hand:** `fit_logos.py` (Step 5.9) AUTO-COMPLETES the header with EVERY logo file in `assets/logos/` — so even if there are more institutes than slots (8 institutes, 6 slots) or you under-fill, no institute is dropped. Only after a real web search fails to find a logo at all is that institute left out (its file never exists on disk). If none resolve, the whole `.logo-block` auto-hides. **Never fabricate** a mark.
- **`{{QR_PAPER}}` / `{{QR_CODE}}`** — scannable QR tiles in the titlebar's right zone, *bottom row*. Run `scripts/make_qr.py --outdir <outdir> --from-metadata <outdir>/assets/meta/metadata.json` (Step 5.7 in `SKILL.md`). make_qr **classifies** each of `paper_url` / `project_url` / `code_url` by destination (Paper / Code / Project), **de-duplicates by URL** (identical links → ONE QR, never two placeholder-looking duplicates), and writes up to two slots `qr/{paper,code}.png` with a `qr` manifest (path + `label`) into `metadata.json`. Fill `{{QR_PAPER}}` from slot 0's `path` and `{{QR_CODE}}` from slot 1's (empty when absent — the `.qr-block` CSS auto-hides missing tiles / the whole row). **Captions are set automatically** by `fit_logos.py` from the manifest `label` — never hand-write "Paper"/"Code". **Never fabricate a URL.** A slot named `paper.png` may legitimately be captioned "Project" (the caption follows the URL, not the filename). NOTE on scannability: the QR is crisp in the print `poster.pdf` and in a PNG rendered at **≥0.5× thumb-scale**; the default 0.35× eval thumbnail shrinks it below the decode threshold — deliver the PDF or a ≥0.5× PNG.
- **`code_url` / `project_url` / `paper_url`** — do **not** render the raw URL strings in the title bar. The `{{VENUE_LINK}}` placeholder on the venue badge exposes the primary link as a click-through (priority: `code_url` → `paper_url` → web-searched landing page), and `{{QR_PAPER}}` / `{{QR_CODE}}` expose the deduplicated, classified links as scannable QR tiles. When any of these URLs is non-empty AND the spec lacks a "Released Artifacts" custom section, the custom-section fill method may also inject a **Released Artifacts** custom section auto-populated with these links (see `staged_fill.md`).
- **Never fabricate.** All fields are best-effort; empty means "couldn't parse" — leave the corresponding placeholder empty rather than guessing.

## Scan-to-Read variants (`--scan` axis)

The bottom **Scan to Read** section (`data-section="scan-to-read"`, shown only with headers v1–v4) has several internal layouts, chosen at compose time by `references/compose_poster.py --scan` (SKILL.md Step 3). Pass the GROUP keyword **`dual`** only when `make_qr.py` emitted TWO QR slots (i.e. two genuinely distinct URLs survived de-duplication), else **`single`** — so a two-QR layout never lands on a one-link paper (whose three URL fields collapse to a single QR). Variants: `aside` (default — title+email left, QR right), `hero`, `contact`, `directory`, `banner`, `twin` (two labelled QR), `chips`. `fit_logos.py` stamps each tile's caption (Paper/Code/Project) from the make_qr manifest and drops any tile whose QR never resolved.

Each variant fills from **existing fields only** (no new extraction) and auto-hides anything empty:

| Token | Source |
|---|---|
| `{{QR_PAPER}}` / `{{QR_CODE}}` | the QR PNG paths (as above) — every variant keeps the `.tq` / `.qr-img` tiles. |
| `{{CONTACT}}` | corresponding-author email (as above) — used by `aside` / `contact`. |
| `{{URL_PAPER}}` / `{{URL_CODE}}` / `{{URL_PROJECT}}` | **Display-only short URL text** for the link-listing variants (`directory`, `chips`, `hero`, `banner`, `twin`). Source from `metadata.json` `paper_url` / `code_url` / `project_url`, **stripped of the scheme** for display (e.g. `https://arxiv.org/abs/2106.09711` → `arxiv.org/abs/2106.09711`). These are NOT clickable links — just text beside the QR. Leave any absent one `""`; its row / pill auto-hides. Same URLs already used by `{{VENUE_LINK}}` / `{{QR_*}}`, so no new extraction. |

When using `references/build_poster.py`, add the `URL_*` keys to its `SUBS` dict alongside `QR_PAPER` / `QR_CODE` (set each to `""` when the underlying `metadata.json` field is empty). With header v5, the section is suppressed entirely — leave all of these `""`.
