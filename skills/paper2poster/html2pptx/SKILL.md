---
name: html2pptx
description: "Convert a rendered HTML page (especially A0 conference posters) into a native PowerPoint .pptx with editable text + native shapes — NOT a PNG-in-slide. Walks the live DOM via headless chromium, extracts BLOCK-level text containers (p/h1-h6/li/td) as TextBoxes with inline <strong>/<em> as mixed-style Runs, <img> as Picture with object-fit:contain respected (plus white-tile decoration under transparent-PNG logos), CSS ::before/::after generated content (e.g. 'So what →' callouts) as inherited-style runs, SVG via cairosvg rasterization, decorative <div>/<section> with bg/border/gradient/box-shadow as Rectangle/RoundedRect with matching fill (solid + linear-gradient + outer shadow). All CSS colors (including color-mix/oklab/color()) normalized via canvas. CSS hyphens:auto becomes OOXML soft hyphens via pyphen. CSS line-height absolute Pt for paragraph spacing. Native OOXML bullets with hanging indent. Optional Claude-vision fidelity auditor runs by default (toggle with `--no-vision-audit`); diffs HTML truth vs PPT render → structured 12-category issue report. Supports both direct API (`ANTHROPIC_AUTH_TOKEN`) and base-URL proxy (`ANTHROPIC_BASE_URL`) auth. Targets ~95% visual fidelity with web fonts installed. TRIGGER when user asks: 'HTML to PPT', 'poster to PowerPoint', 'editable PPT from HTML', 'pptx from html', '1:1 PPT clone', or wants an HTML render shipped as an editable .pptx for a non-developer collaborator."
---

# html2pptx

Convert a rendered HTML page → native PowerPoint .pptx with **editable shapes** (not a PNG-in-slide).

## When to use

- "Convert this HTML poster to PPT."
- "I need an editable PowerPoint version of my HTML page."
- "1:1 PPT clone of poster.html — fonts/colors/layout."
- "Hand off the poster to a non-developer in PPT."

## When NOT to use

- Need a flat PNG slide → use `paper2poster/demo/presentation/posters.pptx`.
- HTML uses heavy JS animations / video → those don't translate to PPT shapes.
- Math-heavy KaTeX content → math gets rasterized fallback (loses equation editability).

## Setup (one-time)

### 1. Python deps
```bash
pip install python-pptx playwright pdf2image lxml Pillow pyphen cairosvg
playwright install chromium     # ~110MB headless browser
```

### 2. soffice (for verification)
```bash
# Linux:
sudo apt install libreoffice-impress
# Mac:
brew install --cask libreoffice
```

### 3. **Web fonts — CRITICAL for fidelity** (Read [GOTCHAS.md](./GOTCHAS.md#g1))

> **Default = Arial → you can skip this whole section.** Since the paper2poster
> Arial default, posters render in **Arial** (or another PPT-safe family: Calibri,
> Aptos, Cambria, Times New Roman, Verdana, Georgia, Trebuchet MS). Those are
> pre-installed on every Mac + Windows PowerPoint, so you do **not** need the font
> installs below and the `.pptx` is portable **without embedding**. The
> Inter / Source Serif 4 / JetBrains Mono setup below applies **only** when the
> poster was rendered with the optional **Inter** webfont override.

Without Inter / Source Serif 4 / JetBrains Mono installed, soffice falls back to DejaVu Sans (Linux) or Helvetica (Mac) — character widths change, text wraps differently, all positions cascade-shift.

**Linux:**
```bash
# Download static-weight TTFs (variable fonts register under wrong family name)
mkdir -p /tmp/fonts-dl && cd /tmp/fonts-dl
curl -sL "https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip" -o Inter.zip
curl -sL "https://github.com/adobe-fonts/source-serif/releases/download/4.005R/source-serif-4.005_Desktop.zip" -o SourceSerif4.zip
curl -sL "https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip" -o JetBrainsMono.zip
unzip -qo Inter.zip -d Inter/
unzip -qo SourceSerif4.zip -d SourceSerif4/
unzip -qo JetBrainsMono.zip -d JetBrainsMono/

mkdir -p ~/.local/share/fonts
cp Inter/extras/ttf/Inter-{Regular,Medium,SemiBold,Bold,Italic,SemiBoldItalic,BoldItalic}.ttf ~/.local/share/fonts/
cp SourceSerif4/source-serif-4.005_Desktop/TTF/SourceSerif4-{Regular,Semibold,Bold,It,SemiboldIt,BoldIt}.ttf ~/.local/share/fonts/
cp JetBrainsMono/fonts/ttf/JetBrainsMono-{Regular,Medium,Bold,Italic,BoldItalic}.ttf ~/.local/share/fonts/
fc-cache -f ~/.local/share/fonts/

# Verify: fc-match MUST return the font itself, not a fallback
fc-match "Inter" "Source Serif 4" "JetBrains Mono"
```

**Mac:** Same downloads, but copy to `~/Library/Fonts/` and **fully quit + reopen PowerPoint** (Cmd+Q) to pick up new fonts.

For a poster using the default **Arial** (or any PPT-safe family), the viewer needs nothing — those fonts ship with PowerPoint, so the pptx is portable as-is. Only for the optional **Inter** override must the viewer either have Inter installed OR the pptx embed it via the opt-in `scripts/font_embedder.py` step (embeds the 4 Inter weights into the pptx; ~3 MB).

## Quick start — one command

```bash
cd skills/paper2poster/html2pptx
python -m scripts.auto_correct_loop --html /path/to/poster.html
```

Outputs default to the input HTML's parent directory (sibling-co-located convention, 2026-06-12 spec) — e.g. `my_paper/poster.html` → `my_paper/poster.pptx`. Successive runs in the same dir overwrite the previous .pptx. Override with `--outdir /custom/path/`.

**Bundle contract (paper2* pipeline).** When invoked as the poster pipeline's final handoff, the caller passes `--outdir <bundle>/assets/_pptx_build/` so every html2pptx artifact (DOM json, sanity PNGs, the soffice render) stays under `assets/`, then promotes the deck to the bundle root — `cp <bundle>/assets/_pptx_build/poster.pptx <bundle>/poster.pptx` — because `poster.pptx` is a top-level deliverable (the only html2pptx output that leaves `assets/`). The input `poster.html` references its figures / logos / fonts with **root-relative `assets/…` `src` paths**; the converter loads the HTML via `file://`, so those resolve from the HTML's own on-disk location automatically — no path handling is needed in the converter.

This is the canonical entry point. It:
1. **Auto-detects canvas** from CSS `@page { size: ... }`, caps to 55" if poster > 56" (PPT limit) with proportional scale
2. **Auto-detects sibling `poster.pdf`** (if present): runs `pdffonts` on it, builds CSS-name → PDF-font alias map. Writes a fontconfig `<match>` runtime override so the browser uses the SAME fonts as the reference PDF — wraps match 1:1. Cleaned up via `atexit`.
3. **Auto-downloads** any other HTML-referenced fonts from Google Fonts (`font_resolver.py`)
4. Extracts DOM (one playwright run, cached as `<name>_dom.json`)
5. Builds pptx → renders via soffice → PNG
6. Saves comparison PNGs: `<name>_html_print.png` (print viewport, matches PPT canvas) and `<name>_html_browser.png` (1920×1080 browser viewport, fullPage)
7. **Vision-audit (ON by default)**: calls Claude vision to diff `<name>_html_print.png` vs `<name>.png`, writes `<name>_audit.json` with structured fidelity issues (severity, category, block_idx, where, description). When a prior audit JSON exists, prints a delta (e.g. `+/- 3 issues vs previous`). **Default model: Opus 4.8** (~$0.10/poster; override with `--vision-model claude-sonnet-4-6` for ~$0.02/poster if budget matters more than catch-rate); ~70s extra runtime.

### Model selection (for orchestrators invoking this skill)

The skill exposes two independent model knobs. When a user says "use Opus" / "use Sonnet" / "use the cheaper one" / etc., the orchestrating Claude **must translate that to the right flag** — the skill scripts have no natural-language parsing.

| User intent | Flag to pass | Applies to |
|---|---|---|
| "Use Opus" / "highest quality" / no model specified (default) | (omit flag — default is Opus 4.8) | both |
| "Use Sonnet" / "cheaper" | `--vision-model claude-sonnet-4-6` (and `--fix-model claude-sonnet-4-6` if running auto_fix_loop) | both |
| "Don't audit" / "skip vision" / batch automation | `--no-vision-audit` | auto_correct_loop |
| "Vision Opus but fix Sonnet" (rare) | `--vision-model claude-opus-4-8 --fix-model claude-sonnet-4-6` | auto_fix_loop only |

**Two separate knobs, two separate scripts**:

- `scripts/auto_correct_loop.py` (build + audit) → `--vision-model <MODEL>`
- `scripts/auto_fix_loop.py` (build + audit + autonomous code-fix subagent) → `--vision-model <MODEL>` AND `--fix-model <MODEL>` (both default Opus 4.8; the `--fix-model` is explicitly passed to `claude -p --model` so the subagent doesn't silently inherit the orchestrator's CLI config)

**Reproducibility**: both scripts log the model choice at start. The vision-audit logs `[vision-audit] calling Claude vision (claude-opus-4-8, auth=...)`; auto_fix_loop logs `[fix-loop] models: vision-audit=..., fixer=...`. If a user reports unexpected behavior, the model used is in the run log.

### Vision-audit auth

Two paths, either works:

| Mode | Env vars | Use case |
|---|---|---|
| **Direct API** | `ANTHROPIC_AUTH_TOKEN` (or `ANTHROPIC_API_KEY`) | Personal key, direct to api.anthropic.com |
| **Base-URL proxy** | `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL` | Corporate proxy / Vertex / Bedrock / company gateway. **This is the setup on the local dev machine.** |

If neither auth is configured, audit silently skips with a one-line hint (so `--no-vision-audit` isn't required for offline/CI runs). Pass `--no-vision-audit` to explicitly disable for batch automation (100 posters = ~$2 + ~2hr extra).

### 3-round revision workflow (dev cycle)

Vision audit replaces the old PIL-based L2 loop with a much more useful signal: **structural fidelity diff**, not cosmetic font shrinking. Each rerun re-runs the audit and shows `+/- N issues vs previous` — the dev iteration loop is:

```bash
# round 1: baseline (defaults to ./output/<timestamp>/)
python -m scripts.auto_correct_loop --html poster.html
# → look at output/<ts>/poster_audit.json, identify top systemic bug

# round 2: after fixing the bug in html_to_pptx.py
python -m scripts.auto_correct_loop --html poster.html --outdir output/<ts>/
# → output shows e.g. `[vision-audit] 2 issues (-9 vs previous)`

# round 3: fix next bug, target near-zero high-severity
python -m scripts.auto_correct_loop --html poster.html --outdir output/<ts>/
```

Empirically: **2-3 rounds clears most issues** on a new HTML template. Each round costs ~1 minute + ~$0.02.

Cross-poster aggregation: `python -m scripts.vision_aggregate <root_dir>` walks every `<poster>/poster_audit.json` and prints category frequencies + per-poster issue counts → reveals SYSTEMIC bugs (same category appearing across N posters) worth fixing in code vs one-off issues.

### Autonomous fix loop (`auto_fix_loop.py`) — fully agentic

For per-poster fidelity fixes you don't want polluting the shipped skill, run:

```bash
python -m scripts.auto_fix_loop --html /path/poster.html --max-rounds 3
```

Each round:
1. Builds + audits (via an ISOLATED COPY of `scripts/` under `output/<ts>/_skill_run_copy/`)
2. Picks top actionable issue from the audit (category whitelist filters out vision-prone false positives like `alignment_off`)
3. Spawns `claude -p` subagent, **sandboxed to the copy** (`--add-dir <copy>`, only Read/Edit/Grep/Glob tools — no Bash, no git, can't escape)
4. Subagent reads `GOTCHAS.md` + the copy's `html_to_pptx.py`, makes a minimal diff
5. Rebuild + re-audit
6. If issue count dropped → keep change in the copy's internal git
   Otherwise → `git reset --hard` in the copy → try next issue
7. Loop terminates: convergence (no actionable issues) OR max-rounds OR consecutive-failures cap

**Per-run isolation** is the critical design point: your shipped `skills/paper2poster/html2pptx/` is NEVER touched. Each run produces:
- `output/<ts>/<name>.pptx`            — final patched PPT
- `output/<ts>/<name>_audit.json`      — final audit (target: 0 issues)
- `output/<ts>/<name>_run_patches.diff` — cumulative subagent diff vs baseline (review me!)
- `output/<ts>/_skill_run_copy/`       — patched skill copy (rerun-able on the same HTML)
- `output/<ts>/<name>_fix_loop_summary.json` — per-round trajectory

If reviewing the `.diff` shows a fix is genuinely general (not poster-specific), cherry-pick it into the shipped skill via a normal PR. Otherwise the patch stays scoped to that one output dir — other posters / other people's installs unaffected.

Cost: ~$1–3 per converged run with default models (Opus 4.8 for both vision-audit and fix subagent). Override either via `--vision-model` / `--fix-model` (e.g. `claude-sonnet-4-6`) to cut cost by ~5× at the price of lower catch-rate / weaker root-causing. Both model choices are logged at start so the run is fully reproducible.

Auth: same as `--vision-audit` (`ANTHROPIC_AUTH_TOKEN` direct or with `ANTHROPIC_BASE_URL` for corporate proxy).

> **Removed 2026-06-05**: the previous "L2 closed-loop" font-shrinking
> rounds — PIL-predicted overflow was decoupled from soffice's actual render
> (audit showed 17→17→17→17 overflows across 4 rounds on paper_4_d), and
> the shrinker introduced occasional false-positive shrinks on healthy body
> paragraphs. Replaced with `--vision-audit` (default-on) which catches REAL
> fidelity issues (missing logo, dropped span, wrong wrap) — issues PIL
> could never see. Wrap fidelity itself is now solved at DOM-extract time
> (browser `extractWrapLines` with CSS line-height threshold), not after-
> the-fact. The `--rounds` / `--shrink-step` flags still parse (silently
> no-op) so existing call sites don't break.

Output convention: outputs land in `dirname(input_html)/` by default (sibling of the source HTML); pass `--outdir <path>` to override.

Default slide 47×33.1" (A0 landscape). Override via `--width-inch` / `--height-inch`.

## Font workflow

The skill resolves fonts in this priority chain:

1. **Sibling `poster.pdf` exists** (or `--reference-pdf` flag): the skill extracts the PDF's actual fonts via `pdffonts`, builds an alias map (e.g. CSS `Inter` → PDF `Arimo`), installs the PDF fonts locally, and writes a fontconfig `<match>` runtime override forcing the browser to render with the PDF fonts (not the CSS-named ones). PPT XML font names = PDF font names. **Best fidelity** when matching a coworker's existing PDF rendering whose machine fell back to different fonts than the CSS designer intent.

2. **No sibling PDF**: the skill walks all `font-family` declarations in the HTML and auto-downloads from Google Fonts any that aren't installed (`font_resolver.py`). Designer-intent fonts (Inter, Source Serif 4, JetBrains Mono, Roboto, Playfair Display, etc.) all available on Google Fonts get installed automatically.

3. **CSS / Mac / Win system fonts** without a Google Fonts equivalent (Helvetica Neue, SF Pro, Menlo, etc.) are mapped via `FONT_ALIASES` in `html_to_pptx.py` to installed equivalents (Inter, JetBrains Mono, Source Serif 4) for both browser-side fontconfig alias and PPT-side run.font.name.

## Verifying output

```bash
# Open the last round's PNG; compare with the HTML render PNG:
ls /tmp/uframe_round_*.png
# soffice → PDF → PNG at 96 DPI to match playwright (DPI mismatch = false font-size-look-smaller bug)
```

**Critical**: `dpi=96` everywhere. Mismatched DPI in comparison PNGs creates visual size discrepancy that looks like a font-size bug but isn't.

**soffice render ≠ PowerPoint render.** Always sanity-check the final `.pptx` in actual PowerPoint (Mac/Win). soffice often diverges on shadow blur, font-shaper kerning, and gradient stops.

## Architecture

```
HTML
  ↓ [playwright chromium] render + DOM walk
  ↓ getComputedStyle on every visible element
  ↓ canvas.fillStyle = anyColor → normalized rgba()
DOM extract (cached as <name>_dom.json)
  ├─ elements   → boxes (bg/border/gradient/shadow) + images (with object-fit + decoration tile)
  └─ text_blocks → block-level (p/li/h1-h6/figcaption/td/th) with inline runs
                   (incl. ::before/::after pseudo-element content as inherited-style runs)
  ↓ [python-pptx + lxml] generate native shapes (Z-order by DOM depth)
PPTX
  - Picture (object-fit:contain math → centered, letterboxed inside content area = bbox - padding)
    + optional decoration tile UNDER picture (CSS background-color/border-radius/box-shadow)
    + SVG → PNG via cairosvg before embed
  - Rectangle / RoundedRect (CSS border-radius → exact roundRect adj)
    + solid fill / linear gradient (gradFill XML)
    + border (line.color/width)
    + box-shadow (outerShdw effect)
  - TextBox per block element
    + multiple inline Runs (one per <strong>/<em>/text node/pseudo-element)
    + CSS padding → tf.margin_*
    + CSS line-height → absolute Pt line_spacing
    + CSS text-transform applied per-run (so ::before uppercase doesn't inherit paragraph 'none')
    + CSS letter-spacing → OOXML rPr spc
    + CSS hyphens:auto → pyphen-inserted U+00AD soft hyphens
    + <li> → native OOXML <a:buChar> with hanging indent + section color marker
    + overflow:hidden + line-clamp → PIL-measured truncation + "…"
    + single-word short text (≤6 chars, no spaces) → word_wrap=False (honors browser-proven fit)
PPTX (final)
  ↓ [optional: --vision-audit] Claude vision diff (html_print.png vs ppt.png)
  ↓ structured fidelity report (<name>_audit.json): 12 categories × 3 severities
  ↓ delta vs previous audit if one exists → dev-cycle smoke test
```

## Capability table

| Capability | Status |
|---|---|
| Position / sizing pixel-perfect | ✓ |
| Computed colors (oklab / color-mix / color() / hsl / named) | ✓ via canvas |
| Alpha compositing (rgba with α<1 → composited over white) | ✓ |
| Inline `<strong>`/`<em>` as Runs in same paragraph | ✓ |
| Section colored banner (h3 bg + text + numbered marker) | ✓ |
| Linear gradients | ✓ (`gradFill`) |
| Box-shadow | ✓ (`outerShdw`) |
| Border-radius (exact CSS px → roundRect adj) | ✓ |
| Per-side borders (border-top/right/bottom/left, asymmetric) | ✓ thin Rect per present side |
| Inline text background → run highlight (Text Highlight Color) | ✓ schema-compliant rPr order |
| Superscript / Subscript (`<sup>`/`<sub>` or CSS vertical-align) | ✓ baseline offset + readability floor |
| Image object-fit:contain (letterboxed inside bbox) | ✓ |
| CSS padding → textbox margins | ✓ |
| CSS line-height absolute (eliminates trailing whitespace) | (leveraged when needed) |
| CSS hyphens:auto (libhyphen → pyphen soft hyphens) | ✓ |
| Native OOXML bullets with hanging indent + section color | ✓ |
| overflow:hidden + line-clamp truncation | ✓ |
| Auto-detect canvas size from `@page { size: ... }` | ✓ |
| Cap slide to PPT 56" with proportional scale | ✓ |
| Auto-download fonts from Google Fonts | ✓ (via font_resolver) |
| Auto-detect sibling poster.pdf → extract its fonts, alias-map | ✓ when present |
| CSS `::before`/`::after` generated content as inherited-style runs | ✓ (catches "So what →" callouts, content-arrow icons) |
| Per-run text-transform override (pseudo-content uppercase != paragraph 'none') | ✓ |
| `<img>` decoration tile (white rounded-rect under transparent-PNG logos) | ✓ (CSS background-color + border-radius + padding) |
| SVG embed (rasterized via cairosvg → PNG) | ✓ |
| Single-word short text → word_wrap=False (badges like ICLR/ICML) | ✓ (≤6 chars, no spaces) |
| Vision-audit fidelity report (Claude vision diff, 12 categories) | ✓ **ON by default** (~$0.02/poster; silently skipped when no auth) |
| Autonomous code-fixer loop (claude-p subagent in isolated skill copy) | ✓ via `scripts/auto_fix_loop.py` (~$0.50-1.50/run; shipped skill never modified) |
| Cross-poster systemic-bug aggregation | ✓ via `scripts/vision_aggregate.py` |
| Closed-loop font shrinking for overflow (L2) | ✗ removed 2026-06-05 (PIL-prediction-vs-soffice decoupling made it a no-op + false-positive risk; replaced by --vision-audit) |
| Match-wrap (force PPT wrap at browser positions) | ✗ default off; opt-in via flag |
| Font embedding in pptx (cross-machine portability) | ✗ (Phase 3 TBD) |
| KaTeX math equations | ✗ (Phase 4 PNG fallback) |
| CSS transforms / filters | ✗ (Phase 4 PNG fallback) |

## Scripts

- `scripts/html_to_pptx.py` — DOM extract + pptx build (accepts `--corrections` legacy, `--match-wrap` to force browser wrap positions). Supports `::before`/`::after` pseudo-element content extraction (CSS callouts like "So what →"), per-run text-transform, `<img>` decoration tiles (white rounded rect under transparent-PNG logos), and SVG rasterization via cairosvg.
- `scripts/auto_correct_loop.py` — **canonical entry**: single-shot DOM-extract → build → render → compare-PNG generator. Handles sibling-PDF font alias + Google Fonts auto-download. Default outdir = `dirname(input_html)/` (sibling-co-located). With `--vision-audit` (default on), runs vision diff after render.
- `scripts/auto_fix_loop.py` — **autonomous fix loop**: copies skill scripts to an isolated `output/<ts>/_skill_run_copy/`, spawns `claude -p` per round to fix the top audit issue in the COPY (sandboxed via `--add-dir`), rebuilds, re-audits, keeps or rolls back via the copy's internal git. Shipped skill stays untouched; per-run diff exported for human cherry-pick.
- `scripts/vision_audit.py` — Claude vision fidelity auditor. Takes (html_truth.png, ppt.png, dom.json) → structured issue list classified into 12 categories (missing_element, wrap_mismatch, text_clipped, color_drift, ...) with severity and block_idx. Replaces the abandoned PIL-based L2 loop.
- `scripts/vision_aggregate.py` — cross-poster category frequency rollup. Walks `<root>/*/poster_audit.json`, prints which bugs recur and how often — surfaces SYSTEMIC issues vs one-off.
- `scripts/font_resolver.py` — Google Fonts auto-download + sibling-PDF font detection + fontconfig runtime alias

## Why this beats pixel-based PDF→PPTX converters

→ See [difference.md](./difference.md) — concrete advantages over iLovePDF / Smallpdf-style raster converters: inline text highlight as run property (not floating shape), native list bullets (not orphan glyphs), bold preserves family (not lookalike substitute), plus other native-vs-pixel semantic preservation.

## Gotchas

→ See [GOTCHAS.md](./GOTCHAS.md) — every non-obvious failure mode + root cause + fix, written after hitting them in production.

Quick links:
- **G1**: Font name vs family (Inter Variable ≠ Inter)
- **G2**: soffice ≠ PowerPoint (always sanity-check in PowerPoint)
- **G3**: DPI consistency for PNG comparison
- **G4**: `line_spacing` only works with correct fonts
- **G5**: CSS color-mix returns oklab — normalize via canvas
- **G6**: `isInlineOnly` tag-name based, not CSS-display based
- **G7**: h3 numbered markers (skip decoration, recolor text)
- **G8**: object-fit:contain — manual letterbox math
- **G9**: hyphens:auto via pyphen + U+00AD
- **G10**: `::marker` is generated content — use OOXML native bullets
- **G11**: Mac PowerPoint needs fonts installed too
- **G12**: Variable fonts confuse fontconfig — use static weights
- **G15**: `<img>` decoration tile must render under picture (white tile under transparent logos)
- **G16**: Single-word short text → set `word_wrap=False` (ICLR/ICML badges)
- **G17**: `::before`/`::after` invisible to DOM walkers — fetch via `getComputedStyle(el, '::before')`
- **G18**: Vision audit false-positive: LEFT-aligned in wide bbox looks centered

## Dependencies

| Package | Purpose |
|---|---|
| playwright | chromium for DOM extract |
| python-pptx | OOXML construction API |
| lxml | direct OOXML when python-pptx lacks (gradients, shadows, bullets) |
| Pillow | image decoding + text measurement |
| pdf2image | PDF → PNG preview |
| pyphen | CSS hyphens:auto soft-hyphen insertion |
| cairosvg | rasterize SVG `<img>` to PNG before embed (PIL can't decode SVG) |

Optional (for `--vision-audit`):
| ANTHROPIC_AUTH_TOKEN | Claude API auth for vision diff |

For verification:
| | |
|---|---|
| libreoffice | PPTX → PDF via soffice |
| poppler-utils | pdf2image's binary backend (`pdftoppm`) |

## Roadmap

- **Phase 3** (TBD): web-font embedding in pptx (`ppt/fonts/*.fntdata` + `embeddedFontLst`). Eliminates the Mac/Win "missing fonts" issue at the cost of ~3 MB per pptx.
- **Phase 4** (TBD): PNG fallback for unsupported subtrees (KaTeX math, complex SVG, CSS transforms).
