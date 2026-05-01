# tests/source_intake/test_fetch_pinned_ip.py
"""Tests for pinned-IP connect (DNS rebinding closure).

Strategy: fake_dns returns a globally-routable IP (1.1.1.1) so it passes
the SSRF validator. The pinned-shim records the intended dest_ip and
overrides _new_conn to raise NewConnectionError so no real packets leave
the test environment.
"""

import pytest

from source_intake.errors import FetchFailed
from source_intake.fetch import fetch


def test_pinned_connection_records_validated_ip(fake_dns, pinned_shim_records):
    """When DNS returns a global IP, the pinned connection is constructed with
    that IP (not whatever DNS would return on a re-resolve)."""
    fake_dns.set("example.com", ["1.1.1.1"])
    pinned_shim_records.reset()

    # Connection will fail (we're not running a server), but we just want to
    # observe that the construction happened with the right pinned IP.
    with pytest.raises(FetchFailed):
        fetch("https://example.com/article")

    assert "1.1.1.1" in pinned_shim_records.dest_ips


def test_dns_rebinding_does_not_re_resolve(fake_dns, pinned_shim_records):
    """First DNS lookup returns global IP (passes validation).
    Second lookup (if it happened) would return 127.0.0.1.
    Pinned connect must ignore the second answer."""
    fake_dns.set_sequence("example.com", [["1.1.1.1"], ["127.0.0.1"]])
    pinned_shim_records.reset()

    with pytest.raises(FetchFailed):
        fetch("https://example.com/article")

    # Validator did exactly ONE getaddrinfo call (count is 1).
    assert fake_dns.lookup_count("example.com") == 1
    # Connection dest was the validated IP, not the rebound one.
    assert pinned_shim_records.dest_ips == ["1.1.1.1"]
    assert "127.0.0.1" not in pinned_shim_records.dest_ips
