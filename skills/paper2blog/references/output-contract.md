# Output Contract

## Required Deliverable

Create **two `.docx` files** for the editing team. In normalized AutoResearch
runs, both must be written at the bundle root: `<blog_outdir>/blog_zh.docx` and
`<blog_outdir>/blog_en.docx`. The only other top-level index is
`manifest.json`; figures and build intermediates live under `assets/`. Legacy
`final/` / `intermedia/` runs remain readable for old demos, but new outputs
must follow this v2 assets layout. Both documents are required by default.

Each document should contain:

- Final title and subtitle (in that document's language).
- Article body in that document's language — Chinese for `_zh`, English for `_en`.
- Embedded figures at intended positions (the **same** figures in both).
- Captions under each figure, written in that document's language.
- Paper link and code/project link when available.
- Optional compact result table when it improves readability (same numbers in both).
- No unresolved placeholders unless the user explicitly requested a draft with TODOs.

The two documents must agree on every number, claim, and figure. They differ only in language and voice.

## Editor-Friendly Formatting

Formatting is not the main value, but the `.docx` should be clean enough to inspect:

- Use readable fonts (Chinese-capable for `_zh`; a clean Latin face for `_en`). The builder script sets these per language by default: `_zh` → 微软雅黑 (Microsoft YaHei) for Chinese and Arial for Latin; `_en` → Arial for Latin text. If the editing team asks for specific fonts, override them in the outline `"fonts"` object or with `--latin-font` / `--east-asia-font`.
- Keep headings obvious.
- Keep body paragraphs as normal text, not text boxes.
- Insert figures as real embedded images.
- Put captions immediately after figures.
- Avoid complex layouts, floating objects, multi-column tricks, decorative covers, or nested tables.
- Use tables only for genuinely tabular information.

## Recommended DOCX Structure

1. Title.
2. Subtitle or one-line deck.
3. Lead paragraphs.
4. Overview figure.
5. Paper/code links.
6. Main article sections.
7. Result table if useful.
8. Closing summary.

## Suggested JSON Outline for the Builder Script

The optional `scripts/build_wechat_docx.py` accepts a JSON file like this. Run it **once per language** with its own outline and output path, passing `--lang zh` or `--lang en` to select the font (`_zh` → 微软雅黑 for Chinese + Arial for Latin; `_en` → Arial for Latin text). The language can also be set via an optional `"lang"` field in the outline, or inferred from the `blog_zh.docx` / `blog_en.docx` output filename. Manual font overrides can be supplied either in the outline `"fonts"` object or via CLI flags; CLI flags take precedence.

`_zh` outline → `<blog_outdir>/blog_zh.docx` (built with `--lang zh`, font 微软雅黑 for Chinese + Arial for Latin):

```json
{
  "title": "ACL 2026 | 数据不是只要选得好，还要排得好",
  "subtitle": "微软研究院等提出大模型训练数据组织新指南",
  "lang": "zh",
  "fonts": {"latin": "Arial", "east_asia": "Microsoft YaHei"},
  "blocks": [
    {"type": "paragraph", "text": "训练大语言模型时，我们通常首先关心..."},
    {"type": "figure", "path": "assets/overview.png", "caption": "图1 ...", "width_inches": 6.2},
    {"type": "heading", "level": 1, "text": "数据组织为什么重要"},
    {"type": "table", "caption": "表1 ...", "headers": ["方法", "结果"], "rows": [["Random", "37.09"], ["SAW", "38.78"]]}
  ]
}
```

`_en` outline → `<blog_outdir>/blog_en.docx` (built with `--lang en`, font Arial; same figures/numbers, English copy):

```json
{
  "title": "ACL 2026 | Good Data Isn't Enough — Order Matters Too",
  "subtitle": "Microsoft Research and collaborators propose new guidelines for organizing LLM training data",
  "lang": "en",
  "blocks": [
    {"type": "paragraph", "text": "When training large language models, we usually worry first about which data to use..."},
    {"type": "figure", "path": "assets/overview.png", "caption": "Figure 1. ...", "width_inches": 6.2},
    {"type": "heading", "level": 1, "text": "Why data organization matters"},
    {"type": "table", "caption": "Table 1. ...", "headers": ["Method", "Score"], "rows": [["Random", "37.09"], ["SAW", "38.78"]]}
  ]
}
```

Note both `figure` blocks point at the **same** `assets/overview.png` — figures are extracted and cropped once and shared. Use the script only as an assembly aid. The article logic must be planned and reviewed by the agent.

## Naming

**Location and names.** In normalized runs, write both `.docx` files into
`<blog_outdir>/` and keep extracted/cropped figures, outlines, rendered
previews, and QA reports under `<blog_outdir>/assets/`.
Use the **fixed names** `blog_zh.docx` and `blog_en.docx`:

- normalized bundle → `<blog_outdir>/blog_zh.docx` and `<blog_outdir>/blog_en.docx`.

The names are fixed and do **not** depend on the paper's title, base name, or arXiv id — every run produces the same two filenames inside its own outdir, so there is never a base-name collision or transliteration question. The Chinese title belongs *inside* the `_zh` document (title page, headings), never in the filename.

These two filenames are ASCII-only by construction. Keep any sibling asset filenames (the JSON outlines, the extracted figures) ASCII-only as well — do not introduce Chinese characters, full-width punctuation, emoji, or other non-ASCII characters in filenames, even though the `_zh` article body is Chinese. This is because:

- Downstream editor tools, CMS uploaders, zip archives, and email attachments frequently mangle non-ASCII filenames (mojibake, Latin-1/UTF-8 confusion, or outright rejection).
- ASCII filenames are stable across Windows, macOS, Linux, and WeChat's upload pipeline.

If the user explicitly asks for a different or Chinese filename, push back once and explain the portability issue; only comply if they confirm.

## Visual QA

If rendering tools are available, render or preview **both** `.docx` files before delivery. Check each for:

- Images are present and readable (and identical across the two versions).
- Captions stay near their figures and are in the right language.
- Tables are not clipped.
- No text overlaps.
- Links and title are visible.

If full rendering is unavailable, inspect each DOCX's structure and embedded media, and disclose that full visual QA was not completed.
