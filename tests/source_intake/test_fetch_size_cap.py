# tests/source_intake/test_fetch_size_cap.py
"""Tests for streaming size cap (proves preload_content=False is in effect)."""

import pytest

from source_intake.errors import TooLarge


def test_oversized_response_raises_too_large(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": b"<html><body>" + (b"x" * 3_000_000) + b"</body></html>",
    }
    with pytest.raises(TooLarge):
        _fetch("/")


def test_size_cap_aborts_before_full_read(fetch_against_local):
    """Slow streaming server: 10MB body delivered in 1KB chunks with a delay.
    Cap is 2MB. Without preload_content=False, urllib3 would buffer the entire
    10MB before the cap check fires; with streaming, the client closes the
    connection mid-transfer and the server delivers far fewer bytes than the
    full body. We assert the server-side bytes-written count rather than wall
    clock, which is robust across platforms with coarse sleep precision."""
    _fetch, handler = fetch_against_local
    spec = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": b"x" * 10_000_000,
        "delay_seconds_per_kb": 0.005,
    }
    handler.SCRIPT["__default__"] = spec
    with pytest.raises(TooLarge):
        _fetch("/")
    bytes_written = spec.get("_bytes_written")
    assert bytes_written is not None, "server did not record bytes_written"
    assert bytes_written < 5_000_000, (
        f"server delivered {bytes_written} bytes — cap is reading entire "
        "response (preload regression)"
    )


def test_at_cap_boundary_accepted(fetch_against_local):
    """A response close to but under 2MB is accepted."""
    _fetch, handler = fetch_against_local
    body = b"<html><body>" + (b"x" * (2_000_000 - 30)) + b"</body></html>"
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": body,
    }
    result = _fetch("/")
    assert len(result.raw_bytes) <= 2_000_000
