# Visual polish reference

Layered visual polish for the rendered `poster.html` so it reads from a few meters away and looks publication-grade up close. Read this when you reach **Step 7 — Polish** in `SKILL.md`. These rules are layered on top of the base template — do not restructure the grid.

## Typography & hierarchy

- Body font stack: `Inter, "Helvetica Neue", Arial, sans-serif`. Reserve weight 700–800 for `<h1>` and `<h2>`.
- Title (`<h1>`): 44–56pt, line-height 1.05, no all-caps.
- Authors: 18–22pt, muted gray `#555`.
- Institutes: 14–16pt, italicized, lighter gray `#777`.
- Section headers (`<h2>`): 22–26pt, bold, 4px-thick left border in the chosen accent color, 8px left padding.
- Body: 14–16pt, line-height 1.45, color `#1a1a1a` (not pure black). Bullets use `•`, 8px between items.

## Color & contrast

- Page background: off-white `#fafaf7`. Section cards: pure `#ffffff`, **1.5px theme-accent border** (thicker 5px on the left chip), 8px border-radius. All cards share one border color.
- `<h2>` has **no background fill**. The text uses the theme accent color; the divider beneath is a 2px line in the accent at ~30% alpha (`color-mix(in srgb, var(--accent) 30%, transparent)`).
- The **theme color** (one of 5 deep-academic themes, applied deterministically by `apply_theme.py`) owns the chrome: outer poster frame, title bar, Full Listen button, all card borders, all `<h2>` text + underlines.
- The **per-section accent** is reserved for the small per-section Listen button only. Body text stays `#1a1a1a` — do not tint paragraphs or bullets per section.
- The `{{HEADLINE_DELTA}}` callout uses the **theme color**. The `.stat` values and borders use **`--callout` red `#ae2622`** — the loudest content on the poster gets its own "this is the result" register, distinct from both chrome and inline body emphasis.
- WCAG AA: heading text on the soft accent band must stay ≥4.5:1 with the default palette. If you introduce a new section color, verify both heading-on-band and chip-on-white pass.

## Inline emphasis — guide the reader's eye

A passerby reads in *seconds*, not minutes. They scan for the most important phrase, latch onto it, and decide whether to keep reading. Make that phrase impossible to miss.

The templates provide three inline tools, all tinted with a single shared highlight color — strong near-black (`--highlight-accent: #111111`, soft band `--highlight-soft: #ececec`). Black (not a colored accent) is deliberate: on a white poster, the most important phrases — the method name, the headline numbers, the key claim — *should be the boldest, darkest ink*, not a colored decoration. Color competes with the chrome; black wins by being more weight than body text without adding a new hue. The reader's eye learns *"the darkest, heaviest thing on the card is the point of this section"* once, and that lesson works across all eight sections.

| Element | Use for | Visual |
|---|---|---|
| `<strong>` / `<b>` | The 2–5 most important nouns/phrases per section — names, key concepts, distinguishing terms (e.g., **dual-view**, **incremental updates**) | Bold + near-black highlight |
| `<span class="hi">…</span>` | The *one* sentence-level claim that, read alone, gives the section's punchline | Pill highlight: soft gray bg + near-black text |
| `<span class="num">…</span>` | Numeric callouts in prose — percentages, deltas, factors | Slightly larger, bold, tabular-nums |

### Discipline rules (over-highlighting is worse than none)

- **Plaintext-only scope — the most important rule.** These three tags are **only for plain body prose** inside `<p>` paragraphs and `<li>` items that sit directly in a `.section`. **Never wrap them inside any accent component**, including:
  - `.callout` and `.callout.callout-bar` (the `{{HEADLINE_DELTA}}` pill, Takeaway bar)
  - `.stat .val` and `.stat .lbl` in the Headline Numbers grid
  - `.arch-row`, `.arch-label`, `.arch-body` banners
  - `table.results` cells (header, body, "Ours" row)
  - `.conclusion` "So what →" lines
  - `<h2>` section headers, `<figcaption>`, `.titlebar`

  These components already carry their own typographic emphasis. Layering `<strong>` or `.hi` on top creates double-emphasis that fights itself: a pill-inside-a-pill reads as noise instead of focus. Inline emphasis *creates* a focal point inside flat prose; if the surrounding element is already a focal point, leave its text plain.

  Concrete examples:
  - Headline delta: `+14.4 pts Acc@5 over OrcaLoca` ✅ — not `+<span class="num">14.4</span> pts <strong>Acc@5</strong> over OrcaLoca` ❌
  - Stat label: `Acc@5 SWE-bench` ✅ — not `<strong>Acc@5</strong> SWE-bench` ❌
  - Takeaway in `.callout.callout-bar`: write the sentence plain — the bar is the emphasis
  - Table cell: `93.7% Acc@5` ✅ — not `<span class="num">93.7%</span> Acc@5` ❌
- **One `.hi` per section, max.** Two pills cancel each other out. If a section has two equally-important sentences, pick one and use `<strong>` for the other's key noun.
- **2–5 `<strong>`s per section.** Bold every important *term*, not every important *word*. If everything is bold, nothing is.
- **`<span class="num">` for every standalone number in body prose** that's part of the paper's story. In accent components the styling is already handled — don't wrap there.
- **Don't use bold for category labels** ("Encoding:", "Method:") starting a bullet — those are structural, not semantic.
- **Highlights compose inside prose only**: a number inside a highlight is fine (`<span class="hi">reaches <span class="num">93.7%</span> Acc@5</span>`) when the surrounding context is plain prose, but don't nest two `.hi`s and don't compose inside any accent component.

When in doubt: re-read the section's `Necessary` text. Whatever sentence captures the *single most surprising or decisive fact* is your `.hi`. Whatever 2–4 proper-noun-ish phrases anchor it are your `<strong>`s. Whatever numbers do the heavy lifting are your `.num`s.

## Stat / Headline Numbers grid

- **Maximum 2 stats per row.** Both templates set `grid-template-columns: repeat(2, 1fr)`. With 1–4 Headline Numbers this gives a 1×N (1 stat), 1×2 (2 stats), 2-then-1 (3 stats), or 2×2 (4 stats) layout — every `.val` stays large enough to read across a poster hall. Packing 3–4 stats into one row shrinks the value font past the legibility threshold; the whole point of the Headline Numbers card is that *the numbers themselves are the visual*, so column count is fixed at 2 and never widened to fit more stats per row.
- Each `.stat`: large value (42–56pt, bold, **`--callout` red**), label below (12–14pt, uppercase, letter-spacing 0.05em, gray `#555`). Card border also `--callout` red — each stat reads as a self-contained results chip.
- Center-align values and labels. Thin 1px divider between stats, or equal-gap flexbox.
- `{{HEADLINE_DELTA}}` renders as a pill: accent background 15% opacity, accent text, 6–10px padding, 999px border-radius, bold.

## Method figure

- Constrain figure height: `max-height: 38vh` for half-template, `max-height: 32vh` for full-template; `width: 100%`; `object-fit: contain`; centered.
- White figure background, 1px `#e5e5e0` border, 4px border-radius. Caption below in 12–13pt italic, gray `#555`, max 2 lines.
- **Cap the FIGURE, not the IMG.** The cap belongs only on `.method-figure` / `figure`. Inside it the `<img>` must be a flex child that shrinks (`flex: 1 1 auto; min-height: 0; max-height: 100%`), and `<figcaption>` must be `flex: 0 0 auto`. If you also cap the `<img>` at the same vh value as the figure, the image consumes the entire figure height and the figcaption gets evicted below the section's bottom border — the bundled templates already have this fixed, so don't "simplify" the rules back. `overflow: hidden` on `figure` is a belt-and-braces guard against residual overflow.
- **Method figure layout is aspect-matched.** In `poster_full_template.html` the Method bullets + figure live in a `.method-body` wrapper, and the on-load `orientMethod` script picks the arrangement from the figure's aspect ratio. A figure **stacks** (bullets on top, figure spanning the full column width below) unless it satisfies **three** conditions: it is portrait (`w_fig/h_fig < 1`) **and** narrower than its stacked slot (`w_fig/h_fig < w_slot/h_slot`, where `h_slot` is the column's vertical budget — column height minus the bullets and sibling cards) **and** the bullets' ~42% share of the row still clears a **readable-width floor** (`min-width: 22em`). Only then does it flip to `.method-horizontal` — a side-by-side row with bullets (~42%) left and figure (~58%) right, so the portrait figure gets a taller slot it fills on **height** instead of painting narrow with a tall band of side gutters. Landscape figures always stack: the row can't widen a wide image and would leave a void beneath it when the bullets wrap taller than the figure. **The bullet-width floor is the third guard:** if the Method column is narrow (a slim template column, or a column-width nudge), 42% of the row can fall below a comfortable text measure and collapse the bullets into a 2–3-word-per-line ribbon — worse than stacking. When that floor isn't met, `orientMethod` vetoes the flip and the body stays stacked, because a full-width figure with bullets above always out-reads starved side-by-side text. This is policy-consistent with the **width-or-height fill rule** (every figure fills 90–100% of its slot on at least one axis): a stacked figure fills width, a side-by-side portrait figure fills height. `fit()` then sizes the image within whichever orientation `orientMethod` chose. Don't hand-toggle `.method-horizontal` — let the script decide. If you change the `min-width: 22em` CSS floor, keep `MIN_BULLET_W` in the footer's `orientMethod` in sync.

## Tables

- `.results` table: full column width; header row uses accent-tinted background and bold text; alternating row stripes `#fafaf7`; 8–10px cell padding; right-align numeric columns; "Ours" row bolded with accent text on the metric cell.

## Section callouts — for mic-drop sentences

The templates ship a `.callout` pill (used by default under Key Results for `{{HEADLINE_DELTA}}`) and a `.callout.callout-bar` variant (left-aligned, 4px accent bar). Either can be appended inside *any* `.section` to give that section a one-line punchline below its body. Use sparingly — for the 1–2 sections where a single sentence captures the whole point and deserves to be shouted.

**When to add:**
- **Takeaway** — if its `Necessary` itself is the mic-drop, render as `<div class="callout callout-bar">` instead of plain `<p>`. The bar reads as narrative emphasis rather than a results pill.
- **Problem** — if Problem is one strong claim and the column has room, render as `.callout.callout-bar`.
- **Method / Ablation** — if there's a single "thing that matters" sentence beyond the bullets (e.g., "Cost scales with diff size, not repo size."), append a centered `.callout` below the bullets/figure.
- **Key Results** — the default `{{HEADLINE_DELTA}}` pill already covers this; don't add a second.

**When NOT to add:**
- The section is already dense (bullets + figure + body) — trim or skip.
- The punchline is just a restatement of what `<span class="hi">` is doing inline.
- The `Necessary` is a list of separate ideas — callouts work only for one-sentence claims.

Keep callouts ≤14 words. Long callouts wrap to 2–3 lines and lose the punch.

## Arch — layered architecture stacks

The templates ship an `.arch` component (vertical stack of full-width `.arch-row` banners, each optionally prefixed with a small uppercase `.arch-label` tier name; rows tinted progressively darker top→bottom so the stack reads as layers). Use inside any section — most naturally **Motivation** — when the section's logic is a *layered architecture* or *tiered stack*: "data layer → model layer → agent layer", "raw repo → encoded RPG → operating agent". Stacked banners do in one glance what a bullet list does in three lines.

**When to add:**
- **Motivation** — the prototypical slot. If the motivation frames the work as a stack, 2–4 arch rows show that instantly.
- **Method** — only if best understood as a layered stack and the Method figure is `none` or weak. The figure is the canonical visual; don't compete.
- **Problem** — to show a broken stack (a missing middle layer) when the failure mode is architectural.

**When NOT to add:**
- Rows are a strict left-to-right sequence (a → b → c). That's a flow, not a stack.
- A flat set of unordered properties — that's a bullet list.
- More than 4 rows — too dense; tighten or use prose.
- Rows are full sentences — banners lose punch above ~6 words. Shorten or skip.
- The Method figure already shows the same stack.

Row naming: 1–4 word noun phrase in `.arch-body`, optional 1-word `.arch-label`. Think labels on an architecture diagram. Examples: `Agent` / `Dual-view RPG` / `Code`; `Query` / `Index` / `Storage`; `Intent` / `Plan` / `Implementation`. The progressive tint is automatic via `:nth-child` — order rows top-to-bottom from most abstract to most concrete.

## Spacing & rhythm

- Outer page padding: 32–40px. Column gap: 24–28px. Vertical gap between cards within a column: 18–22px. Card internal padding: 16–20px.

## Widow lines — last-line stranded word

A multi-line `<p>` or `<li>` whose **last visual line wraps to only 1–2 words** reads as broken typography even when every layout gate passes — the trailing word sits stranded in whitespace, looking like a half-finished thought. This is a separate problem from orphan glyphs (`↑`, `×`) and from the "trailing whitespace at card bottom" gate; it's specifically about *line-shape inside a paragraph*.

The polish gate (`check_poster.py polish`) flags this automatically as `WIDOW: <p|li> last line is only N% of element width ...` whenever the last line takes <20% of the element's content width. It's a soft warning — the fix is editorial, not structural.

**The fix is purely editorial — layout is unchanged either way.** Pick whichever of these two moves is shorter:

1. **Lengthen the prose by 1–2 words** so the last line picks up enough text to look intentional. Add a clarifying adjective, expand an abbreviation, or finish the sentence with a complete clause:
   - ❌ `Sweep: IPC 10 / 50 / 100 (99.2% / 96% / 92% pruning).` — last line: "pruning)."
   - ✅ `Sweep: IPC 10 / 50 / 100 (99.2% / 96% / 92% pruning of full ImageNet-1K).` — last line now: "of full ImageNet-1K)."
2. **Tighten the prose so it reflows into one fewer line.** Drop a filler word, swap a long phrase for a shorter synonym, or pull a clause into the previous sentence. The trailing widow disappears because the whole text is now N-1 lines.

When choosing: prefer **shortening** when the section is already SPARSE-ish (you don't want to grow content uselessly) and prefer **lengthening** when there's still slack to fill. Both moves preserve the section's `FULL` verdict — re-run `check_poster.py slack` after the edit to confirm.

**Do not** try to fix widows by injecting `&nbsp;` or `<br>`. Those work for single-glyph orphans (Gate B's `ORPHAN`) but for word-level widows the right fix is the words themselves, not markup glue.

The gate skips display-chrome elements where a short last "line" is intentional or expected: `.callout`, `.conclusion`, `.stat-mini`, `.hero-label`, `.hero-note`, `.arch-row`, table cells, `figcaption`, headings. Those are sized to their content, not flowing paragraphs.

## Listen buttons & controls

- Pill shape, accent border 1.5px, accent text, transparent background; on hover/active fill with accent + white text. 12–14pt, 16px speaker glyph (use the template's existing SVG/emoji — do not change markup).
- Keep `s` (fullscreen) / `a` (toggle Listen) keybindings untouched. On entering fullscreen the poster widens to the screen (`.fit-screen` → `width: 100vw`) and the whole layout scales proportionally via its container-query units; exiting fullscreen restores the true 60in canvas. Leave this `fullscreenchange` handler and the `.poster.fit-screen` rule untouched.

## Print / export hygiene

The poster is locked to a **60×36 in landscape canvas** (ICML/NeurIPS standard, 5:3 aspect ratio). Both templates declare `@page { size: 60in 36in; margin: 0 }` so `render_poster.py` exports at exactly that physical size. The on-screen `.poster` element pins both `width: min(100vw, calc(100vh * 5 / 3))` AND `height: min(100vh, calc(100vw * 3 / 5))` with `aspect-ratio: 5 / 3` + `overflow: hidden`, so browser preview, printed PDF, and PNG thumbnail show the identical 5:3 box regardless of viewport.

`.poster` also sets `container-type: size`, and **every interior font-size / padding / gap clamp uses `cqw`, not `vw`** — `1cqw` = 1% of the poster's own width, so typography scales with the poster element, not the viewport. Use `clamp()` (e.g., `clamp(13px, 1.05cqw, 64px)`); `vw`/`vh` should only appear in the canvas-sizing rules at the top of `.poster`.

**Do NOT change** the canvas size, `@page`, `aspect-ratio: 5 / 3`, the paired `width`/`height` min() rules, `overflow: hidden`, or `container-type: size`. Together these make the 1900px preview, the 5760px print render, and the printed PDF look like the *same* layout at different magnifications. Without `cqw`, the browser preview hits the clamp ceiling and looks dense while the print render falls below and looks sparse — same HTML, two different posters.

No external font loads from CDNs at render time (offline-safe). If a Google Font is referenced in the base template, keep it; otherwise rely on the system stack above.

## Applying the polish

Append a single `<style>` block after the template's existing styles (so they override cleanly), or apply inline edits to existing rules — whichever keeps the diff smallest. Do not remove any class or id used by the audio/keybinding scripts.
