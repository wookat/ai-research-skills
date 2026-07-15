# Audio narration reference

> `<skills-dir>` = 本包 skills 的安装目录（如项目内 `skills/`、`.agents/skills/`、
> `~/.claude/skills/`，随平台）——不要假设固定为 `~/.claude/skills/`。

How the per-section narration MP3s are produced so the poster's Listen
buttons work. Read this at **Step 5 — Synthesize narration audio** in
paper2poster's `SKILL.md`.

A renderer's per-section Listen buttons + Full Listen control look for mp3s
at `<outdir>/assets/audio/<section-id>.mp3`. The clip ids must match the
`data-section` ids the renderer plays (the poster template's `PLAYLIST`).
If a file is missing for an id the renderer plays, that button flashes its
highlight and falls silent.

Ownership is split: **paper2assets** (its Step 7, `build_package.py`) writes
the narration *text* to `narration.json` — the audio **script** only, no TTS.
**paper2poster** (its Step 5, `generate_audio.py`) synthesizes it to mp3s for
its Listen buttons. paper2video synthesizes its own audio from the deck's
speaker notes in a separate stage. paper2assets never produces `audio/`.

## 1. narration.json (already built in Step 7)

`build_package.py` extracts each section's `**Audio script:**` line from
`paper_spec.md` (and the `title_audio_script` frontmatter for the leading
`title` clip) into:

```json
{
  "provider": "edge",
  "voice": null,
  "sections": [
    {"id": "title",          "heading": "Title",          "text": "<title + authors + one-sentence framing>"},
    {"id": "problem",        "heading": "Problem",        "text": "<Audio script prose>"},
    {"id": "method",         "heading": "Method",         "text": "..."},
    {"id": "key-result",     "heading": "Key Result",     "text": "..."},
    {"id": "ablation-study", "heading": "Ablation Study", "text": "..."}
  ]
}
```

Id conventions: file ids are the hyphenated `data-section` ids — note
`key-result` / `ablation-study` (the spec *headings* are "Key Result" /
"Ablation Study"). The `title` clip is always first and plays at the start
of Full Listen (~80 words: title + authors + one-sentence framing). Use raw
prose — no markdown / HTML / `<strong>`; TTS reads numerals and `%` fine.

## 2. Synthesize (paper2poster Step 5)

```bash
python <skills-dir>/paper2poster/scripts/generate_audio.py \
    <outdir>/assets/meta/narration.json --outdir <outdir>/assets/audio
```

Writes one `<id>.mp3` per clip + a `manifest.json`.

**Backends** (resolution: CLI flag > narration.json field > default):
- **`edge` (DEFAULT, free)** — Microsoft Edge online TTS via the `edge-tts`
  package. No API key, no config file, only network. Voices are
  Azure-Neural short names (default `en-US-AndrewNeural`; also
  `en-US-AriaNeural`, `en-US-GuyNeural`, `en-US-ChristopherNeural`, …).
  `pip install edge-tts` if missing.
- **`azure` (opt-in, `--provider azure`)** — Azure OpenAI TTS. Needs
  `~/.azure/speech.json` (presence gate) + the `AZURE_API_KEY` env var.
  Voices ONLY: `alloy|echo|fable|onyx|nova|shimmer` (a Neural name → HTTP 400).

## 3. Missing-backend handling

If `edge-tts` isn't installed / the network is down (edge), or the Azure
config/key is absent (azure), the script exits with a clear instruction
message and writes nothing — **surface it verbatim** and continue. The
assets are still complete; only Listen is mute. Don't fabricate a config or
skip silently.

## 4. Keep ids in sync with the renderer

The clip ids must equal the ids the renderer plays. The poster template's
`PLAYLIST` lists them; if a render drops a section (e.g. `dataset-benchmark`)
or injects a custom one, the renderer keeps `PLAYLIST` matched to the audio
files present so the Full Listen sequencer never plays a missing clip.

## Why this matters

The whole reason these artifacts beat a static export is the embedded
narration — a passerby clicks Listen and hears an ~80-word voiced
explanation per section. Treat the mp3s as first-class output alongside the
figures and spec.
