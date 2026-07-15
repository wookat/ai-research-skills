"""Model provenance helpers.

Minimal implementation bundled with this pack (the upstream ARIS repo ships a
larger version). `run_state.py` uses `model_family` to enforce cross-family
review: a verdict only counts as cross-model when the reviewer's family
differs from the executor's.
"""

from __future__ import annotations

_FAMILY_PREFIXES = [
    ("openai", ("gpt", "o1", "o3", "o4", "codex", "davinci", "chatgpt")),
    ("anthropic", ("claude", "sonnet", "opus", "haiku")),
    ("google", ("gemini", "gemma", "palm", "bard")),
    ("deepseek", ("deepseek",)),
    ("meta", ("llama",)),
    ("mistral", ("mistral", "mixtral", "codestral")),
    ("alibaba", ("qwen", "qwq")),
    ("zhipu", ("glm", "chatglm")),
    ("moonshot", ("kimi", "moonshot")),
    ("xai", ("grok",)),
    ("cognition", ("devin",)),
]


def model_family(model: str) -> str:
    """Return the vendor family for a model identifier.

    Matching is case-insensitive and prefix-based on the model name after
    stripping a ``vendor/`` prefix if present. Unknown models return the
    normalized model string itself so distinct unknown models still compare
    as different families.
    """
    normalized = (model or "").strip().lower()
    if "/" in normalized:
        vendor, _, rest = normalized.partition("/")
        for family, _prefixes in _FAMILY_PREFIXES:
            if vendor == family:
                return family
        normalized = rest or vendor
    for family, prefixes in _FAMILY_PREFIXES:
        if normalized.startswith(prefixes):
            return family
    return normalized
