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
  "agents/ONBOARDING.md"
  "agents/QUALITY.md"
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

echo "[doctor] git hook path..."
hook_path="$(git config --local --default '' core.hooksPath)"
if [ "$hook_path" != "scripts/git-hooks" ]; then
  echo "[doctor] FAIL: core.hooksPath is '$hook_path' (expected scripts/git-hooks)" >&2
  exit 1
fi

if [ ! -x "scripts/git-hooks/pre-push" ]; then
  echo "[doctor] FAIL: scripts/git-hooks/pre-push missing or not executable" >&2
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "[doctor] FAIL: missing .venv. Run: bash scripts/bootstrap-python.sh" >&2
  exit 1
fi

echo "[doctor] python: $(.venv/bin/python -c 'import sys; print(sys.executable)')"
echo "[doctor] version: $(.venv/bin/python -V)"

echo "[doctor] dependency install (no-op if already satisfied)..."
.venv/bin/pip install -r requirements.txt -q
.venv/bin/pip install -r requirements-dev.txt -q

echo "[doctor] pyrefly baseline (pyrefly.toml scope)..."
# Version pinned here (not requirements-dev.txt) so the gate is
# self-bootstrapping: any agent or CI run that lands here gets the exact
# version the gate was authored against, with no drift risk.
PYREFLY_VERSION="1.0.0"
if ! .venv/bin/pyrefly --version 2>/dev/null | grep -q "^pyrefly $PYREFLY_VERSION$"; then
  echo "[doctor] installing pyrefly==$PYREFLY_VERSION..."
  .venv/bin/pip install "pyrefly==$PYREFLY_VERSION" -q
fi
# `pyrefly check` (no positional arg) honors project-includes in pyrefly.toml.
# Passing `.` would override that scope — don't.
.venv/bin/pyrefly check >/dev/null

echo "[doctor] mypy baseline (mypy.ini scope)..."
.venv/bin/mypy . >/dev/null

echo "[doctor] auth/env preflight..."
.venv/bin/python scripts/check-local-auth.py --port "$PORT"

echo "[doctor] uvicorn entrypoint present..."
.venv/bin/python -c "import uvicorn, fastapi; import main"

echo "[doctor] OK"
