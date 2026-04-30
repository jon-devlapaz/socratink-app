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
