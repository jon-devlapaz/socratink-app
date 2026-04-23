import json
import os
import unittest
from unittest.mock import patch

import main


class SocratinkBrainDrillTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.original_stdout = os.environ.get(main.SOCRATINK_TELEMETRY_STDOUT)
        self.original_capture = os.environ.get(main.SOCRATINK_CAPTURE_DRILL_TRANSCRIPTS)

    def tearDown(self):
        for name, value in (
            (main.SOCRATINK_TELEMETRY_STDOUT, self.original_stdout),
            (main.SOCRATINK_CAPTURE_DRILL_TRANSCRIPTS, self.original_capture),
        ):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def _sample_event(self):
        return {
            "timestamp": "2026-04-12T12:00:00+00:00",
            "status": "success",
            "concept_id": "concept-1",
            "node_id": "core-thesis",
            "node_label": "Core Thesis",
            "drill_session_id": "session-1",
            "client_turn_index": 1,
            "session_key": "concept-1::core-thesis::start::session-1",
            "session_phase": "turn",
            "drill_mode": "re_drill",
            "session_start_iso": "2026-04-12T11:59:00+00:00",
            "message_count_in": 1,
            "messages_in": [{"role": "user", "content": "my private learner answer"}],
            "assistant_message": "assistant feedback",
            "result": {
                "answer_mode": "attempt",
                "generative_commitment": True,
                "classification": "solid",
                "routing": "NEXT",
                "score_eligible": True,
                "graph_mutated": True,
                "ux_reward_emitted": True,
            },
            "transcript": [
                {"role": "user", "content": "my private learner answer"},
                {"role": "assistant", "content": "assistant feedback"},
            ],
        }

    def test_default_runtime_event_summarizes_transcript(self):
        os.environ.pop(main.SOCRATINK_CAPTURE_DRILL_TRANSCRIPTS, None)
        os.environ[main.SOCRATINK_TELEMETRY_STDOUT] = "true"

        with patch("builtins.print") as mock_print:
            main._emit_socratink_brain_drill_event(self._sample_event())

        payload = json.loads(mock_print.call_args.args[0])
        self.assertTrue(payload["socratink_event"])
        self.assertEqual(payload["capture_mode"], "summary")
        self.assertEqual(payload["event"]["classification"], "solid")
        self.assertEqual(payload["event"]["learner_message_chars"], 25)
        self.assertNotIn("messages_in", payload["event"])
        self.assertNotIn("transcript", payload["event"])

    def test_transcript_capture_requires_explicit_env_flag(self):
        os.environ[main.SOCRATINK_CAPTURE_DRILL_TRANSCRIPTS] = "true"
        os.environ[main.SOCRATINK_TELEMETRY_STDOUT] = "true"

        with patch("builtins.print") as mock_print:
            main._emit_socratink_brain_drill_event(self._sample_event())

        payload = json.loads(mock_print.call_args.args[0])
        self.assertEqual(payload["capture_mode"], "transcript")
        self.assertEqual(payload["event"]["messages_in"][0]["content"], "my private learner answer")
        self.assertEqual(payload["event"]["transcript"][1]["content"], "assistant feedback")

    def test_stdout_telemetry_can_be_disabled(self):
        os.environ[main.SOCRATINK_TELEMETRY_STDOUT] = "false"

        with patch("builtins.print") as mock_print:
            main._emit_socratink_brain_drill_event(self._sample_event())

        mock_print.assert_not_called()


if __name__ == "__main__":
    unittest.main()
