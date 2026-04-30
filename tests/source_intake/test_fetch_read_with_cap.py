# tests/source_intake/test_fetch_read_with_cap.py
"""Tests for fetch._read_with_cap — streaming abort at byte cap."""

import pytest

from source_intake.errors import TooLarge
from source_intake.fetch import _read_with_cap


class _FakeStreamingResponse:
    """Mimics the urllib3 response.stream() interface for tests."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    def stream(self, amt: int = 16384, decode_content: bool = False):
        for chunk in self._chunks:
            yield chunk


def test_read_with_cap_returns_full_body_below_cap():
    response = _FakeStreamingResponse([b"hello", b" ", b"world"])
    raw = _read_with_cap(response, max_bytes=100)
    assert raw == b"hello world"


def test_read_with_cap_raises_too_large_when_exceeded():
    big_chunk = b"x" * 10
    response = _FakeStreamingResponse([big_chunk] * 100)  # 1000 bytes total
    with pytest.raises(TooLarge):
        _read_with_cap(response, max_bytes=50)


def test_read_with_cap_aborts_on_first_chunk_over_cap():
    """A single oversized chunk triggers TooLarge immediately."""
    response = _FakeStreamingResponse([b"x" * 10_000])
    with pytest.raises(TooLarge):
        _read_with_cap(response, max_bytes=100)


def test_read_with_cap_handles_empty_response():
    response = _FakeStreamingResponse([])
    raw = _read_with_cap(response, max_bytes=100)
    assert raw == b""


def test_read_with_cap_exact_boundary():
    """Reading exactly max_bytes is allowed; one byte over is rejected."""
    response = _FakeStreamingResponse([b"x" * 100])
    raw = _read_with_cap(response, max_bytes=100)
    assert len(raw) == 100

    response_over = _FakeStreamingResponse([b"x" * 101])
    with pytest.raises(TooLarge):
        _read_with_cap(response_over, max_bytes=100)
