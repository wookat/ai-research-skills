#!/usr/bin/env python3
"""Plan a small, safe TTS rate adjustment after script-level duration planning.

Large duration changes belong in the narration script. This helper only handles
the last few seconds of mismatch by recommending a bounded edge-tts rate such
as +3% or -2%. If the required adjustment is too large, it reports that the
script should be rewritten instead of hiding the problem in an unnatural voice.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "paper2video_tts_rate_plan.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[plan_tts_rate] file not found: {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"[plan_tts_rate] invalid JSON {path}: {exc}")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def which(name: str) -> str | None:
    return shutil.which(name)


def imageio_ffmpeg_binary() -> str | None:
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def find_ffmpeg_pair() -> tuple[str | None, str | None]:
    env_ffmpeg = os.getenv("PAPER2VIDEO_FFMPEG") or os.getenv("FFMPEG_BINARY")
    if env_ffmpeg and Path(env_ffmpeg).expanduser().is_file():
        env_ffprobe = os.getenv("PAPER2VIDEO_FFPROBE")
        if env_ffprobe and Path(env_ffprobe).expanduser().is_file():
            return str(Path(env_ffmpeg).expanduser()), str(Path(env_ffprobe).expanduser())
        return str(Path(env_ffmpeg).expanduser()), str(Path(env_ffmpeg).expanduser())

    fallback = imageio_ffmpeg_binary()
    if fallback:
        return fallback, fallback

    ffmpeg = which("ffmpeg")
    ffprobe = which("ffprobe")
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe
    return ffmpeg, ffprobe


def probe_duration(path: Path, ffmpeg: str | None, ffprobe: str | None) -> float:
    if ffprobe:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                return float(proc.stdout.strip())
            except ValueError:
                pass
    if ffmpeg:
        proc = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
        match = re.search(r"Duration:\s+(\d+):(\d+):([\d.]+)", proc.stderr)
        if match:
            return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
    sys.exit(f"[plan_tts_rate] cannot probe audio duration: {path}")


def load_script_ids(path: Path) -> list[str]:
    payload = read_json(path)
    sections = payload.get("sections") if isinstance(payload, dict) else None
    if not isinstance(sections, list) or not sections:
        sys.exit(f"[plan_tts_rate] script JSON has no sections array: {path}")
    ids = []
    for idx, sec in enumerate(sections, start=1):
        sid = str(sec.get("id") or "").strip()
        if not sid:
            sys.exit(f"[plan_tts_rate] script section {idx} has no id")
        ids.append(sid)
    return ids


def speech_seconds_from_audio(script_json: Path, audio_dir: Path) -> tuple[float, list[dict[str, Any]]]:
    ffmpeg, ffprobe = find_ffmpeg_pair()
    details = []
    total = 0.0
    for sid in load_script_ids(script_json):
        path = audio_dir / f"{sid}.mp3"
        if not path.is_file():
            sys.exit(f"[plan_tts_rate] missing audio for section {sid}: {path}")
        seconds = probe_duration(path, ffmpeg, ffprobe)
        total += seconds
        details.append({"id": sid, "file": str(path), "seconds": round(seconds, 3)})
    return total, details


def speech_seconds_from_duration_report(path: Path) -> tuple[float, int, float, float]:
    payload = read_json(path)
    slides = payload.get("slides") if isinstance(payload, dict) else None
    if not isinstance(slides, list) or not slides:
        sys.exit(f"[plan_tts_rate] duration report has no slides array: {path}")
    speech = 0.0
    for slide in slides:
        try:
            speech += float(slide.get("audio_seconds") or 0.0)
        except (TypeError, ValueError):
            pass
    start_pad = float(payload.get("start_pad") or 0.0)
    pad_tail = float(payload.get("pad_tail") or 0.0)
    return speech, len(slides), start_pad, pad_tail


def edge_rate(percent: float) -> str:
    rounded = int(round(percent))
    if rounded == 0:
        return "+0%"
    return f"{rounded:+d}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--duration-plan", type=Path,
                        help="duration_plan.json from assets_to_script.py; supplies target/tolerance/padding defaults.")
    parser.add_argument("--duration-report", type=Path,
                        help="render_video.py duration report; preferred actual duration source.")
    parser.add_argument("--script-json", type=Path,
                        help="Script JSON used with --audio-dir to probe actual MP3 durations.")
    parser.add_argument("--audio-dir", type=Path,
                        help="Audio directory used with --script-json to probe actual MP3 durations.")
    parser.add_argument("--target-minutes", type=float,
                        help="Target final duration in minutes. Overrides --duration-plan target.")
    parser.add_argument("--duration-tolerance-seconds", type=float,
                        help="Allowed target error. Overrides --duration-plan tolerance.")
    parser.add_argument("--start-pad", type=float,
                        help="Leading silence used by render_video.py. Defaults from duration report/plan.")
    parser.add_argument("--pad-tail", type=float,
                        help="Trailing silence per slide. Defaults from duration report/plan.")
    parser.add_argument("--max-adjust-percent", type=float, default=6.0,
                        help="Maximum recommended TTS rate adjustment (default: 6%%).")
    parser.add_argument("--hard-max-adjust-percent", type=float, default=8.0,
                        help="Absolute safety cap; above this the plan is unsafe (default: 8%%).")
    parser.add_argument("--rate-step-percent", type=float, default=1.0,
                        help="Round recommendation to this percent step (default: 1%%).")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    plan = read_json(args.duration_plan.resolve()) if args.duration_plan else {}
    target_minutes = args.target_minutes
    if target_minutes is None:
        target_minutes = plan.get("target_minutes")
    if target_minutes is None:
        sys.exit("[plan_tts_rate] provide --target-minutes or --duration-plan with target_minutes")
    target_seconds = float(target_minutes) * 60.0
    tolerance = (
        float(args.duration_tolerance_seconds)
        if args.duration_tolerance_seconds is not None
        else float(plan.get("tolerance_seconds") or 30.0)
    )

    section_count = 0
    audio_details: list[dict[str, Any]] = []
    if args.duration_report:
        speech_seconds, section_count, report_start_pad, report_pad_tail = speech_seconds_from_duration_report(args.duration_report.resolve())
        start_pad = float(args.start_pad) if args.start_pad is not None else report_start_pad
        pad_tail = float(args.pad_tail) if args.pad_tail is not None else report_pad_tail
        actual_source = str(args.duration_report.resolve())
    elif args.script_json and args.audio_dir:
        speech_seconds, audio_details = speech_seconds_from_audio(args.script_json.resolve(), args.audio_dir.resolve())
        section_count = len(audio_details)
        start_pad = float(args.start_pad) if args.start_pad is not None else float(plan.get("start_pad") or 0.5)
        pad_tail = float(args.pad_tail) if args.pad_tail is not None else float(plan.get("pad_tail") or 0.3)
        actual_source = str(args.audio_dir.resolve())
    else:
        sys.exit("[plan_tts_rate] provide --duration-report, or both --script-json and --audio-dir")

    if section_count <= 0:
        sys.exit("[plan_tts_rate] section count is zero")
    current_video_seconds = start_pad + speech_seconds + pad_tail * section_count
    delta = current_video_seconds - target_seconds
    desired_speech_seconds = target_seconds - start_pad - pad_tail * section_count
    if desired_speech_seconds <= 0:
        sys.exit("[plan_tts_rate] target is too short for start_pad + pad_tail overhead")

    required_adjust = (speech_seconds / desired_speech_seconds - 1.0) * 100.0
    step = max(float(args.rate_step_percent), 0.1)
    recommended_adjust = round(required_adjust / step) * step
    if abs(recommended_adjust) > abs(required_adjust) and abs(required_adjust) < step:
        recommended_adjust = 0.0

    if abs(delta) <= tolerance:
        status = "within_tolerance"
        recommended_adjust = 0.0
    elif abs(required_adjust) <= args.max_adjust_percent:
        status = "use_rate_adjustment"
    elif abs(required_adjust) <= args.hard_max_adjust_percent:
        status = "borderline_rate_adjustment"
    else:
        status = "needs_script_rewrite"
        recommended_adjust = 0.0

    safe = status in {"within_tolerance", "use_rate_adjustment", "borderline_rate_adjustment"}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "status": status,
        "safe": safe,
        "actual_source": actual_source,
        "target_minutes": float(target_minutes),
        "target_seconds": round(target_seconds, 3),
        "tolerance_seconds": round(tolerance, 3),
        "start_pad": round(start_pad, 3),
        "pad_tail": round(pad_tail, 3),
        "section_count": section_count,
        "current_speech_seconds": round(speech_seconds, 3),
        "current_video_seconds": round(current_video_seconds, 3),
        "current_delta_seconds": round(delta, 3),
        "desired_speech_seconds": round(desired_speech_seconds, 3),
        "required_adjust_percent": round(required_adjust, 3),
        "recommended_adjust_percent": round(recommended_adjust, 3),
        "recommended_edge_rate": edge_rate(recommended_adjust),
        "max_adjust_percent": args.max_adjust_percent,
        "hard_max_adjust_percent": args.hard_max_adjust_percent,
        "audio": audio_details,
        "notes": [
            "Large duration changes must be handled by rewriting script.json.",
            "Use this rate only for final small calibration, then regenerate TTS and word timings.",
        ],
    }
    if status == "needs_script_rewrite":
        payload["recommendation"] = "Rewrite/trim/expand narration script before regenerating TTS; do not hide this delta with rate."
    elif status == "within_tolerance":
        payload["recommendation"] = "Keep TTS rate at +0%; current duration is within tolerance."
    else:
        payload["recommendation"] = (
            "Regenerate audio with generate_edge_audio.py "
            f"--rate-plan {args.out.resolve()} --timings-out <word_timings.json>."
        )

    write_json(args.out.resolve(), payload)
    print(
        f"[plan_tts_rate] {status}: current={current_video_seconds:.1f}s, "
        f"target={target_seconds:.1f}s, delta={delta:+.1f}s, rate={payload['recommended_edge_rate']}"
    )
    print(f"[plan_tts_rate] wrote {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
