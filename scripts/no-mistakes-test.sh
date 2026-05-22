#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

bash scripts/bootstrap-python.sh
source scripts/no-mistakes-env.sh

npm ci
.venv/bin/playwright install chromium

if [ -z "${COMPARE_BRANCH:-}" ] && git rev-parse --verify --quiet origin/dev >/dev/null; then
  export COMPARE_BRANCH="origin/dev"
fi

bash scripts/check-coverage.sh
