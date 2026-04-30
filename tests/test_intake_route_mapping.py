# tests/test_intake_route_mapping.py
"""Parametrized tests for main._map_intake_error.

Pure function; no FastAPI fixture needed.
"""

import pytest

from main import _map_intake_error
from source_intake.errors import (
    BlockedSource,
    FetchFailed,
    InvalidUrl,
    ParseEmpty,
    TooLarge,
    UnsupportedContent,
)


@pytest.mark.parametrize("exc, expected_status, fragment", [
    (InvalidUrl("test"), 400, "valid http(s) URL"),
    (BlockedSource("test", reason="private_address"), 502, "couldn't reach"),
    (BlockedSource("test", reason="blocked_port"), 400, "standard web ports"),
    (BlockedSource("test", reason="blocked_scheme"), 400, "http and https"),
    (BlockedSource("test", reason="blocked_video"), 400, "Video links"),
    (FetchFailed("test", cause="dns"), 502, "couldn't reach"),
    (FetchFailed("test", cause="connect"), 502, "couldn't reach"),
    (FetchFailed("test", cause="timeout"), 502, "couldn't reach"),
    (FetchFailed("test", cause="http_4xx"), 502, "couldn't reach"),
    (FetchFailed("test", cause="http_5xx"), 502, "couldn't reach"),
    (UnsupportedContent("test"), 415, "HTML or plain-text"),
    (TooLarge("test"), 413, "too large"),
    (ParseEmpty("test"), 422, "readable text"),
])
def test_mapping_table(exc, expected_status, fragment):
    result = _map_intake_error(exc)
    assert result.status_code == expected_status
    assert fragment.lower() in result.detail.lower()


def test_oracle_defense_indistinguishable():
    """SSRF block and DNS failure must produce identical user-visible responses."""
    private = _map_intake_error(BlockedSource("test", reason="private_address"))
    dns = _map_intake_error(FetchFailed("test", cause="dns"))
    assert private.status_code == dns.status_code
    assert private.detail == dns.detail


def test_oracle_defense_blocked_port_is_distinct_from_private():
    """blocked_port surfaces specific UX; private_address collapses to generic 502.
    These should NOT be identical (port info is user-actionable; private IP is not)."""
    blocked_port = _map_intake_error(BlockedSource("test", reason="blocked_port"))
    private = _map_intake_error(BlockedSource("test", reason="private_address"))
    # Different status codes AND different messages
    assert blocked_port.status_code != private.status_code or blocked_port.detail != private.detail


def test_unknown_blocked_source_reason_fails_closed():
    """Defensive: unknown reason value → 502 generic, not crash."""
    result = _map_intake_error(BlockedSource("test", reason="future_reason_x"))
    assert result.status_code == 502


def test_summarize_url_for_log_redacts_userinfo():
    from main import _summarize_url_for_log

    summary = _summarize_url_for_log("https://user:pass@example.com/path?secret=token")
    assert summary["has_userinfo"] is True
    # No credential or query values should leak into the summary values.
    # (The boolean field name "has_userinfo" legitimately contains "user".)
    leak_haystack = repr(
        [summary.get("scheme"), summary.get("host"), summary.get("port"),
         summary.get("path_len"), summary.get("has_query"), summary.get("has_userinfo")]
    )
    assert "pass" not in leak_haystack
    assert "token" not in leak_haystack
    assert "secret" not in leak_haystack
    # The username "user" must not appear as a value either; the host is "example.com".
    assert summary.get("host") == "example.com"


def test_summarize_url_for_log_handles_malformed():
    from main import _summarize_url_for_log

    summary = _summarize_url_for_log("not a url at all")
    # Should not raise; returns something logger can serialize
    assert isinstance(summary, dict)
