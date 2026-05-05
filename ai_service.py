import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Optional, TypedDict, TYPE_CHECKING, cast

from llm.types import StructuredLLMResult

if TYPE_CHECKING:
    from learning_commons import LCStandard

from google import genai
from google.genai.errors import APIError
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field

from llm import (
    LLMClient,
    StructuredLLMRequest,
    build_llm_client,
)
from models import ProvisionalMap

MODEL = "gemini-2.5-flash"
EXTRACT_TEMPERATURE = 0.2
DRILL_TEMPERATURE = 0.2
REPAIR_REPS_TEMPERATURE = 0.2
PROMPT_DIR = Path(__file__).parent / "app_prompts"
EXTRACT_PROMPT_PATH = PROMPT_DIR / "extract-system-v1.txt"
DRILL_PROMPT_PATH = PROMPT_DIR / "drill-system-v1.md"
REPAIR_REPS_PROMPT_PATH = PROMPT_DIR / "repair-reps-system-v1.md"
EXTRACT_PROMPT_VERSION = "extract-system-v1"
DRILL_PROMPT_VERSION = "drill-system-v1"
REPAIR_REPS_PROMPT_VERSION = "repair-reps-system-v1"
DRILL_SYSTEM_BASE = DRILL_PROMPT_PATH.read_text()
REPAIR_REPS_SYSTEM_BASE = REPAIR_REPS_PROMPT_PATH.read_text()
# Source-less generation (spec §5.1).
GENERATE_FROM_SKETCH_PROMPT_PATH = PROMPT_DIR / "generate-from-sketch-system-v1.txt"
GENERATE_FROM_SKETCH_PROMPT_VERSION = "v1"
GENERATE_FROM_SKETCH_TEMPERATURE = 0.4  # slightly higher than extraction; we want a hypothesis, not a transcription
MAX_RETRIES = 3
BACKOFF_BASE = 2
RETRYABLE_CODES = {429, 503, 500}
DRILL_SESSION_TIME_LIMIT_ENV = "DRILL_SESSION_TIME_LIMIT_SECONDS"
DISABLED_TIME_LIMIT_VALUES = {"", "0", "off", "none", "null", "disabled", "false"}

USER_PROMPT = (
    "Execute the full extraction pipeline on the following text and return ONLY "
    "the valid JSON object as specified in your instructions. "
    "No preamble, no explanation, no code fences — raw JSON only:\n\n{text}"
)


def get_drill_session_time_limit_seconds() -> int | None:
    raw_limit = os.environ.get(DRILL_SESSION_TIME_LIMIT_ENV, "").strip().lower()
    if raw_limit in DISABLED_TIME_LIMIT_VALUES:
        return None
    try:
        limit_seconds = int(raw_limit)
    except ValueError as exc:
        raise ValueError(
            f"{DRILL_SESSION_TIME_LIMIT_ENV} must be a positive integer or disabled."
        ) from exc
    if limit_seconds <= 0:
        return None
    return limit_seconds


class DrillEvaluation(BaseModel):
    agent_response: str = Field(description="The conversational text shown to the user")
    generative_commitment: Optional[bool] = Field(
        default=None,
        description="True if the learner made a genuine explanatory attempt.",
    )
    answer_mode: Optional[Literal["attempt", "help_request"]] = Field(
        default=None,
        description="Whether the learner made a genuine explanatory attempt or explicitly asked for help.",
    )
    score_eligible: bool = Field(
        default=False,
        description="True only when this turn should count as a scored explanatory attempt.",
    )
    help_request_reason: Optional[
        Literal[
            "explicit_unknown",
            "explicit_explain_request",
            "affective_confusion",
            "none",
        ]
    ] = Field(
        default=None,
        description="Reason for help_request mode. Use null on init.",
    )
    classification: Optional[Literal["solid", "shallow", "deep", "misconception"]] = (
        Field(
            default=None,
            description="Gap classification. null on init phase and before genuine generative attempt.",
        )
    )
    gap_description: Optional[str] = Field(
        default=None,
        description="1-sentence description of the delta between user knowledge and mechanism.",
    )
    routing: Optional[
        Literal["NEXT", "PROBE", "SCAFFOLD", "REROUTE_PREREQ", "SESSION_COMPLETE"]
    ] = Field(
        default=None,
        description="Routing action for the frontend to execute.",
    )
    response_tier: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Transient answer-quality tier for genuine attempts only.",
    )
    response_band: Optional[Literal["spark", "link", "chain", "clear", "tetris"]] = (
        Field(
            default=None,
            description="Named band for response_tier.",
        )
    )
    tier_reason: Optional[str] = Field(
        default=None,
        description="Short explanation of why the response earned its transient tier.",
    )


class RepairRep(BaseModel):
    id: str = Field(
        description="Stable identifier for this rep within the generated set"
    )
    kind: Literal["missing_bridge", "next_step", "cause_effect"] = Field(
        description="The causal micro-practice shape."
    )
    prompt: str = Field(
        description="Typed causal prompt shown before the answer bridge is revealed."
    )
    target_bridge: str = Field(
        description="Short model bridge revealed only after the learner types."
    )
    feedback_cue: str = Field(
        description="Short comparison cue after the bridge is revealed."
    )


class RepairRepsEvaluation(BaseModel):
    reps: list[RepairRep] = Field(
        description="Exactly three typed causal repair reps.",
        min_length=3,
        max_length=3,
    )


class _StrictRepairRep(RepairRep):
    model_config = ConfigDict(extra="forbid")


class _StrictRepairRepsEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reps: list[_StrictRepairRep] = Field(
        description="Exactly three typed causal repair reps.",
        min_length=3,
        max_length=3,
    )


class DrillTurnResult(TypedDict):
    agent_response: str
    generative_commitment: bool | None
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


class RepairRepsResult(TypedDict):
    node_id: str
    prompt_version: str
    reps: list[dict[str, str]]


class MissingAPIKeyError(ValueError):
    pass


class GeminiRateLimitError(ValueError):
    pass


class GeminiServiceError(ValueError):
    pass


def _get_client(api_key: str | None = None):
    key = os.environ.get("GEMINI_API_KEY") or api_key
    if not key:
        raise MissingAPIKeyError(
            "No Gemini API key configured. Add one in Settings or set GEMINI_API_KEY in .env."
        )
    return genai.Client(api_key=key)


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
    pruned: dict[str, Any] = {
        "metadata": {
            "thesis": metadata.get("core_thesis"),
            "governing_assumptions": metadata.get("governing_assumptions") or [],
            "starting_map_context": metadata.get("starting_map_context"),
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
                    target_node_id == "core-thesis" or item.get("id") == target_node_id
                )
            ),
            None,
        )
        if target_backbone is None and knowledge_map.get("backbone"):
            target_backbone = knowledge_map["backbone"][0]

        dependent_cluster_ids = (
            set(target_backbone.get("dependent_clusters") or [])
            if isinstance(target_backbone, dict)
            else set()
        )
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
        if isinstance(item, dict)
        and target_cluster_id in (item.get("dependent_clusters") or [])
    ]
    pruned["relationships"] = {
        "learning_prerequisites": [
            rel
            for rel in relationships.get("learning_prerequisites", [])
            if isinstance(rel, dict)
            and (
                rel.get("from") == target_cluster_id
                or rel.get("to") == target_cluster_id
            )
        ]
    }
    pruned["frameworks"] = [
        framework
        for framework in frameworks
        if isinstance(framework, dict)
        and target_cluster_id in (framework.get("source_clusters") or [])
    ]
    return pruned


def _call_gemini_with_retry(
    client, *, model, contents, config, max_retries=MAX_RETRIES
):
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
                raise GeminiRateLimitError(
                    "Gemini rate limit hit. Try again in 60s."
                ) from err
            if err.code in (503, 500):
                raise GeminiServiceError(
                    f"Gemini service unavailable (HTTP {err.code})."
                ) from err
            raise ValueError(
                f"Gemini API error (HTTP {err.code}): {err.message}"
            ) from err
        except Exception as err:
            raise ValueError(f"Unexpected error: {str(err)}") from err


def _infer_help_request_reason(message: str) -> Literal["explicit_unknown", "explicit_explain_request", "affective_confusion"] | None:
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
        for marker in (
            "i think",
            "i guess",
            "maybe",
            "but",
            "it is",
            "it's",
            "they are",
            "this is",
        )
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
        "i",
        "im",
        "i'm",
        "not",
        "sure",
        "don't",
        "dont",
        "know",
        "can",
        "you",
        "please",
        "explain",
        "this",
        "that",
        "it",
        "me",
        "help",
        "understand",
        "maybe",
        "think",
        "kind",
        "of",
        "sort",
        "just",
    }
    content_words = [word for word in words if word not in filler_words]
    return len(content_words) >= 4 and any(
        word.endswith(("s", "ed", "ing")) for word in content_words
    )


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
    band_by_tier: dict[int, Literal["spark", "link", "chain", "clear", "tetris"]] = {
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

    tier = (
        evaluation.response_tier
        or default_tier_by_classification[evaluation.classification]
    )
    tier = max(min_tier_by_classification[evaluation.classification], tier)
    tier = min(max_tier_by_classification[evaluation.classification], tier)
    evaluation.response_tier = tier
    evaluation.response_band = band_by_tier[tier]


def _normalize_drill_evaluation(
    evaluation: DrillEvaluation,
    *,
    session_phase: str,
    drill_mode: str,
    probe_count: int,
    latest_learner_message: str,
) -> DrillEvaluation:
    if session_phase == "init":
        evaluation.generative_commitment = None
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
    evaluation.generative_commitment = substantive_attempt

    if drill_mode == "cold_attempt":
        evaluation.answer_mode = "attempt" if substantive_attempt else "help_request"
        evaluation.score_eligible = False
        evaluation.classification = None
        evaluation.response_tier = None
        evaluation.response_band = None
        evaluation.tier_reason = None
        if not substantive_attempt:
            evaluation.routing = "SCAFFOLD"
            evaluation.help_request_reason = (
                evaluation.help_request_reason or "explicit_unknown"
            )
            if not evaluation.gap_description:
                evaluation.gap_description = (
                    "Learner produced zero schema; nudge to guess."
                )
        else:
            evaluation.routing = "NEXT"
            evaluation.help_request_reason = "none"
        return evaluation

    if (
        not has_classification
        and (evaluation.answer_mode == "help_request" or inferred_help_request)
        and not substantive_attempt
    ):
        evaluation.answer_mode = "help_request"
        evaluation.score_eligible = False
        evaluation.help_request_reason = (
            evaluation.help_request_reason
            or inferred_help_request_reason
            or "explicit_unknown"
        )
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
        raise ValueError(
            "Gemini returned no classification for a scored drill evaluation turn."
        )

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
    *,
    llm: LLMClient | None = None,
    api_key: str | None = None,
    telemetry_context: dict | None = None,
    on_call_complete: Callable[["StructuredLLMResult"], None] | None = None,
) -> ProvisionalMap:
    """Generate a Provisional map from learner-supplied text.

    The application sees a typed ProvisionalMap, never a dict and never
    a Gemini-shaped response. All provider-specific behavior lives behind
    the LLMClient seam (see llm/ package). The closure validators on
    ProvisionalMap enforce the structural rules from extract-system-v1.txt.
    """
    client: LLMClient = llm if llm is not None else build_llm_client(api_key=api_key)
    request = StructuredLLMRequest(
        system_prompt=EXTRACT_PROMPT_PATH.read_text(),
        user_prompt=USER_PROMPT.format(text=raw_text),
        response_schema=ProvisionalMap,
        temperature=EXTRACT_TEMPERATURE,
        task_name="provisional_map_generation",
        prompt_version=EXTRACT_PROMPT_VERSION,
    )
    result = client.generate_structured(request)
    if on_call_complete is not None:
        on_call_complete(result)
    # Adapter guarantees parsed is a ProvisionalMap or it raised
    # LLMValidationError. The cast is for type-checker clarity.
    return result.parsed  # type: ignore[return-value]


def generate_provisional_map_from_sketch(
    concept: str,
    sketch: str,
    *,
    llm: LLMClient | None = None,
    api_key: str | None = None,
    lc_context: list["LCStandard"] | None = None,
    telemetry_context: dict | None = None,
    on_call_complete: Callable[["StructuredLLMResult"], None] | None = None,
) -> ProvisionalMap:
    """Generate a Provisional map from concept name + learner sketch alone.

    Spec §3.3.2, §5.1. The sketch is the baseline; the AI hypothesizes
    structure around it. Optional ``lc_context`` is grounding-only,
    never authoritative.

    Returns a structurally-validated ProvisionalMap. Same Pydantic model
    as extraction; same closure validators; same error semantics.
    """
    from learning_commons import LCStandard  # local import to avoid cycle on module load

    client: LLMClient = llm if llm is not None else build_llm_client(api_key=api_key)

    user_prompt_parts: list[str] = [
        f"<concept>{concept}</concept>",
        f"<starting_sketch>{sketch}</starting_sketch>",
    ]
    if lc_context:
        lc_block_lines = ["<lc_context>"]
        for std in lc_context:
            code = f" [{std.statement_code}]" if std.statement_code else ""
            lc_block_lines.append(f"- {std.jurisdiction}{code}: {std.description}")
        lc_block_lines.append("</lc_context>")
        user_prompt_parts.append("\n".join(lc_block_lines))

    user_prompt = "\n\n".join(user_prompt_parts)

    request = StructuredLLMRequest(
        system_prompt=GENERATE_FROM_SKETCH_PROMPT_PATH.read_text(),
        user_prompt=user_prompt,
        response_schema=ProvisionalMap,
        temperature=GENERATE_FROM_SKETCH_TEMPERATURE,
        task_name="provisional_map_from_sketch",
        prompt_version=GENERATE_FROM_SKETCH_PROMPT_VERSION,
    )
    result = client.generate_structured(request)
    if on_call_complete is not None:
        on_call_complete(result)
    return result.parsed  # type: ignore[return-value]


def _validate_repair_reps_result(
    evaluation: RepairRepsEvaluation, *, expected_count: int
) -> None:
    if len(evaluation.reps) != expected_count:
        raise ValueError(
            f"Repair reps response must include exactly {expected_count} reps."
        )

    seen_ids: set[str] = set()
    for index, rep in enumerate(evaluation.reps, start=1):
        rep_id = rep.id.strip()
        if not rep_id:
            raise ValueError(f"Repair rep {index} is missing an id.")
        if rep_id in seen_ids:
            raise ValueError(f"Repair rep id is duplicated: {rep_id}")
        seen_ids.add(rep_id)

        if not rep.prompt.strip():
            raise ValueError(f"Repair rep {index} is missing a prompt.")
        if not rep.target_bridge.strip():
            raise ValueError(f"Repair rep {index} is missing a target bridge.")
        if not rep.feedback_cue.strip():
            raise ValueError(f"Repair rep {index} is missing a feedback cue.")


def _parse_repair_reps_response(response) -> RepairRepsEvaluation:
    raw_text = getattr(response, "text", None)
    if raw_text:
        try:
            strict = _StrictRepairRepsEvaluation.model_validate_json(raw_text)
        except Exception as err:
            raise ValueError(
                "Gemini returned an invalid structured repair reps response."
            ) from err
        return RepairRepsEvaluation.model_validate(strict.model_dump())

    evaluation = getattr(response, "parsed", None)
    if isinstance(evaluation, RepairRepsEvaluation):
        return evaluation
    if isinstance(evaluation, dict):
        try:
            strict = _StrictRepairRepsEvaluation.model_validate(evaluation)
        except Exception as err:
            raise ValueError(
                "Gemini returned an invalid structured repair reps response."
            ) from err
        return RepairRepsEvaluation.model_validate(strict.model_dump())
    raise ValueError("Gemini returned an invalid structured repair reps response.")


def generate_repair_reps(
    *,
    knowledge_map: dict,
    concept_id: str | None = None,
    node_id: str,
    node_label: str,
    node_mechanism: str,
    gap_type: str | None = None,
    gap_description: str | None = None,
    count: int = 3,
    api_key: str | None = None,
) -> RepairRepsResult:
    _validate_knowledge_map(knowledge_map)
    if not _knowledge_map_has_node(knowledge_map, node_id):
        raise ValueError(f"Unknown node_id: {node_id}")
    if count != 3:
        raise ValueError("Repair Reps MVP requires exactly 3 reps.")

    client = _get_client(api_key)
    pruned_context = _prune_context(knowledge_map, node_id)
    prompt = (
        "Generate exactly three Repair Reps for the target node. "
        "Each rep must require typed causal reconstruction and must not use term-definition review, "
        "multiple choice, or mastery/progression language.\n\n"
        f"Concept ID: {concept_id or 'unknown'}\n"
        f"Target node:\n- id: {node_id}\n- label: {node_label}\n"
        f"Mechanism answer key:\n{node_mechanism}\n\n"
        f"Known gap type: {gap_type or 'none'}\n"
        f"Known gap description: {gap_description or 'none'}\n\n"
        f"Pruned knowledge map JSON:\n{json.dumps(pruned_context)}"
    )

    response = _call_gemini_with_retry(
        client,
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=REPAIR_REPS_SYSTEM_BASE,
            temperature=REPAIR_REPS_TEMPERATURE,
            response_mime_type="application/json",
            response_schema=RepairRepsEvaluation,
        ),
    )

    evaluation = _parse_repair_reps_response(response)
    _validate_repair_reps_result(evaluation, expected_count=count)

    return {
        "node_id": node_id,
        "prompt_version": REPAIR_REPS_PROMPT_VERSION,
        "reps": [
            {
                "id": rep.id.strip(),
                "kind": rep.kind,
                "prompt": rep.prompt.strip(),
                "target_bridge": rep.target_bridge.strip(),
                "feedback_cue": rep.feedback_cue.strip(),
            }
            for rep in evaluation.reps
        ],
    }


def drill_chat(
    *,
    knowledge_map: dict,
    concept_id: str | None = None,
    node_id: str,
    node_label: str,
    node_mechanism: str,
    messages: list[dict[str, str]],
    session_phase: str,
    drill_mode: str = "re_drill",
    re_drill_count: int = 0,
    probe_count: int = 0,
    nodes_drilled: int = 0,
    attempt_turn_count: int = 0,
    help_turn_count: int = 0,
    session_start_iso: str | None = None,
    bypass_session_limits: bool = False,
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

    latest_learner_message = next(
        (
            msg.get("content", "").strip()
            for msg in reversed(messages)
            if msg.get("role") == "user" and msg.get("content", "").strip()
        ),
        "",
    )

    session_time_limit_seconds = get_drill_session_time_limit_seconds()
    if (
        not bypass_session_limits
        and session_phase == "turn"
        and session_start_iso
        and session_time_limit_seconds is not None
    ):
        session_start = _parse_iso_timestamp(session_start_iso)
        if (
            datetime.now(timezone.utc) - session_start
        ).total_seconds() >= session_time_limit_seconds:
            result: DrillTurnResult = {
                "agent_response": "That's a good stopping point. Your progress is saved. Pick up where you left off next session.",
                "generative_commitment": None,
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
            return result

    client = _get_client(api_key)
    pruned_context = _prune_context(knowledge_map, node_id)
    system_prompt_extras = "\n\n### Target Node (ANSWER KEY — NEVER REVEAL)\n"
    system_prompt_extras += (
        f"Node ID: {node_id}\nNode Label: {node_label}\nMechanism: {node_mechanism}\n"
    )

    if drill_mode == "cold_attempt":
        system_prompt_extras += "\nMODE: COLD ATTEMPT. Ask an open exploratory question, do not reveal the mechanism. If metadata.starting_map_context is present, reference it as global context in one short clause, then ask one smaller target-node question. Do not treat the threshold as evidence, confidence, or diagnosis. Emphasize it is ok to guess. Enforce minimum generative commitment. If the user produces zero schema or asks for help, provide a tiny hint or nudge to guess. Return null for classification/tier."
    else:
        system_prompt_extras += f"\nMODE: RE-DRILL (Attempt {re_drill_count + 1}). Demand multi-step causal reconstruction. Vary prompt angle (e.g. self-explanation, summarization, teaching, problem-posing). Apply concrete rubric: Does response contain (a) initiating condition, (b) causal transition, and (c) resulting state? Err toward false negatives."
        if re_drill_count >= 2:
            system_prompt_extras += "\nBOTTLENECK RECOVERY: The learner has failed multiple re-drills on this node. Escalate scaffolding, simplify the gap, and walk them through."

    system_prompt = DRILL_SYSTEM_BASE + system_prompt_extras
    history = "\n".join(
        f"{msg.get('role', 'user').upper()}: {msg.get('content', '').strip()}"
        for msg in messages
        if msg.get("content", "").strip()
    ).strip()

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
        drill_mode=drill_mode,
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
        if not bypass_session_limits and new_nodes_drilled >= 4:
            session_terminated = True
            termination_reason = "node_cap"
    elif evaluation.routing in ("PROBE", "SCAFFOLD"):
        new_attempt_turn_count += 1
        new_probe_count += 1
        if new_probe_count >= 3 and evaluation.classification != "solid":
            evaluation.routing = "NEXT"
            new_probe_count = 0
            new_nodes_drilled += 1
            if not bypass_session_limits and new_nodes_drilled >= 4:
                session_terminated = True
                termination_reason = "node_cap"

    result = cast(DrillTurnResult, {
        "agent_response": evaluation.agent_response.strip(),
        "generative_commitment": evaluation.generative_commitment,
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
        "ux_reward_emitted": evaluation.answer_mode == "attempt"
        and (evaluation.response_tier or 0) >= 4,
        "session_terminated": session_terminated,
        "termination_reason": termination_reason,
    })
    return result

