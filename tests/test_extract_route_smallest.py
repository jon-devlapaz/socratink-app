"""Acceptance coverage for source-less /api/extract.

The endpoint rejects empty source-less sketches, accepts any non-empty launch
attempt, forwards learner_goal as relevance context, and returns a smallest
ProvisionalMap when generation succeeds.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
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


def test_extract_empty_sketch_no_source_still_rejected(client):
    """Source-less generation still requires some learner-written response."""
    r = client.post("/api/extract", json={
        "name": "Photosynthesis",
        "starting_sketch": "",
        "source": None,
    })
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "missing_sketch"


def test_extract_short_sketch_no_source_returns_smallest_route(client):
    """Any non-empty source-less launch attempt can seed the draft route."""
    from tests._helpers.provisional_map_factory import provisional_map_with_node_count

    fake_pm = provisional_map_with_node_count(3)

    with patch("main.generate_smallest_provisional_map", return_value=fake_pm) as mocked:
        r = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "idk",
            "source": None,
        })

    assert r.status_code == 200
    _args, kwargs = mocked.call_args
    assert kwargs.get("threshold") == "idk" or (len(_args) > 1 and _args[1] == "idk")


def test_extract_fuller_sketch_returns_smallest_route(client):
    """Source-less + non-empty sketch → smallest ProvisionalMap (≤4)."""
    from tests._helpers.provisional_map_factory import provisional_map_with_node_count

    fake_pm = provisional_map_with_node_count(3)

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
    # threshold (the starting_sketch/seed) must be forwarded to the generator
    assert (
        kwargs.get("threshold") == "plants take in light and somehow make sugar through leaves"
        or (len(_args) > 1 and _args[1] == "plants take in light and somehow make sugar through leaves")
    )


def test_extract_source_less_forwards_learner_goal(client):
    from tests._helpers.provisional_map_factory import provisional_map_with_node_count

    fake_pm = provisional_map_with_node_count(3)

    with patch("main.generate_smallest_provisional_map", return_value=fake_pm) as mocked:
        r = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "learner_goal": "I want to explain why leaves make sugar.",
            "starting_sketch": "plants take in light and somehow make sugar through leaves",
            "source": None,
        })

    assert r.status_code == 200
    _args, kwargs = mocked.call_args
    assert kwargs.get("learner_goal") == "I want to explain why leaves make sugar."


def test_extract_smallest_route_cap_exceeded_returns_fallback_route(client):
    """Source-less generation shape failures should not strand a new learner."""
    from ai_service import SmallestRouteCapExceeded

    with patch(
        "main.generate_smallest_provisional_map",
        side_effect=SmallestRouteCapExceeded("generated 7 drillable nodes, cap is 4"),
    ):
        r = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "plants take in light and somehow make sugar through leaves",
            "source": None,
        })

    assert r.status_code == 200
    body = r.json()
    route = body["provisional_map"]
    assert route["metadata"]["source_title"] == "Photosynthesis"
    assert route["metadata"]["core_thesis"] == "Photosynthesis"
    assert route["backbone"] == [{
        "id": "b1",
        "principle": "Starting model",
        "dependent_clusters": ["c1"],
    }]
    assert "plants take in light" in route["clusters"][0]["subnodes"][0]["mechanism"]
    scaffold = route["clusters"][0]["subnodes"][0]["learner_scaffold"]
    assert "plants take in light" in scaffold["entry_prompt"]
    assert scaffold["entry_prompt"].endswith("What do you think connects those parts?")
    assert "photosynthesis" not in scaffold["entry_prompt"].lower()
