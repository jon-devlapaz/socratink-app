"""Tests for archive_for_loop_back — Chunk F (F10)."""
from __future__ import annotations
from pathlib import Path

import pytest

from tools.pipette.orchestrator import _STEP3_SCRATCH


# Single source of truth — drift between this test list and the production
# constant would silently un-test new scratch files added later.
SCRATCH_FILES = list(_STEP3_SCRATCH)

ORIGINAL_ARTIFACTS = ["01-grill.md", "02-diagram.mmd", "03-gemini-verdict.md"]


def _populate(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    for f in SCRATCH_FILES + ORIGINAL_ARTIFACTS:
        (folder / f).write_text("placeholder")


def test_archive_includes_step3_scratch(tmp_path: Path):
    """F10: loop-back archive must include reviewer JSONs, verifier outputs,
    Step 3 prompt, and gemini stdout — the audit trail for attempt 1."""
    from tools.pipette.orchestrator import archive_for_loop_back
    folder = tmp_path / "feature-x"
    _populate(folder)
    arch = archive_for_loop_back(folder=folder, jump_back_to=1.0)
    archived = {p.name for p in arch.iterdir()}
    for scratch in SCRATCH_FILES:
        assert scratch in archived, f"F10: {scratch} should be archived but wasn't"
    for original in ORIGINAL_ARTIFACTS:
        assert original in archived, f"original artifact {original} should still be archived"


def test_archive_does_not_fail_on_missing_scratch(tmp_path: Path):
    """If a scratch file doesn't exist (e.g., Step 3 was a heuristic auto-pass),
    archive_for_loop_back must not raise."""
    from tools.pipette.orchestrator import archive_for_loop_back
    folder = tmp_path / "feature-x"
    folder.mkdir()
    for f in ORIGINAL_ARTIFACTS:
        (folder / f).write_text("placeholder")
    arch = archive_for_loop_back(folder=folder, jump_back_to=1.0)
    archived = {p.name for p in arch.iterdir()}
    for original in ORIGINAL_ARTIFACTS:
        assert original in archived


def test_archive_handles_partial_scratch(tmp_path: Path):
    """Mid-state: only some scratch files exist (e.g., reviewer dispatch
    crashed mid-batch leaving 2 of 4 reviewer JSONs). archive_for_loop_back
    must move the present ones without failing on absentees."""
    from tools.pipette.orchestrator import archive_for_loop_back
    folder = tmp_path / "feature-x"
    folder.mkdir()
    present = ["01-grill.md", "_reviewer-contracts.json", "_reviewer-impact.json"]
    for f in present:
        (folder / f).write_text("placeholder")
    arch = archive_for_loop_back(folder=folder, jump_back_to=1.0)
    archived = {p.name for p in arch.iterdir()}
    assert "01-grill.md" in archived
    assert "_reviewer-contracts.json" in archived
    assert "_reviewer-impact.json" in archived
    assert "_reviewer-glossary.json" not in archived  # never existed
    assert "_reviewer-coverage.json" not in archived  # never existed
