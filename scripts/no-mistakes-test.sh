#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

USER_SOCRATINK_BASE_URL="${SOCRATINK_BASE_URL:-}"
USER_APP_BASE_URL="${APP_BASE_URL:-}"

bash scripts/bootstrap-python.sh
source scripts/no-mistakes-env.sh

if [ -z "$USER_SOCRATINK_BASE_URL" ] && [ -z "$USER_APP_BASE_URL" ]; then
  NO_MISTAKES_PORT="$(
    .venv/bin/python - <<'PY'
import socket

with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    print(s.getsockname()[1])
PY
  )"
  export SOCRATINK_BASE_URL="http://127.0.0.1:${NO_MISTAKES_PORT}"
  export APP_BASE_URL="$SOCRATINK_BASE_URL"
fi

npm ci
.venv/bin/playwright install chromium

if [ -z "${COMPARE_BRANCH:-}" ] && git rev-parse --verify --quiet origin/dev >/dev/null; then
  export COMPARE_BRANCH="origin/dev"
fi

bash scripts/check-coverage.sh
