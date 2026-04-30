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
# _validate_outbound_target(url) -> list[str]
# _PinnedHTTPSConnection / _PinnedHTTPConnection
# _open_pinned, _read_with_cap
