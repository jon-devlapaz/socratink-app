"""Smoke tests for app_prompts/threshold-chat-system-v1.txt.

The prompt must contain explicit anti-filler / Socratic-voice / concept-
derived-analogy directives per spec §3.1, §5.1. These are release-blocker
contracts; this test catches accidental edits that drop them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROMPT_PATH = Path(__file__).parent.parent / "app_prompts" / "threshold-chat-system-v1.txt"


@pytest.fixture(scope="module")
def prompt_text() -> str:
    return PROMPT_PATH.read_text()


def test_prompt_file_exists():
    assert PROMPT_PATH.exists(), f"missing: {PROMPT_PATH}"


def test_no_acknowledgment_clause_present(prompt_text: str):
    assert "no acknowledgments" in prompt_text.lower()


def test_no_affirmations_clause_present(prompt_text: str):
    assert "no affirmations" in prompt_text.lower()


def test_no_preambles_clause_present(prompt_text: str):
    assert "no preambles" in prompt_text.lower()


def test_no_consolation_clause_present(prompt_text: str):
    assert "no consolation" in prompt_text.lower()


def test_concept_derived_analogy_clause_present(prompt_text: str):
    text = prompt_text.lower()
    assert "concept" in text and "analog" in text
    assert ("derive" in text or "fresh" in text or "from the concept" in text), (
        "prompt must instruct the AI to derive the analogy from the learner's "
        "concept rather than templating a fixed example"
    )


def test_no_emoji_or_exclamation_clause_present(prompt_text: str):
    text = prompt_text.lower()
    assert "no emoji" in text
    assert "no exclamation" in text


def test_no_actual_filler_in_examples(prompt_text: str):
    """The prompt itself must not contain example outputs that include filler.

    Catches the kind of regression Gemini's review caught in the spec
    (the original "Fair." example).
    """
    forbidden_in_examples = ["fair.", "got it,", "great start", "interesting,"]
    text = prompt_text.lower()
    for token in forbidden_in_examples:
        assert token not in text, (
            f"prompt contains forbidden filler example {token!r} — see spec §3.1"
        )
