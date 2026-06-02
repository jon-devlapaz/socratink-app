"""Founder-facing terminal Socratink dogfood tests."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TUI_DIR = REPO_ROOT / "scripts" / "socratink_tui"
AGENT_CONTRACTS = TUI_DIR / "pedagogical_agents" / "contracts.json"
LEARNING_CASES_DIR = TUI_DIR / "learning_cases"
LEARNING_CASES = LEARNING_CASES_DIR / "cases.jsonl"
LEARNING_CASE_TRACES = LEARNING_CASES_DIR / "traces"
BRIDGE = TUI_DIR / "bridge.py"
TUI = REPO_ROOT / "scripts" / "socratink-tui"
HARNESS = REPO_ROOT / "scripts" / "socratink-harness"
DASHBOARD = REPO_ROOT / "scripts" / "socratink-dashboard"
SCRIPT = REPO_ROOT / "tests" / "fixtures" / "socratink-tui" / "source_less_script.json"
BLOCKED_REPAIR_SCRIPT = (
    REPO_ROOT / "tests" / "fixtures" / "socratink-tui" / "blocked_repair_script.json"
)
CIRCULAR_REPAIR_SCRIPT = (
    REPO_ROOT / "tests" / "fixtures" / "socratink-tui" / "circular_repair_script.json"
)
HELP_SCRIPT = REPO_ROOT / "tests" / "fixtures" / "socratink-tui" / "help_script.json"


def run_command(
    args: list[str],
    *,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env or {})
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=30,
        env=merged_env,
    )


def test_tui_bridge_generate_route_can_use_fake_llm_without_network() -> None:
    request = {
        "concept": "Immune memory",
        "launch_attempt": "Vaccines give the immune system a preview.",
        "learner_goal": "Explain vaccines.",
        "log_raw_llm": True,
    }

    result = run_command(
        [sys.executable, str(BRIDGE), "generate-route"],
        input_text=json.dumps(request),
        env={"SOCRATINK_TUI_FAKE_LLM": "1"},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["provisional_map"]["metadata"]["core_thesis"].startswith("Immune memory")
    first_node = payload["first_node"]
    assert first_node["id"] == "c1_s1"
    assert first_node["learner_prompt"]
    assert payload["llm_call"]["provider"] == "fake"
    assert payload["llm_call"]["raw_text"]
    assert "<threshold>Vaccines give the immune system a preview.</threshold>" in (
        payload["llm_call"]["raw_prompt"]["user_prompt"]
    )


def test_tui_bridge_can_surface_retryable_route_validation_failure() -> None:
    request = {
        "concept": "Agentic engineering",
        "launch_attempt": "Agents loop over tools and feedback.",
        "learner_goal": "Get a job applying agentic engineering.",
        "route_attempt": 1,
    }

    result = run_command(
        [sys.executable, str(BRIDGE), "generate-route"],
        input_text=json.dumps(request),
        env={"SOCRATINK_TUI_FAKE_ROUTE_FAIL_ONCE": "1"},
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["error"] == "SmallestRouteCapExceeded"
    assert "copies hidden mechanism" in payload["message"]


def test_tui_bridge_repair_scaffold_uses_analogical_question_for_vague_attempt() -> None:
    request = {
        "node_label": "Core Harness Components",
        "node_mechanism": (
            "A harness captures inputs, state, actions, outputs, traces, and evaluations "
            "so agent runs can be replayed and improved."
        ),
        "learner_text": "a loop, a way to manage skills. i believe other things but dont know.",
        "gap_description": "The learner has a vague model and needs the functional purpose of a harness.",
        "evidence_goal": "The learner explains how a harness captures and replays agent behavior.",
        "blank_hint": "Name what the harness must preserve from a run.",
    }

    result = run_command(
        [sys.executable, str(BRIDGE), "repair-scaffold"],
        input_text=json.dumps(request),
        env={"SOCRATINK_TUI_FAKE_LLM": "1"},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    scaffold = payload["repair_scaffold"]
    assert scaffold["question_style"] == "analogical"
    assert "like" in scaffold["socratic_question"].lower()
    assert "what must happen for an agent to receive input" not in scaffold["socratic_question"].lower()


def test_tui_bridge_repair_dialogue_judges_bridge_readiness_without_graph_evidence() -> None:
    request = {
        "node_label": "Immune memory",
        "node_mechanism": (
            "A vaccine safely presents antigen, matching immune cells expand, "
            "memory cells remain, and those cells respond faster later."
        ),
        "gap_id": "gap-c1_s1-1",
        "missing_operation": "durable immune change after the preview",
        "before": "A safe preview presents the antigen.",
        "after": "The later immune response happens faster.",
        "learner_text": "The preview helps because it gives a preview.",
        "turn_index": 1,
    }

    result = run_command(
        [sys.executable, str(BRIDGE), "repair-dialogue"],
        input_text=json.dumps(request),
        env={"SOCRATINK_TUI_FAKE_LLM": "1"},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    judge = payload["repair_dialogue"]
    assert judge["score_eligible"] is False
    assert judge["graph_neutral"] is True
    assert judge["bridge_ready"] is False
    assert judge["echo_risk"] is True
    assert judge["next_dialogue_action"] == "probe_again"
    assert judge["support_level"] == "probe"
    assert "durable immune change after the preview" in judge["next_prompt"]


def test_socratink_tui_keeps_app_and_env_template_together() -> None:
    launcher = TUI.read_text()

    assert (TUI_DIR / "app.mjs").exists()
    assert BRIDGE.exists()
    assert (TUI_DIR / "dashboard.mjs").exists()
    assert (TUI_DIR / ".env.example").read_text().startswith("# Socratink terminal dogfood env")
    assert "scripts/socratink_tui/.env" in launcher
    assert "scripts/socratink_tui/app.mjs" in launcher
    assert "scripts/socratink_tui/dashboard.mjs" in DASHBOARD.read_text()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_tui_help_command_explains_each_prompt_without_recording_help(tmp_path: Path) -> None:
    result = run_command(
        [str(TUI), "--scripted", str(HELP_SCRIPT), "--color=never"],
        env={
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "SOCRATINK_TUI_FAKE_COLD_CLASSIFICATION": "shallow",
            "SOCRATINK_TUI_LOG_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "[Help] Concept" in result.stdout
    assert "[Help] Learner goal" in result.stdout
    assert "[Help] Launch attempt" in result.stdout
    assert "[Help] Cold attempt" in result.stdout
    assert "[Help] Repair dialogue" in result.stdout
    assert "[Help] Post-bridge transfer check" in result.stdout
    assert "[Help] Spaced re-drill" in result.stdout

    session_logs = sorted(tmp_path.glob("*/session.json"))
    assert len(session_logs) == 1
    session = json.loads(session_logs[0].read_text())
    assert session["concept"] == "Immune memory"
    assert session["learner_goal"] == "I want to explain why vaccines work."
    assert session["events"][0]["text"] == (
        "Vaccines show the immune system a safer preview so it can react faster later."
    )
    assert all("/help" not in json.dumps(event).lower() for event in session["events"])


def test_pedagogical_agent_contracts_define_truth_permissions() -> None:
    contracts = json.loads(AGENT_CONTRACTS.read_text())

    assert contracts["architecture"]["truth_contract"] == (
        "Agents propose moves. Training store records events. Derivation decides truth. "
        "Graph displays only derived evidence."
    )
    assert contracts["architecture"]["orchestrator"] == "Socratink Orchestrator"

    agents = {agent["id"]: agent for agent in contracts["agents"]}
    assert set(agents) == {
        "route",
        "cold_attempt",
        "delta",
        "repair",
        "model_bridge",
        "redrill",
        "evidence_judge",
    }
    for agent in agents.values():
        assert agent["truth_permission"] == "none"
        assert agent["may_write_events"] == []
        assert agent["required_outputs"]
        assert agent["failure_mode_to_guard"]

    assert agents["evidence_judge"]["cannot"] == [
        "mutate training store",
        "set graph state",
        "produce solidified directly",
    ]


def load_learning_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in LEARNING_CASES.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def case_by_id(cases: list[dict], case_id: str) -> dict:
    matches = [case for case in cases if case["case_id"] == case_id]
    assert len(matches) == 1
    return matches[0]


def assert_no_visible_bloom_labels(output: str) -> None:
    tokens = set(re.findall(r"[a-z]+", output.lower()))
    assert not ({
        "bloom",
        "taxonomy",
        "remember",
        "understand",
        "apply",
        "analyze",
        "evaluate",
        "create",
    } & tokens)


def test_learning_cases_are_portable_falsifiable_regressions() -> None:
    schema = json.loads((LEARNING_CASES_DIR / "schema.json").read_text())
    cases = load_learning_cases()

    assert schema["title"] == "Socratink TUI Learning Case"
    assert len(cases) == 4
    assert {case["case_type"] for case in cases} == {"regression"}
    assert {case["promotion_status"] for case in cases} == {"active_regression"}
    assert all(case["session_log"].startswith("scripts/socratink_tui/learning_cases/traces/") for case in cases)
    assert all((REPO_ROOT / case["session_log"]).is_file() for case in cases)
    assert not any(".qa-runs" in case["session_log"] for case in cases)

    case = case_by_id(cases, "evidence-hold-solid-spaced-primed-2026-05-26")
    assert case["case_id"] == "evidence-hold-solid-spaced-primed-2026-05-26"
    assert case["case_source"] == "regression_trace"
    assert case["session_log"].endswith("session.json")
    assert case["expected_invariants"] == {
        "event_order": [
            "launch_attempt",
            "route_generated",
            "cold_attempt",
            "gap_identified",
            "repair",
            "model_bridge",
            "gap_drill",
            "spacing_advanced",
            "spaced_redrill",
        ],
        "final_node_state": "primed",
        "spaced_evaluator_classification": "solid",
        "evidence_hold_required": True,
        "truth_source": "training_derivation",
    }

    repair_abandoned = case_by_id(cases, "repair-abandoned-no-model-bridge-2026-05-26")
    assert repair_abandoned["expected_invariants"] == {
        "event_order": [
            "launch_attempt",
            "route_generated",
            "cold_attempt",
            "gap_identified",
            "repair_abandoned",
        ],
        "final_node_state": "primed",
        "repair_count": 0,
        "forbidden_events": ["repair", "model_bridge", "gap_drill", "spacing_advanced", "spaced_redrill"],
        "forbidden_llm_stages": ["model_bridge", "gap_drill", "spaced_redrill"],
        "truth_source": "training_derivation",
    }

    inner_dialogue = case_by_id(cases, "inner-repair-dialogue-gates-model-bridge-2026-05-26")
    assert inner_dialogue["expected_invariants"] == {
        "event_order": [
            "launch_attempt",
            "route_generated",
            "cold_attempt",
            "gap_identified",
            "repair_dialogue_turn",
            "repair_dialogue_turn",
            "repair",
            "model_bridge",
            "post_bridge_transfer_check",
            "spacing_advanced",
            "spaced_redrill",
        ],
        "final_node_state": "primed",
        "repair_dialogue_turn_count": 2,
        "first_repair_dialogue_bridge_ready": False,
        "last_repair_dialogue_bridge_ready": True,
        "post_bridge_transfer_check_required": True,
        "spaced_evaluator_classification": "solid",
        "evidence_hold_required": True,
        "truth_source": "training_derivation",
    }

    strong_cold = case_by_id(cases, "strong-cold-skips-repair-until-spacing-2026-05-26")
    assert strong_cold["expected_invariants"] == {
        "event_order": [
            "launch_attempt",
            "route_generated",
            "cold_attempt",
            "strong_cold_path",
            "spacing_advanced",
            "spaced_redrill",
        ],
        "final_node_state": "solidified",
        "cold_evaluator_classification": "solid",
        "spaced_evaluator_classification": "solid",
        "forbidden_events": ["study_reveal", "repair", "repair_abandoned", "model_bridge", "gap_drill"],
        "forbidden_llm_stages": ["repair_scaffold", "repair_prompt", "model_bridge", "gap_drill"],
        "truth_source": "training_derivation",
    }

    for case in cases:
        assert "agent_response" not in json.dumps(case["expected_invariants"])
        assert "llm_calls" not in json.dumps(case["expected_invariants"])


def test_learning_case_replays_trace_against_expected_invariants() -> None:
    for case in load_learning_cases():
        session = json.loads((REPO_ROOT / case["session_log"]).read_text())
        first_node_id = session["route"]["first_node"]["id"]
        invariants = case["expected_invariants"]
        events = session["events"]
        event_order = [event["type"] for event in events]
        llm_stages = {call["stage"] for call in session["llm_calls"]}

        assert event_order == invariants["event_order"]
        assert session["derived"][-1]["nodes"][first_node_id]["state"] == invariants["final_node_state"]
        assert invariants["truth_source"] == "training_derivation"

        if "cold_evaluator_classification" in invariants:
            assert events[event_order.index("cold_attempt")]["evaluation"]["classification"] == (
                invariants["cold_evaluator_classification"]
            )
        if "spaced_evaluator_classification" in invariants:
            assert events[event_order.index("spaced_redrill")]["evaluation"]["classification"] == (
                invariants["spaced_evaluator_classification"]
            )
        if "evidence_hold_required" in invariants:
            assert bool(session.get("evidence_holds")) is invariants["evidence_hold_required"]
        if "repair_count" in invariants:
            assert session["derived"][-1]["nodes"][first_node_id]["repair_count"] == invariants["repair_count"]
        if "repair_dialogue_turn_count" in invariants:
            dialogue_turns = [event for event in events if event["type"] == "repair_dialogue_turn"]
            assert len(dialogue_turns) == invariants["repair_dialogue_turn_count"]
            assert dialogue_turns[0]["bridge_ready"] is invariants["first_repair_dialogue_bridge_ready"]
            assert dialogue_turns[-1]["bridge_ready"] is invariants["last_repair_dialogue_bridge_ready"]
            assert all(turn["graph_neutral"] is True for turn in dialogue_turns)
            assert all(turn["score_eligible"] is False for turn in dialogue_turns)
        if invariants.get("post_bridge_transfer_check_required"):
            transfer_event = events[event_order.index("post_bridge_transfer_check")]
            assert transfer_event["graph_neutral"] is True
        for forbidden_event in invariants.get("forbidden_events", []):
            assert forbidden_event not in event_order
        for forbidden_stage in invariants.get("forbidden_llm_stages", []):
            assert forbidden_stage not in llm_stages


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_harness_replays_learning_cases() -> None:
    result = run_command([str(HARNESS), "replay"])

    assert result.returncode == 0, result.stderr
    assert "Socratink Harness" in result.stdout
    assert "4 cases" in result.stdout
    assert "PASS evidence-hold-solid-spaced-primed-2026-05-26" in result.stdout
    assert "PASS repair-abandoned-no-model-bridge-2026-05-26" in result.stdout
    assert "PASS strong-cold-skips-repair-until-spacing-2026-05-26" in result.stdout
    assert "PASS inner-repair-dialogue-gates-model-bridge-2026-05-26" in result.stdout
    assert "event order ok" in result.stdout
    assert "final state: primed" in result.stdout
    assert "final state: solidified" in result.stdout
    assert "evaluator: solid" in result.stdout
    assert "evidence hold: present" in result.stdout
    assert "truth source: training_derivation" in result.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_dashboard_summarizes_founder_harness_state() -> None:
    result = run_command([str(DASHBOARD), "--json"])

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["title"] == "Socratink Founder Dashboard"
    assert payload["truth_contract"].startswith("Agents propose")
    assert payload["case_summary"] == {
        "total": 4,
        "active_regression": 4,
        "golden": 0,
        "research": 0,
    }
    assert payload["case_ids"] == [
        "evidence-hold-solid-spaced-primed-2026-05-26",
        "repair-abandoned-no-model-bridge-2026-05-26",
        "strong-cold-skips-repair-until-spacing-2026-05-26",
        "inner-repair-dialogue-gates-model-bridge-2026-05-26",
    ]
    assert payload["latest_trace"]["case_id"] == "inner-repair-dialogue-gates-model-bridge-2026-05-26"
    assert payload["latest_trace"]["final_state"] == "primed"
    assert "simulated learner output-shape guardrails" in payload["next_product_target"].lower()
    assert "deepseek" in payload["simulated_learner_status"].lower()
    assert payload["route_retry_status"] == "implemented"
    assert payload["deepseek_rerun_status"] == "complete"
    assert "training_derivation" in payload["guardrails"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_dashboard_terminal_output_is_founder_facing() -> None:
    result = run_command([str(DASHBOARD), "--color=never"])

    assert result.returncode == 0, result.stderr
    assert "Socratink Founder Dashboard" in result.stdout
    assert "Harness Cases" in result.stdout
    assert "Truth Contract" in result.stdout
    assert "DeepSeek Simulated Learner" in result.stdout
    assert "Next Product Target" in result.stdout
    assert "Bloom level" not in result.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_tui_scripted_source_less_flow_saves_product_needle_logs(tmp_path: Path) -> None:
    result = run_command(
        [str(TUI), "--scripted", str(SCRIPT), "--log-raw-llm"],
        env={
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "SOCRATINK_TUI_FAKE_COLD_CLASSIFICATION": "shallow",
            "SOCRATINK_TUI_LOG_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "Socratink Terminal" in result.stdout
    assert "Launch attempt" in result.stdout
    assert "Smallest actionable route" in result.stdout
    assert "[Cold Attempt Brief]" in result.stdout
    assert "Node: Immune memory" in result.stdout
    assert "Goal: I want to explain why vaccines work." in result.stdout
    assert "Source: no source attached; route is provisional." in result.stdout
    assert "Try your current model before seeing the explanation." in result.stdout
    assert "Cold attempt" in result.stdout
    assert "[Delta]" in result.stdout
    assert "Gap logged" in result.stdout
    assert "[Socratic Repair Drill]" in result.stdout
    assert "Before:" in result.stdout
    assert "After:" in result.stdout
    assert "What must happen to" in result.stdout
    assert "[Own-Words Repair]" in result.stdout
    assert "[Model Bridge]" in result.stdout
    assert "[Targeted Study]" not in result.stdout
    assert "Mechanism slot" not in result.stdout
    assert "internal_bloom_lens" not in result.stdout
    assert_no_visible_bloom_labels(result.stdout)
    assert "[Repair Dialogue]" in result.stdout
    assert "Bridge readiness: ready" in result.stdout
    assert "Post-bridge transfer check" in result.stdout
    assert "Spaced re-drill" in result.stdout
    assert "[Evidence] primed" in result.stdout
    pre_cold_answer = result.stdout.split("Cold attempt:")[0]
    assert "[Cold Attempt Brief]" in pre_cold_answer
    assert "matching immune cells expand" not in pre_cold_answer
    assert result.stdout.index("[Cold Attempt Brief]") < result.stdout.index("Cold attempt:")
    assert result.stdout.index("[Delta]") < result.stdout.index("[Own-Words Repair]")
    assert result.stdout.index("[Own-Words Repair]") < result.stdout.index("[Model Bridge]")

    session_logs = sorted(tmp_path.glob("*/session.json"))
    assert len(session_logs) == 1
    session = json.loads(session_logs[0].read_text())
    assert session["source_mode"] == "source_less"
    assert session["concept"] == "Immune memory"
    assert session["route"]["first_node"]["id"] == "c1_s1"
    assert [event["type"] for event in session["events"]] == [
        "launch_attempt",
        "route_generated",
        "cold_attempt",
        "gap_identified",
        "repair_dialogue_turn",
        "repair",
        "model_bridge",
        "post_bridge_transfer_check",
        "spacing_advanced",
        "spaced_redrill",
    ]
    assert session["events"][3]["graph_neutral"] is True
    assert session["events"][3]["surface"] == "delta"
    assert session["events"][3]["type"] == "gap_identified"
    assert session["events"][3]["gap_log"]["missing_operation"]
    assert session["events"][3]["gap_log"]["internal_bloom_lens"] == "understand"
    assert session["events"][3]["gap_log"]["question_style"] in {"analogical", "direct"}
    assert session["events"][3]["gap_log"]["before"]
    assert session["events"][3]["gap_log"]["after"]
    assert session["events"][3]["repair_scaffold"]["before"]
    assert session["events"][3]["repair_scaffold"]["after"]
    assert session["events"][3]["repair_scaffold"]["socratic_question"].startswith("What must happen")
    assert not session["events"][3]["repair_scaffold"]["socratic_question"].endswith(".")
    assert session["events"][4]["type"] == "repair_dialogue_turn"
    assert session["events"][4]["graph_neutral"] is True
    assert session["events"][4]["score_eligible"] is False
    assert session["events"][4]["bridge_ready"] is True
    assert session["events"][6]["type"] == "model_bridge"
    assert session["events"][7]["graph_neutral"] is True
    assert session["events"][7]["prompt"]
    assert session["events"][3]["gap_log"]["missing_operation"] in session["events"][7]["prompt"]
    derived_by_event = {entry["event"]: entry for entry in session["derived"]}
    assert derived_by_event["gap_identified"]["nodes"]["c1_s1"]["state"] != "solidified"
    assert derived_by_event["repair"]["nodes"]["c1_s1"]["state"] != "solidified"
    assert derived_by_event["model_bridge"]["nodes"]["c1_s1"]["state"] != "solidified"
    assert session["derived"][-1]["nodes"]["c1_s1"]["state"] == "primed"
    assert session["evidence_holds"][0]["event"] == "spaced_redrill"
    assert session["product_loop"]["repair_position"] == "before_model_bridge"
    assert session["agent_contract"]["truth_contract"].startswith("Agents propose")
    assert {call["agent"] for call in session["llm_calls"]} >= {
        "Route Agent",
        "Cold Attempt Agent",
        "Delta Agent",
        "Evidence Judge",
    }
    assert all(call["truth_permission"] == "none" for call in session["llm_calls"])
    assert session["llm_calls"][0]["raw_text"]
    assert session["llm_calls"][0]["raw_prompt"]["user_prompt"]
    cold_judge_call = next(call for call in session["llm_calls"] if call["stage"] == "cold_attempt")
    assert cold_judge_call["raw_prompt"]["learner_text"] == session["events"][2]["text"]
    assert "api_key" not in json.dumps(session).lower()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_tui_runs_bounded_repair_dialogue_before_model_bridge(tmp_path: Path) -> None:
    result = run_command(
        [str(TUI), "--scripted", str(CIRCULAR_REPAIR_SCRIPT), "--color=never"],
        env={
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "SOCRATINK_TUI_FAKE_COLD_CLASSIFICATION": "shallow",
            "SOCRATINK_TUI_LOG_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "[Socratic Repair Drill]" in result.stdout
    assert result.stdout.count("[Repair Dialogue]") == 2
    assert "Bridge readiness: not yet" in result.stdout
    assert "Bridge readiness: ready" in result.stdout
    assert "[Model Bridge]" in result.stdout
    assert "post-bridge transfer" in result.stdout.lower()
    assert result.stdout.index("Bridge readiness: ready") < result.stdout.index("[Model Bridge]")

    session_logs = sorted(tmp_path.glob("*/session.json"))
    assert len(session_logs) == 1
    session = json.loads(session_logs[0].read_text())
    event_types = [event["type"] for event in session["events"]]
    assert event_types == [
        "launch_attempt",
        "route_generated",
        "cold_attempt",
        "gap_identified",
        "repair_dialogue_turn",
        "repair_dialogue_turn",
        "repair",
        "model_bridge",
        "post_bridge_transfer_check",
        "spacing_advanced",
        "spaced_redrill",
    ]
    dialogue_turns = [event for event in session["events"] if event["type"] == "repair_dialogue_turn"]
    assert [turn["turn_index"] for turn in dialogue_turns] == [1, 2]
    assert {turn["gap_id"] for turn in dialogue_turns} == {"gap-c1_s1-1"}
    assert all(turn["graph_neutral"] is True for turn in dialogue_turns)
    assert all(turn["score_eligible"] is False for turn in dialogue_turns)
    assert dialogue_turns[0]["bridge_ready"] is False
    assert dialogue_turns[0]["echo_risk"] is True
    assert dialogue_turns[1]["bridge_ready"] is True
    assert dialogue_turns[1]["not_mastery_reason"]
    assert session["events"][6]["text"] == (
        "The preview leaves memory cells behind, so a later antigen match can trigger a faster response."
    )
    assert session["events"][8]["graph_neutral"] is True
    assert session["events"][8]["prompt"].startswith("Post-bridge transfer check")
    assert session["training"]["node_records"]["c1_s1"]["repairs"] == [
        {
            "id": "repair-1",
            "at": "2026-05-15T10:10:00.000Z",
            "text": "The preview leaves memory cells behind, so a later antigen match can trigger a faster response.",
        }
    ]
    assert "repair_dialogue_turn" not in {entry["event"] for entry in session["derived"]}
    assert session["derived"][-1]["nodes"]["c1_s1"]["state"] == "primed"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_tui_retries_route_validation_failure_and_logs_recovery(tmp_path: Path) -> None:
    result = run_command(
        [str(TUI), "--scripted", str(SCRIPT), "--color=never"],
        env={
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "SOCRATINK_TUI_FAKE_ROUTE_FAIL_ONCE": "1",
            "SOCRATINK_TUI_LOG_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "[Route Retry]" in result.stdout
    assert "SmallestRouteCapExceeded" in result.stdout
    assert "[Spaced Re-Drill]" in result.stdout

    session_logs = sorted(tmp_path.glob("*/session.json"))
    assert len(session_logs) == 1
    session = json.loads(session_logs[0].read_text())
    assert [event["type"] for event in session["events"]][:3] == [
        "launch_attempt",
        "route_retry",
        "route_generated",
    ]
    assert session["events"][1]["attempt"] == 1
    assert session["events"][1]["error"] == "SmallestRouteCapExceeded"
    assert session["events"][1]["graph_neutral"] is True
    assert session["route"]["retry_count"] == 1
    assert session["route"]["retry_reasons"][0]["error"] == "SmallestRouteCapExceeded"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_tui_rejects_answer_shaped_gap_scaffold_before_printing(tmp_path: Path) -> None:
    result = run_command(
        [str(TUI), "--scripted", str(SCRIPT), "--color=never"],
        env={
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "SOCRATINK_TUI_FAKE_COLD_CLASSIFICATION": "shallow",
            "SOCRATINK_TUI_FAKE_LEAKY_SCAFFOLD": "1",
            "SOCRATINK_TUI_LOG_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "observe the tool result, compare it to the goal, update context" not in result.stdout
    assert "Gap logged" in result.stdout
    assert_no_visible_bloom_labels(result.stdout)

    session_logs = sorted(tmp_path.glob("*/session.json"))
    assert len(session_logs) == 1
    session = json.loads(session_logs[0].read_text())
    gap_event = session["events"][3]
    assert gap_event["type"] == "gap_identified"
    assert gap_event["scaffold_rejections"][0]["reason"] == "answer_shaped_scaffold"
    assert gap_event["gap_log"]["missing_operation"] != (
        "observe the tool result, compare it to the goal, update context, refine the plan, and choose the next action"
    )
    assert gap_event["gap_log"]["internal_bloom_lens"] == "understand"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_tui_strong_cold_path_skips_repair_until_spacing(tmp_path: Path) -> None:
    result = run_command(
        [str(TUI), "--scripted", str(SCRIPT), "--color=never"],
        env={
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "SOCRATINK_TUI_LOG_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "[Cold Attempt]" in result.stdout
    assert "[Strong Cold Path]" in result.stdout
    assert "Repair skipped for now" in result.stdout
    assert "[Delta]" not in result.stdout
    assert "[Own-Words Repair]" not in result.stdout
    assert "[Model Bridge]" not in result.stdout
    assert "[Pressure-check]" not in result.stdout
    assert "[Spaced Re-Drill]" in result.stdout
    assert "[Evidence] solidified" in result.stdout

    session_logs = sorted(tmp_path.glob("*/session.json"))
    assert len(session_logs) == 1
    session = json.loads(session_logs[0].read_text())
    assert [event["type"] for event in session["events"]] == [
        "launch_attempt",
        "route_generated",
        "cold_attempt",
        "strong_cold_path",
        "spacing_advanced",
        "spaced_redrill",
    ]
    assert session["events"][2]["evaluation"]["classification"] == "solid"
    assert session["events"][3]["graph_neutral"] is True
    assert session["events"][3]["next_step"] == "spaced_redrill"
    assert session["derived"][0]["nodes"]["c1_s1"]["state"] != "solidified"
    assert session["derived"][-1]["nodes"]["c1_s1"]["state"] == "solidified"
    assert session["product_loop"]["strong_cold_path"] == "skip_repair_until_spacing"
    assert session["product_loop"]["graph_neutral_events"] == ["strong_cold_path"]
    assert "repair_scaffold" not in {call["stage"] for call in session["llm_calls"]}
    assert "model_bridge" not in {call["stage"] for call in session["llm_calls"]}
    assert "api_key" not in json.dumps(session).lower()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_tui_can_color_key_loop_headers(tmp_path: Path) -> None:
    result = run_command(
        [str(TUI), "--scripted", str(SCRIPT), "--color=always"],
        env={
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "SOCRATINK_TUI_FAKE_COLD_CLASSIFICATION": "shallow",
            "SOCRATINK_TUI_LOG_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "\x1b[35m[Ignition]\x1b[0m" in result.stdout
    assert "\x1b[36m[Route]\x1b[0m" in result.stdout
    assert "\x1b[33m[Cold Attempt]\x1b[0m" in result.stdout
    assert "\x1b[34m[Delta]\x1b[0m" in result.stdout
    assert "\x1b[31m[Socratic Repair Drill]\x1b[0m" in result.stdout
    assert "Gap logged" in result.stdout
    assert "\x1b[31m[Own-Words Repair]\x1b[0m" in result.stdout
    assert "\x1b[34m[Model Bridge]\x1b[0m" in result.stdout
    assert "\x1b[32m[Spaced Re-Drill]\x1b[0m" in result.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_tui_explains_solid_spaced_hold_when_derivation_stays_primed(tmp_path: Path) -> None:
    result = run_command(
        [str(TUI), "--scripted", str(SCRIPT), "--color=never"],
        env={
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "SOCRATINK_TUI_FAKE_COLD_CLASSIFICATION": "shallow",
            "SOCRATINK_TUI_LOG_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "[Evidence] primed" in result.stdout
    assert "[Evidence Hold]" in result.stdout
    assert "spaced answer was solid" in result.stdout
    assert "first attempt was not strong" in result.stdout

    session_logs = sorted(tmp_path.glob("*/session.json"))
    assert len(session_logs) == 1
    session = json.loads(session_logs[0].read_text())
    assert session["derived"][-1]["nodes"]["c1_s1"]["state"] == "primed"
    assert session["events"][-1]["evaluation"]["classification"] == "solid"
    assert session["evidence_holds"][0]["event"] == "spaced_redrill"
    assert session["evidence_holds"][0]["state"] == "primed"
    assert "first attempt was not strong" in session["evidence_holds"][0]["reason"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_socratink_tui_blocks_model_bridge_when_repair_is_uncertain(tmp_path: Path) -> None:
    result = run_command(
        [str(TUI), "--scripted", str(BLOCKED_REPAIR_SCRIPT), "--color=never"],
        env={
            "SOCRATINK_TUI_FAKE_LLM": "1",
            "SOCRATINK_TUI_FAKE_COLD_CLASSIFICATION": "shallow",
            "SOCRATINK_TUI_LOG_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "[Own-Words Repair]" in result.stdout
    assert "[Repair Abandoned]" in result.stdout
    assert "No model bridge yet" in result.stdout
    assert "[Model Bridge]" not in result.stdout
    assert "[Spaced Re-Drill]" not in result.stdout

    session_logs = sorted(tmp_path.glob("*/session.json"))
    assert len(session_logs) == 1
    session = json.loads(session_logs[0].read_text())
    assert [event["type"] for event in session["events"]] == [
        "launch_attempt",
        "route_generated",
        "cold_attempt",
        "gap_identified",
        "repair_abandoned",
    ]
    assert session["events"][-1]["graph_neutral"] is True
    assert session["events"][-1]["reason"] == "uncertain_nonrepair"
    assert session["derived"][-1]["event"] == "repair_abandoned"
    assert session["derived"][-1]["nodes"]["c1_s1"]["repair_count"] == 0
    assert "model_bridge" not in {event["type"] for event in session["events"]}
    assert session["training"]["node_records"]["c1_s1"]["repairs"] == []
    assert "model_bridge" not in {call["stage"] for call in session["llm_calls"]}


def test_socratink_tui_notes_log_science_iteration() -> None:
    notes = (TUI_DIR / "NOTES.md").read_text()
    normalized_notes = notes.lower()

    assert "## Iteration Log" in notes
    assert "2026-05-26" in notes
    assert "own-words repair before model bridge" in normalized_notes
    assert "study, repair, and pressure-checks do not produce `solidified`" in normalized_notes
