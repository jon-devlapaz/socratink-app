"""Per-run trace.jsonl writer. Append-only.

Concurrency: `O_APPEND` ensures each `os.write` lands at EOF (the kernel
seeks to the end before writing). For short single-line records on a local
POSIX filesystem, this prevents interleaving without explicit locking.
PIPE_BUF (a guarantee about atomic short writes to PIPES/FIFOs) does NOT
apply to regular files; the soundness of single-line appends here rests
on `O_APPEND` end-positioning + each event being one `os.write`.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

@dataclass
class Event:
    step: float | int
    event: str
    decision: str | None = None
    jump_back_to: float | int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

def append_event(path: Path, ev: Event) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rec: dict[str, Any] = {
        "ts": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "step": ev.step,
        "event": ev.event,
    }
    if ev.decision is not None:
        rec["decision"] = ev.decision
    if ev.jump_back_to is not None:
        rec["jump_back_to"] = ev.jump_back_to
    rec.update(ev.extra)
    line = json.dumps(rec, separators=(",", ":")) + "\n"
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)
