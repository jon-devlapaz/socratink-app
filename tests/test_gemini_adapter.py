from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from llm.errors import (
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)
from llm.gemini_adapter import GeminiAdapter
from llm.types import StructuredLLMRequest


class _Schema(BaseModel):
    x: str


def _request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        system_prompt="sys", user_prompt="user", response_schema=_Schema
    )


def test_missing_key_raises_missing_key_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    adapter = GeminiAdapter(api_key=None, model="gemini-2.5-flash")
    with pytest.raises(LLMMissingKeyError):
        adapter.call_once(_request())


def test_explicit_key_overrides_missing_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # No SDK call should happen here — _resolve_key passes; we'll patch the
    # client to fail loudly if anything tries to use it. Construction must succeed.
    adapter = GeminiAdapter(api_key="explicit-key", model="gemini-2.5-flash")
    # Replace the SDK call so we do not actually hit Gemini in this minimal check.
    import llm.gemini_adapter as ga
    monkeypatch.setattr(
        ga.genai,
        "Client",
        lambda **_: MagicMock(models=MagicMock(generate_content=MagicMock(side_effect=RuntimeError("intercepted")))),
    )
    with pytest.raises(RuntimeError, match="intercepted"):
        adapter.call_once(_request())
