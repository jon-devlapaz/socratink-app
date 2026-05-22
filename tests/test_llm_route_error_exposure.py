from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from ai_service import GeminiRateLimitError, GeminiServiceError, MissingAPIKeyError
from auth.service import AuthSessionState


class FakeAuthService:
    def __init__(self):
        self.enabled = True
        self.cookie_name = "wos_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "wos_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            guest_mode=True,
        )

    def load_session(self, sealed_session: str | None):
        return self.current_state

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


@pytest.fixture
def client():
    original_service = main.app.state.auth_service
    service = FakeAuthService()
    main.app.state.auth_service = service
    test_client = TestClient(main.app)
    test_client.cookies.set(service.cookie_name, "sealed-anon-blob")
    try:
        yield test_client
    finally:
        main.app.state.auth_service = original_service


def sample_knowledge_map():
    return {
        "metadata": {
            "core_thesis": "A thermostat compares actual temperature with a setpoint.",
            "governing_assumptions": [],
        },
        "backbone": [],
        "clusters": [
            {
                "id": "c1",
                "label": "Thermostat feedback",
                "description": "Feedback control for room temperature.",
                "subnodes": [
                    {
                        "id": "c1_s1",
                        "label": "Setpoint comparison",
                        "mechanism": "The thermostat compares measured temperature to the setpoint and turns heat on when the room is too cold.",
                    }
                ],
            }
        ],
        "relationships": {},
        "frameworks": [],
    }


def drill_payload():
    return {
        "concept_id": "thermostat",
        "node_id": "c1_s1",
        "node_label": "Setpoint comparison",
        "knowledge_map": sample_knowledge_map(),
        "messages": [],
        "session_phase": "init",
    }


def repair_reps_payload():
    return {
        "concept_id": "thermostat",
        "node_id": "c1_s1",
        "node_label": "Setpoint comparison",
        "knowledge_map": sample_knowledge_map(),
        "count": 3,
    }


@pytest.mark.parametrize(
    ("exception", "expected_status", "expected_detail"),
    [
        (
            MissingAPIKeyError(
                "No Gemini API key configured. Add one in Settings or set GEMINI_API_KEY in .env."
            ),
            401,
            "No API key configured. Add one in Settings to continue.",
        ),
        (
            GeminiRateLimitError("Gemini rate limit hit. Try again in 60s."),
            429,
            "The AI service is rate-limiting requests. Try again in a minute.",
        ),
        (
            GeminiServiceError("Gemini service unavailable (HTTP 503)."),
            503,
            "The AI service is temporarily unavailable. Please try again shortly.",
        ),
    ],
)
@pytest.mark.parametrize(
    ("path", "payload_factory", "patch_target"),
    [
        ("/api/drill", drill_payload, "main.drill_chat"),
        ("/api/repair-reps", repair_reps_payload, "main.generate_repair_reps"),
    ],
)
def test_drill_and_repair_reps_return_safe_llm_error_copy(
    client,
    path,
    payload_factory,
    patch_target,
    exception,
    expected_status,
    expected_detail,
):
    with patch(patch_target, side_effect=exception):
        response = client.post(path, json=payload_factory())

    assert response.status_code == expected_status
    detail = response.json()["detail"]
    assert detail == expected_detail
    assert "Gemini" not in detail
    assert "GEMINI_API_KEY" not in detail
    assert "HTTP 503" not in detail
