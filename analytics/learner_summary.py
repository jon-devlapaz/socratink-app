"""Learner-facing summary: cadence, retrieval habits, conversion history.

Aggregates drill telemetry rows into the payload shape consumed by the
/api/analytics/learner-runs endpoint. Pure aggregation — no IO, no request
objects. Optional concept_ids filter narrows the input rows before all
downstream calculations.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from analytics._metrics import latest_timestamp, parse_timestamp, pct


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
