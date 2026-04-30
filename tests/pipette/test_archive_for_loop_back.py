"""Tests for archive_for_loop_back — Chunk F (F10)."""
from __future__ import annotations
from pathlib import Path

import pytest


SCRATCH_FILES = [
    "_reviewer-contracts.json",
    "_reviewer-impact.json",
    "_reviewer-glossary.json",
    "_reviewer-coverage.json",
    "_verifier-output.json",
    "_verifier-survivors.json",
    "_step3-prompt.txt",
    "_gemini-stdout.log",
]

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
