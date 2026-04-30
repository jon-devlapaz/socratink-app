#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PORT="${PORT:-8000}"

echo "[doctor] repo: $REPO_ROOT"
echo "[doctor] port: $PORT"

echo "[doctor] required agent/deploy files..."
required_files=(
  "AGENTS.md"
  "docs/project/state.md"
  "docs/codex/onboarding.md"
  "docs/codex/session-bootstrap.md"
  "docs/codex/agent-quality.md"
  "docs/product/evidence-weighted-map.md"
  "docs/product/spec.md"
  "requirements.txt"
  "requirements-dev.txt"
  "vercel.json"
)
for required_file in "${required_files[@]}"; do
  if [ ! -f "$required_file" ]; then
    echo "[doctor] FAIL: missing $required_file" >&2
    exit 1
  fi
done

if [ ! -x ".venv/bin/python" ]; then
  echo "[doctor] FAIL: missing .venv. Run: bash scripts/bootstrap-python.sh" >&2
  exit 1
fi

echo "[doctor] python: $(.venv/bin/python -c 'import sys; print(sys.executable)')"
echo "[doctor] version: $(.venv/bin/python -V)"

echo "[doctor] dependency install (no-op if already satisfied)..."
.venv/bin/pip install -r requirements.txt -q
.venv/bin/pip install -r requirements-dev.txt -q

echo "[doctor] auth/env preflight..."
.venv/bin/python scripts/check-local-auth.py --port "$PORT"

echo "[doctor] uvicorn entrypoint present..."
.venv/bin/python -c "import uvicorn, fastapi; import main"

echo "[doctor] OK"
