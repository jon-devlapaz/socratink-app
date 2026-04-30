# tools/pipette/subagent_stop.py
"""SubagentStop hook handler.

Two checks per spec §3 Step 5:
  1. TDD precedence (chronological git-log walk; coverage<0.6 only)
  2. LLM-based spec-compliance + code-quality review via gemini

Either returning Critical → deny.

The hook reads its context from disk + os.getcwd() (which IS the
worktree under best-of-N's `superpowers:using-git-worktrees`).
Claude Code's stdin payload is drained but ignored — its schema is
not pipette-specific.

Robustness: benign failures (no lockfile, missing files, gemini
unavailable) return allow + explanatory reason; only TDD precedence
violation or LLM Critical findings return deny. Orchestrator's Step 5
prose checks the trace and pauses if review was bypassed.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

from tools.pipette.trace import append_event, Event

def _main_repo_root() -> Path:
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


def _lock_path() -> Path:
    """Resolve the absolute path to the active lockfile.
    Production: <main-repo-root>/docs/pipeline/_meta/.lock, where main-repo-root
      is resolved via `git --git-common-dir` so worktrees inherit the right path.
    Tests: PIPETTE_LOCK_PATH env override points at the fixture's lockfile."""
    if env := os.environ.get("PIPETTE_LOCK_PATH"):
        return Path(env)
    return _main_repo_root() / "docs" / "pipeline" / "_meta" / ".lock"


GIT_LOG_DEPTH = 20

TEST_SUBJECT_RE = re.compile(
    r"^(test:|test\()|.*\b(?:add|write|adds|writes)?[\s-]?tests?\b",
    re.IGNORECASE,
)
IMPL_SUBJECT_RE = re.compile(r"^(feat|fix)(\([^)]+\))?:", re.IGNORECASE)
# Accepts scoped form (`feat(api):`) and unscoped form (`feat:`).
# chore/refactor/perf legitimately don't require new tests; restricting
# IMPL_SUBJECT_RE to feat/fix prevents false denies. (review rounds 10, 12)

GEMINI_BIN = os.environ.get("PIPETTE_GEMINI_BIN", "/opt/homebrew/bin/gemini")
LLM_RETRY_LIMIT = 3
LLM_TIMEOUT_S = 120


def _read_current_step_from_lockfile(default: float = 5) -> float:
    """F8: hook tags trace events with the actual pipeline step rather than
    a hardcoded 5. The lockfile carries `current_step` (set by the orchestrator
    on each step transition); read it here. Returns `default` if the lockfile
    is missing or doesn't carry the field — preserves prior behavior on
    unrecognized state rather than failing the hook."""
    try:
        cur = yaml.safe_load(_lock_path().read_text()) or {}
    except (OSError, yaml.YAMLError):
        return default
    val = cur.get("current_step")
    if isinstance(val, (int, float)):
        return float(val)
    # Fallback to paused_at_step if running-state field is missing
    paused = cur.get("paused_at_step")
    if isinstance(paused, (int, float)):
        return float(paused)
    return default


def _emit(decision: str, reason: str, *, folder: Path | None = None, task_id: str | None = None) -> int:
    out = {"permissionDecision": decision, "reason": reason}
    json.dump(out, sys.stdout)
    if folder is not None:
        try:
            step = _read_current_step_from_lockfile(default=5)
            append_event(
                folder / "trace.jsonl",
                Event(step=step, event="subagent_stop_hook", decision=decision,
                      extra={"task_id": task_id, "reason": reason}),
            )
        except OSError:
            pass
    return 0


def _check_subagent_made_progress(worktree: Path, pre_dispatch_sha: str | None) -> tuple[bool, str]:
    """Returns (ok, reason). ok=False → deny.
    Empty `<boundary>..HEAD` means the subagent stopped without committing
    any work. Without this check, both _check_tdd_precedence (which returns
    'nothing to enforce' on empty log) and _check_llm_review (which returns
    'nothing to review' on empty diff) would trivially pass, letting a lazy
    or stuck subagent bypass the gate."""
    boundary = _resolve_dispatch_boundary(worktree, pre_dispatch_sha)
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


def _check_working_tree_clean(worktree: Path) -> tuple[bool, str]:
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


def _resolve_dispatch_boundary(worktree: Path, pre_dispatch_sha: str | None) -> str | None:
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


def _check_tdd_precedence(worktree: Path, coverage: float, pre_dispatch_sha: str | None) -> tuple[bool, str]:
    """Returns (ok, reason). ok=False → deny.
    Scoped to commits in `<pre_dispatch_sha>..HEAD` (or origin/main..HEAD if
    pre_dispatch_sha unset) so only subagent-introduced commits are checked."""
    if coverage >= 0.6:
        return True, f"coverage {coverage} >= 0.6, TDD enforcement skipped"
    boundary = _resolve_dispatch_boundary(worktree, pre_dispatch_sha)
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


_LLM_REVIEW_PROMPT_TEMPLATE = """\
You are a code reviewer. The plan below has many tasks; your job is to review the DIFF *only* for the implementation of the assigned task.

Assigned task: {task_id}

Do NOT flag missing work for other tasks — those are out of scope for this review. ONLY evaluate whether the diff correctly implements the assigned task.

Severity scale (project /review skill): Critical / High / Medium / Low / Polish.

Critical = correctness defects in the assigned task's implementation, plan deviations that change the assigned task's semantics, security holes, data-loss risks.

Output ONE YAML object and nothing else. No prose, no code fences, no leading or trailing whitespace beyond the YAML body. Schema:

verdict: allow | deny
critical_findings:
  - claim: <one sentence>
    severity: critical
    evidence: <quote from diff or plan>

Emit `verdict: deny` if and only if there is at least one Critical finding pertaining to the assigned task. Otherwise emit `verdict: allow` and `critical_findings: []`.

---

PLAN:

{plan}

---

DIFF (for task {task_id}):

{diff}
"""


def _check_llm_review(folder: Path, worktree: Path, task_id: str | None, pre_dispatch_sha: str | None) -> tuple[bool, str]:
    """Fail-closed: any inability to run the LLM review returns deny.
    The orchestrator's user-override path lets the user bypass on transient
    failure (gemini auth expired etc.) — see Appendix A Step 5."""
    plan_file = folder / "04-plan.md"
    if not plan_file.exists():
        return False, "fail-closed: no 04-plan.md available for LLM review"
    boundary = _resolve_dispatch_boundary(worktree, pre_dispatch_sha)
    if boundary is None:
        return False, "fail-closed: cannot resolve dispatch boundary for diff scoping"
    try:
        diff = subprocess.run(
            ["git", "diff", "--no-color", f"{boundary}..HEAD"],
            cwd=str(worktree), capture_output=True, text=True, timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, f"fail-closed: git diff unavailable ({e})"
    if diff.returncode != 0:
        return False, f"fail-closed: git diff returned {diff.returncode}"
    # NOTE: empty-diff case is caught earlier by _check_subagent_made_progress.
    # By the time we reach _check_llm_review, there is always at least one commit's worth of diff to review.

    # Use .replace() not .format() — diffs and plans contain `{` literals
    # that .format() treats as KeyError-raising placeholders.
    prompt = (
        _LLM_REVIEW_PROMPT_TEMPLATE
        .replace("{task_id}", str(task_id) if task_id else "<unknown>")
        .replace("{plan}", plan_file.read_text())
        .replace("{diff}", diff.stdout)
    )
    last_stdout = ""
    # Hook's gemini call: NO --approval-mode flag. The hook's review is a
    # non-interactive content-generation task (input → YAML output); approval-mode
    # plan is for interactive planning sessions. Plain `gemini` works for one-shot
    # prompts. (Step 3's picker DOES use --approval-mode plan; that's a separate
    # invocation in gemini_picker.py.)
    for attempt in range(LLM_RETRY_LIMIT + 1):
        try:
            r = subprocess.run(
                [GEMINI_BIN], input=prompt, capture_output=True, text=True, timeout=LLM_TIMEOUT_S,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return False, f"fail-closed: gemini unavailable ({e}); resolve and re-dispatch via /pipette resume"
        if r.returncode != 0:
            return False, f"fail-closed: gemini exit {r.returncode}: {r.stderr.strip()}"
        last_stdout = r.stdout
        # Strip markdown fences — LLMs commonly wrap YAML in ```yaml...```
        stripped = re.sub(r"^\s*```(?:yaml|json)?\s*\n?", "", last_stdout, flags=re.IGNORECASE)
        stripped = re.sub(r"\n?```\s*$", "", stripped)
        try:
            parsed = yaml.safe_load(stripped)
        except yaml.YAMLError:
            prompt = prompt + "\n\n[retry] prior output was not valid YAML; emit only the YAML.\n" + last_stdout
            continue
        if not isinstance(parsed, dict) or "verdict" not in parsed:
            prompt = prompt + "\n\n[retry] missing verdict; emit canonical schema.\n" + last_stdout
            continue
        verdict = str(parsed.get("verdict", "")).lower()
        critical = parsed.get("critical_findings")
        if not isinstance(critical, list):
            # Schema violation: critical_findings must be a list (even if empty).
            prompt = prompt + f"\n\n[retry] critical_findings must be a list; got {type(critical).__name__}.\n" + last_stdout
            continue
        if verdict == "deny" or len(critical) > 0:
            first = critical[0] if critical else {"claim": "verdict: deny w/ no findings list"}
            return False, f"LLM review Critical: {first.get('claim', '<no claim>')}"
        if verdict != "allow":
            # Unrecognized verdict ("maybe", "lgtm", "pass", etc.). Treat as
            # schema violation and retry — never fall through to allow.
            prompt = prompt + f"\n\n[retry] verdict must be exactly 'allow' or 'deny'; got {verdict!r}.\n" + last_stdout
            continue
        return True, "LLM review ok"
    return False, f"fail-closed: LLM review YAML invalid 4x; last stdout: {last_stdout[:120]!r}"


def _main_inner() -> int:
    try:
        sys.stdin.read()
    except OSError:
        pass

    lock_path = _lock_path()
    if not lock_path.exists():
        return _emit("allow", f"no active pipette run (no lockfile at {lock_path})")
    try:
        cur = yaml.safe_load(lock_path.read_text())
    except (OSError, yaml.YAMLError) as e:
        return _emit("allow", f"lockfile unreadable: {e}")
    folder = Path(cur.get("folder", ""))
    # Lockfile may store folder as relative to main repo root (orchestrator's CWD).
    # Resolve to absolute so the hook works from inside any worktree.
    if not folder.is_absolute():
        folder = _main_repo_root() / folder
    if not folder.exists():
        return _emit("allow", f"lockfile points at missing folder {folder}")

    task_file = folder / "current_task.json"
    if not task_file.exists():
        return _emit("allow", "no current_task.json — orchestrator hasn't dispatched", folder=folder)
    try:
        task = json.loads(task_file.read_text())
    except (OSError, json.JSONDecodeError) as e:
        # Fail-closed: present-but-unparsable current_task.json indicates a bug
        # in the orchestrator. Allowing here would skip both gates with no audit.
        return _emit("deny", f"fail-closed: current_task.json present but unparsable: {e}",
                     folder=folder)

    coverage = float(task.get("coverage", 1.0))
    task_id = task.get("task_id")
    pre_dispatch_sha = task.get("pre_dispatch_sha")
    worktree = Path(os.getcwd())  # the hook runs in the subagent's cwd

    # Cleanliness check: subagent MUST commit before the hook fires.
    # `git diff <base>..HEAD` and `git log <base>..HEAD` ignore the working tree;
    # uncommitted changes would silently bypass both TDD and LLM review.
    clean_ok, clean_reason = _check_working_tree_clean(worktree)
    if not clean_ok:
        return _emit("deny", clean_reason, folder=folder, task_id=task_id)

    # Productivity check: subagent MUST produce at least one commit.
    # Empty `pre_dispatch_sha..HEAD` means the subagent stopped without doing the task;
    # without this check, the TDD and LLM gates trivially pass on empty work.
    progress_ok, progress_reason = _check_subagent_made_progress(worktree, pre_dispatch_sha)
    if not progress_ok:
        return _emit("deny", progress_reason, folder=folder, task_id=task_id)

    tdd_ok, tdd_reason = _check_tdd_precedence(worktree, coverage, pre_dispatch_sha)
    if not tdd_ok:
        return _emit("deny", tdd_reason, folder=folder, task_id=task_id)

    llm_ok, llm_reason = _check_llm_review(folder, worktree, task_id, pre_dispatch_sha)
    if not llm_ok:
        return _emit("deny", llm_reason, folder=folder, task_id=task_id)

    return _emit("allow", f"{tdd_reason}; {llm_reason}", folder=folder, task_id=task_id)


def main() -> int:
    """Top-level entry — catches every exception so the hook never returns
    an unstructured response. Spec §3 Step 5 requires fail-closed deny on
    hook crash; emitting `deny` here is more useful than letting the
    process exit non-zero (which Claude Code would also treat as deny but
    with no diagnostic trace event)."""
    try:
        return _main_inner()
    except Exception as e:  # noqa: BLE001 — top-level catch is intentional
        # Best-effort: try to write to trace if we can locate the folder.
        try:
            cur = yaml.safe_load(_lock_path().read_text())
            folder = Path(cur.get("folder", ""))
            if folder.exists():
                append_event(folder / "trace.jsonl",
                             Event(step=5, event="subagent_stop_hook_crash",
                                   extra={"err": f"{type(e).__name__}: {e}"}))
        except Exception:
            pass
        json.dump({"permissionDecision": "deny", "reason": f"hook crashed: {type(e).__name__}: {e}"}, sys.stdout)
        return 0  # always exit 0 so Claude Code reads our structured deny


if __name__ == "__main__":
    sys.exit(main())
