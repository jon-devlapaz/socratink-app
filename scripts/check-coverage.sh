#!/usr/bin/env bash
set -e

echo "Registering untracked files in git index for diff-cover..."
UNTRACKED_FILES=$(git ls-files --others --exclude-standard)
if [ -n "$UNTRACKED_FILES" ]; then
    # shellcheck disable=SC2086
    printf '%s\n' "$UNTRACKED_FILES" | xargs -I{} git add -N -- "{}"
    cleanup_intent_to_add() {
        printf '%s\n' "$UNTRACKED_FILES" | xargs -I{} git reset --quiet -- "{}" 2>/dev/null || true
    }
    trap cleanup_intent_to_add EXIT
fi

echo "Clearing old V8 coverage data..."
rm -rf .qa-runs/v8-coverage .qa-runs/coverage-reports

echo "Generating backend and raw V8 coverage..."
SOCRATINK_E2E_LOCAL_GUEST="${SOCRATINK_E2E_LOCAL_GUEST:-1}" ./scripts/test-cov.sh --quiet

echo "Generating frontend coverage report..."
node scripts/generate-frontend-coverage.js

echo "Running diff-cover on full stack..."
# We compare against the main branch, prioritizing origin/main with a fallback.
# This ensures it works locally and in CI/agent worktrees.
resolve_compare_branch() {
    for candidate in "$COMPARE_BRANCH" origin/main main HEAD; do
        [ -z "$candidate" ] && continue
        if git rev-parse --verify --quiet "$candidate" >/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}
RESOLVED_COMPARE_BRANCH=$(resolve_compare_branch) || {
    echo "check-coverage.sh: no valid compare branch (tried COMPARE_BRANCH, origin/main, main, HEAD)" >&2
    exit 1
}
diff-cover coverage.xml .qa-runs/coverage-reports/cobertura-coverage.xml --compare-branch="$RESOLVED_COMPARE_BRANCH" --fail-under=100
