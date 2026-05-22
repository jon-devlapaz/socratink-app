#!/usr/bin/env bash

resolve_no_mistakes_compare_ref() {
  if [ -n "${COMPARE_BRANCH:-}" ]; then
    if git rev-parse --verify --quiet "$COMPARE_BRANCH" >/dev/null; then
      printf '%s\n' "$COMPARE_BRANCH"
      return 0
    fi
    printf 'no-mistakes-lint.sh: COMPARE_BRANCH is not a valid git ref: %s\n' "$COMPARE_BRANCH" >&2
    return 1
  fi

  if git rev-parse --verify --quiet origin/dev >/dev/null; then
    printf '%s\n' "origin/dev"
    return 0
  fi

  printf 'no-mistakes-lint.sh: no valid compare ref (tried COMPARE_BRANCH, origin/dev)\n' >&2
  return 1
}

resolve_no_mistakes_diff_base() {
  local compare_ref
  compare_ref="$(resolve_no_mistakes_compare_ref)"
  git merge-base "$compare_ref" HEAD
}

run_no_mistakes_diff_check() {
  local diff_base="$1"
  git diff --check "$diff_base" HEAD
}

main() {
  set -euo pipefail

  local repo_root
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  cd "$repo_root"

  bash scripts/bootstrap-python.sh
  source scripts/no-mistakes-env.sh

  bash scripts/doctor.sh

  local diff_base
  diff_base="$(resolve_no_mistakes_diff_base)"
  run_no_mistakes_diff_check "$diff_base"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
