# tests/source_intake/test_facade.py
"""Tests for source_intake facade — from_url, from_text, ImportedSource."""

import pytest
from unittest.mock import patch

from source_intake import (
    ImportedSource,
    from_text,
    from_url,
)
from source_intake.errors import ParseEmpty
from source_intake.fetch import FetchedSource


# === ImportedSource value type ===

def test_to_dict_omits_is_remote_source():
    """REGRESSION: is_remote_source is internal; must never appear in API response."""
    src = ImportedSource(
        url="https://example.com",
        title="t",
        text="x" * 250,
        is_remote_source=True,
    )
    body = src.to_dict()
    assert "is_remote_source" not in body
    assert set(body.keys()) == {"url", "title", "text"}


def test_to_dict_includes_url_title_text():
    src = ImportedSource(
        url="https://example.com/page",
        title="Title",
        text="content",
        is_remote_source=True,
    )
    assert src.to_dict() == {"url": "https://example.com/page", "title": "Title", "text": "content"}


def test_imported_source_is_frozen():
    src = ImportedSource(url=None, title="t", text="x" * 250, is_remote_source=False)
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        src.title = "new"


# === from_text ===

def test_from_text_sets_is_remote_source_false():
    src = from_text("hello world content")
    assert src.is_remote_source is False


def test_from_text_url_is_none():
    src = from_text("hello world content")
    assert src.url is None


def test_from_text_default_min_length_one_accepts_short_text():
    """Wire-contract preservation: /api/extract accepts any non-empty text."""
    src = from_text("short")
    assert src.text == "short"


def test_from_text_raises_on_empty_text():
    with pytest.raises(ParseEmpty):
        from_text("")


def test_from_text_raises_on_whitespace_only():
    with pytest.raises(ParseEmpty):
        from_text("   \n  \n  ")


def test_from_text_explicit_min_text_length():
    """Caller can pass min_text_length=200 to enforce URL-path policy."""
    with pytest.raises(ParseEmpty):
        from_text("short", min_text_length=200)


# === from_url with patched fetch ===

def test_from_url_sets_is_remote_source_true():
    fake_html = b"<html><head><title>T</title></head><body>" + b"<p>filler</p>" * 30 + b"</body></html>"
    fake_fetched = FetchedSource(
        raw_bytes=fake_html,
        headers={"content-type": "text/html"},
        final_url="https://example.com/article",
        content_type="text/html",
    )
    with patch("source_intake.fetch.fetch", return_value=fake_fetched):
        src = from_url("https://example.com/article")
    assert src.is_remote_source is True


def test_from_url_uses_final_url_after_redirect():
    fake_html = b"<html><head><title>T</title></head><body>" + b"<p>filler</p>" * 30 + b"</body></html>"
    fake_fetched = FetchedSource(
        raw_bytes=fake_html,
        headers={"content-type": "text/html"},
        final_url="https://example.com/redirected",
        content_type="text/html",
    )
    with patch("source_intake.fetch.fetch", return_value=fake_fetched):
        src = from_url("https://example.com/start")
    assert src.url == "https://example.com/redirected"


def test_from_url_routes_text_plain_to_extract_plain():
    raw_text = ("This is plain text content. " * 30).encode("utf-8")
    fake_fetched = FetchedSource(
        raw_bytes=raw_text,
        headers={"content-type": "text/plain"},
        final_url="https://example.com/file.txt",
        content_type="text/plain",
    )
    with patch("source_intake.fetch.fetch", return_value=fake_fetched):
        src = from_url("https://example.com/file.txt")
    assert "plain text content" in src.text


def test_from_url_routes_html_to_extract_html():
    fake_html = b"<html><head><title>HTML Title</title></head><body>" + b"<p>filler</p>" * 30 + b"</body></html>"
    fake_fetched = FetchedSource(
        raw_bytes=fake_html,
        headers={"content-type": "text/html"},
        final_url="https://example.com/article",
        content_type="text/html",
    )
    with patch("source_intake.fetch.fetch", return_value=fake_fetched):
        src = from_url("https://example.com/article")
    assert src.title == "HTML Title"
