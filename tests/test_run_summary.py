"""Characterization tests for the analytics summary payload builders.

These tests pin current behavior so the Phase 1 extraction
(scripts/summarize_ai_runs.py -> analytics/run_summary.py) can be
verified safely. Behavior must not change between this commit and
the post-extraction commit.

Fixtures contain >=2 rows for any quantity that drives a ratio or
average so a mean/sum swap or n/d swap would not silently pass.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# NOTE: this import path will change in Task 3 to
# `from analytics.run_summary import ...` — that swap is the verification.
from scripts.summarize_ai_runs import (
    build_summary_payload,
    build_learner_summary_payload,
)


EXTRACT_FIXTURE = [
    {
        "timestamp": "2026-04-20T10:00:00Z",
        "status": "success",
        "architecture_type": "linear",
        "difficulty": "intro",
        "duration_ms": 1200,
        "cluster_count": 3,
        "backbone_count": 5,
        "subnode_count": 8,
        "low_density": False,
        "source_title": "Photosynthesis primer",
    },
    {
        "timestamp": "2026-04-20T10:30:00Z",
        "status": "success",
        "architecture_type": "branching",
        "difficulty": "advanced",
        "duration_ms": 800,
        "cluster_count": 4,
        "backbone_count": 6,
        "subnode_count": 10,
        "low_density": True,
        "source_title": "Cellular respiration",
    },
    {
        "timestamp": "2026-04-21T11:00:00Z",
        "status": "error",
        "error_type": "schema_validation",
        "reason": "missing field",
    },
]

DRILL_FIXTURE = [
    {
        "timestamp": "2026-04-22T09:00:00Z",
        "status": "success",
        "session_phase": "turn",
        "answer_mode": "attempt",
        "classification": "solid",
        "routing": "NEXT",
        "node_id": "n1",
        "node_label": "Light reactions",
        "node_type": "mechanism",
        "cluster_id": "c1",
        "concept_id": "concept-a",
        "session_start_iso": "2026-04-22T09:00:00Z",
        "duration_ms": 800,
        "latest_learner_chars": 240,
    },
    {
        "timestamp": "2026-04-22T09:05:00Z",
        "status": "success",
        "session_phase": "turn",
        "answer_mode": "help_request",
        "help_request_reason": "stuck",
        "node_id": "n2",
        "node_label": "Calvin cycle",
        "node_type": "mechanism",
        "cluster_id": "c1",
        "concept_id": "concept-a",
        "session_start_iso": "2026-04-22T09:00:00Z",
        "duration_ms": 600,
        "latest_learner_chars": 60,
    },
    {
        "timestamp": "2026-04-23T10:00:00Z",
        "status": "success",
        "session_phase": "turn",
        "answer_mode": "attempt",
        "classification": "misconception",
        "routing": "REPAIR",
        "node_id": "n3",
        "node_label": "Mitochondrial transport",
        "node_type": "mechanism",
        "cluster_id": "c2",
        "concept_id": "concept-b",
        "session_start_iso": "2026-04-23T10:00:00Z",
        "duration_ms": 1200,
        "latest_learner_chars": 180,
    },
]


@pytest.fixture
def synthetic_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Write fixture JSONL into tmp dir and rebind module constants.

    Returns the actual path objects used so tests can assert on them.
    """
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    extract_log = logs_dir / "extract-runs.jsonl"
    drill_log = logs_dir / "drill-runs.jsonl"
    extract_log.write_text(
        "\n".join(json.dumps(row) for row in EXTRACT_FIXTURE) + "\n",
        encoding="utf-8",
    )
    drill_log.write_text(
        "\n".join(json.dumps(row) for row in DRILL_FIXTURE) + "\n",
        encoding="utf-8",
    )
    # Rebind whichever module currently owns the constants.
    # In Task 3 this import path changes, but the symbol names stay the same.
    import scripts.summarize_ai_runs as mod
    monkeypatch.setattr(mod, "EXTRACT_LOG", extract_log)
    monkeypatch.setattr(mod, "DRILL_LOG", drill_log)
    monkeypatch.setattr(mod, "LOG_DIR", logs_dir)
    return {"logs_dir": logs_dir, "extract_log": extract_log, "drill_log": drill_log}


def test_build_summary_payload_has_top_level_keys(synthetic_logs: dict[str, Path]) -> None:
    payload = build_summary_payload()
    assert set(payload.keys()) == {"extract", "drill", "recent_events", "paths"}


def test_build_summary_payload_extract_aggregates(synthetic_logs: dict[str, Path]) -> None:
    payload = build_summary_payload()
    extract = payload["extract"]
    assert extract["total_runs"] == 3
    assert extract["success_count"] == 2
    assert extract["error_count"] == 1
    # 2 success out of 3 total — non-trivial ratio.
    assert extract["success_rate"] == pytest.approx(2 / 3 * 100)
    # mean(1200, 800) = 1000; this distinguishes mean from sum (would be 2000)
    # or from picking-the-first-value (would be 1200).
    assert extract["avg_duration_ms"] == pytest.approx(1000.0)
    # 1 of 2 success rows has low_density=True.
    assert extract["low_density_rate"] == pytest.approx(50.0)


def test_build_summary_payload_drill_aggregates(synthetic_logs: dict[str, Path]) -> None:
    payload = build_summary_payload()
    drill = payload["drill"]
    assert drill["turn_count"] == 3
    assert drill["attempt_turn_count"] == 2
    assert drill["help_turn_count"] == 1
    assert drill["classified_turn_count"] == 2
    # 1 solid out of 2 classified — non-trivial ratio.
    assert drill["solid_rate"] == pytest.approx(50.0)
    # 2 attempts out of 3 turns.
    assert drill["attempt_rate"] == pytest.approx(2 / 3 * 100)


def test_build_summary_payload_paths_match_monkeypatched(
    synthetic_logs: dict[str, Path],
) -> None:
    payload = build_summary_payload()
    # Exact equality — proves the function reports the actual paths it read,
    # not a default or empty string.
    assert payload["paths"]["extract_log"] == str(synthetic_logs["extract_log"])
    assert payload["paths"]["drill_log"] == str(synthetic_logs["drill_log"])


def test_build_summary_payload_empty_logs_returns_zero_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.summarize_ai_runs as mod
    empty_extract = tmp_path / "missing-extract.jsonl"
    empty_drill = tmp_path / "missing-drill.jsonl"
    monkeypatch.setattr(mod, "EXTRACT_LOG", empty_extract)
    monkeypatch.setattr(mod, "DRILL_LOG", empty_drill)
    payload = build_summary_payload()
    assert payload["extract"]["total_runs"] == 0
    assert payload["drill"]["total_runs"] == 0
    assert payload["recent_events"] == []


def test_build_learner_summary_payload_has_top_level_keys(
    synthetic_logs: dict[str, Path],
) -> None:
    payload = build_learner_summary_payload()
    expected = {
        "retrieval_habits",
        "cadence",
        "conversion_history",
        "session_journal",
        "node_history",
        "concept_stats",
        "paths",
    }
    assert set(payload.keys()) == expected


def test_build_learner_summary_payload_filters_by_concept_id(
    synthetic_logs: dict[str, Path],
) -> None:
    payload_all = build_learner_summary_payload()
    payload_a = build_learner_summary_payload(["concept-a"])
    payload_b = build_learner_summary_payload(["concept-b"])
    payload_other = build_learner_summary_payload(["concept-zzz"])
    assert payload_all["retrieval_habits"]["turn_count"] == 3
    # concept-a contributes 2 turns (one attempt, one help_request).
    assert payload_a["retrieval_habits"]["turn_count"] == 2
    # concept-b contributes 1 turn (one attempt).
    assert payload_b["retrieval_habits"]["turn_count"] == 1
    assert payload_other["retrieval_habits"]["turn_count"] == 0


def test_build_learner_summary_payload_concept_stats_shape(
    synthetic_logs: dict[str, Path],
) -> None:
    payload = build_learner_summary_payload()
    stats_by_concept = {row["concept_id"]: row for row in payload["concept_stats"]}
    assert set(stats_by_concept.keys()) == {"concept-a", "concept-b"}

    a = stats_by_concept["concept-a"]
    assert a["turn_count"] == 2
    assert a["attempt_turn_count"] == 1
    assert a["help_turn_count"] == 1

    b = stats_by_concept["concept-b"]
    assert b["turn_count"] == 1
    assert b["attempt_turn_count"] == 1
    assert b["help_turn_count"] == 0
