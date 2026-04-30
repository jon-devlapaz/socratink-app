#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PORT="${PORT:-8000}"

echo "[doctor] repo: $REPO_ROOT"
echo "[doctor] port: $PORT"

echo "[doctor] Vercel requirements surface..."
python scripts/check-vercel-requirements.py

if [ ! -x ".venv/bin/python" ]; then
  echo "[doctor] FAIL: missing .venv. Run: bash scripts/bootstrap-python.sh" >&2
  exit 1
fi

echo "[doctor] python: $(.venv/bin/python -c 'import sys; print(sys.executable)')"
echo "[doctor] version: $(.venv/bin/python -V)"

echo "[doctor] lock install (no-op if already satisfied)..."
.venv/bin/pip install --require-hashes -r requirements.lock -q
.venv/bin/pip install --require-hashes -r requirements-dev.lock -q

echo "[doctor] auth/env preflight..."
.venv/bin/python scripts/check-local-auth.py --port "$PORT"

echo "[doctor] uvicorn entrypoint present..."
.venv/bin/python -c "import uvicorn, fastapi; import main"

echo "[doctor] OK"
