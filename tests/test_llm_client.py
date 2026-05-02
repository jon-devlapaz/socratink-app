from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm.client import LLMClient
from llm.errors import (
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)
from llm.types import StructuredLLMRequest, StructuredLLMResult, TokenUsage


class _Schema(BaseModel):
    x: str


def _ok_result() -> StructuredLLMResult:
    return StructuredLLMResult(
        parsed=_Schema(x="ok"),
        raw_text='{"x":"ok"}',
        usage=TokenUsage(input_tokens=1, output_tokens=1),
        model="fake",
        provider="fake",
        latency_ms=10.0,
    )


def _request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        system_prompt="sys",
        user_prompt="user",
        response_schema=_Schema,
        max_retries=2,
        task_name="test_task",
        prompt_version="v1",
    )


class _CountingAdapter:
    """Minimal LLMAdapter — counts calls; can be primed to raise or return."""

    def __init__(self, *, raises=None, returns=None):
        self.calls = 0
        self._raises = list(raises) if raises else []
        self._returns = returns

    def call_once(self, request):
        self.calls += 1
        if self._raises:
            exc = self._raises.pop(0)
            if exc is not None:
                raise exc
        return self._returns or _ok_result()


def test_happy_path_delegates_once():
    adapter = _CountingAdapter()
    client = LLMClient(adapter=adapter)
    result = client.generate_structured(_request())
    assert result.parsed.x == "ok"
    assert adapter.calls == 1


def test_retries_on_rate_limit_then_succeeds():
    adapter = _CountingAdapter(raises=[LLMRateLimitError("rate"), None])
    client = LLMClient(adapter=adapter)
    result = client.generate_structured(_request())
    assert result.parsed.x == "ok"
    assert adapter.calls == 2  # one fail + one success


def test_retries_on_service_error_then_succeeds():
    adapter = _CountingAdapter(raises=[LLMServiceError("svc"), None])
    client = LLMClient(adapter=adapter)
    result = client.generate_structured(_request())
    assert result.parsed.x == "ok"
    assert adapter.calls == 2


def test_gives_up_after_max_retries_on_rate_limit():
    adapter = _CountingAdapter(
        raises=[
            LLMRateLimitError("r1"),
            LLMRateLimitError("r2"),
            LLMRateLimitError("r3"),
        ]
    )
    client = LLMClient(adapter=adapter)
    with pytest.raises(LLMRateLimitError):
        client.generate_structured(_request())
    # max_retries=2 → up to 2 retries beyond initial → 3 total calls
    assert adapter.calls == 3
