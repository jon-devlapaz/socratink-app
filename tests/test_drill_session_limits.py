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


def scaffolded_knowledge_map():
    knowledge_map = sample_knowledge_map()
    knowledge_map["clusters"][0]["subnodes"][0]["learner_scaffold"] = {
        "bloom_level": "understand",
        "learner_move": "Say it",
        "task_label": "Starting model",
        "task_cue": "Put the system in your words.",
        "tailoring_anchor": "You mentioned room temperature and heat, so this starts by naming what the thermostat compares.",
        "entry_prompt": "How would you explain the thermostat loop right now?",
        "expected_shape": "Write 1-2 sentences naming the comparison and result.",
        "sentence_starter": "My current guess is that the thermostat...",
        "blank_hint": "Start with what the thermostat compares.",
        "evidence_goal": "Learner states the comparison and the resulting heater state.",
    }
    return knowledge_map


def old_session_start():
    return (datetime.now(timezone.utc) - timedelta(minutes=26)).isoformat()


def drill_response(*, routing="PROBE", classification="shallow", score_eligible=True):
    return FakeResponse(
        ai_service.DrillEvaluation(
            agent_response="You have part of it. Name the comparison and resulting heater state.",
            generative_commitment=True,
            answer_mode="attempt",
            score_eligible=score_eligible,
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
        ):
            result = call_drill_chat(
                session_start_iso=old_session_start(),
                nodes_drilled=3,
            )

        self.assertEqual(result["routing"], "NEXT")
        self.assertTrue(result["session_terminated"])
        self.assertEqual(result["termination_reason"], "node_cap")
        self.assertEqual(result["nodes_drilled"], 4)


class DrillBypassAndDegradedResponseTests(unittest.TestCase):
    """Regression suite for the production 502 cluster on /api/drill.

    Two distinct fragilities both surfaced as `502 Drill evaluation failed`:

    1. **Missing session_start_iso when bypass_session_limits=True.**
       Frontend MVP hardcodes bypass=True; the timestamp init was previously
       gated on the bypass flag, so turn-phase calls hit a ValueError in
       drill_chat. Fixed in two layers (frontend always inits the timestamp;
       backend treats session_start_iso as optional when bypass=True).

    2. **Gemini returns score_eligible=True with classification=None.**
       Earlier no-mistakes review flagged the unconditional raise as a
       potential availability hit. _normalize_drill_evaluation now demotes the
       turn to unscored (score_eligible=False) instead of bubbling a 502.
    """

    def test_bypass_mode_allows_null_session_start_iso(self):
        """bypass_session_limits=True must not require session_start_iso.

        This is the load-bearing fix for the live prod 502. With bypass on,
        session-duration math is moot and the timestamp is decorative.
        """
        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()),
            patch(
                "ai_service._call_gemini_with_retry",
                return_value=drill_response(),
            ),
        ):
            result = ai_service.drill_chat(
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
                nodes_drilled=0,
                attempt_turn_count=0,
                help_turn_count=0,
                session_start_iso=None,
                bypass_session_limits=True,
            )

        self.assertEqual(result["routing"], "PROBE")
        self.assertFalse(result["session_terminated"])
        self.assertIsNone(result["termination_reason"])

    def test_non_bypass_still_requires_session_start_iso(self):
        """Existing contract preserved: without bypass, turn phase REQUIRES
        session_start_iso. Regression-protects the original guard so a future
        commit can't quietly delete it."""
        with self.assertRaises(ValueError) as ctx:
            ai_service.drill_chat(
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
                nodes_drilled=0,
                attempt_turn_count=0,
                help_turn_count=0,
                session_start_iso=None,
                bypass_session_limits=False,
            )

        self.assertIn("session_start_iso is required", str(ctx.exception))

    def test_score_eligible_true_with_null_classification_demotes_instead_of_raising(self):
        """No-mistakes-flagged path: Gemini-the-model occasionally returns
        score_eligible=True but classification=None. The normalizer used to
        bubble a ValueError (→ 502); now it demotes the turn to unscored and
        keeps the drill alive. Routing falls back to PROBE/NEXT based on
        probe_count."""
        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()),
            patch(
                "ai_service._call_gemini_with_retry",
                return_value=FakeResponse(
                    ai_service.DrillEvaluation(
                        agent_response="Keep going — what comes after the comparison?",
                        generative_commitment=True,
                        answer_mode="attempt",
                        score_eligible=True,
                        help_request_reason="none",
                        classification=None,
                        gap_description=None,
                        routing="PROBE",
                        response_tier=2,
                        response_band="link",
                        tier_reason="Partial structure named.",
                    )
                ),
            ),
        ):
            result = ai_service.drill_chat(
                knowledge_map=sample_knowledge_map(),
                concept_id="thermostat",
                node_id="c1_s1",
                node_label="Setpoint comparison",
                node_mechanism="server-resolved mechanism",
                messages=[
                    {
                        "role": "user",
                        "content": "The thermostat checks the room and the setpoint.",
                    }
                ],
                session_phase="turn",
                drill_mode="re_drill",
                re_drill_count=0,
                probe_count=0,
                nodes_drilled=0,
                attempt_turn_count=0,
                help_turn_count=0,
                session_start_iso=None,
                bypass_session_limits=True,
            )

        # Demoted to unscored; classification stays None; routing is a real value.
        self.assertFalse(result["score_eligible"])
        self.assertIsNone(result["classification"])
        self.assertIn(result["routing"], ("PROBE", "SCAFFOLD", "NEXT"))
        # The drill stays alive — no 502.
        self.assertEqual(result["answer_mode"], "attempt")

    def test_cold_attempt_preserves_classification_after_generative_commitment(self):
        """Cold attempts still need grader evidence once the learner commits.

        The first attempt should route the UI into study, but the classification
        must flow back so the training event can record honest gap state.
        """
        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()),
            patch(
                "ai_service._call_gemini_with_retry",
                return_value=drill_response(routing="NEXT", classification="shallow"),
            ),
        ):
            result = ai_service.drill_chat(
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
                drill_mode="cold_attempt",
                re_drill_count=0,
                probe_count=0,
                nodes_drilled=0,
                attempt_turn_count=0,
                help_turn_count=0,
                session_start_iso=None,
                bypass_session_limits=True,
            )

        self.assertTrue(result["generative_commitment"])
        self.assertTrue(result["score_eligible"])
        self.assertEqual(result["classification"], "shallow")
        self.assertEqual(result["routing"], "NEXT")

    def test_cold_attempt_preserves_score_ineligible_classified_scaffold_echo(self):
        """Classified cold turns can still be non-evidence.

        The prompt contract allows a learner to echo scaffolding with enough
        content to classify the miss while still withholding graph evidence.
        The normalizer must not upgrade that to a recordable cold attempt.
        """
        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()),
            patch(
                "ai_service._call_gemini_with_retry",
                return_value=drill_response(
                    routing="SCAFFOLD",
                    classification="shallow",
                    score_eligible=False,
                ),
            ),
        ):
            result = ai_service.drill_chat(
                knowledge_map=sample_knowledge_map(),
                concept_id="thermostat",
                node_id="c1_s1",
                node_label="Setpoint comparison",
                node_mechanism="server-resolved mechanism",
                messages=[
                    {
                        "role": "user",
                        "content": "It is like the hint says: the thermostat compares things.",
                    }
                ],
                session_phase="turn",
                drill_mode="cold_attempt",
                re_drill_count=0,
                probe_count=0,
                nodes_drilled=0,
                attempt_turn_count=0,
                help_turn_count=0,
                session_start_iso=None,
                bypass_session_limits=True,
            )

        self.assertTrue(result["generative_commitment"])
        self.assertEqual(result["answer_mode"], "attempt")
        self.assertFalse(result["score_eligible"])
        self.assertEqual(result["classification"], "shallow")
        self.assertEqual(result["routing"], "SCAFFOLD")

    def test_cold_attempt_help_request_preserves_inferred_reason(self):
        """Non-substantive cold attempts should preserve typed help intent."""
        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()),
            patch(
                "ai_service._call_gemini_with_retry",
                return_value=drill_response(routing="NEXT", classification="shallow"),
            ),
        ):
            result = ai_service.drill_chat(
                knowledge_map=sample_knowledge_map(),
                concept_id="thermostat",
                node_id="c1_s1",
                node_label="Setpoint comparison",
                node_mechanism="server-resolved mechanism",
                messages=[
                    {
                        "role": "user",
                        "content": "Could you explain this?",
                    }
                ],
                session_phase="turn",
                drill_mode="cold_attempt",
                re_drill_count=0,
                probe_count=0,
                nodes_drilled=0,
                attempt_turn_count=0,
                help_turn_count=0,
                session_start_iso=None,
                bypass_session_limits=True,
            )

        self.assertFalse(result["generative_commitment"])
        self.assertFalse(result["score_eligible"])
        self.assertEqual(result["answer_mode"], "help_request")
        self.assertEqual(result["routing"], "SCAFFOLD")
        self.assertEqual(result["help_request_reason"], "explicit_explain_request")

    def test_cold_attempt_passes_learner_scaffold_into_drill_contract(self):
        """Drill evaluation must see the same scaffold that shaped the UI."""
        captured = {}

        def fake_call(_client, *, model, contents, config):
            captured["contents"] = contents
            captured["system_instruction"] = getattr(config, "system_instruction", "")
            return drill_response(routing="NEXT", classification="deep")

        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()),
            patch("ai_service._call_gemini_with_retry", side_effect=fake_call),
        ):
            ai_service.drill_chat(
                knowledge_map=scaffolded_knowledge_map(),
                concept_id="thermostat",
                node_id="c1_s1",
                node_label="Setpoint comparison",
                node_mechanism="server-resolved mechanism",
                messages=[
                    {
                        "role": "user",
                        "content": "The thermostat compares room temperature to a target.",
                    }
                ],
                session_phase="turn",
                drill_mode="cold_attempt",
                re_drill_count=0,
                probe_count=0,
                nodes_drilled=0,
                attempt_turn_count=0,
                help_turn_count=0,
                session_start_iso=None,
                bypass_session_limits=True,
            )

        self.assertIn("Learner Scaffold", captured["system_instruction"])
        self.assertIn("bloom_level: understand", captured["system_instruction"])
        self.assertIn("evidence_goal: Learner states the comparison", captured["system_instruction"])
        self.assertIn("How would you explain the thermostat loop", captured["contents"])

    def test_repair_drill_context_reaches_prompt_without_replacing_answer_key(self):
        captured = {}
        repair_context = "\n".join(
            [
                "Learner cold draft: It turns on somehow.",
                "Detected repairable gap: Missing the comparison-to-heater bridge.",
                "Learner repair text: Below setpoint means heat turns on.",
            ]
        )

        def fake_call(_client, *, model, contents, config):
            captured["system_instruction"] = getattr(config, "system_instruction", "")
            captured["contents"] = contents
            return drill_response(routing="PROBE", classification="deep")

        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()),
            patch("ai_service._call_gemini_with_retry", side_effect=fake_call),
        ):
            ai_service.drill_chat(
                knowledge_map=sample_knowledge_map(),
                concept_id="thermostat",
                node_id="c1_s1",
                node_label="Setpoint comparison",
                node_mechanism="server-resolved mechanism",
                repair_drill_context=repair_context,
                messages=[
                    {
                        "role": "user",
                        "content": "Below setpoint turns on heat.",
                    }
                ],
                session_phase="turn",
                drill_mode="re_drill",
                re_drill_count=0,
                probe_count=0,
                nodes_drilled=0,
                attempt_turn_count=0,
                help_turn_count=0,
                session_start_iso=None,
                bypass_session_limits=True,
            )

        self.assertIn("Mechanism: server-resolved mechanism", captured["system_instruction"])
        self.assertIn("Focused Repair Context", captured["system_instruction"])
        self.assertNotIn("Detected repairable gap: Missing the comparison-to-heater bridge.", captured["system_instruction"])
        self.assertIn("evaluate only the latest learner message", captured["system_instruction"])
        self.assertIn("Focused repair context", captured["contents"])
        self.assertIn("Detected repairable gap: Missing the comparison-to-heater bridge.", captured["contents"])
        self.assertIn("untrusted learner-authored data", captured["contents"])

    def test_cold_attempt_passes_learner_goal_as_relevance_not_grading(self):
        """Goal may shape the question, but node grading stays local."""
        captured = {}
        knowledge_map = scaffolded_knowledge_map()
        knowledge_map["metadata"][
            "learner_goal"
        ] = "Explain why thermostats avoid overheating a room."

        def fake_call(_client, *, model, contents, config):
            captured["contents"] = contents
            captured["system_instruction"] = getattr(config, "system_instruction", "")
            return drill_response(routing="NEXT", classification="deep")

        with (
            patch.dict(os.environ, {ai_service.DRILL_SESSION_TIME_LIMIT_ENV: "0"}),
            patch("ai_service._get_client", return_value=object()),
            patch("ai_service._call_gemini_with_retry", side_effect=fake_call),
        ):
            ai_service.drill_chat(
                knowledge_map=knowledge_map,
                concept_id="thermostat",
                node_id="c1_s1",
                node_label="Setpoint comparison",
                node_mechanism="server-resolved mechanism",
                messages=[],
                session_phase="init",
                drill_mode="cold_attempt",
                bypass_session_limits=True,
            )

        self.assertIn("learner_goal", captured["contents"])
        self.assertIn(
            "Explain why thermostats avoid overheating a room.", captured["contents"]
        )
        self.assertIn(
            "use `metadata.learner_goal` only to frame relevance",
            captured["system_instruction"],
        )
        self.assertIn(
            "Do not grade against the broad learner goal",
            captured["system_instruction"],
        )


if __name__ == "__main__":
    unittest.main()
