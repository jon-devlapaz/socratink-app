import unittest

import ai_service


class AppPromptTests(unittest.TestCase):
    def test_production_prompt_files_are_readable(self):
        self.assertTrue(ai_service.EXTRACT_PROMPT_PATH.is_file())
        self.assertTrue(ai_service.DRILL_PROMPT_PATH.is_file())

        extract_prompt = ai_service.EXTRACT_PROMPT_PATH.read_text()
        drill_prompt = ai_service.DRILL_PROMPT_PATH.read_text()

        self.assertIn("THETA EXTRACT", extract_prompt)
        self.assertIn("Socratic Drill Agent", drill_prompt)
        self.assertEqual(ai_service.DRILL_SYSTEM_BASE, drill_prompt)

    def test_prompt_versions_are_explicit(self):
        self.assertEqual(ai_service.EXTRACT_PROMPT_VERSION, "extract-system-v1")
        self.assertEqual(ai_service.DRILL_PROMPT_VERSION, "drill-system-v1")


if __name__ == "__main__":
    unittest.main()
