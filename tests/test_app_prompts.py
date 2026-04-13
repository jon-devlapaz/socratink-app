import unittest

import ai_service


class AppPromptTests(unittest.TestCase):
    def test_production_prompt_files_are_readable(self):
        self.assertTrue(ai_service.EXTRACT_PROMPT_PATH.is_file())
        self.assertTrue(ai_service.DRILL_PROMPT_PATH.is_file())
        self.assertTrue(ai_service.REPAIR_REPS_PROMPT_PATH.is_file())

        extract_prompt = ai_service.EXTRACT_PROMPT_PATH.read_text()
        drill_prompt = ai_service.DRILL_PROMPT_PATH.read_text()
        repair_prompt = ai_service.REPAIR_REPS_PROMPT_PATH.read_text()

        self.assertIn("THETA EXTRACT", extract_prompt)
        self.assertIn("Socratic Drill Agent", drill_prompt)
        self.assertIn("Repair Reps Agent", repair_prompt)
        self.assertEqual(ai_service.DRILL_SYSTEM_BASE, drill_prompt)
        self.assertEqual(ai_service.REPAIR_REPS_SYSTEM_BASE, repair_prompt)

    def test_prompt_versions_are_explicit(self):
        self.assertEqual(ai_service.EXTRACT_PROMPT_VERSION, "extract-system-v1")
        self.assertEqual(ai_service.DRILL_PROMPT_VERSION, "drill-system-v1")
        self.assertEqual(ai_service.REPAIR_REPS_PROMPT_VERSION, "repair-reps-system-v1")

    def test_repair_reps_prompt_bans_recognition_and_mastery_shortcuts(self):
        repair_prompt = ai_service.REPAIR_REPS_PROMPT_PATH.read_text()

        for phrase in [
            "term-definition cards",
            "multiple choice",
            "choose the right term",
            "answer-key previews",
            "mastery/progression claims",
            "solidified",
            "graph unlock copy",
        ]:
            self.assertIn(phrase, repair_prompt)

        for phrase in [
            "missing_bridge",
            "next_step",
            "cause_effect",
            "typed causal reconstruction",
        ]:
            self.assertIn(phrase, repair_prompt)


if __name__ == "__main__":
    unittest.main()
