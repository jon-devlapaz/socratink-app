"""Smoke tests for app_prompts/generate-from-sketch-system-v1.txt.

Asserts the prompt file describes the source-less generation contract
correctly per spec §5.1.
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROMPT_PATH = (
    Path(__file__).parent.parent / "app_prompts" / "generate-from-sketch-system-v1.txt"
)


@pytest.fixture(scope="module")
def prompt_text() -> str:
    return PROMPT_PATH.read_text()


def test_prompt_file_exists():
    assert PROMPT_PATH.exists(), f"missing: {PROMPT_PATH}"


def test_lc_context_block_role_described(prompt_text: str):
    text = prompt_text.lower()
    assert "<lc_context>" in text
    assert "grounding" in text
    assert "not authoritative" in text or "never authoritative" in text


def test_favor_learner_sketch_rule_present(prompt_text: str):
    text = prompt_text.lower()
    assert ("favor" in text or "prefer" in text or "trust" in text)
    assert "learner" in text and "sketch" in text


def test_hypothesis_framing_present(prompt_text: str):
    text = prompt_text.lower()
    assert "hypothesis" in text or "hypothesize" in text


def test_no_acknowledgment_filler_in_prompt(prompt_text: str):
    text = prompt_text.lower()
    forbidden = ["fair.", "got it,", "great start", "interesting,"]
    for token in forbidden:
        assert token not in text, f"forbidden filler {token!r} in source-less prompt"


def test_output_schema_referenced(prompt_text: str):
    """The output schema must mirror extract-system-v1.txt — say so."""
    text = prompt_text.lower()
    assert "extract-system-v1" in text or "same json" in text or "same schema" in text
