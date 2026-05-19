#!/usr/bin/env bash
# Safely fold local dev onto the daemon-published no-mistakes output.
#
# This script is intentionally narrow: it does not publish work. It only runs
# after no-mistakes has finished and origin/dev is the source of truth.

set -euo pipefail

fail() {
  echo "[no-mistakes-finish-dev] ERROR: $*" >&2
  exit 2
}

info() {
  echo "[no-mistakes-finish-dev] $*"
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || fail "not inside a git repository"
cd "$repo_root"

branch="$(git symbolic-ref --short HEAD 2>/dev/null)" || fail "detached HEAD; switch to dev first"
if [ "$branch" != "dev" ]; then
  fail "current branch is $branch, expected dev"
fi

if ! status_output="$(no-mistakes status 2>&1)"; then
  printf '%s\n' "$status_output" >&2
  fail "could not read no-mistakes status"
fi

if printf '%s\n' "$status_output" | grep -q "Active run"; then
  printf '%s\n' "$status_output"
  info "no-mistakes is still running; attach to finish the gate:"
  echo "  no-mistakes attach"
  exit 2
fi

dirty_status="$(git status --porcelain)"
if [ -n "$dirty_status" ]; then
  info "working tree is not clean; refusing to reset"
  printf '%s\n' "$dirty_status"
  info "commit, remove, or move these files before finishing the gate."
  exit 2
fi

info "fetching daemon output from origin/dev"
git fetch origin +refs/heads/dev:refs/remotes/origin/dev

counts="$(git rev-list --left-right --count origin/dev...HEAD)"
behind="${counts%%[[:space:]]*}"
ahead="${counts##*[[:space:]]}"

info "divergence origin/dev...HEAD: behind=$behind ahead=$ahead"

if [ "$behind" = "0" ] && [ "$ahead" = "0" ]; then
  info "already folded; local dev matches origin/dev"
  exit 0
fi

if [ "$behind" = "0" ]; then
  fail "local dev has $ahead commit(s) not on origin/dev; wait for no-mistakes or publish through the gate first"
fi

if [ "$ahead" != "0" ]; then
  unique_local="$(git cherry origin/dev HEAD | awk '$1 == "+" { print }')"
  if [ -n "$unique_local" ]; then
    info "local dev contains unique commits that are not folded into origin/dev:"
    printf '%s\n' "$unique_local"
    fail "refusing to discard unique local work"
  fi
  info "local commits are patch-equivalent to daemon output; reset is safe"
fi

info "resetting local dev to origin/dev"
git reset --hard origin/dev

verify_counts="$(git rev-list --left-right --count origin/dev...HEAD)"
if [ "$verify_counts" != "0	0" ] && [ "$verify_counts" != "0 0" ]; then
  fail "post-reset verification failed: $verify_counts"
fi

info "done; local dev is folded onto origin/dev"
