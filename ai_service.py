import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional, TypedDict

from google import genai
from google.genai.errors import APIError
from google.genai import types
from pydantic import BaseModel, Field

MODEL       = "gemini-2.5-flash"
EXTRACT_TEMPERATURE = 0.2
DRILL_TEMPERATURE = 0.2
SKILL_PROMPT_PATH = Path(__file__).parent / "learnops/skills/learnops-extract/extract-system-v1.txt"
DRILL_SKILL_PROMPT_PATH = Path(__file__).parent / "learnops/skills/learnops-drill/SKILL.md"
DRILL_SYSTEM_BASE = DRILL_SKILL_PROMPT_PATH.read_text()
MAX_RETRIES = 3
BACKOFF_BASE = 2
RETRYABLE_CODES = {429, 503, 500}

USER_PROMPT = (
    "Execute the full extraction pipeline on the following text and return ONLY "
    "the valid JSON object as specified in your instructions. "
    "No preamble, no explanation, no code fences — raw JSON only:\n\n{text}"
)

class DrillEvaluation(BaseModel):
    agent_response: str = Field(description="The conversational text shown to the user")
    classification: Optional[Literal["solid", "shallow", "deep", "misconception"]] = Field(
        default=None,
        description="Gap classification. null on init phase and before genuine generative attempt.",
    )
    gap_description: Optional[str] = Field(
        default=None,
        description="1-sentence description of the delta between user knowledge and mechanism.",
    )
    routing: Optional[Literal["NEXT", "PROBE", "SCAFFOLD", "REROUTE_PREREQ", "SESSION_COMPLETE"]] = Field(
        default=None,
        description="Routing action for the frontend to execute.",
    )


class DrillTurnResult(TypedDict):
    agent_response: str
    classification: str | None
    gap_description: str | None
    routing: str | None
    node_id: str
    probe_count: int
    nodes_drilled: int
    session_terminated: bool
    termination_reason: str | None


class MissingAPIKeyError(ValueError):
    pass


class GeminiRateLimitError(ValueError):
    pass


class GeminiServiceError(ValueError):
    pass


def _get_client(api_key: str | None = None):
    key = os.environ.get("GEMINI_API_KEY") or api_key
    if not key:
        raise MissingAPIKeyError("No Gemini API key configured. Add one in Settings or set GEMINI_API_KEY in .env.")
    return genai.Client(api_key=key)


def _clean_response(text: str | None, context: str = "Gemini") -> str:
    """Strip code fences. Used ONLY for extract_knowledge_map."""
    result = (text or "").strip()
    if not result:
        raise ValueError(f"{context} returned an empty response.")

    if result.startswith("```"):
        result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return result


def _parse_iso_timestamp(iso_string: str) -> datetime:
    sanitized = iso_string.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(sanitized)
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: {iso_string}") from exc


def _validate_knowledge_map(knowledge_map: dict) -> None:
    if not isinstance(knowledge_map, dict):
        raise ValueError("knowledge_map must be an object.")
    if not isinstance(knowledge_map.get("metadata"), dict):
        raise ValueError("knowledge_map.metadata must be an object.")
    if not isinstance(knowledge_map.get("backbone"), list):
        raise ValueError("knowledge_map.backbone must be a list.")
    if not isinstance(knowledge_map.get("clusters"), list):
        raise ValueError("knowledge_map.clusters must be a list.")


def _knowledge_map_has_node(knowledge_map: dict, node_id: str) -> bool:
    if node_id == "core-thesis":
        return True

    for backbone_item in knowledge_map.get("backbone", []):
        if isinstance(backbone_item, dict) and backbone_item.get("id") == node_id:
            return True

    for cluster in knowledge_map.get("clusters", []):
        if not isinstance(cluster, dict):
            continue
        if cluster.get("id") == node_id:
            return True
        for subnode in cluster.get("subnodes", []):
            if isinstance(subnode, dict) and subnode.get("id") == node_id:
                return True

    return False


def _resolve_target_cluster_id(knowledge_map: dict, target_node_id: str) -> str | None:
    if target_node_id.startswith("c") and "_s" not in target_node_id:
        return target_node_id

    for cluster in knowledge_map.get("clusters", []):
        if not isinstance(cluster, dict):
            continue
        cluster_id = cluster.get("id")
        if cluster_id == target_node_id:
            return cluster_id
        for subnode in cluster.get("subnodes", []):
            if isinstance(subnode, dict) and subnode.get("id") == target_node_id:
                return cluster_id

    return None


def _prune_context(knowledge_map: dict, target_node_id: str) -> dict:
    metadata = knowledge_map.get("metadata") or {}
    pruned = {
        "metadata": {
            "thesis": metadata.get("core_thesis"),
            "governing_assumptions": metadata.get("governing_assumptions") or [],
        }
    }
    relationships = knowledge_map.get("relationships") or {}
    frameworks = knowledge_map.get("frameworks") or []

    if target_node_id == "core-thesis" or target_node_id.startswith("b"):
        target_backbone = next(
            (
                item
                for item in knowledge_map.get("backbone", [])
                if isinstance(item, dict)
                and (
                    target_node_id == "core-thesis"
                    or item.get("id") == target_node_id
                )
            ),
            None,
        )
        if target_backbone is None and knowledge_map.get("backbone"):
            target_backbone = knowledge_map["backbone"][0]

        dependent_cluster_ids = set(target_backbone.get("dependent_clusters") or []) if isinstance(target_backbone, dict) else set()
        cluster_shells = [
            {
                "id": cluster.get("id"),
                "label": cluster.get("label"),
                "description": cluster.get("description"),
            }
            for cluster in knowledge_map.get("clusters", [])
            if isinstance(cluster, dict) and cluster.get("id") in dependent_cluster_ids
        ]

        pruned["backbone"] = [target_backbone] if target_backbone else []
        pruned["clusters"] = cluster_shells
        pruned["relationships"] = relationships
        pruned["frameworks"] = frameworks
        return pruned

    target_cluster_id = _resolve_target_cluster_id(knowledge_map, target_node_id)
    target_cluster = next(
        (
            cluster
            for cluster in knowledge_map.get("clusters", [])
            if isinstance(cluster, dict) and cluster.get("id") == target_cluster_id
        ),
        None,
    )

    pruned["clusters"] = [target_cluster] if target_cluster else []
    pruned["backbone"] = [
        item
        for item in knowledge_map.get("backbone", [])
        if isinstance(item, dict) and target_cluster_id in (item.get("dependent_clusters") or [])
    ]
    pruned["relationships"] = {
        "learning_prerequisites": [
            rel
            for rel in relationships.get("learning_prerequisites", [])
            if isinstance(rel, dict) and (rel.get("from") == target_cluster_id or rel.get("to") == target_cluster_id)
        ]
    }
    pruned["frameworks"] = [
        framework
        for framework in frameworks
        if isinstance(framework, dict) and target_cluster_id in (framework.get("source_clusters") or [])
    ]
    return pruned


def _call_gemini_with_retry(client, *, model, contents, config, max_retries=MAX_RETRIES):
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except APIError as err:
            if err.code in RETRYABLE_CODES and attempt < max_retries - 1:
                time.sleep(BACKOFF_BASE ** (attempt + 1))
                continue
            if err.code == 429:
                raise GeminiRateLimitError("Gemini rate limit hit. Try again in 60s.") from err
            if err.code in (503, 500):
                raise GeminiServiceError(f"Gemini service unavailable (HTTP {err.code}).") from err
            raise ValueError(f"Gemini API error (HTTP {err.code}): {err.message}") from err
        except Exception as err:
            raise ValueError(f"Unexpected error: {str(err)}") from err


def _normalize_drill_evaluation(
    evaluation: DrillEvaluation,
    *,
    session_phase: str,
    probe_count: int,
) -> DrillEvaluation:
    if session_phase == "init":
        evaluation.classification = None
        evaluation.routing = None
        evaluation.gap_description = None
        return evaluation

    if not evaluation.classification:
        raise ValueError("Gemini returned no classification for a drill evaluation turn.")

    if evaluation.classification == "solid":
        evaluation.routing = "NEXT"
        evaluation.gap_description = None
        return evaluation

    if not evaluation.gap_description:
        evaluation.gap_description = "The learner has some correct pieces, but the causal mechanism is still incomplete."

    if evaluation.routing not in ("PROBE", "SCAFFOLD", "NEXT"):
        evaluation.routing = "NEXT" if probe_count >= 2 else "PROBE"

    return evaluation


def extract_knowledge_map(raw_text: str, api_key: str | None = None) -> str:
    client = _get_client(api_key)

    response = _call_gemini_with_retry(
        client,
        model=MODEL,
        contents=USER_PROMPT.format(text=raw_text),
        config=types.GenerateContentConfig(
            system_instruction=SKILL_PROMPT_PATH.read_text(),
            temperature=EXTRACT_TEMPERATURE,
        ),
    )

    return _clean_response(response.text)


def drill_chat(
    *,
    knowledge_map: dict,
    node_id: str,
    node_label: str,
    node_mechanism: str,
    messages: list[dict[str, str]],
    session_phase: str,
    probe_count: int = 0,
    nodes_drilled: int = 0,
    session_start_iso: str | None = None,
    api_key: str | None = None,
) -> DrillTurnResult:
    if session_phase not in {"init", "turn"}:
        raise ValueError("session_phase must be 'init' or 'turn'.")
    _validate_knowledge_map(knowledge_map)
    if not _knowledge_map_has_node(knowledge_map, node_id):
        raise ValueError(f"Unknown node_id: {node_id}")
    if session_phase == "init" and messages:
        raise ValueError("messages must be empty during init phase.")
    if session_phase == "turn" and not session_start_iso:
        raise ValueError("session_start_iso is required during turn phase.")

    if session_phase == "turn" and session_start_iso:
        session_start = _parse_iso_timestamp(session_start_iso)
        if (datetime.now(timezone.utc) - session_start).total_seconds() >= 35 * 60:
            return {
                "agent_response": "That's 35 minutes — a good stopping point. Your progress is saved. Pick up where you left off next session.",
                "classification": None,
                "gap_description": None,
                "routing": "SESSION_COMPLETE",
                "node_id": node_id,
                "probe_count": probe_count,
                "nodes_drilled": nodes_drilled,
                "session_terminated": True,
                "termination_reason": "time_cap",
            }

    client = _get_client(api_key)
    pruned_context = _prune_context(knowledge_map, node_id)
    system_prompt = (
        DRILL_SYSTEM_BASE
        + "\n\n### Target Node (ANSWER KEY — NEVER REVEAL)\n"
        + f"Node ID: {node_id}\n"
        + f"Node Label: {node_label}\n"
        + f"Mechanism: {node_mechanism}\n"
    )
    history = "\n".join(
        f"{msg.get('role', 'user').upper()}: {msg.get('content', '').strip()}"
        for msg in messages
        if msg.get("content", "").strip()
    ).strip()
    latest_learner_message = next(
        (
            msg.get("content", "").strip()
            for msg in reversed(messages)
            if msg.get("role") == "user" and msg.get("content", "").strip()
        ),
        "",
    )
    if session_phase == "turn" and not latest_learner_message:
        raise ValueError("A learner message is required during turn phase.")

    if session_phase == "init":
        prompt = (
            "Generate the opening drill question for the target node. "
            "Do not evaluate because there is no learner response yet.\n\n"
            f"Target node:\n- id: {node_id}\n- label: {node_label}\n"
            f"Knowledge map JSON:\n{json.dumps(pruned_context)}"
        )
    else:
        prompt = (
            "Evaluate the learner's latest response against the drill rubric and continue the drill.\n\n"
            f"Target node:\n- id: {node_id}\n- label: {node_label}\n"
            f"Knowledge map JSON:\n{json.dumps(pruned_context)}\n\n"
            f"Conversation so far:\n{history or 'USER: Start the drill.'}\n\n"
            f"Latest learner message:\n{latest_learner_message}"
        )

    response = _call_gemini_with_retry(
        client,
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=DRILL_TEMPERATURE,
            response_mime_type="application/json",
            response_schema=DrillEvaluation,
        ),
    )

    evaluation = response.parsed
    if not isinstance(evaluation, DrillEvaluation):
        raise ValueError("Gemini returned an invalid structured drill response.")
    if not evaluation.agent_response.strip():
        raise ValueError("Gemini returned an empty drill response.")
    evaluation = _normalize_drill_evaluation(
        evaluation,
        session_phase=session_phase,
        probe_count=probe_count,
    )
    print(
        "[drill] evaluation",
        json.dumps(
            {
                "node_id": node_id,
                "session_phase": session_phase,
                "classification": evaluation.classification,
                "routing": evaluation.routing,
                "gap_description": evaluation.gap_description,
                "probe_count_in": probe_count,
                "nodes_drilled_in": nodes_drilled,
            }
        ),
    )

    new_probe_count = probe_count
    new_nodes_drilled = nodes_drilled
    session_terminated = False
    termination_reason = None

    if session_phase == "init":
        pass
    elif evaluation.routing == "NEXT":
        new_probe_count = 0
        new_nodes_drilled += 1
        if new_nodes_drilled >= 4:
            session_terminated = True
            termination_reason = "node_cap"
    elif evaluation.routing in ("PROBE", "SCAFFOLD"):
        new_probe_count += 1
        if new_probe_count >= 3 and evaluation.classification != "solid":
            evaluation.routing = "NEXT"
            new_probe_count = 0
            new_nodes_drilled += 1
            if new_nodes_drilled >= 4:
                session_terminated = True
                termination_reason = "node_cap"

    return {
        "agent_response": evaluation.agent_response.strip(),
        "classification": evaluation.classification,
        "gap_description": evaluation.gap_description,
        "routing": evaluation.routing,
        "node_id": node_id,
        "probe_count": new_probe_count,
        "nodes_drilled": new_nodes_drilled,
        "session_terminated": session_terminated,
        "termination_reason": termination_reason,
    }
