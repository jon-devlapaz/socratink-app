"""Tests for spec §5.4 backend telemetry events on /api/extract.

Existing events (verified in B7's test suite):
- concept_create.build_blocked (with reason + origin)
- concept_create.lc.enrichment_skipped (with reason)
- concept_create.lc.enrichment_applied (with standards_count)

NEW events tested here (B8):
- concept_create.lc.queried (with concept_hash, top_score, standards_count, latency_ms)
- concept_create.ai_call (with stage, model, tokens_in, tokens_out, latency_ms, cost_usd_est)
"""
from __future__ import annotations

import logging
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import main
from main import app
from auth.service import AuthSessionState
from models.provisional_map import (
    BackboneItem, Cluster, Metadata, ProvisionalMap, Relationships, Subnode,
)
from llm.types import StructuredLLMResult, TokenUsage
from llm.client import LLMClient as RealLLMClient


# --- Auth fixture (mirrored from test_extract_route_source_optional.py) ---

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


def _records_for(caplog, event_name: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage() == event_name]


# --- Tests for concept_create.lc.queried ---

def test_lc_queried_emitted_after_search(client, caplog):
    """concept_create.lc.queried must fire after every LC search call,
    regardless of gate outcome."""
    caplog.set_level(logging.INFO)
    fake_map = _minimal_map()
    from learning_commons import LCSearchResult, LCStandard
    fake_lc_result = LCSearchResult(
        top_score=0.75,
        standards=[LCStandard(
            case_uuid="u", statement_code="HS-LS1-5",
            description="x" * 60, jurisdiction="Multi-State", score=0.75,
        )],
    )
    with patch("main.LCClient") as fake_lc_cls, \
         patch("main.generate_provisional_map_from_sketch", return_value=fake_map):
        fake_lc_cls.return_value.search_concept.return_value = fake_lc_result
        client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and carbon dioxide.",
            "source": None,
        })
    queried = _records_for(caplog, "concept_create.lc.queried")
    assert queried, "must emit concept_create.lc.queried"
    extras = queried[0].__dict__
    assert "concept_hash" in extras
    assert "top_score" in extras
    assert extras["top_score"] == pytest.approx(0.75)
    assert "standards_count" in extras
    assert extras["standards_count"] == 1
    assert "latency_ms" in extras


def test_lc_queried_emitted_even_when_lc_returns_none(client, caplog):
    """The queried event fires even when LC errored or returned no results.
    This is the load-bearing event for measuring LC reachability."""
    caplog.set_level(logging.INFO)
    fake_map = _minimal_map()
    with patch("main.LCClient") as fake_lc_cls, \
         patch("main.generate_provisional_map_from_sketch", return_value=fake_map):
        fake_lc_cls.return_value.search_concept.return_value = None
        client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and carbon dioxide.",
            "source": None,
        })
    queried = _records_for(caplog, "concept_create.lc.queried")
    assert queried, "must emit lc.queried even when LCClient returns None"


def test_lc_skip_reason_is_error_when_lcclient_raises(client, caplog):
    """B7 review M-4: when LCClient() raises, reason must be 'error', not 'no_results'."""
    caplog.set_level(logging.INFO)
    fake_map = _minimal_map()
    # Set the env var so the reason is NOT key_missing
    with patch.dict(os.environ, {"LEARNING_COMMONS_API_KEY": "sk_test_xxx"}), \
         patch("main.LCClient", side_effect=RuntimeError("LC client init failed")), \
         patch("main.generate_provisional_map_from_sketch", return_value=fake_map):
        client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and carbon dioxide.",
            "source": None,
        })
    skipped = _records_for(caplog, "concept_create.lc.enrichment_skipped")
    assert skipped, "must emit lc.enrichment_skipped"
    assert skipped[0].__dict__.get("reason") == "error"


# --- Tests for concept_create.ai_call ---

def test_ai_call_emitted_after_source_less_generation(client, caplog):
    """ai_call event must fire after every AI call with stage/model/tokens/latency/cost."""
    caplog.set_level(logging.INFO)
    fake_map = _minimal_map()
    fake_result = StructuredLLMResult(
        parsed=fake_map,
        raw_text="{}",
        usage=TokenUsage(input_tokens=420, output_tokens=180),
        model="gemini-2.5-flash",
        provider="gemini",
        latency_ms=1234.0,
    )
    fake_llm = MagicMock(spec=RealLLMClient)
    fake_llm.generate_structured.return_value = fake_result
    with patch("main.LCClient") as fake_lc_cls, \
         patch("ai_service.build_llm_client", return_value=fake_llm):
        fake_lc_cls.return_value.search_concept.return_value = None
        client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and carbon dioxide.",
            "source": None,
        })
    ai_calls = _records_for(caplog, "concept_create.ai_call")
    assert ai_calls, "must emit concept_create.ai_call after AI call"
    extras = ai_calls[0].__dict__
    assert extras.get("stage") in ("generation_pure", "generation_lc_enriched")
    assert extras.get("model") == "gemini-2.5-flash"
    assert extras.get("tokens_in") == 420
    assert extras.get("tokens_out") == 180
    assert "latency_ms" in extras
    assert "cost_usd_est" in extras


def test_ai_call_emitted_for_extract_path(client, caplog):
    """ai_call must fire for source-attached path too, with stage=generation_extract."""
    caplog.set_level(logging.INFO)
    fake_map = _minimal_map()
    fake_result = StructuredLLMResult(
        parsed=fake_map,
        raw_text="{}",
        usage=TokenUsage(input_tokens=900, output_tokens=300),
        model="gemini-2.5-flash",
        provider="gemini",
        latency_ms=2345.0,
    )
    fake_llm = MagicMock(spec=RealLLMClient)
    fake_llm.generate_structured.return_value = fake_result
    with patch("ai_service.build_llm_client", return_value=fake_llm):
        client.post("/api/extract", json={
            "text": "Photosynthesis is the process by which plants convert light energy from the sun into chemical energy stored in glucose.",
        })
    ai_calls = _records_for(caplog, "concept_create.ai_call")
    assert ai_calls, "must emit ai_call for source-attached path"
    extras = ai_calls[0].__dict__
    assert extras.get("stage") == "generation_extract"
