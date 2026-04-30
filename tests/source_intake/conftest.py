# tests/source_intake/conftest.py
"""Test fixtures for source_intake tests.

fake_dns:                monkey-patches socket.getaddrinfo with controlled answers
local_redirect_server:   stdlib HTTP server returning 302 with configurable Location
slow_large_server:       stdlib HTTP server streaming controlled-rate large bodies
pinned_shim_records:     captures intended dest_ip from _PinnedHTTPSConnection
"""

from __future__ import annotations

import socket
from typing import Iterator

import pytest


class _FakeDns:
    def __init__(self):
        # hostname → list of IPs, OR list of [list, list, ...] for sequential responses
        self._answers: dict[str, list] = {}
        self._call_counts: dict[str, int] = {}
        self._sequence_indexes: dict[str, int] = {}

    def set(self, hostname: str, ips: list[str]) -> None:
        """Set a single answer for hostname. Every lookup returns this list."""
        self._answers[hostname] = ips

    def set_sequence(self, hostname: str, sequence: list[list[str]]) -> None:
        """Set a sequence of answers. Each lookup returns the next list in order;
        once exhausted, the last one is reused."""
        self._answers[hostname] = sequence
        self._sequence_indexes[hostname] = 0
        # Mark sequence by setting the sequence index; resolved by isinstance check
        self._sequence_indexes[hostname + "::is_sequence"] = 1  # type: ignore[assignment]

    def lookup_count(self, hostname: str) -> int:
        return self._call_counts.get(hostname, 0)

    def _resolve(self, hostname: str) -> list[str]:
        self._call_counts[hostname] = self._call_counts.get(hostname, 0) + 1
        ans = self._answers.get(hostname)
        if ans is None:
            raise socket.gaierror(socket.EAI_NONAME, "Name not known (fake_dns)")
        # If it's a sequence (list of lists), pick by index.
        if hostname + "::is_sequence" in self._sequence_indexes:
            idx = min(self._sequence_indexes[hostname], len(ans) - 1)
            self._sequence_indexes[hostname] = idx + 1
            return ans[idx]
        return ans


@pytest.fixture
def fake_dns(monkeypatch) -> Iterator[_FakeDns]:
    """Monkey-patch socket.getaddrinfo. Use .set() / .set_sequence() to script answers."""
    fdns = _FakeDns()

    def _fake_getaddrinfo(host, port, *args, **kwargs):
        ips = fdns._resolve(host)
        # getaddrinfo returns a list of 5-tuples: (family, type, proto, canonname, sockaddr)
        result = []
        for ip in ips:
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            sockaddr = (ip, port or 0) if family == socket.AF_INET else (ip, port or 0, 0, 0)
            result.append((family, socket.SOCK_STREAM, 0, "", sockaddr))
        return result

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    yield fdns


# === Pinned-IP shim for rebinding tests ===

class _PinnedShimRecord:
    """Records the intended dest_ip from each _PinnedHTTPSConnection construction."""

    def __init__(self):
        self.dest_ips: list[str] = []
        self.hostnames: list[str] = []

    def reset(self):
        self.dest_ips.clear()
        self.hostnames.clear()


@pytest.fixture
def pinned_shim_records(monkeypatch) -> Iterator[_PinnedShimRecord]:
    """Records all (dest_ip, hostname) pairs the pinned connector is asked for.

    Useful for proving the rebinding defense: assert that DNS was called once
    AND the connection went to the validated IP, not whatever DNS returned later.

    Test code physically routes the connection to localhost via the shim.
    """
    record = _PinnedShimRecord()

    # Defer imports until fixture body so monkeypatch is available.
    from source_intake import fetch as fetch_mod
    from urllib3.exceptions import NewConnectionError

    original_init = fetch_mod._PinnedHTTPSConnection.__init__

    def _shim_init(self, *args, dest_ip=None, **kwargs):
        record.dest_ips.append(dest_ip)
        record.hostnames.append(args[0] if args else kwargs.get("host"))
        original_init(self, *args, dest_ip=dest_ip, **kwargs)

    def _shim_new_conn(self):
        # Prevent any outbound packets in test environment.
        raise NewConnectionError(self, f"shimmed: would have connected to {self._dest_ip}")

    monkeypatch.setattr(fetch_mod._PinnedHTTPSConnection, "__init__", _shim_init)
    monkeypatch.setattr(fetch_mod._PinnedHTTPSConnection, "_new_conn", _shim_new_conn)
    yield record


# === Local HTTP server fixtures ===

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _ScriptedHandler(BaseHTTPRequestHandler):
    """Handler that uses class-level scripted responses keyed by path."""

    SCRIPT: dict[str, dict] = {}

    def log_message(self, *args, **kwargs):
        pass  # silence test logs

    def do_GET(self):
        spec = self.SCRIPT.get(self.path) or self.SCRIPT.get("__default__")
        if spec is None:
            self.send_response(404)
            self.end_headers()
            return

        status = spec.get("status", 200)
        headers = spec.get("headers", {"Content-Type": "text/html; charset=utf-8"})
        body = spec.get("body", b"<html><body>ok</body></html>")
        delay_seconds_per_kb = spec.get("delay_seconds_per_kb", 0)

        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()

        if delay_seconds_per_kb:
            for i in range(0, len(body), 1024):
                self.wfile.write(body[i : i + 1024])
                self.wfile.flush()
                time.sleep(delay_seconds_per_kb)
        else:
            self.wfile.write(body)


@pytest.fixture
def local_http_server() -> Iterator[tuple[str, type[_ScriptedHandler]]]:
    """Starts a stdlib ThreadingHTTPServer on 127.0.0.1:<random-port>.

    Returns (base_url, handler_class). Caller sets handler_class.SCRIPT to
    define responses per-path. Default key '__default__' is used if path
    not matched.
    """
    handler = type("Handler", (_ScriptedHandler,), {"SCRIPT": {}})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield base_url, handler
    finally:
        server.shutdown()
        server.server_close()


import socket as _socket


@pytest.fixture
def fetch_against_local(fake_dns, local_http_server, monkeypatch):
    """Composite fixture for content-type / redirect / size-cap tests.

    Returns (fetch_callable, handler_class):
      - sets up fake_dns answers for "test.example" → 1.1.1.1 (validator-accepted public IP)
      - patches _PinnedHTTPSConnection / _PinnedHTTPConnection _new_conn to
        actually connect to localhost on the test server's port
      - returns _fetch(path) that calls fetch("http://test.example<path>")

    Does NOT use pinned_shim_records — they conflict on _new_conn. Use this
    fixture for content-type / redirect / size-cap tests; use
    pinned_shim_records (separately) for rebinding tests.
    """
    base_url, handler = local_http_server
    local_port = int(base_url.rsplit(":", 1)[1])

    fake_dns.set("test.example", ["1.1.1.1"])  # validator-accepted public IP

    from source_intake import fetch as fetch_mod

    def _shim_new_conn(self):
        # Build socket directly to avoid socket.create_connection's internal
        # getaddrinfo call (which would hit fake_dns for "127.0.0.1").
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(("127.0.0.1", local_port))
        return sock

    monkeypatch.setattr(fetch_mod._PinnedHTTPConnection, "_new_conn", _shim_new_conn)
    monkeypatch.setattr(fetch_mod._PinnedHTTPSConnection, "_new_conn", _shim_new_conn)

    def _fetch(path: str):
        return fetch_mod.fetch(f"http://test.example{path}")

    return _fetch, handler
