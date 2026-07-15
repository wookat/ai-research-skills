#!/usr/bin/env python3
"""Shared duration planning helpers for paper2video narration scripts."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


PLAN_SCHEMA_VERSION = "paper2video_duration_plan.v1"
REWRITE_REQUEST_SCHEMA_VERSION = "paper2video_duration_rewrite_request.v1"

_LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_SENTENCE_END_RE = re.compile(r"[.!?。！？]+[\"')\]]*")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def word_count(text: str) -> int:
    """Return a TTS-oriented word-unit count.

    Latin words count as words. CJK characters are approximated as half-words
    so bilingual scripts get a stable, provider-independent duration estimate.
    """
    latin = len(_LATIN_WORD_RE.findall(text))
    cjk = len(_CJK_RE.findall(text))
    return latin + math.ceil(cjk / 2)


def estimate_speech_seconds(text: str, words_per_minute: float) -> float:
    return word_count(text) / max(words_per_minute, 1.0) * 60.0


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    out: list[str] = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(text):
        end = match.end()
        out.append(text[start:end].strip())
        start = end
    rest = text[start:].strip()
    if rest:
        out.append(rest)
    return [s for s in out if s]


def _truncate_by_words(text: str, budget_words: int) -> str:
    budget_words = max(budget_words, 1)
    words = text.split()
    if len(words) > 1:
        trimmed = " ".join(words[:budget_words]).strip()
    else:
        cjk_chars = len(_CJK_RE.findall(text))
        if cjk_chars:
            trimmed = text[: max(6, budget_words * 2)].strip()
        else:
            trimmed = text[: max(24, budget_words * 7)].strip()

    if trimmed and trimmed[-1] not in ".!?。！？":
        trimmed += "."
    return trimmed


def shorten_text_to_words(text: str, budget_words: int) -> tuple[str, bool]:
    """Conservatively trim prose to a word budget.

    The function keeps sentence order and only cuts at sentence boundaries
    unless the first sentence alone is too long.
    """
    budget_words = max(budget_words, 1)
    if word_count(text) <= budget_words:
        return text.strip(), False

    sentences = split_sentences(text)
    if not sentences:
        return text.strip(), False

    kept: list[str] = []
    total = 0
    for sentence in sentences:
        count = word_count(sentence)
        if total + count <= budget_words:
            kept.append(sentence)
            total += count
            continue
        if not kept:
            return _truncate_by_words(sentence, budget_words), True
        remaining = budget_words - total
        if remaining >= 8:
            kept.append(_truncate_by_words(sentence, remaining))
        break

    if not kept:
        return _truncate_by_words(text, budget_words), True
    return " ".join(kept).strip(), True


def _priority(section: dict[str, Any], index: int, total: int) -> int:
    sid = str(section.get("id") or "").lower()
    heading = str(section.get("heading") or "").lower()
    key = f"{sid} {heading}"

    if index == 0:
        return 100
    if index == total - 1:
        return 95

    high = (
        "title", "overview", "problem", "motivation", "method", "approach",
        "key-result", "result", "takeaway", "conclusion",
    )
    medium = (
        "dataset", "benchmark", "evaluation", "experiment", "ablation",
        "scaling", "analysis", "finding",
    )
    low = ("related", "background", "limitation", "future", "appendix")

    if any(k in key for k in high):
        return 90
    if any(k in key for k in medium):
        return 70
    if any(k in key for k in low):
        return 40
    return 60


def _floor_words(section: dict[str, Any], min_section_words: int) -> int:
    sid = str(section.get("id") or "").lower()
    heading = str(section.get("heading") or "").lower()
    key = f"{sid} {heading}"
    if "title" in key:
        return max(8, min_section_words // 2)
    if "takeaway" in key or "conclusion" in key:
        return max(12, min_section_words - 4)
    return min_section_words


def _video_seconds_for_word_counts(
    counts: list[int],
    *,
    words_per_minute: float,
    start_pad: float,
    pad_tail: float,
) -> float:
    speech = sum(counts) / max(words_per_minute, 1.0) * 60.0
    return start_pad + speech + pad_tail * len(counts)


def _drop_sections_for_target(
    sections: list[dict[str, Any]],
    *,
    target_seconds: float,
    tolerance_seconds: float,
    words_per_minute: float,
    start_pad: float,
    pad_tail: float,
    min_section_words: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Drop low-priority sections only when minimum floors cannot fit."""
    current = list(sections)
    dropped: list[dict[str, Any]] = []

    def min_possible_video_seconds(items: list[dict[str, Any]]) -> float:
        floors = [_floor_words(sec, min_section_words) for sec in items]
        return _video_seconds_for_word_counts(
            floors,
            words_per_minute=words_per_minute,
            start_pad=start_pad,
            pad_tail=pad_tail,
        )

    while len(current) > 3 and min_possible_video_seconds(current) > target_seconds + tolerance_seconds:
        total = len(current)
        candidates = []
        for idx, sec in enumerate(current):
            if idx == 0 or idx == total - 1:
                continue
            candidates.append((
                _priority(sec, idx, total),
                -word_count(str(sec.get("text") or "")),
                idx,
                sec,
            ))
        if not candidates:
            break
        _, _, idx, sec = sorted(candidates)[0]
        dropped.append(sec)
        current.pop(idx)

    return current, dropped


def _allocate_word_budgets(
    sections: list[dict[str, Any]],
    *,
    target_speech_seconds: float,
    words_per_minute: float,
    min_section_words: int,
) -> tuple[list[int], bool]:
    source_counts = [word_count(str(sec.get("text") or "")) for sec in sections]
    floors = [_floor_words(sec, min_section_words) for sec in sections]
    target_words = max(1, int(round(target_speech_seconds * words_per_minute / 60.0)))

    if sum(source_counts) <= target_words:
        return source_counts, False

    floor_total = sum(floors)
    min_exceeds_target = floor_total > target_words
    if min_exceeds_target:
        return floors, True

    remaining = target_words - floor_total
    excess = [max(source - floor, 0) for source, floor in zip(source_counts, floors)]
    excess_total = sum(excess)
    if excess_total <= 0:
        return floors, False

    budgets = []
    for source, floor, extra in zip(source_counts, floors, excess):
        add = int(round(remaining * extra / excess_total))
        budgets.append(min(source, floor + add))

    # Rounding can overshoot; trim from the largest budgets first.
    while sum(budgets) > target_words:
        idx = max(range(len(budgets)), key=lambda i: budgets[i] - floors[i])
        if budgets[idx] <= floors[idx]:
            break
        budgets[idx] -= 1

    return budgets, False


def _allocate_expansion_budgets(
    sections: list[dict[str, Any]],
    *,
    target_speech_seconds: float,
    words_per_minute: float,
) -> list[int]:
    source_counts = [word_count(str(sec.get("text") or "")) for sec in sections]
    target_words = max(sum(source_counts), int(round(target_speech_seconds * words_per_minute / 60.0)))
    surplus = target_words - sum(source_counts)
    if surplus <= 0:
        return source_counts

    total = len(sections)
    weights = []
    for idx, (sec, count) in enumerate(zip(sections, source_counts)):
        weights.append(max(1.0, count * (_priority(sec, idx, total) / 60.0)))
    weight_total = sum(weights) or float(len(weights))

    budgets = []
    for count, weight in zip(source_counts, weights):
        budgets.append(count + int(round(surplus * weight / weight_total)))

    # Rounding can undershoot; add the remaining words to the highest-priority
    # sections so the request is still close to the target.
    while sum(budgets) < target_words:
        idx = max(range(len(budgets)), key=lambda i: weights[i])
        budgets[idx] += 1
    return budgets


def build_duration_rewrite_request(plan: dict[str, Any], source_sections: list[dict[str, Any]]) -> dict[str, Any]:
    source_by_id = {str(sec.get("id") or ""): sec for sec in source_sections}
    requests = []
    action = str(plan.get("planning_action") or "rewrite")
    for report in plan.get("sections") or []:
        if not isinstance(report, dict) or not report.get("rewrite_required") or report.get("dropped"):
            continue
        sid = str(report.get("id") or "")
        source = source_by_id.get(sid, {})
        source_text = str(source.get("text") or "")
        budget_words = int(report.get("budget_words") or report.get("target_words") or 0)
        if action == "expand":
            instruction = (
                "Rewrite the whole narration for this slide to be richer and more explanatory, "
                "preserving the original meaning and adding useful connective detail from the slide/paper context."
            )
        else:
            instruction = (
                "Rewrite the whole narration for this slide more concisely while preserving all essential points. "
                "Do not just keep the first sentences; cover the beginning, middle, and ending ideas."
            )
        requests.append({
            "id": sid,
            "heading": str(report.get("heading") or source.get("heading") or sid),
            "direction": action,
            "target_words": budget_words,
            "hard_max_words": max(budget_words + 6, int(round(budget_words * 1.08))),
            "source_words": report.get("source_words"),
            "source_text": source_text,
            "instruction": instruction,
        })

    return {
        "schema_version": REWRITE_REQUEST_SCHEMA_VERSION,
        "created_at": utc_now(),
        "target_minutes": plan.get("target_minutes"),
        "target_seconds": plan.get("target_seconds"),
        "tolerance_seconds": plan.get("tolerance_seconds"),
        "words_per_minute": plan.get("words_per_minute"),
        "planning_action": action,
        "request_count": len(requests),
        "output_schema": {
            "sections": [
                {"id": "<same id>", "text": "<semantically rewritten narration within hard_max_words>"}
            ]
        },
        "rules": [
            "Rewrite each requested section as a complete narration, not a prefix or sentence deletion.",
            "Preserve the slide's full semantic arc: motivation, method/detail, and takeaway when present.",
            "Keep terminology, numbers, and named datasets/models that are important to the paper.",
            "Use natural spoken prose; avoid bullets unless the source narration intentionally speaks a list.",
        ],
        "sections": requests,
    }


def plan_script_sections(
    sections: list[dict[str, Any]],
    *,
    target_minutes: float | None = None,
    tolerance_seconds: float = 30.0,
    words_per_minute: float = 145.0,
    start_pad: float = 0.5,
    pad_tail: float = 0.3,
    min_section_words: int = 18,
    section_mode: str = "keep",
    rewrite_texts: dict[str, str] | None = None,
    allow_extractive_draft: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Return planned sections plus an optional duration_plan document."""
    if target_minutes is None:
        return sections, None

    if target_minutes <= 0:
        raise ValueError("target_minutes must be positive")
    if tolerance_seconds < 0:
        raise ValueError("tolerance_seconds must be non-negative")
    if words_per_minute <= 0:
        raise ValueError("words_per_minute must be positive")
    if min_section_words <= 0:
        raise ValueError("min_section_words must be positive")
    if section_mode not in {"keep", "auto"}:
        raise ValueError("section_mode must be 'keep' or 'auto'")

    target_seconds = target_minutes * 60.0
    selected = [deepcopy(sec) for sec in sections]
    dropped: list[dict[str, Any]] = []
    if section_mode == "auto":
        selected, dropped = _drop_sections_for_target(
            selected,
            target_seconds=target_seconds,
            tolerance_seconds=tolerance_seconds,
            words_per_minute=words_per_minute,
            start_pad=start_pad,
            pad_tail=pad_tail,
            min_section_words=min_section_words,
        )

    if not selected:
        raise ValueError("duration planning dropped every section")

    target_speech_seconds = max(target_seconds - start_pad - pad_tail * len(selected), 1.0)
    source_counts = [word_count(str(sec.get("text") or "")) for sec in selected]
    source_estimated_video_seconds = _video_seconds_for_word_counts(
        source_counts,
        words_per_minute=words_per_minute,
        start_pad=start_pad,
        pad_tail=pad_tail,
    )
    source_delta = source_estimated_video_seconds - target_seconds
    if abs(source_delta) <= tolerance_seconds:
        budgets = source_counts
        min_exceeds_target = False
        planning_action = "none"
    elif source_delta > 0:
        budgets, min_exceeds_target = _allocate_word_budgets(
            selected,
            target_speech_seconds=target_speech_seconds,
            words_per_minute=words_per_minute,
            min_section_words=min_section_words,
        )
        planning_action = "shrink"
    else:
        budgets = _allocate_expansion_budgets(
            selected,
            target_speech_seconds=target_speech_seconds,
            words_per_minute=words_per_minute,
        )
        min_exceeds_target = False
        planning_action = "expand"

    planned: list[dict[str, Any]] = []
    section_reports: list[dict[str, Any]] = []
    rewrite_texts = rewrite_texts or {}
    rewrite_required_count = 0
    rewrite_applied_count = 0
    extractive_draft_count = 0
    for sec, budget in zip(selected, budgets):
        sid = str(sec.get("id") or "")
        source_text = str(sec.get("text") or "")
        source_words = word_count(source_text)
        planned_text = source_text.strip()
        changed = False
        rewrite_required = False
        rewrite_applied = False
        extractive_draft = False

        if sid in rewrite_texts:
            planned_text = str(rewrite_texts[sid] or "").strip()
            if not planned_text:
                raise ValueError(f"duration rewrite for section {sid} is empty")
            changed = planned_text != source_text.strip()
            rewrite_applied = True
            rewrite_applied_count += 1
        elif planning_action == "shrink" and source_words > budget:
            if allow_extractive_draft:
                planned_text, changed = shorten_text_to_words(source_text, budget)
                extractive_draft = changed
                if extractive_draft:
                    extractive_draft_count += 1
            else:
                rewrite_required = True
                rewrite_required_count += 1
        elif planning_action == "expand" and source_words < budget:
            rewrite_required = True
            rewrite_required_count += 1

        sec["text"] = planned_text
        planned_words = word_count(planned_text)
        planned.append(sec)
        section_reports.append({
            "id": sid,
            "heading": str(sec.get("heading") or ""),
            "source_words": source_words,
            "budget_words": budget,
            "target_words": budget,
            "planned_words": planned_words,
            "estimated_speech_seconds": round(planned_words / words_per_minute * 60.0, 3),
            "changed": changed,
            "rewrite_required": rewrite_required,
            "rewrite_applied": rewrite_applied,
            "extractive_draft": extractive_draft,
            "over_budget": planned_words > max(budget + 6, int(round(budget * 1.08))) if planning_action == "shrink" else False,
            "under_budget": planned_words < max(1, int(round(budget * 0.85))) if planning_action == "expand" else False,
            "dropped": False,
        })

    for sec in dropped:
        section_reports.append({
            "id": str(sec.get("id") or ""),
            "heading": str(sec.get("heading") or ""),
            "source_words": word_count(str(sec.get("text") or "")),
            "budget_words": 0,
            "planned_words": 0,
            "estimated_speech_seconds": 0.0,
            "changed": True,
            "rewrite_required": False,
            "rewrite_applied": False,
            "extractive_draft": False,
            "over_budget": False,
            "under_budget": False,
            "dropped": True,
        })

    planned_counts = [word_count(str(sec.get("text") or "")) for sec in planned]
    estimated_video_seconds = _video_seconds_for_word_counts(
        planned_counts,
        words_per_minute=words_per_minute,
        start_pad=start_pad,
        pad_tail=pad_tail,
    )
    delta = estimated_video_seconds - target_seconds
    if rewrite_required_count:
        status = "needs_script_rewrite"
    elif abs(delta) <= tolerance_seconds:
        status = "within_tolerance"
    elif delta > 0:
        status = "above_target"
    else:
        status = "below_target"
    if not rewrite_required_count and min_exceeds_target and delta > tolerance_seconds:
        status = "minimum_exceeds_target"

    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "created_at": utc_now(),
        "target_minutes": target_minutes,
        "target_seconds": round(target_seconds, 3),
        "tolerance_seconds": tolerance_seconds,
        "words_per_minute": words_per_minute,
        "start_pad": start_pad,
        "pad_tail": pad_tail,
        "min_section_words": min_section_words,
        "section_mode": section_mode,
        "planning_action": planning_action,
        "status": status,
        "source_estimated_video_seconds": round(source_estimated_video_seconds, 3),
        "source_estimated_delta_seconds": round(source_delta, 3),
        "estimated_speech_seconds": round(sum(planned_counts) / words_per_minute * 60.0, 3),
        "estimated_video_seconds": round(estimated_video_seconds, 3),
        "estimated_delta_seconds": round(delta, 3),
        "rewrite_required_count": rewrite_required_count,
        "rewrite_applied_count": rewrite_applied_count,
        "extractive_draft_count": extractive_draft_count,
        "sections": section_reports,
    }
    return planned, plan
