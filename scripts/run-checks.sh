#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$repo_root"

echo "Running Codex setup verification..."
python3 scripts/verify_codex_setup.py

echo "Running Codex fresh-session smoke test..."
python3 scripts/smoke_test_codex_context.py
