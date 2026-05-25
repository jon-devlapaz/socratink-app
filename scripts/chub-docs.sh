#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHUB_BIN="$REPO_ROOT/node_modules/.bin/chub"
CHUB_REGISTRY="$REPO_ROOT/.agents/runtime/chub/sources/default/registry.json"

usage() {
  cat >&2 <<'USAGE'
Usage:
  bash scripts/chub-docs.sh update [--full|--force]
  bash scripts/chub-docs.sh cache status
  bash scripts/chub-docs.sh search <query> [--json] [--tags <csv>]
  bash scripts/chub-docs.sh get <id...> [--lang py|js|ts|rb|cs] [--full]

Context Hub output is external evidence only. Do not send secrets, private
source, customer data, or Socratink product doctrine into third-party lookups.
USAGE
}

if [ $# -eq 0 ]; then
  usage
  exit 2
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Error: Node.js is required to run the repo-pinned Context Hub CLI." >&2
  exit 1
fi

if [ ! -x "$CHUB_BIN" ]; then
  echo "Error: @aisuite/chub is not installed for this repo." >&2
  echo "Run: npm install" >&2
  exit 1
fi

case "$1" in
  update|search|get)
    ;;
  cache)
    if [ "${2:-}" != "status" ]; then
      echo "Error: only 'cache status' is supported by this wrapper." >&2
      usage
      exit 2
    fi
    ;;
  *)
    echo "Error: unsupported Context Hub command: $1" >&2
    usage
    exit 2
    ;;
esac

export CHUB_DIR="$REPO_ROOT/.agents/runtime/chub"
export CHUB_TELEMETRY=0
export CHUB_FEEDBACK=0

mkdir -p "$CHUB_DIR"

if [ "$1" = "search" ] || [ "$1" = "get" ]; then
  if [ ! -s "$CHUB_REGISTRY" ]; then
    echo "Error: Context Hub registry is not initialized for this repo." >&2
    echo "Run: bash scripts/chub-docs.sh update" >&2
    exit 1
  fi
fi

exec "$CHUB_BIN" "$@"
