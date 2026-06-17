def test_public_imports_resolve():
    """The full `llm.__all__` public surface must be importable from `llm` directly."""
    import llm
    missing = [name for name in llm.__all__ if not hasattr(llm, name)]
    assert not missing, f"missing from llm package: {missing}"
    assert callable(llm.build_llm_client)


def test_build_llm_client_default_provider_is_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    from llm import build_llm_client, LLMClient
    client = build_llm_client()
    assert isinstance(client, LLMClient)


def test_build_llm_client_builds_gemini_client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from llm import build_llm_client

    client = build_llm_client(api_key="explicit-key")
    assert client.adapter._explicit_key == "explicit-key"


def test_build_llm_client_passes_api_key_to_adapter(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from llm import build_llm_client

    client = build_llm_client(api_key="explicit-key")
    # The adapter should hold the explicit key, ready to resolve on call.
    from llm.gemini_adapter import GeminiAdapter
    assert isinstance(client.adapter, GeminiAdapter)
    assert client.adapter._explicit_key == "explicit-key"


def test_build_llm_client_respects_model_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.5-pro")
    from llm import build_llm_client

    client = build_llm_client()
    assert client.adapter._model == "gemini-2.5-pro"


def test_build_llm_client_rejects_empty_model_env(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "   ")
    from llm import build_llm_client

    try:
        build_llm_client()
    except ValueError as exc:
        assert "LLM_MODEL" in str(exc)
    else:
        raise AssertionError("empty LLM_MODEL should fail")
