"""Tests for paper-search source-health reporting.

A dead source must be reported as ERROR, never silently as "0 papers found" —
that distinction is what lets scoop-check downgrade verdicts to provisional
instead of mistaking an API failure for evidence of novelty.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "paper-search" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import search_papers as sp  # noqa: E402
import search_papers_by_openreview as orv  # noqa: E402


def _fake_loader(mapping):
    def load(source):
        entry = mapping[source]
        if isinstance(entry, Exception):
            raise entry
        return entry
    return load


def test_status_ok_error_and_empty(monkeypatch):
    paper = {"title": "T", "publication_date": "2024-01-01"}
    mapping = {
        "arxiv": lambda q, s, e, m: [paper],
        "dblp": lambda q, s, e, m: (_ for _ in ()).throw(RuntimeError("boom")),
        "crossref": lambda q, s, e, m: [],
    }
    monkeypatch.setattr(sp, "_load_source_func", _fake_loader(mapping))
    results, status = sp.search_papers_with_status(
        "q", 2023, 2026, sources=["arxiv", "dblp", "crossref"], parallel=False)
    assert results["arxiv"] == [paper]
    assert status["arxiv"] == "ok"
    assert results["dblp"] == []
    assert status["dblp"].startswith("ERROR:") and "boom" in status["dblp"]
    assert results["crossref"] == []
    assert status["crossref"] == "ok"  # genuine zero hits, not a failure


def test_status_import_failure(monkeypatch):
    monkeypatch.setattr(
        sp, "_load_source_func", _fake_loader({"arxiv": ImportError("no mod")}))
    results, status = sp.search_papers_with_status(
        "q", 2023, 2026, sources=["arxiv"], parallel=False)
    assert results["arxiv"] == []
    assert status["arxiv"].startswith("ERROR: import failed")


def test_search_papers_wrapper_unchanged(monkeypatch):
    paper = {"title": "T", "publication_date": "2024-01-01"}
    monkeypatch.setattr(
        sp, "_load_source_func", _fake_loader({"arxiv": lambda q, s, e, m: [paper]}))
    results = sp.search_papers("q", 2023, 2026, sources=["arxiv"], parallel=False)
    assert results == {"arxiv": [paper]}


class _FailingClient:
    def get_all_notes(self, **kwargs):
        raise RuntimeError("ChallengeRequiredError: Challenge verification required")


def test_openreview_all_venues_failing_raises(monkeypatch):
    monkeypatch.setattr(orv, "_openreview_clients",
                        lambda: (_FailingClient(), _FailingClient()))
    with pytest.raises(RuntimeError) as exc:
        orv.search_papers_by_openreview("q", 2023, 2026, max_results=5,
                                        venues=["ICLR.cc/2026/Conference"])
    msg = str(exc.value)
    assert "OpenReview venues failed" in msg
    assert "OPENREVIEW_USER" in msg  # actionable credential hint


class _EmptyClient:
    def get_all_notes(self, **kwargs):
        return []


def test_openreview_zero_hits_without_errors_returns_empty(monkeypatch):
    monkeypatch.setattr(orv, "_openreview_clients",
                        lambda: (_EmptyClient(), _EmptyClient()))
    papers = orv.search_papers_by_openreview("q", 2023, 2026, max_results=5,
                                             venues=["ICLR.cc/2026/Conference"])
    assert papers == []
