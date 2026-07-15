# paper2blog

> Turn a paper's shared assets into a bilingual editorial package — a Chinese WeChat article and an English research blog post — with matched facts, matched figures, editor-friendly `.docx` files, and a strict package gate.

`paper2blog` is the **editorial writing stage** of the ResearchStudio pipeline. It prefers the `<outdir>/` bundle produced by [`paper2assets`](../paper2assets/) so the blog, poster, video, and reel all cite the same claims, numbers, figures, captions, and links.

```
paper2assets  ──▶  paper2blog  ──▶  blog_zh.docx
  <outdir>/         shared evidence   blog_en.docx
```

## Input

Either:

- a `paper2assets` `<outdir>/` containing `manifest.json`, `assets/meta/paper_spec.md`, `assets/meta/text.txt`, and cleaned `assets/figures/`;
- a raw paper PDF, which is resolved to the same `<pdf_stem>/` bundle convention and initialized through `paper2assets`;
- additional editorial references such as a poster, slide deck, README, or user-provided positioning notes.

When a shared package exists, use it first. The legacy extractor is only a fallback for old demos or non-standard inputs.

## Output

Written back into the same v2 bundle root, next to `manifest.json` and `assets/`:

| File | What it is |
|---|---|
| `blog_zh.docx` | Chinese WeChat public-account article, with the Chinese title inside the document |
| `blog_en.docx` | English research-blog article |
| `assets/meta/outline_zh.json` | Structured source outline for the Chinese document |
| `assets/meta/outline_en.json` | Structured source outline for the English document |
| `assets/meta/reports/blog_qa_report.json` | QA report from the blog package checker |
| `assets/meta/previews/` | Optional rendered previews used during review |
| `assets/figures/` | Shared cropped figures embedded into both documents |

The two DOCX filenames stay fixed and ASCII-only so downstream CMS, zip, upload, and reel tooling can find them reliably.

## Usage

From a Claude Code session:

```text
# preferred: point at the shared paper2assets bundle
> /paper2blog ./my_paper/

# or start from a raw PDF; the skill resolves the same bundle root first
> /paper2blog ./my_paper.pdf
```

Both `blog_zh.docx` and `blog_en.docx` are required deliverables. A single-language draft is not a complete `paper2blog` run.

## How it works

1. **Resolve one bundle root** — the same `<outdir>/` used by the other paper2 skills.
2. **Read the shared evidence** from `paper_spec.md`, `sections.json`, `text.txt`, figure manifests, captions, metadata, and any user-supplied materials.
3. **Build one evidence map** covering the paper's hook, method, results, limits, source links, and figure roles.
4. **Select and inspect figures** — keep only figures that earn their place, then crop-review selected images before embedding them.
5. **Write two native articles** — same facts and figure set, but `_zh` uses a restrained WeChat register while `_en` uses a neutral Western research-blog register.
6. **Assemble DOCX files** with stable fonts, embedded images, captions, optional tables, and source links.
7. **Run the QA gate** to confirm both documents exist, embed the expected figure set, and satisfy the package contract.

## Editorial shape

Each article starts from the same editorial backbone: title/subtitle, a concise lead, source links, background/problem, method or contribution, figure-led evidence sections, optional compact result table, and a closing section on significance and limitations.

The two documents are not mirror translations. They should agree on every checkable fact, number, figure, and claim, while reading naturally in their own language.

## Scripts

```
scripts/
├── extract_pdf.py        # legacy/fallback PDF -> text + figures + captions + metadata
├── crop_figure.py        # inspect / decaption / autotrim / box selected figures
├── build_wechat_docx.py  # JSON outline -> editor-friendly DOCX
└── check_blog_package.py # strict bilingual DOCX package gate
```

## Requirements

- Python >= 3.10
- `python-docx`, `pymupdf`, `pillow`
- Poppler `pdftotext` for legacy/fallback extraction
- Fonts available to the renderer/editor: Microsoft YaHei for Chinese, Arial for Latin text

## More detail

[`SKILL.md`](SKILL.md) is the authoritative, agent-facing spec: the v2 output contract, bilingual editorial workflow, crop-review rules, package QA, and manifest requirements. The [`references/`](references/) folder holds the editorial style guide, image guidelines, output contract, review checklist, and a case study.
