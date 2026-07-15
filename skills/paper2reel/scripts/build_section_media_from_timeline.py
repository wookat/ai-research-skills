#!/usr/bin/env python3
"""Rebuild reel section media from paper2video timeline.json.

This script keeps an existing section-modal reel bundle but replaces
its fragile time-window guesses with the canonical paper2video timeline. It
updates content_alignment.json, refreshes the inline ALIGNMENT constant in
reel.html, rebuilds complete slide clips, composes section clips from
those slide clips, appends a short silent freeze tail, and crops VTT subtitles
from the full-paper VTT using the same timeline windows.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


VIEWER_VERSION = "section_modal.v2"
TEMPLATE_VERSION = "attention_golden_section_modal.v1"
MEDIA_DIR = "assets/media"


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[timeline_media] file not found: {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"[timeline_media] invalid JSON {path}: {exc}")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def vtt_to_seconds(raw: str) -> float:
    match = re.match(r"(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)", raw.strip())
    if not match:
        raise ValueError(raw)
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_vtt(value: float) -> str:
    value = max(0.0, value)
    hours = int(value // 3600)
    value -= hours * 3600
    minutes = int(value // 60)
    value -= minutes * 60
    seconds = int(value)
    millis = int(round((value - seconds) * 1000))
    if millis == 1000:
        seconds += 1
        millis = 0
    if seconds == 60:
        minutes += 1
        seconds = 0
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def read_vtt(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    if not path.is_file():
        sys.exit(f"[timeline_media] captions VTT not found: {path}")
    blocks = [part.strip() for part in path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n\n") if part.strip()]
    cues: list[dict[str, Any]] = []
    for block in blocks:
        if block == "WEBVTT" or block.startswith("WEBVTT\n"):
            continue
        lines = block.splitlines()
        time_idx = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if time_idx is None:
            continue
        left, right = lines[time_idx].split("-->", 1)
        try:
            start = vtt_to_seconds(left.strip().split()[0])
            end = vtt_to_seconds(right.strip().split()[0])
        except ValueError:
            continue
        body = "\n".join(lines[time_idx + 1:]).strip()
        if body and end > start:
            cues.append({"start": start, "end": end, "text": body})
    return cues


def crop_vtt(cues: list[dict[str, Any]], start: float, end: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["WEBVTT", ""]
    for cue in cues:
        cue_start = float(cue["start"])
        cue_end = float(cue["end"])
        if cue_end <= start or cue_start >= end:
            continue
        local_start = max(cue_start, start) - start
        local_end = min(cue_end, end) - start
        if local_end - local_start < 0.03:
            continue
        lines.append(f"{seconds_to_vtt(local_start)} --> {seconds_to_vtt(local_end)}")
        lines.append(str(cue["text"]))
        lines.append("")
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(
            "[timeline_media] command failed:\n"
            + " ".join(cmd)
            + f"\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )


def probe_duration(ffmpeg: str, path: Path) -> float:
    proc = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
    match = re.search(r"Duration:\s+(\d+):(\d+):([\d.]+)", proc.stderr)
    if not match:
        raise SystemExit(f"[timeline_media] could not probe duration for {path}")
    return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))


def looks_like_burned_final_video(path: Path) -> bool:
    parts = path.resolve().parts
    return (
        path.name == "video.mp4"
        and len(parts) >= 3
        and parts[-2] == "final"
        and parts[-3] == "paper2video"
    )


def cut_video(ffmpeg: str, source: Path, start: float, end: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.1, end - start)
    run([
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-strict",
        "-2",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(out),
    ])


def make_freeze_tail(ffmpeg: str, source_clip: Path, seconds: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if seconds <= 0:
        return
    with tempfile.TemporaryDirectory(prefix="paper2reel_tail_") as tmp:
        frame = Path(tmp) / "last_frame.png"
        seek_time = max(0.0, probe_duration(ffmpeg, source_clip) - 0.08)
        run([
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{seek_time:.3f}",
            "-i",
            str(source_clip),
            "-frames:v",
            "1",
            str(frame),
        ])
        if not frame.is_file():
            raise SystemExit(f"[timeline_media] failed to extract freeze-tail frame from {source_clip}")
        run([
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(frame),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            f"{seconds:.3f}",
            "-vf",
            "format=yuv420p,setsar=1",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-strict",
            "-2",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out),
        ])


def concat_clips(ffmpeg: str, clips: list[Path], out: Path) -> None:
    if not clips:
        raise SystemExit("[timeline_media] cannot compose section clip from zero slide clips")
    out.parent.mkdir(parents=True, exist_ok=True)
    if len(clips) == 1:
        shutil.copy2(clips[0], out)
        return
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for clip in clips:
        cmd.extend(["-i", str(clip)])
    filters = []
    concat_inputs = []
    for idx in range(len(clips)):
        filters.append(f"[{idx}:v:0]format=yuv420p,setsar=1[v{idx}]")
        filters.append(f"[{idx}:a:0]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{idx}]")
        concat_inputs.append(f"[v{idx}][a{idx}]")
    filters.append("".join(concat_inputs) + f"concat=n={len(clips)}:v=1:a=1[v][a]")
    cmd.extend([
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-strict",
        "-2",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(out),
    ])
    run(cmd)


def compose_section_clip(ffmpeg: str, slide_clips: list[Path], out: Path, tail_seconds: float) -> None:
    if not slide_clips:
        raise SystemExit(f"[timeline_media] no slide clips for section output: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    if tail_seconds <= 0:
        concat_clips(ffmpeg, slide_clips, out)
        return
    with tempfile.TemporaryDirectory(prefix="paper2reel_section_") as tmp:
        tmp_dir = Path(tmp)
        base = tmp_dir / "section_base.mp4"
        tail = tmp_dir / "section_tail.mp4"
        concat_clips(ffmpeg, slide_clips, base)
        make_freeze_tail(ffmpeg, base, tail_seconds, tail)
        concat_clips(ffmpeg, [base, tail], out)


def replace_inline_json_constant(html: str, name: str, payload: dict[str, Any]) -> tuple[str, int]:
    # Keep inline script constants ASCII-escaped. Blog prose and VTT captions can
    # contain Unicode line separators that are valid JSON but unsafe in classic
    # JavaScript string literals when embedded directly in <script>.
    replacement = f"const {name} = " + json.dumps(payload, ensure_ascii=True) + ";\n"
    pattern = rf"const {re.escape(name)} = .*?;\n(?=const\s)"
    return re.subn(pattern, lambda _: replacement, html, count=1, flags=re.S)


def caption_text_map(viewer_dir: Path) -> dict[str, str]:
    captions_dir = viewer_dir / MEDIA_DIR / "captions"
    if not captions_dir.is_dir():
        return {}
    out: dict[str, str] = {}
    for path in sorted(captions_dir.rglob("*.vtt")):
        out[path.relative_to(viewer_dir).as_posix()] = path.read_text(encoding="utf-8")
    return out


def update_inline_alignment(html_path: Path, alignment: dict[str, Any]) -> None:
    if not html_path.is_file():
        return
    html = html_path.read_text(encoding="utf-8")
    updated, count = replace_inline_json_constant(html, "ALIGNMENT", alignment)
    if count == 0:
        print(f"[timeline_media] warning: could not find inline ALIGNMENT in {html_path}")
        return
    html_path.write_text(updated, encoding="utf-8")


def update_inline_captions(viewer_dir: Path) -> None:
    html_path = viewer_dir / "reel.html"
    if not html_path.is_file():
        return
    captions = caption_text_map(viewer_dir)
    if not captions:
        return
    html = html_path.read_text(encoding="utf-8")
    updated, count = replace_inline_json_constant(html, "CAPTION_TEXT", captions)
    if count == 0:
        marker = "const sections ="
        if marker not in html:
            print(f"[timeline_media] warning: could not find CAPTION_TEXT insertion point in {html_path}")
            return
        updated = html.replace(marker, "const CAPTION_TEXT = " + json.dumps(captions, ensure_ascii=True) + ";\n" + marker, 1)
    html_path.write_text(updated, encoding="utf-8")


def build_slide_segments(slides_by_index: dict[int, dict[str, Any]], indices: list[int], section_start: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx in indices:
        slide = slides_by_index.get(idx)
        if not slide:
            continue
        segment = slide["segment"]
        start = float(segment["start"])
        end = float(segment["end"])
        out.append({
            "slide": idx,
            "global_start": round(start, 3),
            "global_end": round(end, 3),
            "relative_start": round(start - section_start, 3),
            "relative_end": round(end - section_start, 3),
            "clip": f"{MEDIA_DIR}/slide_clips/slide-{idx:02d}.mp4",
        })
    return out


def slide_targets_are_objects(sec: dict[str, Any]) -> bool:
    slides = sec.get("slides")
    return isinstance(slides, list) and all(
        isinstance(item, dict) and item.get("slide_index") is not None
        for item in slides
    )


def ensure_slide_targets(
    sec: dict[str, Any],
    indices: list[int],
    alignment_slides: dict[int, dict[str, Any]],
) -> None:
    """Keep the viewer-facing `slides` field in target-object form."""
    if slide_targets_are_objects(sec):
        return
    targets: list[dict[str, Any]] = []
    for idx in indices:
        slide = alignment_slides.get(idx, {})
        targets.append(
            {
                "slide_index": idx,
                "slide_id": slide.get("id", f"slide-{idx}"),
                "target": f"#slide-{idx}",
            }
        )
    sec["slides"] = targets


def slide_indices_for_media(sec: dict[str, Any]) -> list[int]:
    raw = sec.get("slide_indices")
    if isinstance(raw, list) and raw:
        return [int(item) for item in raw]
    slides = sec.get("slides")
    if not isinstance(slides, list):
        return []
    indices: list[int] = []
    for item in slides:
        if isinstance(item, dict) and item.get("slide_index") is not None:
            indices.append(int(item["slide_index"]))
        elif isinstance(item, int):
            indices.append(int(item))
    return indices


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--viewer-dir", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path,
                        help="No-subtitle MP4, normally <video_outdir>/video_no_subtitles.mp4.")
    parser.add_argument("--captions-vtt", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--section-tail-seconds", type=float, default=0.9,
                        help="Silent freeze tail appended to section clips (default: 0.9s).")
    parser.add_argument("--skip-media", action="store_true",
                        help="Only update content_alignment.json and reel.html.")
    parser.add_argument("--allow-burned-subtitle-video", action="store_true",
                        help="Allow <video_outdir>/video.mp4 as the reel video source. This can duplicate subtitles when CC is enabled.")
    args = parser.parse_args()

    viewer_dir = args.viewer_dir.resolve()
    timeline = read_json(args.timeline.resolve())
    alignment_path = viewer_dir / "content_alignment.json"
    if not alignment_path.is_file():
        sys.exit(f"[timeline_media] viewer content_alignment.json not found: {alignment_path}")
    alignment = read_json(alignment_path)
    if not isinstance(alignment, dict) or not isinstance(alignment.get("sections"), list):
        sys.exit(f"[timeline_media] invalid content_alignment.json: {alignment_path}")
    alignment["viewer_version"] = VIEWER_VERSION
    alignment["template_version"] = TEMPLATE_VERSION

    timeline_sections = {str(sec.get("id")): sec for sec in timeline.get("sections", []) if isinstance(sec, dict)}
    slides_by_index = {int(slide["index"]): slide for slide in timeline.get("slides", []) if isinstance(slide, dict) and slide.get("index") is not None}
    alignment_slides = {
        int(slide["index"]): slide
        for slide in alignment.get("slides", [])
        if isinstance(slide, dict) and slide.get("index") is not None
    }
    all_slide_indices = sorted(slides_by_index)
    media_dir = viewer_dir / MEDIA_DIR
    video_path = args.video.resolve()
    if looks_like_burned_final_video(video_path) and not args.allow_burned_subtitle_video:
        no_subtitle_candidate = video_path.with_name("video_no_subtitles.mp4")
        sys.exit(
            "[timeline_media] refusing the burned-in subtitle video.mp4 as reel video source. "
            "paper2reel already provides toggleable VTT captions, so using the burned-in final MP4 "
            "can show duplicate subtitles. Use "
            f"{no_subtitle_candidate} for --video, or pass --allow-burned-subtitle-video only for a user-approved degraded run."
        )
    artifacts = alignment.setdefault("artifacts", {})
    if isinstance(artifacts, dict):
        artifacts["video"] = f"{MEDIA_DIR}/video.mp4"
        artifacts["video_source_kind"] = "raw_pre_subtitle" if not args.allow_burned_subtitle_video else "burned_subtitle_override"
        artifacts["caption_delivery"] = "sidecar_vtt_toggle"
        if args.captions_vtt:
            artifacts["captions"] = f"{MEDIA_DIR}/captions/video.vtt"

    for sec in alignment["sections"]:
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or "")
        if sid == "title":
            start = 0.0
            end = float(timeline.get("actual_seconds") or max(float(s["segment"]["end"]) for s in slides_by_index.values()))
            sec["segment"] = {"start": round(start, 3), "end": round(end, 3), "slides": all_slide_indices}
            sec["slide_indices"] = all_slide_indices
            ensure_slide_targets(sec, all_slide_indices, alignment_slides)
            sec["clip"] = f"{MEDIA_DIR}/clips/title.mp4"
            if args.captions_vtt:
                sec["captions"] = f"{MEDIA_DIR}/captions/clips/title.vtt"
            sec["clip_seconds"] = round(end - start, 3)
            sec["slide_segments"] = build_slide_segments(slides_by_index, all_slide_indices, start)
            continue
        timeline_sec = timeline_sections.get(sid)
        if not timeline_sec:
            continue
        indices = [int(i) for i in timeline_sec.get("slide_indices", [])]
        start = float(timeline_sec["start"])
        end = float(timeline_sec["end"])
        sec["segment"] = {"start": round(start, 3), "end": round(end, 3), "slides": indices}
        sec["slide_indices"] = indices
        ensure_slide_targets(sec, indices, alignment_slides)
        sec["clip"] = f"{MEDIA_DIR}/clips/{sid}.mp4"
        if args.captions_vtt:
            sec["captions"] = f"{MEDIA_DIR}/captions/clips/{sid}.vtt"
        sec["source_clip_seconds"] = round(end - start, 3)
        sec["natural_tail_seconds"] = max(0.0, round(args.section_tail_seconds, 3))
        sec["clip_seconds"] = round(end - start + max(0.0, args.section_tail_seconds), 3)
        sec["clip_strategy"] = "complete_slide_concat_with_freeze_tail"
        sec["slide_segments"] = build_slide_segments(slides_by_index, indices, start)

    notes = [str(note) for note in alignment.get("notes", []) if isinstance(note, str)]
    notes = [note for note in notes if "seek to approximate section start/end" not in note]
    media_note = (
        "Section videos are composed from complete timeline slide clips with a "
        "short silent freeze tail; timestamps come from paper2video timeline.json."
    )
    if media_note not in notes:
        notes.append(media_note)
    alignment["notes"] = notes

    write_json(alignment_path, alignment)
    update_inline_alignment(viewer_dir / "reel.html", alignment)

    if not args.skip_media:
        media_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(video_path, media_dir / "video.mp4")
        cues = read_vtt(args.captions_vtt.resolve() if args.captions_vtt else None)
        if cues:
            crop_vtt(cues, 0.0, float(timeline.get("actual_seconds") or 0.0), media_dir / "captions" / "video.vtt")
        for idx, slide in slides_by_index.items():
            segment = slide["segment"]
            start = float(segment["start"])
            end = float(segment["end"])
            cut_video(args.ffmpeg, video_path, start, end, media_dir / "slide_clips" / f"slide-{idx:02d}.mp4")
            if cues:
                crop_vtt(cues, start, end, media_dir / "captions" / "slide_clips" / f"slide-{idx:02d}.vtt")
        for sec in alignment["sections"]:
            if not isinstance(sec, dict) or not sec.get("clip"):
                continue
            if sec.get("id") == "title":
                out = viewer_dir / str(sec["clip"])
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(video_path, out)
                if cues:
                    crop_vtt(
                        cues,
                        0.0,
                        float(timeline.get("actual_seconds") or 0.0),
                        media_dir / "captions" / "clips" / "title.vtt",
                    )
                continue
            slide_indices = slide_indices_for_media(sec)
            slide_clips = [media_dir / "slide_clips" / f"slide-{idx:02d}.mp4" for idx in slide_indices]
            if not slide_clips:
                continue
            out = viewer_dir / str(sec["clip"])
            compose_section_clip(args.ffmpeg, slide_clips, out, max(0.0, args.section_tail_seconds))
            if cues:
                seg = sec.get("segment") or {}
                start = float(seg.get("start") or 0.0)
                end = float(seg.get("end") or start)
                crop_vtt(cues, start, end, media_dir / "captions" / "clips" / f"{sec['id']}.vtt")
        update_inline_captions(viewer_dir)
    else:
        update_inline_captions(viewer_dir)

    print(f"[timeline_media] updated {alignment_path}")
    print(f"[timeline_media] sections from timeline: {len(timeline_sections)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
