from datetime import datetime, timezone
from pathlib import Path
import pytest
from tools.pipette.folder import slug, folder_name, rename_to_aborted, rename_to_crashed


def test_slug_kebab_cases_topic():
    assert slug("Add Concept Tile Drag") == "add-concept-tile-drag"


def test_slug_strips_non_alnum_and_collapses_dashes():
    assert slug("foo  / bar -- baz!") == "foo-bar-baz"


def test_folder_name_includes_full_hhmmss(fixed_now):
    assert folder_name(fixed_now, "add-tile") == "2026-04-28-143211-add-tile"


def test_rename_to_aborted_preserves_full_timestamp(tmp_pipeline_root: Path, fixed_now: datetime):
    src = tmp_pipeline_root / folder_name(fixed_now, "topic-x")
    src.mkdir()
    dst = rename_to_aborted(src)
    assert dst.name == "2026-04-28-143211-topic-x-aborted"
    assert dst.exists() and not src.exists()


def test_rename_to_crashed_preserves_full_timestamp(tmp_pipeline_root: Path, fixed_now: datetime):
    src = tmp_pipeline_root / folder_name(fixed_now, "topic-y")
    src.mkdir()
    dst = rename_to_crashed(src)
    assert dst.name == "2026-04-28-143211-topic-y-crashed"
    assert dst.exists() and not src.exists()
