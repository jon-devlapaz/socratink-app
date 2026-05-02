import pytest
from pydantic import BaseModel

from llm.types import StructuredLLMRequest, StructuredLLMResult, TokenUsage


class _DummySchema(BaseModel):
    foo: str


def test_request_constructs_with_required_and_defaults():
    req = StructuredLLMRequest(
        system_prompt="sys",
        user_prompt="user",
        response_schema=_DummySchema,
    )
    assert req.system_prompt == "sys"
    assert req.user_prompt == "user"
    assert req.response_schema is _DummySchema
    assert req.temperature == 0.0
    assert req.max_retries == 2
    assert req.task_name is None
    assert req.prompt_version is None


def test_request_is_frozen():
    req = StructuredLLMRequest(
        system_prompt="s", user_prompt="u", response_schema=_DummySchema
    )
    with pytest.raises(Exception):
        req.temperature = 0.5  # type: ignore[misc]


def test_token_usage_constructs():
    usage = TokenUsage(input_tokens=100, output_tokens=50)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50


def test_result_constructs():
    parsed = _DummySchema(foo="bar")
    usage = TokenUsage(input_tokens=10, output_tokens=20)
    result = StructuredLLMResult(
        parsed=parsed,
        raw_text='{"foo": "bar"}',
        usage=usage,
        model="gemini-2.5-flash",
        provider="gemini",
        latency_ms=123.4,
    )
    assert result.parsed is parsed
    assert result.usage.input_tokens == 10
    assert result.provider == "gemini"
    assert result.raw_provider_metadata is None
