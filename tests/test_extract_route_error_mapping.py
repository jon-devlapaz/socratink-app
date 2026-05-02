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
