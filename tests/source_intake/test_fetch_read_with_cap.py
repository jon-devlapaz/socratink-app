# tests/source_intake/test_fetch_read_with_cap.py
"""Tests for fetch._read_with_cap — streaming abort at byte cap and
mid-body exception wrapping."""

import pytest
from urllib3.exceptions import ProtocolError, ReadTimeoutError, SSLError

from source_intake.errors import FetchFailed, TooLarge
from source_intake.fetch import _read_with_cap


class _FakeStreamingResponse:
    """Mimics the urllib3 response.stream() interface for tests."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    def stream(self, amt: int = 16384, decode_content: bool = False):
        for chunk in self._chunks:
            yield chunk


class _FakeFailingStream:
    """Yields some chunks then raises a urllib3 exception mid-iteration."""

    def __init__(self, chunks_before_fail: list[bytes], exc: Exception):
        self._chunks = chunks_before_fail
        self._exc = exc

    def stream(self, amt: int = 16384, decode_content: bool = False):
        for chunk in self._chunks:
            yield chunk
        raise self._exc


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


# === Mid-body exception wrapping (closes the 500-vs-502 leak flagged
#     by no-mistakes review on PR #66 / commit 2ffb2ee). Stream-read
#     exceptions must surface as FetchFailed so the route layer maps
#     them to 502, matching connection-establish exceptions. ===


def test_read_with_cap_wraps_read_timeout_in_fetch_failed():
    response = _FakeFailingStream([b"partial"], ReadTimeoutError(None, "test", "read timeout"))
    with pytest.raises(FetchFailed) as exc_info:
        _read_with_cap(response, max_bytes=1024)
    assert exc_info.value.cause == "timeout"
    assert "raw text" not in str(exc_info.value)


def test_read_with_cap_wraps_protocol_error_in_fetch_failed():
    response = _FakeFailingStream([b"partial"], ProtocolError("connection reset"))
    with pytest.raises(FetchFailed) as exc_info:
        _read_with_cap(response, max_bytes=1024)
    assert exc_info.value.cause == "connect"


def test_read_with_cap_wraps_ssl_error_in_fetch_failed():
    response = _FakeFailingStream([b"partial"], SSLError("ssl handshake interrupted"))
    with pytest.raises(FetchFailed) as exc_info:
        _read_with_cap(response, max_bytes=1024)
    assert exc_info.value.cause == "connect"
