#!/usr/bin/env bash
# Compatibility no-op for the removed local AI reviewer.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/local-ai-review.sh check
  scripts/local-ai-review.sh staged
  scripts/local-ai-review.sh diff
  scripts/local-ai-review.sh publish-diff <base-ref>
  scripts/local-ai-review.sh wip
  scripts/local-ai-review.sh publish-preview
  scripts/local-ai-review.sh smoke-local
  scripts/local-ai-review.sh pytest -- <pytest command>

Local AI review has been disabled. This command remains so publication and
workflow wrappers do not fail when they ask for advisory review.
EOF
}

mode="${1:-}"
[ -n "$mode" ] || {
  usage >&2
  exit 2
}
shift || true

case "$mode" in
  --help|-h|help)
    usage
    ;;
  check|staged|diff|publish-diff|wip|publish-preview|smoke-local)
    echo "[local-ai-review] disabled; skipping advisory review."
    ;;
  pytest)
    [ "${1:-}" = "--" ] || {
      echo "[local-ai-review] ERROR: pytest mode requires: scripts/local-ai-review.sh pytest -- <pytest command>" >&2
      exit 2
    }
    echo "[local-ai-review] disabled; skipping advisory review."
    ;;
  *)
    usage >&2
    echo "[local-ai-review] ERROR: unknown mode: $mode" >&2
    exit 2
    ;;
esac
