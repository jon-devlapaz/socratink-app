# tests/source_intake/test_fetch_size_cap.py
"""Tests for streaming size cap (proves preload_content=False is in effect)."""

import time

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
    """Slow streaming server: 10MB at ~100KB/s.
    Cap is 2MB, so abort must happen well before the full transfer time.
    Without preload_content=False, urllib3 would buffer the entire response
    before our cap check fires — this test catches that regression."""
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": b"x" * 10_000_000,
        "delay_seconds_per_kb": 0.01,
    }
    start = time.monotonic()
    with pytest.raises(TooLarge):
        _fetch("/")
    elapsed = time.monotonic() - start
    assert elapsed < 30, f"size cap took too long ({elapsed:.1f}s) — likely buffered"


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
