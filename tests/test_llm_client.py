from __future__ import annotations

import logging

import pytest
from pydantic import BaseModel

from llm.client import LLMClient
from llm.errors import (
    LLMClientError,
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


def test_does_not_retry_on_validation_error():
    adapter = _CountingAdapter(raises=[LLMValidationError("bad shape")])
    client = LLMClient(adapter=adapter)
    with pytest.raises(LLMValidationError):
        client.generate_structured(_request())
    assert adapter.calls == 1


def test_does_not_retry_on_missing_key_error():
    adapter = _CountingAdapter(raises=[LLMMissingKeyError("no key")])
    client = LLMClient(adapter=adapter)
    with pytest.raises(LLMMissingKeyError):
        client.generate_structured(_request())
    assert adapter.calls == 1


def test_does_not_retry_on_client_error():
    """4xx-non-429 errors are permanent — LLMClient must NOT retry them.

    This was a real bug discovered live: an expired GEMINI_API_KEY (HTTP
    400) was being retried 3 times before giving up, wasting quota and
    time. LLMClientError is the fix; this test prevents regression.
    """
    adapter = _CountingAdapter(raises=[LLMClientError("expired key")])
    client = LLMClient(adapter=adapter)
    with pytest.raises(LLMClientError):
        client.generate_structured(_request())
    assert adapter.calls == 1


def test_emits_structured_log_on_success(caplog):
    adapter = _CountingAdapter()
    client = LLMClient(adapter=adapter)
    with caplog.at_level(logging.INFO, logger="llm.client"):
        client.generate_structured(_request())
    matches = [
        r
        for r in caplog.records
        if r.name == "llm.client"
        and getattr(r, "task_name", None) == "test_task"
        and getattr(r, "prompt_version", None) == "v1"
        and getattr(r, "provider", None) == "fake"
        and getattr(r, "input_tokens", None) == 1
        and getattr(r, "output_tokens", None) == 1
    ]
    assert matches, f"no structured success log matched. records: {caplog.records}"


def test_emits_structured_log_on_failure(caplog):
    adapter = _CountingAdapter(raises=[LLMValidationError("bad")])
    client = LLMClient(adapter=adapter)
    with caplog.at_level(logging.WARNING, logger="llm.client"):
        with pytest.raises(LLMValidationError):
            client.generate_structured(_request())
    matches = [
        r
        for r in caplog.records
        if r.name == "llm.client"
        and getattr(r, "task_name", None) == "test_task"
        and getattr(r, "error_class", None) == "LLMValidationError"
    ]
    assert matches, f"no structured failure log matched. records: {caplog.records}"
