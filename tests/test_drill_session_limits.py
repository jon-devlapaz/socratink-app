import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import ai_service


class FakeResponse:
    def __init__(self, parsed):
        self.parsed = parsed


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
                        "mechanism": "The thermostat compares the measured temperature to the setpoint and turns heat on when the room is too cold.",
                    }
                ],
            }
        ],
        "relationships": {},
        "frameworks": [],
    }


def old_session_start():
    return (datetime.now(timezone.utc) - timedelta(minutes=26)).isoformat()


def drill_response(*, routing="PROBE", classification="shallow"):
    return FakeResponse(
        ai_service.DrillEvaluation(
            agent_response="You have part of it. Name the comparison and resulting heater state.",
            generative_commitment=True,
            answer_mode="attempt",
            score_eligible=True,
            help_request_reason="none",
            classification=classification,
            gap_description="The response is missing the heater state that follows the comparison.",
            routing=routing,
            response_tier=2,
            response_band="link",
            tier_reason="The answer names comparison but not the full causal transition.",
        )
    )


def call_drill_chat(*, session_start_iso, nodes_drilled=0):
    return ai_service.drill_chat(
        knowledge_map=sample_knowledge_map(),
        concept_id="thermostat",
        node_id="c1_s1",
        node_label="Setpoint comparison",
        node_mechanism="server-resolved mechanism",
        messages=[
            {
                "role": "user",
                "content": "The thermostat compares room temperature to the setpoint.",
            }
        ],
        session_phase="turn",
        drill_mode="re_drill",
        re_drill_count=0,
        probe_count=0,
        nodes_drilled=nodes_drilled,
        attempt_turn_count=0,
        help_turn_count=0,
        session_start_iso=session_start_iso,
    )


class DrillSessionLimitTests(unittest.TestCase):
    def test_disabled_duration_cap_allows_old_session_to_continue(self):
        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()) as get_client,
            patch(
                "ai_service._call_gemini_with_retry",
                return_value=drill_response(),
            ),
            patch("ai_service._log_drill_run"),
            patch("ai_service._log_drill_chat_turn"),
        ):
            result = call_drill_chat(session_start_iso=old_session_start())

        self.assertEqual(result["routing"], "PROBE")
        self.assertFalse(result["session_terminated"])
        self.assertIsNone(result["termination_reason"])
        get_client.assert_called_once()

    def test_configured_duration_cap_still_returns_time_cap(self):
        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "1500"}),
            patch("ai_service._get_client", return_value=object()) as get_client,
            patch("ai_service._call_gemini_with_retry"),
            patch("ai_service._log_drill_run"),
            patch("ai_service._log_drill_chat_turn"),
        ):
            result = call_drill_chat(session_start_iso=old_session_start())

        self.assertEqual(result["routing"], "SESSION_COMPLETE")
        self.assertTrue(result["session_terminated"])
        self.assertEqual(result["termination_reason"], "time_cap")
        get_client.assert_not_called()

    def test_node_cap_still_terminates_when_duration_cap_disabled(self):
        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()),
            patch(
                "ai_service._call_gemini_with_retry",
                return_value=drill_response(routing="NEXT", classification="solid"),
            ),
            patch("ai_service._log_drill_run"),
            patch("ai_service._log_drill_chat_turn"),
        ):
            result = call_drill_chat(
                session_start_iso=old_session_start(),
                nodes_drilled=3,
            )

        self.assertEqual(result["routing"], "NEXT")
        self.assertTrue(result["session_terminated"])
        self.assertEqual(result["termination_reason"], "node_cap")
        self.assertEqual(result["nodes_drilled"], 4)


if __name__ == "__main__":
    unittest.main()
