# paper2poster

> Turn a paper's extracted assets into a print-ready, single-page academic poster — HTML + PDF + PNG + an editable PowerPoint — fitted to the page exactly.

`paper2poster` is the **rendering stage** of the ResearchStudio pipeline. It takes the `<outdir>/` bundle produced by [`paper2assets`](../paper2assets/), picks the figures, fills a fixed-canvas HTML template with the paper's 9-section spec, runs a measured loop until every section sits at the right density, narrates each section for the in-poster Listen buttons, and exports the result to PDF/PNG plus a natively-editable `.pptx` (via the bundled [`html2pptx`](html2pptx/) sub-skill).

```
paper2assets  ──▶  paper2poster  ──▶  html2pptx
  <outdir>/         poster.html        poster.pptx
                    poster.pdf / .png  (built in — same run)
```

## Input

A `paper2assets` `<outdir>/` containing (at minimum):

- `manifest.json`
- `assets/meta/paper_spec.md` — the 9-section structured summary
- `assets/meta/{text.txt, figures.json, metadata.json}`
- `assets/figures/*.png` — cleaned figure rasters
- `assets/logos/`, `assets/qr/` — optional, best-effort

Run `paper2assets` first if these are missing.

## Output

Written back into the same `<outdir>/`, next to `manifest.json` and `assets/`:

| File | What it is |
|---|---|
| `poster.html` | Self-fitting single-page poster (references `assets/` for figures + fonts). Press `s` for fullscreen, `a` to toggle Listen buttons, `d` for a debug overlay |
| `poster.pdf` | Print-ready PDF at the exact canvas size (Chromium print emulation) |
| `poster.png` | Thumbnail preview |
| `poster.pptx` | Editable PowerPoint — native text + shapes, not a PNG-in-slide (via html2pptx) |
| `assets/audio/*.mp3` | Per-section narration for the Listen buttons (free Edge TTS; skipped if unavailable) |

## Usage

From a Claude Code session:

```text
# point it at a paper2assets <outdir>/
> /paper2poster ./my_paper/

# …or describe what you want in natural language
> /paper2poster Render a portrait poster for arxiv 2502.06434 in teal
```

One run yields all four artifacts — you never call `html2pptx` separately.

## How it works

The lean first render holds only each section's essential text. A **measured fill loop** (`check_poster.py slack` + `polish`) then grows or shrinks content section-by-section until every card reads `FULL` (90–100% of its height) and every figure fills ≥90% of its card on at least one axis. At render time a final **expand** pass lifts under-filled cards toward ~98% and bakes the result back into `poster.html`, so the PDF, PNG, and PPTX all match.

## Two canvas presets

| Orientation | Size | Venues |
|---|---|---|
| **Landscape** (default) | 60 × 36 in (5:3) | NeurIPS · ICML · CVPR |
| **Portrait** (`POSTER_ORIENTATION=portrait`) | A0, 33.1 × 46.8 in | ACL · NAACL · AAAI |

Landscape posters are **composed at build time** from independent layout × style × header modules (see [Header, logos & QR](#header-logos--qr)); portrait keeps dedicated `poster_portrait_{full,half}_solid.html` templates. The renderer routes by orientation, then by the Method figure's aspect ratio.

## Header, logos & QR

The column **layout**, visual **style**, title-band **header**, and **Scan-to-Read** internal layout are four independent axes, composed into one self-contained file by `references/compose_poster.py` (no N×M×K×J template explosion):

- **Layout** — `assets/layouts/{full,half,3col}.html` (column structure).
- **Style** — `assets/styles/*.css` — 11 visual treatments (solid · framed · simple · left-bar · elevated · neo-brutal · tag · underline · tinted · double-rule · legend-frame), randomized by default. `double-rule` and `legend-frame` centre their heading; the other 9 are left-aligned.
- **Header** — `assets/headers/{v1…v5}.html`, randomized by default: v1 venue-left · v2 venue-right · v3 centered strip · v4 title-left / logos-right · v5 classic text badge.
- **Scan** — `assets/scan/{aside,hero,contact,directory,banner,twin,chips}.html`, the Scan-to-Read internal layout. The build picks `--scan single` (paper only) or `dual` (paper + code) and compose samples a fitting variant, so a 2-QR layout never lands on a 1-QR paper.

**Venue logo** — `paper2assets` best-effort fetches the conference mark (Wikipedia / Wikidata) into `assets/logos/_venue.png`; the header shows that logo and hides the venue-year text so the two never duplicate. The venue is always the **real conference / journal** — never "arXiv" (a preprint host is not a publication venue).

**Institution logos** — `references/fit_logos.py` packs the institution marks to fill the header zone at a single **uniform height** (every logo enlarges together, sized by the browser's true aspect ratio so even wide SVG wordmarks fit without overflowing the band).

**QR codes** — the Paper / Code QRs live in the **Scan to Read** section (its internal layout is the scan axis above) for headers v1–v4; the v5 classic header carries a QR in the title band itself. The **3col layout suppresses Scan-to-Read** (its 1/3-width column would read empty) and is kept off v5 — a 3col poster carries no QR.

## Tuning knobs (env vars)

| Var | Default | Controls |
|---|---|---|
| `POSTER_ORIENTATION` | `landscape` | `landscape` or `portrait` |
| `POSTER_STYLE` | random | landscape style: 1 of 11 (`solid` … `legend-frame`) |
| `POSTER_HEADER` | random | title-band header `v1`–`v5` (see [Header, logos & QR](#header-logos--qr)) |
| `POSTER_FONT` | `Arial` | any of 8 PPT-safe families (Arial round-trips with no font embedding) |
| `POSTER_FULL_THRESHOLD` | `0.90` | the fill-loop's FULL gate (raise for a tighter pack, ~2× loop time) |
| `POSTER_EXPAND_THRESHOLD` | `0.98` | render-time expand target (`0` disables) |

## Scripts

```
scripts/
├── check_poster.py     # slack / preflight / polish / verify-final / deliverables gates
├── render_poster.py    # print-emulated PDF + PNG; applies & bakes the expand
└── generate_audio.py   # narration.json → assets/audio/<id>.mp3 (free Edge TTS)
```

Figure-cropping tools live in `paper2assets`; the PPTX converter is bundled at [`html2pptx/`](html2pptx/).

## Requirements

- Python ≥ 3.10, `playwright` + Chromium (`python -m playwright install chromium`)
- `edge-tts` — optional, for the narration audio
- LibreOffice — for the html2pptx PPTX export

## More detail

[`SKILL.md`](SKILL.md) is the authoritative, agent-facing spec: the full step-by-step workflow, the template-routing rules, the staged-fill convergence protocol, and every edge case. The [`references/`](references/) folder holds the deep guides (template substitution, content patterns, visual polish, staged fill, audio narration).
