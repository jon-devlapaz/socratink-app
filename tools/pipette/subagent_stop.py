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
from tools.pipette.vcs import (
    main_repo_root,
    resolve_dispatch_boundary,
    check_working_tree_clean,
    check_subagent_made_progress,
    check_tdd_precedence,
)
from tools.pipette.llm import invoke_gemini, GeminiProcessFailure, GeminiYamlInvalidAfterRetries
from pydantic import BaseModel, Field
from typing import Literal


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


def _lock_path() -> Path:
    """Resolve the absolute path to the active lockfile.
    Production: <main-repo-root>/docs/pipeline/_meta/.lock, where main-repo-root
      is resolved via `git --git-common-dir` so worktrees inherit the right path.
    Tests: PIPETTE_LOCK_PATH env override points at the fixture's lockfile."""
    if env := os.environ.get("PIPETTE_LOCK_PATH"):
        return Path(env)
    return main_repo_root() / "docs" / "pipeline" / "_meta" / ".lock"


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


class CriticalFinding(BaseModel):
    claim: str
    severity: str
    evidence: str

class LLMReviewVerdict(BaseModel):
    verdict: Literal["allow", "deny"]
    critical_findings: list[CriticalFinding] = Field(default_factory=list)

def _check_llm_review(folder: Path, worktree: Path, task_id: str | None, pre_dispatch_sha: str | None) -> tuple[bool, str]:
    """Fail-closed: any inability to run the LLM review returns deny.
    The orchestrator's user-override path lets the user bypass on transient
    failure (gemini auth expired etc.) — see Appendix A Step 5."""
    plan_file = folder / "04-plan.md"
    if not plan_file.exists():
        return False, "fail-closed: no 04-plan.md available for LLM review"
    boundary = resolve_dispatch_boundary(worktree, pre_dispatch_sha)
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

    prompt = (
        _LLM_REVIEW_PROMPT_TEMPLATE
        .replace("{task_id}", str(task_id) if task_id else "<unknown>")
        .replace("{plan}", plan_file.read_text())
        .replace("{diff}", diff.stdout)
    )
    try:
        verdict_obj = invoke_gemini(prompt, LLMReviewVerdict, approval_mode=False)
    except GeminiProcessFailure as e:
        return False, f"fail-closed: {e}; resolve and re-dispatch via /pipette resume"
    except GeminiYamlInvalidAfterRetries as e:
        return False, f"fail-closed: LLM review YAML invalid 4x: {e}"

    if verdict_obj.verdict == "deny" or len(verdict_obj.critical_findings) > 0:
        first = verdict_obj.critical_findings[0] if verdict_obj.critical_findings else CriticalFinding(claim="verdict: deny w/ no findings list", severity="critical", evidence="")
        return False, f"LLM review Critical: {first.claim}"
    if verdict_obj.verdict != "allow":
        return False, f"LLM review returned unexpected verdict: {verdict_obj.verdict}"
    
    return True, "LLM review ok"


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
        folder = main_repo_root() / folder
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
    clean_ok, clean_reason = check_working_tree_clean(worktree)
    if not clean_ok:
        return _emit("deny", clean_reason, folder=folder, task_id=task_id)

    # Productivity check: subagent MUST produce at least one commit.
    # Empty `pre_dispatch_sha..HEAD` means the subagent stopped without doing the task;
    # without this check, the TDD and LLM gates trivially pass on empty work.
    progress_ok, progress_reason = check_subagent_made_progress(worktree, pre_dispatch_sha)
    if not progress_ok:
        return _emit("deny", progress_reason, folder=folder, task_id=task_id)

    tdd_ok, tdd_reason = check_tdd_precedence(worktree, coverage, pre_dispatch_sha)
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
