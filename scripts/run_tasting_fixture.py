#!/usr/bin/env python3
# BML: Build — runs extract + drill against a fixture in the terminal.
# Use for local validation of AI pipeline behavior before merge.
# Telemetry tagged run_mode=fixture to distinguish from real sessions.

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_service import DrillTurnResult, drill_chat, extract_knowledge_map

FIXTURE_DIR = REPO_ROOT / "public/data/taste-fixtures"


def load_fixture(fixture_ref: str) -> dict:
    candidate = Path(fixture_ref)
    if candidate.is_file():
        return json.loads(candidate.read_text(encoding="utf-8"))

    fixture_path = FIXTURE_DIR / f"{fixture_ref}.json"
    if fixture_path.is_file():
        return json.loads(fixture_path.read_text(encoding="utf-8"))

    raise FileNotFoundError(f"Fixture not found: {fixture_ref}")


def list_fixtures() -> list[Path]:
    if not FIXTURE_DIR.is_dir():
        return []
    return sorted(FIXTURE_DIR.glob("*.json"))


def resolve_node(knowledge_map: dict, node_id: str | None) -> dict:
    target_id = node_id or "core-thesis"
    metadata = knowledge_map.get("metadata") or {}

    if target_id == "core-thesis":
        mechanism = metadata.get("core_thesis") or metadata.get("thesis") or ""
        return {
            "id": "core-thesis",
            "label": "Core Thesis",
            "mechanism": mechanism,
            "type": "core",
        }

    for backbone in knowledge_map.get("backbone", []):
        if isinstance(backbone, dict) and backbone.get("id") == target_id:
            principle = backbone.get("principle") or ""
            return {
                "id": target_id,
                "label": principle[:120] if principle else target_id,
                "mechanism": principle,
                "type": "backbone",
            }

    for cluster in knowledge_map.get("clusters", []):
        if not isinstance(cluster, dict):
            continue
        if cluster.get("id") == target_id:
            return {
                "id": target_id,
                "label": cluster.get("label") or target_id,
                "mechanism": cluster.get("description") or "",
                "type": "cluster",
            }
        for subnode in cluster.get("subnodes", []):
            if isinstance(subnode, dict) and subnode.get("id") == target_id:
                return {
                    "id": target_id,
                    "label": subnode.get("label") or target_id,
                    "mechanism": subnode.get("mechanism") or "",
                    "type": "subnode",
                }

    raise KeyError(
        f"Could not resolve node_id={target_id} from extracted knowledge map."
    )


def flatten_nodes(knowledge_map: dict) -> list[dict]:
    rows = [
        {
            "id": "core-thesis",
            "type": "core",
            "label": "Core Thesis",
        }
    ]
    for backbone in knowledge_map.get("backbone", []):
        if isinstance(backbone, dict):
            rows.append(
                {
                    "id": backbone.get("id") or "unknown",
                    "type": "backbone",
                    "label": (backbone.get("principle") or "Backbone")[:120],
                }
            )
    for cluster in knowledge_map.get("clusters", []):
        if not isinstance(cluster, dict):
            continue
        rows.append(
            {
                "id": cluster.get("id") or "unknown",
                "type": "cluster",
                "label": cluster.get("label") or "Cluster",
            }
        )
        for subnode in cluster.get("subnodes", []):
            if isinstance(subnode, dict):
                rows.append(
                    {
                        "id": subnode.get("id") or "unknown",
                        "type": "subnode",
                        "label": subnode.get("label") or "Subnode",
                    }
                )
    return rows


def print_map_summary(knowledge_map: dict) -> None:
    metadata = knowledge_map.get("metadata") or {}
    print("\n== Extraction Summary ==")
    print(
        f"Title: {metadata.get('source_title') or metadata.get('title') or 'unknown'}"
    )
    print(f"Architecture: {metadata.get('architecture_type') or 'unknown'}")
    print(f"Difficulty: {metadata.get('difficulty') or 'unknown'}")
    print(f"Backbone count: {len(knowledge_map.get('backbone') or [])}")
    print(f"Cluster count: {len(knowledge_map.get('clusters') or [])}")
    print(
        "Subnode count: "
        f"{sum(len(cluster.get('subnodes') or []) for cluster in (knowledge_map.get('clusters') or []) if isinstance(cluster, dict))}"
    )
    print("\n== Available Nodes ==")
    for row in flatten_nodes(knowledge_map):
        print(f"- {row['id']} [{row['type']}]: {row['label']}")


def print_scripted_answers(scripted_answers: list[dict]) -> None:
    print("\n== Scripted Answers ==")
    for idx, answer in enumerate(scripted_answers, start=1):
        preview = " ".join((answer.get("input") or "").split())
        if len(preview) > 95:
            preview = preview[:92] + "..."
        print(f"{idx}. {answer.get('label', answer.get('id', idx))}: {preview}")


def answer_expectations(answer: dict) -> str:
    parts: list[str] = []
    if answer.get("expected_answer_mode"):
        parts.append(f"mode={answer['expected_answer_mode']}")
    if answer.get("expected_classification"):
        parts.append(f"classification={answer['expected_classification']}")
    if answer.get("expected_routing"):
        parts.append(f"routing={answer['expected_routing']}")
    return ", ".join(parts) if parts else "no expectation recorded"


def select_scripted_answer(scripted_answers: list[dict], token: str) -> dict | None:
    normalized = token.strip().lower()
    if not normalized:
        return None
    if normalized.isdigit():
        index = int(normalized) - 1
        if 0 <= index < len(scripted_answers):
            return scripted_answers[index]
    for answer in scripted_answers:
        if normalized in {
            str(answer.get("id", "")).lower(),
            str(answer.get("label", "")).lower(),
        }:
            return answer
    return None


def render_turn_result(result: DrillTurnResult, answer: dict | None = None) -> None:
    print("\n== Drill Result ==")
    print(f"answer_mode: {result.get('answer_mode')}")
    print(f"score_eligible: {result.get('score_eligible')}")
    print(f"help_request_reason: {result.get('help_request_reason')}")
    print(f"classification: {result.get('classification')}")
    print(f"routing: {result.get('routing')}")
    print(f"response_tier: {result.get('response_tier')}")
    print(f"response_band: {result.get('response_band')}")
    print(f"probe_count: {result.get('probe_count')}")
    print(f"attempt_turn_count: {result.get('attempt_turn_count')}")
    print(f"help_turn_count: {result.get('help_turn_count')}")
    if answer:
        print(f"expected: {answer_expectations(answer)}")
    print("\nTutor:")
    print(result.get("agent_response") or "")


def scripted_sequence_items(
    scripted_answers: list[dict], sequence: str | None
) -> list[dict]:
    if not sequence:
        return []
    if sequence.strip().lower() == "all":
        return scripted_answers

    selected: list[dict] = []
    for token in sequence.split(","):
        answer = select_scripted_answer(scripted_answers, token)
        if not answer:
            raise ValueError(f"Unknown scripted answer in sequence: {token.strip()}")
        selected.append(answer)
    return selected


def run_fixture(args: argparse.Namespace) -> int:
    fixture = load_fixture(args.fixture)
    fixture_id = fixture.get("id") or Path(args.fixture).stem
    fixture_title = fixture.get("title") or fixture_id
    scripted_answers = fixture.get("scripted_answers") or []
    concept_id = (
        f"fixture-{fixture_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    )

    base_telemetry = {
        "run_mode": "fixture",
        "fixture_id": fixture_id,
        "fixture_title": fixture_title,
        "sandbox": True,
    }

    print(f"Running fixture: {fixture_title}")
    # extract_knowledge_map now returns a ProvisionalMap (Pydantic).
    # drill_chat and the dict-walking helpers in this script still expect a
    # dict, so dump it. When drill_chat migrates through the seam too,
    # update both call sites at once.
    provisional_map = extract_knowledge_map(
        fixture["source_text"],
        api_key=args.api_key,
        telemetry_context=base_telemetry,
    )
    knowledge_map = provisional_map.model_dump()
    print_map_summary(knowledge_map)

    node = resolve_node(
        knowledge_map, args.node or fixture.get("preferred_start_node_id")
    )
    print("\n== Drill Target ==")
    print(f"id: {node['id']}")
    print(f"type: {node['type']}")
    print(f"label: {node['label']}")

    state = {
        "messages": [],
        "probe_count": 0,
        "nodes_drilled": 0,
        "attempt_turn_count": 0,
        "help_turn_count": 0,
        "session_start_iso": datetime.now(timezone.utc).isoformat(),
    }

    init_result = drill_chat(
        knowledge_map=knowledge_map,
        concept_id=concept_id,
        node_id=node["id"],
        node_label=node["label"],
        node_mechanism=node["mechanism"],
        messages=[],
        session_phase="init",
        probe_count=0,
        nodes_drilled=0,
        attempt_turn_count=0,
        help_turn_count=0,
        session_start_iso=state["session_start_iso"],
        api_key=args.api_key,
        telemetry_context=base_telemetry,
    )
    print("\n== Opening Prompt ==")
    print(init_result["agent_response"])
    state["messages"].append(
        {"role": "assistant", "content": init_result["agent_response"]}
    )

    auto_answers = scripted_sequence_items(scripted_answers, args.sequence)
    auto_index = 0

    while True:
        print_scripted_answers(scripted_answers)
        if auto_answers and auto_index < len(auto_answers):
            chosen = auto_answers[auto_index]
            auto_index += 1
            print(f"\n[auto] {chosen.get('label')}: {chosen.get('input')}")
            user_text = chosen.get("input") or ""
        else:
            print(
                "\nCommands: number = scripted answer, m = manual answer, l = list answers, q = quit"
            )
            command = input("> ").strip()
            if command.lower() == "q":
                return 0
            if command.lower() == "l":
                continue
            if command.lower() == "m":
                print("Enter learner answer. Submit an empty line to cancel.")
                user_text = input("manual> ").strip()
                chosen = None
                if not user_text:
                    continue
            else:
                chosen = select_scripted_answer(scripted_answers, command)
                if not chosen:
                    print("Unknown command or scripted answer.")
                    continue
                user_text = chosen.get("input") or ""
                print(f"\n[selected] {chosen.get('label')}: {user_text}")

        state["messages"].append({"role": "user", "content": user_text})
        turn_telemetry = dict(base_telemetry)
        if chosen:
            turn_telemetry["scripted_answer_id"] = chosen.get("id")
            turn_telemetry["scripted_answer_label"] = chosen.get("label")
        else:
            turn_telemetry["scripted_answer_id"] = None
            turn_telemetry["scripted_answer_label"] = "manual"

        result = drill_chat(
            knowledge_map=knowledge_map,
            concept_id=concept_id,
            node_id=node["id"],
            node_label=node["label"],
            node_mechanism=node["mechanism"],
            messages=state["messages"],
            session_phase="turn",
            probe_count=state["probe_count"],
            nodes_drilled=state["nodes_drilled"],
            attempt_turn_count=state["attempt_turn_count"],
            help_turn_count=state["help_turn_count"],
            session_start_iso=state["session_start_iso"],
            api_key=args.api_key,
            telemetry_context=turn_telemetry,
        )
        render_turn_result(result, chosen)
        state["messages"].append(
            {"role": "assistant", "content": result["agent_response"]}
        )
        state["probe_count"] = result.get("probe_count", state["probe_count"])
        state["nodes_drilled"] = result.get("nodes_drilled", state["nodes_drilled"])
        state["attempt_turn_count"] = result.get(
            "attempt_turn_count", state["attempt_turn_count"]
        )
        state["help_turn_count"] = result.get(
            "help_turn_count", state["help_turn_count"]
        )

        if result.get("routing") == "NEXT" or result.get("session_terminated"):
            print(
                "\nFixture drill resolved. Start the script again for a fresh sandbox run."
            )
            return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an internal tasting fixture in the terminal."
    )
    parser.add_argument(
        "fixture",
        nargs="?",
        default="action-potential-core",
        help="Fixture id or path to a fixture JSON file.",
    )
    parser.add_argument(
        "--list", action="store_true", help="List available fixtures and exit."
    )
    parser.add_argument(
        "--node", help="Override the fixture's preferred start node id."
    )
    parser.add_argument(
        "--sequence",
        help="Comma-separated scripted answer ids/labels to auto-run, or 'all' to replay every scripted answer.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY"),
        help="Gemini API key override.",
    )
    args = parser.parse_args()

    if args.list:
        fixtures = list_fixtures()
        if not fixtures:
            print("No fixtures found.")
            return 0
        for fixture_path in fixtures:
            print(fixture_path.stem)
        return 0

    try:
        return run_fixture(args)
    except KeyboardInterrupt:
        print("\nAborted.")
        return 130
    except Exception as err:
        print(f"Fixture run failed: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
