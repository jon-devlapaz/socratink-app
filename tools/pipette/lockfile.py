"""Lockfile state machine for /pipette runs.

Spec: docs/superpowers/specs/2026-04-28-pipette-design.md §5.6.

v1 deviation: NO PID-based crash recovery (see plan §3 "Spec deviation").
Pipette's Python entry points are short-lived subprocesses, so any
recorded PID is dead at next-acquire time, which would make spec-literal
PID liveness erroneously declare every prior run a crash. v1 instead
refuses any `state: running` lockfile and asks the user to /pipette abort.

States when /pipette <topic> is invoked:
  - no lockfile      → acquire and proceed
  - state: running   → LockHeld (refuse; tell user to /pipette abort)
  - state: paused    → LockPaused (refuse; tell user to /pipette resume or /pipette abort)

Initial acquisition uses O_EXCL; state updates use per-pid temp + atomic rename.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os
import secrets
from typing import Any
import yaml

from tools.pipette.folder import rename_to_crashed, rename_to_aborted


class LockError(Exception):
    pass


class LockHeld(LockError):
    """An active running pipeline already holds the lock."""


class LockPaused(LockError):
    """A paused pipeline exists; user must resume or abort."""


class FilesystemUnsupported(LockError):
    """Filesystem does not support O_EXCL semantics (e.g., NFS without flock)."""


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_to_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def detect_filesystem_supports_o_excl(meta_dir: Path) -> bool:
    """Probe O_EXCL semantics on `meta_dir`. Returns True on POSIX local FS.
    Uses per-process sentinel name so concurrent probes don't race on the
    same `.lock-test` file (which would falsely report broken O_EXCL)."""
    sentinel = meta_dir / f".lock-test-{os.getpid()}-{secrets.token_hex(4)}"
    try:
        fd = os.open(str(sentinel), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        os.close(fd)
        try:
            fd2 = os.open(str(sentinel), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            os.close(fd2)
            return False  # second create succeeded → broken O_EXCL
        except FileExistsError:
            return True
    except OSError:
        return False
    finally:
        sentinel.unlink(missing_ok=True)


_STALE_THRESHOLD = timedelta(hours=24)


def acquire(lock_path: Path, *, topic: str, folder: Path) -> None:
    """Acquire the lockfile in `state: running`.

    Raises:
        FilesystemUnsupported: if O_EXCL is broken on the meta dir.
        LockHeld: a running pipeline already holds the lock.
        LockPaused: a paused pipeline exists for some topic.
    """
    meta = lock_path.parent
    meta.mkdir(parents=True, exist_ok=True)
    if not detect_filesystem_supports_o_excl(meta):
        raise FilesystemUnsupported(f"O_EXCL not reliable on {meta}; refuse to run")

    if lock_path.exists():
        existing = yaml.safe_load(lock_path.read_text())
        state = existing.get("state")
        existing_topic = existing.get("topic", "<unknown>")
        if state == "paused":
            raise LockPaused(
                f"a paused pipeline exists for {existing_topic!r} — "
                f"resume with `/pipette resume {existing_topic}` or discard with `/pipette abort {existing_topic}`"
            )
        if state == "running":
            stale_hint = ""
            written = existing.get("lock_written_at")
            if written:
                try:
                    age = datetime.now(tz=timezone.utc) - _iso_to_dt(written)
                    if age > _STALE_THRESHOLD:
                        stale_hint = (
                            f" — lockfile is stale (last written {age} ago); the prior orchestrator likely crashed; "
                            f"run `/pipette abort {existing_topic}` to clear"
                        )
                except ValueError:
                    pass
            raise LockHeld(
                f"a running pipeline lock exists for {existing_topic!r}; "
                f"finish, pause, or abort that run first{stale_hint}"
            )

    # Atomic acquire — exactly one caller wins on race.
    # The earlier `lock_path.exists()` check is best-effort (gives nicer error
    # messages); FileExistsError here means a concurrent caller won the race
    # between that check and this O_EXCL open.
    try:
        fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        raise LockHeld(
            "lock acquired concurrently by another /pipette invocation; "
            "wait for it to finish or `/pipette abort` if stuck"
        ) from None
    try:
        rec = {
            "topic": topic,
            "folder": str(folder),
            "acquired_at": _now_iso(),
            "lock_written_at": _now_iso(),
            "state": "running",
            "research_caps": {"per_step": {}, "per_file": {}},
        }
        os.write(fd, yaml.safe_dump(rec).encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def update_state(lock_path: Path, **fields: Any) -> None:
    """Atomic update of fields on the lockfile. Uses per-pid temp + rename."""
    cur = yaml.safe_load(lock_path.read_text())
    cur.update(fields)
    cur["lock_written_at"] = _now_iso()
    tmp = lock_path.with_name(f".lock.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    tmp.write_text(yaml.safe_dump(cur))
    fd = os.open(str(tmp), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp), str(lock_path))


def pause(lock_path: Path, *, paused_at_step: float | int, pause_reason: str) -> None:
    update_state(lock_path, state="paused", paused_at_step=paused_at_step, pause_reason=pause_reason)


def resume(lock_path: Path, *, topic: str) -> None:
    """Transition paused → running. Refuses any other state."""
    if not lock_path.exists():
        raise FileNotFoundError(f"no paused pipeline for {topic}")
    cur = yaml.safe_load(lock_path.read_text())
    if cur.get("state") != "paused":
        raise LockHeld(f"lockfile is not paused (state: {cur.get('state')})")
    if cur.get("topic") != topic:
        raise LockHeld(f"paused topic is {cur.get('topic')!r}, not {topic!r}")
    update_state(lock_path, state="running",
                 paused_at_step=None, pause_reason=None)


def abort(lock_path: Path, *, topic: str) -> None:
    """Abort: append abort record to trace.jsonl, rename folder to -aborted, remove lock.
    Works for both running and paused states (no PID liveness gate; v1 deviation).
    Spec §5.6 requires the trace event so the audit trail captures the abort.

    Failure modes (e.g., folder already deleted) MUST NOT leave the lockfile
    in place — the lock is the user's escape hatch and must always release.

    Topic is verified against the lockfile's recorded topic; a mismatch
    (typo) raises LockHeld without releasing — protects against accidentally
    nuking a different active pipeline by typing `/pipette abort wrong-topic`.
    """
    from tools.pipette.trace import append_event, Event  # local import to avoid circular w/ folder.py
    # Topic verification (defensive): protects against typos that would otherwise
    # silently destroy an unrelated run. Done OUTSIDE the try/finally so the
    # lockfile is preserved when topics don't match.
    try:
        peek = yaml.safe_load(lock_path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        peek = {}
    if peek.get("topic") and peek["topic"] != topic:
        raise LockHeld(
            f"abort topic {topic!r} does not match lockfile topic {peek['topic']!r}; "
            f"refusing to clear the wrong run. Use `/pipette abort {peek['topic']}` "
            f"to abort the actual active run."
        )

    try:
        # All parsing inside try/finally so a corrupted lockfile still releases.
        try:
            cur = yaml.safe_load(lock_path.read_text()) or {}
        except (OSError, yaml.YAMLError):
            cur = {}
        folder_str = cur.get("folder", "")
        folder = Path(folder_str) if folder_str else None
        if folder is not None:
            try:
                append_event(folder / "trace.jsonl",
                             Event(step=-1, event="aborted",
                                   extra={"topic": topic, "prior_state": cur.get("state")}))
            except OSError:
                pass
            try:
                rename_to_aborted(folder)
            except FileNotFoundError:
                pass  # folder may have been deleted manually; release lock anyway
    finally:
        lock_path.unlink(missing_ok=True)
