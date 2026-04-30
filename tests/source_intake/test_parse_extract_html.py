# tests/source_intake/test_parse_extract_html.py
"""Tests for parse.extract_html — DOM-based HTML parsing."""

from pathlib import Path

import pytest

from source_intake.errors import ParseEmpty
from source_intake.parse import ParsedPage, extract_html

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


# === Title fallback chain ===

def test_title_uses_title_tag_first():
    html = (
        "<html><head><title>Real Title</title>"
        '<meta property="og:title" content="OG"></head>'
        "<body><h1>H1 Title</h1>" + ("<p>filler text </p>" * 30) + "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert page.title == "Real Title"


def test_title_falls_back_to_og_title():
    page = extract_html(_read("og_title_only.html"), "https://example.com")
    assert page.title == "OG Title Wins"


def test_title_falls_back_to_twitter_title():
    page = extract_html(_read("twitter_title_only.html"), "https://example.com")
    assert page.title == "Twitter Title Wins"


def test_title_falls_back_to_h1():
    page = extract_html(_read("h1_only.html"), "https://example.com")
    assert page.title == "H1 Title Wins"


def test_title_falls_back_to_host():
    html = "<html><body>" + "<p>filler </p>" * 30 + "</body></html>"
    page = extract_html(html, "https://example.com/article")
    assert page.title == "example.com"


def test_title_falls_back_to_default_when_no_host():
    html = "<html><body>" + "<p>filler </p>" * 30 + "</body></html>"
    page = extract_html(html, "")
    assert page.title == "Imported text"


def test_title_handles_entity_references():
    html = (
        "<html><head><title>Foo &amp; Bar</title></head>"
        "<body>" + "<p>filler </p>" * 30 + "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert page.title == "Foo & Bar"


def test_title_skips_empty_title_tag():
    """Empty <title></title> should fall through to og:title."""
    html = (
        '<html><head><title></title><meta property="og:title" content="OG Wins"></head>'
        "<body>" + "<p>filler </p>" * 30 + "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert page.title == "OG Wins"


def test_title_truncated_to_200_chars():
    long_title = "x" * 300
    html = (
        f"<html><head><title>{long_title}</title></head>"
        "<body>" + "<p>filler </p>" * 30 + "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert len(page.title) == 200


# === Text extraction ===

def test_text_extraction_strips_script_tags():
    html = (
        "<html><body>"
        "<script>alert('hi')</script>"
        "<p>visible text</p>"
        + ("<p>filler </p>" * 30) +
        "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert "alert" not in page.text
    assert "visible text" in page.text


def test_text_extraction_strips_style_tags():
    html = (
        "<html><body>"
        "<style>.foo { color: red; }</style>"
        "<p>visible</p>"
        + ("<p>filler </p>" * 30) +
        "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert "color: red" not in page.text
    assert "visible" in page.text


def test_text_preserves_pre_block_indentation():
    page = extract_html(_read("pre_block.html"), "https://example.com")
    assert "    if n" in page.text   # 4-space indentation preserved
    assert "        return 1" in page.text   # 8-space indentation preserved


def test_text_strips_control_characters():
    html = (
        "<html><body>"
        "<p>visible\x00\x01 text</p>"
        + ("<p>filler </p>" * 30) +
        "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert "\x00" not in page.text
    assert "\x01" not in page.text


def test_text_collapses_excessive_blank_lines():
    """Three+ consecutive newlines collapse to two."""
    html = "<html><body>" + ("<p>filler </p><br><br><br><br>" * 30) + "</body></html>"
    page = extract_html(html, "https://example.com")
    assert "\n\n\n" not in page.text


# === ParseEmpty ===

def test_extract_html_raises_parse_empty_on_thin_content():
    html = "<html><body><p>too short</p></body></html>"
    with pytest.raises(ParseEmpty):
        extract_html(html, "https://example.com")


def test_extract_html_raises_parse_empty_on_only_scripts():
    """Page with only <script> content extracts to empty body text."""
    html = "<html><body><script>" + ("var x = 1; " * 100) + "</script></body></html>"
    with pytest.raises(ParseEmpty):
        extract_html(html, "https://example.com")


# === Length caps ===

def test_text_truncated_at_500k():
    long_body = "<p>" + ("x" * 100) + "</p>"
    html = "<html><body>" + (long_body * 7000) + "</body></html>"
    page = extract_html(html, "https://example.com")
    assert len(page.text) <= 500_000
