# Image Guidelines

## Where Figures Come From

For a paper PDF, don't hand-collect figures by screenshotting page regions — run the bundled extractor (Workflow step 2):

```bash
python scripts/extract_pdf.py <paper.pdf> --outdir <outdir>
```

It writes one clean PNG per figure to `<outdir>/assets/figures/` and a manifest `<outdir>/assets/meta/figures.json`. Each manifest entry carries the figure's `file`, `page`, pixel `width`/`height`, `caption_label` ("Figure 3"), and the full `caption` text. The extractor is caption-anchored: it locates each figure by its caption, glues multi-panel sub-figures (a/b/c) into a single image, and clamps the paper's own caption text off the bottom edge of the crop. Read `assets/meta/figures.json` first — the captions are the fastest signal for which figure proves which point.

User-supplied loose image files can be used directly; the extractor is specifically for pulling clean figures *out of a PDF*.

## Image Roles

Prefer paper-native or project-native visuals over decorative images.

Common roles:

- Overview or hero figure: explains the whole paper in one visual.
- Method figure: explains the proposed framework, pipeline, or algorithm.
- Mechanism figure: shows why a principle works.
- Result figure: supports the main empirical claim.
- Result table: summarizes exact numeric gains.

## Selection Rules

- Use figures that the article text can explain clearly.
- Choose fewer, stronger figures over many weak ones.
- A typical article should use 3 to 7 figures, depending on paper complexity.
- Match figures to claims using the `caption` field in `assets/meta/figures.json`, not by guessing from the filename.
- If the input paper has dense academic figures, use captions and surrounding paragraphs to guide readers.
- Do not use a figure just because it looks impressive.
- Only the figures you actually select reach the reader — so the crop-review step below applies to *those* figures, not the whole `figures/` folder.

## Crop Review

The extractor is heuristic and usually crops cleanly, but a handful of cases slip through, and a bad crop is one of the most visible defects in a finished article — far more noticeable than a slightly-off sentence. So before embedding a figure, **look at each figure you actually selected** (open it with the Read tool) and clean it with `scripts/crop_figure.py`.

You're checking for four specific defects, because these are the ones the heuristic gets wrong and each has a clean fix:

1. **Floating in whitespace** — the real content sits in the middle of a wide white margin, so in the article it paints as a small stamp marooned in empty space. The most common issue, and the safest to fix.
2. **Orphaned caption / footer text** — a strip of the paper's caption, a page number, or a footer line got left inside the image. The figure crop should contain the figure *only*; its caption is the one you write underneath it in each DOCX (Chinese in `_zh`, English in `_en`). The nastiest variant is a **thin sliver** of the paper's "Figure N: …" caption left along the bottom edge — often just 1–3px, easy to miss by eye, but it sits right above the caption you write and reads as two stacked captions (one of them half-clipped and ugly). Because it's too faint to catch reliably by eye, strip it **automatically** with `decaption` rather than trusting your eyes.
3. **A neighbor bleeding in** — the edge of an adjacent figure, or a column of body text, intrudes from one side.
4. **Chopped content** — an axis label, legend, or panel edge got cut off. This one you usually *cannot* fix by cropping (the pixels aren't there) — note it and, if it's bad enough, fall back to a different figure.

**Always crop every selected figure — pass or fail.** For each figure you selected, run two automated passes that are safe and reversible (each writes a one-time `<file>.png.bak`): first `decaption` to strip any baked-in caption sliver, then `autotrim` to strip excess border whitespace. Both are low-risk and self-guarding — `decaption` only fires when it sees an unmistakable thin caption band below a dominant figure body (it refuses on charts / multi-panel figures and prints why), and `autotrim` only removes near-white border, so it can't eat into real content. *After* those two passes, judge the figure by eye for the remaining defects; when you spot a neighbor bleed (defect 3) or a caption strip too thick for `decaption` to have caught, follow up with a targeted `box` crop.

Reach for the bundled helper rather than hand-rolling image code:

```bash
# Report exact dimensions + how much border whitespace is trimmable.
python scripts/crop_figure.py inspect <outdir>/assets/figures/<file>.png

# Defect 2 (baked-in bottom caption): auto-detect + strip the caption sliver.
# Report-only without --apply; high-precision (refuses on charts/multi-panel).
python scripts/crop_figure.py decaption <outdir>/assets/figures/<file>.png --apply

# Defect 1 (whitespace): strip uniform near-white margins. Safe + reversible.
python scripts/crop_figure.py autotrim <outdir>/assets/figures/<file>.png

# Defects 3 & thick caption strips (real content to cut): crop to an explicit
# pixel box you read off the image. Origin top-left — the frame you see in Read.
python scripts/crop_figure.py box <outdir>/assets/figures/<file>.png --box X0 Y0 X1 Y1
```

The helper writes a one-time `<file>.png.bak` (so you can always recover the original) and updates the figure's `width`/`height` in `figures.json` so it stays consistent with the image. After a `box` crop especially, re-open the file with Read to confirm you cut the right region — one judgment pass, then move on. (`decaption` and `autotrim` are low-risk enough that you can trust their printed before/after dimensions; when `decaption` reports it cut a band, glance at the result once to confirm it took only the caption.)

One subtlety: the extractor pads every crop with a small white margin on purpose, to protect axis labels and legends from being clipped. `autotrim` is conservative about this, so running it on every figure (as the always-crop rule requires) is safe — it strips genuinely excessive margins while leaving a thin protective border. Reserve the explicit `box` crop for when there's actual non-figure content to remove.

## Caption Formula

Figures are extracted and cropped **once** and shared by both articles, but each article gets its **own** caption written natively in its language — a Chinese caption in `_zh`, an English caption in `_en`. They describe the same figure and must agree on every number and label; they are not translations of each other.

Each caption should answer:

1. What is this figure?
2. What should the reader notice?
3. Why does it support the article's point?

Example shapes (same figure, one caption per language):

`图2 不同数据组织策略的分数-位置分布：Random 随机打乱，CL 单调从低到高，FO、ZIG、STR 和 SAW 则尝试在进阶、复习、平滑过渡和局部多样性之间取得平衡。`

`Figure 2. Score-versus-position profiles for each data-ordering strategy: Random shuffles freely, CL rises monotonically from easy to hard, while FO, ZIG, STR, and SAW each trade off progression, review, smooth transitions, and local diversity.`

## Figure-Text Interaction

- Before the figure: introduce the question or concept the figure answers.
- Caption: provide the shortest self-contained explanation.
- After the figure: interpret the implication, not every visual detail.

Bad pattern:

- Paragraph says method A.
- Figure B appears without context.
- Caption repeats figure title only.

Good pattern:

- Paragraph explains why method A needs visual intuition.
- Figure A appears.
- Caption tells readers what to compare.
- Next paragraph explains what the comparison means.

## AI-Generated Images

Use generated images only when:

- The paper lacks a usable overview visual.
- The user asks for a conceptual cover or schematic.
- The generated image is clearly illustrative and not pretending to be experimental data.

Never generate fake charts, fake benchmark results, fake screenshots, or fake paper figures. If generating a conceptual image, label it as a schematic or editorial illustration.

## Technical Handling

- Prefer PNG for compatibility.
- Composite transparent figures onto white backgrounds before embedding when needed.
- Keep image width within page margins.
- Embed the cropped figure (`assets/figures/<file>.png`), not the `<file>.png.bak` backup the cropper leaves behind.
- Both `blog_zh.docx` and `blog_en.docx` embed the **same** cropped PNG — extract and crop once, embed twice, caption per language.
- If the DOCX is for editors, image aesthetics matter less than readability and correct captioning.
