#!/usr/bin/env python3
"""
notes_to_script.py — convert ppt-master per-slide notes into the narration
script JSON shape expected by paper2poster's `scripts/generate_audio.py`.

Pipeline position (inside paper2video):
    Stage 1 (ppt-master) writes <project>/notes/<slide>.md, one file per slide.
    THIS SCRIPT reads them and emits <project>/audio/script.json with shape:

        {
          "voice": "alloy",
          "model": "tts",
          "sections": [
            {"id": "<slide_stem>", "heading": "<H1 or fallback>", "text": "..."},
            ...
          ]
        }

    Stage 2b feeds that JSON to paper2poster's generate_audio.py to produce
    <project>/audio/<slide_stem>.mp3 per slide.

Why id == slide stem:
    paper2poster's TTS script names each MP3 after `section.id`. By pinning
    the id to the slide-file stem, every MP3 lines up 1-to-1 with its slide,
    in slide order, with no separate manifest to track. Pass the resulting
    script JSON to render_video.py via `--script-json` so the compositor uses
    the same sections order.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from duration_planner import build_duration_rewrite_request, plan_script_sections

VOICE_CHOICES = ("alloy", "echo", "fable", "onyx", "nova", "shimmer")

# Reasonable defaults: drop ppt-master conventions like 'Slide 5:' or '第5页:'
SLIDE_PREFIX_RE = re.compile(
    r"^\s*(?:slide|page)\s*\d*\s*[:：\-—]\s*"
    r"|^\s*第\s*\d+\s*[页页]\s*[:：\-—]\s*",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
HR_RE = re.compile(r"^\s*[-*]{3,}\s*$")


def strip_markdown(text: str, drop_first_heading: bool = True) -> str:
    """Strip the markdown formatting that confuses TTS prosody.

    The goal isn't a perfect markdown parser — it's to remove the syntactic
    noise (asterisks, backticks, link brackets, list bullets) so the synth
    voice doesn't read literal punctuation. Horizontal rules are dropped.

    `drop_first_heading=True` removes the leading H1 (and any "Slide N:" /
    "第 N 页：" prefix) from the spoken text — that line is captured as the
    section's heading metadata, and announcing it again before each slide
    is jarring narration. Subsequent in-body headings are flattened to
    plain sentences (rare in ppt-master notes, but cheap to handle).
    """
    out_lines: list[str] = []
    in_code = False
    first_heading_dropped = not drop_first_heading
    for raw in text.splitlines():
        line = raw.rstrip()

        # Fenced code blocks: skip entirely. Spoken code rarely lands.
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        if HR_RE.match(line):
            continue

        m = HEADING_RE.match(line)
        if m:
            if not first_heading_dropped:
                # First heading in the doc → owned by `heading`, drop here.
                first_heading_dropped = True
                continue
            line = m.group(2)

        # Bullet markers, blockquote markers, numbered list markers
        line = re.sub(r"^\s*[-*+]\s+", "", line)
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)
        line = re.sub(r"^\s*>\s?", "", line)

        # Inline emphasis & code
        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"__([^_]+)__", r"\1", line)
        line = re.sub(r"\*([^*]+)\*", r"\1", line)
        line = re.sub(r"_([^_]+)_", r"\1", line)

        # Markdown links / images: keep the visible label
        line = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)

        # HTML tags — strip
        line = re.sub(r"<[^>]+>", "", line)

        out_lines.append(line)

    # Collapse runs of blank lines into a single paragraph break.
    cleaned: list[str] = []
    blank = False
    for ln in out_lines:
        if not ln.strip():
            if not blank and cleaned:
                cleaned.append("")
            blank = True
        else:
            cleaned.append(ln.strip())
            blank = False

    return "\n".join(cleaned).strip()


def derive_heading(stem: str, body_first_line: str) -> str:
    """Pick a human-readable heading for the section.

    Preference order:
      1. The first markdown heading line, with any 'Slide N:' prefix removed.
      2. The slide stem itself, prettified (underscores → spaces, title case
         for ASCII; left alone for CJK).
    """
    candidate = body_first_line.strip()
    candidate = SLIDE_PREFIX_RE.sub("", candidate)
    if candidate:
        return candidate

    pretty = stem.replace("_", " ").replace("-", " ").strip()
    # Drop a leading slide number like "01 " for the heading display.
    pretty = re.sub(r"^\d+\s+", "", pretty)
    if re.search(r"[一-鿿]", pretty):  # CJK — leave as-is
        return pretty
    return pretty.title() if pretty else stem


def first_heading(text: str) -> str:
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            return m.group(2)
    return ""


def collect_notes(project_path: Path) -> list[Path]:
    notes_dir = project_path / "notes"
    if not notes_dir.is_dir():
        sys.exit(f"[notes_to_script] no notes/ directory under {project_path}.\n"
                 f"  Run ppt-master through Step 7.1 first, or run "
                 f"`total_md_split.py {project_path}` if only total.md exists.")

    md_files = sorted(p for p in notes_dir.glob("*.md") if p.name != "total.md")
    if not md_files:
        sys.exit(f"[notes_to_script] notes/ exists but has no per-slide *.md files.\n"
                 f"  Did you forget `total_md_split.py {project_path}`?")
    return md_files


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[notes_to_script] file not found: {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"[notes_to_script] invalid JSON {path}: {exc}")


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
        sys.exit(f"[notes_to_script] no usable rewrites found in {path}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("project_path", help="ppt-master project root (contains notes/, svg_output/, exports/)")
    ap.add_argument("--voice", default="alloy", choices=VOICE_CHOICES,
                    help="Azure OpenAI TTS voice (default: alloy)")
    ap.add_argument("--model", default="tts", help="TTS model name (default: tts)")
    ap.add_argument("--out", default=None,
                    help="Output JSON path (default: <project>/audio/script.json)")
    ap.add_argument("--min-chars", type=int, default=10,
                    help="Skip slides whose cleaned text is shorter than this. "
                         "Default 10 — keeps near-empty divider slides out of the audio set.")
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
                    help="keep preserves slide/audio count; auto may drop low-priority sections "
                         "only when the deck can be made to match.")
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

    project_path = Path(args.project_path).resolve()
    if not project_path.is_dir():
        sys.exit(f"[notes_to_script] project path not found: {project_path}")

    md_files = collect_notes(project_path)

    out_path = Path(args.out) if args.out else project_path / "audio" / "script.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sections = []
    skipped = []
    for md in md_files:
        raw = md.read_text(encoding="utf-8")
        body = strip_markdown(raw)
        if len(body) < args.min_chars:
            skipped.append(md.stem)
            continue

        heading = derive_heading(md.stem, first_heading(raw))
        sections.append({
            "id": md.stem,
            "heading": heading,
            "text": body,
        })

    if not sections:
        sys.exit("[notes_to_script] no usable notes survived (all under min-chars)."
                 " Lower --min-chars or check that notes/*.md actually contain prose.")

    rewrite_texts = load_rewrite_texts(Path(args.duration_rewrite_in).resolve()) if args.duration_rewrite_in else None
    try:
        sections, duration_plan = plan_script_sections(
            sections,
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
        sys.exit(f"[notes_to_script] duration planning failed: {exc}")

    payload = {"voice": args.voice, "model": args.model, "sections": sections}
    if duration_plan is not None and duration_plan.get("status") == "needs_script_rewrite":
        request_path = (
            Path(args.duration_rewrite_request_out).resolve()
            if args.duration_rewrite_request_out
            else out_path.parent / "duration_rewrite_request.json"
        )
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(
            json.dumps(build_duration_rewrite_request(duration_plan, sections), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        plan_path = Path(args.duration_plan_out).resolve() if args.duration_plan_out else out_path.parent / "duration_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(duration_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sys.exit(
            "[notes_to_script] target duration requires semantic script rewrite; "
            f"wrote request to {request_path}. Fill it, rerun with --duration-rewrite-in, "
            "then generate TTS."
        )
    if duration_plan is not None and duration_plan.get("status") != "within_tolerance":
        plan_path = Path(args.duration_plan_out).resolve() if args.duration_plan_out else out_path.parent / "duration_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(duration_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sys.exit(
            f"[notes_to_script] duration plan is still outside tolerance "
            f"(status={duration_plan.get('status')}); adjust the semantic rewrite before TTS."
        )

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[notes_to_script] wrote {len(sections)} sections to {out_path}")
    if duration_plan is not None:
        plan_path = Path(args.duration_plan_out).resolve() if args.duration_plan_out else out_path.parent / "duration_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(duration_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"[notes_to_script] duration plan {duration_plan['status']}: "
            f"target={duration_plan['target_seconds']:.1f}s, "
            f"estimate={duration_plan['estimated_video_seconds']:.1f}s "
            f"(delta={duration_plan['estimated_delta_seconds']:+.1f}s) -> {plan_path}"
        )
    if skipped:
        print(f"[notes_to_script] skipped {len(skipped)} short/empty slides: {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
