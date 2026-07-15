#!/usr/bin/env bash
# save_trace.sh — save a reviewer call trace per shared-references/review-tracing.md.
#
# Usage:
#   bash save_trace.sh --skill <name> --purpose <kebab-label> \
#     --model <resolved-model> [--effort <effort>] [--fallback-reason <why>] \
#     --status <ok|fallback_used|error> [--thread-id <id>] \
#     --prompt <full prompt> --response <full response>
#
# Writes .aris/traces/<skill>/<YYYY-MM-DD>_run<NN>/{run.meta.json,
# NNN-<purpose>.request.json, NNN-<purpose>.response.md, NNN-<purpose>.meta.json}
# and appends a summary event to .aris/meta/events.jsonl.
set -eu

SKILL="" PURPOSE="" MODEL="" EFFORT="" FALLBACK_REASON="" STATUS="ok" THREAD_ID="" PROMPT="" RESPONSE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --skill) SKILL="$2"; shift 2 ;;
        --purpose) PURPOSE="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --effort) EFFORT="$2"; shift 2 ;;
        --fallback-reason) FALLBACK_REASON="$2"; shift 2 ;;
        --status) STATUS="$2"; shift 2 ;;
        --thread-id) THREAD_ID="$2"; shift 2 ;;
        --prompt) PROMPT="$2"; shift 2 ;;
        --response) RESPONSE="$2"; shift 2 ;;
        *) echo "ERROR: unknown argument $1" >&2; exit 2 ;;
    esac
done
[ -n "$SKILL" ] && [ -n "$PURPOSE" ] || { echo "ERROR: --skill and --purpose are required" >&2; exit 2; }

DATE=$(date -u +%Y-%m-%d)
BASE=".aris/traces/$SKILL"
mkdir -p "$BASE"

# Resume today's latest run dir, or start a new one.
RUN_NN=1
for d in "$BASE/${DATE}_run"*/; do
    [ -d "$d" ] || continue
    n=${d##*_run}; n=${n%/}
    case "$n" in (*[!0-9]*) continue ;; esac
    [ "$n" -ge "$RUN_NN" ] && RUN_NN=$n
done
RUN_DIR=$(printf '%s/%s_run%02d' "$BASE" "$DATE" "$RUN_NN")
mkdir -p "$RUN_DIR"

# Next call number within the run.
CALL=1
for f in "$RUN_DIR"/[0-9][0-9][0-9]-*.request.json; do
    [ -f "$f" ] || continue
    n=$(basename "$f" | cut -c1-3 | sed 's/^0*//')
    [ "$n" -ge "$CALL" ] && CALL=$((n + 1))
done
PREFIX=$(printf '%03d-%s' "$CALL" "$PURPOSE")
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if [ ! -f "$RUN_DIR/run.meta.json" ]; then
    SKILL="$SKILL" NOW="$NOW" RUN_ID="$(basename "$RUN_DIR")" python3 - > "$RUN_DIR/run.meta.json" << 'PY'
import json, os
json.dump({"skill": os.environ["SKILL"], "run_id": os.environ["RUN_ID"],
           "started_at": os.environ["NOW"], "executor": os.environ.get("ARIS_EXECUTOR", "unknown"),
           "project_dir": os.getcwd()}, __import__("sys").stdout, indent=2)
PY
fi

CALL="$CALL" PURPOSE="$PURPOSE" NOW="$NOW" MODEL="$MODEL" EFFORT="$EFFORT" \
PROMPT="$PROMPT" python3 - > "$RUN_DIR/$PREFIX.request.json" << 'PY'
import json, os, sys
json.dump({"call_number": int(os.environ["CALL"]), "purpose": os.environ["PURPOSE"],
           "timestamp": os.environ["NOW"], "model": os.environ["MODEL"],
           "config": {"model_reasoning_effort": os.environ["EFFORT"]} if os.environ["EFFORT"] else {},
           "prompt": os.environ["PROMPT"]}, sys.stdout, indent=2)
PY

printf '%s\n' "$RESPONSE" > "$RUN_DIR/$PREFIX.response.md"

CALL="$CALL" PURPOSE="$PURPOSE" NOW="$NOW" MODEL="$MODEL" THREAD_ID="$THREAD_ID" \
STATUS="$STATUS" FALLBACK_REASON="$FALLBACK_REASON" python3 - > "$RUN_DIR/$PREFIX.meta.json" << 'PY'
import json, os, sys
meta = {"call_number": int(os.environ["CALL"]), "purpose": os.environ["PURPOSE"],
        "timestamp": os.environ["NOW"], "thread_id": os.environ["THREAD_ID"],
        "model": os.environ["MODEL"], "status": os.environ["STATUS"]}
if os.environ["FALLBACK_REASON"]:
    meta["fallback_reason"] = os.environ["FALLBACK_REASON"]
json.dump(meta, sys.stdout, indent=2)
PY

mkdir -p .aris/meta
SKILL="$SKILL" PURPOSE="$PURPOSE" THREAD_ID="$THREAD_ID" STATUS="$STATUS" \
RUN_DIR="$RUN_DIR" python3 - >> .aris/meta/events.jsonl << 'PY'
import json, os, sys
json.dump({"event": "review_trace", "skill": os.environ["SKILL"],
           "purpose": os.environ["PURPOSE"], "thread_id": os.environ["THREAD_ID"],
           "trace_path": os.environ["RUN_DIR"] + "/", "status": os.environ["STATUS"]}, sys.stdout)
sys.stdout.write("\n")
PY

echo "trace saved: $RUN_DIR/$PREFIX.*"
