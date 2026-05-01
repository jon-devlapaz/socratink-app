# tests/source_intake/test_fetch_content_type.py
"""Tests for fetch content-type policing and HTTP error mapping."""

import pytest

from source_intake.errors import FetchFailed, UnsupportedContent


def test_404_raises_fetch_failed_http_4xx(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {"status": 404, "body": b"not found"}
    with pytest.raises(FetchFailed) as exc_info:
        _fetch("/missing")
    assert exc_info.value.cause == "http_4xx"


def test_503_raises_fetch_failed_http_5xx(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {"status": 503, "body": b"unavailable"}
    with pytest.raises(FetchFailed) as exc_info:
        _fetch("/")
    assert exc_info.value.cause == "http_5xx"


def test_unsupported_content_type_raises(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "application/pdf"},
        "body": b"%PDF-1.4 ...",
    }
    with pytest.raises(UnsupportedContent):
        _fetch("/")


def test_missing_content_type_header_raises(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {},  # no Content-Type at all
        "body": b"hi",
    }
    with pytest.raises(UnsupportedContent):
        _fetch("/")


def test_encoded_content_rejected(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {
            "Content-Type": "text/html",
            "Content-Encoding": "gzip",
        },
        "body": b"\x1f\x8b... fake gzip",
    }
    with pytest.raises(UnsupportedContent):
        _fetch("/")


def test_text_html_accepted(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": b"<html><body>" + b"<p>filler</p>" * 30 + b"</body></html>",
    }
    result = _fetch("/")
    assert result.content_type == "text/html"
    assert b"filler" in result.raw_bytes


def test_text_plain_accepted(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/plain"},
        "body": b"plain text content",
    }
    result = _fetch("/")
    assert result.content_type == "text/plain"
    assert result.raw_bytes == b"plain text content"


def test_final_url_carries_through_to_fetched_source(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": b"<html><body>" + b"<p>filler</p>" * 30 + b"</body></html>",
    }
    result = _fetch("/page")
    assert result.final_url == "http://test.example/page"


def test_headers_normalized_to_lowercase(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {
            "Content-Type": "text/html",
            "X-Custom-Header": "value",
        },
        "body": b"<html><body>" + b"<p>filler</p>" * 30 + b"</body></html>",
    }
    result = _fetch("/")
    assert "content-type" in result.headers
    assert "x-custom-header" in result.headers
    assert "Content-Type" not in result.headers
