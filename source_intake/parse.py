"""Pure-function HTML/text parsing for source_intake.

This module imports nothing from urllib, socket, ipaddress, or any I/O
layer. All functions are pure (input → output, or input → raise ParseEmpty).

Security note: BS4 with stdlib html.parser does not parse XML and is not
vulnerable to billion-laughs / XXE. We deliberately do not depend on lxml
for this reason.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedPage:
    """Pure-function output of html or plain-text parsing.

    Title is always populated (host fallback applied here, not in the facade).
    """
    title: str    # max 200 chars, never empty
    text: str     # max 500_000 chars; raises ParseEmpty if < min_text_length


# Functions implemented in subsequent tasks: decode, extract_html, extract_plain


import re
from typing import Mapping

import charset_normalizer

# Regex for <meta charset="..."> and <meta http-equiv="content-type" content="...; charset=...">
_META_CHARSET_RE = re.compile(
    rb'<meta\s+[^>]*charset\s*=\s*["\']?([a-zA-Z0-9_\-]+)',
    re.IGNORECASE,
)


def decode(raw_bytes: bytes, headers: Mapping[str, str]) -> str:
    """Decode raw bytes to string. Never raises.

    Order: BOM → Content-Type charset → <meta charset> (HTML only) →
    charset-normalizer fallback → utf-8 with errors='replace'.
    """
    # 1. BOM (authoritative)
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return raw_bytes[3:].decode("utf-8", errors="replace")
    if raw_bytes.startswith(b"\x00\x00\xfe\xff") or raw_bytes.startswith(b"\xff\xfe\x00\x00"):
        return raw_bytes.decode("utf-32", errors="replace")
    if raw_bytes.startswith(b"\xfe\xff") or raw_bytes.startswith(b"\xff\xfe"):
        return raw_bytes.decode("utf-16", errors="replace")

    # 2. Content-Type charset
    content_type = headers.get("content-type", "")
    header_charset = _parse_charset(content_type)
    if header_charset:
        try:
            return raw_bytes.decode(header_charset, errors="replace")
        except LookupError:
            pass  # unknown encoding name; continue chain

    # 3. <meta charset> (HTML only)
    if content_type.split(";")[0].strip().lower() == "text/html":
        meta_charset = _peek_meta_charset(raw_bytes[:1024])
        if meta_charset:
            try:
                return raw_bytes.decode(meta_charset, errors="replace")
            except LookupError:
                pass

    # 4. charset-normalizer fallback
    detected = charset_normalizer.from_bytes(raw_bytes).best()
    if detected is not None:
        return str(detected)

    # 5. final fallback
    return raw_bytes.decode("utf-8", errors="replace")


def _parse_charset(content_type: str) -> str | None:
    """Extract `charset=...` token from Content-Type header. Lowercased."""
    if not content_type:
        return None
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("charset="):
            value = part.split("=", 1)[1].strip().strip('"').strip("'")
            return value.lower() if value else None
    return None


def _peek_meta_charset(prefix: bytes) -> str | None:
    """Bounded scan of first ~1024 bytes for a <meta charset> declaration."""
    match = _META_CHARSET_RE.search(prefix)
    if match:
        return match.group(1).decode("ascii", errors="ignore").lower()
    return None
