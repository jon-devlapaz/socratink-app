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

    def test_drill_prompt_preserves_structured_output_contract(self):
        drill_prompt = ai_service.DRILL_PROMPT_PATH.read_text()

        for phrase in [
            "Target Node (ANSWER KEY)",
            "Learner Scaffold",
            "`bloom_level`",
            "Structured Output Contract",
            "`agent_response`",
            "`answer_mode`",
            "`score_eligible`",
            "`help_request_reason`",
            "`classification`",
            "`routing`",
            "`gap_description`",
            "`response_tier`",
            "`response_band`",
            "`tier_reason`",
        ]:
            self.assertIn(phrase, drill_prompt)

    def test_drill_prompt_encodes_reconstruction_throughline(self):
        drill_prompt = ai_service.DRILL_PROMPT_PATH.read_text()

        for phrase in [
            "socratink turns material into reconstruction targets",
            "learner attempts expose repairable gaps",
            "records learning evidence only when the learner reconstructs from memory under the right conditions",
            "Generation Before Recognition",
            "source material, learner goal, learner sketch, and learner scaffold are context, not evidence",
            "Bloom is internal node-intent grammar",
        ]:
            self.assertIn(phrase, drill_prompt)

    def test_drill_prompt_docs_encode_reconstruction_throughline(self):
        readme = (ai_service.PROMPT_DIR / "README.md").read_text()

        for phrase in [
            "turns material into reconstruction targets",
            "uses learner attempts to expose repairable gaps",
            "classifies reconstruction attempts for the app to record",
            "Source material, learner goals, learner sketches, and learner scaffolds are context, not evidence",
            "Bloom/node-intent grammar stays internal",
        ]:
            self.assertIn(phrase, readme)

    def test_drill_prompt_blocks_scaffold_echoes_from_evidence(self):
        drill_prompt = ai_service.DRILL_PROMPT_PATH.read_text()

        for phrase in [
            "If this turn or prior assistant history revealed or supplied the mechanism",
            "score_eligible = false",
            "echoes or paraphrases that scaffold",
            "independent causal reconstruction beyond the revealed wording",
        ]:
            self.assertIn(phrase, drill_prompt)

    def test_bounded_drill_prompt_surfaces_do_not_reuse_retired_framing(self):
        surfaces = {
            "drill prompt": ai_service.DRILL_PROMPT_PATH.read_text(),
            "app prompts README": (ai_service.PROMPT_DIR / "README.md").read_text(),
        }
        retired_phrases = [
            "Theta",
            "Stage 3",
            "LearnOps pipeline",
            "evaluator taxonomy",
            "neurocognitive",
            "taxonomy and input type constraints",
        ]

        for surface_name, surface_text in surfaces.items():
            for phrase in retired_phrases:
                with self.subTest(surface=surface_name, phrase=phrase):
                    self.assertNotIn(phrase, surface_text)

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
