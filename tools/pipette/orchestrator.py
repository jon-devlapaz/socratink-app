# tools/pipette/orchestrator.py
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

from tools.pipette.folder import folder_name, slug
from tools.pipette.lockfile import (
    acquire, resume, abort, LockHeld, LockPaused, FilesystemUnsupported,
)
from tools.pipette.trace import append_event, Event


def _meta(root: Path) -> Path:
    p = root / "_meta"
    p.mkdir(parents=True, exist_ok=True)
    return p


def start(*, topic: str, root: Path) -> int:
    topic_slug = slug(topic)
    now = datetime.now(tz=timezone.utc)
    folder = (root / folder_name(now, topic_slug)).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    lock = _meta(root) / ".lock"
    try:
        acquire(lock, topic=topic_slug, folder=folder)
    except (LockHeld, LockPaused, FilesystemUnsupported) as e:
        folder.rmdir()
        print(f"pipette: {e}", file=sys.stderr)
        return 1
    append_event(folder / "trace.jsonl", Event(step=-1, event="started", extra={"topic": topic_slug}))
    print(f"pipette: started {topic_slug} → {folder}")
    return 0


def resume_run(*, topic: str, root: Path) -> int:
    lock = _meta(root) / ".lock"
    if not lock.exists():
        print(f"pipette: no paused pipeline for {topic}", file=sys.stderr)
        return 1
    pre_cur = yaml.safe_load(lock.read_text())
    paused_step = pre_cur.get("paused_at_step", -1)
    folder = Path(pre_cur["folder"])
    try:
        resume(lock, topic=slug(topic))
    except (LockHeld, FileNotFoundError) as e:
        print(f"pipette: {e}", file=sys.stderr)
        return 1
    append_event(folder / "trace.jsonl", Event(step=paused_step, event="resumed"))
    print(f"pipette: resumed {topic} from step {paused_step} → {folder}")
    return 0


def abort_run(*, topic: str, root: Path) -> int:
    lock = _meta(root) / ".lock"
    if not lock.exists():
        print(f"pipette: no pipeline to abort for {topic}", file=sys.stderr)
        return 1
    try:
        abort(lock, topic=slug(topic))
    except LockHeld as e:
        print(f"pipette: {e}", file=sys.stderr)
        return 1
    print(f"pipette: aborted {topic}")
    return 0


def lock_status() -> int:
    lock = Path("docs/pipeline/_meta/.lock")
    if not lock.exists():
        print("(no active pipeline)")
        return 0
    print(lock.read_text())
    return 0


def pause_run(*, step: float | int, reason: str, root: Path) -> int:
    from tools.pipette.lockfile import pause as _pause
    lock = _meta(root) / ".lock"
    if not lock.exists():
        print("pipette: no active pipeline to pause", file=sys.stderr)
        return 1
    _pause(lock, paused_at_step=step, pause_reason=reason)
    cur = yaml.safe_load(lock.read_text())
    folder = Path(cur["folder"])
    append_event(folder / "trace.jsonl", Event(step=step, event="paused", extra={"reason": reason}))
    print(f"pipette: paused at step {step} ({reason})")
    return 0


def finish_run(*, folder: Path, root: Path) -> int:
    lock = _meta(root) / ".lock"
    append_event(folder / "trace.jsonl", Event(step=7, event="finished"))
    if lock.exists():
        lock.unlink()
    print("pipette: ✅ pipeline complete")
    return 0


def recover_run(*, topic: str, root: Path) -> int:
    """Force release of a stale `state: running` lock without renaming the folder."""
    lock = _meta(root) / ".lock"
    if not lock.exists():
        print(f"pipette: no lockfile to recover for {topic}", file=sys.stderr)
        return 1
    cur = yaml.safe_load(lock.read_text()) or {}
    if cur.get("topic") != slug(topic):
        print(f"pipette: lockfile topic {cur.get('topic')!r} does not match {topic!r}; "
              f"refusing to recover the wrong run", file=sys.stderr)
        return 1
    folder = Path(cur.get("folder", ""))
    last_event = "<no trace>"
    if folder.exists() and (folder / "trace.jsonl").exists():
        lines = (folder / "trace.jsonl").read_text().splitlines()
        if lines:
            last_event = lines[-1][:200]
        append_event(folder / "trace.jsonl", Event(step=-1, event="recovered",
                                                   extra={"prior_state": cur.get("state")}))
    lock.unlink()
    print(f"pipette: lock released for {topic}. Folder preserved at {folder}.")
    print(f"pipette: last trace event was: {last_event}")
    print(f"pipette: re-run /pipette {topic} to start fresh, or work with the artifacts directly.")
    return 0


def archive_for_loop_back(*, folder: Path, jump_back_to: float) -> Path:
    """§5.3: archive artifacts from step jump_back_to..highest into _attempts/N-<ts>/."""
    from shutil import move
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    arch = folder / "_attempts" / f"{jump_back_to}-{ts}"
    arch.mkdir(parents=True)
    affected = {
        1.0: ["01-grill.md", "01b-glossary-delta.md", "02-diagram.mmd", "02-diagram.excalidraw", "03-gemini-verdict.md"],
        1.5: ["01b-glossary-delta.md", "02-diagram.mmd", "02-diagram.excalidraw", "03-gemini-verdict.md"],
        2.0: ["02-diagram.mmd", "02-diagram.excalidraw", "03-gemini-verdict.md"],
    }
    for fname in affected[float(jump_back_to)]:
        src = folder / fname
        if src.exists():
            move(str(src), str(arch / fname))
    return arch
