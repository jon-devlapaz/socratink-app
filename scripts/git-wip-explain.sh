#!/usr/bin/env bash
# Explain the current working-tree state without changing it.

set -euo pipefail

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  color_ok="$(printf '\033[32m')"
  color_warn="$(printf '\033[33m')"
  color_block="$(printf '\033[31m')"
  color_reset="$(printf '\033[0m')"
else
  color_ok=""
  color_warn=""
  color_block=""
  color_reset=""
fi

badge() {
  case "$1" in
    OK) printf '%s[OK]%s' "$color_ok" "$color_reset" ;;
    WARN) printf '%s[WARN]%s' "$color_warn" "$color_reset" ;;
    BLOCKED) printf '%s[BLOCKED]%s' "$color_block" "$color_reset" ;;
    *) printf '[%s]' "$1" ;;
  esac
}

usage() {
  cat <<'EOF'
Usage: scripts/git-wip-explain.sh [--short] [--help]

Read-only helper that explains staged, unstaged, and untracked work.
It does not add, remove, reset, stash, commit, fetch, or push.
EOF
}

short_mode="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --short)
      short_mode="1"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "[git-wip-explain] ERROR: not inside a git repository" >&2
  exit 2
}
cd "$repo_root"

branch="$(git symbolic-ref --short HEAD 2>/dev/null || echo "detached")"
upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
head_sha="$(git rev-parse --short HEAD)"
head_subject="$(git log -1 --pretty=%s)"
behind=0
ahead=0

if [ "$short_mode" != "1" ]; then
  echo "[git-wip-explain] repo:   $repo_root"
  echo "[git-wip-explain] branch: $branch"
  echo "[git-wip-explain] head:   $head_sha $head_subject"
fi

if [ -n "$upstream" ]; then
  counts="$(git rev-list --left-right --count "$upstream"...HEAD 2>/dev/null || true)"
  if [ -n "$counts" ]; then
    behind="${counts%%[[:space:]]*}"
    ahead="${counts##*[[:space:]]}"
    if [ "$short_mode" != "1" ]; then
      echo "[git-wip-explain] upstream: $upstream (behind=$behind ahead=$ahead)"
    fi
  else
    if [ "$short_mode" != "1" ]; then
      echo "[git-wip-explain] upstream: $upstream"
    fi
  fi
else
  if [ "$short_mode" != "1" ]; then
    echo "[git-wip-explain] upstream: none"
  fi
fi

print_commit_preview() {
  local title="$1"
  local range="$2"
  local count="$3"
  echo
  echo "$title ($count):"
  if [ "$count" -eq 0 ]; then
    echo "  none"
    return
  fi
  git log --oneline --decorate --max-count=8 "$range" | sed 's/^/  /'
  if [ "$count" -gt 8 ]; then
    echo "  ... $((count - 8)) more"
  fi
}

if [ "$short_mode" != "1" ] && [ -n "$upstream" ]; then
  print_commit_preview "Local commits not on $upstream" "$upstream..HEAD" "$ahead"
  print_commit_preview "Remote commits not in local HEAD" "HEAD..$upstream" "$behind"
fi

if [ "$short_mode" != "1" ]; then
  echo
  echo "Known worktrees:"
fi
current_wt=""
current_head=""
current_branch=""
same_branch_count=0

print_worktree_entry() {
  [ -n "$current_wt" ] || return 0
  local display_branch="detached"
  local marker=" "
  local short_head="${current_head:0:7}"
  if [ -n "$current_branch" ]; then
    display_branch="${current_branch#refs/heads/}"
  fi
  if [ "$current_wt" = "$repo_root" ]; then
    marker="*"
  elif [ "$branch" != "detached" ] && [ "$display_branch" = "$branch" ]; then
    same_branch_count=$((same_branch_count + 1))
    marker="!"
  fi
  if [ "$short_mode" != "1" ]; then
    printf '  %s %-34s %-8s %s\n' "$marker" "$display_branch" "$short_head" "$current_wt"
  fi
}

while IFS= read -r line; do
  if [ -z "$line" ]; then
    print_worktree_entry
    current_wt=""
    current_head=""
    current_branch=""
    continue
  fi
  case "$line" in
    worktree\ *) current_wt="${line#worktree }" ;;
    HEAD\ *) current_head="${line#HEAD }" ;;
    branch\ *) current_branch="${line#branch }" ;;
  esac
done < <(git worktree list --porcelain)
print_worktree_entry

if [ "$short_mode" != "1" ]; then
  echo "  * current worktree"
  echo "  ! another worktree on the same branch"
  if [ "$same_branch_count" -gt 0 ]; then
    echo "[git-wip-explain] WARNING: $same_branch_count other worktree(s) are on branch $branch."
  fi
fi

if [ "$short_mode" != "1" ]; then
  echo
  echo "Raw status:"
  git status --short --branch
fi

status_lines="$(git status --porcelain)"

staged_count=0
unstaged_count=0
untracked_count=0
staged_output=""
unstaged_output=""
untracked_output=""

while IFS= read -r line; do
  [ -n "$line" ] || continue
  x="${line:0:1}"
  y="${line:1:1}"
  path="${line:3}"

  if [ "$x$y" = "??" ]; then
    untracked_output="${untracked_output}  ${path}"$'\n'
    untracked_count=$((untracked_count + 1))
    continue
  fi
  if [ "$x" != " " ] && [ "$x" != "?" ]; then
    staged_output="${staged_output}  ${x} ${path}"$'\n'
    staged_count=$((staged_count + 1))
  fi
  if [ "$y" != " " ]; then
    unstaged_output="${unstaged_output}  ${y} ${path}"$'\n'
    unstaged_count=$((unstaged_count + 1))
  fi
done <<< "$status_lines"

dirty_count=$((staged_count + unstaged_count + untracked_count))

upstream_state="OK"
upstream_message="aligned with upstream"
if [ -z "$upstream" ]; then
  upstream_state="WARN"
  upstream_message="no upstream configured"
elif [ "${behind:-0}" -gt 0 ] && [ "${ahead:-0}" -gt 0 ]; then
  upstream_state="BLOCKED"
  upstream_message="diverged from $upstream; inspect before reset, merge, or push"
elif [ "${behind:-0}" -gt 0 ]; then
  upstream_state="WARN"
  upstream_message="$upstream has ${behind} commit(s) you do not have; finish/sync before new work"
elif [ "${ahead:-0}" -gt 0 ]; then
  upstream_state="WARN"
  upstream_message="local branch has ${ahead} unpublished commit(s); publish through no-mistakes before finishing"
fi

worktree_state="OK"
worktree_message="clean"
if [ "$dirty_count" -gt 0 ]; then
  worktree_state="BLOCKED"
  worktree_message="$dirty_count staged/unstaged/untracked item(s)"
fi

session_state="OK"
session_message="no same-branch sibling worktrees"
if [ "$same_branch_count" -gt 0 ]; then
  session_state="WARN"
  session_message="$same_branch_count same-branch sibling worktree(s)"
fi

finish_blocked="no"
finish_state="OK"
finish_message="safe to run when no-mistakes is finished"
if [ "$dirty_count" -gt 0 ]; then
  finish_blocked="yes"
  finish_state="BLOCKED"
  finish_message="dirty working tree; review/commit/move files first"
elif [ -n "$upstream" ] && [ "${ahead:-0}" -gt 0 ]; then
  finish_blocked="yes"
  finish_state="BLOCKED"
  finish_message="local commits are not on $upstream; publish or inspect before finishing"
elif [ -z "$upstream" ]; then
  finish_blocked="yes"
  finish_state="BLOCKED"
  finish_message="no upstream configured"
fi

recommended_next="none; ready for new work"
if [ "$dirty_count" -gt 0 ]; then
  recommended_next="git diff && git status --short"
elif [ -n "$upstream" ] && [ "$ahead" -gt 0 ] && [ "$behind" -gt 0 ]; then
  recommended_next="git fetch && git status --short --branch && git diff @{u}...HEAD"
elif [ -n "$upstream" ] && [ "$ahead" -gt 0 ]; then
  if [ "$branch" = "dev" ]; then
    recommended_next="python3 scripts/agent-push.py --target no-mistakes/dev"
  elif [[ "$branch" == feat/* ]]; then
    recommended_next="python3 scripts/agent-push.py --target origin/$branch"
  else
    recommended_next="git status --short --branch && git log --oneline @{u}..HEAD"
  fi
elif [ -n "$upstream" ] && [ "$behind" -gt 0 ]; then
  if [ "$branch" = "dev" ]; then
    recommended_next="scripts/no-mistakes-finish-dev.sh"
  else
    recommended_next="git fetch && git status --short --branch && git log --oneline HEAD..@{u}"
  fi
elif [ "$same_branch_count" -gt 0 ]; then
  recommended_next="scripts/git-worktree-cleanup.sh"
fi

if [ "$short_mode" = "1" ]; then
  printf '%s %s @ %s | worktree=%s | upstream=behind:%s ahead:%s | sessions=%s | finish=%s\n' \
    "$(badge "$upstream_state")" "$branch" "$head_sha" "$worktree_state" "$behind" "$ahead" "$session_state" "$finish_state"
  echo "Next: $recommended_next"
  exit 0
fi

echo
echo "Health summary:"
printf '  %s Worktree: %s\n' "$(badge "$worktree_state")" "$worktree_message"
printf '  %s Upstream: %s\n' "$(badge "$upstream_state")" "$upstream_message"
printf '  %s Sessions: %s\n' "$(badge "$session_state")" "$session_message"
printf '  %s Finish helper: %s\n' "$(badge "$finish_state")" "$finish_message"
echo "  Next: $recommended_next"

if [ "$dirty_count" -eq 0 ]; then
  echo
  echo "Working tree is clean."
  echo "Blocks no-mistakes finish helper: $finish_blocked"
  exit 0
fi

print_section() {
  local title="$1"
  local count="$2"
  local output="$3"
  echo
  echo "$title ($count):"
  if [ "$count" -eq 0 ]; then
    echo "  none"
    return
  fi
  printf '%s' "$output"
}

print_section "Staged for commit" "$staged_count" "$staged_output"
print_section "Unstaged changes" "$unstaged_count" "$unstaged_output"
print_section "Untracked files" "$untracked_count" "$untracked_output"

if ! git diff --quiet; then
  echo
  echo "Unstaged diffstat:"
  git diff --stat
fi

if ! git diff --cached --quiet; then
  echo
  echo "Staged diffstat:"
  git diff --cached --stat
fi

echo
echo "Blocks no-mistakes finish helper: $finish_blocked"
echo
echo "Recommended next command:"
echo "  $recommended_next"
echo
echo "Least-resistance next step:"
if [ "$unstaged_count" -gt 0 ] || [ "$untracked_count" -gt 0 ]; then
  echo "  Review unstaged/untracked work before any reset:"
  echo "    git diff"
  echo "    git status --short"
  echo "  Then either commit intended work, move local-only files out of the repo, or intentionally remove junk."
elif [ "$staged_count" -gt 0 ]; then
  echo "  Staged work exists. Commit it, or unstage it with:"
  echo "    git restore --staged <path>"
else
  echo "  No action needed."
fi
