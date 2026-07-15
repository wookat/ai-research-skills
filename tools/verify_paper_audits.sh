#!/usr/bin/env bash
# verify_paper_audits.sh <paper-dir> — canonical entry point (see
# shared-references/assurance-contract.md "Verifier Contract").
# Thin wrapper: the implementation lives in verify_paper_audits.py.
set -eu
exec python3 "$(dirname "$0")/verify_paper_audits.py" "$@"
