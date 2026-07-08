#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

expected_version="$(cat .python-version 2>/dev/null | tr -d '[:space:]')"
if [ -z "$expected_version" ]; then
  echo "[bootstrap-python] ERROR: .python-version missing or empty" >&2
  exit 1
fi

version_matches() {
  actual="$1"
  expected="$2"
  case "$expected" in
    [0-9]*.[0-9]*.[0-9]*) [ "$actual" = "$expected" ] ;;
    [0-9]*.[0-9]*) [ "${actual%.*}" = "$expected" ] ;;
    *) [ "$actual" = "$expected" ] ;;
  esac
}

resolved_version="$(python -c 'import sys; print("{}.{}.{}".format(*sys.version_info[:3]))' 2>/dev/null || true)"
if ! version_matches "$resolved_version" "$expected_version"; then
  echo "[bootstrap-python] ERROR: 'python' resolves to $resolved_version, but .python-version pins $expected_version" >&2
  echo "[bootstrap-python] Hint: install pyenv + run 'pyenv install $expected_version', or ensure pyenv shims are on PATH" >&2
  exit 1
fi

if [ -x ".venv/bin/python" ]; then
  venv_version="$(.venv/bin/python -c 'import sys; print("{}.{}.{}".format(*sys.version_info[:3]))' 2>/dev/null || true)"
  if ! version_matches "$venv_version" "$expected_version"; then
    echo "[bootstrap-python] .venv has Python $venv_version, expected $expected_version — recreating" >&2
    rm -rf .venv
  fi
fi

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

. ".venv/bin/activate"

python -m pip install --upgrade pip

python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

echo "[bootstrap-python] OK"
