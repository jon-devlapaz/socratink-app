# tools/pipette/vcs.py
from __future__ import annotations
import re
import subprocess
from pathlib import Path

GIT_LOG_DEPTH = 20

TEST_SUBJECT_RE = re.compile(
    r"^(test:|test\()|.*\b(?:add|write|adds|writes)?[\s-]?tests?\b",
    re.IGNORECASE,
)
IMPL_SUBJECT_RE = re.compile(r"^(feat|fix)(\([^)]+\))?:", re.IGNORECASE)
# Accepts scoped form (`feat(api):`) and unscoped form (`feat:`).
# chore/refactor/perf legitimately don't require new tests; restricting
# IMPL_SUBJECT_RE to feat/fix prevents false denies. (review rounds 10, 12)


def main_repo_root() -> Path:
    """Locate the MAIN repo root, even when called from inside a disposable
    git worktree. `git rev-parse --git-common-dir` returns the path to the
    main repo's .git dir (worktrees share this). Its parent is the main repo root.

    The hook MUST use this rather than `__file__`-based resolution: superpowers'
    using-git-worktrees skill creates worktrees where `__file__` resolves to
    `<worktree>/tools/pipette/...`, leading the hook to look for the lockfile
    in `<worktree>/docs/pipeline/_meta/.lock` — but that file is gitignored
    and only exists in the main repo.
    """
    r = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, timeout=5,
    )
    if r.returncode != 0:
        # Outside a git worktree entirely; fall back to __file__-based.
        return Path(__file__).resolve().parents[2]
    git_common = Path(r.stdout.strip())
    return git_common.parent  # the .git dir's parent is the repo root


def resolve_dispatch_boundary(worktree: Path, pre_dispatch_sha: str | None) -> str | None:
    """The lower bound for `<boundary>..HEAD` walks.
    Prefer `pre_dispatch_sha` (written by orchestrator before dispatch)
    so the hook scopes only to commits the subagent introduced.
    Fallback to origin/main, then origin/master.
    Returns None if no valid boundary can be resolved (caller treats as 'fail-closed deny')."""
    candidates: list[str] = []
    if pre_dispatch_sha:
        candidates.append(pre_dispatch_sha)
    candidates.extend(["origin/main", "origin/master"])
    for candidate in candidates:
        r = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
            cwd=str(worktree), capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return candidate
    return None


def check_working_tree_clean(worktree: Path) -> tuple[bool, str]:
    """Returns (ok, reason). ok=False → deny.
    `git status --porcelain` outputs one line per dirty file; empty stdout = clean.
    A subagent that left work uncommitted would produce empty `git diff base..HEAD`,
    silently bypassing the hook's TDD and LLM gates."""
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(worktree), capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, f"fail-closed: git status unavailable ({e})"
    if r.returncode != 0:
        return False, f"fail-closed: git status returned {r.returncode}: {r.stderr.strip()}"
    if r.stdout.strip():
        dirty_lines = r.stdout.strip().splitlines()[:5]
        return False, (
            f"working tree has uncommitted changes — commit your work before stopping. "
            f"Dirty files (first 5): {dirty_lines}"
        )
    return True, "working tree clean"


def check_subagent_made_progress(worktree: Path, pre_dispatch_sha: str | None) -> tuple[bool, str]:
    """Returns (ok, reason). ok=False → deny.
    Empty `<boundary>..HEAD` means the subagent stopped without committing
    any work. Without this check, both _check_tdd_precedence (which returns
    'nothing to enforce' on empty log) and _check_llm_review (which returns
    'nothing to review' on empty diff) would trivially pass, letting a lazy
    or stuck subagent bypass the gate."""
    boundary = resolve_dispatch_boundary(worktree, pre_dispatch_sha)
    if boundary is None:
        return False, "fail-closed: cannot resolve dispatch boundary for progress check"
    try:
        r = subprocess.run(
            ["git", "rev-list", "--count", f"{boundary}..HEAD"],
            cwd=str(worktree), capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, f"fail-closed: rev-list unavailable ({e})"
    if r.returncode != 0:
        return False, f"fail-closed: rev-list returned {r.returncode}"
    try:
        n = int(r.stdout.strip())
    except ValueError:
        return False, f"fail-closed: rev-list output unparsable: {r.stdout!r}"
    if n == 0:
        return False, "no commits in dispatch boundary..HEAD — subagent stopped without doing the task"
    return True, f"{n} commit(s) since dispatch"


def check_tdd_precedence(worktree: Path, coverage: float, pre_dispatch_sha: str | None) -> tuple[bool, str]:
    """Returns (ok, reason). ok=False → deny.
    Scoped to commits in `<pre_dispatch_sha>..HEAD` (or origin/main..HEAD if
    pre_dispatch_sha unset) so only subagent-introduced commits are checked."""
    if coverage >= 0.6:
        return True, f"coverage {coverage} >= 0.6, TDD enforcement skipped"
    boundary = resolve_dispatch_boundary(worktree, pre_dispatch_sha)
    if boundary is None:
        return False, "cannot resolve dispatch boundary (pre_dispatch_sha + origin/main both missing); fail-closed deny"
    try:
        log = subprocess.run(
            ["git", "log", f"{boundary}..HEAD", "--pretty=format:%H %s"],
            cwd=str(worktree), capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, f"git log failed under fail-closed regime ({e}); deny"
    if log.returncode != 0:
        return False, f"git log nonzero under fail-closed regime ({log.stderr.strip()}); deny"
    # `git log` is newest-first. Reverse for chronological order.
    entries = [ln.split(" ", 1) for ln in log.stdout.splitlines() if ln.strip()]
    if not entries:
        return True, f"no commits in {boundary}..HEAD; nothing to enforce"
    chronological = list(reversed(entries))
    first_impl_idx = None
    saw_test_before = False
    for i, (sha, subj) in enumerate(chronological):
        if first_impl_idx is None and IMPL_SUBJECT_RE.match(subj):
            first_impl_idx = i
            break
        if TEST_SUBJECT_RE.match(subj):
            saw_test_before = True
    if first_impl_idx is None:
        return True, "no impl commits in recent history; nothing to enforce"
    if not saw_test_before:
        sha, subj = chronological[first_impl_idx]
        return False, f"TDD precedence violated: impl commit {sha[:7]} {subj!r} has no preceding test commit"
    return True, "TDD precedence ok: test commit precedes first impl commit in recent history"
