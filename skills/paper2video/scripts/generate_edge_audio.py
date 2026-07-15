#!/usr/bin/env python3
"""
Generate MP3 narration from a paper2video script JSON using edge-tts.

The output contract intentionally matches paper2poster's generate_audio.py:
one <section.id>.mp3 per section plus a manifest.json under --outdir.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError as exc:  # pragma: no cover - depends on local env
    raise SystemExit(
        "[generate_edge_audio] edge_tts is not installed in this Python env. "
        "Install edge-tts or use skills/paper2poster/scripts/generate_audio.py."
    ) from exc


DEFAULT_VOICE = "en-US-AriaNeural"
TIMINGS_SCHEMA_VERSION = "paper2video_edge_word_boundaries.v1"


def load_rate_plan(path: Path, *, allow_unsafe: bool) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[generate_edge_audio] rate plan not found: {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"[generate_edge_audio] invalid rate plan {path}: {exc}")
    if payload.get("schema_version") != "paper2video_tts_rate_plan.v1":
        sys.exit(f"[generate_edge_audio] unsupported rate plan schema: {payload.get('schema_version')}")
    status = str(payload.get("status") or "")
    safe = bool(payload.get("safe"))
    if not safe and not allow_unsafe:
        sys.exit(
            "[generate_edge_audio] rate plan is not safe for automatic TTS regeneration "
            f"(status={status}). Rewrite the narration script first, or pass "
            "--allow-unsafe-rate-plan only for an explicit experiment."
        )
    if status == "needs_script_rewrite" and not allow_unsafe:
        sys.exit("[generate_edge_audio] rate plan requires script rewrite; refusing to hide it with TTS rate.")
    rate = str(payload.get("recommended_edge_rate") or "+0%")
    if not rate.endswith("%") or not (rate.startswith("+") or rate.startswith("-")):
        sys.exit(f"[generate_edge_audio] invalid recommended_edge_rate in {path}: {rate!r}")
    return rate


async def synthesize_section(text: str, *, voice: str, rate: str, pitch: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(out_path))


def edge_ticks_to_seconds(raw: object) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    # edge-tts WordBoundary offsets are 100ns ticks.
    return value / 10_000_000.0


async def synthesize_section_with_timings(
    text: str,
    *,
    voice: str,
    rate: str,
    pitch: str,
    out_path: Path,
) -> list[dict]:
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        boundary="WordBoundary",
    )
    words: list[dict] = []
    with out_path.open("wb") as fh:
        async for chunk in communicate.stream():
            kind = chunk.get("type")
            if kind == "audio":
                data = chunk.get("data")
                if data:
                    fh.write(data)
            elif kind == "WordBoundary":
                start = edge_ticks_to_seconds(chunk.get("offset"))
                duration = edge_ticks_to_seconds(chunk.get("duration"))
                words.append({
                    "text": str(chunk.get("text") or ""),
                    "start": round(start, 3),
                    "end": round(start + max(duration, 0.0), 3),
                    "duration": round(max(duration, 0.0), 3),
                })
    return words


async def synthesize_all(
    sections: list[dict],
    *,
    voice: str,
    rate: str,
    pitch: str,
    outdir: Path,
    collect_timings: bool,
) -> tuple[list[dict], list[dict]]:
    manifest = []
    timing_sections = []
    for sec in sections:
        sid = str(sec.get("id") or "").strip()
        text = str(sec.get("text") or "").strip()
        if not sid:
            raise ValueError("every script section must have an id")
        if not text:
            raise ValueError(f"section {sid} has empty text")
        out_path = outdir / f"{sid}.mp3"
        print(f"[edge-tts] {sid} ({len(text)} chars, voice={voice}, rate={rate}) -> {out_path}")
        words: list[dict] = []
        if collect_timings:
            words = await synthesize_section_with_timings(
                text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                out_path=out_path,
            )
        else:
            await synthesize_section(text, voice=voice, rate=rate, pitch=pitch, out_path=out_path)
        manifest.append({
            "id": sid,
            "heading": sec.get("heading", sid),
            "file": out_path.name,
            "bytes": out_path.stat().st_size,
            "provider": "edge-tts",
            "voice": voice,
            "rate": rate,
            "pitch": pitch,
            "word_boundaries": len(words),
        })
        if collect_timings:
            timing_sections.append({
                "id": sid,
                "heading": sec.get("heading", sid),
                "file": out_path.name,
                "words": words,
            })
    return manifest, timing_sections


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate paper2video narration audio with edge-tts.")
    ap.add_argument("script", help="Path to script JSON")
    ap.add_argument("--outdir", required=True, help="Directory to write <id>.mp3 files")
    ap.add_argument("--voice", default=None,
                    help=f"Edge voice name (default: script.edge_voice or {DEFAULT_VOICE})")
    ap.add_argument("--rate", default=None, help="Edge rate adjustment, e.g. +0%%, -8%%, +10%%")
    ap.add_argument("--rate-plan", default=None,
                    help="Optional plan_tts_rate.py JSON. Uses recommended_edge_rate and refuses unsafe plans.")
    ap.add_argument("--allow-unsafe-rate-plan", action="store_true",
                    help="Allow a rate plan whose status says the script should be rewritten. Experimental only.")
    ap.add_argument("--pitch", default="+0Hz", help="Edge pitch adjustment, e.g. +0Hz")
    ap.add_argument("--timings-out", default=None,
                    help="Optional JSON path for Edge WordBoundary timings used by visual cue alignment.")
    args = ap.parse_args()

    script_path = Path(args.script).resolve()
    payload = json.loads(script_path.read_text(encoding="utf-8"))
    sections = payload.get("sections") or []
    if not isinstance(sections, list) or not sections:
        sys.exit("[generate_edge_audio] script JSON has no sections array")

    voice = args.voice or payload.get("edge_voice") or DEFAULT_VOICE
    if args.rate_plan:
        rate = load_rate_plan(Path(args.rate_plan).resolve(), allow_unsafe=args.allow_unsafe_rate_plan)
        if args.rate and args.rate != rate:
            print(f"[generate_edge_audio] --rate-plan overrides --rate {args.rate} -> {rate}")
    else:
        rate = args.rate or "+0%"
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        manifest, timing_sections = asyncio.run(
            synthesize_all(
                sections,
                voice=voice,
                rate=rate,
                pitch=args.pitch,
                outdir=outdir,
                collect_timings=args.timings_out is not None,
            )
        )
    except Exception as exc:
        sys.exit(f"[generate_edge_audio] {exc}")

    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.timings_out:
        timings_path = Path(args.timings_out).resolve()
        timings_path.parent.mkdir(parents=True, exist_ok=True)
        timings_payload = {
            "schema_version": TIMINGS_SCHEMA_VERSION,
            "provider": "edge-tts",
            "voice": voice,
            "rate": rate,
            "pitch": args.pitch,
            "sections": timing_sections,
        }
        timings_path.write_text(json.dumps(timings_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[edge-tts] wrote word-boundary timings to {timings_path}")
    print(f"\n[edge-tts] wrote {len(manifest)} clips to {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
