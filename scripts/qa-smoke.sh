#!/usr/bin/env bash
# QA browser smoke — single-command runner for socratink-app.
#
# Usage:
#   bash scripts/qa-smoke.sh                     # local (http://localhost:8000)
#   bash scripts/qa-smoke.sh local               # local (http://localhost:8000) — explicit form
#   bash scripts/qa-smoke.sh live                # live (https://app.socratink.ai)
#   bash scripts/qa-smoke.sh https://custom-url.com
#   SOCRATINK_BASE_URL=... bash scripts/qa-smoke.sh
#
# What it does:
#   1. Starts a local app when the loopback target is not already healthy.
#   2. Ensures pytest-playwright + chromium are available.
#   3. Runs tests/e2e/test_smoke.py against the target URL.
#   4. Exits 0 on pass, non-zero on fail (with verbose pytest output).
#
# Designed to be invoked by humans, by Claude Code, or by Gemini CLI.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LOCAL_SERVER_PID=""
LOCAL_LOOP_STORE=""

cleanup() {
  if [ -n "$LOCAL_SERVER_PID" ]; then
    kill "$LOCAL_SERVER_PID" 2>/dev/null || true
    wait "$LOCAL_SERVER_PID" 2>/dev/null || true
  fi
  if [ -n "$LOCAL_LOOP_STORE" ]; then
    rm -rf "$LOCAL_LOOP_STORE"
  fi
}
trap cleanup EXIT

if [ ! -x ".venv/bin/python" ]; then
  echo "[qa-smoke] ERROR: .venv is missing. Run: bash scripts/bootstrap-python.sh" >&2
  exit 1
fi

PYTHON_BIN=".venv/bin/python"
PYTEST_BIN=".venv/bin/pytest"
PLAYWRIGHT_BIN=".venv/bin/playwright"
UVICORN_BIN=".venv/bin/uvicorn"

# 1. Resolve target URL: positional arg > SOCRATINK_BASE_URL env var > local default.
if [ $# -ge 1 ]; then
    INPUT="$1"
    if [ "$INPUT" = "local" ]; then
        TARGET="http://localhost:8000"
    elif [ "$INPUT" = "live" ]; then
        TARGET="https://app.socratink.ai"
    else
        # Allow passing an explicit URL as a fallback
        TARGET="$INPUT"
    fi
fi

TARGET="${TARGET:-${SOCRATINK_BASE_URL:-http://localhost:8000}}"

export SOCRATINK_BASE_URL="$TARGET"

case "$TARGET" in
  http://localhost:*|http://localhost|http://127.0.0.1:*|http://127.0.0.1)
    export SOCRATINK_E2E_LOCAL_GUEST="${SOCRATINK_E2E_LOCAL_GUEST:-1}"
    ;;
esac

echo "[qa-smoke] target: $SOCRATINK_BASE_URL"

# 2. Verify deps. Install if missing (idempotent).
if ! "$PYTHON_BIN" -c "import pytest_playwright" 2>/dev/null; then
  echo "[qa-smoke] FAIL: pytest-playwright missing. Run: bash scripts/bootstrap-python.sh" >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c "from playwright.sync_api import sync_playwright; sync_playwright().__enter__().chromium.launch().close()" 2>/dev/null; then
  echo "[qa-smoke] installing Chromium browser binary..."
  "$PLAYWRIGHT_BIN" install chromium
fi

# 3. Start a missing loopback app; remote targets remain caller-owned.
LOCAL_PORT=$("$PYTHON_BIN" - "$TARGET" <<'PY' || true
import sys
from urllib.parse import urlparse

target = urlparse(sys.argv[1])
if target.scheme == "http" and target.hostname in {"localhost", "127.0.0.1"}:
    print(target.port or 80)
PY
)

if [ -n "$LOCAL_PORT" ]; then
  HEALTH_URL="${TARGET%/}/api/health"
  if ! "$PYTHON_BIN" - "$HEALTH_URL" <<'PY'
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=2) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1)
PY
  then
    if [ ! -x "$UVICORN_BIN" ]; then
      echo "[qa-smoke] ERROR: local app is unavailable and uvicorn is missing. Run: bash scripts/bootstrap-python.sh" >&2
      exit 1
    fi
    echo "[qa-smoke] starting local app at $TARGET"
    mkdir -p .qa-runs
    LOCAL_LOOP_STORE="$REPO_ROOT/.qa-runs/qa-smoke-loop-sessions-$$"
    mkdir -p "$LOCAL_LOOP_STORE"
    SOCRATINK_DEV_AUTOGUEST="${SOCRATINK_DEV_AUTOGUEST:-1}" \
    SOCRATINK_E2E_LOCAL_GUEST="${SOCRATINK_E2E_LOCAL_GUEST:-1}" \
    SOCRATINK_TUI_FAKE_LLM="${SOCRATINK_TUI_FAKE_LLM:-1}" \
    SOCRATINK_LOOP_SESSION_STORE_DIR="${SOCRATINK_LOOP_SESSION_STORE_DIR:-$LOCAL_LOOP_STORE}" \
    PYTHON="${PYTHON:-$REPO_ROOT/$PYTHON_BIN}" \
    "$REPO_ROOT/$UVICORN_BIN" main:app --host 127.0.0.1 --port "$LOCAL_PORT" \
      >.qa-runs/qa-smoke-uvicorn.log 2>&1 &
    LOCAL_SERVER_PID="$!"

    "$PYTHON_BIN" - "$HEALTH_URL" <<'PY'
import sys
import time
import urllib.request

deadline = time.time() + 30
last_error = None
while time.time() < deadline:
    try:
        with urllib.request.urlopen(sys.argv[1], timeout=2) as response:
            if response.status == 200:
                raise SystemExit(0)
    except Exception as exc:  # noqa: BLE001 - shell diagnostic path
        last_error = exc
        time.sleep(1)
raise SystemExit(f"local app did not become healthy: {last_error}")
PY
  fi
fi

# 4. Run the suite.
"$PYTEST_BIN" tests/e2e/test_smoke.py -v --tb=short
