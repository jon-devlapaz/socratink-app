"""Tests for is_substantive_sketch legacy/parity verdicts."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.sketch_validation import is_substantive_sketch


PARITY_FIXTURE = (
    Path(__file__).parent / "fixtures" / "sketch_validation_parity.json"
)


def _load_parity_entries():
    payload = json.loads(PARITY_FIXTURE.read_text())
    return [(e["text"], e["expected_substantive"]) for e in payload["entries"]]


@pytest.mark.parametrize("text,expected", _load_parity_entries())
def test_parity_fixture_entries(text: str, expected: bool):
    """Every parity-fixture entry must produce the labeled result.

    This test is the contract enforced between Python and JS implementations.
    A divergence means the legacy parity contract is broken.
    """
    assert is_substantive_sketch(text) is expected, (
        f"is_substantive_sketch({text!r}) returned "
        f"{is_substantive_sketch(text)!r}, expected {expected!r}"
    )


def test_strips_leading_trailing_whitespace():
    assert is_substantive_sketch("  idk  ") is False
    # Use a fixture-substantive sketch wrapped in extra whitespace.
    # The intent is to verify normalization strips leading/trailing whitespace
    # without lowering the substantiveness threshold.
    sketch = "Plants take in light and somehow make sugar. Not sure where the water goes."
    assert is_substantive_sketch(f"\n\n  {sketch}  \n") is True


def test_case_insensitive_dont_know_patterns():
    for variant in ("IDK", "idk", "Idk", "I Don't Know", "I DON'T KNOW", "no IDEA"):
        assert is_substantive_sketch(variant) is False, f"{variant!r} should be non-substantive"


def test_empty_string_is_non_substantive():
    assert is_substantive_sketch("") is False
    assert is_substantive_sketch("   ") is False


def test_is_dont_know_empty_string():
    from models.sketch_validation import _is_dont_know

    assert _is_dont_know("") is True


def test_dont_know_pattern_with_short_followup():
    assert is_substantive_sketch("idk really") is False
    assert is_substantive_sketch("no idea about plants") is False
    assert is_substantive_sketch("idk really how plants") is False
    assert is_substantive_sketch("idk really maybe something with light water sugar growth") is True
