"""Tests for is_substantive_sketch — the shared substantiveness gate."""
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
    A divergence between this and Plan B's JS implementation is a release-blocker.
    """
    assert is_substantive_sketch(text) is expected, (
        f"is_substantive_sketch({text!r}) returned "
        f"{is_substantive_sketch(text)!r}, expected {expected!r}"
    )


def test_strips_leading_trailing_whitespace():
    assert is_substantive_sketch("  idk  ") is False
    assert is_substantive_sketch("\n\n  Plants take in light and make sugar  \n") is True


def test_case_insensitive_dont_know_patterns():
    for variant in ("IDK", "idk", "Idk", "I Don't Know", "I DON'T KNOW", "no IDEA"):
        assert is_substantive_sketch(variant) is False, f"{variant!r} should be non-substantive"


def test_empty_string_is_non_substantive():
    assert is_substantive_sketch("") is False
    assert is_substantive_sketch("   ") is False
