#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VERCEL_CLI_VERSION="${VERCEL_CLI_VERSION:-51.6.1}"

cleanup() {
  rm -f pyproject.toml uv.lock
}
trap cleanup EXIT

echo "[preflight-deploy] repo: $REPO_ROOT"
echo "[preflight-deploy] Vercel CLI: $VERCEL_CLI_VERSION"

bash scripts/doctor.sh

cleanup
npx --yes "vercel@${VERCEL_CLI_VERSION}" build --yes

echo "[preflight-deploy] OK"
