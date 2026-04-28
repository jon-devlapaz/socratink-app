# tests/pipette/test_subagent_stop.py
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]

def _run(*, cwd: Path, gemini_bin: Path | None = None, lock_path: Path | None = None) -> tuple[int, dict]:
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    if gemini_bin is not None:
        env["PIPETTE_GEMINI_BIN"] = str(gemini_bin)
    if lock_path is not None:
        env["PIPETTE_LOCK_PATH"] = str(lock_path)
    r = subprocess.run(
        [sys.executable, "-m", "tools.pipette.subagent_stop"],
        input='{"hook_event_name":"SubagentStop"}',
        capture_output=True, text=True, cwd=cwd, env=env,
    )
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip() else {})

def _make_fake_gemini(tmp_path: Path, *, stdout: str, exit_code: int = 0, name: str = "fake_gemini") -> Path:
    """Create an executable shell script that mimics gemini CLI output."""
    path = tmp_path / name
    # Use heredoc-safe single-quote escaping
    safe = stdout.replace("'", "'\"'\"'")
    path.write_text(f"#!/bin/sh\nprintf '%s' '{safe}'\nexit {exit_code}\n")
    path.chmod(0o755)
    return path

GEMINI_ALLOW = "verdict: allow\ncritical_findings: []\n"
GEMINI_DENY = "verdict: deny\ncritical_findings:\n  - claim: 'broke contract X'\n    severity: critical\n"

def _setup_pipeline(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a fake docs/pipeline tree with lockfile pointing at a fake run folder.
    Returns (pipeline_root, folder, lock_path) — pass lock_path to _run via the
    PIPETTE_LOCK_PATH env override.
    """
    pipeline = tmp_path / "docs" / "pipeline"
    meta = pipeline / "_meta"
    meta.mkdir(parents=True)
    folder = pipeline / "2026-04-28-143211-x"
    folder.mkdir()
    lock = meta / ".lock"
    lock.write_text(yaml.safe_dump({
        "topic": "x", "folder": str(folder), "pid": os.getpid(),
        "pid_started_at": "2026-04-28T14:32:11Z", "lock_written_at": "2026-04-28T14:32:11Z",
        "state": "running", "research_caps": {"per_step": {}, "per_file": {}},
    }))
    return pipeline, folder, lock

def _init_git_worktree(d: Path, *, commits: list[str]) -> None:
    """Sets up a worktree with an `origin/main` ref (empty initial commit)
    and the given list of subagent-equivalent commits on top of it.
    commits: subject lines, oldest first. Each gets its own commit on a topic branch."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "x@x"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "x"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "commit.gpgsign", "false"], check=True)
    # Empty initial commit on main, then mark it as origin/main so the hook's _resolve_base_ref finds it.
    subprocess.run(["git", "-C", str(d), "commit", "-q", "--allow-empty", "-m", "chore: init main"], check=True)
    subprocess.run(["git", "-C", str(d), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    subprocess.run(["git", "-C", str(d), "checkout", "-q", "-b", "task"], check=True)
    for i, subj in enumerate(commits):
        (d / f"f{i}.py").write_text(f"# {subj}\n")
        subprocess.run(["git", "-C", str(d), "add", f"f{i}.py"], check=True)
        subprocess.run(["git", "-C", str(d), "commit", "-q", "-m", subj], check=True)

def test_no_lockfile_returns_allow(tmp_path: Path):
    rc, out = _run(cwd=tmp_path)
    assert rc == 0 and out["permissionDecision"] == "allow"
    assert "no active pipette" in out["reason"].lower()

def test_no_current_task_returns_allow(tmp_path: Path):
    _, _, lock = _setup_pipeline(tmp_path)
    rc, out = _run(cwd=tmp_path, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "allow"
    assert "current_task" in out["reason"].lower()

def test_high_coverage_skips_tdd_check_and_runs_llm(tmp_path: Path):
    """High coverage skips TDD, but LLM review still runs (fail-closed).
    Write 04-plan.md and fake gemini-allow so the LLM path completes."""
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    (folder / "04-plan.md").write_text("plan body")
    wt = tmp_path / "wt"
    wt.mkdir()
    _init_git_worktree(wt, commits=["test: t", "feat: x"])  # ensure non-empty diff
    pre_sha = subprocess.run(["git", "-C", str(wt), "rev-list", "task", "-n", "1", "--skip=2", "--reverse"],
                              capture_output=True, text=True, check=True).stdout.strip() or "origin/main"
    (folder / "current_task.json").write_text(json.dumps({
        "task_id": "t1", "coverage": 0.85, "pre_dispatch_sha": pre_sha,
    }))
    fake = _make_fake_gemini(tmp_path, stdout=GEMINI_ALLOW)
    rc, out = _run(cwd=wt, gemini_bin=fake, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "allow"

def test_low_coverage_no_test_commit_denies(tmp_path: Path):
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    wt = tmp_path / "wt"
    wt.mkdir()
    _init_git_worktree(wt, commits=["feat: add x"])  # impl only
    (folder / "current_task.json").write_text(json.dumps({"task_id": "t2", "coverage": 0.4}))
    fake = _make_fake_gemini(tmp_path, stdout=GEMINI_ALLOW)
    # Hook uses os.getcwd() — the cwd at hook invocation MUST be the worktree.
    rc, out = _run(cwd=wt, gemini_bin=fake, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "deny"
    assert "tdd" in out["reason"].lower()

def test_low_coverage_test_after_impl_denies(tmp_path: Path):
    """Chronological check: test commit AFTER impl commit must still deny."""
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    wt = tmp_path / "wt"
    wt.mkdir()
    _init_git_worktree(wt, commits=["feat: add x", "test: add test for x"])  # WRONG order
    (folder / "current_task.json").write_text(json.dumps({"task_id": "t2b", "coverage": 0.4}))
    fake = _make_fake_gemini(tmp_path, stdout=GEMINI_ALLOW)
    rc, out = _run(cwd=wt, gemini_bin=fake, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "deny"
    assert "tdd" in out["reason"].lower()

def test_low_coverage_test_before_impl_allows(tmp_path: Path):
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    wt = tmp_path / "wt"
    wt.mkdir()
    _init_git_worktree(wt, commits=["test: add test for x", "feat: add x"])  # right order
    (folder / "current_task.json").write_text(json.dumps({"task_id": "t3", "coverage": 0.4}))
    (folder / "04-plan.md").write_text("plan body")
    fake = _make_fake_gemini(tmp_path, stdout=GEMINI_ALLOW)
    rc, out = _run(cwd=wt, gemini_bin=fake, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "allow"

def test_llm_review_critical_finding_denies(tmp_path: Path):
    """Even when TDD passes, an LLM Critical finding must deny."""
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    wt = tmp_path / "wt"
    wt.mkdir()
    _init_git_worktree(wt, commits=["test: t", "feat: x"])
    (folder / "04-plan.md").write_text("plan body")
    (folder / "current_task.json").write_text(json.dumps({"task_id": "t-critical", "coverage": 0.4}))
    fake = _make_fake_gemini(tmp_path, stdout=GEMINI_DENY)
    rc, out = _run(cwd=wt, gemini_bin=fake, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "deny"
    assert "llm" in out["reason"].lower() or "critical" in out["reason"].lower()

def test_gemini_unavailable_denies_fail_closed(tmp_path: Path):
    """Fail-closed regime: gemini process failure MUST deny.
    The orchestrator surfaces the deny reason and offers the user
    `/pipette resume` after resolving auth, or `override`."""
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    wt = tmp_path / "wt"
    wt.mkdir()
    _init_git_worktree(wt, commits=["test: t", "feat: x"])
    (folder / "04-plan.md").write_text("plan body")
    (folder / "current_task.json").write_text(json.dumps({"task_id": "t-unavail", "coverage": 0.85}))  # >=0.6 to skip TDD
    fake = _make_fake_gemini(tmp_path, stdout="boom", exit_code=1)
    rc, out = _run(cwd=wt, gemini_bin=fake, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "deny"
    assert "fail-closed" in out["reason"].lower()
    assert "gemini" in out["reason"].lower()

def test_unrecognized_verdict_string_does_not_bypass(tmp_path: Path):
    """Codex Phase-C review caught: any LLM output that parses as YAML+dict+has-`verdict`
    but doesn't say `deny` was treated as `allow`. e.g. `verdict: maybe` would silently
    bypass the gate. Must retry on unrecognized verdict, then fail-closed deny after
    retries exhausted."""
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    wt = tmp_path / "wt"
    wt.mkdir()
    _init_git_worktree(wt, commits=["test: t", "feat: x"])
    (folder / "04-plan.md").write_text("plan body")
    (folder / "current_task.json").write_text(json.dumps({"task_id": "t-bypass", "coverage": 0.85}))
    # Fake gemini emits a parseable but invalid verdict — every retry returns the same
    # garbage so eventually we exhaust retries and fail-closed deny.
    fake = _make_fake_gemini(tmp_path, stdout="verdict: maybe\ncritical_findings: []\n")
    rc, out = _run(cwd=wt, gemini_bin=fake, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "deny"
    assert "fail-closed" in out["reason"].lower() or "llm review yaml invalid" in out["reason"].lower()


def test_critical_findings_not_a_list_does_not_bypass(tmp_path: Path):
    """Sibling defect of the verdict-string case. critical_findings: 'broken'
    (a string, not a list) used to evaluate `len(critical) > 0` truthy via the
    string's len, but the schema requires a list. Must retry."""
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    wt = tmp_path / "wt"
    wt.mkdir()
    _init_git_worktree(wt, commits=["test: t", "feat: x"])
    (folder / "04-plan.md").write_text("plan body")
    (folder / "current_task.json").write_text(json.dumps({"task_id": "t-list", "coverage": 0.85}))
    fake = _make_fake_gemini(tmp_path, stdout='verdict: allow\ncritical_findings: "not a list"\n')
    rc, out = _run(cwd=wt, gemini_bin=fake, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "deny"


def test_writes_decision_to_trace(tmp_path: Path):
    """Trace event written even when the hook denies (so orchestrator can read it)."""
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    (folder / "current_task.json").write_text(json.dumps({"task_id": "t4", "coverage": 0.85}))
    # No 04-plan.md, no fake gemini → fail-closed deny path. Still writes trace.
    _run(cwd=tmp_path, lock_path=lock)
    assert (folder / "trace.jsonl").exists()
    line = (folder / "trace.jsonl").read_text().splitlines()[0]
    assert "subagent_stop_hook" in line

def test_malformed_stdin_does_not_crash(tmp_path: Path):
    """The hook must not crash on non-JSON stdin — Claude Code may emit
    an empty payload or different schemas across versions. Hook returns
    allow with an explanatory reason; the orchestrator can detect this
    via the reason string if it cares."""
    r = subprocess.run(
        [sys.executable, "-m", "tools.pipette.subagent_stop"],
        input="not json",
        capture_output=True, text=True, cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["permissionDecision"] == "allow"

def test_uncommitted_working_tree_denies(tmp_path: Path):
    """Subagent that leaves work uncommitted MUST be denied — otherwise
    git diff base..HEAD is empty and the hook's TDD/LLM gates silently pass."""
    pipeline, folder, lock = _setup_pipeline(tmp_path)
    wt = tmp_path / "wt"
    wt.mkdir()
    _init_git_worktree(wt, commits=["test: t", "feat: x"])
    # Leave a dirty file in the worktree
    (wt / "uncommitted.py").write_text("dirty\n")
    (folder / "04-plan.md").write_text("plan body")
    (folder / "current_task.json").write_text(json.dumps({"task_id": "t-dirty", "coverage": 0.85}))
    fake = _make_fake_gemini(tmp_path, stdout=GEMINI_ALLOW)
    rc, out = _run(cwd=wt, gemini_bin=fake, lock_path=lock)
    assert rc == 0 and out["permissionDecision"] == "deny"
    assert "uncommitted" in out["reason"].lower() or "commit your work" in out["reason"].lower()
