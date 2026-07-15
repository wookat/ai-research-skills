# Visual cues JSON - semantic highlight boxes and cursor overlays

`render_video.py` can burn simple attention cues into each static slide segment.
Use this when a narrated video feels too inert but you do not want to animate
the slide deck itself.

## CLI

```bash
python skills/paper2video/scripts/render_video.py <project_path> \
  --pptx <project_path>/exports/<name>.pptx \
  --audio-dir <project_path>/audio \
  --script-json <project_path>/audio/script.json \
  --attention-mode highlight \
  --highlight-style spotlight_laser \
  --visual-cues <project_path>/visual_cues.json \
  --out <project_path>/exports/<name>.mp4
```

`--attention-mode` controls which cues are applied:

| Mode | Behavior |
|---|---|
| `none` | Ignore cues; use only for an approved no-highlight render |
| `highlight` | Apply only `type: "highlight"` cues; default final-delivery mode |
| `cursor` | Apply only `type: "cursor"` cues |
| `both` | Apply both cue types when the cue file contains both |

## Schema

Production highlight cues are box-first. Coordinates are normalized to the final video
frame:

- `[0, 0]` is top-left.
- `[1, 1]` is bottom-right.
- A highlight `box` is `[x, y, w, h]` and is the geometry actually rendered.
  The renderer expands it by about one border width, then draws a low-opacity
  slate fill and soft border around that target.
- A highlight should also include `point` as the center for compatibility and
  audit tooling. Point-only highlight cues remain valid as degraded/debug
  fallbacks, but strict QA expects boxes.
- Automatic cues should include `semantic_*` and `geometry_*` fields. The
  semantic fields explain what narration target was selected; the geometry
  fields explain which PPTX or PPTX-cluster box was used for the visible
  highlight. When PPTX geometry cannot be matched with enough confidence,
  `geometry_matched` is false and the cue falls back to the semantic box.
- Timing should come from `edge_word_alignment`, which aligns each narration
  chunk back to the real word-boundary timeline. `duration_proportional` is
  scaffolding/debug timing only and should fail strict final QA when word
  timings are required.
- A cursor `point` is `[x, y]`.

```json
{
  "schema_version": "paper2video_visual_cues.v3",
  "cue_shape": "semantic_box",
  "slides": [
    {
      "id": "07_fineweb_accuracy_lift",
      "cues": [
        {
          "start": 3.2,
          "end": 8.5,
          "type": "highlight",
          "box": [0.12, 0.28, 0.14, 0.21],
          "point": [0.19, 0.39],
          "target": "cue_s07_c1_accuracy_lift",
          "target_role": "result",
          "semantic_target": "svg:g:cues07-result-card",
          "semantic_source": "svg",
          "semantic_box": [0.11, 0.27, 0.16, 0.22],
          "geometry_target": "TextBox 18",
          "geometry_source": "pptx",
          "geometry_box": [0.12, 0.28, 0.14, 0.21],
          "geometry_matched": true,
          "geometry_match_score": 5.72,
          "confidence": 0.82,
          "color": "#64748B",
          "opacity": 0.18,
          "size": 56
        },
        {
          "start": 9.0,
          "duration": 4.0,
          "type": "cursor",
          "point": [0.52, 0.62],
          "color": "#ff6b00",
          "opacity": 0.95,
          "size": 32
        }
      ]
    }
  ]
}
```

## Slide matching

Prefer `id`, matching the narration/audio stem:

```json
{"id": "07_fineweb_accuracy_lift", "cues": []}
```

Use `index` only when ids are unavailable:

```json
{"index": 7, "cues": []}
```

## Timing

Cue times are relative to the start of that slide's own video segment, not the
global MP4 timeline. They should align with the narration text for that slide.

Accepted timing forms:

```json
{"start": 3.2, "end": 8.5}
{"at": 9.0, "duration": 4.0}
```

Times are clipped to the slide segment duration, including `--pad-tail`.

## Rendering

`highlight` cues are box-first, and the default presentation style is
`spotlight_laser`: a feathered spotlight around the accepted box plus a small
red laser-pointer dot at the cue center. Existing point-only cue files remain
valid and render as cursor/point fallbacks, but final strict attention QA
requires highlight boxes.

`render_video.py --highlight-style` controls the presentation of accepted
highlight cues:

| Style | Behavior |
|---|---|
| `box` | Subtle filled frame around the selected box |
| `cursor` | Mouse pointer only at the cue point |
| `box_cursor` | Box plus mouse pointer for debugging or reviewer comparisons |
| `spotlight` | Feathered dim-out around the selected box |
| `spotlight_cursor` | Feathered dim-out plus mouse pointer |
| `laser` | Red laser-pointer dot only at the cue point |
| `spotlight_laser` | Default delivery style: feathered dim-out plus red laser-pointer dot |

The spotlight styles generate a full-frame transparent alpha mask for each cue:
the accepted box remains at original brightness while the surrounding slide
fades out with a continuous feather. At 1080p the default feather is about
56 px. They are visually tolerant, but full-video encoding can be slower
because each cue adds an extra overlay mask.

Cursor styles render a generated transparent mouse pointer. The renderer keeps
the same cue point semantics, but eases the visible pointer between consecutive
cue points on a slide shortly before each next cue starts.

Laser styles use the same cue point semantics and eased movement, but render a
small red dot with a soft halo instead of the mouse pointer.

## Semantic vs geometry review

`generate_visual_cues.py` keeps semantic matching separate from rendered
geometry. A cue may select an SVG semantic group, then render a matched PPTX
box. It may also promote a line-level text target to a nearby module/group when
that parent is still bounded enough for presentation-style highlighting.
Connected PPTX clusters are filtered so a large union box does not cross
unrelated regions.

Always write the review artifacts during automatic cue generation:

```bash
python skills/paper2video/scripts/generate_visual_cues.py <project_path> \
  --script-json <project_path>/audio/script.json \
  --audio-dir <project_path>/audio \
  --pptx <project_path>/exports/<name>.pptx \
  --timings-json <project_path>/audio/word_timings.json \
  --strict-gate \
  --require-timestamps \
  --out <project_path>/visual_cues.json \
  --geometry-report-out <project_path>/geometry_resolution.json \
  --cue-plan-out <project_path>/visual_cue_plan.json \
  --audit-out <project_path>/cue_audit.json \
  --html-audit-out <project_path>/cue_audit.html \
  --candidate-review-out <project_path>/cue_candidate_review.html
```

Use `cue_candidate_review.html` when a rendered frame looks wrong. It shows
the chunk text, word-timing match, selected semantic target, final geometry
target, promotion reason, and top semantic/geometry candidates that were
accepted or rejected.

## Current limits

This implementation renders stable, deterministic overlays with ffmpeg
filters. It should not guess highlights from layout alone. For automatic cue
generation, first create a visual-anchor contract and ask ppt-master to create
semantic anchors:

```bash
python skills/paper2video/scripts/generate_cue_requirements.py \
  <project_path>/audio/script.json \
  --out <project_path>/cue_requirements.json \
  --contract-out <project_path>/visual_anchor_contract.json \
  --markdown-out <project_path>/cue_requirements.md
```

Write anchors into both the final SVG and the exported PPTX when possible.
SVG/HTML anchors are still valuable semantic labels, especially when the slide
source groups related content more cleanly than PPTX. The cue generator now
prefers PPTX geometry for the rendered box when it can match the semantic SVG
target to a PPTX element or a small connected PPTX element cluster. PPTX shape
name, alt-text title, or alt-text description keeps that geometry auditable.
SVG/HTML can carry the same anchor in `id`, `data-cue-label`, `<title>`, or
`<desc>`:

```xml
<g id="cue_s08_c2_multi_head_attention"
   data-cue-label="multi-head attention split eight heads concatenate projections">
  <title>cue_s08_c2_multi_head_attention</title>
  <desc>Multi-head attention diagram: split Q/K/V projections into eight heads, then concatenate.</desc>
  ...
</g>
```

Anchor rules:

- Prefer stable PPTX/SVG ids beginning with `cue_`.
- Include narration keywords in `<title>`, `<desc>`, or `data-cue-label`.
- Anchor specific visual content: chart row, formula block, diagram panel,
  card, or figure subregion.
- Do not anchor headers, captions, logos, QR tiles, page numbers, or background
  chrome.
- When `--anchor-contract` is provided, exact `anchor_id` matching is required;
  the matcher should not silently fall back to layout guessing for that chunk.

```bash
python skills/paper2video/scripts/generate_visual_cues.py <project_path> \
  --script-json <project_path>/audio/script.json \
  --audio-dir <project_path>/audio \
  --pptx <project_path>/exports/<name>.pptx \
  --anchor-contract <project_path>/visual_anchor_contract.json \
  --require-pptx-anchors \
  --timings-json <project_path>/audio/word_timings.json \
  --strict-gate \
  --require-timestamps \
  --out <project_path>/visual_cues.json \
  --geometry-report-out <project_path>/geometry_resolution.json \
  --candidate-review-out <project_path>/cue_candidate_review.html \
  --cue-plan-out <project_path>/visual_cue_plan.json \
  --audit-out <project_path>/cue_audit.json \
  --html-audit-out <project_path>/cue_audit.html \
  --repair-out <project_path>/cue_repair_requests.json \
  --repair-md-out <project_path>/cue_repair_requests.md
```

`geometry_resolution.json` summarizes how many cues rendered from direct PPTX
boxes, PPTX connected clusters, or semantic fallbacks. Review this file with
`cue_audit.html` when a frame looks too broad or too narrow. Use
`--no-prefer-pptx-geometry` only for debugging an SVG-vs-PPTX geometry
regression; final highlighted videos should prefer PPTX geometry unless the
gate reports low confidence and requests repair.

If strict mode fails, the script still writes cue audits and repair requests,
then exits non-zero. Fix the deck or narration and rerun before rendering a
highlighted video.
