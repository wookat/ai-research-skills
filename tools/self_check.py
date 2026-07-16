#!/usr/bin/env python3
"""Pack self-check: verify the pack's tools and paper-search sources are usable.

Run this BEFORE starting a research-pipeline run (it is step 1 of the pipeline's
启动自检清单). Offline by default: checks Python deps and script syntax only.
``--online`` additionally fires one live query per paper-search source and
reports which sources actually return results.

Exit code: 0 = all required checks pass; 1 = something required is missing.
"""

from __future__ import annotations

import argparse
import importlib
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# module -> (pip name, required?) — required means scoop-check cannot give a
# non-provisional verdict without it.
DEPS = {
    "yaml": ("pyyaml", True),
    "requests": ("requests", True),
    "openreview": ("openreview-py", True),
    "scholarly": ("scholarly", False),
    "numpy": ("numpy", False),
    "scipy": ("scipy", False),
}

SEARCH_SCRIPT = REPO_ROOT / "skills" / "paper-search" / "scripts" / "search_papers.py"


def check_deps() -> list[str]:
    missing_required = []
    for mod, (pip_name, required) in DEPS.items():
        try:
            importlib.import_module(mod)
            print(f"  ok       {mod}")
        except ImportError:
            tag = "MISSING! " if required else "missing  "
            print(f"  {tag}{mod}  ->  pip install {pip_name}"
                  + ("" if required else "  (optional)"))
            if required:
                missing_required.append(pip_name)
    return missing_required


def check_tools() -> list[str]:
    bad = []
    for script in sorted((REPO_ROOT / "tools").glob("*.py")):
        proc = subprocess.run([sys.executable, "-m", "py_compile", str(script)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            bad.append(script.name)
            print(f"  SYNTAX ERROR  tools/{script.name}")
    if not bad:
        print(f"  ok       {len(list((REPO_ROOT / 'tools').glob('*.py')))} tool scripts compile")
    return bad


_RESULT_LINE = re.compile(r"^\s*(?P<source>[a-z_]+): (?P<n>\d+) papers found\s*$")


def check_online() -> list[str]:
    """One live query through search_papers.py; report per-source result counts."""
    proc = subprocess.run(
        [sys.executable, str(SEARCH_SCRIPT), "--query", "transformer time series",
         "--start-year", "2023", "--end-year", "2026", "--max-papers", "2"],
        capture_output=True, text=True, timeout=300)
    counts: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        m = _RESULT_LINE.match(line)
        if m:
            counts[m.group("source")] = int(m.group("n"))
    if not counts:
        print("  ONLINE CHECK FAILED — no per-source result lines; stderr:")
        print("  " + (proc.stderr or "").strip()[:500])
        return ["search_papers.py"]
    dead = []
    for source, n in sorted(counts.items()):
        print(f"  {'ok      ' if n else 'DEAD    '} {source}: {n} results")
        if not n:
            dead.append(source)
    return dead


def main() -> int:
    ap = argparse.ArgumentParser(description="ai-research-skills pack self-check")
    ap.add_argument("--online", action="store_true",
                    help="also run one live query per paper-search source")
    a = ap.parse_args()

    print("[1/3] python deps")
    missing = check_deps()
    print("[2/3] tool script syntax")
    bad = check_tools()
    dead: list[str] = []
    if a.online:
        print("[3/3] live paper-search sources")
        dead = check_online()
    else:
        print("[3/3] live sources skipped (pass --online to test)")

    if missing or bad:
        print(f"\nFAIL: missing required deps={missing or 'none'}, broken scripts={bad or 'none'}")
        print("Fix: pip install -r requirements.txt")
        return 1
    if dead:
        print(f"\nWARN: dead sources: {dead} — scoop-check verdicts relying on these "
              "sources must be marked provisional (openreview in particular covers "
              "under-review collisions).")
    print("\nself-check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
