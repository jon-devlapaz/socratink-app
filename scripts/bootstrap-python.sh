#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

. ".venv/bin/activate"

python -m pip install --upgrade pip

python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

echo "[bootstrap-python] OK"
