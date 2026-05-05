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
#   1. Ensures pytest-playwright + chromium are available.
#   2. Runs tests/e2e/test_smoke.py against the target URL.
#   3. Exits 0 on pass, non-zero on fail (with verbose pytest output).
#
# Designed to be invoked by humans, by Claude Code, or by Gemini CLI.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -x ".venv/bin/python" ]; then
  echo "[qa-smoke] ERROR: .venv is missing. Run: bash scripts/bootstrap-python.sh" >&2
  exit 1
fi

PYTHON_BIN=".venv/bin/python"
PYTEST_BIN=".venv/bin/pytest"
PLAYWRIGHT_BIN=".venv/bin/playwright"

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

# 3. Run the suite.
exec "$PYTEST_BIN" tests/e2e/test_smoke.py -v --tb=short
