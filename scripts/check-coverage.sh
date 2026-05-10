#!/usr/bin/env bash
set -e

echo "Registering untracked files in git index for diff-cover..."
git add -N .

echo "Clearing old V8 coverage data..."
rm -rf .qa-runs/v8-coverage .qa-runs/coverage-reports

echo "Generating backend and raw V8 coverage..."
./scripts/test-cov.sh --quiet

echo "Generating frontend coverage report..."
node scripts/generate-frontend-coverage.js

echo "Running diff-cover on full stack..."
# We compare against the main branch, prioritizing origin/main with a fallback.
# This ensures it works locally and in CI/agent worktrees.
diff-cover coverage.xml .qa-runs/coverage-reports/cobertura-coverage.xml --compare-branch=${COMPARE_BRANCH:-origin/main} --fail-under=100
