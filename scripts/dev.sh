#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python scripts/check-local-auth.py --port "${PORT:-8000}"
exec uvicorn main:app --reload --port "${PORT:-8000}"
