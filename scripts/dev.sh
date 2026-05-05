#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -x ".venv/bin/python" ]; then
  echo "[dev] ERROR: .venv is missing. Run: bash scripts/bootstrap-python.sh" >&2
  exit 1
fi

PYTHON_BIN=".venv/bin/python"
UVICORN_BIN=".venv/bin/uvicorn"

# Local-only: skip the /login wall by auto-minting a guest session on the
# first protected GET. Hard-gated in main.py against Vercel/CI runtime env
# markers, so this stays inert in any non-local environment.
export SOCRATINK_DEV_AUTOGUEST="${SOCRATINK_DEV_AUTOGUEST:-1}"

"$PYTHON_BIN" scripts/check-local-auth.py --port "${PORT:-8000}"
exec "$UVICORN_BIN" main:app --reload --port "${PORT:-8000}"
