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


from dataclasses import dataclass


# F15 thresholds — hardcoded constants per spec scope cuts.
# Tuning requires editing this file (deliberate; no scoring module).
F15_COVERAGE_FLOOR = 0.80
F15_RISK_CEILING = 0.30
F15_LINES_CEILING = 50


@dataclass
class Step3HeuristicDecision:
    auto_pass: bool
    reason: str  # "heuristic_auto_pass" | "coverage_below_80" | "risk_above_30" | "lines_above_50" | "coverage_malformed" | "grill_meta_missing"


def _read_grill_meta(folder: Path) -> tuple[int | None, float | None]:
    """Parse the `<!-- pipette-meta total_changed_lines=N max_risk_score=F -->`
    annotation that the grill writes into 01-grill.md. The grill prompt
    instructs it to emit this block; if missing, both values are None and
    F15 falls through (no auto-pass without a grounded count)."""
    import re
    p = folder / "01-grill.md"
    if not p.exists():
        return None, None
    text = p.read_text()
    m = re.search(r"pipette-meta\s+total_changed_lines=(\d+)\s+max_risk_score=([\d.]+)", text)
    if not m:
        return None, None
    return int(m.group(1)), float(m.group(2))


def _read_coverage_min(folder: Path) -> tuple[float | None, str | None]:
    """Returns (min_coverage_across_affected, error_reason). On malformed
    JSON or missing file, returns (None, 'coverage_malformed')."""
    import json as _json
    p = folder / "coverage_map.json"
    if not p.exists():
        return None, "coverage_malformed"
    try:
        data = _json.loads(p.read_text())
    except _json.JSONDecodeError:
        return None, "coverage_malformed"
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not files:
        return None, "coverage_malformed"
    return min(float(v) for v in files.values()), None


def step3_heuristic_decision(*, folder: Path, write_trace: bool = False) -> "Step3HeuristicDecision":
    """F15: gate at Step 3 entry. Auto-pass IFF all thresholds met.

    On fall-through, optionally emits an `autopass_rejected` trace event
    naming the failed threshold — needed for future threshold tuning.
    """
    cov_min, cov_err = _read_coverage_min(folder)
    if cov_err:
        decision = Step3HeuristicDecision(auto_pass=False, reason=cov_err)
    elif cov_min < F15_COVERAGE_FLOOR:
        decision = Step3HeuristicDecision(auto_pass=False, reason="coverage_below_80")
    else:
        lines, risk = _read_grill_meta(folder)
        if lines is None or risk is None:
            decision = Step3HeuristicDecision(auto_pass=False, reason="grill_meta_missing")
        elif risk >= F15_RISK_CEILING:
            decision = Step3HeuristicDecision(auto_pass=False, reason="risk_above_30")
        elif lines >= F15_LINES_CEILING:
            decision = Step3HeuristicDecision(auto_pass=False, reason="lines_above_50")
        else:
            decision = Step3HeuristicDecision(auto_pass=True, reason="heuristic_auto_pass")

    if write_trace and not decision.auto_pass:
        try:
            append_event(folder / "trace.jsonl",
                         Event(step=3, event="autopass_rejected",
                               extra={"reason": decision.reason}))
        except OSError:
            pass
    return decision


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
