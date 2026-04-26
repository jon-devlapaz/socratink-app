"""Production analytics: summary payload builders for /api/analytics/* endpoints.

Pure aggregation over the extract and drill JSONL logs. No request objects,
no CLI concerns. The CLI lives in scripts/summarize_ai_runs.py and re-imports
from here.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from analytics._metrics import (
    latest_timestamp,
    parse_timestamp,
    pct,
    safe_mean,
    top_counter,
)
from analytics.learner_summary import learner_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
EXTRACT_LOG = LOG_DIR / "extract-runs.jsonl"
DRILL_LOG = LOG_DIR / "drill-runs.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []

    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                rows.append(
                    {
                        "status": "error",
                        "error_type": "log_parse_error",
                        "reason": f"Invalid JSONL at {path.name}:{line_number}",
                    }
                )
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def extract_summary(rows: list[dict]) -> dict:
    success_rows = [row for row in rows if row.get("status") == "success"]
    error_rows = [row for row in rows if row.get("status") == "error"]

    architecture = Counter(
        row.get("architecture_type") or "unknown" for row in success_rows
    )
    difficulty = Counter(row.get("difficulty") or "unknown" for row in success_rows)
    error_types = Counter(row.get("error_type") or "unknown" for row in error_rows)
    source_titles = Counter(
        row.get("source_title") or "unknown" for row in success_rows
    )

    return {
        "total_runs": len(rows),
        "success_count": len(success_rows),
        "error_count": len(error_rows),
        "success_rate": pct(len(success_rows), len(rows)),
        "avg_duration_ms": safe_mean(
            [row.get("duration_ms", 0) for row in success_rows]
        ),
        "avg_cluster_count": safe_mean(
            [row.get("cluster_count", 0) for row in success_rows]
        ),
        "avg_backbone_count": safe_mean(
            [row.get("backbone_count", 0) for row in success_rows]
        ),
        "avg_subnode_count": safe_mean(
            [row.get("subnode_count", 0) for row in success_rows]
        ),
        "low_density_rate": pct(
            sum(1 for row in success_rows if row.get("low_density") is True),
            len(success_rows),
        ),
        "latest_run_at": latest_timestamp(rows),
        "latest_success_at": latest_timestamp(success_rows),
        "latest_error_at": latest_timestamp(error_rows),
        "architecture_distribution": architecture,
        "difficulty_distribution": difficulty,
        "error_types": error_types,
        "top_sources": top_counter(source_titles),
    }


def drill_summary(rows: list[dict]) -> dict:
    success_rows = [row for row in rows if row.get("status") == "success"]
    error_rows = [row for row in rows if row.get("status") == "error"]
    turn_rows = [row for row in success_rows if row.get("session_phase") == "turn"]
    attempt_turns = [row for row in turn_rows if row.get("answer_mode") == "attempt"]
    help_turns = [row for row in turn_rows if row.get("answer_mode") == "help_request"]
    classified_turns = [row for row in attempt_turns if row.get("classification")]

    classification = Counter(
        row.get("classification") or "none" for row in classified_turns
    )
    routing = Counter(row.get("routing") or "none" for row in turn_rows)
    node_types = Counter(row.get("node_type") or "unknown" for row in turn_rows)
    answer_modes = Counter(row.get("answer_mode") or "none" for row in turn_rows)
    help_request_reasons = Counter(
        row.get("help_request_reason") or "none" for row in help_turns
    )
    response_tiers = Counter(
        str(row.get("response_tier"))
        for row in attempt_turns
        if row.get("response_tier") is not None
    )
    response_bands = Counter(
        row.get("response_band") or "none"
        for row in attempt_turns
        if row.get("response_band")
    )
    terminations = Counter(
        row.get("termination_reason") or "none"
        for row in success_rows
        if row.get("session_terminated")
    )
    error_types = Counter(row.get("error_type") or "unknown" for row in error_rows)
    run_modes = Counter(row.get("run_mode") or "default" for row in turn_rows)

    solid_turns = sum(
        1 for row in classified_turns if row.get("classification") == "solid"
    )
    non_solid_next = sum(
        1
        for row in classified_turns
        if row.get("routing") == "NEXT" and row.get("classification") != "solid"
    )
    force_advanced = sum(
        1 for row in classified_turns if row.get("force_advanced") is True
    )
    attempt_force_advanced = sum(
        1 for row in attempt_turns if row.get("force_advanced") is True
    )
    help_force_advanced = sum(
        1 for row in help_turns if row.get("force_advanced") is True
    )
    one_turn_solids = sum(
        1
        for row in classified_turns
        if row.get("classification") == "solid" and row.get("probe_count_in", 0) == 0
    )
    reward_emitted = sum(
        1 for row in attempt_turns if row.get("ux_reward_emitted") is True
    )

    sessions: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in turn_rows:
        session_key = (
            str(row.get("concept_id") or "unknown"),
            str(row.get("node_id") or "unknown"),
            str(row.get("session_start_iso") or "missing"),
        )
        sessions[session_key].append(row)
    help_only_sessions = sum(
        1
        for session_rows in sessions.values()
        if session_rows
        and all(row.get("answer_mode") == "help_request" for row in session_rows)
    )

    by_node: dict[str, dict] = defaultdict(
        lambda: {
            "label": "",
            "turns": 0,
            "solid": 0,
            "misconception": 0,
            "force_advanced": 0,
        }
    )
    by_cluster: dict[str, dict] = defaultdict(
        lambda: {"turns": 0, "solid": 0, "misconception": 0, "force_advanced": 0}
    )
    by_node_type: dict[str, dict] = defaultdict(
        lambda: {"turns": 0, "solid": 0, "non_solid": 0, "force_advanced": 0}
    )

    for row in classified_turns:
        node_id = row.get("node_id") or "unknown"
        node_type = row.get("node_type") or "unknown"
        cluster_id = row.get("cluster_id") or "none"

        by_node[node_id]["label"] = row.get("node_label") or ""
        by_node[node_id]["turns"] += 1
        by_node_type[node_type]["turns"] += 1
        by_cluster[cluster_id]["turns"] += 1

        if row.get("classification") == "solid":
            by_node[node_id]["solid"] += 1
            by_node_type[node_type]["solid"] += 1
            by_cluster[cluster_id]["solid"] += 1
        else:
            by_node_type[node_type]["non_solid"] += 1

        if row.get("classification") == "misconception":
            by_node[node_id]["misconception"] += 1
            by_cluster[cluster_id]["misconception"] += 1

        if row.get("force_advanced") is True:
            by_node[node_id]["force_advanced"] += 1
            by_node_type[node_type]["force_advanced"] += 1
            by_cluster[cluster_id]["force_advanced"] += 1

    hotspot_nodes = []
    for node_id, stats in by_node.items():
        turns = stats["turns"]
        if turns < 2:
            continue
        hotspot_nodes.append(
            {
                "node_id": node_id,
                "label": stats["label"],
                "turns": turns,
                "solid_rate": pct(stats["solid"], turns),
                "misconception_rate": pct(stats["misconception"], turns),
                "force_advance_rate": pct(stats["force_advanced"], turns),
            }
        )
    hotspot_nodes.sort(
        key=lambda row: (
            -row["force_advance_rate"],
            -row["misconception_rate"],
            row["solid_rate"],
        )
    )

    hotspot_clusters = []
    for cluster_id, stats in by_cluster.items():
        turns = stats["turns"]
        if turns < 2 or cluster_id == "none":
            continue
        hotspot_clusters.append(
            {
                "cluster_id": cluster_id,
                "turns": turns,
                "solid_rate": pct(stats["solid"], turns),
                "misconception_rate": pct(stats["misconception"], turns),
                "force_advance_rate": pct(stats["force_advanced"], turns),
            }
        )
    hotspot_clusters.sort(
        key=lambda row: (
            -row["force_advance_rate"],
            -row["misconception_rate"],
            row["solid_rate"],
        )
    )

    node_type_benchmarks = []
    for node_type, stats in sorted(by_node_type.items()):
        turns = stats["turns"]
        if turns == 0:
            continue
        node_type_benchmarks.append(
            {
                "node_type": node_type,
                "turns": turns,
                "solid_rate": pct(stats["solid"], turns),
                "non_solid_rate": pct(stats["non_solid"], turns),
                "force_advance_rate": pct(stats["force_advanced"], turns),
            }
        )

    return {
        "total_runs": len(rows),
        "success_count": len(success_rows),
        "error_count": len(error_rows),
        "success_rate": pct(len(success_rows), len(rows)),
        "turn_count": len(turn_rows),
        "attempt_turn_count": len(attempt_turns),
        "help_turn_count": len(help_turns),
        "classified_turn_count": len(classified_turns),
        "avg_duration_ms": safe_mean(
            [row.get("duration_ms", 0) for row in success_rows]
        ),
        "avg_attempt_learner_chars": safe_mean(
            [row.get("latest_learner_chars", 0) for row in attempt_turns]
        ),
        "avg_help_learner_chars": safe_mean(
            [row.get("latest_learner_chars", 0) for row in help_turns]
        ),
        "latest_run_at": latest_timestamp(rows),
        "latest_turn_at": latest_timestamp(turn_rows),
        "latest_success_at": latest_timestamp(success_rows),
        "latest_error_at": latest_timestamp(error_rows),
        "classification_distribution": classification,
        "routing_distribution": routing,
        "node_type_distribution": node_types,
        "answer_mode_distribution": answer_modes,
        "help_request_reason_distribution": help_request_reasons,
        "run_mode_distribution": run_modes,
        "response_tier_distribution": response_tiers,
        "response_band_distribution": response_bands,
        "termination_distribution": terminations,
        "error_types": error_types,
        "attempt_rate": pct(len(attempt_turns), len(turn_rows)),
        "help_request_rate": pct(len(help_turns), len(turn_rows)),
        "solid_rate": pct(solid_turns, len(classified_turns)),
        "non_solid_next_rate": pct(non_solid_next, len(classified_turns)),
        "force_advance_rate": pct(force_advanced, len(classified_turns)),
        "attempt_force_advance_rate": pct(attempt_force_advanced, len(attempt_turns)),
        "help_force_advance_rate": pct(help_force_advanced, len(help_turns)),
        "one_turn_solid_rate": pct(one_turn_solids, len(classified_turns)),
        "reward_emit_rate": pct(reward_emitted, len(attempt_turns)),
        "help_only_session_count": help_only_sessions,
        "hotspot_nodes": hotspot_nodes[:5],
        "hotspot_clusters": hotspot_clusters[:5],
        "node_type_benchmarks": node_type_benchmarks,
    }


def recent_events(
    extract_rows: list[dict], drill_rows: list[dict], limit: int = 12
) -> list[dict]:
    events: list[dict] = []

    for row in extract_rows:
        events.append(
            {
                "timestamp": row.get("timestamp"),
                "stage": "extract",
                "status": row.get("status"),
                "title": row.get("source_title")
                or row.get("fixture_title")
                or "Extraction",
                "summary": row.get("reason")
                or row.get("architecture_type")
                or "Extraction run",
                "run_mode": row.get("run_mode") or "default",
                "fixture_id": row.get("fixture_id"),
            }
        )

    for row in drill_rows:
        events.append(
            {
                "timestamp": row.get("timestamp"),
                "stage": "drill",
                "status": row.get("status"),
                "title": row.get("node_label") or row.get("node_id") or "Drill turn",
                "summary": row.get("reason")
                or row.get("classification")
                or row.get("routing")
                or "Drill turn",
                "run_mode": row.get("run_mode") or "default",
                "fixture_id": row.get("fixture_id"),
            }
        )

    events.sort(key=lambda row: parse_timestamp(row.get("timestamp")), reverse=True)
    return events[:limit]


def build_summary_payload() -> dict:
    extract_rows = load_jsonl(EXTRACT_LOG)
    drill_rows = load_jsonl(DRILL_LOG)
    extract_data = extract_summary(extract_rows)
    drill_data = drill_summary(drill_rows)

    return {
        "extract": extract_data,
        "drill": drill_data,
        "recent_events": recent_events(extract_rows, drill_rows),
        "paths": {
            "extract_log": str(EXTRACT_LOG),
            "drill_log": str(DRILL_LOG),
        },
    }


def build_learner_summary_payload(concept_ids: list[str] | None = None) -> dict:
    drill_rows = load_jsonl(DRILL_LOG)
    learner_data = learner_summary(drill_rows, concept_ids)
    return {
        **learner_data,
        "paths": {
            "drill_log": str(DRILL_LOG),
        },
    }
