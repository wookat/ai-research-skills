#!/usr/bin/env python3
"""
Synthesize per-section narration audio for a paper's poster/blog/video.

Consumes the `narration.json` that paper2assets already produced
(build_package.py):

    {
      "provider": "edge" | "azure" | null,   # optional; CLI overrides
      "voice":    "<voice name>" | null,      # optional; CLI overrides
      "sections": [
        {"id": "title",  "heading": "Title",  "text": "..."},
        {"id": "method", "heading": "Method", "text": "..."},
        ...
      ]
    }

Output: one `<id>.mp3` per section in <outdir>/, plus a manifest.json.
The poster's Listen buttons + Full Listen control look for exactly these
files at `<outdir>/audio/<id>.mp3` (ids must match the template PLAYLIST).

Two TTS backends:
  - edge  (DEFAULT, free): Microsoft Edge online TTS via the `edge-tts`
    package. No API key, no config file — only network access. Voices are
    Azure-Neural short names, e.g. en-US-AndrewNeural / en-US-AriaNeural.
  - azure (opt-in): Azure OpenAI TTS. Requires ~/.azure/speech.json to
    exist (presence gate) AND the AZURE_API_KEY env var. Voices are the
    OpenAI set only: alloy|echo|fable|onyx|nova|shimmer.

Provider/voice resolution: CLI flag > narration.json field > backend default.
Missing edge-tts or missing Azure creds → exits with a clear message and
writes nothing; the poster still renders, only Listen is silent.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib import request, error

EDGE_DEFAULT_VOICE = "en-US-AndrewNeural"
AZURE_DEFAULT_VOICE = "alloy"
AZURE_VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
AZURE_CONFIG_PATH = Path.home() / ".azure" / "speech.json"
AZURE_API_VERSION = "2025-03-01-preview"


# ── Edge TTS (free default) ─────────────────────────────────────────────
def synth_edge(sections: list[dict], outdir: Path, voice: str) -> list[dict]:
    try:
        import edge_tts  # type: ignore
    except ImportError:
        sys.exit(
            "edge-tts is not installed — it backs the free default TTS:\n"
            "    pip install edge-tts\n\n"
            "Audio narration was SKIPPED. The poster's HTML/PDF still render\n"
            "correctly; only the Listen buttons stay silent. (Or pass\n"
            "--provider azure to use Azure OpenAI TTS instead.)"
        )

    async def run() -> list[dict]:
        manifest: list[dict] = []
        for sec in sections:
            sid = sec["id"]
            text = (sec.get("text") or "").strip()
            if not text:
                print(f"[tts/edge] {sid}: empty text, skipped", file=sys.stderr)
                continue
            out_path = outdir / f"{sid}.mp3"
            print(f"[tts/edge] {sid} ({len(text)} chars, voice={voice}) -> {out_path.name}")
            await edge_tts.Communicate(text, voice).save(str(out_path))
            manifest.append({"id": sid, "heading": sec.get("heading", sid),
                             "file": f"{sid}.mp3", "bytes": out_path.stat().st_size})
        return manifest

    return asyncio.run(run())


# ── Azure OpenAI TTS (opt-in) ───────────────────────────────────────────
def _azure_cfg() -> dict:
    if not AZURE_CONFIG_PATH.exists():
        sys.exit(
            f"--provider azure requires the config gate {AZURE_CONFIG_PATH} "
            f"(create it) and the AZURE_API_KEY env var. Audio was SKIPPED.\n"
            f"Drop --provider azure to use the free Edge backend (default)."
        )
    cfg = {
        "endpoint": "https://67786-mpmfvjz3-swedencentral.cognitiveservices.azure.com",
        "deployment": "tts",
        "model": "tts",
        "key": os.environ.get("AZURE_API_KEY", ""),
    }
    if not cfg["key"]:
        sys.exit("AZURE_API_KEY env var is empty — required for --provider azure.")
    return cfg


def synth_azure(sections: list[dict], outdir: Path, voice: str) -> list[dict]:
    cfg = _azure_cfg()
    manifest: list[dict] = []
    for sec in sections:
        sid = sec["id"]
        text = (sec.get("text") or "").strip()
        if not text:
            continue
        out_path = outdir / f"{sid}.mp3"
        print(f"[tts/azure] {sid} ({len(text)} chars, voice={voice}) -> {out_path.name}")
        url = (f"{cfg['endpoint'].rstrip('/')}/openai/deployments/{cfg['deployment']}"
               f"/audio/speech?api-version={AZURE_API_VERSION}")
        body = json.dumps({"model": cfg["model"], "input": text, "voice": voice}).encode("utf-8")
        req = request.Request(url, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {cfg['key']}"})
        try:
            with request.urlopen(req, timeout=120) as resp:
                out_path.write_bytes(resp.read())
        except error.HTTPError as e:
            msg = e.read().decode("utf-8", errors="replace")
            sys.exit(f"Azure OpenAI TTS HTTP {e.code} for {sid}.mp3: {msg}")
        manifest.append({"id": sid, "heading": sec.get("heading", sid),
                         "file": f"{sid}.mp3", "bytes": out_path.stat().st_size})
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Synthesize poster narration mp3s from a paper2assets narration.json")
    ap.add_argument("script", help="Path to narration.json")
    ap.add_argument("--outdir", required=True, help="Directory to write <id>.mp3 files")
    ap.add_argument("--provider", choices=["edge", "azure"], default=None,
                    help="TTS backend. Default: narration.json 'provider', else 'edge' (free).")
    ap.add_argument("--voice", default=None,
                    help="Override voice for the chosen provider "
                         "(edge: en-US-*Neural; azure: alloy|echo|fable|onyx|nova|shimmer).")
    a = ap.parse_args()

    doc = json.loads(Path(a.script).read_text())
    sections = doc.get("sections") or []
    if not sections:
        sys.exit("narration.json has no 'sections' array (nothing to synthesize).")

    provider = a.provider or doc.get("provider") or "edge"
    voice = a.voice or doc.get("voice") or (
        EDGE_DEFAULT_VOICE if provider == "edge" else AZURE_DEFAULT_VOICE)
    # Guard cross-provider voice mismatch (e.g. a stored Azure 'alloy' under
    # the edge backend, or an edge 'en-US-*' name under azure).
    if provider == "edge" and voice in AZURE_VOICES:
        voice = EDGE_DEFAULT_VOICE
    if provider == "azure" and voice not in AZURE_VOICES:
        voice = AZURE_DEFAULT_VOICE

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    synth = synth_edge if provider == "edge" else synth_azure
    manifest = synth(sections, outdir, voice)

    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n[tts] wrote {len(manifest)} clips to {outdir} "
          f"(provider={provider}, voice={voice})")


if __name__ == "__main__":
    main()
