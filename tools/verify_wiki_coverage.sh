#!/usr/bin/env bash
# verify_wiki_coverage.sh <wiki-dir> — diagnostic coverage report for the
# research wiki (integration-contract.md §2 Policy E: exit 1 reports gaps but
# is never propagated as a workflow gate).
#
# Checks:
#   1. every edge endpoint in graph/edges.jsonl has a page on disk
#   2. every entity page participates in at least one edge (no orphans)
#   3. required generated views exist (index.md, query_pack.md, log.md)
set -u

WIKI="${1:?usage: verify_wiki_coverage.sh <wiki-dir>}"
[ -d "$WIKI" ] || { echo "ERROR: wiki dir not found: $WIKI" >&2; exit 1; }

WIKI="$WIKI" python3 << 'PY'
import json, os, sys
from pathlib import Path

wiki = Path(os.environ["WIKI"])
dirs = {"paper": "papers", "idea": "ideas", "exp": "experiments", "claim": "claims"}
gaps = []

for view in ("index.md", "query_pack.md", "log.md"):
    if not (wiki / view).exists():
        gaps.append(f"missing view: {view}")

edges = []
edges_file = wiki / "graph" / "edges.jsonl"
if edges_file.exists():
    for line in edges_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            edges.append(json.loads(line))
else:
    gaps.append("missing graph/edges.jsonl")

def page(node_id):
    kind, _, slug = node_id.partition(":")
    d = dirs.get(kind)
    return (wiki / d / f"{slug}.md") if d else None

linked = set()
for e in edges:
    for end in (e.get("from", ""), e.get("to", "")):
        if not end:
            continue
        linked.add(end)
        p = page(end)
        if p is not None and not p.exists():
            gaps.append(f"edge endpoint has no page: {end}")

for kind, d in dirs.items():
    for f in sorted((wiki / d).glob("*.md")) if (wiki / d).is_dir() else []:
        node = f"{kind}:{f.stem}"
        if node not in linked:
            gaps.append(f"orphan entity (no edges): {node}")

print(f"Wiki coverage report: {wiki}")
print(f"  edges: {len(edges)}")
for kind, d in dirs.items():
    n = len(list((wiki / d).glob('*.md'))) if (wiki / d).is_dir() else 0
    print(f"  {d}: {n}")
if gaps:
    print(f"\nGAPS ({len(gaps)}):")
    for g in gaps:
        print(f"  - {g}")
    sys.exit(1)
print("\nNo coverage gaps found.")
PY
