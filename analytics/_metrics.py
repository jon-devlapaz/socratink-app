"""Small numerical and temporal primitives shared across the summary aggregators.

Internal to the analytics package (leading underscore). These functions have
no domain-specific knowledge — they're general-purpose helpers used by
extract_summary, drill_summary, learner_summary, and recent_events to
turn lists of rows into ratios, means, top-N tables, and parsed timestamps.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from statistics import mean


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
