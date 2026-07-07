#!/usr/bin/env bash
# Read-only lane status: git, PR, worktree, and optional Herdr ownership.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/agent-lane-status.sh [--json] [repo-path]

Answers where the current Socratink agent lane is, what blocks it, and the next
professional move. Read-only: no fetch, push, checkout, branch, stash, or Herdr
mutation.
EOF
}

json_mode="0"
repo_arg="."

while [ "$#" -gt 0 ]; do
  case "$1" in
    --json)
      json_mode="1"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    -*)
      usage >&2
      exit 2
      ;;
    *)
      repo_arg="$1"
      shift
      ;;
  esac
done

repo_root="$(git -C "$repo_arg" rev-parse --show-toplevel 2>/dev/null)" || {
  echo "[agent-lane-status] ERROR: not inside a git repository: $repo_arg" >&2
  exit 2
}

export ALS_REPO_ROOT="$repo_root"
export ALS_JSON_MODE="$json_mode"

python3 - <<'PY'
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO = Path(os.environ["ALS_REPO_ROOT"]).resolve()
JSON_MODE = os.environ["ALS_JSON_MODE"] == "1"


def run(cmd, cwd=REPO, check=False, timeout=10):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"{' '.join(cmd)} failed: {detail}")
    return result


def git(args, cwd=REPO, check=False):
    return run(["git", *args], cwd=cwd, check=check)


def git_out(args, cwd=REPO):
    return git(args, cwd=cwd, check=True).stdout.strip()


def lines(text):
    return [line for line in text.splitlines() if line.strip()]


def parse_worktrees():
    worktrees = []
    current = {}
    raw = git_out(["worktree", "list", "--porcelain"])
    for line in raw.splitlines() + [""]:
        if not line:
            if current:
                raw_path = current.get("path", "")
                path = Path(raw_path)
                exists = path.is_dir()
                resolved = str(path.resolve()) if exists else raw_path
                branch_ref = current.get("branch", "")
                branch = branch_ref.removeprefix("refs/heads/") if branch_ref else "detached"
                status = git(["status", "--porcelain"], cwd=Path(resolved), check=False).stdout.strip() if exists else ""
                worktrees.append(
                    {
                        "path": resolved,
                        "branch": branch,
                        "head": current.get("head", ""),
                        "exists": exists,
                        "dirty": bool(status),
                        "current": Path(resolved) == REPO,
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
    return worktrees


def rev_counts(left, right):
    result = git(["rev-list", "--left-right", "--count", f"{left}...{right}"])
    if result.returncode != 0:
        return None
    left_count, right_count = result.stdout.strip().split()
    return {"left": int(left_count), "right": int(right_count)}


def current_branch():
    result = git(["symbolic-ref", "--quiet", "--short", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else "detached"


def check_summary(checks):
    if checks is None:
        return "unknown"
    if not checks:
        return "none"
    failed = 0
    pending = 0
    passed = 0
    for check in checks:
        status = check.get("status")
        conclusion = check.get("conclusion")
        if status != "COMPLETED":
            pending += 1
        elif conclusion in ("SUCCESS", "SKIPPED", "NEUTRAL"):
            passed += 1
        else:
            failed += 1
    if failed:
        return "failed"
    if pending:
        return "pending"
    if passed:
        return "green"
    return "none"


def github_status(branches):
    if not shutil.which("gh"):
        return {"available": False, "state": "unknown", "reason": "gh unavailable", "open_prs": [], "matching_pr": None}

    base_cmd = ["gh", "pr", "list", "--json", "number,state,isDraft,headRefName,url,statusCheckRollup,mergeStateStatus"]
    open_result = run([*base_cmd, "--state", "open", "--limit", "100"], timeout=15)
    if open_result.returncode != 0:
        return {
            "available": True,
            "state": "unknown",
            "reason": (open_result.stderr.strip() or open_result.stdout.strip() or "gh pr list failed"),
            "open_prs": [],
            "matching_pr": None,
        }

    open_prs = json.loads(open_result.stdout or "[]")
    wanted = set(branches)
    pr = next((item for item in open_prs if item.get("headRefName") in wanted), None)
    if pr is None:
        for candidate in branches:
            all_result = run([*base_cmd, "--state", "all", "--head", candidate, "--limit", "10"], timeout=15)
            if all_result.returncode != 0:
                continue
            matching = json.loads(all_result.stdout or "[]")
            if matching:
                pr = matching[0]
                break
    if pr:
        pr["checks"] = check_summary(pr.get("statusCheckRollup"))
    return {"available": True, "state": "ok", "reason": "", "open_prs": open_prs, "matching_pr": pr}


def herdr_status(repo, branch):
    if os.environ.get("HERDR_ENV") != "1":
        return {"available": False, "state": "skipped", "reason": "HERDR_ENV not set", "duplicate_active_owner": False, "panes": []}
    if not shutil.which("herdr"):
        return {"available": False, "state": "unknown", "reason": "herdr unavailable", "duplicate_active_owner": False, "panes": []}

    attempts = [
        ["herdr", "panes", "--json"],
        ["herdr", "list", "--json"],
        ["herdr", "ps", "--json"],
        ["herdr", "list"],
    ]
    result = None
    for cmd in attempts:
        try:
            candidate = run(cmd, timeout=5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
        if candidate.returncode == 0 and candidate.stdout.strip():
            result = candidate
            break
    if result is None:
        return {"available": True, "state": "skipped", "reason": "herdr pane list unavailable", "duplicate_active_owner": False, "panes": []}

    text = result.stdout.strip()
    active_hits = []
    repo_terms = {str(repo), repo.name}
    for line in text.splitlines():
        low = line.lower()
        if branch in line and any(term in line for term in repo_terms) and any(word in low for word in ("active", "running", "busy")):
            active_hits.append(line)
    return {
        "available": True,
        "state": "ok",
        "reason": "",
        "duplicate_active_owner": len(active_hits) > 1,
        "panes": active_hits,
        "raw": text[:4000],
    }


branch = current_branch()
status_short = git_out(["status", "--short", "--branch"])
dirty_lines = lines(git_out(["status", "--porcelain"]))
dirty = bool(dirty_lines)
head = git_out(["rev-parse", "--short", "HEAD"])
head_subject = git_out(["log", "-1", "--pretty=%s"])
upstream = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"]).stdout.strip()
upstream_counts = rev_counts(upstream, "HEAD") if upstream else None
origin_counts = rev_counts("origin/main", "HEAD")
origin_exists = git(["rev-parse", "--verify", "--quiet", "origin/main"]).returncode == 0
worktrees = parse_worktrees()
local_branches = lines(git_out(["branch", "--format=%(refname:short)"]))
remote_branches = lines(git_out(["branch", "-r", "--format=%(refname:short)"]))
stashes = lines(git_out(["stash", "list"]))
github_branches = [branch]
github_branches.extend(
    wt["branch"] for wt in worktrees if wt["branch"] not in {branch, "main", "detached"}
)
github = github_status(github_branches)
herdr = herdr_status(REPO, branch)
dirty_worktrees = [wt for wt in worktrees if wt["dirty"]]

local_residue = [b for b in local_branches if b != "main"]
remote_residue = [b for b in remote_branches if b not in ("origin", "origin/main", "origin/HEAD")]
extra_worktrees = [wt for wt in worktrees if Path(wt["path"]) != Path(worktrees[0]["path"])]
matching_pr = github["matching_pr"]
open_prs = github["open_prs"]

checks = matching_pr.get("checks") if matching_pr else "none"
pr_state = matching_pr.get("state") if matching_pr else "none"
merge_state = matching_pr.get("mergeStateStatus") if matching_pr else "none"
is_draft = bool(matching_pr.get("isDraft")) if matching_pr else False

blockers = []
if dirty:
    blockers.append("dirty working tree")
elif dirty_worktrees:
    blockers.append(f"dirty worktree: {dirty_worktrees[0]['path']}")
if branch != "main" and origin_counts and origin_counts["left"] and origin_counts["right"]:
    blockers.append("branch diverged from origin/main")
if matching_pr and checks == "failed":
    blockers.append("failed PR checks")
if herdr["duplicate_active_owner"]:
    blockers.append("duplicate active Herdr owner")
if github["state"] == "unknown":
    blockers.append(f"GitHub PR state unknown: {github['reason']}")
if matching_pr and matching_pr.get("state") == "OPEN" and merge_state in ("UNKNOWN", "DIRTY", "BLOCKED"):
    blockers.append(f"unclear PR mergeability: {merge_state.lower()}")

git_golden = (
    branch == "main"
    and not dirty
    and origin_exists
    and origin_counts == {"left": 0, "right": 0}
    and len(worktrees) == 1
    and not local_residue
    and not remote_residue
    and not stashes
    and github["state"] == "ok"
    and not open_prs
)

if blockers:
    gate = "blocked"
elif matching_pr and pr_state == "MERGED" and (local_residue or remote_residue or extra_worktrees):
    gate = "cleanup gate"
elif matching_pr and pr_state == "OPEN" and not is_draft and checks == "green" and merge_state == "CLEAN":
    gate = "merge decision gate"
elif matching_pr and pr_state == "OPEN":
    gate = "PR truth gate"
elif git_golden:
    gate = "git-golden"
elif extra_worktrees or local_residue or remote_residue or branch != "main":
    gate = "active worktree"
else:
    gate = "blocked" if github["state"] == "unknown" else "cleanup gate"

if blockers:
    next_move = "clear blocker: " + blockers[0]
elif gate == "git-golden":
    next_move = "start the next focused lane with agent-work start <slug>"
elif gate == "active worktree":
    next_move = "finish the active lane, then promote to feat/<slug> or clean the worktree"
elif gate == "PR truth gate":
    next_move = "wait for checks or fix the failing PR signal before merge"
elif gate == "merge decision gate":
    next_move = "merge after explicit approval, then run cleanup and prove git-golden"
elif gate == "cleanup gate":
    next_move = "remove merged branch/worktree/stash residue, then rerun lane status"
else:
    next_move = "inspect lane state manually"

extra_residue = []
if extra_worktrees:
    extra_residue.append(f"{len(extra_worktrees)} extra worktree(s)")
if local_residue:
    extra_residue.append("local branches: " + ", ".join(local_residue[:8]))
if remote_residue:
    extra_residue.append("remote branches: " + ", ".join(remote_residue[:8]))
if stashes:
    extra_residue.append(f"{len(stashes)} stash item(s)")
if open_prs:
    extra_residue.append(f"{len(open_prs)} open PR(s)")

current_worktree = next((wt for wt in worktrees if wt["current"]), worktrees[0])
review_worktree = extra_worktrees[0] if current_worktree == worktrees[0] and extra_worktrees else current_worktree
home = worktrees[0]
payload = {
    "schema_version": 1,
    "repo": str(REPO),
    "gate": gate,
    "git_golden": git_golden,
    "next_move": next_move,
    "blockers": blockers,
    "git": {
        "branch": branch,
        "head": head,
        "head_subject": head_subject,
        "dirty": dirty,
        "dirty_count": len(dirty_lines),
        "status_short": status_short,
        "upstream": upstream or None,
        "upstream_counts": upstream_counts,
        "origin_main_counts": origin_counts,
        "local_branches": local_branches,
        "remote_branches": remote_branches,
        "stashes": stashes,
        "worktrees": worktrees,
    },
    "github": github,
    "herdr": herdr,
    "residue": extra_residue,
}

if JSON_MODE:
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0)

home_parity = "origin parity unknown"
if origin_counts:
    home_parity = f"origin/main behind={origin_counts['left']} ahead={origin_counts['right']}"
pr_line = "none"
if matching_pr:
    pr_line = (
        f"#{matching_pr['number']} {matching_pr['state'].lower()}"
        f"{' draft' if is_draft else ''}, checks={checks}, mergeability={merge_state.lower()}, {matching_pr['url']}"
    )
elif github["state"] == "unknown":
    pr_line = f"unknown ({github['reason']})"

print(f"We are at the {gate}.")
print()
print("Current state:")
print(f"- Home checkout: {home['branch']}, {'dirty' if home['dirty'] else 'clean'}, {home_parity}")
print(f"- Worktree or branch under review: {review_worktree['branch']}, {'dirty' if review_worktree['dirty'] else 'clean'}, {review_worktree['path']}")
print(f"- PR: {pr_line}")
print(f"- Blocker: {blockers[0] if blockers else 'none'}")
print(f"- Extra residue: {'; '.join(extra_residue) if extra_residue else 'none'}")
print(f"- Herdr: {herdr['state']} ({herdr['reason'] or 'read-only check complete'})")
print()
print("Loop position:")
print("1. Orient from repo truth: done")
print(f"2. {gate}: {'blocked' if blockers else 'passed'}")
print(f"3. Next: {next_move}")
print()
print(f"Git-golden verdict: {'yes' if git_golden else 'no'}")
PY
