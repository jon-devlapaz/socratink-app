#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

CLEANUP_INTENT_TO_ADD=0

cleanup() {
    if [ "$CLEANUP_INTENT_TO_ADD" = "1" ] && [ -n "${UNTRACKED_FILES:-}" ]; then
        printf '%s\n' "$UNTRACKED_FILES" |
            xargs -I{} git reset --quiet -- "{}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

resolve_compare_branch() {
    if [ -n "${COMPARE_BRANCH:-}" ]; then
        if git rev-parse --verify --quiet "$COMPARE_BRANCH" >/dev/null; then
            echo "$COMPARE_BRANCH"
            return 0
        fi
        echo "check-coverage.sh: invalid COMPARE_BRANCH: $COMPARE_BRANCH" >&2
        return 1
    fi

    for candidate in origin/main main; do
        if git rev-parse --verify --quiet "$candidate" >/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

DIFF_COVER_BIN="${DIFF_COVER_BIN:-.venv/bin/diff-cover}"
if [ ! -x "$DIFF_COVER_BIN" ]; then
    DIFF_COVER_BIN="diff-cover"
fi

echo "Registering untracked files in git index for diff-cover..."
UNTRACKED_FILES=$(git ls-files --others --exclude-standard)
if [ -n "$UNTRACKED_FILES" ]; then
    printf '%s\n' "$UNTRACKED_FILES" | xargs -I{} git add -N -- "{}"
    CLEANUP_INTENT_TO_ADD=1
fi

echo "Generating application-logic coverage..."
./scripts/test-cov.sh --quiet

RESOLVED_COMPARE_BRANCH=$(resolve_compare_branch) || {
    echo "check-coverage.sh: no valid compare branch found" >&2
    exit 1
}

echo "Running diff-cover on application logic..."
"$DIFF_COVER_BIN" \
    coverage.xml \
    --compare-branch="$RESOLVED_COMPARE_BRANCH" \
    --fail-under=100
