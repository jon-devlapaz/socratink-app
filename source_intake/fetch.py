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

from .errors import BlockedSource, FetchFailed, InvalidUrl, UnsupportedContent

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


from .errors import FetchFailed, TooLarge


def _read_with_cap(response, max_bytes: int) -> bytes:
    """Stream-read up to max_bytes; raise TooLarge if exceeded.

    Uses response.stream() in chunks; aborts as soon as cumulative size
    exceeds cap. Does not trust Content-Length. Does not auto-decompress
    (decode_content=False, paired with Accept-Encoding: identity at request).

    Mid-body urllib3 exceptions (ReadTimeoutError, ProtocolError, SSLError)
    are wrapped as FetchFailed so the route layer maps them to 502, matching
    connection-establishment exceptions instead of leaking as 500.
    """
    chunks: list[bytes] = []
    total = 0
    try:
        for chunk in response.stream(amt=16384, decode_content=False):
            total += len(chunk)
            if total > max_bytes:
                raise TooLarge(f"exceeded {max_bytes} bytes")
            chunks.append(chunk)
    except TooLarge:
        raise
    except ReadTimeoutError as exc:
        raise FetchFailed(f"body read timeout: {exc}", cause="timeout") from exc
    except (ProtocolError, SSLError) as exc:
        raise FetchFailed(
            f"body stream interrupted: {type(exc).__name__}", cause="connect"
        ) from exc
    return b"".join(chunks)


import socket as _socket
from urllib.parse import urljoin

import urllib3
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import (
    ConnectTimeoutError,
    NewConnectionError,
    ProtocolError,
    ReadTimeoutError,
    SSLError,
)
from urllib3.util import Timeout


class _PinnedHTTPSConnection(HTTPSConnection):
    """Connects to a pre-validated IP while preserving Host/SNI/cert verification
    against the original hostname. Closes DNS rebinding TOCTOU."""

    def __init__(self, *args, dest_ip: str | None = None, **kwargs):
        self._dest_ip = dest_ip
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        # Connect to self._dest_ip on self.port.
        # self.host stays as the hostname for SNI and cert verification.
        if self._dest_ip is None:
            return super()._new_conn()
        try:
            sock = _socket.create_connection(
                (self._dest_ip, self.port),
                timeout=self.timeout if self.timeout else None,
                source_address=self.source_address,
            )
        except OSError as exc:
            raise NewConnectionError(self, f"failed to establish a new connection: {exc}") from exc
        return sock


class _PinnedHTTPConnection(HTTPConnection):
    """Plain-http variant of the pinned connection."""

    def __init__(self, *args, dest_ip: str | None = None, **kwargs):
        self._dest_ip = dest_ip
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        if self._dest_ip is None:
            return super()._new_conn()
        try:
            sock = _socket.create_connection(
                (self._dest_ip, self.port),
                timeout=self.timeout if self.timeout else None,
                source_address=self.source_address,
            )
        except OSError as exc:
            raise NewConnectionError(self, f"failed to establish a new connection: {exc}") from exc
        return sock


class _PinnedHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _PinnedHTTPSConnection

    def __init__(self, host, port, dest_ip, timeout):
        super().__init__(host=host, port=port, timeout=timeout, retries=False)
        self._dest_ip = dest_ip

    def _new_conn(self):
        return self.ConnectionCls(
            host=self.host, port=self.port, dest_ip=self._dest_ip,
            timeout=self.timeout.connect_timeout,
        )


class _PinnedHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = _PinnedHTTPConnection

    def __init__(self, host, port, dest_ip, timeout):
        super().__init__(host=host, port=port, timeout=timeout, retries=False)
        self._dest_ip = dest_ip

    def _new_conn(self):
        return self.ConnectionCls(
            host=self.host, port=self.port, dest_ip=self._dest_ip,
            timeout=self.timeout.connect_timeout,
        )


def _build_pinned_pool(parsed, dest_ip: str):
    """Construct a single-use pool pinned to dest_ip."""
    host = parsed.hostname
    scheme = parsed.scheme
    port = parsed.port or (443 if scheme == "https" else 80)
    timeout = Timeout(total=TIMEOUT_SECONDS)

    if scheme == "https":
        return _PinnedHTTPSConnectionPool(host=host, port=port, dest_ip=dest_ip, timeout=timeout)
    return _PinnedHTTPConnectionPool(host=host, port=port, dest_ip=dest_ip, timeout=timeout)


def _open_pinned(url: str, validated_ips: list[str]):
    """Try each validated IP in order; first connect wins.

    Sends a relative request target (path + query). Direct origin connections
    expect origin-form, not absolute URL.
    """
    parsed = urlparse(url)
    request_target = parsed.path or "/"
    if parsed.query:
        request_target = f"{request_target}?{parsed.query}"

    last_exc: Exception | None = None
    for ip in validated_ips:
        try:
            pool = _build_pinned_pool(parsed, ip)
            return pool.urlopen(
                "GET",
                request_target,
                headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
                redirect=False,
                preload_content=False,
                decode_content=False,
                timeout=Timeout(total=TIMEOUT_SECONDS),
            )
        except (NewConnectionError, ConnectTimeoutError) as exc:
            last_exc = exc
            continue
    raise FetchFailed("all validated IPs unreachable", cause="connect") from last_exc


import logging

logger = logging.getLogger(__name__)


def fetch(url: str) -> FetchedSource:
    """Fetch URL with SSRF + redirect re-validation, pinned-IP connect, byte cap.

    Raises any of: InvalidUrl, BlockedSource, FetchFailed, UnsupportedContent, TooLarge.
    """
    current_url = url
    redirects = 0

    while True:
        validated_ips = _validate_outbound_target(current_url)

        try:
            response = _open_pinned(current_url, validated_ips)
        except (ConnectTimeoutError, ReadTimeoutError) as exc:
            raise FetchFailed(f"timeout: {exc}", cause="timeout") from exc
        except (NewConnectionError, ProtocolError) as exc:
            raise FetchFailed(f"connect: {exc}", cause="connect") from exc

        try:
            # Redirects: extract Location, release, re-loop with re-validation.
            if 300 <= response.status < 400:
                location = response.headers.get("Location") or response.headers.get("location")
                response.release_conn()
                if not location:
                    raise FetchFailed("3xx without Location", cause="connect")
                redirects += 1
                if redirects > MAX_REDIRECTS:
                    raise FetchFailed("too many redirects", cause="connect")
                current_url = urljoin(current_url, location)
                continue

            # 4xx / 5xx: urllib3 returns these as responses, not exceptions.
            if 400 <= response.status < 500:
                response.release_conn()
                raise FetchFailed(f"upstream HTTP {response.status}", cause="http_4xx")
            if 500 <= response.status < 600:
                response.release_conn()
                raise FetchFailed(f"upstream HTTP {response.status}", cause="http_5xx")

            # Reject server-side compression
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                response.release_conn()
                raise UnsupportedContent("server returned encoded content")

            # Content-type policing
            content_type_header = response.headers.get("content-type", "") or ""
            if not content_type_header:
                response.release_conn()
                raise UnsupportedContent("missing content-type")
            content_type = content_type_header.split(";")[0].strip().lower()
            if content_type not in SUPPORTED_CONTENT_TYPES:
                response.release_conn()
                raise UnsupportedContent(f"content-type {content_type!r}")

            # Stream with byte cap
            try:
                raw = _read_with_cap(response, MAX_BYTES)
            except Exception:
                response.release_conn()
                raise

            response.release_conn()

            # Normalize headers: lowercase keys
            headers = {k.lower(): v for k, v in response.headers.items()}
            return FetchedSource(
                raw_bytes=raw,
                headers=headers,
                final_url=current_url,
                content_type=content_type,
            )
        except Exception:
            try:
                response.release_conn()
            except Exception:
                pass
            raise
