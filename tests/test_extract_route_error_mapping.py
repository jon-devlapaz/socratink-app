"""Task 10 — /api/extract maps normalized LLM errors to HTTP statuses.

These are wiring tests for the route's new exception mapping. Source-intake
behavior is unchanged (covered by tests/test_extract_route.py); these
tests cover the post-intake LLM seam errors.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from auth.service import AuthSessionState
from llm.errors import (
    LLMClientError,
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)


class _FakeAuthService:
    def __init__(self):
        self.enabled = True
        self.cookie_name = "wos_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "wos_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.current_state = AuthSessionState(
            auth_enabled=True, authenticated=True, guest_mode=True
        )

    def load_session(self, sealed_session):
        return self.current_state

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


@pytest.fixture
def client():
    original = main.app.state.auth_service
    service = _FakeAuthService()
    main.app.state.auth_service = service
    test_client = TestClient(main.app)
    test_client.cookies.set(service.cookie_name, "sealed-anon-blob")
    try:
        yield test_client
    finally:
        main.app.state.auth_service = original


def _post(client):
    # ParseEmpty floor for from_text is 1 char in default; a non-empty
    # short string is enough to reach extract_knowledge_map.
    return client.post("/api/extract", json={"text": "x" * 250})


@pytest.mark.parametrize(
    "exc_cls, expected_status",
    [
        (LLMMissingKeyError, 401),
        (LLMRateLimitError, 429),
        (LLMServiceError, 503),
        (LLMClientError, 503),
        (LLMValidationError, 502),
    ],
)
def test_route_maps_normalized_errors_to_http(client, exc_cls, expected_status):
    if exc_cls is LLMValidationError:
        exc_instance: Exception = exc_cls("boom", raw_text="{}")
    else:
        exc_instance = exc_cls("boom")
    with patch("main.extract_knowledge_map", side_effect=exc_instance):
        resp = _post(client)
    assert resp.status_code == expected_status, resp.json()


def test_route_client_error_does_not_leak_provider_message(client):
    """LLMClientError carries operator-debug detail (e.g., 'API key expired').
    The user-facing message must be stable copy; the operator gets the real
    cause via the warning log only.
    """
    leaky = LLMClientError("Gemini API error (HTTP 400): API key expired")
    with patch("main.extract_knowledge_map", side_effect=leaky):
        resp = _post(client)
    assert resp.status_code == 503
    detail = resp.json().get("detail", "")
    assert "API key" not in detail
    assert "HTTP 400" not in detail
    assert "Gemini" not in detail


# Provider-debug strings that MUST NEVER appear in the user-facing detail
# regardless of which LLM error type is raised.
_LEAKY_PROVIDER_TOKENS = ("Gemini", "HTTP 400", "HTTP 429", "HTTP 503", "gemini-2.5-flash")


@pytest.mark.parametrize(
    "exc",
    [
        LLMMissingKeyError("No Gemini API key configured. Set GEMINI_API_KEY."),
        LLMRateLimitError("Gemini rate-limited: too many requests"),
        LLMServiceError("Gemini service error (HTTP 503): upstream"),
        LLMClientError("Gemini API error (HTTP 400): expired key"),
        LLMValidationError(
            "Gemini response did not match ProvisionalMap.",
            raw_text='{"oops":"data"}',
        ),
    ],
    ids=["missing_key", "rate_limit", "service", "client", "validation"],
)
def test_no_llm_error_leaks_provider_details_to_user(client, exc):
    """Across the entire LLM error hierarchy, the user-facing detail must
    contain stable copy and no provider-internal strings. Surfaced by the
    Gemini sanity check: previously LLMMissingKeyError, LLMRateLimitError,
    and LLMServiceError used `str(err)` which leaked the provider name and
    HTTP code into the wire response.
    """
    with patch("main.extract_knowledge_map", side_effect=exc):
        resp = _post(client)
    detail = resp.json().get("detail", "")
    for token in _LEAKY_PROVIDER_TOKENS:
        assert token not in detail, (
            f"{type(exc).__name__} response leaked {token!r} via detail: {detail!r}"
        )


def test_route_validation_error_does_not_leak_raw_text(client):
    """LLMValidationError carries raw_text for fixture refresh, but the
    user-facing message must be stable copy, not the raw response.
    """
    leaky_raw = '{"this_should_not_leak": "to user"}'
    exc = LLMValidationError("internal mismatch", raw_text=leaky_raw)
    with patch("main.extract_knowledge_map", side_effect=exc):
        resp = _post(client)
    assert resp.status_code == 502
    body = resp.json()
    detail = body.get("detail", "")
    assert "this_should_not_leak" not in detail
    assert "to user" not in detail
