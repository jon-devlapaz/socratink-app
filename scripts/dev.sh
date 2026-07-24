#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -x ".venv/bin/python" ]; then
  echo "[dev] ERROR: .venv is missing. Run: bash scripts/bootstrap-python.sh" >&2
  exit 1
fi

PYTHON_BIN=".venv/bin/python"
UVICORN_BIN=".venv/bin/uvicorn"
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

export APP_BASE_URL="${APP_BASE_URL:-http://localhost:${PORT}}"

# Local-only: skip the /login wall by auto-minting a guest session on the
# first protected GET. Hard-gated in main.py against Vercel/CI runtime env
# markers, so this stays inert in any non-local environment.
if [ "${SOCRATINK_PREVIEW_LOGIN:-0}" = "1" ]; then
  export SOCRATINK_DEV_AUTOGUEST="${SOCRATINK_DEV_AUTOGUEST:-0}"
  export SOCRATINK_LOCAL_AUTH_BYPASS="${SOCRATINK_LOCAL_AUTH_BYPASS:-0}"
  export SOCRATINK_E2E_LOCAL_GUEST="${SOCRATINK_E2E_LOCAL_GUEST:-0}"
  echo "[dev] login preview: http://localhost:${PORT}/login"
else
  export SOCRATINK_DEV_AUTOGUEST="${SOCRATINK_DEV_AUTOGUEST:-1}"
  export SOCRATINK_E2E_LOCAL_GUEST="${SOCRATINK_E2E_LOCAL_GUEST:-1}"
fi

"$PYTHON_BIN" scripts/check-local-auth.py --port "$PORT"
exec "$UVICORN_BIN" main:app --reload --host "$HOST" --port "$PORT"
