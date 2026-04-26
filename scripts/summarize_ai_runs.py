#!/usr/bin/env python3
"""CLI for analytics summary. Production logic lives in analytics.run_summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/summarize_ai_runs.py` to find the analytics package at
# the repo root. (`python -m scripts.summarize_ai_runs` works without this.)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytics.run_summary import build_summary_payload  # noqa: E402
# Re-exported so any transitional caller still importing from this module path
# keeps working until Task 5 lands. Removed once main.py is updated.
from analytics.run_summary import build_learner_summary_payload  # noqa: F401, E402


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
