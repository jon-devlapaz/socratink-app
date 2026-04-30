# tools/pipette/orchestrator.py
from __future__ import annotations
import sys
from dataclasses import dataclass
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


# F13: per-reviewer artifact subsets. Spec recommendation:
#   contracts: needs symbols → [00, 01]
#   impact: needs everything → [00, 01, 02, _meta/CONTEXT.md]
#   glossary: terminology, not graph → [01, 02, _meta/CONTEXT.md]
#   coverage: tests, not graph → [00, 01, coverage_map.json]
# Saves ~30% on per-reviewer context.
_REVIEWER_ARTIFACTS = {
    "contracts": ["00-graph-context.md", "01-grill.md"],
    "impact": ["00-graph-context.md", "01-grill.md", "02-diagram.mmd", "_meta/CONTEXT.md"],
    "glossary": ["01-grill.md", "02-diagram.mmd", "_meta/CONTEXT.md"],
    "coverage": ["00-graph-context.md", "01-grill.md", "coverage_map.json"],
}

_FULL_ARTIFACT_STACK = ["00-graph-context.md", "01-grill.md", "02-diagram.mmd", "_meta/CONTEXT.md"]


def reviewer_artifacts(reviewer: str) -> list[str]:
    """Return the artifact list passed to a reviewer subagent's context.
    Unknown reviewer names fall back to the full stack rather than raising,
    preserving backward compatibility if a new reviewer is added without
    updating this table."""
    return _REVIEWER_ARTIFACTS.get(reviewer, _FULL_ARTIFACT_STACK)


# F11: smart-reviewers redispatch on loop-back.
@dataclass
class ReviewerRedispatchPlan:
    reviewers: list[str]
    fallback_reason: str | None  # None on happy path; non-None when full-dispatch fallback fired


_ALL_REVIEWERS = ["contracts", "impact", "glossary", "coverage"]
_MEDIUM_OR_HIGHER = {"medium", "high", "critical"}


def reviewers_to_redispatch(survivors_by_reviewer: dict[str, list[dict]]) -> list[str]:
    """F11: only redispatch reviewers that flagged >= medium in the prior attempt.

    `_verifier-survivors.json` shape (de facto contract — not yet written by
    any code as of Chunk F): {reviewer_name: [{"severity": "...", ...}, ...]}.
    The orchestrator's loop-back dispatch path is the de facto producer."""
    out: list[str] = []
    for reviewer in _ALL_REVIEWERS:
        findings = survivors_by_reviewer.get(reviewer) or []
        if any((f.get("severity") or "").lower() in _MEDIUM_OR_HIGHER for f in findings):
            out.append(reviewer)
    return out


def reviewers_to_redispatch_from_folder(folder: Path) -> ReviewerRedispatchPlan:
    """Read `_verifier-survivors.json` from `folder`. On malformed/missing,
    fall back to full dispatch and log the reason — spec enhancement.
    The orchestrator emits a `smart_reviewers_fallback` trace event when
    `fallback_reason` is non-None."""
    import json as _json
    p = folder / "_verifier-survivors.json"
    if not p.exists():
        return ReviewerRedispatchPlan(reviewers=list(_ALL_REVIEWERS),
                                      fallback_reason="survivors_missing")
    try:
        data = _json.loads(p.read_text())
    except _json.JSONDecodeError:
        return ReviewerRedispatchPlan(reviewers=list(_ALL_REVIEWERS),
                                      fallback_reason="survivors_unparseable")
    if not isinstance(data, dict):
        return ReviewerRedispatchPlan(reviewers=list(_ALL_REVIEWERS),
                                      fallback_reason="survivors_unexpected_shape")
    return ReviewerRedispatchPlan(reviewers=reviewers_to_redispatch(data),
                                  fallback_reason=None)


def archive_for_loop_back(*, folder: Path, jump_back_to: float) -> Path:
    """§5.3: archive artifacts from step jump_back_to..highest into _attempts/N-<ts>/.

    B-revision (2026-04-28): Step 1.5 was collapsed into Step 1; grill-with-docs
    handles glossary updates inline. jump_back_to=1.5 is no longer valid.
    01b-glossary-delta.md is no longer produced; the glossary lives in
    docs/pipeline/_meta/CONTEXT.md and is updated in-place during Step 1.
    """
    from shutil import move
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    # Normalize float steps to int when whole (1.0 → 1) for tidy dir names.
    step_label = int(jump_back_to) if jump_back_to == int(jump_back_to) else jump_back_to
    arch = folder / "_attempts" / f"{step_label}-{ts}"
    arch.mkdir(parents=True)
    affected = {
        1.0: ["01-grill.md", "02-diagram.mmd", "02-diagram.excalidraw", "03-gemini-verdict.md"],
        2.0: ["02-diagram.mmd", "02-diagram.excalidraw", "03-gemini-verdict.md"],
    }
    if float(jump_back_to) not in affected:
        raise ValueError(f"jump_back_to must be 1 or 2 (B-revision dropped 1.5); got {jump_back_to!r}")
    for fname in affected[float(jump_back_to)]:
        src = folder / fname
        if src.exists():
            move(str(src), str(arch / fname))
    return arch
