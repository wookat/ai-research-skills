# Review Checklist

Run this before delivering — and run it against **both** deliverables, the Chinese `<blog_outdir>/blog_zh.docx` and the English `<blog_outdir>/blog_en.docx` in normalized runs. The two articles share one evidence map and one set of figures, so most checks below apply to each file independently, plus a cross-version consistency pass.

## Bilingual Consistency

- Both `blog_zh.docx` and `blog_en.docx` exist at the paper2blog bundle root; extracted/cropped figures and outlines live under `assets/`.
- Every number, claim, dataset/model name, and acceptance status matches between the two versions.
- Both embed the **same** cropped figures in the same order — only the caption language differs.
- Neither version is a sentence-by-sentence translation of the other; each reads natively in its own voice.
- Paper and code links are identical in both.

## Factual Accuracy

- Paper title, authors, venue/status, paper link, and code link are correct.
- Main claims are supported by the input paper or user materials.
- Numeric results match the source.
- Dataset, model, benchmark, and training-stage names are correct.
- Limitations or assumptions are not hidden when they matter.
- No invented figures, tables, links, affiliations, or acceptance status.

## Editorial Logic

- The opening explains why the problem matters before diving into method names.
- Each section advances the story.
- Technical terms are introduced before they are used heavily.
- The article distinguishes problem, method, evidence, and takeaway.
- The ending explains practical significance without overstating impact.

## Figure Logic

- Every figure is referenced or prepared by nearby text.
- Every figure has a meaningful caption.
- Figures appear in the order the reader needs them.
- Result figures or tables support claims made in the text.
- Captions do not claim more than the figure shows.

## Chinese Copy (`_zh`)

- Main body is Chinese.
- Necessary English terms are preserved and explained on first use.
- Sentences are not direct machine-translation fragments.
- Tone is professional and public-account friendly.
- No repetitive phrase patterns across sections.

## English Copy (`_en`)

- Main body is fluent, idiomatic English — no translationese ("aiming at the problem of...", "has important significance", "carried out experiments").
- Technical terms, method names, benchmarks, datasets, and model names match the paper's spelling exactly.
- Tone is a neutral Western research-blog register: informative, not promotional.
- No hype words (revolutionary, groundbreaking, game-changing) unless the paper makes the claim and backs it.
- Interpretation is signaled ("this suggests", "the authors argue") rather than dressed up as the paper's stated conclusion.

## DOCX Structure (both files)

- Final output is **two** `.docx` files at the paper2blog bundle root: `blog_zh.docx` and `blog_en.docx`.
- Both filenames are exactly `blog_zh.docx` / `blog_en.docx` (ASCII-only by construction). The Chinese title goes inside the `_zh` document, not in the filename.
- Each uses a font that renders its language (`_zh` defaults to 微软雅黑 / Microsoft YaHei for Chinese and Arial for Latin; `_en` defaults to Arial, with Microsoft YaHei as CJK fallback). Any manual font override is intentional and recorded in the outline or builder command.
- Images are embedded in each file, not merely linked.
- Captions are adjacent to figures and in that document's language.
- Tables, if any, are readable and carry the same numbers in both versions.
- There are no TODO markers unless requested.
- Run the hard gate before final delivery:

  ```bash
  python skills/paper2blog/scripts/check_blog_package.py <blog_outdir> --strict
  ```

- Strict gate must inspect rendered layout previews for both DOCX files. By default it uses LibreOffice/PyMuPDF to render PDF/PNG previews. If the machine cannot render DOCX directly, create page PNGs with the available document tool and pass `--zh-preview-dir` and `--en-preview-dir`; do not skip preview checks for final output.
- Fix any gate finding for large non-final page whitespace, near-blank/sparse pages, underfilled images, likely orphan tails, missing media, font declaration issues, placeholder text, or bilingual figure/number mismatch.

## Final Response to User

Mention:

- Both final `.docx` paths (`_zh` and `_en`).
- Any important QA limitation, such as unavailable rendering tools.
- One or two concise notes about what the drafts contain.
