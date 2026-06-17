"""Phase 1 Characterization Tests.

These tests capture the current behavioral state of the core routes
targeted for internal pruning. We use them to verify that logic 
simplification does not break existing contracts.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

import main
from auth.service import AuthSessionState
from models.provisional_map import (
    ProvisionalMap, Metadata, BackboneItem, Cluster, Subnode, Relationships
)

class _FakeAuthService:
    def __init__(self):
        self.enabled = True
        self.cookie_name = "socratink_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "socratink_oauth_state"
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

def _build_minimal_valid_map(concept="Photosynthesis"):
    """Builds a structurally valid ProvisionalMap for testing."""
    return ProvisionalMap(
        metadata=Metadata(
            source_title="Wikipedia",
            core_thesis="Sun becomes sugar.",
            architecture_type="causal_chain",
            difficulty="easy"
        ),
        backbone=[
            BackboneItem(id="b1", principle="Energy capture", dependent_clusters=["c1"])
        ],
        clusters=[
            Cluster(
                id="c1", 
                label="Chloroplasts", 
                description="The factory.",
                subnodes=[Subnode(id="c1_s1", label="Chlorophyll", mechanism="Absorption")]
            )
        ],
        relationships=Relationships(domain_mechanics=[], learning_prerequisites=[]),
        frameworks=[]
    )

# --- /api/extract ---
def test_extract_characterization(client):
    """Characterize /api/extract with a successful LLM return."""
    mock_map = _build_minimal_valid_map()
    with patch("main.extract_knowledge_map", return_value=mock_map):
        response = client.post("/api/extract", json={
            "name": "Plant nutrition",
            "starting_sketch": "Plants use light to make food.",
            "source": {"type": "text", "text": "How do plants eat?"},
        })
    
    assert response.status_code == 200
    data = response.json()
    # Actual wire shape uses "knowledge_map" key
    k_map = data["knowledge_map"]
    assert k_map["metadata"]["source_title"] == "Wikipedia"
    assert k_map["backbone"][0]["id"] == "b1"
    assert k_map["clusters"][0]["subnodes"][0]["id"] == "c1_s1"

# --- /api/extract-url ---
def test_extract_url_characterization(client):
    """Characterize /api/extract-url with success."""
    mock_map = _build_minimal_valid_map()
    # Source intake returns a Source object with a .to_dict() method
    mock_source = MagicMock()
    mock_source.to_dict.return_value = {"knowledge_map": mock_map.model_dump()}
    
    with patch("main.source_intake.from_url", return_value=mock_source):
        # The route calls src.to_dict() then returns it
        response = client.post("/api/extract-url", json={"url": "https://example.com"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["knowledge_map"]["metadata"]["core_thesis"] == "Sun becomes sugar."

# --- /api/generate-smallest-route ---
def test_generate_smallest_route_characterization(client):
    """Characterize the smallest route generation (C-prime)."""
    mock_map = _build_minimal_valid_map()
    # Triggering decision["path"] == "from_threshold" requires 'name' and 'starting_sketch'
    with patch("main.generate_smallest_provisional_map", return_value=mock_map):
        # We also need to mock LCClient.search_concept or the result of it
        with patch("main.LCClient.search_concept", return_value=None):
            response = client.post("/api/extract", json={
                "name": "Quantum mechanics",
                "starting_sketch": "Quantum mechanics involves the study of very small particles like atoms and subatomic components which behave in quantized ways."
            })
    
    assert response.status_code == 200
    data = response.json()
    # Actual wire shape uses "provisional_map" key for this branch
    p_map = data["provisional_map"]
    assert p_map["metadata"]["source_title"] == "Wikipedia"

# --- /api/health ---
def test_health_characterization(client):
    """Characterize basic health check."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "server_key_configured" in data

# --- /api/me ---
def test_me_characterization(client):
    """Characterize auth status endpoint."""
    response = client.get("/api/me")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert data["guest_mode"] is True
