# Narration script JSON — schema and gotchas

paper2poster's `scripts/generate_audio.py` reads a single JSON file and writes
one MP3 per `sections[*].id`. paper2video reuses it verbatim. The same shape is
also produced from paper2assets by
`skills/paper2video/scripts/assets_to_script.py`. The script JSON shape:

```json
{
  "voice": "alloy",          // optional; overrides cfg default. OpenAI TTS voices only.
  "model": "tts",            // optional; usually leave at "tts".
  "sections": [
    {"id": "01-intro",     "heading": "Introduction",   "text": "Welcome..."},
    {"id": "02-method",    "heading": "Method",         "text": "We propose..."},
    ...
  ]
}
```

## What each field does

- **voice** — one of `alloy / echo / fable / onyx / nova / shimmer`. Anything
  else (e.g. an Azure Neural name like `en-US-JennyNeural`) makes the API
  return HTTP 400. If the user wants a Neural-style voice, use ppt-master's
  `notes_to_audio.py` instead — paper2poster's path is OpenAI-TTS only.
- **model** — defaults to `tts`. Don't set it unless the user asked for a
  specific Azure deployment.
- **sections[*].id** — also the output filename (`audio/<id>.mp3`). For
  ppt-master projects, this is usually the slide stem (`01-intro`). For
  paper2assets, this is the semantic section id (`problem`, `key-result`).
  In both cases, pass the JSON to `render_video.py --script-json` so frame and
  audio pairing follows `sections` order instead of alphabetical filename
  order.
- **sections[*].heading** — only used in `manifest.json`. Cosmetic.
- **sections[*].text** — what gets spoken. Plain text only — markdown
  syntax (`**bold**`, `` `code` ``, list bullets) is read literally by the
  TTS, which sounds robotic. `notes_to_script.py` strips markdown before
  emitting the JSON; if you assemble the JSON by hand, do the same.

## Gotchas

- **End each section with sentence-final punctuation.** The TTS engine uses
  punctuation to cue prosody and pause. A section ending with "we propose
  the following approach" trails off in a flat tone; "we propose the
  following approach." gets the natural drop. `notes_to_script.py` doesn't
  fix this — keep it in mind if you hand-edit text.
- **Don't include code blocks.** Synthesizing literal Python or shell is
  almost always worse than just describing what the code does. The helper
  drops fenced code blocks; if you're hand-writing text, paraphrase code
  rather than spelling it out.
- **One section ~= one slide ~= one MP3.** Don't try to merge multiple slides
  into one section to save TTS calls — Stage 3's frame/audio pairing
  assumes 1-to-1.
- **Skipped slides are fine for divider/title slides** with no narration.

## Duration planning sidecar

When `notes_to_script.py` or `assets_to_script.py` is called with
`--target-minutes`, it still writes the same TTS-compatible `script.json`.
It also writes a sidecar `duration_plan.json`:

```json
{
  "schema_version": "paper2video_duration_plan.v1",
  "target_seconds": 180.0,
  "tolerance_seconds": 30.0,
  "status": "within_tolerance",
  "estimated_video_seconds": 192.4,
  "sections": [
    {
      "id": "method",
      "source_words": 82,
      "budget_words": 44,
      "planned_words": 41,
      "changed": true,
      "dropped": false
    }
  ]
}
```

This sidecar is metadata only. `generate_audio.py` should consume `script.json`,
not `duration_plan.json`. After TTS, `render_video.py --target-minutes` writes a
real `duration_report.json` based on probed MP3/MP4 duration.
  `notes_to_script.py --min-chars` filters them out automatically. Just
  remember the resulting MP4 will also skip those slides — if a divider
  needs a few seconds of screentime, give it a real one-line note.

## Worked example

ppt-master output (excerpt):

```
projects/llama_paper_ppt169_20260607/
├── notes/
│   ├── 01-title.md          ("# LLaMA: Open and Efficient ...")
│   ├── 02-motivation.md
│   ├── 03-method.md
│   └── 04-results.md
└── ...
```

After `notes_to_script.py`:

```json
{
  "voice": "alloy",
  "model": "tts",
  "sections": [
    {"id": "01-title",      "heading": "LLaMA: Open and Efficient ...", "text": "..."},
    {"id": "02-motivation", "heading": "Motivation",                    "text": "..."},
    {"id": "03-method",     "heading": "Method",                        "text": "..."},
    {"id": "04-results",    "heading": "Results",                       "text": "..."}
  ]
}
```

After `generate_audio.py`:

```
audio/
├── 01-title.mp3
├── 02-motivation.mp3
├── 03-method.mp3
├── 04-results.mp3
├── manifest.json
└── script.json
```

`render_video.py` then reads the PPTX (4 slides) and audio dir (4 MP3s) and
muxes them in sorted order. PNGs are named `slide-01.png … slide-04.png`
inside the temp dir; matching is positional, not by stem.
