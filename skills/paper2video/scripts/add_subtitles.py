#!/usr/bin/env python3
"""
add_subtitles.py — generate subtitles from per-slide narration notes and
either burn them into the video pixels (hardsub, default) or mux them as a
soft mov_text track (`--soft`).

Pipeline position (optional post-step for paper2video):
    Inputs:
        <project_path>     : ppt-master project root (must contain notes/ + audio/)
        --mp4              : the MP4 produced by render_video.py
        --out              : destination for the subtitled MP4
        --srt-out          : (optional) where to also save the standalone .srt
        --vtt-out          : (optional) where to also save the standalone .vtt
        --start-pad        : MUST match render_video.py's --start-pad
        --pad-tail         : MUST match render_video.py's --pad-tail

    Steps:
        1. Read subtitle text from --script-json sections order when provided
           (falling back to notes/<id>.md if present), otherwise pair sorted
           notes/*.md with sorted audio/*.mp3 for legacy ppt-master projects.
        2. Probe each audio/<id>.mp3 to get the spoken duration of that slide.
        3. Split each slide's text into sentence-level cues (~80 chars each).
        4. Distribute the slide's audio duration across its cues proportional
           to character count, snapping cue boundaries inside [start, end].
        5. Walk slides in sorted order, advancing the clock by
           pad + audio_duration + tail to mirror render_video.py's layout.
        6. Probe the bottom band of each slide for luminance; pick black text
           on light slides and white text on dark ones. Add the opposite color
           as an outline so the text is legible even when the picker is on
           a borderline slide.
        7. Write the cues to <project>/exports/<stem>.srt and .vtt (always —
           useful as YouTube/archive sidecars and timeline/visualization input).
        8. Default (hardsub): convert cues to an ASS file with a translucent
           dark caption box and burn it into the video with ffmpeg's `ass=`
           filter. The video is re-encoded (libx264 CRF 20 by default),
           audio is stream-copied. Output:
               <project>/exports/<stem>_subbed.mp4
           The subtitles are now part of every frame — no player toggle, no
           font-rendering surprise on phones that don't honor mov_text.
        9. `--soft` mode: skip burn-in, stream-copy video+audio, and mux the
           SRT as a `mov_text` track. Toggleable in players that honor it,
           invisible on players that don't. Output filename unchanged.

Why hardsub by default (this turn's contract — "make the script part of the
video file"):
    Soft mov_text is a polite default for English-speaking desktop viewers,
    but in practice: mobile share targets (WeChat, Twitter, Slack previews),
    inline-played embeds on news sites, and most VR / signage stacks ignore
    the soft track entirely. Burning the cues into pixels guarantees the
    captions are seen by every viewer on every player. The cost is a full
    re-encode of the video stream (~2–3× the previous render time) and a
    decision baked into the file. That tradeoff is what the user is asking
    for when they say "part of the video file".

Why ASS instead of just feeding SRT to the `subtitles=` filter:
    libass's SRT parser silently drops some `<font color>` corners, and we
    rely on per-slide colors to keep cues legible. Converting our cues to
    a tiny ASS file with explicit `{\\c&Hbbggrr&\\3c&Hbbggrr&}` overrides
    per dialogue line gives us deterministic per-cue color + outline. The
    SRT is still emitted as a sidecar.

Per-slide text color (white vs. black) for readability:
    Different slides may have different background colors (white hero pages,
    dark navy cover pages, photographic backgrounds, etc.). To keep the
    subtitle text legible on every slide we sample one frame per slide at
    the slide's midpoint timestamp, measure the mean luminance of the
    bottom band where the cues actually render, and pick the higher-
    contrast color (`#FFFFFF` on dark backgrounds, `#000000` on light ones).

Timing assumptions:
    render_video.py lays out the timeline as:
        [start_pad of silence] + [audio_1 + pad_tail] + [audio_2 + pad_tail] + ...
    This script reproduces that math exactly. If you change start_pad or
    pad_tail when calling render_video.py, pass the SAME values here or the
    subtitles will drift relative to the audio.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
import json


# ---------------------------------------------------------------------------
# Tool discovery — mirrors render_video.py so we accept the same fallback
# ---------------------------------------------------------------------------

def _which(name: str) -> str | None:
    return shutil.which(name)


def _imageio_ffmpeg_binary() -> str | None:
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def find_ffmpeg_pair() -> tuple[str, str]:
    """Return (ffmpeg, ffprobe) paths or exit with guidance.

    Same fallback policy as render_video.py: prefer explicit env binaries, then
    the static `imageio_ffmpeg` binary, then system binaries. The static binary
    lacks ffprobe, so durations are probed by parsing `ffmpeg -i` stderr.
    """
    env_ffmpeg = os.getenv("PAPER2VIDEO_FFMPEG") or os.getenv("FFMPEG_BINARY")
    if env_ffmpeg:
        env_path = Path(env_ffmpeg).expanduser()
        if env_path.is_file():
            env_ffprobe = os.getenv("PAPER2VIDEO_FFPROBE")
            if env_ffprobe and Path(env_ffprobe).expanduser().is_file():
                return str(env_path), str(Path(env_ffprobe).expanduser())
            return str(env_path), str(env_path)

    fallback = _imageio_ffmpeg_binary()
    if fallback:
        return fallback, fallback

    ffmpeg = _which("ffmpeg")
    ffprobe = _which("ffprobe")
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe

    sys.exit(
        "[add_subtitles] ffmpeg/ffprobe not found and imageio_ffmpeg is not installed.\n"
        "Pick one:\n"
        "  • System install:  sudo apt-get install -y ffmpeg\n"
        "  • Python fallback: pip install imageio-ffmpeg\n"
    )


def probe_duration(audio: Path, ffprobe: str, ffmpeg: str) -> float:
    """Return audio duration in seconds; falls back to parsing ffmpeg stderr."""
    if ffprobe != ffmpeg:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
            capture_output=True, text=True,
        )
        if out.returncode == 0 and out.stdout.strip():
            return float(out.stdout.strip())

    out = subprocess.run([ffmpeg, "-i", str(audio)], capture_output=True, text=True)
    m = re.search(r"Duration:\s+(\d+):(\d+):([\d.]+)", out.stderr)
    if not m:
        sys.exit(f"[add_subtitles] could not probe duration for {audio.name}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


# ---------------------------------------------------------------------------
# Text → cue chunks
# ---------------------------------------------------------------------------

# Abbreviations whose trailing period is NOT a sentence boundary. Conservative
# list — better to under-split than to break in the middle of "e.g." or
# "Ph.D.". Add to taste; the test is "would a reader pause here? if no, list it".
ABBREVS = (
    "e.g.", "i.e.", "etc.", "vs.", "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.",
    "St.", "Ph.D.", "U.S.", "U.K.", "Fig.", "Eq.", "No.", "Ref.", "Sec.",
)

# Markdown line-level prefixes we should peel off before treating the body
# as spoken prose. ppt-master's per-slide notes are usually already plain
# text (total_md_split.py drops the H1 heading), but a stray bullet or a
# blockquote can sneak through.
_BULLET_RE = re.compile(r"^\s*[-*+]\s+")
_NUMLIST_RE = re.compile(r"^\s*\d+[.)]\s+")
_QUOTE_RE = re.compile(r"^\s*>\s?")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
_HR_RE = re.compile(r"^\s*[-*]{3,}\s*$")


def strip_markdown(text: str) -> str:
    """Cheap markdown → plain prose. Mirrors notes_to_script.strip_markdown
    closely enough for cue splitting; we don't need perfect fidelity here.
    """
    out = []
    in_code = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or _HR_RE.match(line):
            continue
        line = _HEADING_RE.sub("", line)
        line = _BULLET_RE.sub("", line)
        line = _NUMLIST_RE.sub("", line)
        line = _QUOTE_RE.sub("", line)
        # Inline emphasis/code/links — strip syntax, keep text.
        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"__([^_]+)__", r"\1", line)
        line = re.sub(r"\*([^*]+)\*", r"\1", line)
        line = re.sub(r"_([^_]+)_", r"\1", line)
        line = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"<[^>]+>", "", line)
        out.append(line)
    # Collapse to single space-separated paragraph; subtitles don't honor
    # line breaks in source notes.
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def _split_sentences(text: str) -> list[str]:
    """Split on `. `, `? `, `! ` when the next char looks like a sentence start.

    Conservative: refuses to split right after a known abbreviation (e.g.,
    "e.g.", "Dr.") and refuses to split when the period sits between digits
    (decimals, version numbers, "IPC 100." mid-list).
    """
    # First, mask the periods inside known abbreviations with U+FFFD so the
    # splitter can't trip on them. We restore them after splitting.
    masked = text
    for a in ABBREVS:
        masked = masked.replace(a, a.replace(".", "�"))

    # Also mask decimal points (digit.digit) so "1.5" doesn't split.
    masked = re.sub(r"(\d)\.(\d)", r"\1�\2", masked)

    parts = re.split(r"(?<=[.!?])\s+(?=[\"'(A-Z0-9])", masked)
    parts = [p.replace("�", ".") for p in parts]
    return [p.strip() for p in parts if p.strip()]


def _chunk_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """Break a too-long sentence at clause boundaries (commas, semicolons,
    em-dashes / en-dashes / hyphen-surrounded-by-spaces). Falls back to
    word-level chunking if no clause breaks help.
    """
    if len(sentence) <= max_chars:
        return [sentence]

    # Clause splitter — keep the punctuation glued to the left side.
    pieces = re.split(r"(?<=[,;])\s+|\s+[—–-]\s+", sentence)
    pieces = [p.strip() for p in pieces if p and p.strip()]

    # Reassemble greedily up to max_chars.
    chunks: list[str] = []
    buf = ""
    for p in pieces:
        candidate = (buf + " " + p).strip() if buf else p
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)

    # Last-resort word chunking for any chunk still way over budget.
    final: list[str] = []
    for c in chunks:
        if len(c) <= int(max_chars * 1.4):
            final.append(c)
            continue
        words = c.split()
        cur: list[str] = []
        for w in words:
            cur.append(w)
            if len(" ".join(cur)) >= max_chars:
                final.append(" ".join(cur))
                cur = []
        if cur:
            final.append(" ".join(cur))
    return final


def split_into_cues(text: str, max_chars: int) -> list[str]:
    """Produce a list of subtitle-friendly chunks for one slide."""
    text = strip_markdown(text)
    if not text:
        return []
    sentences = _split_sentences(text)
    cues: list[str] = []
    for s in sentences:
        cues.extend(_chunk_long_sentence(s, max_chars))
    return cues


# ---------------------------------------------------------------------------
# Per-slide subtitle text color (white on dark / black on light)
# ---------------------------------------------------------------------------

# Subtitle text colors. Only white and black per the user's contract — no
# off-grays. A high-contrast pure color reads cleanly over both photographic
# and flat-fill backgrounds and degrades well on older players.
COLOR_WHITE = "#FFFFFF"
COLOR_BLACK = "#000000"

# Fraction of the frame height where mov_text actually renders. Players vary
# (QuickTime ~88%, VLC ~85%, mpv configurable) but the bottom 18%–8% band is
# almost always where the text lands. Sampling that strip — not the full
# frame — is what makes the picker robust against e.g. a dark navy header
# bar on an otherwise-white slide.
SUBTITLE_BAND_TOP = 0.78
SUBTITLE_BAND_BOTTOM = 0.96
# Side margin: skip the outer 5% to ignore page-number chips / decorative
# stripes that don't sit under the actual text.
SUBTITLE_BAND_SIDE = 0.05

# Above this mean-luma the band reads as "light" → use black text.
# 128 is the obvious midpoint but in practice 140 reads better because
# the eye weighs near-white pixels more heavily than near-black ones.
LUMA_THRESHOLD = 140.0


def extract_frame_at(mp4: Path, timestamp: float, out_png: Path, ffmpeg: str) -> bool:
    """Grab one frame from `mp4` at `timestamp` seconds. Returns True on success.

    Uses `-ss` BEFORE `-i` for fast-seek (input-side seek) — accurate enough
    for picking a subtitle color, and avoids decoding from t=0 for every
    slide which would make this O(slides²) on a 10-minute video.
    """
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-ss", f"{max(timestamp, 0):.3f}",
        "-i", str(mp4),
        "-frames:v", "1",
        "-q:v", "2",
        str(out_png),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0 and out_png.is_file() and out_png.stat().st_size > 0


def pick_color_for_frame(png_path: Path) -> tuple[str, float]:
    """Return (color_hex, mean_luma) for the subtitle band of `png_path`.

    Mean luma is BT.601-weighted (0.299 R + 0.587 G + 0.114 B), matching how
    the human eye perceives brightness — pure green looks much brighter than
    pure blue at the same intensity. The threshold compares against this
    perceptual luma, not raw RGB averages.
    """
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        sys.exit(
            "[add_subtitles] Pillow is required for per-slide color picking.\n"
            "  Install with: pip install Pillow\n"
            "  Or pass --color white|black to skip auto-pick."
        )

    with Image.open(png_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        left = int(w * SUBTITLE_BAND_SIDE)
        right = int(w * (1.0 - SUBTITLE_BAND_SIDE))
        top = int(h * SUBTITLE_BAND_TOP)
        bottom = int(h * SUBTITLE_BAND_BOTTOM)
        band = img.crop((left, top, right, bottom))

        # Downsample first — averaging 1.7M pixels per slide adds up across
        # a long deck. A 64×16 strip preserves enough fidelity for a binary
        # white-vs-black decision and is ~1000× cheaper.
        band = band.resize((64, 16), Image.BILINEAR)
        pixels = list(band.getdata())

    total_luma = 0.0
    for r, g, b in pixels:
        total_luma += 0.299 * r + 0.587 * g + 0.114 * b
    mean_luma = total_luma / len(pixels)

    color = COLOR_BLACK if mean_luma >= LUMA_THRESHOLD else COLOR_WHITE
    return color, mean_luma


def pick_slide_colors(mp4: Path, slide_midpoints: list[float],
                      ffmpeg: str, default: str | None) -> list[str]:
    """Return one color hex per slide, in order.

    `default` short-circuits the probe: if the user passed `--color white`
    or `--color black`, we honor it and skip frame extraction entirely.
    """
    if default in (COLOR_WHITE, COLOR_BLACK):
        return [default] * len(slide_midpoints)

    colors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="subtitle_probe_") as td:
        td_path = Path(td)
        for i, t in enumerate(slide_midpoints, start=1):
            frame = td_path / f"probe_{i:03d}.png"
            ok = extract_frame_at(mp4, t, frame, ffmpeg)
            if not ok:
                # If the seek failed (rare — usually only on the very last
                # second of the video), fall back to white. Better to be a
                # bit harder to read on one slide than to crash the run.
                print(f"[add_subtitles] warn: could not sample frame at t={t:.2f}s "
                      f"for slide {i}; defaulting to white text.", file=sys.stderr)
                colors.append(COLOR_WHITE)
                continue
            color, luma = pick_color_for_frame(frame)
            colors.append(color)
            label = "BLACK" if color == COLOR_BLACK else "WHITE"
            print(f"[add_subtitles] slide {i:02d}  t={t:6.2f}s  "
                  f"band luma={luma:5.1f}  →  {label}")
    return colors


# ---------------------------------------------------------------------------
# Cue timing
# ---------------------------------------------------------------------------

@dataclass
class Cue:
    index: int
    start: float
    end: float
    text: str
    color: str = COLOR_WHITE  # one of COLOR_WHITE / COLOR_BLACK


def allocate_slide_cues(cues: list[str], audio_duration: float,
                        slide_start: float,
                        min_cue_dur: float, min_gap: float) -> list[tuple[float, float, str]]:
    """Distribute one slide's audio_duration over its cue chunks.

    Cue durations are proportional to character length — long sentences get
    more screen time. Each cue gets at least `min_cue_dur` seconds so flashes
    don't blink past the viewer. After clamping, durations are rescaled to fit
    exactly into [slide_start, slide_start + audio_duration]. A tiny `min_gap`
    is reserved between adjacent cues so players don't merge them visually.
    """
    if not cues:
        return []
    if audio_duration <= 0:
        return []

    char_counts = [max(len(c), 1) for c in cues]
    total = sum(char_counts)
    raw = [audio_duration * n / total for n in char_counts]

    # Floor each cue to min_cue_dur. If the sum exceeds audio_duration we
    # have to give up the floor for some cues — accept that, otherwise the
    # last cue would spill past the slide boundary.
    floored = [max(d, min_cue_dur) for d in raw]
    if sum(floored) > audio_duration:
        # Too many cues to fit min duration — fall back to even split.
        per = max(audio_duration / len(cues), 0.4)
        floored = [per] * len(cues)

    scale = audio_duration / sum(floored) if sum(floored) > 0 else 1.0
    if scale < 1.0:
        floored = [d * scale for d in floored]

    out: list[tuple[float, float, str]] = []
    t = slide_start
    for c, d in zip(cues, floored):
        start = t
        end = t + max(d - min_gap, 0.4)
        out.append((start, end, c))
        t = start + d
    # Make sure the last cue ends no later than the slide audio ends.
    slide_end = slide_start + audio_duration
    last_s, last_e, last_t = out[-1]
    if last_e > slide_end:
        out[-1] = (last_s, slide_end, last_t)
    return out


# ---------------------------------------------------------------------------
# SRT formatting
# ---------------------------------------------------------------------------

def fmt_ts(seconds: float) -> str:
    """SRT timestamp: HH:MM:SS,mmm (note the comma decimal separator)."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def write_srt(cues: list[Cue], path: Path) -> None:
    """Write cues to an SRT file with per-cue `<font color="...">` tags.

    The font tag is the de-facto SRT styling convention. ffmpeg's mov_text
    encoder parses it and stores the color in the tx3g style atom, so the
    soft-track mux carries the color through to playback. Players that
    don't understand the tag (very old hardware decoders) just render the
    inner text as plain — the cue stays legible, only the styling is lost.
    """
    lines: list[str] = []
    for c in cues:
        lines.append(str(c.index))
        lines.append(f"{fmt_ts(c.start)} --> {fmt_ts(c.end)}")
        # Soft-wrap long cues at ~42 chars on a clause boundary for two-line
        # display in players that respect the SRT newline.
        wrapped = _soft_wrap(c.text, target=42)
        lines.append(f'<font color="{c.color}">{wrapped}</font>')
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def fmt_vtt_ts(seconds: float) -> str:
    """WebVTT timestamp: HH:MM:SS.mmm."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def write_vtt(cues: list[Cue], path: Path) -> None:
    lines: list[str] = ["WEBVTT", ""]
    for c in cues:
        lines.append(f"{fmt_vtt_ts(c.start)} --> {fmt_vtt_ts(c.end)}")
        lines.append(_soft_wrap(c.text, target=42))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _soft_wrap(text: str, target: int) -> str:
    """Insert at most one newline near `target` chars at a word boundary.

    Most players render at most two lines of SRT cleanly. Anything longer
    overflows or shrinks the font. We aim for two short lines, not three.
    """
    if len(text) <= target:
        return text
    # Find the space closest to `target` without exceeding ~1.4× target.
    cap = int(target * 1.4)
    if len(text) <= cap:
        # short enough to leave on one line
        return text
    # break at the space nearest to `target`
    split_at = text.rfind(" ", 0, target + 10)
    if split_at < target // 2:
        split_at = text.find(" ", target)
    if split_at <= 0:
        return text
    return text[:split_at].rstrip() + "\n" + text[split_at + 1:].lstrip()


# ---------------------------------------------------------------------------
# Mux SRT into MP4 as mov_text soft track
# ---------------------------------------------------------------------------

def mux_subtitles(mp4: Path, srt: Path, out: Path, language: str,
                  title: str, ffmpeg: str) -> None:
    """Stream-copy video+audio, encode SRT as mov_text into the output MP4."""
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-i", str(mp4),
        "-f", "srt", "-i", str(srt),
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-map", "1:0",
        "-c:v", "copy",
        "-c:a", "copy",
        "-c:s", "mov_text",
        "-metadata:s:s:0", f"language={language}",
        "-metadata:s:s:0", f"title={title}",
        "-disposition:s:0", "default",
        "-movflags", "+faststart",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"[add_subtitles] ffmpeg mux failed:\n{proc.stderr}")


# ---------------------------------------------------------------------------
# Hardsub — burn cues into the video pixels via libass
# ---------------------------------------------------------------------------

def _hex_to_ass_color(hex_rgb: str, *, alpha: int = 0) -> str:
    """SRT/CSS hex `#RRGGBB` → ASS `&HAABBGGRR&`.

    ASS color literals are little-endian BGR with a one-byte alpha prefix.
    Alpha is inverse opacity: 00 is fully opaque and FF is fully transparent.
    Picking the wrong byte order is the single most common ASS bug — a
    "white" sub that renders red is the R and B bytes swapped.
    """
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    alpha = max(0, min(255, int(alpha)))
    return f"&H{alpha:02X}{b}{g}{r}".upper() + "&"


def _opacity_to_ass_alpha(opacity: float) -> int:
    """Convert CSS-like opacity to ASS inverse alpha."""
    opacity = max(0.0, min(1.0, float(opacity)))
    return int(round((1.0 - opacity) * 255))


def _ass_escape(text: str) -> str:
    """Escape characters that have special meaning in ASS dialogue lines.

    ASS uses `{...}` for overrides and `\\N` for hard line breaks. We turn
    our SRT-style newlines into `\\N` and neutralize literal braces.
    """
    return (text.replace("\\", "\\\\")
                .replace("{", "\\{")
                .replace("}", "\\}")
                .replace("\n", "\\N"))


def _ass_timestamp(seconds: float) -> str:
    """ASS timestamp: H:MM:SS.cc (centiseconds, single-digit hour)."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass(cues: list[Cue], path: Path, *,
              video_w: int, video_h: int,
              font_name: str, font_size: int,
              outline_width: float, shadow_depth: float,
              subtitle_box: bool, box_opacity: float,
              box_padding: float) -> None:
    """Emit an ASS subtitle file with per-event color overrides.

    The style block sets sensible defaults (font, size, outline/background).
    By default paper2video uses a translucent dark box so burned-in subtitles
    do not visually merge with PPT text. Legacy no-box mode keeps the
    per-event outline fallback for users who explicitly want plain captions.

    PlayResX/PlayResY MUST match the output frame size or libass renders
    at the wrong scale (text either tiny or oversized). We pass video_w/h
    in from the probed input MP4.
    """
    box_alpha = _opacity_to_ass_alpha(box_opacity)
    box_color = _hex_to_ass_color("#101820", alpha=box_alpha)
    if subtitle_box:
        border_style = 3
        style_outline = max(0.0, float(box_padding))
        style_shadow = 0.0
        style_primary = _hex_to_ass_color(COLOR_WHITE)
        style_outline_color = box_color
        style_back_color = box_color
    else:
        border_style = 1
        style_outline = outline_width
        style_shadow = shadow_depth
        style_primary = _hex_to_ass_color(COLOR_WHITE)
        style_outline_color = _hex_to_ass_color(COLOR_BLACK)
        style_back_color = _hex_to_ass_color(COLOR_BLACK, alpha=128)

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {video_w}\n"
        f"PlayResY: {video_h}\n"
        "ScaledBorderAndShadow: yes\n"
        "WrapStyle: 0\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # Bold=0; Alignment=2 = bottom-center; MarginV=60 lifts the cue off
        # the very bottom edge so it doesn't collide with a player chrome.
        f"Style: Default,{font_name},{font_size},{style_primary},&H000000FF&,"
        f"{style_outline_color},{style_back_color},0,0,0,0,100,100,0,0,"
        f"{border_style},{style_outline},{style_shadow},2,40,40,60,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )

    body_lines: list[str] = []
    for c in cues:
        if subtitle_box:
            # Box mode intentionally keeps the cue text white. The box is the
            # contrast mechanism; using auto-picked black text on a dark box
            # would make the final burned-in captions hard to read.
            override = f"{{\\c{_hex_to_ass_color(COLOR_WHITE)}}}"
        else:
            primary = _hex_to_ass_color(c.color)
            # Outline is the opposite color — a black-text cue gets a white halo
            # and vice versa. That gives the cue a defensive readable edge if
            # the auto-pick lands on a slide whose actual background luma is
            # close to the threshold.
            opposite = COLOR_WHITE if c.color == COLOR_BLACK else COLOR_BLACK
            outline = _hex_to_ass_color(opposite)
            override = f"{{\\c{primary}\\3c{outline}}}"
        text = override + _ass_escape(c.text)
        line = (
            f"Dialogue: 0,{_ass_timestamp(c.start)},{_ass_timestamp(c.end)},"
            f"Default,,0,0,0,,{text}"
        )
        body_lines.append(line)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n".join(body_lines) + "\n", encoding="utf-8")


def probe_video_dimensions(mp4: Path, ffmpeg: str) -> tuple[int, int]:
    """Return (width, height) from the input MP4 by parsing ffmpeg's stderr."""
    out = subprocess.run([ffmpeg, "-i", str(mp4)], capture_output=True, text=True)
    # Stream line looks like: ... Video: h264 (High) ... 1920x1080 [SAR ...]
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", out.stderr)
    if not m:
        # Sensible default — render_video.py's 1080p preset. Better to log
        # and continue than to crash on a corner-case ffmpeg build whose
        # stderr formatting differs.
        print(f"[add_subtitles] warn: could not parse video dimensions from {mp4.name}; "
              f"falling back to 1920x1080.", file=sys.stderr)
        return 1920, 1080
    return int(m.group(1)), int(m.group(2))


def burn_subtitles(mp4: Path, ass: Path, out: Path, ffmpeg: str, *,
                   crf: int, preset: str) -> None:
    """Re-encode the video with the ASS file rendered onto every frame.

    The `ass=` filter needs an OS path; on Linux/macOS we pass it verbatim,
    on Windows ffmpeg requires backslash-escaped drive letters (`C\\:`). We
    use the resolved absolute path so the filter doesn't depend on CWD.

    Audio is stream-copied — there's no reason to re-encode the AAC track
    a second time and it would only add drift.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    ass_abs = str(ass.resolve())
    # Filter-graph path escaping: colons and backslashes are filter syntax.
    # Forward slashes are safe on Linux/macOS; on Windows we'd need extra
    # escaping. Our pipeline doesn't target Windows for rendering, so the
    # POSIX path passes through cleanly.
    ass_filter = f"ass={ass_abs}"
    cmd = [
        ffmpeg, "-y",
        "-i", str(mp4),
        "-vf", ass_filter,
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"[add_subtitles] ffmpeg burn-in failed:\n{proc.stderr}")


# ---------------------------------------------------------------------------
# Project file gathering
# ---------------------------------------------------------------------------

def collect_notes(project_path: Path) -> list[Path]:
    notes_dir = project_path / "notes"
    if not notes_dir.is_dir():
        sys.exit(f"[add_subtitles] notes/ not found under {project_path}")
    md = sorted(p for p in notes_dir.glob("*.md") if p.name != "total.md")
    if not md:
        sys.exit(f"[add_subtitles] notes/ has no per-slide *.md files (only total.md?). "
                 f"Run ppt-master's total_md_split.py first.")
    return md


def _load_script_sections(script_json: Path) -> list[dict]:
    try:
        payload = json.loads(script_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"[add_subtitles] invalid script JSON {script_json}: {exc}")

    sections = payload.get("sections") or []
    if not isinstance(sections, list) or not sections:
        sys.exit(f"[add_subtitles] script JSON has no sections array: {script_json}")

    out: list[dict] = []
    for idx, sec in enumerate(sections, start=1):
        if not isinstance(sec, dict) or not sec.get("id"):
            sys.exit(f"[add_subtitles] script section {idx} is missing an id in {script_json}")
        out.append(sec)
    return out


def autodetect_script_json(project_path: Path, audio_dir: Path) -> Path | None:
    for candidate in (
        audio_dir / "script.json",
        project_path / "assets" / "meta" / "narration.json",
        project_path / "narration.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def collect_audio(audio_dir: Path) -> list[Path]:
    if not audio_dir.is_dir():
        sys.exit(f"[add_subtitles] audio dir not found: {audio_dir}")
    mp3s = sorted(audio_dir.glob("*.mp3"))
    if not mp3s:
        sys.exit(f"[add_subtitles] no .mp3 files in {audio_dir}")
    return mp3s


def collect_timed_inputs(
    project_path: Path,
    audio_dir: Path,
    script_json: Path | None,
) -> list[tuple[str, str, Path]]:
    """Return (id, subtitle_text, mp3_path) in the timeline order.

    Without a script JSON this preserves the original ppt-master behavior:
    pair sorted notes/*.md with sorted audio/*.mp3. With a script JSON, use
    `sections` order and fall back to each section's `text` when notes/<id>.md
    is not present. That lets paper2assets narration.json drive subtitles
    without requiring synthetic notes files.
    """
    if script_json is None:
        script_json = autodetect_script_json(project_path, audio_dir)

    if script_json is None:
        notes = collect_notes(project_path)
        mp3s = collect_audio(audio_dir)
        if len(notes) != len(mp3s):
            sys.exit(
                f"[add_subtitles] notes/audio count mismatch: "
                f"{len(notes)} notes vs {len(mp3s)} mp3s.\n"
                f"  Notes: {[p.name for p in notes]}\n"
                f"  Audio: {[p.name for p in mp3s]}\n"
                f"  Subtitle timing requires 1-to-1 alignment. Regenerate the missing side."
            )
        rows: list[tuple[str, str, Path]] = []
        for note_md, mp3 in zip(notes, mp3s):
            if note_md.stem != mp3.stem:
                print(f"[add_subtitles] warn: notes stem '{note_md.stem}' != audio stem '{mp3.stem}' "
                      f"— pairing by sort order. Check for renamed/missing files if subtitles drift.",
                      file=sys.stderr)
            rows.append((note_md.stem, note_md.read_text(encoding="utf-8"), mp3))
        print("[add_subtitles] subtitle order from sorted notes/audio filenames")
        return rows

    script_json = script_json.resolve()
    notes_dir = project_path / "notes"
    rows = []
    missing_audio = []
    for sec in _load_script_sections(script_json):
        sid = str(sec["id"])
        mp3 = audio_dir / f"{sid}.mp3"
        if not mp3.is_file():
            missing_audio.append(mp3.name)
            continue
        note_md = notes_dir / f"{sid}.md"
        if note_md.is_file():
            text = note_md.read_text(encoding="utf-8")
        else:
            text = str(sec.get("text") or "")
        rows.append((sid, text, mp3))

    if missing_audio:
        sys.exit(
            f"[add_subtitles] script/audio mismatch using {script_json}:\n"
            f"  missing mp3s under {audio_dir}: {missing_audio}"
        )
    if not rows:
        sys.exit(f"[add_subtitles] no usable sections in {script_json}")
    print(f"[add_subtitles] subtitle order from {script_json}")
    return rows


def autodetect_mp4(exports_dir: Path) -> Path:
    """Pick the newest *.mp4 in exports/ that isn't already a _subbed.mp4."""
    if not exports_dir.is_dir():
        sys.exit(f"[add_subtitles] exports/ not found: {exports_dir}")
    candidates = [p for p in exports_dir.glob("*.mp4") if not p.stem.endswith("_subbed")]
    if not candidates:
        sys.exit(f"[add_subtitles] no MP4 in {exports_dir} — run render_video.py first or pass --mp4")
    # Newest by mtime
    return max(candidates, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("project_path", help="ppt-master project root (contains notes/, audio/, exports/)")
    ap.add_argument("--mp4", default=None,
                    help="Input MP4 (default: newest non-_subbed.mp4 in <project>/exports)")
    ap.add_argument("--audio-dir", default=None,
                    help="Per-slide audio directory (default: <project>/audio)")
    ap.add_argument("--script-json", default=None,
                    help="Narration script JSON whose sections order defines subtitle/audio order. "
                         "Defaults to <audio-dir>/script.json, then <project>/assets/meta/narration.json, then <project>/narration.json, "
                         "then sorted notes/audio filenames.")
    ap.add_argument("--out", default=None,
                    help="Output MP4 path (default: <project>/exports/<mp4_stem>_subbed.mp4)")
    ap.add_argument("--srt-out", default=None,
                    help="Standalone SRT path (default: <project>/exports/<mp4_stem>.srt)")
    ap.add_argument("--vtt-out", default=None,
                    help="Standalone WebVTT path (default: <project>/exports/<mp4_stem>.vtt)")
    ap.add_argument("--start-pad", type=float, default=0.5,
                    help="Lead-in silence used by render_video.py (default: 0.5s — MUST match)")
    ap.add_argument("--pad-tail", type=float, default=0.3,
                    help="Per-slide trailing silence used by render_video.py (default: 0.3s — MUST match)")
    ap.add_argument("--max-chars-per-cue", type=int, default=85,
                    help="Soft cap on cue length before clause-level chunking (default: 85)")
    ap.add_argument("--min-cue-duration", type=float, default=1.2,
                    help="Floor on per-cue screen time (default: 1.2s)")
    ap.add_argument("--min-cue-gap", type=float, default=0.08,
                    help="Visible gap between adjacent cues (default: 0.08s)")
    ap.add_argument("--language", default="eng",
                    help="ISO 639-2 language tag for the mov_text stream (default: eng)")
    ap.add_argument("--track-title", default="Narration",
                    help="Display name for the subtitle track (default: Narration)")
    ap.add_argument("--color", choices=("auto", "white", "black"), default="auto",
                    help="Subtitle text color (default: auto — sample each slide's "
                         "subtitle band and pick white-on-dark or black-on-light).")
    ap.add_argument("--soft", action="store_true",
                    help="Soft-mux as mov_text instead of burning into pixels. "
                         "Use this if you want a toggleable caption track and don't "
                         "mind that some players (mobile previews, embeds) ignore it.")
    ap.add_argument("--font", default="DejaVu Sans",
                    help="Font for burned-in subtitles (default: DejaVu Sans — present "
                         "on most Linux installs; pick a system font you actually have).")
    ap.add_argument("--font-size", type=int, default=44,
                    help="Burn-in font size in ASS units (default: 44 — readable at 1080p).")
    ap.add_argument("--outline-width", type=float, default=2.0,
                    help="Stroke width around burn-in text (default: 2.0).")
    ap.add_argument("--shadow-depth", type=float, default=0.5,
                    help="Drop-shadow depth for burn-in text (default: 0.5).")
    ap.add_argument("--subtitle-box", dest="subtitle_box", action="store_true", default=True,
                    help="Burn subtitles with a translucent dark background box (default).")
    ap.add_argument("--no-subtitle-box", dest="subtitle_box", action="store_false",
                    help="Legacy mode: burn plain text with outline/shadow and no background box.")
    ap.add_argument("--subtitle-box-opacity", type=float, default=0.62,
                    help="Opacity for the subtitle background box, 0..1 (default: 0.62).")
    ap.add_argument("--subtitle-box-padding", type=float, default=10.0,
                    help="ASS opaque-box padding around subtitle text (default: 10).")
    ap.add_argument("--crf", type=int, default=20,
                    help="x264 CRF for the burn-in re-encode (default: 20 — visually "
                         "lossless for screen content).")
    ap.add_argument("--preset", default="medium",
                    help="x264 preset for the burn-in re-encode (default: medium).")
    ap.add_argument("--srt-only", action="store_true",
                    help="Write the .srt and exit (skip muxing/burning).")
    args = ap.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.is_dir():
        sys.exit(f"[add_subtitles] project path not found: {project_path}")

    exports_dir = project_path / "exports"
    mp4_path = Path(args.mp4).resolve() if args.mp4 else autodetect_mp4(exports_dir)
    if not mp4_path.is_file():
        sys.exit(f"[add_subtitles] MP4 not found: {mp4_path}")

    audio_dir = Path(args.audio_dir).resolve() if args.audio_dir else project_path / "audio"
    script_json = Path(args.script_json).resolve() if args.script_json else None
    timed_inputs = collect_timed_inputs(project_path, audio_dir, script_json)

    ffmpeg, ffprobe = find_ffmpeg_pair()

    # Walk slides, advancing the clock just like render_video.py does.
    # We collect per-slide cue groups together with each slide's midpoint
    # timestamp, then probe the slide colors in one pass and apply them
    # back to the cues. Two-pass keeps the audio probing and frame probing
    # cleanly separated, and means a `--color white|black` short-circuit
    # avoids touching ffmpeg's frame extractor at all.
    t = max(args.start_pad, 0.0)
    next_index = 1
    pending: list[tuple[int, list[Cue], float]] = []  # (slide_idx, cues, midpoint)

    for slide_idx, (sid, text, mp3) in enumerate(timed_inputs, start=1):
        duration = probe_duration(mp3, ffprobe, ffmpeg)
        cues = split_into_cues(text, args.max_chars_per_cue)

        if not cues:
            # Skip silent / empty notes but still advance the clock.
            t += duration + args.pad_tail
            continue

        timed = allocate_slide_cues(
            cues, duration, slide_start=t,
            min_cue_dur=args.min_cue_duration,
            min_gap=args.min_cue_gap,
        )
        slide_cues: list[Cue] = []
        for start, end, txt in timed:
            slide_cues.append(Cue(index=next_index, start=start, end=end, text=txt))
            next_index += 1

        midpoint = t + duration / 2.0
        pending.append((slide_idx, slide_cues, midpoint))

        # Advance past this slide's audio + the trailing silence pad.
        t += duration + args.pad_tail

    if not pending:
        sys.exit("[add_subtitles] no cues generated — every note file was empty.")

    # Per-slide color decision. `--color white|black` forces a single color
    # across the whole deck and skips the probe pass entirely.
    forced = {"white": COLOR_WHITE, "black": COLOR_BLACK, "auto": None}[args.color]
    midpoints = [m for _, _, m in pending]
    colors = pick_slide_colors(mp4_path, midpoints, ffmpeg, default=forced)

    all_cues: list[Cue] = []
    for (slide_idx, slide_cues, _), color in zip(pending, colors):
        for c in slide_cues:
            c.color = color
            all_cues.append(c)

    if not all_cues:
        sys.exit("[add_subtitles] no cues generated — every note file was empty.")

    srt_path = (Path(args.srt_out).resolve() if args.srt_out
                else exports_dir / f"{mp4_path.stem}.srt")
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    write_srt(all_cues, srt_path)
    print(f"[add_subtitles] wrote {len(all_cues)} cues to {srt_path}")
    vtt_path = (Path(args.vtt_out).resolve() if args.vtt_out
                else exports_dir / f"{mp4_path.stem}.vtt")
    vtt_path.parent.mkdir(parents=True, exist_ok=True)
    write_vtt(all_cues, vtt_path)
    print(f"[add_subtitles] wrote {len(all_cues)} cues to {vtt_path}")

    if args.srt_only:
        return 0

    out_path = (Path(args.out).resolve() if args.out
                else exports_dir / f"{mp4_path.stem}_subbed.mp4")

    if args.soft:
        # Soft mov_text track — stream-copy video+audio, no re-encode.
        mux_subtitles(mp4_path, srt_path, out_path,
                      language=args.language, title=args.track_title, ffmpeg=ffmpeg)
        print(f"[add_subtitles] muxed soft subtitle track into {out_path}")
        print(f"[add_subtitles] toggle in VLC: Subtitle → Sub Track → {args.track_title}")
        return 0

    # Default: burn cues into the video pixels via libass. This is what the
    # user means by "part of the video file" — there is no toggle, every
    # player on every device shows the captions because they are pixels now.
    video_w, video_h = probe_video_dimensions(mp4_path, ffmpeg)
    ass_path = exports_dir / f"{mp4_path.stem}.ass"
    write_ass(
        all_cues, ass_path,
        video_w=video_w, video_h=video_h,
        font_name=args.font, font_size=args.font_size,
        outline_width=args.outline_width, shadow_depth=args.shadow_depth,
        subtitle_box=args.subtitle_box,
        box_opacity=args.subtitle_box_opacity,
        box_padding=args.subtitle_box_padding,
    )
    print(f"[add_subtitles] wrote ASS at {video_w}×{video_h} → {ass_path}")
    print(f"[add_subtitles] burning subtitles into pixels (libx264 crf={args.crf} preset={args.preset})…")
    burn_subtitles(mp4_path, ass_path, out_path, ffmpeg,
                   crf=args.crf, preset=args.preset)
    print(f"[add_subtitles] burned subtitles into {out_path}")
    print(f"[add_subtitles] captions are part of every frame — no player toggle required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
