import json
import os
import re
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
EXTRACT_FAILURE_LOG_PATH = Path(__file__).parent / "logs/extract-invalid-json.log"
EXTRACT_RUN_LOG_PATH = Path(__file__).parent / "logs/extract-runs.jsonl"
DRILL_RUN_LOG_PATH = Path(__file__).parent / "logs/drill-runs.jsonl"
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
    answer_mode: Optional[Literal["attempt", "help_request"]] = Field(
        default=None,
        description="Whether the learner made a genuine explanatory attempt or explicitly asked for help.",
    )
    score_eligible: bool = Field(
        default=False,
        description="True only when this turn should count as a scored explanatory attempt.",
    )
    help_request_reason: Optional[Literal["explicit_unknown", "explicit_explain_request", "affective_confusion", "none"]] = Field(
        default=None,
        description="Reason for help_request mode. Use null on init.",
    )
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
    response_tier: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Transient answer-quality tier for genuine attempts only.",
    )
    response_band: Optional[Literal["spark", "link", "chain", "clear", "tetris"]] = Field(
        default=None,
        description="Named band for response_tier.",
    )
    tier_reason: Optional[str] = Field(
        default=None,
        description="Short explanation of why the response earned its transient tier.",
    )


class DrillTurnResult(TypedDict):
    agent_response: str
    answer_mode: str | None
    score_eligible: bool
    help_request_reason: str | None
    classification: str | None
    gap_description: str | None
    routing: str | None
    response_tier: int | None
    response_band: str | None
    tier_reason: str | None
    node_id: str
    probe_count: int
    nodes_drilled: int
    attempt_turn_count: int
    help_turn_count: int
    graph_mutated: bool
    ux_reward_emitted: bool
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


def _log_extract_failure(*, reason: str, raw_response: str | None, cleaned_response: str | None = None) -> None:
    try:
        EXTRACT_FAILURE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EXTRACT_FAILURE_LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write("=" * 80 + "\n")
            log_file.write(f"timestamp: {datetime.now(timezone.utc).isoformat()}\n")
            log_file.write(f"reason: {reason}\n")
            log_file.write("raw_response:\n")
            log_file.write((raw_response or "").strip() or "<empty>")
            log_file.write("\n")
            if cleaned_response is not None and cleaned_response != raw_response:
                log_file.write("cleaned_response:\n")
                log_file.write(cleaned_response.strip() or "<empty>")
                log_file.write("\n")
    except Exception:
        # Logging must never break extraction error handling.
        pass


def _log_extract_run(event: dict) -> None:
    try:
        EXTRACT_RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EXTRACT_RUN_LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Logging must never break extraction error handling.
        pass


def _log_drill_run(event: dict) -> None:
    try:
        DRILL_RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DRILL_RUN_LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Logging must never break drill error handling.
        pass


def _with_telemetry_context(event: dict, telemetry_context: dict | None) -> dict:
    if not telemetry_context:
        return event
    merged = dict(event)
    for key, value in telemetry_context.items():
        if key not in merged:
            merged[key] = value
    return merged


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


def _infer_node_type(knowledge_map: dict, node_id: str) -> str:
    if node_id == "core-thesis":
        return "core"

    for backbone_item in knowledge_map.get("backbone", []):
        if isinstance(backbone_item, dict) and backbone_item.get("id") == node_id:
            return "backbone"

    for cluster in knowledge_map.get("clusters", []):
        if not isinstance(cluster, dict):
            continue
        if cluster.get("id") == node_id:
            return "cluster"
        for subnode in cluster.get("subnodes", []):
            if isinstance(subnode, dict) and subnode.get("id") == node_id:
                return "subnode"

    return "unknown"


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


def _infer_help_request_reason(message: str) -> str | None:
    normalized = " ".join((message or "").strip().lower().split())
    if not normalized:
        return None

    explicit_unknown_markers = (
        "i don't know",
        "i dont know",
        "idk",
        "no idea",
        "not sure",
        "i'm not sure",
        "im not sure",
        "unsure",
    )
    explain_request_markers = (
        "please explain",
        "can you explain",
        "could you explain",
        "explain that",
        "explain this",
        "break that down",
        "break this down",
        "walk me through",
        "help me understand",
        "what does that mean",
    )
    affective_confusion_markers = (
        "this is confusing",
        "i'm confused",
        "im confused",
        "confusing",
        "lost here",
    )

    if any(marker in normalized for marker in explicit_unknown_markers):
        return "explicit_unknown"
    if any(marker in normalized for marker in explain_request_markers):
        return "explicit_explain_request"
    if any(marker in normalized for marker in affective_confusion_markers):
        return "affective_confusion"
    return None


def _has_substantive_attempt(message: str) -> bool:
    normalized = " ".join((message or "").strip().lower().split())
    if not normalized:
        return False

    if "?" in normalized and not any(
        marker in normalized
        for marker in ("i think", "i guess", "maybe", "but", "it is", "it's", "they are", "this is")
    ):
        return False

    if re.search(
        r"\b("
        r"because|if|when|then|by|so that|causes?|leads? to|creates?|"
        r"means?|happens?|opens?|closes?|flows?|travels?|moves?|rushes?|"
        r"depolariz|repolariz"
        r")\b",
        normalized,
    ):
        return True

    words = re.findall(r"[a-z']+", normalized)
    if len(words) < 6:
        return False

    filler_words = {
        "i", "im", "i'm", "not", "sure", "don't", "dont", "know", "can", "you",
        "please", "explain", "this", "that", "it", "me", "help", "understand",
        "maybe", "think", "kind", "of", "sort", "just",
    }
    content_words = [word for word in words if word not in filler_words]
    return len(content_words) >= 4 and any(word.endswith(("s", "ed", "ing")) for word in content_words)


def _normalize_response_quality(evaluation: DrillEvaluation) -> None:
    if evaluation.answer_mode != "attempt":
        evaluation.response_tier = None
        evaluation.response_band = None
        evaluation.tier_reason = None
        return

    max_tier_by_classification = {
        "misconception": 1,
        "shallow": 2,
        "deep": 3,
        "solid": 5,
    }
    min_tier_by_classification = {
        "misconception": 1,
        "shallow": 1,
        "deep": 2,
        "solid": 3,
    }
    default_tier_by_classification = {
        "misconception": 1,
        "shallow": 2,
        "deep": 3,
        "solid": 4,
    }
    band_by_tier = {
        1: "spark",
        2: "link",
        3: "chain",
        4: "clear",
        5: "tetris",
    }

    if not evaluation.classification:
        evaluation.response_tier = None
        evaluation.response_band = None
        evaluation.tier_reason = None
        return

    tier = evaluation.response_tier or default_tier_by_classification[evaluation.classification]
    tier = max(min_tier_by_classification[evaluation.classification], tier)
    tier = min(max_tier_by_classification[evaluation.classification], tier)
    evaluation.response_tier = tier
    evaluation.response_band = band_by_tier[tier]


def _normalize_drill_evaluation(
    evaluation: DrillEvaluation,
    *,
    session_phase: str,
    probe_count: int,
    latest_learner_message: str,
) -> DrillEvaluation:
    if session_phase == "init":
        evaluation.answer_mode = None
        evaluation.score_eligible = False
        evaluation.help_request_reason = None
        evaluation.classification = None
        evaluation.routing = None
        evaluation.gap_description = None
        evaluation.response_tier = None
        evaluation.response_band = None
        evaluation.tier_reason = None
        return evaluation

    inferred_help_request_reason = _infer_help_request_reason(latest_learner_message)
    has_classification = bool(evaluation.classification)
    inferred_help_request = inferred_help_request_reason is not None
    substantive_attempt = _has_substantive_attempt(latest_learner_message)

    if not has_classification and (evaluation.answer_mode == "help_request" or inferred_help_request) and not substantive_attempt:
        evaluation.answer_mode = "help_request"
        evaluation.score_eligible = False
        evaluation.help_request_reason = evaluation.help_request_reason or inferred_help_request_reason or "explicit_unknown"
        evaluation.classification = None
        evaluation.routing = "SCAFFOLD"
        if not evaluation.gap_description:
            evaluation.gap_description = "The learner paused to ask for help and needs a simpler foothold before making another attempt."
        _normalize_response_quality(evaluation)
        return evaluation

    evaluation.answer_mode = "attempt"
    evaluation.score_eligible = True
    evaluation.help_request_reason = "none"

    if not evaluation.classification:
        raise ValueError("Gemini returned no classification for a scored drill evaluation turn.")

    if evaluation.classification == "solid":
        evaluation.routing = "NEXT"
        evaluation.gap_description = None
        _normalize_response_quality(evaluation)
        return evaluation

    if not evaluation.gap_description:
        evaluation.gap_description = "The learner has some correct pieces, but the causal mechanism is still incomplete."

    if evaluation.routing not in ("PROBE", "SCAFFOLD", "NEXT"):
        evaluation.routing = "NEXT" if probe_count >= 2 else "PROBE"

    _normalize_response_quality(evaluation)
    return evaluation


def extract_knowledge_map(
    raw_text: str,
    api_key: str | None = None,
    telemetry_context: dict | None = None,
) -> dict:
    client = _get_client(api_key)
    started_at = datetime.now(timezone.utc)
    started_perf = time.perf_counter()

    response = _call_gemini_with_retry(
        client,
        model=MODEL,
        contents=USER_PROMPT.format(text=raw_text),
        config=types.GenerateContentConfig(
            system_instruction=SKILL_PROMPT_PATH.read_text(),
            temperature=EXTRACT_TEMPERATURE,
        ),
    )

    raw_response = response.text
    try:
        cleaned = _clean_response(raw_response)
    except ValueError as err:
        _log_extract_failure(reason=str(err), raw_response=raw_response)
        _log_extract_run(_with_telemetry_context({
            "timestamp": started_at.isoformat(),
            "stage": "extract",
            "status": "error",
            "error_type": "empty_response",
            "reason": str(err),
            "model": MODEL,
            "prompt_version": SKILL_PROMPT_PATH.name,
            "input_chars": len(raw_text),
            "raw_response_chars": len(raw_response or ""),
            "duration_ms": round((time.perf_counter() - started_perf) * 1000, 2),
        }, telemetry_context))
        raise

    try:
        knowledge_map = json.loads(cleaned)
    except json.JSONDecodeError as err:
        _log_extract_failure(
            reason=f"Invalid JSON: {err.msg} at line {err.lineno} column {err.colno}",
            raw_response=raw_response,
            cleaned_response=cleaned,
        )
        _log_extract_run(_with_telemetry_context({
            "timestamp": started_at.isoformat(),
            "stage": "extract",
            "status": "error",
            "error_type": "invalid_json",
            "reason": f"{err.msg} at line {err.lineno} column {err.colno}",
            "model": MODEL,
            "prompt_version": SKILL_PROMPT_PATH.name,
            "input_chars": len(raw_text),
            "raw_response_chars": len(raw_response or ""),
            "cleaned_response_chars": len(cleaned),
            "duration_ms": round((time.perf_counter() - started_perf) * 1000, 2),
        }, telemetry_context))
        raise ValueError(f"Gemini returned invalid JSON for extraction: {err.msg}") from err

    try:
        _validate_knowledge_map(knowledge_map)
    except ValueError as err:
        _log_extract_failure(
            reason=f"Schema validation failed: {err}",
            raw_response=raw_response,
            cleaned_response=cleaned,
        )
        _log_extract_run(_with_telemetry_context({
            "timestamp": started_at.isoformat(),
            "stage": "extract",
            "status": "error",
            "error_type": "schema_validation",
            "reason": str(err),
            "model": MODEL,
            "prompt_version": SKILL_PROMPT_PATH.name,
            "input_chars": len(raw_text),
            "raw_response_chars": len(raw_response or ""),
            "cleaned_response_chars": len(cleaned),
            "duration_ms": round((time.perf_counter() - started_perf) * 1000, 2),
        }, telemetry_context))
        raise

    _log_extract_run(_with_telemetry_context({
        "timestamp": started_at.isoformat(),
        "stage": "extract",
        "status": "success",
        "model": MODEL,
        "prompt_version": SKILL_PROMPT_PATH.name,
        "input_chars": len(raw_text),
        "raw_response_chars": len(raw_response or ""),
        "cleaned_response_chars": len(cleaned),
        "duration_ms": round((time.perf_counter() - started_perf) * 1000, 2),
        "source_title": (knowledge_map.get("metadata") or {}).get("source_title"),
        "architecture_type": (knowledge_map.get("metadata") or {}).get("architecture_type"),
        "difficulty": (knowledge_map.get("metadata") or {}).get("difficulty"),
        "low_density": (knowledge_map.get("metadata") or {}).get("low_density"),
        "backbone_count": len(knowledge_map.get("backbone") or []),
        "cluster_count": len(knowledge_map.get("clusters") or []),
        "framework_count": len(knowledge_map.get("frameworks") or []),
        "subnode_count": sum(
            len(cluster.get("subnodes") or [])
            for cluster in (knowledge_map.get("clusters") or [])
            if isinstance(cluster, dict)
        ),
    }, telemetry_context))
    return knowledge_map


def drill_chat(
    *,
    knowledge_map: dict,
    concept_id: str | None = None,
    node_id: str,
    node_label: str,
    node_mechanism: str,
    messages: list[dict[str, str]],
    session_phase: str,
    probe_count: int = 0,
    nodes_drilled: int = 0,
    attempt_turn_count: int = 0,
    help_turn_count: int = 0,
    session_start_iso: str | None = None,
    api_key: str | None = None,
    telemetry_context: dict | None = None,
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

    started_at = datetime.now(timezone.utc)
    started_perf = time.perf_counter()
    node_type = _infer_node_type(knowledge_map, node_id)
    cluster_id = _resolve_target_cluster_id(knowledge_map, node_id)

    if session_phase == "turn" and session_start_iso:
        session_start = _parse_iso_timestamp(session_start_iso)
        if (datetime.now(timezone.utc) - session_start).total_seconds() >= 35 * 60:
            result = {
                "agent_response": "That's 35 minutes — a good stopping point. Your progress is saved. Pick up where you left off next session.",
                "answer_mode": None,
                "score_eligible": False,
                "help_request_reason": None,
                "classification": None,
                "gap_description": None,
                "routing": "SESSION_COMPLETE",
                "response_tier": None,
                "response_band": None,
                "tier_reason": None,
                "node_id": node_id,
                "probe_count": probe_count,
                "nodes_drilled": nodes_drilled,
                "attempt_turn_count": attempt_turn_count,
                "help_turn_count": help_turn_count,
                "graph_mutated": False,
                "ux_reward_emitted": False,
                "session_terminated": True,
                "termination_reason": "time_cap",
            }
            _log_drill_run(_with_telemetry_context({
                "timestamp": started_at.isoformat(),
                "stage": "drill",
                "status": "success",
                "model": MODEL,
                "prompt_version": DRILL_SKILL_PROMPT_PATH.name,
                "concept_id": concept_id,
                "node_id": node_id,
                "node_type": node_type,
                "cluster_id": cluster_id,
                "node_label": node_label,
                "session_phase": session_phase,
                "session_start_iso": session_start_iso,
                "message_count": len(messages),
                "latest_learner_chars": 0,
                "answer_mode": result["answer_mode"],
                "score_eligible": result["score_eligible"],
                "help_request_reason": result["help_request_reason"],
                "probe_count_in": probe_count,
                "probe_count_out": result["probe_count"],
                "nodes_drilled_in": nodes_drilled,
                "nodes_drilled_out": result["nodes_drilled"],
                "attempt_turn_count_in": attempt_turn_count,
                "attempt_turn_count_out": result["attempt_turn_count"],
                "help_turn_count_in": help_turn_count,
                "help_turn_count_out": result["help_turn_count"],
                "classification": result["classification"],
                "routing": result["routing"],
                "response_tier": result["response_tier"],
                "response_band": result["response_band"],
                "tier_reason": result["tier_reason"],
                "counted_as_probe": False,
                "force_advance_mode": "none",
                "graph_mutated": result["graph_mutated"],
                "ux_reward_emitted": result["ux_reward_emitted"],
                "session_terminated": result["session_terminated"],
                "termination_reason": result["termination_reason"],
                "agent_response_chars": len(result["agent_response"]),
                "duration_ms": round((time.perf_counter() - started_perf) * 1000, 2),
            }, telemetry_context))
            return result

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

    try:
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
    except Exception as err:
        _log_drill_run(_with_telemetry_context({
            "timestamp": started_at.isoformat(),
            "stage": "drill",
            "status": "error",
            "error_type": type(err).__name__,
            "reason": str(err),
            "model": MODEL,
            "prompt_version": DRILL_SKILL_PROMPT_PATH.name,
            "concept_id": concept_id,
            "node_id": node_id,
            "node_type": node_type,
            "cluster_id": cluster_id,
            "node_label": node_label,
            "session_phase": session_phase,
            "session_start_iso": session_start_iso,
            "message_count": len(messages),
            "latest_learner_chars": len(latest_learner_message),
            "answer_mode": None,
            "score_eligible": False,
            "help_request_reason": None,
            "probe_count_in": probe_count,
            "nodes_drilled_in": nodes_drilled,
            "attempt_turn_count_in": attempt_turn_count,
            "help_turn_count_in": help_turn_count,
            "duration_ms": round((time.perf_counter() - started_perf) * 1000, 2),
        }, telemetry_context))
        raise

    evaluation = response.parsed
    if not isinstance(evaluation, DrillEvaluation):
        _log_drill_run(_with_telemetry_context({
            "timestamp": started_at.isoformat(),
            "stage": "drill",
            "status": "error",
            "error_type": "invalid_structured_response",
            "reason": "Gemini returned an invalid structured drill response.",
            "model": MODEL,
            "prompt_version": DRILL_SKILL_PROMPT_PATH.name,
            "concept_id": concept_id,
            "node_id": node_id,
            "node_type": node_type,
            "cluster_id": cluster_id,
            "node_label": node_label,
            "session_phase": session_phase,
            "session_start_iso": session_start_iso,
            "message_count": len(messages),
            "latest_learner_chars": len(latest_learner_message),
            "answer_mode": None,
            "score_eligible": False,
            "help_request_reason": None,
            "probe_count_in": probe_count,
            "nodes_drilled_in": nodes_drilled,
            "attempt_turn_count_in": attempt_turn_count,
            "help_turn_count_in": help_turn_count,
            "duration_ms": round((time.perf_counter() - started_perf) * 1000, 2),
        }, telemetry_context))
        raise ValueError("Gemini returned an invalid structured drill response.")
    if not evaluation.agent_response.strip():
        _log_drill_run(_with_telemetry_context({
            "timestamp": started_at.isoformat(),
            "stage": "drill",
            "status": "error",
            "error_type": "empty_agent_response",
            "reason": "Gemini returned an empty drill response.",
            "model": MODEL,
            "prompt_version": DRILL_SKILL_PROMPT_PATH.name,
            "concept_id": concept_id,
            "node_id": node_id,
            "node_type": node_type,
            "cluster_id": cluster_id,
            "node_label": node_label,
            "session_phase": session_phase,
            "session_start_iso": session_start_iso,
            "message_count": len(messages),
            "latest_learner_chars": len(latest_learner_message),
            "answer_mode": None,
            "score_eligible": False,
            "help_request_reason": None,
            "probe_count_in": probe_count,
            "nodes_drilled_in": nodes_drilled,
            "attempt_turn_count_in": attempt_turn_count,
            "help_turn_count_in": help_turn_count,
            "duration_ms": round((time.perf_counter() - started_perf) * 1000, 2),
        }, telemetry_context))
        raise ValueError("Gemini returned an empty drill response.")
    evaluation = _normalize_drill_evaluation(
        evaluation,
        session_phase=session_phase,
        probe_count=probe_count,
        latest_learner_message=latest_learner_message,
    )

    new_probe_count = probe_count
    new_nodes_drilled = nodes_drilled
    new_attempt_turn_count = attempt_turn_count
    new_help_turn_count = help_turn_count
    session_terminated = False
    termination_reason = None

    if session_phase == "init":
        pass
    elif evaluation.answer_mode == "help_request":
        new_help_turn_count += 1
    elif evaluation.routing == "NEXT":
        new_attempt_turn_count += 1
        new_probe_count = 0
        new_nodes_drilled += 1
        if new_nodes_drilled >= 4:
            session_terminated = True
            termination_reason = "node_cap"
    elif evaluation.routing in ("PROBE", "SCAFFOLD"):
        new_attempt_turn_count += 1
        new_probe_count += 1
        if new_probe_count >= 3 and evaluation.classification != "solid":
            evaluation.routing = "NEXT"
            new_probe_count = 0
            new_nodes_drilled += 1
            if new_nodes_drilled >= 4:
                session_terminated = True
                termination_reason = "node_cap"

    result = {
        "agent_response": evaluation.agent_response.strip(),
        "answer_mode": evaluation.answer_mode,
        "score_eligible": evaluation.score_eligible,
        "help_request_reason": evaluation.help_request_reason,
        "classification": evaluation.classification,
        "gap_description": evaluation.gap_description,
        "routing": evaluation.routing,
        "response_tier": evaluation.response_tier,
        "response_band": evaluation.response_band,
        "tier_reason": evaluation.tier_reason,
        "node_id": node_id,
        "probe_count": new_probe_count,
        "nodes_drilled": new_nodes_drilled,
        "attempt_turn_count": new_attempt_turn_count,
        "help_turn_count": new_help_turn_count,
        "graph_mutated": evaluation.routing == "NEXT",
        "ux_reward_emitted": evaluation.answer_mode == "attempt" and (evaluation.response_tier or 0) >= 4,
        "session_terminated": session_terminated,
        "termination_reason": termination_reason,
    }
    force_advanced = (
        session_phase == "turn"
        and result["answer_mode"] == "attempt"
        and result["routing"] == "NEXT"
        and result["classification"] not in (None, "solid")
        and probe_count >= 2
    )
    counted_as_probe = (
        session_phase == "turn"
        and result["answer_mode"] == "attempt"
        and result["routing"] in ("PROBE", "SCAFFOLD")
    )
    _log_drill_run(_with_telemetry_context({
        "timestamp": started_at.isoformat(),
        "stage": "drill",
        "status": "success",
        "model": MODEL,
        "prompt_version": DRILL_SKILL_PROMPT_PATH.name,
        "concept_id": concept_id,
        "node_id": node_id,
        "node_type": node_type,
        "cluster_id": cluster_id,
        "node_label": node_label,
        "session_phase": session_phase,
        "session_start_iso": session_start_iso,
        "message_count": len(messages),
        "latest_learner_chars": len(latest_learner_message),
        "answer_mode": result["answer_mode"],
        "score_eligible": result["score_eligible"],
        "help_request_reason": result["help_request_reason"],
        "probe_count_in": probe_count,
        "probe_count_out": result["probe_count"],
        "nodes_drilled_in": nodes_drilled,
        "nodes_drilled_out": result["nodes_drilled"],
        "attempt_turn_count_in": attempt_turn_count,
        "attempt_turn_count_out": result["attempt_turn_count"],
        "help_turn_count_in": help_turn_count,
        "help_turn_count_out": result["help_turn_count"],
        "classification": result["classification"],
        "routing": result["routing"],
        "response_tier": result["response_tier"],
        "response_band": result["response_band"],
        "tier_reason": result["tier_reason"],
        "counted_as_probe": counted_as_probe,
        "force_advanced": force_advanced,
        "force_advance_mode": "attempt" if force_advanced else "none",
        "graph_mutated": result["graph_mutated"],
        "ux_reward_emitted": result["ux_reward_emitted"],
        "session_terminated": result["session_terminated"],
        "termination_reason": result["termination_reason"],
        "agent_response_chars": len(result["agent_response"]),
        "duration_ms": round((time.perf_counter() - started_perf) * 1000, 2),
    }, telemetry_context))
    return result
