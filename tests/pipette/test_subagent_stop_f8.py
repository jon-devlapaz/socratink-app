"""Unit tests for tools.pipette.subagent_stop — added in Chunk C (F8)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def lockfile_at_step_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a fixture lockfile + folder representing 'pipeline paused at step 3'."""
    folder = tmp_path / "feature-x"
    folder.mkdir()
    lock = tmp_path / ".lock"
    lock.write_text(yaml.safe_dump({
        "topic": "feature-x",
        "folder": str(folder),
        "state": "running",
        "current_step": 3,  # the new field the hook should read
        "acquired_at": "2026-04-30T00:00:00Z",
        "lock_written_at": "2026-04-30T00:00:00Z",
    }))
    monkeypatch.setenv("PIPETTE_LOCK_PATH", str(lock))
    return folder


def test_emit_uses_step_from_lockfile_when_set(lockfile_at_step_3: Path):
    """F8 — read path: when the lockfile carries `current_step: N`, the
    SubagentStop hook tags its trace event with that step rather than
    the legacy hardcoded `step=5`.

    NOTE: this test exercises the READ path only — the fixture writes
    `current_step: 3` directly into the lockfile yaml. In production
    today, the orchestrator's step-transition sites do not yet call
    `lockfile.set_current_step` (that wiring is markdown-driven and
    lands in a later chunk), so the hook falls back to `default=5` for
    real runs. Direct test coverage for `set_current_step` itself lives
    in `tests/pipette/test_lockfile.py`."""
    from tools.pipette.subagent_stop import _emit
    from tools.pipette.trace import Event  # noqa: F401 — used via _emit's append_event call

    rc = _emit("allow", "test", folder=lockfile_at_step_3, task_id="t.1")
    assert rc == 0
    trace_line = (lockfile_at_step_3 / "trace.jsonl").read_text().strip().splitlines()[-1]
    rec = json.loads(trace_line)
    assert rec["event"] == "subagent_stop_hook"
    assert rec["step"] == 3, f"expected step=3 from lockfile, got step={rec['step']}"
