# GOTCHAS — html2pptx

Failures we hit in production. Each has: symptom → root cause → fix → why.

If you hit something not on this list, append it here.

---

## G1: Font name vs family ("Inter Variable" ≠ "Inter")

**Symptom**: PPT text looks blocky / monospace-ish. fc-match "Inter" returns DejaVu Sans.

**Root cause**: `InterVariable.ttf` registers under fontconfig family name "Inter Variable", not "Inter". When PPT requests "Inter", fontconfig has no match → falls back to a default sans (DejaVu Sans on Linux, ~Calibri/Helvetica on Mac/Win). Same for Source Serif 4 variable.

**Fix**: install **static-weight** TTFs (Regular / Medium / SemiBold / Bold + italics), not variable. Confirm with:
```bash
fc-match "Inter" "Source Serif 4" "JetBrains Mono"
# Each MUST return the font itself, not a fallback
```

**Why**: variable fonts' OS/2 family naming is a known fontconfig friction point. Static weights register with the canonical family name.

---

## G2: soffice ≠ PowerPoint

**Symptom**: pptx looks fine via `soffice → PDF → PNG`, looks broken when opened in Mac/Win PowerPoint.

**Root cause**: different rendering engines diverge on:
- font fallback (when font isn't installed)
- shadow blur radius
- linear gradient interpolation
- text shaper / kerning
- character spacing

**Fix**: always sanity-check the final `.pptx` in **actual PowerPoint** (or Keynote). Soffice PNG is for quick iteration only.

**Why**: soffice/LibreOffice has its own OOXML interpreter. It's "close enough" but not byte-identical to MS PowerPoint.

---

## G3: DPI mismatch creates fake "font is smaller" bug

**Symptom**: PPT text looks 16% smaller than HTML text when viewing PNGs side by side. User thinks font size is wrong.

**Root cause**: HTML render PNG is at 96 DPI (playwright default → 4494 px wide for A0). PPT render PNG via `pdf2image.convert_from_path(dpi=80)` is 3760 px wide (80 DPI). Same physical font (24pt) takes proportionally fewer pixels at lower DPI → looks smaller when viewed at 1:1 pixel scale.

**Fix**: always render PPT preview at `dpi=96` to match playwright. Physical font size on A0 paper is identical regardless.

**Why**: PNG size = (inches × DPI). Comparing PNGs at different DPIs always shows a relative-size discrepancy that isn't real.

---

## G4: `line_spacing` only helps when correct fonts are installed

**Symptom**: setting `paragraph.line_spacing = Pt(css_lh)` made text overlap WORSE in early iterations.

**Root cause**: PPT was using DejaVu Sans fallback (wider per char). Setting line_spacing to CSS line-height value (which assumed Inter metrics) caused text to wrap to extra lines and overflow.

**Fix**: install correct fonts FIRST (G1). THEN enable line_spacing. PPT's default single-spacing uses `1.0 × font natural line height`, which for Inter at 24pt is ~29pt — short of CSS 1.36×24pt=32.6pt. Each block under-fills its bbox, accumulating ~10-20px trailing whitespace that visually widens paragraph gaps. Setting `line_spacing = Pt(lh_pt)` matches CSS exactly.

**Why**: line_spacing semantics depends on font metrics; "right" value depends on which font actually renders.

---

## G5: CSS `color-mix()` and modern color spaces

**Symptom**: callout boxes / panel-groups appear with no background color in PPT (look white). Border colors missing too.

**Root cause**: Chrome 120+ resolves `color-mix(in oklab, ..., ...)` to `oklab(L a b)` or `color(srgb r g b)` strings. Python `_parse_color()` regex only understood `rgb()` / `rgba()` / `#hex`. → returned None → has_decoration returned false → box never drawn → callout looks unstyled.

**Fix**: in JS extract, normalize every CSS color through a 1×1 canvas (`ctx.fillStyle = anyColor; ctx.fillRect(); getImageData()`) to get a guaranteed `rgba(r, g, b, a)` string. Browser already knows how to resolve any color format.

**Why**: writing a CSS color parser that handles every modern color spec is a rabbit hole. The browser already has one — let it do the work.

---

## G6: `isInlineOnly` is tag-name based, NOT CSS-display based

**Symptom**: Two failure modes from different attempts:
- Tag-name only check → figure-wrap div containing img + caption div was emitted as text block; full caption text painted across the entire figure area (phantom text above figure).
- CSS-display check → h3 with `display: flex` and a `span.num` (display: block) child → h3 marked "has block descendants" → h3 text never emitted → all 6 section titles disappeared.

**Root cause**: CSS display is too aggressive (any styled-as-block child kills emission). Tag name is too narrow (misses divs).

**Fix**: tag-name based check with expanded BLOCK_LAYOUT_TAGS set including div, figure, section, header, footer, nav, main, aside, article, table, etc. — a `<span>` is inline-flow even with `display:block`; a `<div>` is block-flow even with `display:flex`.

**Why**: HTML semantic tags carry the "is this a block container" intent; CSS display is presentational and can be overridden in either direction.

---

## G7: Section h3 with numbered marker (span.num)

**Symptom**: section banner shows colored square overlapping the title text; the digit "1" is invisible (orange on orange).

**Root cause**: template uses `<h3><span class="num">1</span>Motivation</h3>` where span.num is a CSS-styled circle with `display:block`, `background: section-color`, color: white. In PPT:
- span.num emits as a small colored rectangle at its bbox
- h3 textbox contains runs `["1" (orange), "MOTIVATION" (white)]` — "1" is invisible against orange banner
- → user sees rectangle + invisible digit + visible title = "squished mess"

**Fix**: 
1. Mark elements with `inside_heading=true` if any ancestor is h1-h6
2. Skip decoration emission for inside_heading elements (no rectangle)
3. In heading text blocks, override all run colors to use the heading's own color (white)
4. Insert space separator between runs from different element boundaries: "1MOTIVATION" → "1 MOTIVATION"

**Why**: CSS-styled circular markers can't be cleanly replicated in PPT shape primitives. Per user preference: "delete the circle, keep the digit with the title".

---

## G8: `object-fit: contain` on images

**Symptom**: figures look stretched / squashed in PPT compared to HTML. Aspect ratio is wrong.

**Root cause**: passing the IMG's bbox directly to `add_picture(width=bbox_w, height=bbox_h)` forces the image to fill that bbox. Browser actually letterboxes the image inside the bbox via `object-fit: contain`, preserving aspect ratio.

**Fix**: extract `naturalWidth`, `naturalHeight`, `cs.objectFit` in JS. When `object_fit == "contain"`, compute the contained dimensions:
```python
nat_ratio = nat_w / nat_h
bbox_ratio = bbox_w / bbox_h
if nat_ratio > bbox_ratio:  # wider than bbox: fit by width, letterbox top/bottom
    px_w, px_h = bbox_w, bbox_w / nat_ratio
else:  # taller: fit by height, letterbox left/right
    px_h, px_w = bbox_h, bbox_h * nat_ratio
off_x, off_y = (bbox_w - px_w)/2, (bbox_h - px_h)/2
```
Place picture at (bbox_x + off_x, bbox_y + off_y) with size (px_w, px_h). The wrap container's gray bg shows in the letterbox gap — matches HTML.

**Why**: PPT has no built-in object-fit; we replicate the math.

---

## G9: CSS `hyphens: auto`

**Symptom**: long words like "temperature" wrap whole-word to next line in PPT but break as "tempera-ture" in HTML → cascading spacing differences.

**Root cause**: browser uses libhyphen with language dictionary to break long words at syllable boundaries when wrap forces it. PPT's line breaker only breaks at whitespace — long words go whole-word to next line.

**Fix**: pyphen library + OOXML soft hyphens.
1. Detect `cs.hyphens == "auto"` per text block
2. Before sending text to PPT, run each long word (≥7 chars) through `pyphen.Pyphen(lang="en_US").inserted(word, "­")`
3. PPT and soffice both honor U+00AD soft hyphens: invisible until wrap, then visible as "-"

**Why**: OOXML supports the same soft-hyphen concept as CSS hyphens; pyphen provides the syllabification dictionary the browser uses internally.

---

## G10: `<li>` `::marker` is generated content

**Symptom**: bullet points (•) all missing from PPT.

**Root cause**: CSS `::marker` is a pseudo-element. Its content is NOT in `element.textContent` and isn't part of any DOM node. Collecting runs from `<li>` gives only the visible text, no bullet.

**Fix**: tag `is_list_item=true` in extract. In PPT generation:
- Extend the li textbox LEFT by the parent ul/ol's `padding-left` (so bullet sits in marker area, not in li content)
- Add OOXML native bullet: `<a:buFont typeface="Arial">` + `<a:buChar char="•">` + `<a:buClr>` with first-run color
- Set hanging indent: `pPr.set("marL", shift)` and `pPr.set("indent", -shift)` — bullet at left edge, wrap-text aligned with first-line content

**Why**: native OOXML bullets render properly in PowerPoint and respect color/font. Prepending "•  " to text would put bullet at wrong x position.

---

## G11: Mac PowerPoint also needs fonts

**Symptom**: pptx renders correctly via soffice on Linux, but a different team member on Mac opens it and everything looks wrong.

**Root cause**: pptx file says "use Inter" but doesn't INCLUDE the Inter font. PowerPoint on the viewer's machine falls back to whatever's installed (Helvetica / Calibri / Arial). Character widths differ from Inter → text wraps differently → cascading layout errors.

**Fix**: until font embedding is implemented (Phase 3 roadmap), **every viewer of the pptx must install the same fonts on their machine**. Provide the install commands in your hand-off.

**Why**: pptx font references are by name only. Without embedded font tables, viewer's OS supplies the actual font data.

---

## G12: Variable fonts confuse fontconfig

(Same root cause as G1, restated as a standalone gotcha.)

`fc-match "Inter"` against an installed `InterVariable.ttf` returns DejaVuSans because variable fonts register under a different family name ("Inter Variable" suffix). 

**Always install static-weight TTFs**. Don't trust "variable fonts are universally supported" — fontconfig matching is the bottleneck, not the rendering engine.

---

## G13: PIL line-height estimate vs actual PPT render

**Symptom**: L2 closed-loop's PIL measurement marks blocks as overflowing when they actually fit, leading to unnecessary font shrinking.

**Root cause**: `auto_correct_loop.py` uses `line_h = font_size_pt * 1.30 * 96/72` as the line-height estimate. Actual PPT line-height depends on the font's natural metrics, which can be anywhere from 1.15× to 1.40× of font size depending on the family.

**Fix**: tune the threshold. Current default: only shrink if overflow > 1.05× (5% margin). Raise to 1.10 if you see false positives. The 5% threshold catches real overflow without over-shrinking.

**Why**: PIL doesn't know which line-height PPT will use. The estimate is a heuristic; we tolerate small misalignment.

---

## G14: `MSO_AUTO_SIZE` and trailing whitespace

**Symptom**: tried disabling auto-resize (`MSO_AUTO_SIZE.NONE`) thinking it would prevent overflow. Made overlap worse.

**Root cause**: with proper fonts installed, text under-fills its bbox. AUTO_SIZE.NONE pins the textbox to bbox dimensions but doesn't change where text sits within it. The next textbox is still at its own bbox y, so paragraph gaps widen (G4 cause).

**Fix**: leave auto_size at default (text shrinks shape) AND set `line_spacing = Pt(css_line_height)` to fill bbox naturally. Don't fight the layout — match it.

**Why**: PPT's text fitting is sensible by default. Setting `line_spacing` to match CSS makes the text fill the browser-measured bbox correctly.

---

## G15: `<img>` decoration tile must render UNDER the picture, not after

**Symptom**: Transparent-PNG logos (Microsoft Research wordmark, etc.) on a colored banner look like only fragments of text — vision audit reports "Microsoft Research logo missing, only 'Research' faintly visible."

**Root cause**: CSS often gives logos a white tile via `.logo { background: white; padding: 10pt 14pt; border-radius: 8pt }`. The early img-branch in `build_pptx` just emitted `Picture` and returned, skipping the decoration code. Picture sits on the section background → transparent text disappears into red/blue banner.

**Fix**: in img branch, FIRST emit a Rectangle/RoundedRect with the element's `bg_color` + `border_radius` + border (if `has_decoration(el)`), THEN add the Picture sized inside `bbox - padding` so it doesn't break out of the tile edges. Also extract padding for elements (was previously only extracted for text_blocks).

**Why**: PPT z-order = shape add order. Tile must be added BEFORE picture. Picture must be sized to the padded content area, not the full bbox.

## G16: Single-word short text in tight bbox → PPT char-wraps when browser didn't

**Symptom**: 4-letter conference badges ("ICLR" / "ICML") render as "ICL\nR" in PPT — second-line "R" visually collides with the year text below.

**Root cause**: PPT's auto-wrap uses font shaper that gives slightly wider character advance than the browser. For a tight 4-char box at large font (88pt), the difference pushes the last char to a new line. PPT falls back to character-level wrap when there's no whitespace to break on.

**Fix**: in build_pptx, detect short single-word blocks (joined run text has no spaces AND ≤6 chars) → set `text_frame.word_wrap = False`. Browser already proved the word fits the bbox; force PPT to honor it instead of breaking.

**Why**: with `word_wrap=False`, PPT overflows horizontally rather than char-breaking. For short tight badges this looks identical to browser. For long text it would cause clipping — that's why the heuristic restricts to ≤6 chars single-word.

## G17: CSS `::before`/`::after` pseudo-element content is invisible to DOM walkers

**Symptom**: A `.conclusion::before { content: "So what →" }` callout that prefixes every Key Results paragraph vanishes from the PPT — vision audit reports "SO WHAT label absent in 6 posters."

**Root cause**: `document.querySelectorAll('*')` and `el.childNodes` only iterate REAL DOM nodes. Pseudo-elements are rendering-layer constructs with no DOM presence. `getComputedStyle(el).content` returns `"normal"`; you have to call `getComputedStyle(el, '::before').content` to get the generated string.

**Fix**: at the start of `collectRuns(el, runs)`, fetch `::before` via the 2-arg getComputedStyle and push as a synthetic run (inheriting pseudo's font/color/transform). Same for `::after` at end. Decode CSS `\xxxx` unicode escapes (e.g. `\2192` → `→`).

**Why**: per-run text-transform override is needed too — `::before { text-transform: uppercase }` should not inherit the paragraph's default `none`. Each run's `text_transform` field is now checked before falling back to block-level.

## G18: Vision audit false-positive: LEFT-aligned text in wide bbox looks centered

**Symptom**: Vision audit reports "Method heading is center-aligned in PPT, left-aligned in HTML" across all 9 posters — but DOM data shows `text_align='start'` for ALL h2 headings.

**Root cause**: When a section spans the wide middle column of a 1fr/2.4fr/1fr grid, its h2 bbox is ~2.5× wider than side-column h2s. LEFT-aligned text in that wide box starts at the box's left edge, which happens to fall near the visual CENTER of the whole poster (because the column itself is in the middle). Vision compares position relative to the poster's center axis, not relative to the box's own edge.

**Fix**: not a code bug — keep `text_align` as-is. When reading vision audit reports, cross-check `alignment_off` findings against the DOM's text_align field before treating them as actionable.

**Why**: the audit prompt could in principle be improved to make vision compare WITHIN the bbox, but the current prompt is already constrained and adding more conditional reasoning often degrades the high-value findings. False positives in low-stakes category are acceptable; the workflow is human-review-then-fix anyway.

## G19: Native OMML slide-math (`<a14:m>`) renders BLANK outside Microsoft PowerPoint

**Symptom**: a display equation (e.g. `0.90 ≤ h_content/h_slide ≤ 1.00`) is present in the `.pptx` and shows fine in real PowerPoint, but the callout box top is empty white in the soffice-exported PNG (and in Keynote / Google Slides / most previewers).

**Root cause**: Pass-3 converts MathJax `data-tex` → MathML → OMML and injects it wrapped in `<a14:m>` (the DrawingML-2010 slide-math extension). Only Microsoft PowerPoint rasterizes `a14:m`; LibreOffice/soffice ignores the extension, so the equation is invisible in every soffice-based render and any downstream PNG.

**Fix**: rasterize each equation region to a PNG during extraction (while the page is still open) and emit that PNG as a `Picture` in Pass-3, `continue`-ing PAST the OMML branch so they never double-draw. The screenshot is taken from the browser-rendered MathJax via `page.screenshot(clip=<mjx bbox>)`; the browser context is opened with `device_scale_factor=2` so the raster is crisp (this only affects rasters — `getBoundingClientRect` stays in CSS px, so no element geometry shifts). A PNG renders in ALL viewers. The OMML path still runs when no raster was captured (e.g. `latex2mathml`/`mathml2omml` present but the screenshot failed), so nothing regresses.

**Why**: universal visibility beats the "editable native math" affordance for a poster deliverable — nobody edits equations in a rendered A0 poster, but everybody's previewer must show them. The raster is the source of truth; OMML is the fallback, not the reverse.

**Test caveat**: this (and all logo/QR/figure emission) can only be validated on an ASSET-INTACT bundle. A stripped delivery folder (top-level deliverables only, `assets/` removed) has dangling `<img src="assets/...">`, so logos/QR/figures silently drop and every render looks broken. Always rebuild the `.pptx` from the generation dir where `assets/logos`, `assets/qr`, `assets/figures` still exist, NOT from the shipped bundle. (The equation raster is the exception — it is a screenshot of browser-rendered MathJax, which is CSS/JS, so it survives even when `assets/` is gone.)

## G20: Table row hairline separators vanish below the 1px EMU floor

**Symptom**: HTML data tables (Key Results) show thin `border-bottom` rules between rows; in the PPT render only the header shading survives and the per-row hairlines are faint or gone.

**Root cause**: each `td`/`tr` bottom-border is emitted as a thin filled Rectangle. After the OOXML-clamp `slide_scale` shrink, a 1px CSS hairline maps to sub-pixel EMU height; soffice rounds it to nothing on some rows.

**Fix**: floor the thin dimension of every per-side border rect to ~1.3px in the ORIGINAL coordinate space before EMU conversion — `ex_h = max(ex_h, int(emu_y(sy + 1.3) - ex_y))` for top/bottom sides, the `emu_x` analogue for left/right — then `max(1, …)` the EMU as a final backstop.

**Why**: a hairline must stay ≥1 rendered pixel at the final raster DPI or it disappears; flooring in source-px space keeps it proportional across canvas sizes instead of hard-coding an EMU constant.
