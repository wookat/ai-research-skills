"""Aggregate vision_audit reports across many posters.

Reads <outdir>/<poster>/audit.json (per-poster output of vision_audit),
prints a cross-poster summary:
- total issues
- category frequency (most-common bugs to fix first)
- severity breakdown
- per-poster issue counts
- top recurring issues (same category appearing in N posters)

Usage:
  python -m scripts.vision_aggregate /tmp/paper_extract_eval/
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path,
                    help="Root dir containing <poster>/audit.json subdirs")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    posters: dict[str, dict] = {}
    for audit_path in sorted(a.root.glob("*/audit.json")):
        name = audit_path.parent.name
        try:
            posters[name] = json.loads(audit_path.read_text())
        except json.JSONDecodeError:
            continue

    if not posters:
        sys.exit(f"no audit.json files found under {a.root}/*/")

    total_issues = sum(p["n_issues"] for p in posters.values())
    cat_global: dict[str, int] = defaultdict(int)
    sev_global: dict[str, int] = defaultdict(int)
    cat_by_poster: dict[str, set] = defaultdict(set)  # category → set of posters hit
    block_recur: dict[tuple[str, str], int] = defaultdict(int)  # (category, where) repeats

    for name, report in posters.items():
        for k, v in report.get("by_category", {}).items():
            cat_global[k] += v
            cat_by_poster[k].add(name)
        for k, v in report.get("by_severity", {}).items():
            sev_global[k] += v
        for it in report.get("issues", []):
            block_recur[(it["category"], it["where"][:60])] += 1

    print(f"\n=== VISION AUDIT AGGREGATE — {len(posters)} posters, {total_issues} total issues ===\n")

    print("By severity:")
    for sev in ("high", "medium", "low"):
        print(f"  {sev:>7s} : {sev_global.get(sev,0)}")

    print(f"\nBy category (most-common bugs — fix-priority list):")
    for cat, n in sorted(cat_global.items(), key=lambda x: -x[1]):
        n_posters = len(cat_by_poster[cat])
        print(f"  {n:>3d} issues across {n_posters} poster(s)  {cat}")

    print(f"\nPer-poster issue count:")
    for name, p in sorted(posters.items()):
        sevb = p.get("by_severity", {})
        print(f"  {name:<26s}  {p['n_issues']:>3d} issues  "
              f"(H{sevb.get('high',0)} M{sevb.get('medium',0)} L{sevb.get('low',0)})")

    print(f"\nTop recurring (category + similar location across posters):")
    for (cat, where), n in sorted(block_recur.items(), key=lambda x: -x[1])[:10]:
        if n > 1:
            print(f"  {n}× {cat:<20s} | {where}")

    if a.out:
        a.out.write_text(json.dumps({
            "n_posters": len(posters),
            "total_issues": total_issues,
            "by_severity": dict(sev_global),
            "by_category": {k: v for k, v in cat_global.items()},
            "category_poster_count": {k: sorted(v) for k, v in cat_by_poster.items()},
            "per_poster": {k: {"n": v["n_issues"],
                                "by_category": v.get("by_category", {}),
                                "by_severity": v.get("by_severity", {})}
                            for k, v in posters.items()},
        }, indent=2))
        print(f"\n[saved] {a.out}")


if __name__ == "__main__":
    main()
