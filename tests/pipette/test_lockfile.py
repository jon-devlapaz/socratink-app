import os
import subprocess
import sys
from pathlib import Path
import pytest
import yaml

from tools.pipette.lockfile import (
    acquire,
    LockHeld,
    LockPaused,
    update_state,
    pause,
    resume,
    abort,
    detect_filesystem_supports_o_excl,
)

def _read_lock(p: Path) -> dict:
    return yaml.safe_load(p.read_text())

def test_acquire_creates_when_no_lockfile(tmp_pipeline_root: Path):
    lock = tmp_pipeline_root / "_meta" / ".lock"
    folder = tmp_pipeline_root / "2026-04-28-143211-x"
    folder.mkdir()
    acquire(lock, topic="x", folder=folder)
    d = _read_lock(lock)
    assert d["state"] == "running"
    assert d["topic"] == "x"
    assert "acquired_at" in d

def test_acquire_refuses_any_running_state(tmp_pipeline_root: Path):
    """v1 deviation from spec §5.6: no PID liveness; any running state
    refuses until user runs /pipette abort. This protects from concurrent
    runs AND from stale locks; the cost is the user must explicitly
    clean up after a crashed orchestrator."""
    lock = tmp_pipeline_root / "_meta" / ".lock"
    folder = tmp_pipeline_root / "2026-04-28-143211-x"
    folder.mkdir()
    acquire(lock, topic="x", folder=folder)
    with pytest.raises(LockHeld) as ei:
        acquire(lock, topic="y", folder=tmp_pipeline_root / "2026-04-28-143212-y")
    assert "abort" in str(ei.value).lower()

def test_acquire_message_hints_abort_on_old_lock(tmp_pipeline_root: Path):
    """Lockfile older than 24h → error message includes 'stale' hint so
    the user knows abort is the right move."""
    lock = tmp_pipeline_root / "_meta" / ".lock"
    folder = tmp_pipeline_root / "2026-04-28-143211-x"
    folder.mkdir()
    fake = {
        "topic": "x", "folder": str(folder),
        "acquired_at": "2025-01-01T00:00:00Z",  # >24h ago
        "lock_written_at": "2025-01-01T00:00:00Z",
        "state": "running",
    }
    lock.write_text(yaml.safe_dump(fake))
    with pytest.raises(LockHeld) as ei:
        acquire(lock, topic="z", folder=tmp_pipeline_root / "2026-04-28-143212-z")
    assert "stale" in str(ei.value).lower() or "abort" in str(ei.value).lower()

def test_acquire_fails_when_paused(tmp_pipeline_root: Path):
    lock = tmp_pipeline_root / "_meta" / ".lock"
    folder = tmp_pipeline_root / "2026-04-28-143211-x"
    folder.mkdir()
    acquire(lock, topic="x", folder=folder)
    pause(lock, paused_at_step=3, pause_reason="NEEDS_RESEARCH")
    with pytest.raises(LockPaused):
        acquire(lock, topic="y", folder=tmp_pipeline_root / "2026-04-28-143212-y")

def test_concurrent_acquisition_only_one_wins(tmp_pipeline_root: Path):
    """Spawn two subprocesses racing on acquire. Exactly one returns 0; the other returns nonzero."""
    lock = tmp_pipeline_root / "_meta" / ".lock"
    # The try/except must be on separate lines for Python's -c mode to parse it.
    code = "\n".join([
        "from tools.pipette.lockfile import acquire, LockHeld, LockPaused",
        "from pathlib import Path",
        "import sys, os, time",
        f"lock=Path({str(lock)!r})",
        f"folder=Path({str(tmp_pipeline_root)!r})/('2026-04-28-143200-'+os.environ['T'])",
        "folder.mkdir(exist_ok=True)",
        "time.sleep(0.05)",
        "try:",
        "    acquire(lock, topic=os.environ['T'], folder=folder)",
        "    sys.exit(0)",
        "except (LockHeld, LockPaused):",
        "    sys.exit(2)",
    ])
    p1 = subprocess.Popen([sys.executable, "-c", code], env={**os.environ, "T": "a"})
    p2 = subprocess.Popen([sys.executable, "-c", code], env={**os.environ, "T": "b"})
    rc = sorted([p1.wait(), p2.wait()])
    assert rc == [0, 2]

def test_state_update_uses_per_pid_temp(tmp_pipeline_root: Path):
    lock = tmp_pipeline_root / "_meta" / ".lock"
    folder = tmp_pipeline_root / "2026-04-28-143211-x"
    folder.mkdir()
    acquire(lock, topic="x", folder=folder)
    update_state(lock, **{"lock_written_at": "2026-04-28T14:33:00Z"})
    static_tmp = tmp_pipeline_root / "_meta" / ".lock.tmp"
    assert not static_tmp.exists(), "static .lock.tmp must NEVER appear (TOCTOU race)"

def test_pause_then_resume_round_trips(tmp_pipeline_root: Path):
    lock = tmp_pipeline_root / "_meta" / ".lock"
    folder = tmp_pipeline_root / "2026-04-28-143211-x"
    folder.mkdir()
    acquire(lock, topic="x", folder=folder)
    pause(lock, paused_at_step=3, pause_reason="NEEDS_RESEARCH")
    assert _read_lock(lock)["state"] == "paused"
    resume(lock, topic="x")
    d = _read_lock(lock)
    assert d["state"] == "running"
    # v1 deviation: no pid recorded; resume does not re-write a pid field.
    assert d.get("paused_at_step") is None  # cleared by resume
    assert d.get("pause_reason") is None

def test_resume_fails_when_not_paused(tmp_pipeline_root: Path):
    lock = tmp_pipeline_root / "_meta" / ".lock"
    folder = tmp_pipeline_root / "2026-04-28-143211-x"
    folder.mkdir()
    acquire(lock, topic="x", folder=folder)
    with pytest.raises(LockHeld):
        resume(lock, topic="x")

def test_resume_fails_when_no_lockfile(tmp_pipeline_root: Path):
    with pytest.raises(FileNotFoundError):
        resume(tmp_pipeline_root / "_meta" / ".lock", topic="x")

def test_abort_renames_folder_and_removes_lock(tmp_pipeline_root: Path):
    lock = tmp_pipeline_root / "_meta" / ".lock"
    folder = tmp_pipeline_root / "2026-04-28-143211-x"
    folder.mkdir()
    acquire(lock, topic="x", folder=folder)
    pause(lock, paused_at_step=3, pause_reason="user_initiated")
    abort(lock, topic="x")
    assert not lock.exists()
    assert (tmp_pipeline_root / "2026-04-28-143211-x-aborted").exists()

def test_filesystem_detection_passes_on_local_fs(tmp_pipeline_root: Path):
    assert detect_filesystem_supports_o_excl(tmp_pipeline_root / "_meta") is True
