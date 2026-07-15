#!/usr/bin/env python3
"""verify_paper_audits.py — verifier for mandatory paper audits.

Implements the Verifier Contract in shared-references/assurance-contract.md:
single source of truth for "are mandatory audits complete and current?".
Called as `verify_paper_audits <paper-dir>`; exit 0 = all green, exit 1 =
any FAIL / BLOCKED / ERROR / STALE / missing artifact. Writes the structured
report to <paper-dir>/.aris/audit-verifier-report.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_VERDICTS = {"PASS", "WARN", "FAIL", "BLOCKED", "ERROR", "NOT_APPLICABLE"}
BLOCKING_VERDICTS = {"FAIL", "BLOCKED", "ERROR"}
REQUIRED_FIELDS = [
    "audit_skill", "verdict", "reason_code", "summary",
    "audited_input_hashes", "trace_path", "generated_at",
]
DEFAULT_AUDITS = {
    "proof-checker": "PROOF_AUDIT.json",
    "paper-claim-audit": "PAPER_CLAIM_AUDIT.json",
    "citation-audit": "CITATION_AUDIT.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def check_artifact(paper_dir: Path, skill: str, artifact: Path) -> dict:
    result = {"audit_skill": skill, "artifact": str(artifact), "problems": []}
    if not artifact.exists():
        result["status"] = "MISSING"
        result["problems"].append("artifact JSON not found")
        return result
    try:
        data = json.loads(artifact.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        result["status"] = "ERROR"
        result["problems"].append(f"invalid JSON: {e}")
        return result

    for field in REQUIRED_FIELDS:
        if field not in data:
            result["problems"].append(f"missing required field: {field}")
    verdict = data.get("verdict", "")
    result["verdict"] = verdict
    if verdict not in ALLOWED_VERDICTS:
        result["problems"].append(f"invalid verdict: {verdict!r}")

    # Semantic paper audits may not self-label deterministic.
    if data.get("review_independence") == "deterministic":
        result["problems"].append(
            "review_independence=deterministic rejected for semantic paper audits")

    stale = []
    for rel, expected in (data.get("audited_input_hashes") or {}).items():
        p = Path(rel) if rel.startswith("/") else paper_dir / rel
        if not p.exists():
            stale.append(f"{rel}: file missing")
        elif sha256(p) != expected:
            stale.append(f"{rel}: hash mismatch")
    if stale:
        result["status"] = "STALE"
        result["problems"].extend(stale)
        return result

    trace = data.get("trace_path", "")
    if trace:
        tp = Path(trace) if trace.startswith("/") else Path(trace)
        if not (tp.exists() and any(tp.iterdir()) if tp.is_dir() else tp.exists()):
            result["problems"].append(f"trace_path missing or empty: {trace}")

    if result["problems"]:
        result["status"] = "ERROR"
    elif verdict in BLOCKING_VERDICTS:
        result["status"] = "BLOCKING"
        result["problems"].append(f"verdict {verdict} blocks submission")
    else:
        result["status"] = "GREEN"
        result["independence"] = data.get("review_independence", "unspecified")
    return result


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_paper_audits.py <paper-dir>", file=sys.stderr)
        return 2
    paper_dir = Path(sys.argv[1])
    if not paper_dir.is_dir():
        print(f"ERROR: paper dir not found: {paper_dir}", file=sys.stderr)
        return 1

    manifest = paper_dir / ".aris" / "audit-manifest.json"
    if manifest.exists():
        audits = json.loads(manifest.read_text(encoding="utf-8"))
    else:
        audits = DEFAULT_AUDITS

    results = [check_artifact(paper_dir, skill, paper_dir / rel)
               for skill, rel in audits.items()]

    any_red = any(r["status"] != "GREEN" for r in results)
    if any_red:
        overall = "blocked"
    elif all(r.get("independence") in ("cross-family", "deterministic")
             for r in results):
        overall = "accepted"
    else:
        overall = "provisional"

    report = {
        "verifier": "verify_paper_audits",
        "paper_dir": str(paper_dir),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall_assurance": overall,
        "exit_code": 1 if any_red else 0,
        "audits": results,
    }
    out = paper_dir / ".aris" / "audit-verifier-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
