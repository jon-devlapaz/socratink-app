import os
from datetime import datetime, timezone
from pathlib import Path
import pytest


@pytest.fixture
def tmp_pipeline_root(tmp_path: Path) -> Path:
    """Returns a fresh docs/pipeline-equivalent under tmp_path with _meta/ pre-created."""
    root = tmp_path / "pipeline"
    (root / "_meta").mkdir(parents=True)
    return root


@pytest.fixture
def fixed_now() -> datetime:
    """Deterministic 'now' for folder naming tests."""
    return datetime(2026, 4, 28, 14, 32, 11, tzinfo=timezone.utc)
