"""Network I/O for source_intake.

Owns: URL parsing, SSRF validation (initial + every redirect), pinned-IP
connect (closes DNS rebinding TOCTOU), redirect lifecycle, byte-capped
streaming, content-type policing, header normalization.

This module imports nothing from parse.py or __init__.py. Returns raw bytes
and headers; never interprets charset.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class FetchedSource:
    """Raw fetch result. Headers preserved verbatim with lowercase keys."""
    raw_bytes: bytes
    headers: Mapping[str, str]   # lowercase keys; values verbatim
    final_url: str               # post-redirect canonical URL
    content_type: str            # lowercase, no charset suffix


# Functions implemented in subsequent tasks:
# fetch(url) -> FetchedSource
# _PinnedHTTPSConnection / _PinnedHTTPConnection
# _open_pinned, _read_with_cap


import ipaddress
import socket
from urllib.parse import urlparse

from .errors import BlockedSource, FetchFailed, InvalidUrl

ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443})
SUPPORTED_CONTENT_TYPES = frozenset({"text/html", "text/plain"})
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 12
USER_AGENT = "Mozilla/5.0 (compatible; socratink/1.0; +https://app.socratink.ai)"
VIDEO_HOST_SUFFIXES = ("youtube.com", "youtu.be", "youtube-nocookie.com")


def _validate_outbound_target(url: str) -> list[str]:
    """Pre-fetch validation. Raises InvalidUrl, BlockedSource, or FetchFailed(cause='dns').

    Returns the ordered list of validated global IPs for hostname.

    Called on the initial URL and on every redirect target.

    Order rationale (see spec):
      - scheme first so file://, gopher://, etc. never reach DNS;
      - DNS+private check before port so http://10.0.0.1:25 and :80 both
        surface as private_address (oracle defense);
      - port and denylist last (cheap, but their reasons are user-safe to surface).
    """
    parsed = urlparse(url)

    # 2. Scheme allowlist
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise BlockedSource(f"scheme {parsed.scheme!r}", reason="blocked_scheme")

    # 3. Hostname presence
    if not parsed.hostname:
        raise InvalidUrl(f"missing hostname in {url!r}")

    # 4. Port (parsed.port can raise ValueError on bad ports)
    try:
        port = parsed.port
    except ValueError as exc:
        raise InvalidUrl(f"invalid port in {url!r}") from exc

    # 5a. DNS resolve
    try:
        addrinfo = socket.getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchFailed(f"DNS failure for {parsed.hostname}", cause="dns") from exc

    # 5b. Private IP check — ALL resolved addresses must be global
    validated_ips: list[str] = []
    for _, _, _, _, sockaddr in addrinfo:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError as exc:
            raise BlockedSource(f"unparseable address {ip_str!r}", reason="private_address") from exc
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise BlockedSource(f"non-global address {ip}", reason="private_address")
        validated_ips.append(ip_str)

    # 6. Effective port
    effective_port = port if port is not None else (443 if parsed.scheme == "https" else 80)
    if effective_port not in ALLOWED_PORTS:
        raise BlockedSource(f"port {effective_port}", reason="blocked_port")

    # 7. Video denylist
    host_lower = parsed.hostname.lower()
    if any(host_lower == s or host_lower.endswith("." + s) for s in VIDEO_HOST_SUFFIXES):
        raise BlockedSource(f"video host {host_lower}", reason="blocked_video")

    return validated_ips
