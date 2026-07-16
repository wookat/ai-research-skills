#!/usr/bin/env python3
"""Unified interface to search for academic papers across multiple sources.

Supported sources: arXiv, DBLP, Google Scholar, OpenAlex, OpenReview,
Semantic Scholar, Crossref.
"""

import argparse
import concurrent.futures
import importlib
import json
from datetime import date, datetime
from typing import Optional

# Load .env (credentials for openreview etc.) before any source runs, so the aggregator works
# when invoked via bash without a shell-sourced .env. No-op if no .env is found.
try:
    from _env import load_env_once
    load_env_once()
except Exception:
    pass

# Map source name -> module that defines `search_papers_by_<source>`. Modules are imported
# LAZILY (only when a source is actually queried, see _load_source_func) so that a missing
# optional dependency for ONE source — e.g. `scholarly` for google_scholar — no longer crashes
# the whole aggregator at import time. By convention the function name equals the module name.
_SOURCE_MODULE = {
    "arxiv": "search_papers_by_arxiv",
    "dblp": "search_papers_by_dblp",
    # "google_scholar": "search_papers_by_google_scholar",  # needs `scholarly`; disabled by default
    "open_alex": "search_papers_by_open_alex",
    "openreview": "search_papers_by_openreview",
    "semantic_scholar": "search_papers_by_semantic_scholar",
    "crossref": "search_papers_by_crossref",
}
ALL_SOURCES = list(_SOURCE_MODULE.keys())


def _load_source_func(source: str):
    """Lazily import and return the search function for one source.

    Raises ImportError (with the underlying missing-module message) if the source's
    optional dependency is not installed — callers catch this and skip just that source."""
    module_name = _SOURCE_MODULE[source]
    module = importlib.import_module(module_name)
    return getattr(module, module_name)

def _parse_date(value, field_name: str) -> Optional[date]:
    """Parse a YYYY-MM-DD string (or pass through date/None) for the post-filter."""
    if value is None or isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as e:
        raise ValueError(f"{field_name} must be YYYY-MM-DD, got {value!r}") from e


def _filter_by_date_range(
    papers: list[dict],
    start_date: Optional[date],
    end_date: Optional[date],
) -> list[dict]:
    """Drop papers whose publication_date falls outside [start_date, end_date].

    Papers without a parseable publication_date are KEPT (we can't prove they're
    out of range, and dropping them would silently lose otherwise relevant results)."""
    if not start_date and not end_date:
        return papers
    kept: list[dict] = []
    for p in papers:
        pub_str = p.get("publication_date")
        if not pub_str:
            kept.append(p)
            continue
        try:
            pub = datetime.strptime(pub_str[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            kept.append(p)
            continue
        if start_date and pub < start_date:
            continue
        if end_date and pub > end_date:
            continue
        kept.append(p)
    return kept


def search_papers(
    query: str,
    start_year: int,
    end_year: int,
    max_results: int = 10,
    sources: Optional[list[str]] = None,
    parallel: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, list[dict]]:
    """Search for papers across multiple academic sources.

    Args:
        query: Search query string.
        start_year: Filter papers published from this year (used in source queries).
        end_year: Filter papers published up to this year (used in source queries).
        max_results: Maximum number of papers to return per source.
        sources: List of source names to search. Defaults to all sources.
            Valid values: arxiv, dblp, google_scholar, open_alex, openreview,
            semantic_scholar, crossref.
        parallel: Whether to query sources in parallel (default: True).
        start_date: Optional YYYY-MM-DD lower bound applied as a post-filter to all
            returned papers (finer-grained than start_year). Papers without a
            parseable publication_date are kept.
        end_date: Optional YYYY-MM-DD upper bound applied as a post-filter (inclusive).

    Returns:
        Dictionary mapping source name to list of paper dictionaries.
        Each paper dict contains: title, authors, year, abstract, url,
        venue, citation_count, publication_date, source.
    """
    results, _ = search_papers_with_status(
        query=query, start_year=start_year, end_year=end_year,
        max_results=max_results, sources=sources, parallel=parallel,
        start_date=start_date, end_date=end_date,
    )
    return results


def search_papers_with_status(
    query: str,
    start_year: int,
    end_year: int,
    max_results: int = 10,
    sources: Optional[list[str]] = None,
    parallel: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Like search_papers, but also returns per-source status.

    Second return value maps source name -> status string: "ok" when the source
    executed without error (even with 0 hits), or "ERROR: <message>" when it
    failed. Callers (scoop-check, self_check) use this to distinguish a genuine
    zero-hit result from a dead source — the two must never look the same.
    """
    sources = sources or ALL_SOURCES
    invalid = set(sources) - set(ALL_SOURCES)
    if invalid:
        raise ValueError(f"Unknown sources: {invalid}. Valid: {ALL_SOURCES}")

    start_d = _parse_date(start_date, "start_date")
    end_d = _parse_date(end_date, "end_date")
    if start_d and end_d and start_d > end_d:
        raise ValueError(f"start_date {start_d} is after end_date {end_d}")

    results: dict[str, list[dict]] = {}
    status: dict[str, str] = {}

    def _search(source: str) -> tuple[str, list[dict], str]:
        try:
            func = _load_source_func(source)
        except Exception as e:
            # Missing optional dependency for this source — skip it, keep the others working.
            print(f"[{source}] unavailable (import failed: {e}); skipping this source.")
            return source, [], f"ERROR: import failed: {e}"
        try:
            papers = func(query, start_year, end_year, max_results)
        except Exception as e:
            print(f"[{source}] Error: {e}")
            return source, [], f"ERROR: {e}"
        return source, papers, "ok"

    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
            futures = {executor.submit(_search, s): s for s in sources}
            for future in concurrent.futures.as_completed(futures):
                source, papers, st = future.result()
                results[source] = papers
                status[source] = st
    else:
        for source in sources:
            _, papers, st = _search(source)
            results[source] = papers
            status[source] = st

    if start_d or end_d:
        results = {s: _filter_by_date_range(ps, start_d, end_d) for s, ps in results.items()}

    return results, status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search papers across multiple academic sources",
    )
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--start-year", type=int, required=True, help="Start year")
    parser.add_argument("--end-year", type=int, required=True, help="End year")
    parser.add_argument(
        "--max-papers", type=int, default=10,
        help="Max number of papers per source (default: 10)",
    )
    parser.add_argument(
        "--sources", nargs="+", default=None,
        choices=ALL_SOURCES,
        help=f"Sources to search (default: all). Choices: {', '.join(ALL_SOURCES)}",
    )
    parser.add_argument(
        "--no-parallel", action="store_true",
        help="Disable parallel querying of sources",
    )
    parser.add_argument(
        "--start-date", default=None,
        help="Optional YYYY-MM-DD lower bound; applied as a post-filter (finer than --start-year)",
    )
    parser.add_argument(
        "--end-date", default=None,
        help="Optional YYYY-MM-DD inclusive upper bound; applied as a post-filter",
    )
    parser.add_argument(
        "--out", default=None, metavar="FILE",
        help="Write full results as JSONL to FILE and print only per-source counts "
             "and the SOURCE HEALTH block (keeps agent context small; downstream "
             "steps read the file instead of the terminal output)",
    )
    args = parser.parse_args()

    results, status = search_papers_with_status(
        query=args.query,
        start_year=args.start_year,
        end_year=args.end_year,
        max_results=args.max_papers,
        sources=args.sources,
        parallel=not args.no_parallel,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    total = 0
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for source, papers in results.items():
                for p in papers:
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
        for source, papers in sorted(results.items()):
            print(f"  {source}: {len(papers)} papers found")
            total += len(papers)
        print(f"\nWrote {total} papers to {args.out} (JSONL).")
    else:
        for source, papers in results.items():
            print(f"\n{'='*60}")
            print(f"  {source}: {len(papers)} papers found")
            print(f"{'='*60}")
            for i, p in enumerate(papers, 1):
                print(f"  [{i}] {p['title']}")
                print(f"      Authors: {', '.join(p['authors'][:3])}{'...' if len(p['authors']) > 3 else ''}")
                print(f"      Year: {p['year']}  Citations: {p['citation_count']}  Venue: {p['venue']}")
                print(f"      URL: {p['url']}")
                print()
            total += len(papers)

    print(f"\nTotal: {total} papers from {len(results)} sources.")

    # Per-source health: a dead source must never be mistaken for "no matches".
    print("\nSOURCE HEALTH:")
    for source in sorted(results):
        st = status.get(source, "ok")
        n = len(results[source])
        if st != "ok":
            print(f"  {source}: {st}")
        elif n == 0:
            print(f"  {source}: ok (0 hits for this query)")
        else:
            print(f"  {source}: ok ({n} results)")

# Example usage:
# python search_papers.py --query "data efficacy for LM training" --start-year 2024 --end-year 2026 --max-papers 20
# python search_papers.py --query "transformers" --start-year 2023 --end-year 2025 --sources arxiv semantic_scholar
