#!/usr/bin/env bash
# QA browser smoke — single-command runner for socratink-app.
#
# Usage:
#   bash scripts/qa-smoke.sh                     # local (http://localhost:8000)
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

# 1. Resolve target URL: 'local', 'live', or explicit URL.
INPUT="${1:-local}"

if [ "$INPUT" = "local" ]; then
    TARGET="http://localhost:8000"
elif [ "$INPUT" = "live" ]; then
    TARGET="https://app.socratink.ai"
else
    # Allow passing an explicit URL as a fallback
    TARGET="$INPUT"
fi

# Override with SOCRATINK_BASE_URL env var if it's set
TARGET="${SOCRATINK_BASE_URL:-$TARGET}"
export SOCRATINK_BASE_URL="$TARGET"

echo "[qa-smoke] target: $SOCRATINK_BASE_URL"

# 2. Verify deps. Install if missing (idempotent).
if ! python3 -c "import pytest_playwright" 2>/dev/null; then
  echo "[qa-smoke] installing dev deps..."
  pip install -r requirements-dev.txt
fi

if ! python3 -c "from playwright.sync_api import sync_playwright; sync_playwright().__enter__().chromium.launch().close()" 2>/dev/null; then
  echo "[qa-smoke] installing Chromium browser binary..."
  playwright install chromium
fi

# 3. Run the suite.
exec pytest tests/e2e/test_smoke.py -v --tb=short
