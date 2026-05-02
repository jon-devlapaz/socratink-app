import pytest


@pytest.fixture(autouse=True)
def _no_real_sleep_in_llm_client(monkeypatch):
    """Replace LLMClient backoff sleep with a no-op so retry tests stay fast.

    Only affects the LLMClient retry path; tests that need real timing
    measure latency_ms via time.perf_counter.
    """
    try:
        import llm.client as _client_mod  # type: ignore
    except ImportError:
        return  # llm package not yet built; nothing to patch
    if hasattr(_client_mod.LLMClient, "_sleep_backoff"):
        monkeypatch.setattr(
            _client_mod.LLMClient,
            "_sleep_backoff",
            staticmethod(lambda attempt: None),
        )
