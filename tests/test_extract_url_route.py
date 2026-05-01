# tests/test_extract_url_route.py
"""End-to-end tests for /api/extract-url through FastAPI TestClient.

These are smoke-level — most behavior is tested in tests/source_intake/
at the facade and mapping-table levels. Catches wiring errors only.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from auth.service import AuthSessionState
from source_intake import ImportedSource
from source_intake.errors import BlockedSource, FetchFailed, ParseEmpty, TooLarge


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


def test_extract_url_returns_imported_source_dict(client):
    fake_src = ImportedSource(
        url="https://example.com/page",
        title="Title",
        text="x" * 250,
        is_remote_source=True,
    )
    with patch("source_intake.from_url", return_value=fake_src):
        response = client.post("/api/extract-url", json={"url": "https://example.com/page"})
    assert response.status_code == 200
    body = response.json()
    assert body == {"url": "https://example.com/page", "title": "Title", "text": "x" * 250}
    assert "is_remote_source" not in body


def test_extract_url_maps_private_address_to_502(client):
    with patch("source_intake.from_url", side_effect=BlockedSource("test", reason="private_address")):
        response = client.post("/api/extract-url", json={"url": "http://internal/"})
    assert response.status_code == 502
    assert "couldn't reach" in response.json()["detail"].lower()


def test_extract_url_maps_blocked_video_to_400(client):
    with patch("source_intake.from_url", side_effect=BlockedSource("test", reason="blocked_video")):
        response = client.post("/api/extract-url", json={"url": "https://youtu.be/abc"})
    assert response.status_code == 400
    assert "video" in response.json()["detail"].lower()


def test_extract_url_maps_too_large_to_413(client):
    with patch("source_intake.from_url", side_effect=TooLarge("test")):
        response = client.post("/api/extract-url", json={"url": "https://example.com/big"})
    assert response.status_code == 413


def test_extract_url_maps_parse_empty_to_422(client):
    with patch("source_intake.from_url", side_effect=ParseEmpty("test")):
        response = client.post("/api/extract-url", json={"url": "https://example.com/thin"})
    assert response.status_code == 422


def test_extract_url_oracle_defense_dns_and_private_indistinguishable(client):
    with patch("source_intake.from_url", side_effect=BlockedSource("test", reason="private_address")):
        r1 = client.post("/api/extract-url", json={"url": "http://internal/"})
    with patch("source_intake.from_url", side_effect=FetchFailed("test", cause="dns")):
        r2 = client.post("/api/extract-url", json={"url": "http://nonexistent/"})
    assert r1.status_code == r2.status_code
    assert r1.json()["detail"] == r2.json()["detail"]
