# tools/pipette/orchestrator.py — stubs; full impl in C5
"""Orchestrator stubs. Replaced wholesale in Task C5.

All functions referenced by tools/pipette/cli.py are declared here so
the lazy imports resolve. They raise NotImplementedError until C5.
"""
from pathlib import Path


def start(*, topic: str, root: Path) -> int:
    raise NotImplementedError("C5 lands the orchestrator")


def resume_run(*, topic: str, root: Path) -> int:
    raise NotImplementedError


def abort_run(*, topic: str, root: Path) -> int:
    raise NotImplementedError


def recover_run(*, topic: str, root: Path) -> int:
    raise NotImplementedError


def lock_status() -> int:
    raise NotImplementedError


def pause_run(*, step: float | int, reason: str, root: Path) -> int:
    raise NotImplementedError


def finish_run(*, folder: Path, root: Path) -> int:
    raise NotImplementedError


def archive_for_loop_back(*, folder: Path, jump_back_to: float) -> Path:
    raise NotImplementedError
