"""Tests for generate_provisional_map_from_sketch."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ai_service import generate_provisional_map_from_sketch
from learning_commons import LCStandard
from llm.client import LLMClient
from llm.types import StructuredLLMResult, TokenUsage
from models.provisional_map import (
    BackboneItem, Cluster, Metadata, ProvisionalMap, Relationships, Subnode,
)


def _minimal_provisional_map(concept: str = "Photosynthesis") -> ProvisionalMap:
    return ProvisionalMap(
        metadata=Metadata(
            source_title=concept,
            core_thesis=f"{concept} is a process worth understanding.",
            architecture_type="causal_chain",
            difficulty="medium",
            governing_assumptions=["learner sketched a rough idea"],
            low_density=False,
        ),
        backbone=[
            BackboneItem(id="b1", principle="Stage 1", dependent_clusters=["c1"]),
        ],
        clusters=[
            Cluster(
                id="c1",
                label="First cluster",
                description="A single cluster",
                subnodes=[Subnode(id="c1_s1", label="A", mechanism="x")],
            ),
        ],
        relationships=Relationships(),
        frameworks=[],
    )


def _fake_llm_returning(map_obj: ProvisionalMap) -> LLMClient:
    fake = MagicMock(spec=LLMClient)
    fake.generate_structured.return_value = StructuredLLMResult(
        parsed=map_obj,
        raw_text="{}",
        usage=TokenUsage(input_tokens=420, output_tokens=180),
        latency_ms=1234.0,
        model="gemini-2.5-flash",
        provider="gemini",
    )
    return fake


def test_returns_provisional_map():
    result = generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light and somehow make sugar.",
        llm=_fake_llm_returning(_minimal_provisional_map()),
    )
    assert isinstance(result, ProvisionalMap)
    assert result.metadata.source_title == "Photosynthesis"


def test_user_prompt_includes_concept_and_sketch():
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light and somehow make sugar.",
        llm=fake,
    )
    request = fake.generate_structured.call_args.args[0]
    assert "Photosynthesis" in request.user_prompt
    assert "Plants take in light" in request.user_prompt
    assert "<concept>" in request.user_prompt
    assert "<starting_sketch>" in request.user_prompt


def test_user_prompt_omits_lc_context_block_when_none():
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light and make sugar.",
        llm=fake,
        lc_context=None,
    )
    request = fake.generate_structured.call_args.args[0]
    assert "<lc_context>" not in request.user_prompt


def test_user_prompt_includes_lc_context_block_when_provided():
    fake = _fake_llm_returning(_minimal_provisional_map())
    standards = [
        LCStandard(
            case_uuid="u-1", statement_code=None,
            description="Plants use light to make sugars.",
            jurisdiction="Multi-State", score=0.76,
        ),
        LCStandard(
            case_uuid="u-2", statement_code="HS-LS1-5",
            description="Photosynthesis converts light energy to stored chemical energy.",
            jurisdiction="Multi-State", score=0.74,
        ),
    ]
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light and make sugar.",
        llm=fake,
        lc_context=standards,
    )
    request = fake.generate_structured.call_args.args[0]
    assert "<lc_context>" in request.user_prompt
    assert "Plants use light to make sugars" in request.user_prompt
    assert "Photosynthesis converts light energy" in request.user_prompt


def test_uses_correct_system_prompt():
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light.",
        llm=fake,
    )
    request = fake.generate_structured.call_args.args[0]
    # System prompt must come from generate-from-sketch-system-v1.txt
    assert "Provisional concept map" in request.system_prompt
    assert "<starting_sketch>" in request.system_prompt
    assert "<lc_context>" in request.system_prompt


def test_response_schema_is_provisional_map():
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light.",
        llm=fake,
    )
    request = fake.generate_structured.call_args.args[0]
    assert request.response_schema is ProvisionalMap


def test_task_name_distinguishes_from_extraction():
    """Telemetry distinguishes source-less generation from source extraction."""
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light.",
        llm=fake,
    )
    request = fake.generate_structured.call_args.args[0]
    assert request.task_name == "provisional_map_from_sketch"
