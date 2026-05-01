"""Smoke tests for /api/extract (text route).

Most extraction behavior is tested at the source_intake unit level. These
are wiring tests for the route's exception mapping — particularly that
internal source_intake messages don't leak to users.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from auth.service import AuthSessionState
from source_intake.errors import ParseEmpty


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


def test_extract_parse_empty_does_not_leak_internal_message(client):
    """ParseEmpty's internal message ("raw text 0 chars (min 1)") must NOT
    surface to the user. The route should respond with stable, user-facing
    copy regardless of the exception's internal text.
    """
    leaky = ParseEmpty("raw text 0 chars (min 1)")
    with patch("main.source_intake.from_text", side_effect=leaky):
        response = client.post("/api/extract", json={"text": "abc"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "raw text" not in detail.lower()
    assert "(min " not in detail
    assert "chars" not in detail.lower()


def test_extract_parse_empty_returns_user_facing_message(client):
    """The route should return a stable, helpful message for the user."""
    with patch("main.source_intake.from_text", side_effect=ParseEmpty("internal")):
        response = client.post("/api/extract", json={"text": "abc"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    # Stable user-facing phrasing.
    assert any(token in detail.lower() for token in ("readable text", "couldn't"))
