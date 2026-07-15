#!/usr/bin/env python3
"""capture_filter.py — mechanical anti-self-poisoning screen for durable captures.

Implements the deterministic side of shared-references/capture-antipatterns.md:
flags env-specific failures, transient errors, and negative tool-capability
claims about the pack's own tooling before they are persisted into the
research wiki or a SKILL.md proposal. Deliberately conservative: research
findings about a *model/method* are NOT flagged — only operational noise.

Library:
    from capture_filter import screen, reason_detail
    screen(text) -> [reason, ...]   # [] = clean
    # reason in {"env_failure", "transient_error", "negative_tool_claim"}

CLI:
    python3 tools/capture_filter.py <file|->   # exit 1 + reasons if flagged
"""
from __future__ import annotations

import re
import sys

_ENV_FAILURE_PATTERNS = [
    r"No module named",
    r"ModuleNotFoundError",
    r"ImportError:",
    r"command not found",
    r"Permission denied",
    r"No such file or directory",
    r"pip (?:install )?fail",
    r"EACCES|ENOENT",
]

_TRANSIENT_PATTERNS = [
    r"\b429\b|rate limit",
    r"CUDA out of memory|CUDA OOM|\bOOM\b",
    r"connection (?:refused|reset|timed? ?out)",
    r"\b50[234]\b (?:error|gateway|unavailable)",
    r"temporar(?:y|ily) (?:fail|unavailable)",
    r"SSLError|TLS handshake",
]

# Infrastructure nouns: the pack's own tooling, not research subjects.
_TOOL_NOUNS = (
    r"(?:codex|gemini|oracle|claude|devin|cursor|the reviewer|the MCP|"
    r"the CLI|the agent|the skill|the helper|the tool)"
)
_NEGATIVE_TOOL_PATTERNS = [
    rf"{_TOOL_NOUNS}[^.\n]*\b(?:can'?t|cannot|is broken|doesn'?t work|"
    r"never works|always fails|is unable to)",
    rf"(?:don'?t|do not|never) use {_TOOL_NOUNS}",
    rf"{_TOOL_NOUNS} (?:is|are) (?:broken|useless|unreliable)",
]

_REASONS = [
    ("env_failure", _ENV_FAILURE_PATTERNS),
    ("transient_error", _TRANSIENT_PATTERNS),
    ("negative_tool_claim", _NEGATIVE_TOOL_PATTERNS),
]


def reason_detail(text: str) -> dict[str, list[str]]:
    """Return {reason: [matched snippets]} for every anti-pattern found."""
    found: dict[str, list[str]] = {}
    for reason, patterns in _REASONS:
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                start = max(0, m.start() - 30)
                snippet = text[start:m.end() + 30].replace("\n", " ").strip()
                found.setdefault(reason, []).append(snippet)
    return found


def screen(text: str) -> list[str]:
    """Return the list of anti-pattern reasons found ([] = clean)."""
    return sorted(reason_detail(text).keys())


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: capture_filter.py <file|->", file=sys.stderr)
        return 2
    if sys.argv[1] == "-":
        text = sys.stdin.read()
    else:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    detail = reason_detail(text)
    if not detail:
        print("clean")
        return 0
    for reason, snippets in sorted(detail.items()):
        print(f"FLAGGED {reason}:")
        for s in snippets[:5]:
            print(f"  ... {s} ...")
    print("Store the fix / missing config / workaround instead — never "
          "'X can't do Y' or raw error text.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
