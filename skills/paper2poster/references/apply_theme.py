#!/usr/bin/env python3
"""apply_theme.py -- swap a rendered poster's color THEME in place (no re-render).

The poster templates drive every chrome element -- title bar, card borders, h2
text + underline, callout accents -- from a small set of CSS custom properties
in the canonical `:root` block: `--accent`, `--accent-soft`, `--callout`. This
script rewrites just those hex values; layout, typography, figures, and content
are untouched, so re-theming is O(seconds) with no Claude tokens and no
Playwright re-render.

The injection point (the `:root` `--accent` / `--accent-soft` / `--callout`
lines) is IDENTICAL in the landscape composed poster.html and in the legacy
portrait monolith, so ONE injector re-themes both orientations.

Random theme selection is DETERMINISTIC: `--theme random` hashes a seed
(default the poster path) so a wave of posters gets a stable, reproducible
SPREAD across the palette -- the same mechanism `compose_poster.py` uses for
its layout/style/header axes, and NOT a flaky model "pick a color" step.

Five deep-academic bundles. Each theme's `--callout` deliberately CONTRASTS its
`--accent` so the "this is the result" register never clashes with a same-hue
accent (a red poster gets a navy callout, etc.). Neutrals (text / muted / bg)
are the templates' fixed defaults and are NOT swapped. Every accent is dark +
saturated enough to give white titlebar text >= 4.5:1 contrast AND read as a
distinct outline on white.

Usage:
    python references/apply_theme.py <poster.html> --theme random
    python references/apply_theme.py <poster.html> --theme teal --dry-run

Exit codes:
    0  success (or already on the target theme)
    1  no `--accent: #...` line found (not a paper2poster template)
    2  invalid CLI args / file missing
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# 8 theme bundles -- single source of truth, taken verbatim from the palette the
# gallery recolor used (p2p-bench/gen_gallery_pdf.py PALETTE), the "good color
# schemes" this pool is meant to reproduce. Each is {accent, accent-soft}; the
# result-register `--callout` (#ae2622 crimson) is deliberately NOT swapped, so
# it stays a consistent "this is the number" cue across every theme (exactly how
# the gallery shipped). Every accent is dark + saturated enough for white
# titlebar text >= 4.5:1 AND reads as a distinct color as h2 text / borders on
# the light (white / pale-tint) header.
THEMES: dict[str, dict[str, str]] = {
    "blue":     {"accent": "#1d3a87", "accent-soft": "#e8edf7"},
    "teal":     {"accent": "#0f6070", "accent-soft": "#e2eff1"},
    "green":    {"accent": "#2d5f3e", "accent-soft": "#e6f0ea"},
    "burgundy": {"accent": "#8f2437", "accent-soft": "#f6e7ea"},
    "purple":   {"accent": "#4b2e83", "accent-soft": "#ece7f4"},
    "rust":     {"accent": "#a2521c", "accent-soft": "#f6ece1"},
    "slate":    {"accent": "#33415e", "accent-soft": "#e9ecf3"},
    "plum":     {"accent": "#7d2860", "accent-soft": "#f4e6ef"},
    # Neutral / minimal "clean white" register: a near-black charcoal accent (no
    # hue), so the poster reads grayscale on the light template background.
    "mono":     {"accent": "#34373b", "accent-soft": "#eeeff1"},
}

# Vars rewritten per theme, longest name first (so `--accent-soft` is not
# clobbered by `--accent`). `--play-highlight-blue` (the "now playing" audio ring
# baseline) tracks the accent, matching the gallery recolor. Each is swapped in
# its FIRST `:root` occurrence only (count=1).
ROLES = ("accent-soft", "accent", "play-highlight-blue")


def _ink(accent_hex: str) -> str:
    """Readable text color for text placed ON the accent: light ink for a dark
    accent, dark ink for a light accent (WCAG relative luminance). So an accent
    pill's label stays legible whatever theme (even a light custom accent) is
    applied — not a hard-coded white that vanishes on a pale accent."""
    h = accent_hex.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except Exception:
        return "#ffffff"
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return "#ffffff" if L < 0.4 else "#141414"


def _rand_pick_list(opts: list[str], seed: str) -> str:
    """Deterministically pick one of ``opts`` keyed by ``seed`` (SHA-256).
    Mirrors compose_poster.py's sampler so themes spread reproducibly across a
    wave seeded by output paths, with no flaky model 'pick random' step."""
    if not opts:
        sys.exit(f"_rand_pick_list: empty option list for seed {seed!r}")
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    return opts[h % len(opts)]


def resolve_theme(name: str, seed: str) -> str:
    """Resolve a theme name. ``random`` -> deterministic pick keyed by ``seed``;
    any other name must be a key of THEMES (exits non-zero otherwise)."""
    if name == "random":
        return _rand_pick_list(sorted(THEMES), seed)
    if name not in THEMES:
        sys.exit(f"apply_theme: unknown theme {name!r}; "
                 f"choose from: random, {', '.join(sorted(THEMES))}")
    return name


def recolor(src: str, theme: dict[str, str]) -> tuple[str, list[tuple[str, str, str]]]:
    """Return the recolored html plus a list of (role, old_hex, new_hex).
    Swaps each ROLE's hex in the FIRST `--role: #hex` occurrence only."""
    out = src
    changes: list[tuple[str, str, str]] = []
    for role in ROLES:
        # play-highlight-blue is not a palette key -- it tracks the accent so the
        # "now playing" audio ring stays consistent (matches the gallery recolor).
        new_hex = theme.get(role, theme["accent"])
        pat = re.compile(rf"(--{role}:\s*)(#[0-9a-fA-F]{{3,8}})", re.IGNORECASE)
        m = pat.search(out)
        if not m:
            continue
        old_hex = m.group(2)
        if old_hex.upper() == new_hex.upper():
            continue
        out = pat.sub(rf"\g<1>{new_hex}", out, count=1)
        changes.append((role, old_hex, new_hex))
    # Adaptive on-accent text color, derived from the resolved accent luminance,
    # injected right after the :root --accent declaration (idempotent). Used by
    # accent pills (e.g. the scan-to-read Paper/Code chips) via var(--accent-ink).
    ink = _ink(theme["accent"])
    if re.search(r"--accent-ink:\s*#[0-9a-fA-F]{3,8}", out, re.I):
        out = re.sub(r"(--accent-ink:\s*)#[0-9a-fA-F]{3,8}",
                     rf"\g<1>{ink}", out, count=1, flags=re.I)
    else:
        m = re.search(r"--accent:\s*#[0-9a-fA-F]{3,8};?", out, re.I)
        if m:
            out = out[:m.end()] + f"\n  --accent-ink: {ink};" + out[m.end():]
    changes.append(("accent-ink", "", ink))
    return out, changes


def apply_theme_to_file(html_path: Path, theme_name: str, *,
                        seed: str | None = None) -> str:
    """Resolve ``theme_name`` (``random`` keyed by ``seed`` or the path), recolor
    ``html_path`` in place, and return the RESOLVED theme name. For programmatic
    use by compose_poster.py."""
    resolved = resolve_theme(theme_name, seed or str(html_path))
    src = html_path.read_text(encoding="utf-8")
    new_src, _ = recolor(src, THEMES[resolved])
    html_path.write_text(new_src, encoding="utf-8")
    return resolved


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="apply_theme.py",
        description="Swap a poster.html's :root color theme in place "
                    "(landscape or portrait) without re-rendering.",
    )
    ap.add_argument("html", type=Path,
                    help="path to poster.html (or any html with --accent etc. in :root)")
    ap.add_argument("--theme", default="random",
                    help="random (default; deterministic per --seed) or one of: "
                         + ", ".join(sorted(THEMES)))
    ap.add_argument("--seed", default=None,
                    help="seed for --theme random (default: the html path)")
    ap.add_argument("--output", type=Path,
                    help="write to a different path instead of overwriting input")
    ap.add_argument("--dry-run", action="store_true",
                    help="show planned changes without writing")
    args = ap.parse_args(argv)

    if not args.html.exists():
        print(f"error: {args.html} does not exist", file=sys.stderr)
        return 2

    resolved = resolve_theme(args.theme, args.seed or str(args.html))
    src = args.html.read_text(encoding="utf-8")
    new_src, changes = recolor(src, THEMES[resolved])

    if not changes:
        print(f"[apply_theme] {args.html}: no recolorable vars found "
              f"(or already on theme {resolved!r})")
        return 1 if "--accent:" not in src else 0

    print(f"[apply_theme] {args.html} -> theme={resolved}"
          + (f" (from --theme {args.theme})" if args.theme != resolved else ""))
    for role, old, new in changes:
        print(f"  --{role:<12} {old} -> {new}")

    if args.dry_run:
        print("[apply_theme] --dry-run: not writing")
        return 0

    dest = args.output or args.html
    dest.write_text(new_src, encoding="utf-8")
    if dest != args.html:
        print(f"[apply_theme] wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
