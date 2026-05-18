#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTEST_BIN="${PYTEST_BIN:-.venv/bin/pytest}"
if [ ! -x "$PYTEST_BIN" ]; then
  PYTEST_BIN="pytest"
fi

# Run tests with coverage reporting.
exec "$PYTEST_BIN" --cov=api --cov=auth --cov=db --cov=llm --cov=models --cov=source_intake --cov-report=xml --cov-report=term-missing --cov-branch "$@"
