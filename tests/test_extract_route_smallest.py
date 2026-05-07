"""C-prime spec §5.2 acceptance: source-less /api/extract returns a
smallest ProvisionalMap (≤4 nodes), and name-only/source-null bypasses
are still rejected."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from main import app
from auth.service import AuthSessionState


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


def test_extract_thin_sketch_no_source_still_rejected(client):
    """The existing thin_sketch_no_source guard is preserved (defense in depth)."""
    r = client.post("/api/extract", json={
        "name": "Photosynthesis",
        "starting_sketch": "",
        "source": None,
    })
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "thin_sketch_no_source"


def test_extract_idk_sketch_no_source_rejected(client):
    """`idk` is not substantive."""
    r = client.post("/api/extract", json={
        "name": "Photosynthesis",
        "starting_sketch": "idk",
        "source": None,
    })
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "thin_sketch_no_source"


def test_extract_substantive_threshold_returns_smallest_route(client):
    """Source-less + substantive threshold → smallest ProvisionalMap (≤4)."""
    from tests.test_generate_smallest_route import _provisional_map_with_node_count

    fake_pm = _provisional_map_with_node_count(3)

    with patch("main.generate_smallest_provisional_map", return_value=fake_pm) as mocked:
        r = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "plants take in light and somehow make sugar through leaves",
            "source": None,
        })

    assert r.status_code == 200
    mocked.assert_called_once()
    # Verify call kwargs match expected signature
    _args, kwargs = mocked.call_args
    # concept should be passed either as positional or keyword
    assert kwargs.get("concept") == "Photosynthesis" or (len(_args) > 0 and _args[0] == "Photosynthesis")
