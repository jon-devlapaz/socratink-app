#!/usr/bin/env python3
"""Python LLM bridge for the founder-facing Socratink terminal dogfood app.

The terminal UI stays in Node so it can reuse the browser training-store and
training-derive modules. This bridge keeps LLM calls on the existing Python seam.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import ai_service
from llm import StructuredLLMRequest, build_llm_client
from llm.types import StructuredLLMResult
from pydantic import BaseModel, Field
from models.provisional_map import (
    BackboneItem,
    Cluster,
    LearnerScaffold,
    Metadata,
    ProvisionalMap,
    Relationships,
    Subnode,
)


class RepairScaffold(BaseModel):
    repair_target: str = Field(
        description="One direct sentence naming the gap boundary without completing the answer."
    )
    before: str = Field(description="The part of the learner's model before the missing operation.")
    missing_operation: str = Field(description="A terse name for the missing operation, not a full mechanism.")
    after: str = Field(description="The downstream result the missing operation should connect to.")
    internal_bloom_lens: str = Field(
        description="Internal route lens: remember, understand, apply, analyze, evaluate, or create. Never show this to the learner."
    )
    question_style: str = Field(
        description="direct or analogical. Use analogical when the learner model is vague or low-resolution."
    )
    socratic_question: str = Field(
        description="One question beginning with 'What must happen' that forces the learner to generate the missing operation."
    )


class RepairDialogueJudge(BaseModel):
    classification: str = Field(description="thin, partial, wrong_direction, or strong for this graph-neutral repair turn.")
    score_eligible: bool = Field(description="Always false; inner repair dialogue is not graph evidence.")
    graph_neutral: bool = Field(description="Always true; dialogue routing cannot mutate graph truth.")
    support_level: str = Field(description="probe, hint, micro_scaffold, or direct_explanation.")
    causal_link_present: bool = Field(description="Whether the learner expressed a before -> operation -> after link.")
    missing_operation_addressed: bool = Field(description="Whether the named missing operation was addressed.")
    echo_risk: bool = Field(description="Whether the learner appears to echo words without reconstructing the causal link.")
    bridge_ready: bool = Field(description="Whether model bridge may be revealed after this own-words repair.")
    next_dialogue_action: str = Field(description="commit_repair, probe_again, micro_scaffold, or abandon.")
    judge_reason: str = Field(description="One plain sentence explaining the decision.")
    next_prompt: str = Field(description="The next prompt if another dialogue turn is needed, otherwise an empty string.")
    not_mastery_reason: str = Field(description="Why this turn is not graph mastery evidence.")


def _read_request() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _write_response(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")


def _call_metadata(result: StructuredLLMResult, *, include_raw: bool) -> dict[str, Any]:
    payload = {
        "provider": result.provider,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "usage": asdict(result.usage),
    }
    if include_raw:
        payload["raw_text"] = result.raw_text
    return payload


def _route_user_prompt(
    *,
    concept: str,
    launch_attempt: str,
    learner_goal: str | None,
) -> str:
    parts = [
        f"<concept>{concept}</concept>",
        f"<threshold>{launch_attempt}</threshold>",
    ]
    if learner_goal:
        parts.append(f"<learner_goal>{learner_goal}</learner_goal>")
    return "\n\n".join(parts)


def _first_node(pm: ProvisionalMap) -> dict[str, Any]:
    for cluster in pm.clusters:
        for node in cluster.subnodes:
            scaffold = node.learner_scaffold
            return {
                "id": node.id,
                "label": node.label,
                "mechanism": node.mechanism,
                "learner_prompt": scaffold.entry_prompt if scaffold else f"Reconstruct {node.label}.",
                "task_label": scaffold.task_label if scaffold else node.label,
                "blank_hint": scaffold.blank_hint if scaffold else "",
                "evidence_goal": scaffold.evidence_goal if scaffold else "",
            }
    raise ValueError("generated route has no drillable node")


def _fake_map(concept: str) -> ProvisionalMap:
    scaffold = LearnerScaffold(
        bloom_level="understand",
        learner_move="reconstruct the causal link",
        task_label="Explain the first mechanism",
        task_cue="Use your own words before reading the study note.",
        tailoring_anchor="Connect the launch attempt to one local causal bridge.",
        entry_prompt="In your own words, why does a safe preview make the later response faster?",
        expected_shape="safe preview -> immune selection -> memory -> faster later response",
        sentence_starter="A safe preview helps because...",
        blank_hint="Name what remains after the preview.",
        evidence_goal="The learner reconstructs how immune memory links safe exposure to faster response.",
    )
    return ProvisionalMap(
        metadata=Metadata(
            source_title=f"{concept} source-less route",
            core_thesis=f"{concept} depends on a safe preview creating durable response memory.",
            architecture_type="causal_chain",
            difficulty="easy",
            governing_assumptions=["Source-less route is provisional until learner evidence accumulates."],
            low_density=False,
        ),
        backbone=[
            BackboneItem(
                id="b1",
                principle="Safe preview creates durable response memory.",
                dependent_clusters=["c1"],
            )
        ],
        clusters=[
            Cluster(
                id="c1",
                label="Memory bridge",
                description="The local bridge between safe exposure and faster later response.",
                subnodes=[
                    Subnode(
                        id="c1_s1",
                        label="Immune memory",
                        mechanism=(
                            "A vaccine safely presents antigen, matching immune cells expand, "
                            "memory cells remain, and those cells respond faster later."
                        ),
                        learner_scaffold=scaffold,
                    )
                ],
            )
        ],
        relationships=Relationships(domain_mechanics=[], learning_prerequisites=[]),
        frameworks=[],
    )


def generate_route(request: dict[str, Any]) -> dict[str, Any]:
    concept = str(request.get("concept") or "").strip()
    launch_attempt = str(request.get("launch_attempt") or "").strip()
    if not concept:
        raise ValueError("concept-required")
    if not launch_attempt:
        raise ValueError("launch-attempt-required")

    include_raw = bool(request.get("log_raw_llm"))
    learner_goal = str(request.get("learner_goal") or "").strip() or None
    route_attempt = int(request.get("route_attempt") or 1)
    retry_guidance = str(request.get("route_retry_reason") or "").strip() or None
    if os.environ.get("SOCRATINK_TUI_FAKE_ROUTE_FAIL_ALWAYS") == "1":
        raise ai_service.SmallestRouteCapExceeded(
            "smallest route subnode 'fake' sentence_starter copies hidden mechanism"
        )
    if os.environ.get("SOCRATINK_TUI_FAKE_ROUTE_FAIL_ONCE") == "1" and route_attempt <= 1:
        raise ai_service.SmallestRouteCapExceeded(
            "smallest route subnode 'fake' sentence_starter copies hidden mechanism"
        )
    if os.environ.get("SOCRATINK_TUI_FAKE_LLM") == "1":
        pm = _fake_map(concept)
        llm_call = {
            "provider": "fake",
            "model": "fake-source-less-route",
            "latency_ms": 0,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
        if include_raw:
            llm_call["raw_text"] = pm.model_dump_json(by_alias=True)
            llm_call["raw_prompt"] = {
                "system_prompt": "fake source-less route prompt",
                "user_prompt": _route_user_prompt(
                    concept=concept,
                    launch_attempt=launch_attempt,
                    learner_goal=learner_goal,
                ),
            }
    else:
        captured: dict[str, Any] = {}

        def on_call_complete(result: StructuredLLMResult) -> None:
            captured.update(_call_metadata(result, include_raw=include_raw))

        pm = ai_service.generate_smallest_provisional_map(
            concept=concept,
            threshold=launch_attempt,
            learner_goal=learner_goal,
            retry_guidance=retry_guidance,
            on_call_complete=on_call_complete,
        )
        llm_call = captured
        if include_raw:
            llm_call["raw_prompt"] = {
                "system_prompt": ai_service.GENERATE_SMALLEST_ROUTE_PROMPT_PATH.read_text(),
                "user_prompt": _route_user_prompt(
                    concept=concept,
                    launch_attempt=launch_attempt,
                    learner_goal=learner_goal,
                ),
            }

    return {
        "provisional_map": pm.model_dump(by_alias=True),
        "first_node": _first_node(pm),
        "llm_call": llm_call,
    }


def _fake_evaluation(request: dict[str, Any]) -> dict[str, Any]:
    mode = request.get("drill_mode")
    if mode == "gap_drill":
        classification = "shallow"
        response = "That post-bridge transfer check keeps the repaired link active without changing graph evidence."
    elif mode == "cold_attempt" and os.environ.get("SOCRATINK_TUI_FAKE_COLD_CLASSIFICATION"):
        classification = os.environ["SOCRATINK_TUI_FAKE_COLD_CLASSIFICATION"]
        response = "Useful start. The first attempt has a gap to repair."
    else:
        classification = "solid"
        response = "Good reconstruction. You connected the causal bridge in your own words."
    return {
        "evaluation": {
            "agent_response": response,
            "generative_commitment": True,
            "answer_mode": "attempt",
            "score_eligible": True,
            "help_request_reason": "none",
            "classification": classification,
            "gap_description": None if classification == "solid" else "Name what remains after the safe preview and why it speeds the later response.",
            "routing": "NEXT",
            "response_tier": 4 if classification == "solid" else 3,
            "response_band": "clear" if classification == "solid" else "chain",
            "tier_reason": "The response names the key causal transition.",
        },
        "llm_call": {
            "provider": "fake",
            "model": "fake-drill-evaluator",
            "latency_ms": 0,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            **({"raw_text": '{"classification":"solid"}'} if request.get("log_raw_llm") else {}),
            **({"raw_prompt": request} if request.get("log_raw_llm") else {}),
        },
    }


def _is_vague_learner_text(text: str) -> bool:
    normalized = text.lower()
    return (
        "dont know" in normalized
        or "don't know" in normalized
        or "do not know" in normalized
        or "i believe other things" in normalized
        or "not sure" in normalized
    )


def _fake_repair_scaffold(request: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("SOCRATINK_TUI_FAKE_LEAKY_SCAFFOLD") == "1":
        scaffold = RepairScaffold(
            repair_target="Repair the full agent feedback loop.",
            before="The agent calls a tool.",
            missing_operation=(
                "observe the tool result, compare it to the goal, update context, "
                "refine the plan, and choose the next action"
            ),
            after="The agent chooses a better next action.",
            internal_bloom_lens="understand",
            question_style="direct",
            socratic_question=(
                "How does the agent observe the tool result, compare it to the goal, "
                "update context, refine the plan, and choose the next action?"
            ),
        )
        return {
            "repair_scaffold": scaffold.model_dump(),
            "llm_call": {
                "provider": "fake",
                "model": "fake-leaky-repair-scaffold",
                "latency_ms": 0,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }

    learner_text = str(request.get("learner_text") or "")
    if _is_vague_learner_text(learner_text):
        scaffold = RepairScaffold(
            repair_target="Repair the purpose of the harness by naming what it captures and replays.",
            before="The learner has a rough idea of a loop or skill scaffold.",
            missing_operation="capture and replay run evidence",
            after="The harness can judge whether the system actually improved.",
            internal_bloom_lens="understand",
            question_style="analogical",
            socratic_question=(
                "If a harness is like a flight recorder plus test track, what must it capture "
                "and replay so we can tell whether the agent actually improved?"
            ),
        )
        return {
            "repair_scaffold": scaffold.model_dump(),
            "llm_call": {
                "provider": "fake",
                "model": "fake-repair-scaffold",
                "latency_ms": 0,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }

    scaffold = RepairScaffold(
        repair_target="Repair the gap between the safe preview and the faster later response.",
        before="A safe preview presents the antigen.",
        missing_operation="durable immune change after the preview",
        after="The later immune response happens faster.",
        internal_bloom_lens="understand",
        question_style="direct",
        socratic_question="What must happen to the safe preview before it can make the later response faster?",
    )
    return {
        "repair_scaffold": scaffold.model_dump(),
        "llm_call": {
            "provider": "fake",
            "model": "fake-repair-scaffold",
            "latency_ms": 0,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
    }


def _fake_repair_dialogue(request: dict[str, Any]) -> dict[str, Any]:
    learner_text = str(request.get("learner_text") or "").lower()
    missing_operation = str(request.get("missing_operation") or "the missing operation")
    if (
        "memory cells" in learner_text
        or "memory" in learner_text and "faster response" in learner_text
        or "capture" in learner_text and "replay" in learner_text
    ):
        judge = RepairDialogueJudge(
            classification="strong",
            score_eligible=False,
            graph_neutral=True,
            support_level="probe",
            causal_link_present=True,
            missing_operation_addressed=True,
            echo_risk=False,
            bridge_ready=True,
            next_dialogue_action="commit_repair",
            judge_reason="The learner connected the before state to the after state through the missing operation.",
            next_prompt="",
            not_mastery_reason="Inner repair dialogue is scaffold-adjacent practice; only spaced reconstruction can prove durable evidence.",
        )
    else:
        judge = RepairDialogueJudge(
            classification="thin",
            score_eligible=False,
            graph_neutral=True,
            support_level="probe",
            causal_link_present=False,
            missing_operation_addressed=False,
            echo_risk=True,
            bridge_ready=False,
            next_dialogue_action="probe_again",
            judge_reason="The learner repeated the setup without connecting the missing operation to the result.",
            next_prompt=f"Stay on this link: what changes because of {missing_operation}, and how does that change cause the after-state?",
            not_mastery_reason="This turn is dialogue routing, not independent spaced reconstruction evidence.",
        )
    return {
        "repair_dialogue": judge.model_dump(),
        "llm_call": {
            "provider": "fake",
            "model": "fake-repair-dialogue",
            "latency_ms": 0,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            **({"raw_text": judge.model_dump_json()} if request.get("log_raw_llm") else {}),
            **({"raw_prompt": request} if request.get("log_raw_llm") else {}),
        },
    }


def build_repair_scaffold(request: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("SOCRATINK_TUI_FAKE_LLM") == "1":
        return _fake_repair_scaffold(request)

    node_label = str(request.get("node_label") or "").strip()
    node_mechanism = str(request.get("node_mechanism") or "").strip()
    learner_text = str(request.get("learner_text") or "").strip()
    gap_description = str(request.get("gap_description") or "").strip()
    evidence_goal = str(request.get("evidence_goal") or "").strip()
    blank_hint = str(request.get("blank_hint") or "").strip()
    include_raw = bool(request.get("log_raw_llm"))
    if not node_label or not node_mechanism or not learner_text:
        raise ValueError("repair-scaffold-context-required")

    system_prompt = (
        "You write Socratink Delta repair scaffolds.\n"
        "Preserve Generation Before Recognition: do not reveal the full answer key, "
        "do not write the repair for the learner, and do not use praise.\n"
        "Log the gap boundary, then ask one narrow Socratic question.\n"
        "The Delta may name a missing operation category, but it must not complete "
        "the causal chain or list the answer steps.\n"
        "Choose question_style='analogical' when the learner text is vague, low-resolution, "
        "or says they do not know much. In that case, use an analogy to provoke model-building "
        "without revealing the answer. Choose question_style='direct' when the learner is close "
        "and only missing one causal operation.\n"
        "Choose internal_bloom_lens from remember, understand, apply, analyze, "
        "evaluate, or create. This is internal routing metadata only.\n"
        "Keep each field short and learner-facing."
    )
    prompt = {
        "target_node": {"label": node_label},
        "answer_key_for_internal_use_only": node_mechanism,
        "learner_attempt": learner_text,
        "gap_description": gap_description or None,
        "evidence_goal": evidence_goal or None,
        "blank_hint": blank_hint or None,
    }
    llm_request = StructuredLLMRequest(
        system_prompt=system_prompt,
        user_prompt=json.dumps(prompt, ensure_ascii=False),
        response_schema=RepairScaffold,
        temperature=0.2,
        task_name="socratink_tui_repair_scaffold",
        prompt_version="socratink-tui-repair-scaffold-v1",
    )
    result = build_llm_client().generate_structured(llm_request)
    scaffold = result.parsed
    if not isinstance(scaffold, RepairScaffold):
        raise ValueError("invalid-repair-scaffold")
    return {
        "repair_scaffold": scaffold.model_dump(),
        "llm_call": {
            **_call_metadata(result, include_raw=include_raw),
            **({
                "raw_prompt": {
                    "system_prompt": system_prompt,
                    "user_prompt": json.dumps(prompt, ensure_ascii=False),
                }
            } if include_raw else {}),
        },
    }


def judge_repair_dialogue(request: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("SOCRATINK_TUI_FAKE_LLM") == "1":
        return _fake_repair_dialogue(request)

    node_label = str(request.get("node_label") or "").strip()
    node_mechanism = str(request.get("node_mechanism") or "").strip()
    missing_operation = str(request.get("missing_operation") or "").strip()
    before = str(request.get("before") or "").strip()
    after = str(request.get("after") or "").strip()
    learner_text = str(request.get("learner_text") or "").strip()
    turn_index = int(request.get("turn_index") or 1)
    if not node_label or not node_mechanism or not missing_operation or not before or not after:
        raise ValueError("repair-dialogue-context-required")
    if not learner_text:
        raise ValueError("learner-text-required")

    system_prompt = (
        "You are Socratink's repair-dialogue judge.\n"
        "Your job is dialogue routing only. You cannot update graph truth, cannot mark mastery, "
        "and cannot reveal the full answer key.\n"
        "Judge whether the learner reconstructed this exact bridge in their own words: "
        "before state -> missing operation -> after state.\n"
        "All inner dialogue turns must set score_eligible=false and graph_neutral=true.\n"
        "Set bridge_ready=true only when the learner connects the before state to the after "
        "state through the missing operation without merely echoing the prompt. If not ready, "
        "ask one concrete follow-up about the same missing operation. After repeated weak turns, "
        "use support_level='micro_scaffold' and next_dialogue_action='micro_scaffold'."
    )
    prompt = {
        "target_node": {"label": node_label},
        "answer_key_for_internal_use_only": node_mechanism,
        "gap": {
            "gap_id": request.get("gap_id") or None,
            "before": before,
            "missing_operation": missing_operation,
            "after": after,
        },
        "learner_text": learner_text,
        "turn_index": turn_index,
    }
    llm_request = StructuredLLMRequest(
        system_prompt=system_prompt,
        user_prompt=json.dumps(prompt, ensure_ascii=False),
        response_schema=RepairDialogueJudge,
        temperature=0.2,
        task_name="socratink_tui_repair_dialogue",
        prompt_version="socratink-tui-repair-dialogue-v1",
    )
    result = build_llm_client().generate_structured(llm_request)
    judge = result.parsed
    if not isinstance(judge, RepairDialogueJudge):
        raise ValueError("invalid-repair-dialogue")
    return {
        "repair_dialogue": judge.model_dump(),
        "llm_call": {
            **_call_metadata(result, include_raw=bool(request.get("log_raw_llm"))),
            **({
                "raw_prompt": {
                    "system_prompt": system_prompt,
                    "user_prompt": json.dumps(prompt, ensure_ascii=False),
                }
            } if request.get("log_raw_llm") else {}),
        },
    }


def evaluate_attempt(request: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("SOCRATINK_TUI_FAKE_LLM") == "1":
        return _fake_evaluation(request)

    node_id = str(request.get("node_id") or "").strip()
    node_label = str(request.get("node_label") or "").strip()
    node_mechanism = str(request.get("node_mechanism") or "").strip()
    learner_text = str(request.get("learner_text") or "").strip()
    drill_mode = str(request.get("drill_mode") or "cold_attempt").strip()
    if not node_id or not node_label or not node_mechanism:
        raise ValueError("node-context-required")
    if not learner_text:
        raise ValueError("learner-text-required")

    system_prompt = (
        f"{ai_service.DRILL_SYSTEM_BASE}\n\n"
        "### Target Node (ANSWER KEY - NEVER REVEAL)\n"
        f"Node ID: {node_id}\nNode Label: {node_label}\nMechanism: {node_mechanism}\n"
    )
    if drill_mode == "cold_attempt":
        system_prompt += (
            "\nMODE: COLD ATTEMPT. Evaluate the learner's first genuine generative attempt. "
            "Do not reveal the mechanism. Cold attempts are unscored to the learner, but populate "
            "classification and routing for the app.\n"
        )
    elif drill_mode == "gap_drill":
        system_prompt += (
            "\nMODE: GAP DRILL. This is graph-neutral repair pressure-check practice. "
            "Evaluate the latest learner text, but do not imply graph mutation or mastery.\n"
        )
    else:
        system_prompt += (
            "\nMODE: RE-DRILL. Demand multi-step causal reconstruction. A solid result only counts "
            "because the terminal app controls spacing before this call.\n"
        )

    prompt = {
        "target_node": {"id": node_id, "label": node_label},
        "learner_text": learner_text,
        "repair_drill_context": request.get("repair_drill_context") or None,
        "knowledge_map": request.get("knowledge_map") or {},
    }
    llm_request = StructuredLLMRequest(
        system_prompt=system_prompt,
        user_prompt=json.dumps(prompt, ensure_ascii=False),
        response_schema=ai_service.DrillEvaluation,
        temperature=ai_service.DRILL_TEMPERATURE,
        task_name=f"socratink_tui_{drill_mode}",
        prompt_version=ai_service.DRILL_PROMPT_VERSION,
    )
    result = build_llm_client().generate_structured(llm_request)
    evaluation = result.parsed
    if not isinstance(evaluation, ai_service.DrillEvaluation):
        raise ValueError("invalid-drill-evaluation")
    return {
        "evaluation": evaluation.model_dump(),
        "llm_call": {
            **_call_metadata(result, include_raw=bool(request.get("log_raw_llm"))),
            **({
                "raw_prompt": {
                    "system_prompt": system_prompt,
                    "user_prompt": json.dumps(prompt, ensure_ascii=False),
                }
            } if request.get("log_raw_llm") else {}),
        },
    }


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: scripts/socratink_tui/bridge.py <generate-route|evaluate-attempt|repair-scaffold|repair-dialogue>\n")
        return 2
    try:
        request = _read_request()
        if sys.argv[1] == "generate-route":
            _write_response(generate_route(request))
            return 0
        if sys.argv[1] == "repair-scaffold":
            _write_response(build_repair_scaffold(request))
            return 0
        if sys.argv[1] == "repair-dialogue":
            _write_response(judge_repair_dialogue(request))
            return 0
        if sys.argv[1] == "evaluate-attempt":
            _write_response(evaluate_attempt(request))
            return 0
        raise ValueError(f"unknown-action:{sys.argv[1]}")
    except Exception as exc:  # pragma: no cover - exercised through subprocess
        _write_response({"error": type(exc).__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
