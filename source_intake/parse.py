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


from urllib.parse import urlparse

from .errors import ParseEmpty

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]")
_BLANK_LINES_RE = re.compile(r"\n{3,}")

MAX_TEXT_LENGTH = 500_000
MAX_TITLE_LENGTH = 200


def extract_plain(text: str, source_url: str | None = None, *, min_text_length: int = 200) -> ParsedPage:
    """Pure: raw text → ParsedPage.

    Used by from_text and by Content-Type: text/plain URLs.

    min_text_length is a parameter rather than a hard-coded floor because
    the two intake paths have different policies: from_url enforces 200
    (preserves URL-path behavior); from_text overrides to 1 (preserves
    /api/extract wire contract).
    """
    cleaned = text.replace("\r", "\n")
    cleaned = _CONTROL_CHARS_RE.sub("", cleaned)
    cleaned = _BLANK_LINES_RE.sub("\n\n", cleaned).strip()

    if len(cleaned) < min_text_length:
        raise ParseEmpty(f"raw text {len(cleaned)} chars (min {min_text_length})")

    # Title: first non-empty line if short, else host or default.
    first_line = next((l.strip() for l in cleaned.split("\n") if l.strip()), "")
    if first_line and len(first_line) <= MAX_TITLE_LENGTH:
        title = first_line
    elif source_url and (host := urlparse(source_url).hostname):
        title = host
    else:
        title = "Imported text"

    return ParsedPage(title=title[:MAX_TITLE_LENGTH], text=cleaned[:MAX_TEXT_LENGTH])


from bs4 import BeautifulSoup

MIN_HTML_TEXT_LENGTH = 200


def extract_html(html: str, source_url: str) -> ParsedPage:
    """Pure: HTML string → ParsedPage. Raises ParseEmpty if < 200 chars extracted."""
    soup = BeautifulSoup(html, "html.parser")

    title = _extract_title(soup, source_url)

    # Preserve <pre> block content before stripping (whitespace matters for code).
    # Inline <code> is intentionally NOT special-cased — that produces weird spacing.
    pre_blocks = _extract_pre_placeholders(soup)

    # Drop non-content tags. <head> is removed AFTER title extraction.
    for tag in soup.select("script, style, noscript, svg, iframe, template, head"):
        tag.decompose()

    body = soup.body or soup
    text = body.get_text(separator="\n", strip=True)
    text = _restore_pre_placeholders(text, pre_blocks)
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    text = text.strip()

    if len(text) < MIN_HTML_TEXT_LENGTH:
        raise ParseEmpty(f"extracted {len(text)} chars after parsing")

    return ParsedPage(title=title[:MAX_TITLE_LENGTH], text=text[:MAX_TEXT_LENGTH])


def _extract_title(soup: BeautifulSoup, source_url: str) -> str:
    """Title fallback chain: <title> → og:title → twitter:title → first <h1> → host → default."""
    if soup.title:
        t = soup.title.get_text(strip=True)
        if t:
            return t

    og = soup.find("meta", attrs={"property": "og:title"})
    if og:
        og_content = og.get("content")
        if isinstance(og_content, list):
            og_content = " ".join(og_content)
        if isinstance(og_content, str):
            t = og_content.strip()
            if t:
                return t

    tw = soup.find("meta", attrs={"name": "twitter:title"})
    if tw:
        tw_content = tw.get("content")
        if isinstance(tw_content, list):
            tw_content = " ".join(tw_content)
        if isinstance(tw_content, str):
            t = tw_content.strip()
            if t:
                return t

    h1 = soup.find("h1")
    if h1:
        t = h1.get_text(strip=True)
        if t:
            return t

    if source_url:
        host = urlparse(source_url).hostname
        if host:
            return host

    return "Imported text"


_PRE_PLACEHOLDER = "\x00PRE_BLOCK_{}\x00"


def _extract_pre_placeholders(soup: BeautifulSoup) -> list[str]:
    """Replace each <pre> block with a placeholder. Returns the original contents in order.

    Block-only — inline <code> is left untouched.
    """
    blocks: list[str] = []
    for i, pre in enumerate(soup.find_all("pre")):
        blocks.append(pre.get_text())
        pre.string = _PRE_PLACEHOLDER.format(i)
    return blocks


def _restore_pre_placeholders(text: str, blocks: list[str]) -> str:
    for i, original in enumerate(blocks):
        text = text.replace(_PRE_PLACEHOLDER.format(i), original)
    return text
