# tests/source_intake/test_parse_extract_plain.py
"""Tests for parse.extract_plain — pure raw-text normalization."""

import pytest

from source_intake.errors import ParseEmpty
from source_intake.parse import ParsedPage, extract_plain


# === Length thresholds ===

def test_extract_plain_default_min_length_200_raises_on_short():
    with pytest.raises(ParseEmpty):
        extract_plain("x" * 50)


def test_extract_plain_default_min_length_200_passes_long():
    page = extract_plain("hello world. " * 30)  # > 200 chars
    assert isinstance(page, ParsedPage)


def test_extract_plain_min_text_length_parameter_overrides_default():
    """from_text uses min_text_length=1; this is the test that enforces that policy."""
    page = extract_plain("short content", min_text_length=1)
    assert page.text == "short content"


def test_extract_plain_min_text_length_zero_still_rejects_empty_after_strip():
    with pytest.raises(ParseEmpty):
        extract_plain("   \n  \n  ", min_text_length=1)  # only whitespace


# === Title heuristic ===

def test_extract_plain_first_line_becomes_title_when_short():
    text = "My Document Title\n\n" + "body content. " * 30
    page = extract_plain(text)
    assert page.title == "My Document Title"


def test_extract_plain_long_first_line_falls_to_default():
    text = ("very long single line " * 20) + "\n" + "body. " * 50
    page = extract_plain(text)
    assert page.title == "Imported text"


def test_extract_plain_falls_back_to_host_when_long_first_line_with_url():
    text = ("very long single line " * 20) + "\n" + "body. " * 50
    page = extract_plain(text, source_url="https://example.com/article")
    assert page.title == "example.com"


def test_extract_plain_default_title_when_no_url_no_short_first_line():
    text = ("long line " * 30) + "\n" + "body. " * 50
    page = extract_plain(text)
    assert page.title == "Imported text"


# === Whitespace normalization ===

def test_extract_plain_collapses_excessive_blank_lines():
    text = "first\n\n\n\n\nsecond" + "\n" + "x" * 250
    page = extract_plain(text)
    assert "\n\n\n" not in page.text


def test_extract_plain_normalizes_carriage_returns():
    text = "first\r\nsecond" + "\n" + "x" * 250
    page = extract_plain(text)
    assert "\r" not in page.text


# === Control character stripping ===

def test_extract_plain_strips_nul_and_other_control_chars():
    text = "valid\x00\x01\x02 content " + "x" * 250
    page = extract_plain(text)
    assert "\x00" not in page.text
    assert "\x01" not in page.text
    assert "\x02" not in page.text
    # Tab/newline/CR should be preserved (CR converted to \n)
    assert "valid content" in page.text


def test_extract_plain_preserves_tab_and_newline():
    text = "first\ttabbed\nsecond" + "\n" + "x" * 250
    page = extract_plain(text)
    assert "\t" in page.text
    assert "\n" in page.text


# === Length caps ===

def test_extract_plain_truncates_text_at_500k():
    text = "x" * 600_000
    page = extract_plain(text)
    assert len(page.text) <= 500_000


def test_extract_plain_truncates_title_at_200():
    text = ("a" * 250) + "\n" + "x" * 300
    page = extract_plain(text)
    assert len(page.title) <= 200
