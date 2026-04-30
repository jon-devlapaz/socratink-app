"""Tests for orchestrator dispatch decisions — Chunk F (F11–F13)."""
from __future__ import annotations
from pathlib import Path

import pytest


@pytest.fixture
def folder_with_artifacts(tmp_path: Path) -> Path:
    """A pipeline folder with standard Step 3 artifacts pre-populated."""
    folder = tmp_path / "feature-x"
    folder.mkdir()
    for name in ["00-graph-context.md", "01-grill.md", "02-diagram.mmd", "_meta/CONTEXT.md"]:
        p = folder / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("placeholder")
    return folder


# ---------------------------------------------------------------------------
# F13 — per-reviewer artifact subsets
# ---------------------------------------------------------------------------

def test_f13_glossary_reviewer_does_not_get_graph_context():
    """F13: per-reviewer artifact subsets. Glossary reviewer never sees
    00-graph-context.md (graph data, not glossary)."""
    from tools.pipette.orchestrator import reviewer_artifacts
    artifacts = reviewer_artifacts("glossary")
    assert "00-graph-context.md" not in artifacts


def test_f13_impact_reviewer_gets_full_artifact_stack():
    """F13: impact is the only reviewer that needs all four artifacts."""
    from tools.pipette.orchestrator import reviewer_artifacts
    artifacts = reviewer_artifacts("impact")
    assert {"00-graph-context.md", "01-grill.md", "02-diagram.mmd",
            "_meta/CONTEXT.md"}.issubset(set(artifacts))


def test_f13_unknown_reviewer_gets_full_stack():
    """Defensive: an unknown reviewer name falls back to the full stack
    rather than raising — preserves backward compatibility if a future
    reviewer is added without updating the lookup table."""
    from tools.pipette.orchestrator import reviewer_artifacts
    artifacts = reviewer_artifacts("future_reviewer")
    assert "00-graph-context.md" in artifacts
