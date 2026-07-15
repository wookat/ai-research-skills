# Idea Spark — Setup (first use only)

Read this once when installing the skill; at run time SKILL.md never needs this file. The skill's Phase 0 + Phase 3.1 retrieval needs API credentials for 2 of the 4 connectors. Without them the affected connectors are skipped and the orchestrator continues with whichever connectors are available — but it prints a prominent **CONNECTORS DEGRADED** banner and writes a `.connectors_degraded` marker so a partial run is never mistaken for a full one.

0. **Set two shell variables once per session** — where this skill is installed, and where run outputs should go. Neither depends on the harness:
   ```bash
   SKILL_DIR=~/.claude/skills/idea-spark            # Claude Code default; Codex CLI: ~/.codex/skills/idea-spark; else wherever this folder lives
   RUN_DIR="$PWD/ideaspark_run/<topic-slug>" && mkdir -p "$RUN_DIR"   # convention: one run = one dir under ideaspark_run/, kebab-case topic slug; any absolute dir works
   ```
   `RUN_DIR` is purely an output anchor — the orchestrator only ever sees the absolute `--out` paths you pass, so the variable *name* does not matter (Claude Code sessions can reuse the injected `CLAUDE_PROJECT_DIR` as their `RUN_DIR`). The orchestrator hard-fails early with an actionable message when a path argument contains an unexpanded `$variable`, collapses to filesystem root (empty expansion, e.g. `/phase0`), or is a relative `--out` — instead of a confusing `FileNotFoundError` mid-run.

1. **Install the skill**: `idea-spark` — Phase 0 literature search runs from its bundled connector scripts (no separate sub-skill). On non-Claude-Code harnesses, clone or copy this folder anywhere and point `SKILL_DIR` at it.

2. **Install Python deps** (cross-platform — macOS & Linux): `python3 -m pip install feedparser openreview-py beautifulsoup4 pymupdf`. Four lean packages. Skipping this is the most common first-run failure: `arxiv` errors with `package not installed`, and missing `pymupdf`/`beautifulsoup4` silently degrades every full-text fetch to abstract-only.
   - **PEP 668 systems** (recent macOS/Homebrew & Ubuntu 23.04+) reject a bare `pip install` with `externally-managed-environment`. Two safe options:
     - **venv (recommended):** `python3 -m venv .venv && source .venv/bin/activate && pip install feedparser openreview-py beautifulsoup4 pymupdf` — then launch every phase **from this same activated shell** (see the connector-degradation note below).
     - **user install:** `python3 -m pip install --user --break-system-packages feedparser openreview-py beautifulsoup4 pymupdf`.
   - **Use the SAME interpreter everywhere.** `check_connectors` and the phase commands must run under the one Python that has these packages. A package installed for `pip3` but launched under a different `python3` (or a background/non-login shell that drops `--user` site-packages) will pass `check_connectors` yet skip `arxiv`/`openreview` at runtime — the run prints a loud **CONNECTORS DEGRADED** banner and drops a `.connectors_degraded` marker when that happens.
   - **Optional deps (only if you want the extras):** PDF compilation of the idea card needs **xelatex** *or* **tectonic** (macOS `brew install --cask mactex-no-gui` or `brew install tectonic`; Ubuntu `sudo apt-get install texlive-xetex` or `cargo install tectonic`). Without either, the `.md`/`.tex` cards are still written and only the PDF is skipped (with a hint). The optional pipeline-diagram image needs the `azure-*` packages; absent, it is skipped silently.

3. **Copy** the env template at the project root: `cp .env.template .env`.

4. **Fill in keys** (priority order — by impact on retrieval quality):

| Key | Required for | How to get |
|---|---|---|
| `OPENREVIEW_USER` + `OPENREVIEW_PASS` | OpenReview connector (in-review forward signal). Without these, openreview is silently skipped — you lose the 0-6mo in-review window unique to it. | Free signup at https://openreview.net |
| `SEMANTICSCHOLAR_API_KEY` | Semantic Scholar connector at usable rate. Anonymous tier (~100 req/5min) hits 429 on Phase 0 multi-query batches; with key it's stable at 1 req/s. | Free apply at https://www.semanticscholar.org/product/api#api-key-form (≈24h review). Connector still runs anonymously without it but will frequently 429. |
| `OPENALEX_API_KEY` | Optional, premium rate. Polite-pool already works for typical Phase 0 load. | Apply at openalex.org if you exceed polite limits. |

5. **Verify** (from the SAME shell/venv you will launch phases from): `python3 "$SKILL_DIR/scripts/run.py" check_connectors` — should show ✅ for all 4 connectors AND the two full-text fetch deps (`pymupdf`, `beautifulsoup4`). If you verify in one shell but run phases in another, the package set can differ — keep it one shell.

6. **The orchestrator auto-loads `.env`** at runtime (walks up from skill dir to find `.env`), so you do NOT need to `source .env` in your shell. Shell-set env vars take precedence over `.env` values, so you can override on the fly.

7. **Optional — standing compute profile**: if your real budget differs from the factory default (80GB-class GPUs, ≤8 concurrent, ≈150 GPU-days / 5 months, ~$10k API campaign), add one line to `.env` instead of re-typing it per run: `IDEASPARK_DEFAULT_COMPUTE="8×H100 node, ~300 GPU-days, $50k API budget"`. Precedence: compute stated in your query > this profile > factory default.

If a connector shows ❌, it's either missing creds (fix in `.env`) or missing the pip package (the error message tells you which `pip install` to run). If a full-text dep shows ⚠️, run `pip install feedparser openreview-py beautifulsoup4 pymupdf`.
