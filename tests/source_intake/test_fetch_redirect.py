# tests/source_intake/test_fetch_redirect.py
"""Tests for redirect re-validation."""

import pytest

from source_intake.errors import BlockedSource, FetchFailed


def test_simple_redirect_followed(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["/start"] = {"status": 302, "headers": {"Location": "/dest"}, "body": b""}
    handler.SCRIPT["/dest"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": b"<html><body>" + b"<p>filler</p>" * 30 + b"</body></html>",
    }
    result = _fetch("/start")
    assert result.final_url.endswith("/dest")
    assert b"filler" in result.raw_bytes


def test_redirect_to_private_ip_blocked(fetch_against_local, fake_dns):
    """302 to a hostname that resolves to private IP must be rejected."""
    fake_dns.set("internal.example", ["10.0.0.1"])
    _fetch, handler = fetch_against_local
    handler.SCRIPT["/start"] = {
        "status": 302,
        "headers": {"Location": "http://internal.example/admin"},
        "body": b"",
    }
    with pytest.raises(BlockedSource) as exc_info:
        _fetch("/start")
    assert exc_info.value.reason == "private_address"


def test_redirect_to_blocked_scheme(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["/start"] = {
        "status": 302,
        "headers": {"Location": "file:///etc/passwd"},
        "body": b"",
    }
    with pytest.raises(BlockedSource) as exc_info:
        _fetch("/start")
    assert exc_info.value.reason == "blocked_scheme"


def test_max_redirects_enforced(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["/loop"] = {"status": 302, "headers": {"Location": "/loop"}, "body": b""}
    with pytest.raises(FetchFailed) as exc_info:
        _fetch("/loop")
    assert exc_info.value.cause == "connect"
    assert "too many redirects" in str(exc_info.value).lower()


def test_3xx_without_location_raises(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["/bad"] = {"status": 302, "headers": {}, "body": b""}
    with pytest.raises(FetchFailed):
        _fetch("/bad")
