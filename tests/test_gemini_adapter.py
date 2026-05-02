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


# --- Error-code classification (Task 5.2) ------------------------------------


class _FakeAPIError(Exception):
    """Stand-in for google.genai.errors.APIError; same .code/.message contract."""

    def __init__(self, code: int, message: str = "boom"):
        super().__init__(message)
        self.code = code
        self.message = message


def _patch_genai_client(monkeypatch, *, raises=None, response=None):
    """Replace genai.Client(...) construction with a fake whose
    .models.generate_content either raises or returns response.
    """
    fake_models = MagicMock()
    if raises is not None:
        fake_models.generate_content.side_effect = raises
    else:
        fake_models.generate_content.return_value = response
    fake_client = MagicMock()
    fake_client.models = fake_models

    import llm.gemini_adapter as ga
    monkeypatch.setattr(ga.genai, "Client", lambda **_: fake_client)


def test_429_maps_to_rate_limit_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import llm.gemini_adapter as ga
    monkeypatch.setattr(ga, "APIError", _FakeAPIError)
    _patch_genai_client(monkeypatch, raises=_FakeAPIError(429))

    adapter = GeminiAdapter(model="gemini-2.5-flash")
    with pytest.raises(LLMRateLimitError):
        adapter.call_once(_request())


@pytest.mark.parametrize("code", [500, 503, 504, 401, 400])
def test_other_codes_map_to_service_error(monkeypatch, code):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import llm.gemini_adapter as ga
    monkeypatch.setattr(ga, "APIError", _FakeAPIError)
    _patch_genai_client(monkeypatch, raises=_FakeAPIError(code))

    adapter = GeminiAdapter(model="gemini-2.5-flash")
    with pytest.raises(LLMServiceError):
        adapter.call_once(_request())
