#!/usr/bin/env python3
# BML: Measure — compiles extract + drill JSONL logs into operator and learner analytics.
# Imported by main.py for /api/analytics/* endpoints. Also runs standalone as CLI.

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean


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


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return (numerator / denominator) * 100


def safe_mean(values: list[float | int]) -> float:
    if not values:
        return 0.0
    return float(mean(values))


def top_counter(counter: Counter, limit: int = 5) -> list[tuple[str, int]]:
    return [(str(key), value) for key, value in counter.most_common(limit)]


def latest_timestamp(rows: list[dict]) -> str | None:
    timestamps = [row.get("timestamp") for row in rows if row.get("timestamp")]
    if not timestamps:
        return None
    return max(t for t in timestamps if t is not None)


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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


def _normalize_concept_ids(concept_ids: list[str] | None) -> set[str]:
    if not concept_ids:
        return set()
    return {
        str(concept_id).strip() for concept_id in concept_ids if str(concept_id).strip()
    }


def _filter_turn_rows(
    rows: list[dict], concept_ids: list[str] | None = None
) -> list[dict]:
    concept_filter = _normalize_concept_ids(concept_ids)
    return [
        row
        for row in rows
        if row.get("status") == "success"
        and row.get("session_phase") == "turn"
        and (not concept_filter or str(row.get("concept_id") or "") in concept_filter)
    ]


def _days_between(now: datetime, timestamp: str | None) -> int | None:
    if not timestamp:
        return None
    delta = now - parse_timestamp(timestamp)
    return max(int(delta.total_seconds() // 86400), 0)


def _journal_outcome(
    row: dict, converted_node_ids: set[tuple[str, str]]
) -> tuple[str, str]:
    concept_id = str(row.get("concept_id") or "")
    node_id = str(row.get("node_id") or "")
    key = (concept_id, node_id)
    answer_mode = row.get("answer_mode")
    classification = row.get("classification")

    if answer_mode == "help_request":
        return ("Used scaffolding", "Try this node again from memory.")
    if classification == "solid" and key in converted_node_ids:
        return (
            "Solidified on return",
            "Keep your momentum and take the next reachable node.",
        )
    if classification == "solid":
        return ("Verified understanding", "Advance to the next reachable node.")
    if classification == "misconception":
        return (
            "Misconception caught",
            "Revisit this mechanism soon while the gap is fresh.",
        )
    if classification:
        return ("Still in progress", "Return for one more clean pass.")
    return (
        "Activity logged",
        "Choose one reachable node and reconstruct it from memory.",
    )


def learner_summary(
    drill_rows: list[dict], concept_ids: list[str] | None = None
) -> dict:
    turn_rows = _filter_turn_rows(drill_rows, concept_ids)
    now = datetime.now(timezone.utc)
    recent_window = now - timedelta(days=14)
    due_threshold_days = 3

    attempt_turns = [row for row in turn_rows if row.get("answer_mode") == "attempt"]
    help_turns = [row for row in turn_rows if row.get("answer_mode") == "help_request"]
    recent_turns = [
        row
        for row in turn_rows
        if parse_timestamp(row.get("timestamp")) >= recent_window
    ]

    session_keys = {
        (
            str(row.get("concept_id") or "unknown"),
            str(row.get("node_id") or "unknown"),
            str(row.get("session_start_iso") or "missing"),
        )
        for row in turn_rows
    }
    active_days = sorted(
        {
            parse_timestamp(row.get("timestamp")).date().isoformat()
            for row in turn_rows
            if row.get("timestamp")
        }
    )
    active_days_last_7 = {
        parse_timestamp(row.get("timestamp")).date().isoformat()
        for row in turn_rows
        if row.get("timestamp")
        and parse_timestamp(row.get("timestamp")) >= now - timedelta(days=7)
    }
    active_days_last_14 = {
        parse_timestamp(row.get("timestamp")).date().isoformat()
        for row in turn_rows
        if row.get("timestamp")
        and parse_timestamp(row.get("timestamp")) >= recent_window
    }

    node_history: dict[tuple[str, str], dict] = {}
    conversion_history: list[dict] = []
    converted_node_ids: set[tuple[str, str]] = set()

    grouped_rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in turn_rows:
        key = (str(row.get("concept_id") or ""), str(row.get("node_id") or ""))
        grouped_rows[key].append(row)

    for key, rows in grouped_rows.items():
        concept_id, node_id = key
        ordered_rows = sorted(
            rows, key=lambda row: parse_timestamp(row.get("timestamp"))
        )
        history = {
            "concept_id": concept_id,
            "node_id": node_id,
            "node_label": ordered_rows[-1].get("node_label") or node_id,
            "cluster_id": ordered_rows[-1].get("cluster_id"),
            "node_type": ordered_rows[-1].get("node_type") or "unknown",
            "attempt_count": 0,
            "help_count": 0,
            "solid_count": 0,
            "non_solid_count": 0,
            "misconception_count": 0,
            "last_attempt_at": None,
            "last_help_at": None,
            "last_turn_at": None,
            "latest_classification": None,
        }
        seen_non_solid_at = None
        seen_non_solid_label = None

        for row in ordered_rows:
            timestamp = row.get("timestamp")
            history["last_turn_at"] = timestamp or history["last_turn_at"]

            if row.get("answer_mode") == "help_request":
                history["help_count"] += 1
                history["last_help_at"] = timestamp or history["last_help_at"]
                continue

            if row.get("answer_mode") != "attempt":
                continue

            history["attempt_count"] += 1
            history["last_attempt_at"] = timestamp or history["last_attempt_at"]
            classification = row.get("classification")
            history["latest_classification"] = (
                classification or history["latest_classification"]
            )

            if classification == "solid":
                history["solid_count"] += 1
                if seen_non_solid_at and key not in converted_node_ids:
                    conversion_history.append(
                        {
                            "concept_id": concept_id,
                            "node_id": node_id,
                            "node_label": history["node_label"],
                            "converted_at": timestamp,
                            "last_non_solid_at": seen_non_solid_at,
                            "previous_gap_type": seen_non_solid_label,
                        }
                    )
                    converted_node_ids.add(key)
            elif classification:
                history["non_solid_count"] += 1
                seen_non_solid_at = timestamp
                seen_non_solid_label = classification
                if classification == "misconception":
                    history["misconception_count"] += 1

        node_history[key] = history

    due_nodes = [
        {
            "concept_id": concept_id,
            "node_id": node_id,
            "node_label": stats["node_label"],
            "days_since_attempt": _days_between(now, stats["last_attempt_at"]),
            "latest_classification": stats["latest_classification"],
        }
        for (concept_id, node_id), stats in node_history.items()
        if stats["latest_classification"] not in (None, "solid")
        and (_days_between(now, stats["last_attempt_at"]) or 0) >= due_threshold_days
    ]
    due_nodes.sort(
        key=lambda row: (-(row["days_since_attempt"] or 0), row["node_label"])
    )

    conversion_history.sort(
        key=lambda row: parse_timestamp(row.get("converted_at")),
        reverse=True,
    )
    journal_rows = sorted(
        turn_rows, key=lambda row: parse_timestamp(row.get("timestamp")), reverse=True
    )[:40]
    concept_stats: dict[str, dict] = {}
    concept_sessions: dict[str, set[tuple[str, str, str]]] = defaultdict(set)

    for row in turn_rows:
        concept_id = str(row.get("concept_id") or "")
        concept_sessions[concept_id].add(
            (
                concept_id,
                str(row.get("node_id") or "unknown"),
                str(row.get("session_start_iso") or "missing"),
            )
        )
        stats = concept_stats.setdefault(
            concept_id,
            {
                "concept_id": concept_id,
                "turn_count": 0,
                "attempt_turn_count": 0,
                "help_turn_count": 0,
                "solid_attempt_count": 0,
                "latest_activity_at": None,
                "active_days_last_14": set(),
            },
        )
        stats["turn_count"] += 1
        row_timestamp = row.get("timestamp")
        if parse_timestamp(row_timestamp) > parse_timestamp(
            stats["latest_activity_at"]
        ):
            stats["latest_activity_at"] = row_timestamp
        timestamp = parse_timestamp(row.get("timestamp"))
        if timestamp >= recent_window:
            stats["active_days_last_14"].add(timestamp.date().isoformat())
        if row.get("answer_mode") == "attempt":
            stats["attempt_turn_count"] += 1
            if row.get("classification") == "solid":
                stats["solid_attempt_count"] += 1
        elif row.get("answer_mode") == "help_request":
            stats["help_turn_count"] += 1

    return {
        "retrieval_habits": {
            "turn_count": len(turn_rows),
            "attempt_turn_count": len(attempt_turns),
            "help_turn_count": len(help_turns),
            "attempt_before_help_rate": pct(len(attempt_turns), len(turn_rows)),
            "help_usage_rate": pct(len(help_turns), len(turn_rows)),
            "verified_reconstruction_rate_14d": pct(
                sum(
                    1
                    for row in recent_turns
                    if row.get("answer_mode") == "attempt"
                    and row.get("classification") == "solid"
                ),
                sum(1 for row in recent_turns if row.get("answer_mode") == "attempt"),
            ),
        },
        "cadence": {
            "window_days": 14,
            "revisit_due_days": due_threshold_days,
            "session_count": len(session_keys),
            "active_days": active_days,
            "active_days_last_7": len(active_days_last_7),
            "active_days_last_14": len(active_days_last_14),
            "overdue_revisit_count": len(due_nodes),
            "due_nodes": due_nodes[:8],
            "latest_activity_at": latest_timestamp(turn_rows),
        },
        "conversion_history": {
            "conversion_count": len(conversion_history),
            "recent_conversions": conversion_history[:24],
        },
        "session_journal": [
            {
                "timestamp": row.get("timestamp"),
                "concept_id": row.get("concept_id"),
                "node_id": row.get("node_id"),
                "node_label": row.get("node_label")
                or row.get("node_id")
                or "Untitled node",
                "cluster_id": row.get("cluster_id"),
                "classification": row.get("classification"),
                "answer_mode": row.get("answer_mode"),
                "help_request_reason": row.get("help_request_reason"),
                "outcome_label": _journal_outcome(row, converted_node_ids)[0],
                "next_action": _journal_outcome(row, converted_node_ids)[1],
                "gap_label": row.get("classification")
                if row.get("classification") not in (None, "solid")
                else None,
            }
            for row in journal_rows
        ],
        "node_history": [
            {
                **stats,
                "days_since_attempt": _days_between(now, stats["last_attempt_at"]),
            }
            for stats in sorted(
                node_history.values(),
                key=lambda row: parse_timestamp(row.get("last_turn_at")),
                reverse=True,
            )
        ],
        "concept_stats": [
            {
                **stats,
                "session_count": len(concept_sessions.get(stats["concept_id"]) or []),
                "active_days_last_14": len(stats["active_days_last_14"]),
                "attempt_before_help_rate": pct(
                    stats["attempt_turn_count"], stats["turn_count"]
                ),
                "verified_reconstruction_rate": pct(
                    stats["solid_attempt_count"], stats["attempt_turn_count"]
                ),
            }
            for stats in sorted(
                concept_stats.values(),
                key=lambda row: parse_timestamp(row.get("latest_activity_at")),
                reverse=True,
            )
        ],
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


def render_markdown(extract_data: dict, drill_data: dict) -> str:
    lines: list[str] = []

    lines.append("**AI Run Summary**")
    lines.append("")
    lines.append("**Extraction**")
    lines.append(
        f"- Runs: {extract_data['total_runs']} ({extract_data['success_count']} success, {extract_data['error_count']} error, {extract_data['success_rate']:.1f}% success)"
    )
    lines.append(f"- Avg duration: {extract_data['avg_duration_ms']:.1f} ms")
    lines.append(
        f"- Avg map size: {extract_data['avg_backbone_count']:.1f} backbone, {extract_data['avg_cluster_count']:.1f} clusters, {extract_data['avg_subnode_count']:.1f} subnodes"
    )
    lines.append(f"- Low-density success rate: {extract_data['low_density_rate']:.1f}%")
    if extract_data["architecture_distribution"]:
        lines.append(
            f"- Architecture mix: {dict(extract_data['architecture_distribution'])}"
        )
    if extract_data["difficulty_distribution"]:
        lines.append(
            f"- Difficulty mix: {dict(extract_data['difficulty_distribution'])}"
        )
    if extract_data["error_types"]:
        lines.append(f"- Error types: {dict(extract_data['error_types'])}")
    if extract_data["top_sources"]:
        lines.append(f"- Top sources: {extract_data['top_sources']}")

    lines.append("")
    lines.append("**Drill**")
    lines.append(
        f"- Runs: {drill_data['total_runs']} ({drill_data['success_count']} success, {drill_data['error_count']} error, {drill_data['success_rate']:.1f}% success)"
    )
    lines.append(
        f"- Turns: {drill_data['turn_count']} ({drill_data['attempt_turn_count']} attempts, {drill_data['help_turn_count']} help requests)"
    )
    lines.append(f"- Scored attempt turns: {drill_data['classified_turn_count']}")
    lines.append(f"- Avg duration: {drill_data['avg_duration_ms']:.1f} ms")
    lines.append(
        f"- Avg learner response length: {drill_data['avg_attempt_learner_chars']:.1f} chars on attempts, {drill_data['avg_help_learner_chars']:.1f} chars on help requests"
    )
    lines.append(f"- Attempt rate: {drill_data['attempt_rate']:.1f}%")
    lines.append(f"- Help-request rate: {drill_data['help_request_rate']:.1f}%")
    lines.append(f"- Solid rate: {drill_data['solid_rate']:.1f}%")
    lines.append(f"- Non-solid NEXT rate: {drill_data['non_solid_next_rate']:.1f}%")
    lines.append(
        f"- Force-advance rate: {drill_data['force_advance_rate']:.1f}% on scored attempts"
    )
    lines.append(
        f"- Attempt force-advance rate: {drill_data['attempt_force_advance_rate']:.1f}%"
    )
    lines.append(
        f"- Help force-advance rate: {drill_data['help_force_advance_rate']:.1f}%"
    )
    lines.append(f"- One-turn solid rate: {drill_data['one_turn_solid_rate']:.1f}%")
    lines.append(
        f"- Reward emit rate: {drill_data['reward_emit_rate']:.1f}% of attempts"
    )
    lines.append(f"- Help-only sessions: {drill_data['help_only_session_count']}")
    if drill_data["classification_distribution"]:
        lines.append(
            f"- Classification mix: {dict(drill_data['classification_distribution'])}"
        )
    if drill_data["routing_distribution"]:
        lines.append(f"- Routing mix: {dict(drill_data['routing_distribution'])}")
    if drill_data["node_type_distribution"]:
        lines.append(f"- Node-type mix: {dict(drill_data['node_type_distribution'])}")
    if drill_data["answer_mode_distribution"]:
        lines.append(
            f"- Answer-mode mix: {dict(drill_data['answer_mode_distribution'])}"
        )
    if drill_data["help_request_reason_distribution"]:
        lines.append(
            f"- Help-request reasons: {dict(drill_data['help_request_reason_distribution'])}"
        )
    if drill_data["response_tier_distribution"]:
        lines.append(
            f"- Response-tier mix: {dict(drill_data['response_tier_distribution'])}"
        )
    if drill_data["response_band_distribution"]:
        lines.append(
            f"- Response-band mix: {dict(drill_data['response_band_distribution'])}"
        )
    if drill_data["termination_distribution"]:
        lines.append(f"- Terminations: {dict(drill_data['termination_distribution'])}")
    if drill_data["error_types"]:
        lines.append(f"- Error types: {dict(drill_data['error_types'])}")

    lines.append("")
    lines.append("**Product Signals**")
    if drill_data["hotspot_nodes"]:
        lines.append("- Friction nodes:")
        for row in drill_data["hotspot_nodes"]:
            label = row["label"] or row["node_id"]
            lines.append(
                f"  - {label} ({row['node_id']}): turns={row['turns']}, solid={row['solid_rate']:.1f}%, misconception={row['misconception_rate']:.1f}%, force-advance={row['force_advance_rate']:.1f}%"
            )
    else:
        lines.append("- Friction nodes: not enough drill volume yet")

    if drill_data["hotspot_clusters"]:
        lines.append("- Friction clusters:")
        for row in drill_data["hotspot_clusters"]:
            lines.append(
                f"  - {row['cluster_id']}: turns={row['turns']}, solid={row['solid_rate']:.1f}%, misconception={row['misconception_rate']:.1f}%, force-advance={row['force_advance_rate']:.1f}%"
            )
    else:
        lines.append("- Friction clusters: not enough drill volume yet")

    if drill_data["node_type_benchmarks"]:
        lines.append("- Node-type benchmarks:")
        for row in drill_data["node_type_benchmarks"]:
            lines.append(
                f"  - {row['node_type']}: turns={row['turns']}, solid={row['solid_rate']:.1f}%, non-solid={row['non_solid_rate']:.1f}%, force-advance={row['force_advance_rate']:.1f}%"
            )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize extraction and drill telemetry logs."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of markdown.",
    )
    args = parser.parse_args()

    payload = build_summary_payload()
    extract_data = payload["extract"]
    drill_data = payload["drill"]

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print(render_markdown(extract_data, drill_data))


if __name__ == "__main__":
    main()
