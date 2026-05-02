"""Task 9 — extract_knowledge_map now returns a ProvisionalMap via LLMClient."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from llm.errors import (
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMValidationError,
)
from llm.types import StructuredLLMRequest, StructuredLLMResult, TokenUsage
from models import ProvisionalMap


VALID_MAP_DICT = {
    "metadata": {
        "source_title": "Test source",
        "core_thesis": "Test thesis.",
        "architecture_type": "system_description",
        "difficulty": "easy",
        "governing_assumptions": [],
        "low_density": False,
    },
    "backbone": [
        {"id": "b1", "principle": "test principle", "dependent_clusters": ["c1"]}
    ],
    "clusters": [
        {
            "id": "c1",
            "label": "x",
            "description": "x",
            "subnodes": [
                {
                    "id": "c1_s1",
                    "label": "x",
                    "mechanism": "x",
                    "drill_status": None,
                    "gap_type": None,
                    "gap_description": None,
                    "last_drilled": None,
                }
            ],
        }
    ],
    "relationships": {"domain_mechanics": [], "learning_prerequisites": []},
    "frameworks": [],
}


@dataclass
class _FakeClient:
    """Captures calls; returns a pre-built StructuredLLMResult."""
    response: StructuredLLMResult | None = None
    raises: Exception | None = None
    last_request: StructuredLLMRequest | None = None

    def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        self.last_request = request
        if self.raises is not None:
            raise self.raises
        return self.response  # type: ignore[return-value]


def _ok_result() -> StructuredLLMResult:
    return StructuredLLMResult(
        parsed=ProvisionalMap.model_validate(VALID_MAP_DICT),
        raw_text="{}",
        usage=TokenUsage(input_tokens=10, output_tokens=20),
        model="gemini-2.5-flash",
        provider="gemini",
        latency_ms=12.0,
    )


def test_extract_returns_provisional_map():
    from ai_service import extract_knowledge_map

    fake = _FakeClient(response=_ok_result())
    result = extract_knowledge_map(
        "raw text input here for extraction",
        llm=fake,
    )
    assert isinstance(result, ProvisionalMap)
    assert result.metadata.core_thesis == "Test thesis."


def test_extract_request_uses_provisional_map_schema():
    from ai_service import extract_knowledge_map

    fake = _FakeClient(response=_ok_result())
    extract_knowledge_map("some raw text", llm=fake)

    assert fake.last_request is not None
    assert fake.last_request.response_schema is ProvisionalMap
    assert fake.last_request.task_name == "provisional_map_generation"
    assert "some raw text" in fake.last_request.user_prompt


def test_extract_propagates_validation_error():
    from ai_service import extract_knowledge_map

    fake = _FakeClient(raises=LLMValidationError("bad shape", raw_text="{...}"))
    with pytest.raises(LLMValidationError):
        extract_knowledge_map("text", llm=fake)


def test_extract_propagates_rate_limit_and_missing_key():
    from ai_service import extract_knowledge_map

    for exc in (LLMRateLimitError("r"), LLMMissingKeyError("k")):
        fake = _FakeClient(raises=exc)
        with pytest.raises(type(exc)):
            extract_knowledge_map("text", llm=fake)
