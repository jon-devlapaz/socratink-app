"""Research-gate brief writer with anti-loop caps (per-file: 2, per-step: 3).

The per-step cap is the load-bearing defense — slug variation cannot
bypass it. The per-file cap is a localized convenience for repeated
attacks at the same question.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import re
import yaml

class ResearchCapExceeded(Exception):
    pass

_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "for", "in", "on", "at", "to", "from", "by", "with", "as",
    "and", "or", "but", "that", "this", "these", "those", "it", "its",
    "do", "does", "did", "we", "i", "you", "they",
}
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_PER_FILE_CAP = 2
_PER_STEP_CAP = 3


def derive_slug(question: str) -> str:
    """First 8 content words after stop-word removal, kebab-cased."""
    tokens = _NON_ALNUM.sub(" ", question.lower()).split()
    content = [t for t in tokens if t not in _STOP_WORDS]
    return "-".join(content[:8])


def _lock_path_from_folder(folder: Path) -> Path:
    return folder.parent / "_meta" / ".lock"


def _bump_caps(folder: Path, step: float | int, file_slug: str) -> tuple[int, int]:
    """Increment the per-step and per-file counters; raise if either now exceeds.
    Returns (per_step_count_after, per_file_count_after).
    Uses lockfile.update_state for atomic temp-file+rename so concurrent
    readers (lock-status, abort) never see a half-written lockfile."""
    from tools.pipette.lockfile import update_state  # local import to avoid circular
    lock = _lock_path_from_folder(folder)
    cur = yaml.safe_load(lock.read_text())
    caps = cur.get("research_caps") or {"per_step": {}, "per_file": {}}
    per_step = caps.setdefault("per_step", {})
    per_file = caps.setdefault("per_file", {})
    file_key = f"{step}-{file_slug}.md"
    new_file = per_file.get(file_key, 0) + 1
    new_step = per_step.get(str(step), 0) + 1
    per_file[file_key] = new_file
    per_step[str(step)] = new_step
    if new_file > _PER_FILE_CAP:
        raise ResearchCapExceeded(
            f"per-file cap ({_PER_FILE_CAP}) exceeded for {file_key}: re-raising the same question is not allowed"
        )
    if new_step > _PER_STEP_CAP:
        raise ResearchCapExceeded(
            f"per-step cap ({_PER_STEP_CAP}) exceeded for step {step}: too many research raises in one run"
        )
    update_state(lock, research_caps=caps)
    return new_step, new_file


def write_brief(*, folder: Path, step: float | int, question: str, why: str) -> Path:
    s = derive_slug(question)
    _bump_caps(folder, step, s)
    rdir = folder / "_research"
    rdir.mkdir(parents=True, exist_ok=True)
    target = rdir / f"{step}-{s}.md"
    if target.exists():
        prefix = target.read_text() + "\n\n---\n\n"
    else:
        prefix = ""
    rec = {
        "raised_by_step": step,
        "raised_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_question": question,
        "why_needed": why,
        "suggested_tools": ["Claude Research", "ChatGPT Deep Research", "Perplexity", "Gemini Deep Research"],
        "required_findings": [
            "confirmation w/ source URL and date",
            "example call pattern (when applicable)",
            "known gotchas / breaking changes",
        ],
        "blocking": True,
    }
    target.write_text(prefix + yaml.safe_dump(rec))
    return target


def write_findings(*, folder: Path, step: float | int, question: str, findings_text: str) -> Path:
    """User pastes back research findings; appended to the same file."""
    s = derive_slug(question)
    target = folder / "_research" / f"{step}-{s}.md"
    if not target.exists():
        raise FileNotFoundError(target)
    target.write_text(target.read_text() + "\n\n## Findings\n\n" + findings_text + "\n")
    return target
