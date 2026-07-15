#!/usr/bin/env python3
"""Prepare paper2video narration inputs from a paper2assets package.

The script reads narration from a paper2assets bundle. It supports the current
v2 assets layout (<bundle>/assets/meta/narration.json) and falls back to the
legacy flat layout (<bundle>/narration.json) for old demo bundles. It writes a
generate_audio.py-compatible script JSON and can materialize notes/<id>.md
files so the subtitle step has human-readable cue text even when the deck did
not come from ppt-master.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from duration_planner import build_duration_rewrite_request, plan_script_sections

VOICE_CHOICES = ("alloy", "echo", "fable", "onyx", "nova", "shimmer")


def bundle_file(bundle_dir: Path, key: str, *, legacy_name: str | None = None) -> Path:
    """Resolve a paper2assets file path from manifest, v2 assets layout, or legacy flat layout."""
    manifest_path = bundle_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        if isinstance(manifest, dict):
            files = manifest.get("files")
            if isinstance(files, dict) and isinstance(files.get(key), str):
                candidate = bundle_dir / files[key]
                if candidate.is_file():
                    return candidate

    defaults = {
        "narration": "assets/meta/narration.json",
        "sections": "assets/meta/sections.json",
        "paper_spec": "assets/meta/paper_spec.md",
        "text": "assets/meta/text.txt",
        "metadata": "assets/meta/metadata.json",
        "figures": "assets/meta/figures.json",
        "captions": "assets/meta/captions.json",
    }
    if key in defaults:
        candidate = bundle_dir / defaults[key]
        if candidate.is_file():
            return candidate

    legacy = legacy_name or f"{key}.json"
    return bundle_dir / legacy


def bundle_subdir(bundle_dir: Path, key: str, *, create: bool = False) -> Path:
    defaults = {
        "audio": "assets/audio",
        "notes": "assets/meta/notes",
        "meta": "assets/meta",
    }
    rel = defaults.get(key, key)
    path = bundle_dir / rel
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[assets_to_script] file not found: {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"[assets_to_script] invalid JSON {path}: {exc}")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_rewrite_texts(path: Path) -> dict[str, str]:
    payload = load_json(path)
    out: dict[str, str] = {}
    if isinstance(payload, dict) and isinstance(payload.get("sections"), list):
        for sec in payload["sections"]:
            if not isinstance(sec, dict):
                continue
            sid = str(sec.get("id") or "").strip()
            text = str(sec.get("text") or "").strip()
            if sid and text:
                out[sid] = text
    elif isinstance(payload, dict):
        for sid, text in payload.items():
            if isinstance(text, str) and text.strip():
                out[str(sid)] = text.strip()
    if not out:
        sys.exit(f"[assets_to_script] no usable rewrites found in {path}")
    return out


def safe_filename_id(section_id: str) -> str:
    if not section_id or "/" in section_id or "\\" in section_id or section_id in {".", ".."}:
        sys.exit(f"[assets_to_script] unsafe section id for an audio filename: {section_id!r}")
    return section_id


def index_sections(sections_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(sec.get("id")): sec for sec in sections_doc.get("sections", []) if sec.get("id")}


def plain_text(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def section_note_text(narration_sec: dict[str, Any], section_sec: dict[str, Any] | None) -> str:
    heading = str(narration_sec.get("heading") or narration_sec.get("id") or "Section")
    spoken = plain_text(str(narration_sec.get("text") or ""))

    if not section_sec:
        return f"# {heading}\n\n{spoken}\n"

    necessary = plain_text(str(section_sec.get("necessary") or ""))
    additional = plain_text(str(section_sec.get("additional") or ""))
    parts = [f"# {heading}"]
    if necessary:
        parts.append(f"Core claim: {necessary}")
    if additional:
        parts.append(f"Supporting detail: {additional}")
    if spoken:
        parts.append(f"Narration: {spoken}")
    return "\n\n".join(parts).rstrip() + "\n"


def select_sections(narration: dict[str, Any], ids: list[str] | None, exclude_title: bool) -> list[dict[str, Any]]:
    sections = narration.get("sections") or []
    if not isinstance(sections, list) or not sections:
        sys.exit("[assets_to_script] narration.json has no sections array")

    by_id = {str(sec.get("id")): sec for sec in sections if sec.get("id")}
    if ids:
        missing = [sid for sid in ids if sid not in by_id]
        if missing:
            sys.exit(f"[assets_to_script] requested ids not found in narration.json: {missing}")
        selected = [by_id[sid] for sid in ids]
    else:
        selected = [sec for sec in sections if sec.get("id")]

    if exclude_title:
        selected = [sec for sec in selected if sec.get("id") != "title"]
    if not selected:
        sys.exit("[assets_to_script] no sections selected")
    return selected


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("assets_dir", help="paper2assets package root")
    ap.add_argument("--out", default=None,
                    help="Output script JSON (default: <bundle_dir>/assets/audio/script.json)")
    ap.add_argument("--notes-dir", default=None,
                    help="Directory for notes/<id>.md (default: <bundle_dir>/assets/meta/notes)")
    ap.add_argument("--ids", default=None,
                    help="Comma-separated section ids to include, in slide order. "
                         "Default: narration.json order.")
    ap.add_argument("--exclude-title", action="store_true",
                    help="Drop the title narration entry when the deck has no title slide.")
    ap.add_argument("--voice", choices=VOICE_CHOICES, default=None,
                    help="Azure OpenAI TTS voice to write into script JSON.")
    ap.add_argument("--model", default=None,
                    help="TTS model/deployment name to write into script JSON.")
    ap.add_argument("--no-notes", action="store_true",
                    help="Only write script JSON; do not materialize notes/*.md.")
    ap.add_argument("--target-minutes", type=float, default=None,
                    help="Target final video duration in minutes. When semantic rewriting is "
                         "needed, write a rewrite request instead of truncating narration.")
    ap.add_argument("--duration-tolerance-seconds", type=float, default=30.0,
                    help="Allowed target duration error for the plan (default: 30s).")
    ap.add_argument("--words-per-minute", type=float, default=145.0,
                    help="Estimated TTS speaking rate used before audio exists (default: 145).")
    ap.add_argument("--start-pad", type=float, default=0.5,
                    help="Planned leading silence used by render_video.py (default: 0.5s).")
    ap.add_argument("--pad-tail", type=float, default=0.3,
                    help="Planned trailing silence per slide used by render_video.py (default: 0.3s).")
    ap.add_argument("--min-section-words", type=int, default=18,
                    help="Minimum narration word budget per kept section (default: 18).")
    ap.add_argument("--duration-section-mode", choices=("keep", "auto"), default="keep",
                    help="keep preserves selected section count; auto may drop low-priority "
                         "sections when the minimum budgets cannot fit the target.")
    ap.add_argument("--duration-plan-out", default=None,
                    help="Output duration plan JSON (default: alongside script.json when "
                         "--target-minutes is set).")
    ap.add_argument("--duration-rewrite-in", default=None,
                    help="JSON with semantically rewritten section texts from a prior "
                         "duration_rewrite_request.json.")
    ap.add_argument("--duration-rewrite-request-out", default=None,
                    help="Output rewrite request when target duration requires semantic "
                         "script rewriting (default: alongside script.json).")
    ap.add_argument("--allow-extractive-duration-draft", action="store_true",
                    help="Experimental only: allow old sentence-boundary extractive drafts "
                         "instead of requiring semantic rewrite.")
    args = ap.parse_args()

    assets_dir = Path(args.assets_dir).resolve()
    if not assets_dir.is_dir():
        sys.exit(f"[assets_to_script] assets_dir not found: {assets_dir}")

    narration_path = bundle_file(assets_dir, "narration")
    sections_path = bundle_file(assets_dir, "sections")
    narration = load_json(narration_path)
    sections_doc = load_json(sections_path) if sections_path.exists() else {}
    sections_by_id = index_sections(sections_doc if isinstance(sections_doc, dict) else {})

    ids = [part.strip() for part in args.ids.split(",") if part.strip()] if args.ids else None
    selected = select_sections(narration, ids, args.exclude_title)

    script_sections = []
    for sec in selected:
        sid = safe_filename_id(str(sec["id"]))
        text = plain_text(str(sec.get("text") or ""))
        if not text:
            sys.exit(f"[assets_to_script] selected section has empty narration text: {sid}")
        script_sections.append({
            "id": sid,
            "heading": str(sec.get("heading") or sid),
            "text": text,
        })

    rewrite_texts = load_rewrite_texts(Path(args.duration_rewrite_in).resolve()) if args.duration_rewrite_in else None
    try:
        script_sections, duration_plan = plan_script_sections(
            script_sections,
            target_minutes=args.target_minutes,
            tolerance_seconds=args.duration_tolerance_seconds,
            words_per_minute=args.words_per_minute,
            start_pad=args.start_pad,
            pad_tail=args.pad_tail,
            min_section_words=args.min_section_words,
            section_mode=args.duration_section_mode,
            rewrite_texts=rewrite_texts,
            allow_extractive_draft=args.allow_extractive_duration_draft,
        )
    except ValueError as exc:
        sys.exit(f"[assets_to_script] duration planning failed: {exc}")

    out_path = Path(args.out).resolve() if args.out else bundle_subdir(assets_dir, "audio", create=True) / "script.json"
    if duration_plan is not None and duration_plan.get("status") == "needs_script_rewrite":
        request_path = (
            Path(args.duration_rewrite_request_out).resolve()
            if args.duration_rewrite_request_out
            else out_path.parent / "duration_rewrite_request.json"
        )
        write_json(request_path, build_duration_rewrite_request(duration_plan, script_sections))
        plan_path = Path(args.duration_plan_out).resolve() if args.duration_plan_out else out_path.parent / "duration_plan.json"
        write_json(plan_path, duration_plan)
        sys.exit(
            "[assets_to_script] target duration requires semantic script rewrite; "
            f"wrote request to {request_path}. Fill it, rerun with --duration-rewrite-in, "
            "then generate TTS."
        )
    if duration_plan is not None and duration_plan.get("status") != "within_tolerance":
        plan_path = Path(args.duration_plan_out).resolve() if args.duration_plan_out else out_path.parent / "duration_plan.json"
        write_json(plan_path, duration_plan)
        sys.exit(
            f"[assets_to_script] duration plan is still outside tolerance "
            f"(status={duration_plan.get('status')}); adjust the semantic rewrite before TTS."
        )

    payload: dict[str, Any] = {"sections": script_sections}
    voice = args.voice or narration.get("voice")
    model = args.model or narration.get("model")
    if voice:
        payload["voice"] = voice
    if model:
        payload["model"] = model

    write_json(out_path, payload)
    print(f"[assets_to_script] wrote {len(script_sections)} sections to {out_path}")

    if duration_plan is not None:
        plan_path = Path(args.duration_plan_out).resolve() if args.duration_plan_out else out_path.parent / "duration_plan.json"
        write_json(plan_path, duration_plan)
        print(
            f"[assets_to_script] duration plan {duration_plan['status']}: "
            f"target={duration_plan['target_seconds']:.1f}s, "
            f"estimate={duration_plan['estimated_video_seconds']:.1f}s "
            f"(delta={duration_plan['estimated_delta_seconds']:+.1f}s) -> {plan_path}"
        )

    if not args.no_notes:
        notes_dir = Path(args.notes_dir).resolve() if args.notes_dir else bundle_subdir(assets_dir, "notes", create=True)
        notes_dir.mkdir(parents=True, exist_ok=True)
        for sec in script_sections:
            sid = safe_filename_id(str(sec["id"]))
            note = section_note_text(sec, sections_by_id.get(sid))
            (notes_dir / f"{sid}.md").write_text(note, encoding="utf-8")
        print(f"[assets_to_script] wrote notes to {notes_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
