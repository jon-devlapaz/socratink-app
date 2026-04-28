# tests/pipette/test_orchestrator.py
import os
import yaml
from pathlib import Path
from tools.pipette.orchestrator import start, resume_run, abort_run, lock_status, archive_for_loop_back

def test_start_creates_folder_and_lock(tmp_path: Path, capsys):
    rc = start(topic="add tile drag", root=tmp_path / "pipeline")
    assert rc == 0
    folders = list((tmp_path / "pipeline").glob("*-add-tile-drag"))
    assert len(folders) == 1
    lock = (tmp_path / "pipeline" / "_meta" / ".lock")
    assert lock.exists()
    out = capsys.readouterr().out
    assert "started" in out.lower() or str(folders[0]) in out

def test_start_refuses_when_running(tmp_path: Path, capsys):
    start(topic="x", root=tmp_path / "pipeline")
    rc = start(topic="y", root=tmp_path / "pipeline")
    assert rc == 1
    captured_err = capsys.readouterr().err.lower()
    assert "already running" in captured_err or "running" in captured_err

def test_abort_rolls_folder_to_aborted(tmp_path: Path):
    start(topic="x", root=tmp_path / "pipeline")
    # simulate paused state for non-running abort
    from tools.pipette.lockfile import pause
    pause(tmp_path / "pipeline" / "_meta" / ".lock", paused_at_step=3, pause_reason="user_initiated")
    rc = abort_run(topic="x", root=tmp_path / "pipeline")
    assert rc == 0
    aborted = list((tmp_path / "pipeline").glob("*-x-aborted"))
    assert len(aborted) == 1

def test_resume_fails_when_no_paused(tmp_path: Path, capsys):
    rc = resume_run(topic="nope", root=tmp_path / "pipeline")
    assert rc == 1
    assert "no paused" in capsys.readouterr().err.lower()

def test_archive_for_loop_back_step_1(tmp_path: Path):
    folder = tmp_path / "run"
    folder.mkdir()
    for f in ["01-grill.md", "02-diagram.mmd", "03-gemini-verdict.md"]:
        (folder / f).write_text("x")
    arch = archive_for_loop_back(folder=folder, jump_back_to=1.0)
    assert (arch / "01-grill.md").exists()
    assert not (folder / "01-grill.md").exists()

def test_archive_for_loop_back_step_1_5(tmp_path: Path):
    folder = tmp_path / "run"
    folder.mkdir()
    (folder / "01-grill.md").write_text("x")
    (folder / "01b-glossary-delta.md").write_text("x")
    arch = archive_for_loop_back(folder=folder, jump_back_to=1.5)
    assert (folder / "01-grill.md").exists()  # NOT archived (precedes 1.5)
    assert (arch / "01b-glossary-delta.md").exists()  # archived

def test_archive_for_loop_back_step_2(tmp_path: Path):
    folder = tmp_path / "run"
    folder.mkdir()
    (folder / "01b-glossary-delta.md").write_text("x")
    (folder / "02-diagram.mmd").write_text("x")
    arch = archive_for_loop_back(folder=folder, jump_back_to=2.0)
    assert (folder / "01b-glossary-delta.md").exists()  # NOT archived (precedes 2)
    assert (arch / "02-diagram.mmd").exists()
