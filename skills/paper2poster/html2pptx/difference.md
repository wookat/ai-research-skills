# Why html2pptx beats generic PDF→PPTX converters

Compared to web tools (iLovePDF, Smallpdf, Adobe converter, etc.) that work by **rasterizing a PDF and OCR-ing text back into shapes**, html2pptx walks the **live DOM** of an HTML page. That gives us first-class access to the design's semantic structure, not just pixel groups. Concrete consequences:

---

## 1. Inline text backgrounds = real text property, not floating shape

**Generic converter**: An inline `<span style="background: yellow">` becomes a separately-positioned yellow Rectangle behind the text, with the text on top as a different shape.
- ❌ Drag the text → the yellow Rectangle stays put, leaving an orphan color block.
- ❌ Edit the text → the Rectangle is the wrong width.
- ❌ Resize → text reflows, but the colored block does not.

**html2pptx**: Detects `display: inline` + `background-color` and emits OOXML `<a:rPr><a:highlight>` (PowerPoint's *Text Highlight Color*, the same property you'd set via the ribbon).
- ✅ Drag → highlight moves with the text.
- ✅ Edit → highlight extends/shrinks with the glyphs.
- ✅ The text is one run, one inline property — no orphan blocks.

---

## 2. Lists stay as ONE list, bullets stay as bullets

**Generic converter**: A `<ul>` with 4 `<li>` items becomes:
- A column of bullet glyphs (•, •, •, •) as one shape.
- The 4 lines of text as a separate shape (often one text-box per line, all flat).
- The bullet glyphs are **decorative text, not list markers**.

What breaks:
- ❌ Drag the text → bullets stay behind.
- ❌ Press Enter inside a paragraph → no auto-bullet on the next line (it's not a real list).
- ❌ Indent / outdent buttons do nothing.
- ❌ Reorder by dragging — bullets and text desync.

**html2pptx**: Detects `<li>` and emits OOXML `<a:buChar char="•"/>` with `marL` + negative `indent` (PowerPoint's *hanging-indent list*). Bullet color = section accent via `<a:buClr>`.
- ✅ One textbox per list item — each editable individually.
- ✅ Bullets are PPT-native list markers — Enter creates a new bullet, Tab indents.
- ✅ Drag a paragraph — its bullet follows.
- ✅ Reordering preserves bullet styling.

---

## 3. Bold ≠ different font

**Generic converter**: When part of a paragraph is `<strong>`, the converter often:
- Treats it as a separate text element ("bold-style spans don't have continuous baseline with the surrounding regular text" — they don't, because reverse-engineered from rendered pixels).
- Picks a different font that "looks like the bold weight" (Helvetica Bold instead of Inter Bold), so a single sentence ends up in two visually similar but different families.
- Splits the paragraph into multiple shapes at every bold-run boundary.

**html2pptx**: Walks the DOM in BLOCK-level passes (one textbox per `<p>`/`<li>`/`<h*>`) and inserts each `<strong>`/`<em>`/inline child as a typed `Run` inside the SAME paragraph.
- ✅ One textbox per block; one paragraph; bold is just `<a:rPr b="1">` on a sub-run.
- ✅ Same font family across the whole paragraph — bold uses the same family's bold weight, not a substitute.
- ✅ Editing the text auto-reflows everything as a continuous paragraph; bold runs stay bold inline.

---

## Other things we get right that pixel-based converters can't

### Native element types preserve semantics
| HTML construct | Pixel-converter output | html2pptx output |
|---|---|---|
| `<img>` | Cropped raster region | `<p:pic>` (PowerPoint Picture) — replaceable, resizable, real image |
| `<sup>` / `<sub>` | Smaller text at wrong baseline | `<a:rPr baseline="30000">` (PowerPoint's Superscript text style) |
| `linear-gradient(...)` background | Flattened to RGB rectangle | `<a:gradFill>` with `<a:gsLst>` — editable gradient stops |
| `box-shadow` | Often dropped | `<a:effectLst><a:outerShdw>` — editable shadow effect |
| `border-radius: 4px` | Approximation | `prstGeom roundRect` with explicit adj — exact corner radius |
| `border-bottom: 2px solid` | Often dropped (one-sided borders) | Per-side thin Rectangle, exact color + width |
| `text-transform: uppercase` | Text frozen as uppercase glyphs | Source text stays original; uppercase applied via PPT text-transform (preserves "edit me" intent) |
| `hyphens: auto` | Frozen wrap with hard breaks | Soft hyphens (U+00AD) inserted via `pyphen` — PPT wraps with hyphenation |
| `<table>` | Bitmap region or flat text | (Currently text-as-text in textboxes; PPT-native `<a:tbl>` is roadmap) |

### Coordinate space, not pixel space
- Generic converters infer positions from pixels → 0.5pt off here, 1pt off there.
- We use browser-computed `getBoundingClientRect()` → exact CSS pixel positions, then proportional conversion to EMU. No accumulation drift.

### Color fidelity
- Pixel converters work in screen sRGB. Source CSS often has `color-mix(in oklab, ...)`, `color(srgb ...)`, `hsl()` — these are computed by the browser to sRGB by us via a 1×1 canvas (`ctx.fillStyle = anyColor; getImageData()`) before we send them to PPT. Generic converters that don't understand CSS color models can drift.

### Font fidelity (when reference PDF is present)
- We auto-detect a sibling `poster.pdf` and extract its `pdffonts` output. The font names in our PPT match the reference PDF's font set, so a coworker comparing to the PDF doesn't see two different things.

### Auto-detection of canvas size
- Pixel converters assume the input PDF's first-page size is what you want.
- We parse `@page { size: ... }` from the source CSS and use the designed canvas — so a 60×36" academic poster ends up as a 55×33" PPT slide (capped to PPT's 56" max) with everything scaled proportionally, not jammed into a 10×7.5" default.

---

## What we lose vs. pixel converters

Honesty: pixel-based converters DO have a few edges:
- They work on any PDF, even ones with no recoverable source. We require HTML.
- They handle KaTeX/MathJax/SVG math gracefully (everything's a pixel anyway). We currently rasterize-fallback only conceptually — math equations need work (Phase 4).
- They handle complex CSS transforms (rotate, skew, 3D) by snapshot. We don't transform shapes yet.

So: if you have the HTML source, use us. If all you have is a final PDF and you don't care about post-edit semantics, use a pixel converter.
