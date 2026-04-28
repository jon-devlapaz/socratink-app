# tests/pipette/test_e2e_integration.py
"""Fake end-to-end smoke. Exercises the CLI surface in the order Appendix A invokes it,
against fake artifacts so no real subagent or external service is required.

Catches command-name drift (e.g., if the slash command says `pipette gemini-pick`
but cli.py actually has `pipette gemini`)."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]

def _cli(*args, cwd=None, input=None, env_extra=None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "tools.pipette", *args],
        capture_output=True, text=True, cwd=cwd or REPO, env=env, input=input,
    )

def test_full_lifecycle_against_fakes(tmp_path: Path):
    """start → trace-append → research-brief → pause → resume → trace-append → finish.
    Verifies every CLI subcommand wired in Appendix A actually exists and works."""
    root = tmp_path / "pipeline"

    # 1. start
    r = _cli("start", "fake topic", "--root", str(root))
    assert r.returncode == 0, r.stderr
    assert "started" in r.stdout
    folders = list(root.glob("*-fake-topic"))
    assert len(folders) == 1
    folder = folders[0]
    assert (root / "_meta" / ".lock").exists()

    # 2. trace-append (orchestrator-internal)
    r = _cli("trace-append", "--folder", str(folder), "--step", "0", "--event", "graph_recon_done")
    assert r.returncode == 0, r.stderr
    line = (folder / "trace.jsonl").read_text().splitlines()[-1]
    assert "graph_recon_done" in line

    # 3. research-brief
    brief = tmp_path / "brief.yaml"
    brief.write_text(yaml.safe_dump({"question": "Fake research Q?", "why_needed": "test integration"}))
    r = _cli("research-brief", "--folder", str(folder), "--step", "1", "--brief-file", str(brief))
    assert r.returncode == 0, r.stderr
    rfiles = list((folder / "_research").glob("1-*.md"))
    assert len(rfiles) == 1

    # 4. pause
    r = _cli("pause", "--step", "1", "--reason", "NEEDS_RESEARCH", "--root", str(root))
    assert r.returncode == 0, r.stderr
    lock = yaml.safe_load((root / "_meta" / ".lock").read_text())
    assert lock["state"] == "paused"
    assert lock["paused_at_step"] == 1

    # 5. research-findings (resume path)
    findings = tmp_path / "findings.md"
    findings.write_text("# Findings\nFake research result\n")
    r = _cli("research-findings", "--folder", str(folder), "--step", "1",
             "--question", "Fake research Q?", "--findings-file", str(findings))
    assert r.returncode == 0, r.stderr
    assert "## Findings" in rfiles[0].read_text()

    # 6. resume
    r = _cli("resume", "fake topic", "--root", str(root))
    assert r.returncode == 0, r.stderr
    lock = yaml.safe_load((root / "_meta" / ".lock").read_text())
    assert lock["state"] == "running"

    # 7. parse-jump (validates user --jump-to input).
    # B-revision (2026-04-28): only 1 or 2 valid; 1.5 dropped along with Step 1.5.
    r = _cli("parse-jump", "--jump-to 2")
    assert r.returncode == 0 and r.stdout.strip() == "2"
    r = _cli("parse-jump", "--jump-to 1.5")
    assert r.returncode == 2  # invalid (was valid before B-revision)
    r = _cli("parse-jump", "--jump-to 3")
    assert r.returncode == 2  # invalid

    # 8. archive-for-loop-back (Step 3 FAIL path)
    (folder / "01-grill.md").write_text("dummy")
    (folder / "03-gemini-verdict.md").write_text("dummy")
    r = _cli("archive-for-loop-back", "--folder", str(folder), "--jump-back-to", "1")
    assert r.returncode == 0, r.stderr
    assert any((folder / "_attempts").glob("1-*"))

    # 9. verifier-filter
    sample = json.dumps({
        "reviewer": "verifier",
        "findings": [
            {"reviewer": "verifier", "severity": "high", "confidence": 0.9, "claim": "x", "evidence": ["a"]},
            {"reviewer": "verifier", "severity": "low",  "confidence": 0.5, "claim": "y", "evidence": ["b"]},
        ],
        "notes": "",
    })
    r = _cli("verifier-filter", input=sample)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert len(out["findings"]) == 1  # the 0.5-confidence one is dropped

    # 10. finish
    r = _cli("finish", "--folder", str(folder), "--root", str(root))
    assert r.returncode == 0, r.stderr
    assert not (root / "_meta" / ".lock").exists()
    last_event = json.loads((folder / "trace.jsonl").read_text().splitlines()[-1])
    assert last_event["event"] == "finished"


def test_doctor_fails_clearly_when_gemini_missing(tmp_path: Path, monkeypatch):
    """Acceptance failure-path: doctor must surface a clear actionable error
    when a critical dep is missing."""
    monkeypatch.setenv("PATH", str(tmp_path))  # PATH with no gemini
    r = _cli("doctor", cwd=tmp_path)
    # Doctor exits 1 when any check fails; gemini will be one of them.
    assert r.returncode == 1
    assert "gemini" in r.stdout.lower()
    assert "FIX:" in r.stdout


def test_start_refuses_second_active_run(tmp_path: Path):
    """Acceptance failure-path: starting a second run while one is active
    must refuse with a clear error."""
    root = tmp_path / "pipeline"
    r1 = _cli("start", "first", "--root", str(root))
    assert r1.returncode == 0
    r2 = _cli("start", "second", "--root", str(root))
    assert r2.returncode == 1
    assert "running" in r2.stderr.lower() or "abort" in r2.stderr.lower()


def test_abort_renames_folder_and_releases_lock(tmp_path: Path):
    """Acceptance failure-path: abort must successfully clean up regardless
    of state (running, paused, or recover)."""
    root = tmp_path / "pipeline"
    _cli("start", "ax", "--root", str(root))
    assert (root / "_meta" / ".lock").exists()
    folders_before = list(root.glob("*-ax"))
    r = _cli("abort", "ax", "--root", str(root))
    assert r.returncode == 0, r.stderr
    assert not (root / "_meta" / ".lock").exists()
    aborted = list(root.glob("*-ax-aborted"))
    assert len(aborted) == 1
    assert not folders_before[0].exists()  # original was renamed


def test_abort_topic_mismatch_refuses(tmp_path: Path):
    """Defensive: aborting with the wrong topic must NOT destroy the active run."""
    root = tmp_path / "pipeline"
    _cli("start", "real-topic", "--root", str(root))
    r = _cli("abort", "wrong-topic", "--root", str(root))
    assert r.returncode == 1
    assert (root / "_meta" / ".lock").exists()  # not destroyed
    assert any(root.glob("*-real-topic"))       # folder preserved
