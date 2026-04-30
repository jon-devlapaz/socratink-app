import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import ai_service
import main
from auth.service import AuthSessionState, AuthUser


STARTING_MAP = {
    "global_context": "I think a thermostat compares room temperature to a target.",
    "fuzzy_area": "I am not sure when the heater turns on.",
}


class FakeAuthService:
    enabled = True
    cookie_name = "sb_session"
    cookie_samesite = "lax"
    cookie_max_age = 120
    oauth_state_cookie_name = "sb_oauth_state"
    oauth_state_ttl_seconds = 600

    def load_session(self, sealed_session: str | None):
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
        )

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


class TextResponse:
    def __init__(self, text: str):
        self.text = text


class ParsedResponse:
    def __init__(self, parsed):
        self.parsed = parsed


def sample_knowledge_map(include_starting_map: bool = False) -> dict:
    metadata = {
        "source_title": "Thermostat",
        "core_thesis": "A thermostat uses feedback to regulate room temperature.",
        "governing_assumptions": [],
    }
    if include_starting_map:
        metadata["starting_map"] = dict(STARTING_MAP)
    return {
        "metadata": metadata,
        "backbone": [
            {
                "id": "b1",
                "principle": "Temperature control compares the current reading with the setpoint.",
                "dependent_clusters": ["c1"],
            }
        ],
        "clusters": [
            {
                "id": "c1",
                "label": "Thermostat feedback",
                "description": "Feedback control for room temperature.",
                "subnodes": [
                    {
                        "id": "c1_s1",
                        "label": "Setpoint comparison",
                        "mechanism": "The thermostat turns heat on when measured temperature is below the setpoint.",
                    }
                ],
            }
        ],
        "relationships": {"domain_mechanics": [], "learning_prerequisites": []},
        "frameworks": [],
    }


class StartingMapFlowTests(unittest.TestCase):
    def setUp(self):
        self.original_service = main.app.state.auth_service
        main.app.state.auth_service = FakeAuthService()

    def tearDown(self):
        main.app.state.auth_service = self.original_service

    def test_extract_endpoint_passes_starting_map_to_extraction(self):
        client = TestClient(main.app)
        returned_map = sample_knowledge_map(include_starting_map=True)

        with patch("main.extract_knowledge_map", return_value=returned_map) as extract_map:
            response = client.post(
                "/api/extract",
                json={"text": "thermostat source text", "starting_map": STARTING_MAP},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["knowledge_map"]["metadata"]["starting_map"], STARTING_MAP)
        extract_map.assert_called_once()
        self.assertEqual(extract_map.call_args.kwargs["starting_map"], STARTING_MAP)

    def test_extracted_map_retains_starting_map_metadata(self):
        returned_text = json.dumps(sample_knowledge_map(include_starting_map=False))
        captured = {}

        def fake_call(*args, **kwargs):
            captured["contents"] = kwargs["contents"]
            return TextResponse(returned_text)

        with (
            patch("ai_service._get_client", return_value=object()),
            patch("ai_service._call_gemini_with_retry", side_effect=fake_call),
        ):
            result = ai_service.extract_knowledge_map(
                "thermostat source text",
                starting_map=STARTING_MAP,
                api_key="test-key",
            )

        self.assertEqual(result["metadata"]["starting_map"], STARTING_MAP)
        self.assertIn("route-shaping context", captured["contents"])
        self.assertIn(STARTING_MAP["global_context"], captured["contents"])

    def test_pruned_drill_context_includes_starting_map(self):
        pruned = ai_service._prune_context(
            sample_knowledge_map(include_starting_map=True),
            "core-thesis",
        )

        self.assertEqual(pruned["metadata"]["starting_map"], STARTING_MAP)

    def test_cold_attempt_prompt_uses_starting_map_without_answer_reveal(self):
        captured = {}

        def fake_call(*args, **kwargs):
            captured["contents"] = kwargs["contents"]
            captured["system_instruction"] = kwargs["config"].system_instruction
            return ParsedResponse(
                ai_service.DrillEvaluation(
                    agent_response="You wrote that the thermostat compares a reading to a target. What is the smaller comparison happening in this room?",
                    generative_commitment=None,
                    answer_mode=None,
                    score_eligible=False,
                    help_request_reason=None,
                    classification=None,
                    gap_description=None,
                    routing="PROBE",
                    response_tier=None,
                    response_band=None,
                    tier_reason=None,
                )
            )

        with (
            patch("ai_service._get_client", return_value=object()),
            patch("ai_service._call_gemini_with_retry", side_effect=fake_call),
        ):
            result = ai_service.drill_chat(
                knowledge_map=sample_knowledge_map(include_starting_map=True),
                concept_id="thermostat",
                node_id="core-thesis",
                node_label="Core Thesis",
                node_mechanism="A thermostat uses feedback to regulate room temperature.",
                messages=[],
                session_phase="init",
                drill_mode="cold_attempt",
                re_drill_count=0,
                probe_count=0,
                nodes_drilled=0,
                attempt_turn_count=0,
                help_turn_count=0,
                api_key="test-key",
            )

        self.assertIsNone(result["routing"])
        self.assertIn('"starting_map"', captured["contents"])
        self.assertIn("global context only", captured["system_instruction"])
        self.assertIn("do not reveal the mechanism", captured["system_instruction"].lower())
        self.assertIn("do not use score, diagnostic, or mastery language", captured["system_instruction"].lower())


if __name__ == "__main__":
    unittest.main()
