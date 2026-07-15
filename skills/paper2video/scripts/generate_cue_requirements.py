#!/usr/bin/env python3
"""Create visual-cue anchor requirements for ppt-master slide authoring.

This is a pre-generation helper. It reads paper2video script.json and writes a
small contract that can be pasted into the ppt-master prompt. The point is to
make cue targets explicit while the deck is authored instead of asking the
post-hoc matcher to infer semantics from arbitrary shapes.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from generate_visual_cues import content_tokens, expected_roles, split_sentences, chunk_sentences


SCHEMA_VERSION = "paper2video_cue_requirements.v1"
CONTRACT_SCHEMA_VERSION = "paper2video_visual_anchor_contract.v1"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(text: str, *, limit: int = 36) -> str:
    tokens = content_tokens(text)
    if not tokens:
        tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    slug = "_".join(tokens[:5])
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", slug).strip("_").lower()
    return (slug or "cue")[:limit].strip("_") or "cue"


def role_hint(chunk: str) -> str:
    roles = sorted(expected_roles(chunk))
    preferred = [r for r in ("method", "result", "figure", "takeaway", "qr", "title", "guidance") if r in roles]
    return preferred[0] if preferred else "content"


def build_requirements(script: dict[str, Any], *, max_cues_per_slide: int) -> dict[str, Any]:
    sections = script.get("sections") or []
    slides = []
    for index, section in enumerate(sections, start=1):
        sid = str(section.get("id") or f"slide_{index:02d}")
        heading = str(section.get("heading") or sid)
        text = str(section.get("text") or "").strip()
        chunks = chunk_sentences(split_sentences(text), max_cues_per_slide)
        slide_chunks = []
        for chunk_index, chunk in enumerate(chunks, start=1):
            role = role_hint(chunk)
            anchor_id = f"cue_s{index:02d}_c{chunk_index}_{slugify(chunk)}"
            chunk_id = f"s{index:02d}_c{chunk_index:02d}"
            cue_keywords = content_tokens(chunk)[:10]
            slide_chunks.append({
                "chunk_index": chunk_index,
                "chunk_id": chunk_id,
                "text": chunk,
                "preferred_role": role,
                "expected_role": role,
                "anchor_id": anchor_id,
                "cue_keywords": cue_keywords,
                "required": True,
                "authoring_instruction": (
                    f"Create or label one visible {role} region for this narration chunk. "
                    f"Use id=\"{anchor_id}\" when possible; otherwise include this value "
                    f"in data-cue-label/title/desc. Also include the cue keywords "
                    f"{', '.join(cue_keywords[:6]) or 'from the narration'} in title/desc "
                    f"so the matcher can verify semantic overlap."
                ),
            })
        slides.append({
            "index": index,
            "id": sid,
            "heading": heading,
            "chunks": slide_chunks,
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "source_script": script.get("source") or "",
        "max_cues_per_slide": max_cues_per_slide,
        "slides": slides,
    }


def build_contract(requirements: dict[str, Any]) -> dict[str, Any]:
    slides = []
    for slide in requirements.get("slides") or []:
        chunks = []
        for chunk in slide.get("chunks") or []:
            chunks.append({
                "chunk_index": chunk.get("chunk_index"),
                "chunk_id": chunk.get("chunk_id"),
                "anchor_id": chunk.get("anchor_id"),
                "text": chunk.get("text"),
                "expected_role": chunk.get("expected_role") or chunk.get("preferred_role"),
                "cue_keywords": chunk.get("cue_keywords") or [],
                "required": bool(chunk.get("required", True)),
            })
        slides.append({
            "index": slide.get("index"),
            "id": slide.get("id"),
            "heading": slide.get("heading"),
            "chunks": chunks,
        })
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "source_script": requirements.get("source_script") or "",
        "max_cues_per_slide": requirements.get("max_cues_per_slide"),
        "slides": slides,
        "authoring_contract": {
            "pptx": "Write anchor_id into the corresponding shape name, alt-text title, or alt-text description.",
            "svg_html": "Write anchor_id into id, data-cue-label, title, or desc on the visible target group.",
            "target_scope": "Only label the few key visual targets used for video highlights; do not label every decorative element.",
        },
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# paper2video visual cue requirements for ppt-master",
        "",
        "Use this file while authoring the deck. It is not a design style; it is a semantic anchor contract for video highlights.",
        "",
        "For each slide, create 2-5 visible content groups whose IDs, `<title>`, `<desc>`, or `data-cue-label` match the requested anchor IDs. Keep the highlight target on real content, not headers, captions, logos, or background chrome.",
        "",
        "The final cue renderer uses translucent point highlights centered on these regions, so the region should wrap the specific diagram/card/chart area being discussed. Prefer a stable SVG group id beginning with `cue_`; include the narration keywords in `<desc>` or `data-cue-label` so the matcher can confirm semantic overlap instead of guessing from layout alone.",
        "",
    ]
    for slide in payload.get("slides", []):
        lines.extend([
            f"## Slide {int(slide.get('index') or 0):02d}: {slide.get('id')}",
            "",
            f"Heading: {slide.get('heading') or ''}",
            "",
        ])
        for chunk in slide.get("chunks", []):
            lines.extend([
                f"### Cue {chunk.get('chunk_index')}: `{chunk.get('anchor_id')}`",
                "",
                f"- Preferred role: `{chunk.get('preferred_role')}`",
                f"- Cue keywords: `{', '.join(chunk.get('cue_keywords') or [])}`",
                f"- Narration: {chunk.get('text')}",
                f"- Authoring: {chunk.get('authoring_instruction')}",
                "",
            ])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ppt-master cue-anchor requirements from paper2video script.json.")
    parser.add_argument("script_json", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--contract-out", type=Path,
                        help="Optional visual_anchor_contract.json output used by strict cue QA.")
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--max-cues-per-slide", type=int, default=4)
    args = parser.parse_args()

    script_path = args.script_json.resolve()
    if not script_path.is_file():
        raise SystemExit(f"[generate_cue_requirements] script not found: {script_path}")
    if args.max_cues_per_slide < 1:
        raise SystemExit("[generate_cue_requirements] --max-cues-per-slide must be positive")

    script = read_json(script_path)
    payload = build_requirements(script, max_cues_per_slide=args.max_cues_per_slide)
    payload["source_script"] = str(script_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.contract_out:
        args.contract_out.parent.mkdir(parents=True, exist_ok=True)
        args.contract_out.write_text(json.dumps(build_contract(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(payload, args.markdown_out)
        written = [str(args.out), str(args.markdown_out)]
    else:
        written = [str(args.out)]
    if args.contract_out:
        written.append(str(args.contract_out))
    print(f"[generate_cue_requirements] wrote {', '.join(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
