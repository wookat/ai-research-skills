#!/usr/bin/env python3
"""research_wiki.py — canonical helper for the research-wiki knowledge base.

Clean-room implementation of the helper interface documented in
skills/research-wiki/SKILL.md (the upstream ARIS helper is not open-source).
Entities: papers / ideas / experiments / claims; relationships live only in
graph/edges.jsonl; index.md, query_pack.md and Connections sections are
generated views.

Subcommands:
  init <wiki_dir>
  ingest_paper <wiki_dir> [--arxiv-id ID] [--title T --authors A --year Y --venue V]
               [--thesis S] [--tags t1,t2] [--update-on-exist]
  sync <wiki_dir> (--arxiv-ids id1,id2,... | --from-file FILE)
  add_edge <wiki_dir> --from NODE --to NODE --type TYPE [--evidence S]
  upsert_idea <wiki_dir> --slug S --title T [--stage proposed] [--outcome pending]
              [--thesis S] [--risks S] [--based-on paper:a,paper:b]
              [--target-gaps G1,G2] [--update-on-exist]
  add_experiment <wiki_dir> --slug S [--idea idea:X] [--verdict yes|partial|no]
              [--confidence high|medium|low] [--metrics S] [--reasoning S]
              [--provenance S] [--update-on-exist]
  add_claim <wiki_dir> --slug S --name N [--status drafted] [--statement S]
              [--provenance S] [--update-on-exist]
  update <wiki_dir> --node NODE_ID --field F --value V
  rebuild_query_pack <wiki_dir>
  log <wiki_dir> <message>
  lint <wiki_dir>
  stats <wiki_dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

EDGE_TYPES = {
    "extends", "contradicts", "addresses_gap", "inspired_by",
    "tested_by", "supports", "invalidates", "supersedes",
}
CLAIM_STATUSES = {
    "drafted", "unproven", "sound-modulo-imports", "verified",
    "refuted", "retracted",
}
ENTITY_DIRS = {"paper": "papers", "idea": "ideas", "exp": "experiments", "claim": "claims"}
QUERY_PACK_BUDGET = 8000


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def wiki_path(arg: str) -> Path:
    return Path(arg)


def append_log(wiki: Path, message: str) -> None:
    with (wiki / "log.md").open("a", encoding="utf-8") as f:
        f.write(f"- {now_iso()} — {message}\n")


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return re.sub(r"_+", "_", text)


# ---------- frontmatter helpers ----------

def dump_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for sk, sv in v.items():
                lines.append(f"  {sk}: {json.dumps(sv, ensure_ascii=False)}")
        elif v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {json.dumps(str(v), ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def parse_frontmatter(text: str) -> dict:
    meta: dict = {}
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return meta
    current_dict = None
    for line in m.group(1).splitlines():
        if re.match(r"^\s{2,}\S", line) and current_dict is not None:
            sk, _, sv = line.strip().partition(":")
            meta[current_dict][sk.strip()] = _parse_val(sv.strip())
            continue
        current_dict = None
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if v == "":
            meta[k] = {}
            current_dict = k
        else:
            meta[k] = _parse_val(v)
    return meta


def _parse_val(v: str):
    if v == "null":
        return None
    try:
        return json.loads(v)
    except (json.JSONDecodeError, ValueError):
        return v


def node_file(wiki: Path, node_id: str) -> Path | None:
    if ":" not in node_id:
        return None
    kind, _, slug = node_id.partition(":")
    d = ENTITY_DIRS.get(kind)
    if not d:
        return None
    return wiki / d / f"{slug}.md"


# ---------- edges ----------

def load_edges(wiki: Path) -> list[dict]:
    path = wiki / "graph" / "edges.jsonl"
    edges = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                edges.append(json.loads(line))
    return edges


def write_edge(wiki: Path, edge: dict) -> None:
    with (wiki / "graph" / "edges.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(edge, ensure_ascii=False) + "\n")


def regenerate_connections(wiki: Path) -> None:
    edges = load_edges(wiki)
    by_node: dict[str, list[str]] = {}
    for e in edges:
        by_node.setdefault(e["from"], []).append(
            f"- `{e['type']}` → `{e['to']}`" + (f" — {e['evidence']}" if e.get("evidence") else ""))
        by_node.setdefault(e["to"], []).append(
            f"- `{e['from']}` → `{e['type']}` → (this)" + (f" — {e['evidence']}" if e.get("evidence") else ""))
    for kind, d in ENTITY_DIRS.items():
        for page in sorted((wiki / d).glob("*.md")):
            text = page.read_text(encoding="utf-8")
            meta = parse_frontmatter(text)
            nid = meta.get("node_id") or f"{kind}:{page.stem}"
            block = "\n".join(by_node.get(nid, ["(no edges yet)"]))
            new = re.sub(
                r"(## Connections\n)(.*?)(?=\n## |\Z)",
                lambda m: m.group(1) + "\n" + block + "\n",
                text, count=1, flags=re.S)
            if new != text:
                page.write_text(new, encoding="utf-8")


# ---------- index / query pack ----------

def rebuild_index(wiki: Path) -> None:
    lines = ["# Research Wiki Index", "", f"_auto-generated {now_iso()}_", ""]
    for kind, d in ENTITY_DIRS.items():
        pages = sorted((wiki / d).glob("*.md"))
        lines.append(f"## {d} ({len(pages)})")
        lines.append("")
        for p in pages:
            meta = parse_frontmatter(p.read_text(encoding="utf-8"))
            title = meta.get("title") or meta.get("name") or p.stem
            lines.append(f"- `{kind}:{p.stem}` — {title}")
        lines.append("")
    (wiki / "index.md").write_text("\n".join(lines), encoding="utf-8")


def _section(text: str, heading: str) -> str:
    m = re.search(rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)", text, re.S)
    return m.group(1).strip() if m else ""


def rebuild_query_pack(wiki: Path) -> None:
    parts: list[str] = [f"# Query Pack (auto-generated {now_iso()})", ""]
    brief = Path("RESEARCH_BRIEF.md")
    if brief.exists():
        parts += ["## Project direction", brief.read_text(encoding="utf-8")[:600], ""]
    gap_map = wiki / "gap_map.md"
    if gap_map.exists():
        parts += ["## Top gaps", gap_map.read_text(encoding="utf-8")[:1200], ""]
    failed: list[str] = []
    ideas: list[str] = []
    for p in sorted((wiki / "ideas").glob("*.md")):
        meta = parse_frontmatter(p.read_text(encoding="utf-8"))
        line = f"- idea:{p.stem} — {meta.get('title', p.stem)} (outcome: {meta.get('outcome', 'unknown')})"
        if meta.get("outcome") in ("negative", "mixed"):
            failed.append(line)
        else:
            ideas.append(line)
    parts += ["## Failed ideas (anti-repeat banlist)"] + (failed or ["(none)"]) + [""]
    papers: list[str] = []
    for p in sorted((wiki / "papers").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        thesis = _section(text, "One-line thesis")[:200]
        papers.append(f"- paper:{p.stem} ({meta.get('year', '?')}, {meta.get('venue', '?')}): {thesis}")
    parts += ["## Top papers"] + (papers[:12] or ["(none)"]) + [""]
    parts += ["## Active ideas"] + (ideas or ["(none)"]) + [""]
    pack = "\n".join(parts)
    if len(pack) > QUERY_PACK_BUDGET:
        pack = pack[:QUERY_PACK_BUDGET - 20] + "\n...(truncated)"
    (wiki / "query_pack.md").write_text(pack, encoding="utf-8")


def refresh_views(wiki: Path) -> None:
    regenerate_connections(wiki)
    rebuild_index(wiki)
    rebuild_query_pack(wiki)


# ---------- subcommands ----------

def cmd_init(args) -> int:
    wiki = wiki_path(args.wiki)
    for d in list(ENTITY_DIRS.values()) + ["graph"]:
        (wiki / d).mkdir(parents=True, exist_ok=True)
    for name, content in [
        ("log.md", "# Wiki Log\n\n"),
        ("gap_map.md", "# Gap Map\n\n<!-- gaps with stable IDs: G1, G2, ... -->\n"),
    ]:
        f = wiki / name
        if not f.exists():
            f.write_text(content, encoding="utf-8")
    edges = wiki / "graph" / "edges.jsonl"
    if not edges.exists():
        edges.write_text("", encoding="utf-8")
    rebuild_index(wiki)
    rebuild_query_pack(wiki)
    append_log(wiki, "Wiki initialized")
    print(f"OK: wiki initialized at {wiki}")
    return 0


PAPER_BODY = """
# {title}

## One-line thesis

{thesis}

## Problem / Gap

## Method

## Key Results

## Assumptions

## Limitations / Failure Modes

## Reusable Ingredients

## Open Questions

## Claims

## Connections

(no edges yet)

## Relevance to This Project

"""


def fetch_arxiv(arxiv_id: str) -> dict | None:
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            root = ET.fromstring(r.read())
    except Exception as e:  # network failure → caller falls back to manual fields
        print(f"WARN: arXiv fetch failed for {arxiv_id}: {e}", file=sys.stderr)
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entry = root.find("a:entry", ns)
    if entry is None:
        return None
    title = re.sub(r"\s+", " ", entry.findtext("a:title", "", ns)).strip()
    authors = [a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)]
    published = entry.findtext("a:published", "", ns)
    abstract = re.sub(r"\s+", " ", entry.findtext("a:summary", "", ns)).strip()
    return {
        "title": title, "authors": authors,
        "year": int(published[:4]) if published[:4].isdigit() else None,
        "abstract": abstract,
    }


def _ingest_one(wiki: Path, args, arxiv_id: str | None) -> str | None:
    title, authors, year, venue, abstract = args.title, args.authors, args.year, args.venue, None
    if arxiv_id:
        meta = fetch_arxiv(arxiv_id)
        if meta:
            title = title or meta["title"]
            authors = authors or ", ".join(meta["authors"])
            year = year or meta["year"]
            venue = venue or "arXiv"
            abstract = meta["abstract"]
    if not title:
        print("ERROR: no title (arXiv fetch failed and --title not given)", file=sys.stderr)
        return None
    first_last = (authors or "unknown").split(",")[0].strip().split()[-1] if authors else "unknown"
    keyword = "_".join(slugify(title).split("_")[:4])
    slug = f"{slugify(first_last)}{year or ''}_{keyword}"
    page = wiki / "papers" / f"{slug}.md"
    if page.exists() and not args.update_on_exist:
        print(f"SKIP: paper:{slug} already exists")
        return slug
    meta = {
        "type": "paper", "node_id": f"paper:{slug}", "title": title,
        "authors": [a.strip() for a in (authors or "").split(",") if a.strip()],
        "year": year, "venue": venue or "arXiv",
        "external_ids": {"arxiv": arxiv_id, "doi": None, "s2": None},
        "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()],
        "added": now_iso(),
    }
    body = PAPER_BODY.format(title=title, thesis=args.thesis or "")
    if abstract and arxiv_id:
        body += f"\n## Abstract (original)\n\n> {abstract}\n"
    page.write_text(dump_frontmatter(meta) + body, encoding="utf-8")
    append_log(wiki, f"ingested paper:{slug}")
    print(f"OK: paper:{slug}")
    return slug


def cmd_ingest_paper(args) -> int:
    wiki = wiki_path(args.wiki)
    slug = _ingest_one(wiki, args, args.arxiv_id)
    if slug is None:
        return 1
    refresh_views(wiki)
    return 0


def cmd_sync(args) -> int:
    wiki = wiki_path(args.wiki)
    ids: list[str] = []
    if args.arxiv_ids:
        ids += [i.strip() for i in args.arxiv_ids.split(",") if i.strip()]
    if args.from_file:
        for line in Path(args.from_file).read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line:
                ids.append(line)
    if not ids:
        print("ERROR: no ids (use --arxiv-ids or --from-file)", file=sys.stderr)
        return 1
    for arxiv_id in ids:
        _ingest_one(wiki, args, arxiv_id)
    refresh_views(wiki)
    return 0


def cmd_add_edge(args) -> int:
    wiki = wiki_path(args.wiki)
    if args.type not in EDGE_TYPES:
        print(f"ERROR: edge type {args.type!r} not in {sorted(EDGE_TYPES)}", file=sys.stderr)
        return 1
    edge = {"from": args.src, "to": args.dst, "type": args.type,
            "evidence": args.evidence or "", "added": now_iso()}
    for e in load_edges(wiki):
        if (e["from"], e["to"], e["type"]) == (edge["from"], edge["to"], edge["type"]):
            print("SKIP: edge already exists")
            return 0
    write_edge(wiki, edge)
    append_log(wiki, f"edge {args.src} -{args.type}-> {args.dst}")
    refresh_views(wiki)
    print("OK: edge added")
    return 0


def _write_entity(wiki: Path, kind: str, slug: str, meta: dict, body: str,
                  update_on_exist: bool) -> bool:
    page = wiki / ENTITY_DIRS[kind] / f"{slug}.md"
    if page.exists() and not update_on_exist:
        print(f"SKIP: {kind}:{slug} already exists")
        return True
    page.write_text(dump_frontmatter(meta) + body, encoding="utf-8")
    append_log(wiki, f"upserted {kind}:{slug}")
    print(f"OK: {kind}:{slug}")
    return True


def cmd_upsert_idea(args) -> int:
    wiki = wiki_path(args.wiki)
    meta = {
        "type": "idea", "node_id": f"idea:{args.slug}", "title": args.title,
        "stage": args.stage, "outcome": args.outcome, "added": now_iso(),
    }
    body = (f"\n# {args.title}\n\n## Thesis\n\n{args.thesis or ''}\n\n"
            f"## Risks\n\n{args.risks or ''}\n\n## Failure notes\n\n\n"
            "## Connections\n\n(no edges yet)\n")
    _write_entity(wiki, "idea", args.slug, meta, body, args.update_on_exist)
    for src in [s.strip() for s in (args.based_on or "").split(",") if s.strip()]:
        write_edge(wiki, {"from": f"idea:{args.slug}", "to": src,
                          "type": "inspired_by", "evidence": "", "added": now_iso()})
    for gap in [g.strip() for g in (args.target_gaps or "").split(",") if g.strip()]:
        write_edge(wiki, {"from": f"idea:{args.slug}", "to": f"gap:{gap}",
                          "type": "addresses_gap", "evidence": "", "added": now_iso()})
    refresh_views(wiki)
    return 0


def cmd_add_experiment(args) -> int:
    wiki = wiki_path(args.wiki)
    meta = {
        "type": "exp", "node_id": f"exp:{args.slug}", "title": args.slug,
        "idea": args.idea, "verdict": args.verdict, "confidence": args.confidence,
        "provenance": args.provenance, "added": now_iso(),
    }
    body = (f"\n# {args.slug}\n\n## Metrics\n\n{args.metrics or ''}\n\n"
            f"## Reasoning\n\n{args.reasoning or ''}\n\n"
            "## Connections\n\n(no edges yet)\n")
    _write_entity(wiki, "exp", args.slug, meta, body, args.update_on_exist)
    if args.idea:
        write_edge(wiki, {"from": args.idea, "to": f"exp:{args.slug}",
                          "type": "tested_by", "evidence": "", "added": now_iso()})
    refresh_views(wiki)
    return 0


def cmd_add_claim(args) -> int:
    wiki = wiki_path(args.wiki)
    if args.status not in CLAIM_STATUSES:
        print(f"ERROR: claim status {args.status!r} not in {sorted(CLAIM_STATUSES)} "
              "(empirical support is edges-only, never status)", file=sys.stderr)
        return 1
    meta = {
        "type": "claim", "node_id": f"claim:{args.slug}", "name": args.name,
        "status": args.status, "provenance": args.provenance, "added": now_iso(),
    }
    body = (f"\n# {args.name}\n\n## Statement\n\n{args.statement or ''}\n\n"
            "## Connections\n\n(no edges yet)\n")
    _write_entity(wiki, "claim", args.slug, meta, body, args.update_on_exist)
    refresh_views(wiki)
    return 0


def cmd_update(args) -> int:
    wiki = wiki_path(args.wiki)
    page = node_file(wiki, args.node)
    if page is None or not page.exists():
        print(f"ERROR: node {args.node} not found", file=sys.stderr)
        return 1
    kind = args.node.partition(":")[0]
    if kind == "claim" and args.field == "status":
        if args.value not in CLAIM_STATUSES:
            print(f"ERROR: claim status must be one of {sorted(CLAIM_STATUSES)}; "
                  "empirical support is carried by edges only", file=sys.stderr)
            return 1
    text = page.read_text(encoding="utf-8")
    new_line = f"{args.field}: {json.dumps(args.value, ensure_ascii=False)}"
    pattern = rf"^{re.escape(args.field)}:.*$"
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if m and re.search(pattern, m.group(1), re.M):
        fm = re.sub(pattern, new_line, m.group(1), count=1, flags=re.M)
        text = text.replace(m.group(1), fm, 1)
    elif m:
        text = text.replace("\n---", f"\n{new_line}\n---", 1)
    page.write_text(text, encoding="utf-8")
    append_log(wiki, f"update {args.node} {args.field}={args.value}")
    refresh_views(wiki)
    print(f"OK: {args.node} {args.field} updated")
    return 0


def cmd_rebuild_query_pack(args) -> int:
    wiki = wiki_path(args.wiki)
    rebuild_query_pack(wiki)
    print("OK: query_pack.md rebuilt")
    return 0


def cmd_log(args) -> int:
    append_log(wiki_path(args.wiki), args.message)
    return 0


def cmd_lint(args) -> int:
    wiki = wiki_path(args.wiki)
    edges = load_edges(wiki)
    linked = {e["from"] for e in edges} | {e["to"] for e in edges}
    findings: list[str] = []
    for kind, d in ENTITY_DIRS.items():
        for p in sorted((wiki / d).glob("*.md")):
            nid = f"{kind}:{p.stem}"
            text = p.read_text(encoding="utf-8")
            if nid not in linked:
                findings.append(f"- orphan: `{nid}` has zero edges")
            if len(re.findall(r"## .*\n\s*(?=\n## |\Z)", text)) >= 3:
                findings.append(f"- sparse: `{nid}` has 3+ empty sections")
    support: dict[str, set] = {}
    for e in edges:
        if e["type"] in ("supports", "invalidates"):
            support.setdefault(e["to"], set()).add(e["type"])
    for node, kinds in support.items():
        if kinds == {"supports", "invalidates"}:
            findings.append(f"- contradiction: `{node}` has both supports and invalidates edges")
    report = "# Lint Report\n\n" + ("\n".join(findings) if findings else "No issues found.") + "\n"
    (wiki / "LINT_REPORT.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


def cmd_stats(args) -> int:
    wiki = wiki_path(args.wiki)
    counts = {d: len(list((wiki / d).glob("*.md"))) for d in ENTITY_DIRS.values()}
    print("Research Wiki Stats")
    print(f"Papers: {counts['papers']}")
    print(f"Ideas: {counts['ideas']}")
    print(f"Experiments: {counts['experiments']}")
    print(f"Claims: {counts['claims']}")
    print(f"Edges: {len(load_edges(wiki))}")
    print(f"Last checked: {now_iso()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **_):
        sp = sub.add_parser(name)
        sp.add_argument("wiki")
        sp.set_defaults(fn=fn)
        return sp

    add("init", cmd_init)

    sp = add("ingest_paper", cmd_ingest_paper)
    sp.add_argument("--arxiv-id")
    sp.add_argument("--title")
    sp.add_argument("--authors")
    sp.add_argument("--year", type=int)
    sp.add_argument("--venue")
    sp.add_argument("--thesis")
    sp.add_argument("--tags")
    sp.add_argument("--update-on-exist", action="store_true")

    sp = add("sync", cmd_sync)
    sp.add_argument("--arxiv-ids")
    sp.add_argument("--from-file")
    sp.set_defaults(title=None, authors=None, year=None, venue=None,
                    thesis=None, tags=None, update_on_exist=False)

    sp = add("add_edge", cmd_add_edge)
    sp.add_argument("--from", dest="src", required=True)
    sp.add_argument("--to", dest="dst", required=True)
    sp.add_argument("--type", required=True)
    sp.add_argument("--evidence")

    sp = add("upsert_idea", cmd_upsert_idea)
    sp.add_argument("--slug", required=True)
    sp.add_argument("--title", required=True)
    sp.add_argument("--stage", default="proposed")
    sp.add_argument("--outcome", default="pending",
                    choices=["unknown", "pending", "negative", "mixed", "positive"])
    sp.add_argument("--thesis")
    sp.add_argument("--risks")
    sp.add_argument("--based-on")
    sp.add_argument("--target-gaps")
    sp.add_argument("--update-on-exist", action="store_true")

    sp = add("add_experiment", cmd_add_experiment)
    sp.add_argument("--slug", required=True)
    sp.add_argument("--idea")
    sp.add_argument("--verdict", choices=["yes", "partial", "no"])
    sp.add_argument("--confidence", choices=["high", "medium", "low"])
    sp.add_argument("--metrics")
    sp.add_argument("--reasoning")
    sp.add_argument("--provenance")
    sp.add_argument("--update-on-exist", action="store_true")

    sp = add("add_claim", cmd_add_claim)
    sp.add_argument("--slug", required=True)
    sp.add_argument("--name", required=True)
    sp.add_argument("--status", default="drafted")
    sp.add_argument("--statement")
    sp.add_argument("--provenance")
    sp.add_argument("--update-on-exist", action="store_true")

    sp = add("update", cmd_update)
    sp.add_argument("--node", required=True)
    sp.add_argument("--field", required=True)
    sp.add_argument("--value", required=True)

    add("rebuild_query_pack", cmd_rebuild_query_pack)

    sp = add("log", cmd_log)
    sp.add_argument("message")

    add("lint", cmd_lint)
    add("stats", cmd_stats)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
