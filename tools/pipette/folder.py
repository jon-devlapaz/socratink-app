"""Per-feature folder naming and lifecycle (rename to -aborted/-crashed).

Folder name format: YYYY-MM-DD-HHMMSS-<kebab-topic>. The full HHMMSS is
preserved across renames so two aborts of the same topic on the same day
produce distinct folders.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slug(topic: str) -> str:
    """Kebab-case + strip non-[a-z0-9] runs."""
    s = _NON_ALNUM.sub("-", topic.lower()).strip("-")
    return s


def folder_name(now: datetime, topic_slug: str) -> str:
    return f"{now.strftime('%Y-%m-%d-%H%M%S')}-{topic_slug}"


def rename_to_aborted(folder: Path) -> Path:
    return _rename_with_suffix(folder, "-aborted")


def rename_to_crashed(folder: Path) -> Path:
    return _rename_with_suffix(folder, "-crashed")


def _rename_with_suffix(folder: Path, suffix: str) -> Path:
    if not folder.exists():
        raise FileNotFoundError(folder)
    dst = folder.with_name(folder.name + suffix)
    folder.rename(dst)
    return dst
