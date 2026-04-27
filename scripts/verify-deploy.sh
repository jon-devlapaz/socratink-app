#!/usr/bin/env bash
# verify-deploy.sh — wait for Vercel to finish deploying a commit, then run
# the QA browser smoke against production.
#
# Usage:
#   bash scripts/verify-deploy.sh                      # uses origin/main HEAD
#   bash scripts/verify-deploy.sh <sha>                # uses given SHA
#   bash scripts/verify-deploy.sh HEAD                 # uses local HEAD
#
# Exit codes:
#   0  Deploy succeeded AND smoke passed
#   2  Vercel deploy reported failure/error before smoke ran
#   3  Timed out waiting for Vercel (default 5 min)
#   4  Vercel deployed successfully but smoke failed
#
# Designed to be invoked by humans, by Claude Code, or by Gemini CLI.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

REPO_SLUG="${SOCRATINK_REPO_SLUG:-jon-devlapaz/socratink-app}"
PROD_URL="${SOCRATINK_BASE_URL:-https://app.socratink.ai}"
MAX_WAIT_SEC="${VERIFY_DEPLOY_MAX_WAIT_SEC:-300}"
POLL_INTERVAL_SEC=10

# 1. Resolve target SHA
TARGET="${1:-}"
if [ -z "$TARGET" ] || [ "$TARGET" = "origin/main" ]; then
  git fetch origin --quiet
  SHA=$(git rev-parse origin/main)
elif [ "$TARGET" = "HEAD" ]; then
  SHA=$(git rev-parse HEAD)
else
  SHA="$TARGET"
fi
SHORT_SHA="${SHA:0:7}"

echo "[verify-deploy] repo:     $REPO_SLUG"
echo "[verify-deploy] target:   $SHORT_SHA ($SHA)"
echo "[verify-deploy] prod URL: $PROD_URL"
echo "[verify-deploy] max wait: ${MAX_WAIT_SEC}s"
echo

# 2. Poll Vercel deployment via GitHub Deployments API
elapsed=0
last_status=""
target_url=""
deployment_url=""

while [ $elapsed -lt $MAX_WAIT_SEC ]; do
  # `gh` is authenticated in-process; quiet on transient failures, retry next loop.
  deploy_json=$(gh api "/repos/$REPO_SLUG/deployments?sha=$SHA&environment=Production" 2>/dev/null || echo "[]")
  deploy_id=$(echo "$deploy_json" | jq -r '.[0].id // empty')

  if [ -n "$deploy_id" ]; then
    status_json=$(gh api "/repos/$REPO_SLUG/deployments/$deploy_id/statuses" 2>/dev/null || echo "[]")
    last_status=$(echo "$status_json" | jq -r '.[0].state // "queued"')
    target_url=$(echo "$status_json" | jq -r '.[0].target_url // ""')

    case "$last_status" in
      success)
        deployment_url="$target_url"
        echo "[verify-deploy] Vercel: success at $deployment_url"
        break
        ;;
      failure|error)
        echo "[verify-deploy] FAIL: Vercel deployment $last_status for $SHORT_SHA"
        [ -n "$target_url" ] && echo "[verify-deploy] inspect: $target_url"
        exit 2
        ;;
      *)
        # pending, in_progress, queued, inactive — keep waiting
        ;;
    esac
  fi

  printf "[verify-deploy] waiting... status=%s elapsed=%ds\n" \
    "${last_status:-no-deployment-yet}" "$elapsed"
  sleep $POLL_INTERVAL_SEC
  elapsed=$((elapsed + POLL_INTERVAL_SEC))
done

if [ "$last_status" != "success" ]; then
  echo "[verify-deploy] TIMEOUT after ${MAX_WAIT_SEC}s — last status: ${last_status:-none}"
  exit 3
fi

# 3. Run the smoke against production
echo
echo "[verify-deploy] deploy verified — running QA smoke"
echo "===================================================================="
if bash "$REPO_ROOT/scripts/qa-smoke.sh" "$PROD_URL"; then
  echo "===================================================================="
  echo "[verify-deploy] PASS: $SHORT_SHA deployed and smoke is green"
  exit 0
else
  smoke_exit=$?
  echo "===================================================================="
  echo "[verify-deploy] FAIL: $SHORT_SHA deployed but smoke is red (exit $smoke_exit)"
  echo "[verify-deploy] Vercel deployment: $deployment_url"
  exit 4
fi
