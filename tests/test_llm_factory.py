import pytest


def test_public_imports_resolve():
    # These names must all be importable from `llm` directly.
    from llm import (
        LLMClient,
        StructuredLLMRequest,
        StructuredLLMResult,
        TokenUsage,
        LLMError,
        LLMMissingKeyError,
        LLMRateLimitError,
        LLMServiceError,
        LLMValidationError,
        build_llm_client,
    )
    assert callable(build_llm_client)


def test_build_llm_client_default_provider_is_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    from llm import build_llm_client, LLMClient
    client = build_llm_client()
    assert isinstance(client, LLMClient)


def test_build_llm_client_unknown_provider_errors(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    from llm import build_llm_client
    with pytest.raises(NotImplementedError):
        build_llm_client()


def test_build_llm_client_passes_api_key_to_adapter(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    from llm import build_llm_client

    client = build_llm_client(api_key="explicit-key")
    # The adapter should hold the explicit key, ready to resolve on call.
    from llm.gemini_adapter import GeminiAdapter
    assert isinstance(client.adapter, GeminiAdapter)
    assert client.adapter._explicit_key == "explicit-key"


def test_build_llm_client_respects_model_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.5-pro")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    from llm import build_llm_client

    client = build_llm_client()
    assert client.adapter._model == "gemini-2.5-pro"
