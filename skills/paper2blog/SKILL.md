---
name: paper2blog
description: Use when transforming an academic paper, arXiv/OpenReview PDF, conference paper, technical report, poster, slide deck, repository README, or related research materials into a bilingual editorial package for an editing team. Produces two articles by default — a Chinese WeChat public-account version (`blog_zh.docx`) and an English research-blog version (`blog_en.docx`). Use for drafting, revising, or packaging article copy, figure placement, captions, image prompts, and the final `.docx` deliverables.
---

# Bilingual Paper Editorial

## Purpose

Create an editorial package for an editing team from academic paper materials. By default the package has **two required deliverables**, both `.docx`:

- **`<blog_outdir>/blog_zh.docx`** — a Chinese WeChat public-account article.
- **`<blog_outdir>/blog_en.docx`** — an English research-blog article.

Both carry strong content logic, figure-text coordination, captions, and source links. They share **one** evidence map and **one** set of extracted/cropped figures — you do the paper analysis and figure prep once, then write the article twice, once per language. When a `paper2assets` package exists, use it as that shared source of truth so blog, poster, slides, and video agree on the same section claims, figures, numbers, and narration scripts. Visual polish is secondary because editors may re-layout the article.

The two versions are not a mirror translation of each other. They report the **same facts, figures, numbers, and claims**, but each is voiced for its own audience: the `_zh` version in the restrained, public-account WeChat register; the `_en` version in a neutral Western research-blog register (see `references/editorial-style.md`). Write each natively in its language rather than translating sentence-by-sentence.

The default reader is technically curious but not necessarily expert in the paper's subfield. Preserve academic accuracy while making the contribution understandable and worth reading.

Work autonomously. Read the paper, make the editorial judgment calls yourself, and deliver two finished drafts — don't stop to ask the user to confirm the hook, structure, figures, captions, or titles. The only thing you never guess is a checkable hard fact (paper/code link, DOI, affiliation, acceptance status): if it isn't in the inputs, omit it rather than inventing one. Everything else, decide and move on.

## Output Contract

Follow the shared paper2assets v2 layout. The paper2blog bundle top level holds
only deliverable files plus `manifest.json`; dependencies and build artifacts
live under a single `assets/` container:

```text
<blog_outdir>/
  blog_zh.docx
  blog_en.docx
  manifest.json
  assets/
    figures/
    meta/
      outline_zh.json
      outline_en.json
      reports/blog_qa_report.json
      previews/blog_qa_preview/
```

**Pick `<blog_outdir>` (resolve BEFORE any file writes).** The bundle directory is shared across every paper2* skill — when paper2assets, paper2blog, paper2poster, and paper2video target the same root, the blog's figures sit next to the poster's figures, the shared narration script, and any other deliverables in one self-contained package. Resolve deterministically:

1. **An explicit `<blog_outdir>` argument from the caller wins** — honor it verbatim. The defaults below only fire when no path was passed.
2. **A `paper2assets` package already exists** → reuse its folder verbatim as `<blog_outdir>`. The canonical detection signal is `<dir>/assets/meta/paper_spec.md` (the cross-skill source of truth produced by `paper2assets` Step 4); `<dir>/manifest.json` with `"layout": "v2-assets"` is a confirming hint when present. Writing into the same bundle means both `.docx` files share the existing `assets/figures/`, the QA report lands under `assets/meta/reports/`, and downstream tools reading `manifest.json` see the blog deliverables alongside everything else with no path swap.
3. **Otherwise (a bare PDF is the only input)** → default to **`<input_pdf_dir>/<pdf_stem>/`** — the directory containing the input PDF, then a subfolder named after the PDF basename (no extension). Example: `papers/8008_Ink3D_Sculpting.pdf` → `<blog_outdir> = papers/8008_Ink3D_Sculpting/`. This matches the `paper2assets` default convention, so if you invoke `paper2assets` in Workflow step 2 below it lands in the same bundle without a later path swap.

```bash
# 1. Resolve $BLOG_OUT per the rule above
if [[ -n "$blog_outdir_arg" ]]; then
  BLOG_OUT="$blog_outdir_arg"                                  # explicit caller arg wins
elif [[ -f "$paper2assets_dir/assets/meta/paper_spec.md" ]]; then
  BLOG_OUT="$paper2assets_dir"                                 # reuse the paper2assets bundle
else
  BLOG_OUT="$(dirname "$paper_pdf")/$(basename "$paper_pdf" .pdf)"
fi

# 2. Create the assets/ scaffolding under that root
BLOG_ASSETS=$BLOG_OUT/assets
BLOG_META=$BLOG_ASSETS/meta
mkdir -p "$BLOG_ASSETS/figures" "$BLOG_META/reports" "$BLOG_META/previews"
```

`manifest.json` records root-relative paths and includes `"layout": "v2-assets"`.
Legacy `final/` / `intermedia/` outputs remain readable by the QA checker for old
demos, but new runs must use the v2 bundle shape above.

## Load References

- Read `references/editorial-style.md` before drafting article copy.
- Read `references/output-contract.md` before creating the `.docx`.
- Read `references/image-guidelines.md` before selecting, cropping, editing, or prompting images — it carries the figure crop-review procedure (`scripts/crop_figure.py`).
- Read `references/review-checklist.md` before final delivery.
- Read `references/case-study-acl2026.md` only when a concrete style example is useful.

## Workflow

1. Gather inputs:
   - Paper PDF or source, title, authors, venue, links, code/repo links.
   - Existing `paper2assets` package files when available: `manifest.json`, `assets/meta/sections.json`, `assets/meta/narration.json`, `assets/meta/figures.json`, `assets/meta/captions.json`, `assets/meta/text.txt`, and `assets/figures/`.
   - Existing examples under the current project, especially example input/output pairs.
   - Paper figures, tables, poster assets, README summaries, and any user-provided constraints.
   - The editing team's required output format. Default to `.docx`.

2. Extract figures, text, and captions from the PDF:
   - If the working folder already has a shared `paper2assets` package, read it first:
     - `manifest.json` for file locations and counts.
     - `assets/meta/sections.json` for canonical claims, section ordering, selected figure references, and reusable evidence.
     - `assets/meta/figures.json` / `assets/meta/captions.json` / `assets/figures/` for image selection and captions.
     - `assets/meta/text.txt` for source verification and details not captured by the sections.
   - If starting from a PDF and no shared package exists yet, initialize one **into `$BLOG_OUT` directly** (resolved per the Output Contract above) — re-using `$BLOG_OUT` as paper2assets' `--outdir` keeps every paper2* skill writing into the same bundle root, so figures/captions/spec/narration that paper2assets produces sit right next to the `.docx` files this skill will later write. From the repo root:

     ```bash
     python skills/paper2assets/scripts/build_package.py <paper.pdf> --outdir "$BLOG_OUT"
     ```

     After `paper_spec.md` or an equivalent section spec exists, sync it:

     ```bash
     python skills/paper2assets/scripts/build_package.py <paper.pdf> \
       --outdir "$BLOG_OUT" \
       --skip-extract \
       --paper-spec "$BLOG_OUT/assets/meta/paper_spec.md"
     ```

   - When the input is a paper PDF, run the bundled extractor instead of hand-collecting figures. It does the tedious, error-prone work — locating each figure on the page, gluing multi-panel sub-figures into one image, and clamping the paper's own caption text off the bottom — far more reliably than eyeballing or screenshotting page regions by hand.

     ```bash
     python scripts/extract_pdf.py <paper.pdf> --outdir "$BLOG_OUT"
     ```

     Use this legacy extractor command only as a fallback when `paper2assets` is not available; new cross-skill workflows should initialize `paper2assets` first. `$BLOG_OUT` is the value you resolved in the Output Contract above — the same bundle root that will later carry `blog_zh.docx` / `blog_en.docx`.

     `outdir` is a working folder for this article (e.g. a folder named after the PDF). It produces:
     - `assets/meta/text.txt` — full paper text (layout-preserving, page breaks kept)
     - `assets/figures/` — one clean PNG per figure
     - `assets/meta/figures.json` — manifest with each figure's `file`, `page`, `width`, `height`, `caption_label`, and `caption`
     - `assets/meta/captions.json` — every "Figure N: …" / "Table N: …" caption keyed by label
     - `assets/meta/metadata.json` — best-effort cover-page metadata (venue, year, emails, code_url, paper_url, arxiv_id, doi); fields may be empty, never fabricated
   - Read `assets/meta/figures.json` to see what figures exist and what each one shows — the captions are your fastest signal for which figure proves which point.
   - If the user supplies loose image files instead of a PDF (or in addition), you can still place those directly; the extractor is for getting clean figures *out of a PDF*.

3. Build an evidence map:
   - Core problem and why it matters now.
   - Prior work or common practice the paper responds to.
   - Main contribution, method, and named components.
   - Key experimental results with exact numbers and dataset/model names.
   - Limitations, assumptions, and claims that must not be overstated.
   - Usable figures and what each figure proves (cross-reference `assets/meta/figures.json` captions).

4. Study examples when available:
   - Extract the article structure, title style, opening rhythm, section depth, figure density, and caption style.
   - Treat examples as editorial style signals, not as text to imitate mechanically.
   - If example output exists as `.docx`, inspect its paragraph sequence and media count.

5. Plan the article before writing:
   - Choose one reader-facing hook or analogy.
   - Decide the section sequence and figure sequence together.
   - Select the 3–7 figures that earn their place (see `references/image-guidelines.md`); note their filenames from `assets/meta/figures.json`.
   - Place each figure immediately after the paragraph that prepares the reader to understand it.
   - Use a table only for compact numeric comparison or benchmark summary.

6. Prepare the selected figures (crop review):
   - The extractor is heuristic and usually crops cleanly, but a few defects slip through, and a bad crop is one of the most visible flaws in a finished article — a figure marooned in whitespace, or the paper's raw English "Figure N: …" caption baked into the image right above the Chinese caption you'll write under it. So **look at each figure you actually selected** (not the whole `figures/` folder — unused figures never reach the reader) and clean it with the bundled `scripts/crop_figure.py`.
   - For every selected figure, run the two safe automated passes — `decaption` (strip any baked-in caption sliver) then `autotrim` (strip excess border whitespace) — then judge by eye and fix any neighbor-bleed or thick caption strip with an explicit `box` crop.
   - Read `references/image-guidelines.md` for the full crop-review procedure, the four defects to watch for, and the exact commands. Don't skip this — it's the single biggest lever on figure quality.

7. Draft both language versions:
   - Write from the **shared evidence map** (step 3) and the **shared figures** (steps 5–6) — same structure, same figures, same numbers and claims in both versions. What changes is the voice, not the facts.
   - **`_zh` (Chinese WeChat):** main body Chinese; keep necessary English terms, paper names, method names, benchmarks, datasets, and model names. Introduce an English technical term with a Chinese gloss on first use when helpful.
   - **`_en` (English research blog):** fluent, native English for a Western technical audience — not a sentence-by-sentence translation of the Chinese. The rhythm and phrasing can differ; the substance must match.
   - **Work autonomously.** Make the editorial calls — hook, structure, figure choice, captions, titles, how to phrase the contribution — yourself, and deliver one complete draft. Don't pause to ask the user to confirm these choices; they'll edit whatever they want changed.
   - For both: prefer clear, restrained, publication-ready prose over marketing copy. Don't invent claims or results, and don't fabricate a checkable hard fact — a paper link, code link, DOI, author affiliation, or acceptance status — since a wrong one ships straight into the editorial pipeline. If such a fact is missing from the inputs, omit it gracefully rather than guessing a specific false value or leaving a "to be confirmed" placeholder. Everything that's editorial judgment, you decide yourself.
   - Read `references/editorial-style.md` for the per-language voice (it carries both the Chinese WeChat register and the English research-blog register).

8. Create the two `.docx` files:
   - **Output location and names:** write final deliverables to `$BLOG_OUT/blog_zh.docx` and `$BLOG_OUT/blog_en.docx`, and keep outlines, cropped figures, previews, and reports under `$BLOG_ASSETS` / `$BLOG_META`. The names are fixed regardless of the paper's title or filename — the Chinese title goes *inside* the `_zh` document, never in the filename.
   - Keep layout simple and editor-friendly: title, subtitle, body paragraphs, headings, inserted figures, captions, optional result table, source links.
   - The two filenames are already ASCII-only by construction (`blog_zh.docx` / `blog_en.docx`); keep any sibling asset filenames (JSON outlines, extracted figures) ASCII-only too. See `references/output-contract.md` for the rationale (downstream CMS/zip/upload tools mangle non-ASCII filenames).
   - Both documents embed the **same** cropped figures from `assets/figures/` (use stable image paths and embed the images into each document, not links). Each figure gets a caption in that document's language.
   - If using Python and `python-docx` is available, `scripts/build_wechat_docx.py` can assemble each document from a JSON outline — run it once per language with its own outline and output path. Pass `--lang zh` for the Chinese document and `--lang en` for the English one so each gets the right font (`_zh` → 微软雅黑 / Microsoft YaHei for Chinese, Arial for Latin; `_en` → Arial for Latin text). If `--lang` is omitted the script infers it from the `blog_zh.docx` / `blog_en.docx` output filename. If an editor requires specific fonts, set an outline-level `"fonts"` object or pass `--latin-font` / `--east-asia-font`; those overrides do not change the article logic.
   - If platform-specific document tools are available, use them, but the final artifacts must still be two `.docx` files.

9. Review and iterate:
   - Run the checklist in `references/review-checklist.md`.
   - Run the machine QA gate before delivery:

     ```bash
     python skills/paper2blog/scripts/check_blog_package.py "$BLOG_OUT" --strict
     ```

     The gate checks that both `.docx` files exist, embed the same figure set,
     declare expected fonts, avoid TODO placeholders, and keep bilingual
     numbers/terms aligned. It also looks for pagination risks: large blank
     areas before images, underfilled images, and likely orphan tails.
   - In strict mode the checker tries to render both DOCX files into PDF/PNG
     previews with LibreOffice and PyMuPDF, then runs page-level layout checks
     for non-final bottom whitespace, near-blank pages, and sparse content. If
     the machine cannot render DOCX directly, render the pages with the
     available document tool and pass:

     ```bash
     python skills/paper2blog/scripts/check_blog_package.py "$BLOG_OUT" \
       --strict \
       --zh-preview-dir <rendered_cn_page_pngs> \
       --en-preview-dir <rendered_en_page_pngs>
     ```

     Strict final delivery must not silently skip preview checks.
   - Write `<blog_outdir>/manifest.json` with root-relative paths for both DOCX
     files, `assets/figures/`, outlines, and QA reports. Include
     `"layout": "v2-assets"`. If the QA gate reports any ERROR, stop and fix the
     blog package unless the user explicitly approves a named degraded path.
   - Deliver one strong complete draft rather than stopping to offer the user options or ask which direction to take — decide, draft, and hand over the finished `.docx` files. The user iterates from a real artifact, not from a list of questions.
   - When the user does edit for personal taste, preserve their preferences unless they introduce factual or logical problems.

## Default Article Shape

Use this as the starting structure for **each** language version unless the user's example suggests otherwise. Both versions share this shape and the same figures; only the language and voice differ.

1. Title and subtitle.
2. Two to three lead paragraphs:
   - what people usually think or do,
   - why the paper's question matters now,
   - the paper's main idea.
3. First overview figure and caption.
4. Source links: paper and code when available.
5. Background/problem section.
6. Method or contribution section, often split into named components.
7. Figure-led evidence sections.
8. Compact result table only if it improves scanability.
9. Summary section with practical significance and limitations.

## Quality Bar

A good output should feel like an editor can send it into the production pipeline after light copy edits. Both the `_zh` and `_en` versions should be understandable, technically faithful, and visually navigable even before professional layout — and they must agree on every number, claim, and figure.

Never let formatting polish compensate for weak content. The paragraph logic, figure captions, and claim accuracy matter most.

## Tools

```
scripts/
├── extract_pdf.py        ← CLI: paper.pdf → text.txt + figures/ + figures.json + captions.json + metadata.json
├── crop_figure.py        ← CLI: clean a selected figure PNG (inspect / decaption / autotrim / box)
├── build_wechat_docx.py  ← CLI: JSON outline → editor-friendly .docx
└── check_blog_package.py ← CLI: hard QA gate for bilingual DOCX deliverables
```

- `extract_pdf.py` is caption-anchored: it finds each figure by its caption, glues multi-panel sub-figures together, and clamps caption text off the bottom of the crop. Run it once per paper PDF (Workflow step 2).
- `crop_figure.py` is the corrective tool for the crop-review step (Workflow step 6). It always backs up to `<file>.png.bak` before writing and keeps `figures.json` dimensions in sync. Full procedure and command reference live in `references/image-guidelines.md`.
- `build_wechat_docx.py` assembles one `.docx` from a JSON outline (paragraphs, headings, embedded figures, captions, tables). Run it **once per language** with `--lang` — a `_zh` outline → `$BLOG_FINAL/blog_zh.docx --lang zh` (font: 微软雅黑 for Chinese, Arial for Latin) and an `_en` outline → `$BLOG_FINAL/blog_en.docx --lang en` (font: Arial for Latin text), both embedding the same figures. The article logic must be planned by the agent; the script is only an assembly aid.
- `check_blog_package.py` validates the final bilingual package and rendered
  layout previews. Run it with `--strict` before delivery and iterate until it
  passes.
- Python package dependencies are listed in `requirements.txt`; `extract_pdf.py` also needs the Poppler `pdftotext` executable on `PATH`.
