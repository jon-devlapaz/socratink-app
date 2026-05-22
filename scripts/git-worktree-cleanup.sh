#!/usr/bin/env bash
# List and safely remove stale git worktrees.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/git-worktree-cleanup.sh
  scripts/git-worktree-cleanup.sh --json
  scripts/git-worktree-cleanup.sh --remove <worktree-path> --apply
  scripts/git-worktree-cleanup.sh --remove-clean --apply

Default mode is read-only. Removal mode refuses the current worktree, the main
worktree, dirty worktrees, and paths that are not registered git worktrees.
EOF
}

fail() {
  echo "[git-worktree-cleanup] ERROR: $*" >&2
  exit 2
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || fail "not inside a git repository"
main_worktree="$(git worktree list --porcelain | awk '/^worktree /{sub(/^worktree /, ""); print; exit}')"

remove_path=""
remove_clean="0"
apply="0"
json_mode="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --json)
      json_mode="1"
      shift
      ;;
    --remove)
      [ "$#" -ge 2 ] || fail "--remove requires a worktree path"
      remove_path="$2"
      shift 2
      ;;
    --remove-clean)
      remove_clean="1"
      shift
      ;;
    --apply)
      apply="1"
      shift
      ;;
    *)
      usage >&2
      fail "unknown argument: $1"
      ;;
  esac
done

[ -z "$remove_path" ] || [ "$remove_clean" = "0" ] || fail "--remove and --remove-clean cannot be combined"
[ "$json_mode" = "0" ] || { [ -z "$remove_path" ] && [ "$remove_clean" = "0" ]; } || fail "--json is only supported in list mode"

canonical_path() {
  local path="$1"
  if [ ! -d "$path" ]; then
    return 1
  fi
  (cd "$path" && pwd -P)
}

is_clean_worktree() {
  local path="$1"
  git -C "$path" diff --quiet --ignore-submodules -- \
    && git -C "$path" diff --cached --quiet --ignore-submodules -- \
    && [ -z "$(git -C "$path" ls-files --others --exclude-standard)" ]
}

has_branch_head() {
  local path="$1"
  git -C "$path" symbolic-ref --quiet --short HEAD >/dev/null
}

collect_clean_removable_worktrees() {
  local repo_root_canonical main_canonical wt wt_canonical
  repo_root_canonical="$(canonical_path "$repo_root")"
  main_canonical="$(canonical_path "$main_worktree")"

  while IFS= read -r line; do
    case "$line" in
      worktree\ *)
        wt="${line#worktree }"
        [ -d "$wt" ] || continue
        wt_canonical="$(canonical_path "$wt")" || continue
        [ "$wt_canonical" != "$repo_root_canonical" ] || continue
        [ "$wt_canonical" != "$main_canonical" ] || continue
        has_branch_head "$wt_canonical" || continue
        if is_clean_worktree "$wt_canonical"; then
          printf '%s\n' "$wt_canonical"
        fi
        ;;
    esac
  done < <(git worktree list --porcelain)
}

print_list() {
  echo "[git-worktree-cleanup] registered worktrees:"
  current_wt=""
  current_head=""
  current_branch=""

  print_entry() {
    [ -n "$current_wt" ] || return 0
    local display_branch="detached"
    local marker=" "
    local short_head="${current_head:0:7}"
    local status="candidate"
    if [ -n "$current_branch" ]; then
      display_branch="${current_branch#refs/heads/}"
    fi
    if [ "$current_wt" = "$repo_root" ]; then
      marker="*"
      status="current"
    elif [ "$current_wt" = "$main_worktree" ]; then
      marker="M"
      status="main"
    elif [ -z "$current_branch" ]; then
      status="detached-blocked"
    elif [ -d "$current_wt" ]; then
      if is_clean_worktree "$current_wt"; then
        status="clean-removable"
      else
        status="dirty-blocked"
      fi
    else
      status="missing-prunable"
    fi
    printf '  %s %-34s %-8s %-17s %s\n' "$marker" "$display_branch" "$short_head" "$status" "$current_wt"
  }

  while IFS= read -r line; do
    if [ -z "$line" ]; then
      print_entry
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
  print_entry

  echo
  echo "Legend:"
  echo "  * current worktree; never removed by this helper"
  echo "  M main worktree; never removed by this helper"
  echo "  clean-removable: can be removed with --remove <path> --apply"
  echo "  all clean-removable: can be removed with --remove-clean --apply"
  echo "  detached-blocked: detached HEAD; create or move a branch before removal"
  echo "  dirty-blocked: has staged, unstaged, or untracked files"
  echo "  missing-prunable: path is gone; run git worktree prune manually if needed"
}

print_list_json() {
  python3 - "$repo_root" "$main_worktree" <<'PY'
import json
import subprocess
import sys
from pathlib import Path


repo_root = Path(sys.argv[1]).resolve()
main_worktree = Path(sys.argv[2]).resolve()


def git(args, cwd=repo_root, check=True):
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"git {' '.join(args)} failed: {message}")
    return result.stdout.strip()


def is_clean(path: Path) -> bool:
    return (
        subprocess.run(["git", "-C", str(path), "diff", "--quiet", "--ignore-submodules", "--"], check=False).returncode == 0
        and subprocess.run(["git", "-C", str(path), "diff", "--cached", "--quiet", "--ignore-submodules", "--"], check=False).returncode == 0
        and not git(["ls-files", "--others", "--exclude-standard"], cwd=path, check=False)
    )


def has_branch_head(path: Path) -> bool:
    return subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--quiet", "--short", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    ).returncode == 0


worktrees = []
current = {}
for line in git(["worktree", "list", "--porcelain"]).splitlines() + [""]:
    if not line:
        if current:
            raw_path = current.get("path", "")
            path = Path(raw_path)
            exists = path.is_dir()
            resolved = path.resolve() if exists else path
            branch_ref = current.get("branch", "")
            branch = branch_ref.removeprefix("refs/heads/") if branch_ref else "detached"
            if resolved == repo_root:
                status = "current"
            elif resolved == main_worktree:
                status = "main"
            elif not branch_ref:
                status = "detached-blocked"
            elif exists and has_branch_head(resolved):
                status = "clean-removable" if is_clean(resolved) else "dirty-blocked"
            else:
                status = "missing-prunable"
            worktrees.append(
                {
                    "path": str(resolved),
                    "branch": branch,
                    "head": current.get("head", ""),
                    "status": status,
                    "exists": exists,
                    "current": resolved == repo_root,
                    "main": resolved == main_worktree,
                }
            )
        current = {}
        continue
    if line.startswith("worktree "):
        current["path"] = line.removeprefix("worktree ")
    elif line.startswith("HEAD "):
        current["head"] = line.removeprefix("HEAD ")
    elif line.startswith("branch "):
        current["branch"] = line.removeprefix("branch ")

payload = {
    "schema_version": 1,
    "repo": str(repo_root),
    "main_worktree": str(main_worktree),
    "worktrees": worktrees,
}
print(json.dumps(payload, sort_keys=True))
PY
}

if [ "$remove_clean" = "1" ]; then
  [ "$apply" = "1" ] || fail "bulk removal requires --apply"
  clean_worktrees=()
  while IFS= read -r target; do
    clean_worktrees+=("$target")
  done < <(collect_clean_removable_worktrees)
  if [ "${#clean_worktrees[@]}" -eq 0 ]; then
    echo "[git-worktree-cleanup] no clean-removable worktrees found"
    exit 0
  fi
  echo "[git-worktree-cleanup] removing ${#clean_worktrees[@]} clean-removable worktree(s)"
  for target in "${clean_worktrees[@]}"; do
    echo "[git-worktree-cleanup] removing $target"
    git worktree remove "$target"
  done
  echo "[git-worktree-cleanup] removed ${#clean_worktrees[@]} worktree(s)"
  exit 0
fi

if [ -z "$remove_path" ]; then
  if [ "$json_mode" = "1" ]; then
    print_list_json
    exit 0
  fi
  print_list
  exit 0
fi

[ "$apply" = "1" ] || fail "removal requires --apply"

target="$(canonical_path "$remove_path")" || fail "path does not exist: $remove_path"
repo_root_canonical="$(canonical_path "$repo_root")"
main_canonical="$(canonical_path "$main_worktree")"

[ "$target" != "$repo_root_canonical" ] || fail "refusing to remove current worktree"
[ "$target" != "$main_canonical" ] || fail "refusing to remove main worktree"

registered="0"
while IFS= read -r line; do
  case "$line" in
    worktree\ *)
      wt="${line#worktree }"
      if [ -d "$wt" ] && [ "$(canonical_path "$wt")" = "$target" ]; then
        registered="1"
      fi
      ;;
  esac
done < <(git worktree list --porcelain)

[ "$registered" = "1" ] || fail "path is not a registered worktree: $remove_path"
has_branch_head "$target" || fail "refusing to remove detached HEAD worktree; create or move a branch first"

dirty_status="$(git -C "$target" status --porcelain)"
if [ -n "$dirty_status" ]; then
  echo "[git-worktree-cleanup] refusing dirty worktree:"
  printf '%s\n' "$dirty_status"
  fail "commit, move, or remove that work before deleting this worktree"
fi

echo "[git-worktree-cleanup] removing $target"
git worktree remove "$target"
echo "[git-worktree-cleanup] removed"
