"""End-to-end tests for the source-optional /api/extract endpoint.

Covers the four truth-table states from spec §3.2:
  | Source | Sketch substantive? | Expected behavior          |
  | ------ | ------------------- | -------------------------- |
  |  yes   |       any           | success via extract path   |
  |  no    |       yes           | success via sketch path    |
  |  yes   |       no            | success via extract path   |
  |  no    |       no            | 422 thin_sketch_no_source  |

Plus: missing concept name → 422 missing_concept.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from main import app
from auth.service import AuthSessionState
from models.provisional_map import (
    BackboneItem, Cluster, Metadata, ProvisionalMap, Relationships, Subnode,
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


def _minimal_map() -> ProvisionalMap:
    """Construct a valid minimal ProvisionalMap for route-level patching."""
    return ProvisionalMap(
        metadata=Metadata(
            source_title="Photosynthesis",
            core_thesis="Photosynthesis is a process worth understanding.",
            architecture_type="causal_chain",
            difficulty="medium",
            governing_assumptions=["learner sketched a rough idea"],
            low_density=False,
        ),
        backbone=[
            BackboneItem(id="b1", principle="Stage 1", dependent_clusters=["c1"]),
        ],
        clusters=[
            Cluster(
                id="c1",
                label="First cluster",
                description="A single cluster",
                subnodes=[Subnode(id="c1_s1", label="A", mechanism="x")],
            ),
        ],
        relationships=Relationships(),
        frameworks=[],
    )


def test_substantive_sketch_no_source_dispatches_to_sketch_path(client):
    fake_map = _minimal_map()
    with patch(
        "main.generate_provisional_map_from_sketch",
        return_value=fake_map,
    ) as fake_gen, patch("main.extract_knowledge_map") as fake_extract:
        response = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and carbon dioxide.",
            "source": None,
        })
    assert response.status_code == 200
    assert fake_gen.called, "must call generate_provisional_map_from_sketch"
    assert not fake_extract.called, "must NOT call extract_knowledge_map"


def test_thin_sketch_no_source_returns_422_thin_sketch(client):
    response = client.post("/api/extract", json={
        "name": "Photosynthesis",
        "starting_sketch": "idk",
        "source": None,
    })
    assert response.status_code == 422
    body = response.json()
    detail = body.get("detail", body)
    assert (detail.get("error") if isinstance(detail, dict) else None) == "thin_sketch_no_source"


def test_substantive_sketch_with_source_dispatches_to_extract_path(client):
    fake_map = _minimal_map()
    with patch("main.extract_knowledge_map", return_value=fake_map) as fake_extract, \
         patch("main.generate_provisional_map_from_sketch") as fake_gen:
        response = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and CO2.",
            "source": {"type": "text", "text": "Photosynthesis is the process by which..."},
        })
    assert response.status_code == 200
    assert fake_extract.called
    assert not fake_gen.called


def test_thin_sketch_with_source_dispatches_to_extract_path(client):
    """Thin sketch is OK when source carries the structural seed."""
    fake_map = _minimal_map()
    with patch("main.extract_knowledge_map", return_value=fake_map) as fake_extract, \
         patch("main.generate_provisional_map_from_sketch") as fake_gen:
        response = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "idk",
            "source": {"type": "text", "text": "Photosynthesis is the process by which..."},
        })
    assert response.status_code == 200
    assert fake_extract.called
    assert not fake_gen.called


def test_missing_concept_returns_422_missing_concept(client):
    response = client.post("/api/extract", json={
        "name": "",
        "starting_sketch": "Plants take in light and make sugar from water and CO2.",
        "source": None,
    })
    assert response.status_code == 422
    body = response.json()
    detail = body.get("detail", body)
    assert (detail.get("error") if isinstance(detail, dict) else None) == "missing_concept"


def test_whitespace_only_concept_returns_422_missing_concept(client):
    response = client.post("/api/extract", json={
        "name": "   \n\t  ",
        "starting_sketch": "Plants take in light and make sugar from water and CO2.",
        "source": None,
    })
    assert response.status_code == 422
    body = response.json()
    detail = body.get("detail", body)
    assert (detail.get("error") if isinstance(detail, dict) else None) == "missing_concept"


def test_legacy_text_only_payload_still_works(client):
    """Back-compat: the old {text, api_key} payload still hits extract path.

    Plan B will deprecate this once the new frontend ships, but during
    rollout the old client must keep working.
    """
    fake_map = _minimal_map()
    with patch("main.extract_knowledge_map", return_value=fake_map) as fake_extract:
        response = client.post("/api/extract", json={
            "text": "Photosynthesis is the process by which...",
        })
    assert response.status_code == 200
    assert fake_extract.called


def test_lc_enrichment_is_attempted_for_source_less_path(client):
    """When source-less, LC search is attempted and result feeds into generation."""
    fake_map = _minimal_map()
    from learning_commons import LCSearchResult, LCStandard
    fake_lc_result = LCSearchResult(
        top_score=0.75,
        standards=[LCStandard(
            case_uuid="u", statement_code="HS-LS1-5",
            description="x" * 60, jurisdiction="Multi-State", score=0.75,
        )],
    )
    with patch("main.generate_provisional_map_from_sketch", return_value=fake_map) as fake_gen, \
         patch("main.LCClient") as fake_lc_cls:
        fake_lc_cls.return_value.search_concept.return_value = fake_lc_result
        response = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and carbon dioxide.",
            "source": None,
        })
    assert response.status_code == 200
    fake_gen.assert_called_once()
    kwargs = fake_gen.call_args.kwargs
    assert kwargs.get("lc_context") is not None
    assert len(kwargs["lc_context"]) >= 1
