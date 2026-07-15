#!/usr/bin/env python3
"""Pack-native skill inventory checker.

Validates every ``skills/*/SKILL.md`` frontmatter and keeps
``docs/SKILLS_CATALOG.md`` in sync with the actual skill set, so catalog drift
is caught in CI instead of by a reader.

Checks:
  1. every skill directory (except ``shared-references``) has a SKILL.md;
  2. frontmatter is valid YAML with non-empty ``name`` and ``description``;
  3. ``name`` matches the directory name;
  4. names are unique across the pack;
  5. docs/SKILLS_CATALOG.md matches the generated catalog exactly.

Usage:
  python3 tools/check_pack_inventory.py           # check (exit 1 on drift)
  python3 tools/check_pack_inventory.py --write   # regenerate the catalog
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
CATALOG = REPO_ROOT / "docs" / "SKILLS_CATALOG.md"
NON_SKILL_DIRS = {"shared-references"}

HEADER = """# Skills Catalog

自动生成，勿手改 — 由 `python3 tools/check_pack_inventory.py --write` 重新生成，
CI 中由同一脚本校验是否漂移。

| Skill | Description |
|---|---|
"""


def _one_line(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def collect_skills() -> tuple[list[tuple[str, str]], list[str]]:
    """Return (sorted [(name, description)], errors)."""
    errors: list[str] = []
    rows: list[tuple[str, str]] = []
    seen: dict[str, str] = {}
    for d in sorted(p for p in SKILLS_ROOT.iterdir() if p.is_dir()):
        if d.name in NON_SKILL_DIRS:
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"{d.name}: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            errors.append(f"{d.name}: SKILL.md has no YAML frontmatter")
            continue
        try:
            _, fm, _ = text.split("---", 2)
            meta = yaml.safe_load(fm)
        except (ValueError, yaml.YAMLError) as e:
            errors.append(f"{d.name}: invalid frontmatter YAML ({e})")
            continue
        if not isinstance(meta, dict):
            errors.append(f"{d.name}: frontmatter is not a mapping")
            continue
        name = (meta.get("name") or "").strip()
        desc = str(meta.get("description") or "").strip()
        if not name:
            errors.append(f"{d.name}: frontmatter missing non-empty `name`")
            continue
        if not desc:
            errors.append(f"{d.name}: frontmatter missing non-empty `description`")
            continue
        if name != d.name:
            errors.append(f"{d.name}: frontmatter name {name!r} != directory name")
        if name in seen:
            errors.append(f"{d.name}: duplicate skill name {name!r} (also {seen[name]})")
        seen[name] = d.name
        rows.append((name, desc))
    return sorted(rows), errors


def render_catalog(rows: list[tuple[str, str]]) -> str:
    lines = [HEADER.rstrip("\n")]
    for name, desc in rows:
        lines.append(f"| [`{name}`](../skills/{name}/SKILL.md) | {_one_line(desc)} |")
    lines.append("")
    lines.append(f"共 {len(rows)} 个 skill。")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="regenerate docs/SKILLS_CATALOG.md")
    a = ap.parse_args()

    rows, errors = collect_skills()
    for e in errors:
        print(f"error: {e}", file=sys.stderr)

    expected = render_catalog(rows)
    if a.write:
        CATALOG.parent.mkdir(parents=True, exist_ok=True)
        CATALOG.write_text(expected, encoding="utf-8")
        print(f"wrote {CATALOG.relative_to(REPO_ROOT)} ({len(rows)} skills)")
    else:
        if not CATALOG.exists():
            errors.append("docs/SKILLS_CATALOG.md missing — run with --write")
            print("error: docs/SKILLS_CATALOG.md missing — run with --write", file=sys.stderr)
        elif CATALOG.read_text(encoding="utf-8") != expected:
            errors.append("catalog drift")
            print("error: docs/SKILLS_CATALOG.md is out of date — run "
                  "`python3 tools/check_pack_inventory.py --write`", file=sys.stderr)

    if errors:
        return 1
    print(f"inventory OK: {len(rows)} skills, catalog in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
