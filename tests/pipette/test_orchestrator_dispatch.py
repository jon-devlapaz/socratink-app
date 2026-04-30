"""Tests for orchestrator dispatch decisions — Chunk G (F15, F14) and Chunk F (F11–F13)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# F15 thresholds (hardcoded constants per spec scope cuts)
COVERAGE_FLOOR = 0.80
RISK_CEILING = 0.30
LINES_CEILING = 50


@pytest.fixture
def folder_with_artifacts(tmp_path: Path):
    """A pipeline folder with the artifacts F15 inspects."""
    folder = tmp_path / "feature-x"
    folder.mkdir()
    return folder


def _write_coverage_map(folder: Path, files_map: dict[str, float]):
    (folder / "coverage_map.json").write_text(
        json.dumps({"_method": "graph_approx_v1", "files": files_map})
    )


def _write_grill_summary(folder: Path, total_changed_lines: int, max_risk_score: float):
    (folder / "01-grill.md").write_text(
        f"# Grill summary\n\n"
        f"<!-- pipette-meta total_changed_lines={total_changed_lines} max_risk_score={max_risk_score} -->\n"
        f"...\n"
    )


def test_f15_auto_pass_when_all_thresholds_met(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.95, "src/bar.py": 0.88})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=20, max_risk_score=0.10)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is True
    assert decision.reason == "heuristic_auto_pass"


def test_f15_falls_through_on_low_coverage(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.50})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=10, max_risk_score=0.10)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is False
    assert decision.reason == "coverage_below_80"


def test_f15_falls_through_on_high_risk(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.95})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=10, max_risk_score=0.50)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is False
    assert decision.reason == "risk_above_30"


def test_f15_falls_through_on_large_diff(folder_with_artifacts: Path):
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.95})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=200, max_risk_score=0.10)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is False
    assert decision.reason == "lines_above_50"


def test_f15_falls_through_on_malformed_coverage(folder_with_artifacts: Path):
    """F15 + F3 dependency: malformed coverage data → fall through with logged reason."""
    from tools.pipette.orchestrator import step3_heuristic_decision

    (folder_with_artifacts / "coverage_map.json").write_text("{not json}")
    _write_grill_summary(folder_with_artifacts, total_changed_lines=10, max_risk_score=0.10)
    decision = step3_heuristic_decision(folder=folder_with_artifacts)
    assert decision.auto_pass is False
    assert decision.reason == "coverage_malformed"


def test_f15_emits_autopass_rejected_trace_event(folder_with_artifacts: Path):
    """Per spec enhancement: each fall-through writes a structured event."""
    from tools.pipette.orchestrator import step3_heuristic_decision

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.40})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=10, max_risk_score=0.10)
    step3_heuristic_decision(folder=folder_with_artifacts, write_trace=True)
    line = (folder_with_artifacts / "trace.jsonl").read_text().strip().splitlines()[-1]
    rec = json.loads(line)
    assert rec["event"] == "autopass_rejected"
    assert rec["reason"] == "coverage_below_80"


def test_f14_lite_mode_overrides_f15_unconditionally(folder_with_artifacts: Path):
    """Spec enhancement: lite mode is an absolute manual override.
    Even synthetic high-risk-score input that would fail F15 must still
    bypass Step 3 in lite mode."""
    from tools.pipette.orchestrator import should_run_step3

    _write_coverage_map(folder_with_artifacts, {"src/foo.py": 0.40})
    _write_grill_summary(folder_with_artifacts, total_changed_lines=999, max_risk_score=0.99)
    # Lite mode: never run Step 3, regardless of heuristic.
    assert should_run_step3(folder=folder_with_artifacts, lite_mode=True) is False
    # Default: F15 fall-through → run Step 3.
    assert should_run_step3(folder=folder_with_artifacts, lite_mode=False) is True


def test_lite_mode_runs_correct_step_subset(folder_with_artifacts: Path, monkeypatch: pytest.MonkeyPatch):
    """Lite path runs Steps 0, 1, 2, 4, 5, 6, 7 — never Step 3."""
    from tools.pipette.orchestrator import lite_pipeline_steps
    steps = lite_pipeline_steps()
    assert 3 not in steps
    assert {0, 1, 2, 4, 5, 6, 7}.issubset(set(steps))
