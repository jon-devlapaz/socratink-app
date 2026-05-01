# tests/source_intake/test_fetch_validate.py
"""Tests for fetch._validate_outbound_target.

Validation order (oracle-defense rationale in spec):
1. Parse URL → InvalidUrl on parse failure
2. Scheme not in {http, https} → BlockedSource(blocked_scheme)
3. Hostname missing → InvalidUrl
4. Port via parsed.port (try/except ValueError → InvalidUrl("invalid port"))
5. DNS resolve → FetchFailed(cause="dns") on gaierror; otherwise BlockedSource(private_address) if any IP non-global
6. Effective port not in {80, 443} → BlockedSource(blocked_port)
7. Hostname in video denylist → BlockedSource(blocked_video)
"""

import pytest

from source_intake.errors import BlockedSource, FetchFailed, InvalidUrl
from source_intake.fetch import _validate_outbound_target


# === Scheme allowlist (priority 2) ===

@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "gopher://example.com",
    "data:text/html,<h1>x</h1>",
    "ftp://example.com",
    "javascript:alert(1)",
])
def test_blocks_unsupported_schemes(url, fake_dns):
    fake_dns.set("example.com", ["93.184.216.34"])
    with pytest.raises(BlockedSource) as exc_info:
        _validate_outbound_target(url)
    assert exc_info.value.reason == "blocked_scheme"


# === Hostname missing (priority 3) ===

def test_missing_hostname_raises_invalid_url():
    with pytest.raises(InvalidUrl):
        _validate_outbound_target("http://")


# === Invalid port (priority 4) ===

def test_invalid_port_in_url_raises_invalid_url():
    with pytest.raises(InvalidUrl):
        _validate_outbound_target("http://example.com:99999")


# === DNS failure (priority 5a) ===

def test_dns_failure_raises_fetch_failed(fake_dns):
    """Hostname not in fake_dns answers → gaierror → FetchFailed(cause='dns')."""
    with pytest.raises(FetchFailed) as exc_info:
        _validate_outbound_target("http://nonexistent.invalid")
    assert exc_info.value.cause == "dns"


# === Private IPs (priority 5b) ===

@pytest.mark.parametrize("ip", [
    "10.0.0.1",          # private 10.0.0.0/8
    "172.16.0.1",        # private 172.16.0.0/12
    "192.168.0.1",       # private 192.168.0.0/16
    "127.0.0.1",         # loopback
    "169.254.169.254",   # link-local — AWS IMDS
    "0.0.0.0",           # unspecified
    "100.64.0.1",        # CGN (RFC 6598) — is_private=False on Py3.13, only is_global=False catches it
    "203.0.113.5",       # TEST-NET-3 (RFC 5737)
    "198.51.100.7",      # TEST-NET-2 (RFC 5737)
    "192.0.2.99",        # TEST-NET-1 (RFC 5737)
])
def test_blocks_private_ipv4(ip, fake_dns):
    fake_dns.set("attacker.example", [ip])
    with pytest.raises(BlockedSource) as exc_info:
        _validate_outbound_target("https://attacker.example/")
    assert exc_info.value.reason == "private_address"


@pytest.mark.parametrize("ip", [
    "::1",         # IPv6 loopback
    "fc00::1",     # IPv6 unique-local
    "fe80::1",     # IPv6 link-local
])
def test_blocks_private_ipv6(ip, fake_dns):
    fake_dns.set("attacker.example", [ip])
    with pytest.raises(BlockedSource) as exc_info:
        _validate_outbound_target("https://attacker.example/")
    assert exc_info.value.reason == "private_address"


# === Port allowlist (priority 6) — runs AFTER private check ===

def test_blocks_non_standard_port_on_public_host(fake_dns):
    fake_dns.set("example.com", ["93.184.216.34"])
    with pytest.raises(BlockedSource) as exc_info:
        _validate_outbound_target("https://example.com:8080/")
    assert exc_info.value.reason == "blocked_port"


def test_oracle_defense_private_ip_with_bad_port(fake_dns):
    """http://10.0.0.1:25 must surface as private_address, not blocked_port."""
    fake_dns.set("internal.example", ["10.0.0.1"])
    with pytest.raises(BlockedSource) as exc_info:
        _validate_outbound_target("http://internal.example:25/")
    assert exc_info.value.reason == "private_address"


def test_default_ports_accepted(fake_dns):
    """No explicit port → effective port is scheme default (80/443) → no blocked_port."""
    fake_dns.set("example.com", ["93.184.216.34"])
    # Should not raise:
    ips = _validate_outbound_target("https://example.com/")
    assert "93.184.216.34" in ips


# === Video denylist (priority 7) ===

@pytest.mark.parametrize("url", [
    "https://youtu.be/abc123",
    "https://youtube.com/watch?v=abc",
    "https://www.youtube.com/watch?v=abc",
    "https://m.youtube.com/watch?v=abc",
    "https://youtube-nocookie.com/embed/abc",
    "https://www.youtube-nocookie.com/embed/abc",
])
def test_blocks_youtube_variants(url, fake_dns):
    fake_dns.set("youtu.be", ["142.250.80.110"])
    fake_dns.set("youtube.com", ["142.250.80.110"])
    fake_dns.set("www.youtube.com", ["142.250.80.110"])
    fake_dns.set("m.youtube.com", ["142.250.80.110"])
    fake_dns.set("youtube-nocookie.com", ["142.250.80.110"])
    fake_dns.set("www.youtube-nocookie.com", ["142.250.80.110"])
    with pytest.raises(BlockedSource) as exc_info:
        _validate_outbound_target(url)
    assert exc_info.value.reason == "blocked_video"


# === Happy path ===

def test_valid_global_url_returns_ip_list(fake_dns):
    fake_dns.set("example.com", ["93.184.216.34"])
    ips = _validate_outbound_target("https://example.com/article")
    assert ips == ["93.184.216.34"]


def test_returns_multiple_ips_when_dns_returns_multiple(fake_dns):
    fake_dns.set("example.com", ["93.184.216.34", "93.184.216.35"])
    ips = _validate_outbound_target("https://example.com/")
    assert ips == ["93.184.216.34", "93.184.216.35"]


def test_rejects_when_any_resolved_address_is_private(fake_dns):
    """If hostname resolves to public AND private IPs, reject."""
    fake_dns.set("mixed.example", ["93.184.216.34", "10.0.0.1"])
    with pytest.raises(BlockedSource) as exc_info:
        _validate_outbound_target("https://mixed.example/")
    assert exc_info.value.reason == "private_address"
