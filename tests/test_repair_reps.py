import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import ai_service
import main
from auth import GUEST_COOKIE_NAME
from auth.service import AuthSessionState


class FakeAuthService:
    def __init__(self, *, enabled=True):
        self.enabled = enabled
        self.cookie_name = "wos_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "wos_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.current_state = AuthSessionState(auth_enabled=enabled, authenticated=False)

    def load_session(self, sealed_session: str | None):
        return self.current_state

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


class FakeResponse:
    def __init__(self, parsed, text=None):
        self.parsed = parsed
        self.text = text


def sample_knowledge_map():
    return {
        "metadata": {
            "core_thesis": "A thermostat control loop compares actual temperature against a setpoint to trigger heating.",
            "governing_assumptions": [],
        },
        "backbone": [
            {
                "id": "b1",
                "principle": "Feedback control depends on comparing current state to desired state.",
                "dependent_clusters": ["c1"],
            }
        ],
        "clusters": [
            {
                "id": "c1",
                "label": "Thermostat feedback",
                "description": "How thermostats regulate temperature.",
                "subnodes": [
                    {
                        "id": "c1_s1",
                        "label": "Setpoint comparison",
                        "mechanism": "The thermostat compares measured temperature to the setpoint; if the measured value is below the setpoint, it turns heating on until the gap closes.",
                    }
                ],
            }
        ],
        "relationships": {},
        "frameworks": [],
    }


def valid_repair_reps():
    return ai_service.RepairRepsEvaluation(
        reps=[
            ai_service.RepairRep(
                id="rep-1",
                kind="missing_bridge",
                prompt="What causal bridge connects the measured temperature to the heating decision?",
                target_bridge="Measured temperature below the setpoint creates a gap, so heating turns on.",
                feedback_cue="Compare whether your bridge named the gap and the heating response.",
            ),
            ai_service.RepairRep(
                id="rep-2",
                kind="next_step",
                prompt="If the room is still below the setpoint, what changes next?",
                target_bridge="The thermostat keeps heating active until the measured temperature reaches the setpoint.",
                feedback_cue="Check whether your answer kept the loop tied to the setpoint comparison.",
            ),
            ai_service.RepairRep(
                id="rep-3",
                kind="cause_effect",
                prompt="Why does the setpoint comparison control the heater?",
                target_bridge="The comparison identifies whether the current state is too low, which determines whether heat is needed.",
                feedback_cue="Look for the cause-effect chain from comparison to heater state.",
            ),
        ]
    )


def has_schema_key(value, key):
    if isinstance(value, dict):
        return key in value or any(has_schema_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(has_schema_key(item, key) for item in value)
    return False


class RepairRepsApiTests(unittest.TestCase):
    def setUp(self):
        self.original_service = main.app.state.auth_service

    def tearDown(self):
        main.app.state.auth_service = self.original_service

    def build_client(self, *, guest=True) -> TestClient:
        main.app.state.auth_service = FakeAuthService(enabled=True)
        client = TestClient(main.app)
        if guest:
            client.cookies.set(GUEST_COOKIE_NAME, "guest")
        return client

    def test_repair_reps_api_requires_guest_or_auth_entry(self):
        client = self.build_client(guest=False)

        response = client.post("/api/repair-reps", json={})

        self.assertEqual(response.status_code, 401)

    def test_repair_reps_endpoint_uses_server_resolved_mechanism(self):
        client = self.build_client()
        captured = {}

        def fake_generate_repair_reps(**kwargs):
            captured.update(kwargs)
            return {
                "node_id": kwargs["node_id"],
                "prompt_version": "repair-reps-system-v1",
                "reps": [
                    {
                        "id": "rep-1",
                        "kind": "missing_bridge",
                        "prompt": "Prompt one",
                        "target_bridge": "Bridge one",
                        "feedback_cue": "Cue one",
                    },
                    {
                        "id": "rep-2",
                        "kind": "next_step",
                        "prompt": "Prompt two",
                        "target_bridge": "Bridge two",
                        "feedback_cue": "Cue two",
                    },
                    {
                        "id": "rep-3",
                        "kind": "cause_effect",
                        "prompt": "Prompt three",
                        "target_bridge": "Bridge three",
                        "feedback_cue": "Cue three",
                    },
                ],
            }

        with patch("main.generate_repair_reps", side_effect=fake_generate_repair_reps):
            response = client.post(
                "/api/repair-reps",
                json={
                    "concept_id": "thermostat",
                    "node_id": "c1_s1",
                    "node_label": "Setpoint comparison",
                    "knowledge_map": sample_knowledge_map(),
                    "gap_type": "deep",
                    "gap_description": "Missing the comparison-to-heater bridge.",
                    "count": 3,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("measured temperature to the setpoint", captured["node_mechanism"])
        payload = response.json()
        self.assertEqual(payload["prompt_version"], "repair-reps-system-v1")
        self.assertEqual(len(payload["reps"]), 3)
        for forbidden_field in ("routing", "classification", "score_eligible", "graph_mutated"):
            self.assertNotIn(forbidden_field, payload)

    def test_repair_reps_endpoint_rejects_unknown_node_id(self):
        client = self.build_client()

        response = client.post(
            "/api/repair-reps",
            json={
                "concept_id": "thermostat",
                "node_id": "missing-node",
                "node_label": "Missing node",
                "knowledge_map": sample_knowledge_map(),
                "count": 3,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown node_id", response.json()["detail"])

    def test_repair_reps_endpoint_returns_controlled_error_for_malformed_ai_output(self):
        client = self.build_client()

        with patch(
            "main.generate_repair_reps",
            side_effect=ValueError("Repair reps response must include exactly 3 reps."),
        ), patch("main.logger.exception"):
            response = client.post(
                "/api/repair-reps",
                json={
                    "concept_id": "thermostat",
                    "node_id": "c1_s1",
                    "node_label": "Setpoint comparison",
                    "knowledge_map": sample_knowledge_map(),
                    "count": 3,
                },
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "Repair Reps generation failed. Please retry.")

    def test_generate_repair_reps_returns_exact_three_graph_neutral_reps(self):
        with patch("ai_service._get_client", return_value=object()), patch(
            "ai_service._call_gemini_with_retry",
            return_value=FakeResponse(valid_repair_reps()),
        ):
            result = ai_service.generate_repair_reps(
                knowledge_map=sample_knowledge_map(),
                concept_id="thermostat",
                node_id="c1_s1",
                node_label="Setpoint comparison",
                node_mechanism="server-resolved mechanism",
                count=3,
            )

        self.assertEqual(result["prompt_version"], "repair-reps-system-v1")
        self.assertEqual(len(result["reps"]), 3)
        for forbidden_field in ("routing", "classification", "score_eligible", "graph_mutated"):
            self.assertNotIn(forbidden_field, result)

    def test_repair_reps_gemini_schema_omits_unsupported_extra_forbid_keyword(self):
        schema = ai_service.RepairRepsEvaluation.model_json_schema()

        self.assertFalse(has_schema_key(schema, "additionalProperties"))
        self.assertFalse(has_schema_key(schema, "additional_properties"))

    def test_generate_repair_reps_rejects_extra_fields_from_raw_response(self):
        payload = valid_repair_reps().model_dump()
        payload["routing"] = "NEXT"
        payload["reps"][0]["score_eligible"] = True

        with patch("ai_service._get_client", return_value=object()), patch(
            "ai_service._call_gemini_with_retry",
            return_value=FakeResponse(None, text=json.dumps(payload)),
        ):
            with self.assertRaisesRegex(ValueError, "invalid structured repair reps response"):
                ai_service.generate_repair_reps(
                    knowledge_map=sample_knowledge_map(),
                    concept_id="thermostat",
                    node_id="c1_s1",
                    node_label="Setpoint comparison",
                    node_mechanism="server-resolved mechanism",
                    count=3,
                )

    def test_generate_repair_reps_rejects_undersized_ai_output(self):
        undersized = ai_service.RepairRepsEvaluation.model_construct(
            reps=valid_repair_reps().reps[:2]
        )

        with patch("ai_service._get_client", return_value=object()), patch(
            "ai_service._call_gemini_with_retry",
            return_value=FakeResponse(undersized),
        ):
            with self.assertRaisesRegex(ValueError, "exactly 3 reps"):
                ai_service.generate_repair_reps(
                    knowledge_map=sample_knowledge_map(),
                    concept_id="thermostat",
                    node_id="c1_s1",
                    node_label="Setpoint comparison",
                    node_mechanism="server-resolved mechanism",
                    count=3,
                )


if __name__ == "__main__":
    unittest.main()
