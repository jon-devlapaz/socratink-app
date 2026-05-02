from pydantic import BaseModel

from llm.adapter import LLMAdapter
from llm.types import StructuredLLMRequest, StructuredLLMResult, TokenUsage


class _Schema(BaseModel):
    x: str


class FakeAdapter:
    """A duck-typed adapter that should satisfy the Protocol."""

    def call_once(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        parsed = _Schema(x="ok")
        return StructuredLLMResult(
            parsed=parsed,
            raw_text='{"x":"ok"}',
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            model="fake",
            provider="fake",
            latency_ms=1.0,
        )


def test_fake_adapter_satisfies_protocol_at_runtime():
    adapter = FakeAdapter()
    assert isinstance(adapter, LLMAdapter)


def test_protocol_documents_call_once():
    # call_once is the single primitive the Protocol exposes.
    assert hasattr(LLMAdapter, "call_once")


def test_non_adapter_class_does_not_satisfy_protocol():
    class _NotAnAdapter:
        def something_else(self) -> None: ...

    assert not isinstance(_NotAnAdapter(), LLMAdapter)
