"""Tests for source_intake domain exceptions."""

import pytest

from source_intake.errors import (
    BlockedSource,
    FetchFailed,
    InvalidUrl,
    ParseEmpty,
    SourceIntakeError,
    TooLarge,
    UnsupportedContent,
)


def test_all_subclass_source_intake_error():
    """Single base class lets routes catch all module exceptions uniformly."""
    for cls in (InvalidUrl, BlockedSource, FetchFailed, UnsupportedContent, TooLarge, ParseEmpty):
        assert issubclass(cls, SourceIntakeError)


def test_blocked_source_carries_reason():
    exc = BlockedSource("private 10.0.0.1", reason="private_address")
    assert exc.reason == "private_address"
    assert "private 10.0.0.1" in str(exc)


@pytest.mark.parametrize("reason", ["private_address", "blocked_port", "blocked_video", "blocked_scheme"])
def test_blocked_source_reasons(reason):
    exc = BlockedSource("test", reason=reason)
    assert exc.reason == reason


def test_blocked_source_requires_keyword_reason():
    with pytest.raises(TypeError):
        BlockedSource("test", "private_address")  # positional should fail


def test_fetch_failed_carries_cause():
    exc = FetchFailed("DNS lookup failed", cause="dns")
    assert exc.cause == "dns"
    assert "DNS lookup failed" in str(exc)


@pytest.mark.parametrize("cause", ["dns", "connect", "timeout", "http_4xx", "http_5xx"])
def test_fetch_failed_causes(cause):
    exc = FetchFailed("test", cause=cause)
    assert exc.cause == cause


def test_fetch_failed_requires_keyword_cause():
    with pytest.raises(TypeError):
        FetchFailed("test", "dns")  # positional should fail


def test_simple_exceptions_take_message_only():
    """InvalidUrl, UnsupportedContent, TooLarge, ParseEmpty have no extra attrs."""
    for cls in (InvalidUrl, UnsupportedContent, TooLarge, ParseEmpty):
        exc = cls("test message")
        assert "test message" in str(exc)
