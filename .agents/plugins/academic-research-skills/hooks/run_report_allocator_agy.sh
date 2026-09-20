#!/bin/sh
# ARS report allocator launcher for Antigravity CLI (agy).
# Reads AGY protojson payload on stdin, executes allocate_report_path.py --stdin-hook,
# and emits AGY decision JSON on stdout with graceful degradation.

PASS_THROUGH='{"decision":"allow"}'

emit_allow_and_exit() {
    printf '%s\n' "$PASS_THROUGH"
    exit 0
}

SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || emit_allow_and_exit
ALLOCATOR="$SELF_DIR/../scripts/allocate_report_path.py"

[ -f "$ALLOCATOR" ] || emit_allow_and_exit

PAYLOAD=$(cat)

find_python() {
    for cand in "python3" "python" "py -3"; do
        cmd=$(printf '%s' "$cand" | awk '{print $1}')
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
                printf '%s' "$cand"
                return 0
            fi
        fi
    done
    return 1
}

PY=$(find_python) || emit_allow_and_exit

ALLOC_OUT=$(printf '%s' "$PAYLOAD" | $PY "$ALLOCATOR" --stdin-hook 2>/dev/null)
ALLOC_STATUS=$?

is_valid_decision_json() {
    printf '%s' "$ALLOC_OUT" | $PY -c '
import sys, json
try:
    d = json.load(sys.stdin)
    sys.exit(0 if isinstance(d, dict) and "decision" in d else 1)
except Exception:
    sys.exit(1)
' >/dev/null 2>&1
}

if [ "$ALLOC_STATUS" -eq 0 ] && [ -n "$ALLOC_OUT" ] && is_valid_decision_json; then
    printf '%s\n' "$ALLOC_OUT"
    exit 0
fi

emit_allow_and_exit
