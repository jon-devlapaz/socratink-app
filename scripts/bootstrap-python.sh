#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

. ".venv/bin/activate"

python -m pip install --upgrade pip

# Always install from the pinned locks. This is the “one true path” for local reproducibility.
python -m pip install --require-hashes -r requirements.lock
python -m pip install --require-hashes -r requirements-dev.lock

echo "[bootstrap-python] OK"

