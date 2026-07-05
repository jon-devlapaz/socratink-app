#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

LOCAL_SERVER_PID=""
CLEANUP_INTENT_TO_ADD=0

cleanup() {
    if [ "$CLEANUP_INTENT_TO_ADD" = "1" ] && [ -n "${UNTRACKED_FILES:-}" ]; then
        printf '%s\n' "$UNTRACKED_FILES" | xargs -I{} git reset --quiet -- "{}" 2>/dev/null || true
    fi
    if [ -n "$LOCAL_SERVER_PID" ]; then
        kill "$LOCAL_SERVER_PID" 2>/dev/null || true
        wait "$LOCAL_SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

wait_for_health() {
    local health_url="$1"
    .venv/bin/python - "$health_url" <<'PY'
import sys
import time
import urllib.request

health_url = sys.argv[1]
deadline = time.time() + 30
last_error = None
while time.time() < deadline:
    try:
        with urllib.request.urlopen(health_url, timeout=2) as response:
            if response.status == 200:
                raise SystemExit(0)
    except Exception as exc:  # noqa: BLE001 - shell diagnostic path
        last_error = exc
        time.sleep(1)
raise SystemExit(f"local app did not become healthy: {last_error}")
PY
}

ensure_local_server() {
    local base_url="${SOCRATINK_BASE_URL:-http://localhost:8000}"
    local local_port
    local_port=$(.venv/bin/python - "$base_url" <<'PY'
import sys
from urllib.parse import urlparse

parsed = urlparse(sys.argv[1])
if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
    raise SystemExit(1)
print(parsed.port or 80)
PY
    ) || return 0

    local health_url="${base_url%/}/api/health"
    if .venv/bin/python - "$health_url" <<'PY'
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=2) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1)
PY
    then
        return 0
    fi

    if [ ! -x ".venv/bin/uvicorn" ]; then
        echo "check-coverage.sh: local app is not reachable and .venv/bin/uvicorn is missing." >&2
        echo "  Run: bash scripts/bootstrap-python.sh" >&2
        exit 1
    fi

    echo "Starting local app for browser coverage at $base_url..."
    mkdir -p .qa-runs
    local loop_store=".qa-runs/check-coverage-loop-sessions"
    rm -rf "$loop_store"
    mkdir -p "$loop_store"
    SOCRATINK_DEV_AUTOGUEST="${SOCRATINK_DEV_AUTOGUEST:-1}" \
    SOCRATINK_E2E_LOCAL_GUEST="${SOCRATINK_E2E_LOCAL_GUEST:-1}" \
    SOCRATINK_TUI_FAKE_LLM="${SOCRATINK_TUI_FAKE_LLM:-1}" \
    SOCRATINK_LOOP_SESSION_STORE_DIR="${SOCRATINK_LOOP_SESSION_STORE_DIR:-$PWD/$loop_store}" \
    PYTHON="${PYTHON:-$PWD/.venv/bin/python}" \
    .venv/bin/uvicorn main:app --host 127.0.0.1 --port "$local_port" >.qa-runs/check-coverage-uvicorn.log 2>&1 &
    LOCAL_SERVER_PID="$!"
    wait_for_health "$health_url"
}

DIFF_COVER_BIN="${DIFF_COVER_BIN:-.venv/bin/diff-cover}"
if [ ! -x "$DIFF_COVER_BIN" ]; then
    DIFF_COVER_BIN="diff-cover"
fi

echo "Registering untracked files in git index for diff-cover..."
UNTRACKED_FILES=$(git ls-files --others --exclude-standard)
if [ -n "$UNTRACKED_FILES" ]; then
    # shellcheck disable=SC2086
    printf '%s\n' "$UNTRACKED_FILES" | xargs -I{} git add -N -- "{}"
    CLEANUP_INTENT_TO_ADD=1
fi

echo "Clearing old V8 coverage data..."
rm -rf .qa-runs/v8-coverage .qa-runs/coverage-reports

ensure_local_server

echo "Generating backend and raw V8 coverage..."
SOCRATINK_E2E_LOCAL_GUEST="${SOCRATINK_E2E_LOCAL_GUEST:-1}" ./scripts/test-cov.sh --quiet

echo "Generating frontend coverage report..."
node scripts/generate-frontend-coverage.js

echo "Running diff-cover on full stack..."
resolve_compare_branch() {
    if [ -n "${COMPARE_BRANCH:-}" ]; then
        if git rev-parse --verify --quiet "$COMPARE_BRANCH" >/dev/null; then
            echo "$COMPARE_BRANCH"
            return 0
        fi
        echo "check-coverage.sh: COMPARE_BRANCH is not a valid git ref: $COMPARE_BRANCH" >&2
        return 1
    fi

    for candidate in origin/main main; do
        [ -z "$candidate" ] && continue
        if git rev-parse --verify --quiet "$candidate" >/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}
RESOLVED_COMPARE_BRANCH=$(resolve_compare_branch) || {
    echo "check-coverage.sh: no valid compare branch (tried COMPARE_BRANCH, origin/main, main)" >&2
    exit 1
}
echo "Checking frontend cache-bust pins..."
.venv/bin/python scripts/check_frontend_cache_pins.py "$RESOLVED_COMPARE_BRANCH"
"$DIFF_COVER_BIN" coverage.xml .qa-runs/coverage-reports/cobertura-coverage.xml --compare-branch="$RESOLVED_COMPARE_BRANCH" --fail-under=100
