#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Wire git hooks (idempotent). Tracked hooks live under scripts/git-hooks/;
# pointing core.hooksPath there means hooks are versioned with the code,
# so worktrees + fresh clones get them automatically.
if [ -d ".git" ] || [ -f ".git" ]; then
  if [ "$(git config --local --default '' core.hooksPath)" != "scripts/git-hooks" ]; then
    git config --local core.hooksPath scripts/git-hooks
    echo "[bootstrap-python] configured core.hooksPath -> scripts/git-hooks"
  fi
  # Ensure the hooks themselves are executable (idempotent).
  chmod +x scripts/git-hooks/* 2>/dev/null || true
fi

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

. ".venv/bin/activate"

python -m pip install --upgrade pip

python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

echo "[bootstrap-python] OK"
