"""Final deliverables-presence gate — the *forcing function* that prevents
"fill loop done = task done" rationalization.

The 12-step paper2poster workflow ends with four required artifacts in the
output directory:

  - ``assets/meta/paper_spec.md`` (Step 4)
  - ``poster.html``    (Steps 6-9, fill loop)
  - ``poster.pdf``     (Step 10, render_poster.py)
  - ``poster.png``     (Step 10, render_poster.py)

In practice, models running the skill **probabilistically skip Step 10** —
they finish the fill loop (which itself has slack/polish hard gates), see
``poster.html`` in place, and rationalize "all hard gates passed, task done"
without ever invoking ``render_poster.py``. Observed N=2/3 skip rate on the
same paper across two sessions; not deterministic, can't be fixed by
adding more prose to SKILL.md.

This command is the deterministic check the model is required to run before
declaring done. It exits 1 with an explicit "missing X, run Y" message so the
failure forces the correct corrective action — no editorial judgment, no
self-evaluation.

Usage:
  check_poster.py deliverables <outdir>

Exit codes:
  0  all four files exist and meet minimum size thresholds
  1  one or more missing or suspiciously small (with remediation guidance)
  2  invalid argument (outdir doesn't exist or isn't a directory)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .cli_common import eprint as _eprint
from .textutil import ascii_safe


# Each entry: (filename, minimum size in bytes, what produced it, how to fix).
# Size floors are deliberately generous — a real poster will blow past them.
# The point is to catch zero-byte / truncated / placeholder files, not to
# audit content quality (that's slack/polish/verify-final's job).
_REQUIRED = [
    (
        "assets/meta/paper_spec.md",
        2_000,
        "Step 4 (spec generation)",
        "Re-run Step 4: write the 9-section spec to <outdir>/assets/meta/paper_spec.md.",
    ),
    (
        "poster.html",
        20_000,
        "Steps 6-9 (template substitution + fill loop)",
        "Re-run Steps 6-9: substitute the template, then run the fill loop "
        "until `check_poster.py slack --strict` passes.",
    ),
    (
        "poster.pdf",
        50_000,
        "Step 10 (render_poster.py)",
        "Run Step 10:  python <skills-dir>/paper2poster/scripts/"
        "render_poster.py <outdir>/poster.html",
    ),
    (
        "poster.png",
        20_000,
        "Step 10 (render_poster.py — produced alongside the PDF)",
        "Run Step 10:  python <skills-dir>/paper2poster/scripts/"
        "render_poster.py <outdir>/poster.html",
    ),
]


def cmd_deliverables(args: argparse.Namespace) -> int:
    outdir = Path(args.outdir).resolve()
    if not outdir.exists() or not outdir.is_dir():
        _eprint(f"ERROR: outdir not found or not a directory: "
                f"{ascii_safe(outdir)}")
        return 2

    missing: list[tuple[str, str, str]] = []  # (name, reason, fix)
    present: list[tuple[str, int]] = []  # (name, bytes)

    for name, min_bytes, produced_by, how_to_fix in _REQUIRED:
        path = outdir / name
        if not path.exists():
            missing.append((name, f"file does not exist (expected from "
                                  f"{produced_by})", how_to_fix))
            continue
        size = path.stat().st_size
        if size < min_bytes:
            missing.append((
                name,
                f"file exists but is {size} bytes (under {min_bytes} byte "
                f"floor — likely truncated or placeholder; expected from "
                f"{produced_by})",
                how_to_fix,
            ))
            continue
        present.append((name, size))

    # Always show what's there (positive feedback) and what's not.
    for name, size in present:
        print(f"  OK   {name:<18}  {size:>10,} bytes")
    for name, reason, _ in missing:
        print(f"  MISS {name:<18}  {reason}")

    if not missing:
        print(f"\nAll {len(_REQUIRED)} deliverables present in {outdir}. "
              f"You may declare the task done.")
        return 0

    # Failure path: print the exact commands the model needs to run.
    _eprint(f"\nFAIL: {len(missing)} of {len(_REQUIRED)} required "
            f"deliverable(s) missing in {ascii_safe(outdir)}.")
    _eprint("")
    _eprint("This gate exists because models often exit the fill loop "
            "thinking the task is done — but the fill loop only verifies "
            "HTML, not the rendered PDF/PNG. Run the fix(es) below, then "
            "re-run this command.")
    _eprint("")
    for name, _, how_to_fix in missing:
        _eprint(f"  {name}:")
        for line in how_to_fix.splitlines():
            _eprint(f"    {line}")
        _eprint("")
    return 1


def add_parser(sub: argparse._SubParsersAction) -> None:
    """Register the `deliverables` subcommand on the shared dispatcher."""
    p = sub.add_parser(
        "deliverables",
        help="REQUIRED before declaring done: assert all 4 final files "
             "exist in <outdir> (assets/meta/paper_spec.md, poster.html, "
             "poster.pdf, poster.png). Exit 1 with remediation guidance if "
             "any are missing or suspiciously small.",
    )
    p.add_argument(
        "outdir",
        help="path to the paper's output directory (contains poster.html)",
    )
    p.set_defaults(func=cmd_deliverables)
