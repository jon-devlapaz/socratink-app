# Imported Source Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract `source_intake/` module from `main.py:285-449`. Unify URL fetch and raw-text submission behind one `ImportedSource` value type. Close DNS-rebinding SSRF gap with pinned-IP connect. Replace regex HTML stripping with a parser-based pipeline.

**Architecture:** Three-way split — `fetch.py` (network I/O, SSRF, redirects, byte cap), `parse.py` (pure: charset chain, BS4 DOM, title fallback, text extraction), and `__init__.py` (facade orchestrating fetch → parse → `ImportedSource`). Routes know only domain exceptions; one mapping function in `main.py` handles HTTPException translation with oracle defense. Pinned-IP connect via `urllib3` custom connection class closes DNS-rebinding TOCTOU.

**Tech Stack:** Python 3.13+, FastAPI, `urllib3==2.6.3`, `beautifulsoup4==4.14.3` (with stdlib `html.parser`), `charset-normalizer==3.4.6`, `pytest`. No `lxml`, no `selectolax`, no native deps.

**Spec:** `docs/superpowers/specs/2026-04-30-imported-source-intake-design.md` (committed `2ecd3b8`).

---

## File structure

**Created:**
- `source_intake/__init__.py` — facade: `ImportedSource`, `from_url`, `from_text`, errors re-export
- `source_intake/errors.py` — `SourceIntakeError` + 6 subclasses
- `source_intake/fetch.py` — `FetchedSource`, `fetch`, `_validate_outbound_target`, `_PinnedHTTPSConnection`, `_open_pinned`, `_read_with_cap`
- `source_intake/parse.py` — `ParsedPage`, `decode`, `extract_html`, `extract_plain`, helpers
- `tests/source_intake/__init__.py`
- `tests/source_intake/conftest.py` — `fake_dns`, `local_redirect_server`, `slow_large_server`, `pinned_shim_records` fixtures
- `tests/source_intake/test_errors.py`
- `tests/source_intake/test_parse_decode.py`
- `tests/source_intake/test_parse_extract_plain.py`
- `tests/source_intake/test_parse_extract_html.py`
- `tests/source_intake/test_fetch_validate.py`
- `tests/source_intake/test_fetch_read_with_cap.py`
- `tests/source_intake/test_fetch_pinned_ip.py`
- `tests/source_intake/test_fetch_redirect.py`
- `tests/source_intake/test_fetch_content_type.py`
- `tests/source_intake/test_fetch_size_cap.py`
- `tests/source_intake/test_facade.py`
- `tests/source_intake/fixtures/` — HTML and byte fixtures
- `tests/test_intake_route_mapping.py`
- `tests/test_extract_url_route.py` (new tests; existing route tests retained)

**Modified:**
- `requirements.txt` — add 3 exact-pin deps
- `UBIQUITOUS_LANGUAGE.md` — add "Content Intake" section
- `main.py:228-585` — `_resolve_node_mechanism`, `extract_url`, `extract`, plus new `_map_intake_error`, `_summarize_url_for_log` helpers
- `main.py:285-345` — DELETE `_extract_text_from_html`, `_is_blocked_video_url`, `_is_private_url` (final task only)

---

## Task 1: Glossary update — add "Imported source" to `UBIQUITOUS_LANGUAGE.md`

**Files:**
- Modify: `UBIQUITOUS_LANGUAGE.md`

- [ ] **Step 1: Add new "Content Intake" section after the "Product Claims" section**

Insert before the "Relationships" section in `UBIQUITOUS_LANGUAGE.md`:

```markdown
## Content Intake

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Imported source** | A normalized text source ready for Gemini extraction. Either fetched from a URL or supplied as raw text by the learner. Carries the canonical (post-redirect) URL when present and a flag indicating remote-attacker-controllability. | "Article", "fetched page", "scraped content" |

```

- [ ] **Step 2: Extend the "Relationships" section with two bullets**

Append to the existing "Relationships" section:

```markdown
- An **Imported source** is the input to the **Draft map** extraction pipeline.
- An **Imported source** that is `is_remote_source=True` is treated as untrusted in extraction prompt assembly (per OWASP LLM01).
```

- [ ] **Step 3: Verify docs consistency**

Run: `bash scripts/doctor.sh`
Expected: passes (no doc drift detected).

- [ ] **Step 4: Commit**

```bash
git add UBIQUITOUS_LANGUAGE.md
git commit -m "$(cat <<'EOF'
docs(source-intake): add "Imported source" to ubiquitous language

Defines the value type that the source_intake module will produce.
Adds prompt-injection trust note (OWASP LLM01) for is_remote_source.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add dependencies to `requirements.txt`

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add three exact pins**

Append to `requirements.txt`:

```
beautifulsoup4==4.14.3
charset-normalizer==3.4.6
urllib3==2.6.3
```

Note: `charset-normalizer` and `urllib3` are already installed transitively; pinning them explicitly makes them direct deps of this module.

- [ ] **Step 2: Verify install works**

Run: `pip install -r requirements.txt`
Expected: all three deps install cleanly. No conflicts.

- [ ] **Step 3: Verify Vercel build surface**

Run: `bash scripts/preflight-deploy.sh`
Expected: passes (validates the same dep/build surface Vercel uses).

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "$(cat <<'EOF'
build(source-intake): pin beautifulsoup4, charset-normalizer, urllib3

Direct dependencies for the new source_intake module:
- beautifulsoup4: HTML parsing with stdlib html.parser (no native dep)
- charset-normalizer: charset detection fallback
- urllib3: pinned-IP connect for DNS rebinding closure

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Scaffolding — create empty module structure

**Files:**
- Create: `source_intake/__init__.py`
- Create: `source_intake/errors.py`
- Create: `source_intake/fetch.py`
- Create: `source_intake/parse.py`
- Create: `tests/source_intake/__init__.py`

- [ ] **Step 1: Create `source_intake/errors.py` with all 6 exception classes**

```python
"""Domain exceptions for source_intake.

These are the only exceptions raised by source_intake module functions.
Routes map them to HTTP responses via main._map_intake_error.
"""


class SourceIntakeError(Exception):
    """Base for all domain exceptions raised by source_intake."""


class InvalidUrl(SourceIntakeError):
    """Malformed URL, missing hostname, or invalid port.

    Note: scheme errors (file://, gopher://, etc.) are NOT InvalidUrl;
    they raise BlockedSource(reason="blocked_scheme").
    """


class BlockedSource(SourceIntakeError):
    """Source refused by policy: SSRF private address, port not in {80,443},
    unsupported scheme, or video denylist match.

    Reason attribute carries the specific category for server-side logging
    and route-layer UX differentiation. The route mapping collapses
    private_address to the same generic 502 response as FetchFailed (oracle
    defense); other reasons surface specific user messages.
    """

    def __init__(self, message: str, *, reason: str):
        super().__init__(message)
        # one of: "private_address" | "blocked_port" | "blocked_video" | "blocked_scheme"
        self.reason = reason


class FetchFailed(SourceIntakeError):
    """Network-layer failure: DNS, connect, timeout, or upstream HTTP error.

    Cause attribute carries the specific failure mode for server-side logging.
    All causes collapse to the same generic 502 response at the route layer
    (oracle defense — attacker cannot distinguish DNS from connect from 5xx).
    """

    def __init__(self, message: str, *, cause: str):
        super().__init__(message)
        # one of: "dns" | "connect" | "timeout" | "http_4xx" | "http_5xx"
        self.cause = cause


class UnsupportedContent(SourceIntakeError):
    """Content-type not in {text/html, text/plain}, or content-encoding != identity."""


class TooLarge(SourceIntakeError):
    """Streamed bytes exceeded MAX_BYTES (2 MB)."""


class ParseEmpty(SourceIntakeError):
    """Extracted text below min_text_length after parsing."""
```

- [ ] **Step 2: Create `source_intake/parse.py` stub**

```python
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
```

- [ ] **Step 3: Create `source_intake/fetch.py` stub**

```python
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
```

- [ ] **Step 4: Create `source_intake/__init__.py` facade stub**

```python
"""source_intake — unified content intake module.

Public surface:
    ImportedSource          — value type (URL or text → normalized text source)
    from_url(url)           — fetch + parse
    from_text(text)         — normalize raw text submission
    errors (re-exported)    — SourceIntakeError + 6 subclasses
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import (
    BlockedSource,
    FetchFailed,
    InvalidUrl,
    ParseEmpty,
    SourceIntakeError,
    TooLarge,
    UnsupportedContent,
)

__all__ = [
    "ImportedSource",
    "from_url",
    "from_text",
    "SourceIntakeError",
    "InvalidUrl",
    "BlockedSource",
    "FetchFailed",
    "UnsupportedContent",
    "TooLarge",
    "ParseEmpty",
]


@dataclass(frozen=True)
class ImportedSource:
    """An imported text source, ready for Gemini extraction.

    Either fetched from a URL (via from_url) or supplied as raw text
    (via from_text). Carries the canonical (post-redirect) URL when present.

    is_remote_source flags content as remote-attacker-controllable for
    downstream prompt-injection awareness in ai_service.py extraction prompt
    assembly. Per OWASP LLM01.
    """
    url: str | None             # final_url after redirects, or None for from_text
    title: str                  # max 200 chars, never empty
    text: str                   # max 500_000 chars
    is_remote_source: bool      # True from from_url, False from from_text

    def to_dict(self) -> dict:
        """JSON shape for the /api/extract-url response.

        Intentionally omits is_remote_source — that flag is internal-only.
        Regression test test_to_dict_omits_is_remote_source enforces this.
        """
        return {"url": self.url, "title": self.title, "text": self.text}


# from_url and from_text implemented in Task 12 (facade).
```

- [ ] **Step 5: Create `tests/source_intake/__init__.py`**

```python
# Test package for source_intake.
```

- [ ] **Step 6: Verify pytest collection still passes**

Run: `pytest --collect-only -q`
Expected: collection succeeds; no errors. New test directory present but empty.

- [ ] **Step 7: Verify imports work**

Run:
```bash
python -c "from source_intake import ImportedSource, SourceIntakeError, InvalidUrl, BlockedSource, FetchFailed, UnsupportedContent, TooLarge, ParseEmpty; print('imports ok')"
```
Expected: `imports ok`

- [ ] **Step 8: Commit**

```bash
git add source_intake/ tests/source_intake/__init__.py
git commit -m "$(cat <<'EOF'
feat(source-intake): scaffold module with public types and exceptions

Stubs for source_intake/ with ImportedSource, FetchedSource, ParsedPage
value types and the six domain exceptions (SourceIntakeError +
InvalidUrl/BlockedSource/FetchFailed/UnsupportedContent/TooLarge/ParseEmpty).
No logic yet; nothing imports the module from production code.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Implement and test domain exceptions

**Files:**
- Create: `tests/source_intake/test_errors.py`

- [ ] **Step 1: Write failing tests for exception construction**

```python
# tests/source_intake/test_errors.py
"""Tests for source_intake domain exceptions."""

import pytest

from source_intake.errors import (
    BlockedSource,
    FetchFailed,
    InvalidUrl,
    ParseEmpty,
    SourceIntakeError,
    TooLarge,
    UnsupportedContent,
)


def test_all_subclass_source_intake_error():
    """Single base class lets routes catch all module exceptions uniformly."""
    for cls in (InvalidUrl, BlockedSource, FetchFailed, UnsupportedContent, TooLarge, ParseEmpty):
        assert issubclass(cls, SourceIntakeError)


def test_blocked_source_carries_reason():
    exc = BlockedSource("private 10.0.0.1", reason="private_address")
    assert exc.reason == "private_address"
    assert "private 10.0.0.1" in str(exc)


@pytest.mark.parametrize("reason", ["private_address", "blocked_port", "blocked_video", "blocked_scheme"])
def test_blocked_source_reasons(reason):
    exc = BlockedSource("test", reason=reason)
    assert exc.reason == reason


def test_blocked_source_requires_keyword_reason():
    with pytest.raises(TypeError):
        BlockedSource("test", "private_address")  # positional should fail


def test_fetch_failed_carries_cause():
    exc = FetchFailed("DNS lookup failed", cause="dns")
    assert exc.cause == "dns"
    assert "DNS lookup failed" in str(exc)


@pytest.mark.parametrize("cause", ["dns", "connect", "timeout", "http_4xx", "http_5xx"])
def test_fetch_failed_causes(cause):
    exc = FetchFailed("test", cause=cause)
    assert exc.cause == cause


def test_fetch_failed_requires_keyword_cause():
    with pytest.raises(TypeError):
        FetchFailed("test", "dns")  # positional should fail


def test_simple_exceptions_take_message_only():
    """InvalidUrl, UnsupportedContent, TooLarge, ParseEmpty have no extra attrs."""
    for cls in (InvalidUrl, UnsupportedContent, TooLarge, ParseEmpty):
        exc = cls("test message")
        assert "test message" in str(exc)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/source_intake/test_errors.py -v`
Expected: all 8 tests pass. (The exception classes were defined in Task 3; these tests just lock the contracts.)

- [ ] **Step 3: Commit**

```bash
git add tests/source_intake/test_errors.py
git commit -m "$(cat <<'EOF'
test(source-intake): lock domain exception contracts

Verifies the six exceptions all subclass SourceIntakeError; that
BlockedSource.reason and FetchFailed.cause are keyword-only attributes;
and that simple exceptions accept message-only construction.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Implement `parse.decode` (charset chain)

**Files:**
- Modify: `source_intake/parse.py`
- Create: `tests/source_intake/test_parse_decode.py`

- [ ] **Step 1: Write failing tests covering the full charset chain**

```python
# tests/source_intake/test_parse_decode.py
"""Tests for parse.decode — charset chain.

Order: BOM → Content-Type charset → <meta charset> → charset-normalizer fallback → utf-8 errors=replace.
"""

import pytest

from source_intake.parse import decode


# === BOM (priority 1) ===

def test_decode_utf8_bom_strips_bom_and_decodes():
    raw = b"\xef\xbb\xbfhello world"
    result = decode(raw, {"content-type": "text/html"})
    assert result == "hello world"


def test_decode_utf16_le_bom():
    raw = b"\xff\xfeh\x00i\x00"
    result = decode(raw, {"content-type": "text/html"})
    assert "hi" in result


def test_decode_bom_overrides_header():
    """BOM is authoritative — wins over a contradicting header."""
    raw = b"\xef\xbb\xbfhi"
    result = decode(raw, {"content-type": "text/html; charset=latin-1"})
    assert result == "hi"


# === Content-Type header (priority 2) ===

def test_decode_uses_header_charset():
    raw = "Café".encode("latin-1")
    result = decode(raw, {"content-type": "text/html; charset=latin-1"})
    assert result == "Café"


def test_decode_header_charset_case_insensitive():
    raw = "Café".encode("utf-8")
    result = decode(raw, {"content-type": "text/html; charset=UTF-8"})
    assert result == "Café"


def test_decode_unknown_header_charset_falls_through():
    """Unknown encoding name in header → continue chain, do not crash."""
    raw = "Café".encode("utf-8")
    result = decode(raw, {"content-type": "text/html; charset=nosuchcharset-9999"})
    # Should fall through to meta or detector and decode correctly
    assert "Café" in result


# === <meta charset> (priority 3) ===

def test_decode_uses_meta_charset_when_no_header():
    raw = b'<html><head><meta charset="latin-1"></head><body>Caf\xe9</body></html>'
    result = decode(raw, {"content-type": "text/html"})
    assert "Café" in result


def test_decode_uses_meta_http_equiv():
    raw = (
        b'<html><head><meta http-equiv="Content-Type" '
        b'content="text/html; charset=latin-1"></head><body>Caf\xe9</body></html>'
    )
    result = decode(raw, {"content-type": "text/html"})
    assert "Café" in result


def test_decode_meta_only_for_html():
    """text/plain skips the meta-charset peek."""
    raw = b'<meta charset="latin-1"> Caf\xe9'
    # Header says text/plain → meta peek is skipped → falls to detector
    result = decode(raw, {"content-type": "text/plain"})
    # Detector should still handle it
    assert "Café" in result or "Caf" in result


# === charset-normalizer fallback (priority 4) ===

def test_decode_falls_back_to_normalizer():
    """No BOM, no header charset, no meta — detector runs."""
    raw = "Café".encode("cp1252")
    result = decode(raw, {"content-type": "text/html"})
    assert "Café" in result


# === Final fallback ===

def test_decode_returns_string_for_undetectable_input():
    """Even on garbage, decode never raises."""
    raw = b"\xff\xfe\xfd\xfc"
    result = decode(raw, {})
    assert isinstance(result, str)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/source_intake/test_parse_decode.py -v`
Expected: all tests FAIL with `ImportError: cannot import name 'decode'`.

- [ ] **Step 3: Implement `decode` and helpers in `source_intake/parse.py`**

Append to `source_intake/parse.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/source_intake/test_parse_decode.py -v`
Expected: all 11 tests pass.

- [ ] **Step 5: Commit**

```bash
git add source_intake/parse.py tests/source_intake/test_parse_decode.py
git commit -m "$(cat <<'EOF'
feat(source-intake): implement parse.decode charset chain

Order: BOM → Content-Type charset → <meta charset> (HTML only) →
charset-normalizer fallback → utf-8 with errors='replace'. Never raises.

Tests cover priority ordering (BOM beats header), unknown encoding names
falling through, text/plain skipping meta peek, and final fallback safety.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Implement `parse.extract_plain`

**Files:**
- Modify: `source_intake/parse.py`
- Create: `tests/source_intake/test_parse_extract_plain.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/source_intake/test_parse_extract_plain.py
"""Tests for parse.extract_plain — pure raw-text normalization."""

import pytest

from source_intake.errors import ParseEmpty
from source_intake.parse import ParsedPage, extract_plain


# === Length thresholds ===

def test_extract_plain_default_min_length_200_raises_on_short():
    with pytest.raises(ParseEmpty):
        extract_plain("x" * 50)


def test_extract_plain_default_min_length_200_passes_long():
    page = extract_plain("hello world. " * 30)  # > 200 chars
    assert isinstance(page, ParsedPage)


def test_extract_plain_min_text_length_parameter_overrides_default():
    """from_text uses min_text_length=1; this is the test that enforces that policy."""
    page = extract_plain("short content", min_text_length=1)
    assert page.text == "short content"


def test_extract_plain_min_text_length_zero_still_rejects_empty_after_strip():
    with pytest.raises(ParseEmpty):
        extract_plain("   \n  \n  ", min_text_length=1)  # only whitespace


# === Title heuristic ===

def test_extract_plain_first_line_becomes_title_when_short():
    text = "My Document Title\n\n" + "body content. " * 30
    page = extract_plain(text)
    assert page.title == "My Document Title"


def test_extract_plain_long_first_line_falls_to_default():
    text = ("very long single line " * 20) + "\n" + "body. " * 50
    page = extract_plain(text)
    assert page.title == "Imported text"


def test_extract_plain_falls_back_to_host_when_long_first_line_with_url():
    text = ("very long single line " * 20) + "\n" + "body. " * 50
    page = extract_plain(text, source_url="https://example.com/article")
    assert page.title == "example.com"


def test_extract_plain_default_title_when_no_url_no_short_first_line():
    text = ("long line " * 30) + "\n" + "body. " * 50
    page = extract_plain(text)
    assert page.title == "Imported text"


# === Whitespace normalization ===

def test_extract_plain_collapses_excessive_blank_lines():
    text = "first\n\n\n\n\nsecond" + "\n" + "x" * 250
    page = extract_plain(text)
    assert "\n\n\n" not in page.text


def test_extract_plain_normalizes_carriage_returns():
    text = "first\r\nsecond" + "\n" + "x" * 250
    page = extract_plain(text)
    assert "\r" not in page.text


# === Control character stripping ===

def test_extract_plain_strips_nul_and_other_control_chars():
    text = "valid\x00\x01\x02 content " + "x" * 250
    page = extract_plain(text)
    assert "\x00" not in page.text
    assert "\x01" not in page.text
    assert "\x02" not in page.text
    # Tab/newline/CR should be preserved (CR converted to \n)
    assert "valid content" in page.text


def test_extract_plain_preserves_tab_and_newline():
    text = "first\ttabbed\nsecond" + "\n" + "x" * 250
    page = extract_plain(text)
    assert "\t" in page.text
    assert "\n" in page.text


# === Length caps ===

def test_extract_plain_truncates_text_at_500k():
    text = "x" * 600_000
    page = extract_plain(text)
    assert len(page.text) <= 500_000


def test_extract_plain_truncates_title_at_200():
    text = ("a" * 250) + "\n" + "x" * 300
    page = extract_plain(text)
    assert len(page.title) <= 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/source_intake/test_parse_extract_plain.py -v`
Expected: all FAIL with `ImportError: cannot import name 'extract_plain'`.

- [ ] **Step 3: Implement `extract_plain` in `source_intake/parse.py`**

Append to `source_intake/parse.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/source_intake/test_parse_extract_plain.py -v`
Expected: all 14 tests pass.

- [ ] **Step 5: Commit**

```bash
git add source_intake/parse.py tests/source_intake/test_parse_extract_plain.py
git commit -m "$(cat <<'EOF'
feat(source-intake): implement parse.extract_plain

Pure raw-text normalization: strip control chars (preserve tab/newline/CR),
collapse blank line runs, derive title from first short line / source host /
default, enforce configurable min_text_length, cap title and text lengths.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Implement `parse.extract_html` with title fallback chain and `<pre>` preservation

**Files:**
- Modify: `source_intake/parse.py`
- Create: `tests/source_intake/test_parse_extract_html.py`
- Create: `tests/source_intake/fixtures/og_title_only.html`
- Create: `tests/source_intake/fixtures/twitter_title_only.html`
- Create: `tests/source_intake/fixtures/h1_only.html`
- Create: `tests/source_intake/fixtures/pre_block.html`

- [ ] **Step 1: Create HTML fixtures**

`tests/source_intake/fixtures/og_title_only.html`:
```html
<!DOCTYPE html>
<html>
<head>
  <meta property="og:title" content="OG Title Wins">
</head>
<body>
  <p>This page has no &lt;title&gt; tag, only Open Graph metadata.</p>
  <p>This is filler content to clear the 200-char minimum so that ParseEmpty
  does not fire during testing. Lorem ipsum dolor sit amet, consectetur
  adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore.</p>
</body>
</html>
```

`tests/source_intake/fixtures/twitter_title_only.html`:
```html
<!DOCTYPE html>
<html>
<head>
  <meta name="twitter:title" content="Twitter Title Wins">
</head>
<body>
  <p>No title tag, no og:title. Only twitter:title. The title fallback chain
  should pick this one. Filler content follows to clear the 200-char minimum
  for the ParseEmpty threshold so we can isolate the title-extraction logic.</p>
</body>
</html>
```

`tests/source_intake/fixtures/h1_only.html`:
```html
<!DOCTYPE html>
<html>
<body>
  <h1>H1 Title Wins</h1>
  <p>No title tag, no og:title, no twitter:title. Only an h1. The title
  fallback chain should pick this one. Filler content follows to clear the
  200-char minimum for ParseEmpty so we can test title extraction.</p>
</body>
</html>
```

`tests/source_intake/fixtures/pre_block.html`:
```html
<!DOCTYPE html>
<html>
<head><title>Code Block Page</title></head>
<body>
  <p>Here is a Python snippet:</p>
  <pre>def factorial(n):
    if n &lt;= 1:
        return 1
    return n * factorial(n - 1)</pre>
  <p>The indentation in the code block above must be preserved verbatim
  through extraction. Filler content to clear the 200-char minimum so that
  ParseEmpty does not fire on this page during the round-trip test.</p>
</body>
</html>
```

- [ ] **Step 2: Write failing tests**

```python
# tests/source_intake/test_parse_extract_html.py
"""Tests for parse.extract_html — DOM-based HTML parsing."""

from pathlib import Path

import pytest

from source_intake.errors import ParseEmpty
from source_intake.parse import ParsedPage, extract_html

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


# === Title fallback chain ===

def test_title_uses_title_tag_first():
    html = (
        "<html><head><title>Real Title</title>"
        '<meta property="og:title" content="OG"></head>'
        "<body><h1>H1 Title</h1>" + ("<p>filler text </p>" * 30) + "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert page.title == "Real Title"


def test_title_falls_back_to_og_title():
    page = extract_html(_read("og_title_only.html"), "https://example.com")
    assert page.title == "OG Title Wins"


def test_title_falls_back_to_twitter_title():
    page = extract_html(_read("twitter_title_only.html"), "https://example.com")
    assert page.title == "Twitter Title Wins"


def test_title_falls_back_to_h1():
    page = extract_html(_read("h1_only.html"), "https://example.com")
    assert page.title == "H1 Title Wins"


def test_title_falls_back_to_host():
    html = "<html><body>" + "<p>filler </p>" * 30 + "</body></html>"
    page = extract_html(html, "https://example.com/article")
    assert page.title == "example.com"


def test_title_falls_back_to_default_when_no_host():
    html = "<html><body>" + "<p>filler </p>" * 30 + "</body></html>"
    page = extract_html(html, "")
    assert page.title == "Imported text"


def test_title_handles_entity_references():
    html = (
        "<html><head><title>Foo &amp; Bar</title></head>"
        "<body>" + "<p>filler </p>" * 30 + "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert page.title == "Foo & Bar"


def test_title_skips_empty_title_tag():
    """Empty <title></title> should fall through to og:title."""
    html = (
        '<html><head><title></title><meta property="og:title" content="OG Wins"></head>'
        "<body>" + "<p>filler </p>" * 30 + "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert page.title == "OG Wins"


def test_title_truncated_to_200_chars():
    long_title = "x" * 300
    html = (
        f"<html><head><title>{long_title}</title></head>"
        "<body>" + "<p>filler </p>" * 30 + "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert len(page.title) == 200


# === Text extraction ===

def test_text_extraction_strips_script_tags():
    html = (
        "<html><body>"
        "<script>alert('hi')</script>"
        "<p>visible text</p>"
        + ("<p>filler </p>" * 30) +
        "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert "alert" not in page.text
    assert "visible text" in page.text


def test_text_extraction_strips_style_tags():
    html = (
        "<html><body>"
        "<style>.foo { color: red; }</style>"
        "<p>visible</p>"
        + ("<p>filler </p>" * 30) +
        "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert "color: red" not in page.text
    assert "visible" in page.text


def test_text_preserves_pre_block_indentation():
    page = extract_html(_read("pre_block.html"), "https://example.com")
    assert "    if n" in page.text   # 4-space indentation preserved
    assert "        return 1" in page.text   # 8-space indentation preserved


def test_text_strips_control_characters():
    html = (
        "<html><body>"
        "<p>visible\x00\x01 text</p>"
        + ("<p>filler </p>" * 30) +
        "</body></html>"
    )
    page = extract_html(html, "https://example.com")
    assert "\x00" not in page.text
    assert "\x01" not in page.text


def test_text_collapses_excessive_blank_lines():
    """Three+ consecutive newlines collapse to two."""
    html = "<html><body>" + ("<p>filler </p><br><br><br><br>" * 30) + "</body></html>"
    page = extract_html(html, "https://example.com")
    assert "\n\n\n" not in page.text


# === ParseEmpty ===

def test_extract_html_raises_parse_empty_on_thin_content():
    html = "<html><body><p>too short</p></body></html>"
    with pytest.raises(ParseEmpty):
        extract_html(html, "https://example.com")


def test_extract_html_raises_parse_empty_on_only_scripts():
    """Page with only <script> content extracts to empty body text."""
    html = "<html><body><script>" + ("var x = 1; " * 100) + "</script></body></html>"
    with pytest.raises(ParseEmpty):
        extract_html(html, "https://example.com")


# === Length caps ===

def test_text_truncated_at_500k():
    long_body = "<p>" + ("x" * 100) + "</p>"
    html = "<html><body>" + (long_body * 7000) + "</body></html>"
    page = extract_html(html, "https://example.com")
    assert len(page.text) <= 500_000
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/source_intake/test_parse_extract_html.py -v`
Expected: all FAIL with `ImportError: cannot import name 'extract_html'`.

- [ ] **Step 4: Implement `extract_html` and helpers in `source_intake/parse.py`**

Append to `source_intake/parse.py`:

```python
from bs4 import BeautifulSoup, Tag

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
    if og and og.get("content"):
        t = og["content"].strip()
        if t:
            return t

    tw = soup.find("meta", attrs={"name": "twitter:title"})
    if tw and tw.get("content"):
        t = tw["content"].strip()
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/source_intake/test_parse_extract_html.py -v`
Expected: all 17 tests pass.

Note: the test_text_strips_control_characters test inserts `\x00` into source HTML; html.parser may or may not preserve those bytes. If the test fails because BS4 strips them itself, simplify to use `\x01` and `\x02` only (which BS4 leaves alone). Adjust fixture inline if needed.

- [ ] **Step 6: Run full pytest to confirm no regression**

Run: `pytest tests/source_intake/ -v`
Expected: all parse tests green; no other suites break.

- [ ] **Step 7: Commit**

```bash
git add source_intake/parse.py tests/source_intake/test_parse_extract_html.py tests/source_intake/fixtures/
git commit -m "$(cat <<'EOF'
feat(source-intake): implement parse.extract_html

BS4 with stdlib html.parser. Title fallback chain: <title> → og:title →
twitter:title → first <h1> → URL host → "Imported text". Strips script/
style/noscript/svg/iframe/template/head before text extraction. Preserves
<pre> block whitespace via placeholder swap (block-only, not inline <code>).
Strips control chars; collapses 3+ newline runs. Caps at 200/500_000 chars.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Test fixtures — `fake_dns` for SSRF validation tests

**Files:**
- Create: `tests/source_intake/conftest.py`

- [ ] **Step 1: Implement `fake_dns` fixture**

```python
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
```

- [ ] **Step 2: Verify the fixture itself works (smoke test in a parametrize)**

Add to bottom of `conftest.py`:

```python
def _smoke_fake_dns(fdns):
    fdns.set("example.com", ["93.184.216.34"])
    info = socket.getaddrinfo("example.com", 80)
    assert info[0][4][0] == "93.184.216.34"
```

(This isn't a test — just a guard against an obvious typo. Test infra is exercised by Task 9 onwards.)

- [ ] **Step 3: Commit**

```bash
git add tests/source_intake/conftest.py
git commit -m "$(cat <<'EOF'
test(source-intake): add fake_dns fixture for SSRF tests

Monkey-patches socket.getaddrinfo with controlled answers. Supports
single-answer (.set) and sequential answers (.set_sequence) for
DNS-rebinding tests. Tracks lookup counts to verify pinned-IP semantics.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Implement `fetch._validate_outbound_target` (validation order + SSRF)

**Files:**
- Modify: `source_intake/fetch.py`
- Create: `tests/source_intake/test_fetch_validate.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/source_intake/test_fetch_validate.py -v`
Expected: all FAIL with `ImportError: cannot import name '_validate_outbound_target'`.

- [ ] **Step 3: Implement `_validate_outbound_target` and constants in `source_intake/fetch.py`**

Append to `source_intake/fetch.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/source_intake/test_fetch_validate.py -v`
Expected: all 27 tests pass.

- [ ] **Step 5: Commit**

```bash
git add source_intake/fetch.py tests/source_intake/test_fetch_validate.py
git commit -m "$(cat <<'EOF'
feat(source-intake): implement fetch._validate_outbound_target

Pre-fetch SSRF + policy validation. Order: scheme → hostname → port →
DNS resolve → private-IP rejection → effective-port allowlist → video
denylist. Returns validated global IP list for pinned-connect.

Oracle-defense ordering: DNS+private check before port check, so
http://10.0.0.1:25 and :80 both surface as private_address (attacker
cannot probe internal port topology by varying scheme/port).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Implement `fetch._read_with_cap` (streaming size cap)

**Files:**
- Modify: `source_intake/fetch.py`
- Create: `tests/source_intake/test_fetch_read_with_cap.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/source_intake/test_fetch_read_with_cap.py
"""Tests for fetch._read_with_cap — streaming abort at byte cap."""

import pytest

from source_intake.errors import TooLarge
from source_intake.fetch import _read_with_cap


class _FakeStreamingResponse:
    """Mimics the urllib3 response.stream() interface for tests."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    def stream(self, amt: int = 16384, decode_content: bool = False):
        for chunk in self._chunks:
            yield chunk


def test_read_with_cap_returns_full_body_below_cap():
    response = _FakeStreamingResponse([b"hello", b" ", b"world"])
    raw = _read_with_cap(response, max_bytes=100)
    assert raw == b"hello world"


def test_read_with_cap_raises_too_large_when_exceeded():
    big_chunk = b"x" * 10
    response = _FakeStreamingResponse([big_chunk] * 100)  # 1000 bytes total
    with pytest.raises(TooLarge):
        _read_with_cap(response, max_bytes=50)


def test_read_with_cap_aborts_on_first_chunk_over_cap():
    """A single oversized chunk triggers TooLarge immediately."""
    response = _FakeStreamingResponse([b"x" * 10_000])
    with pytest.raises(TooLarge):
        _read_with_cap(response, max_bytes=100)


def test_read_with_cap_handles_empty_response():
    response = _FakeStreamingResponse([])
    raw = _read_with_cap(response, max_bytes=100)
    assert raw == b""


def test_read_with_cap_exact_boundary():
    """Reading exactly max_bytes is allowed; one byte over is rejected."""
    response = _FakeStreamingResponse([b"x" * 100])
    raw = _read_with_cap(response, max_bytes=100)
    assert len(raw) == 100

    response_over = _FakeStreamingResponse([b"x" * 101])
    with pytest.raises(TooLarge):
        _read_with_cap(response_over, max_bytes=100)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/source_intake/test_fetch_read_with_cap.py -v`
Expected: all FAIL with `ImportError: cannot import name '_read_with_cap'`.

- [ ] **Step 3: Implement `_read_with_cap` in `source_intake/fetch.py`**

Append to `source_intake/fetch.py`:

```python
from .errors import TooLarge


def _read_with_cap(response, max_bytes: int) -> bytes:
    """Stream-read up to max_bytes; raise TooLarge if exceeded.

    Uses response.stream() in chunks; aborts as soon as cumulative size
    exceeds cap. Does not trust Content-Length. Does not auto-decompress
    (decode_content=False, paired with Accept-Encoding: identity at request).
    """
    chunks: list[bytes] = []
    total = 0
    for chunk in response.stream(amt=16384, decode_content=False):
        total += len(chunk)
        if total > max_bytes:
            raise TooLarge(f"exceeded {max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/source_intake/test_fetch_read_with_cap.py -v`
Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add source_intake/fetch.py tests/source_intake/test_fetch_read_with_cap.py
git commit -m "$(cat <<'EOF'
feat(source-intake): implement fetch._read_with_cap

Stream-read with byte cap. Uses response.stream() chunks and aborts on
first cumulative-size overrun. Does not trust Content-Length; does not
auto-decompress.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Implement `_PinnedHTTPSConnection` and `_open_pinned`

**Files:**
- Modify: `source_intake/fetch.py`
- Create: `tests/source_intake/test_fetch_pinned_ip.py`

- [ ] **Step 1: Add pinned-shim hook to `tests/source_intake/conftest.py`**

Append to `tests/source_intake/conftest.py`:

```python
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

    original_init = fetch_mod._PinnedHTTPSConnection.__init__

    def _shim_init(self, *args, dest_ip=None, **kwargs):
        record.dest_ips.append(dest_ip)
        record.hostnames.append(args[0] if args else kwargs.get("host"))
        original_init(self, *args, dest_ip=dest_ip, **kwargs)

    monkeypatch.setattr(fetch_mod._PinnedHTTPSConnection, "__init__", _shim_init)
    yield record
```

- [ ] **Step 2: Write failing tests**

```python
# tests/source_intake/test_fetch_pinned_ip.py
"""Tests for pinned-IP connect (DNS rebinding closure).

Strategy: fake_dns returns RFC 5737 test IPs (203.0.113.x / 198.51.100.x —
accepted as global by validator). The pinned-shim records the intended
dest_ip; the actual connection is intercepted to never leave localhost.
"""

import pytest

from source_intake.errors import FetchFailed
from source_intake.fetch import fetch


def test_pinned_connection_records_validated_ip(fake_dns, pinned_shim_records):
    """When DNS returns a global IP, the pinned connection is constructed with
    that IP (not whatever DNS would return on a re-resolve)."""
    fake_dns.set("example.com", ["203.0.113.5"])
    pinned_shim_records.reset()

    # Connection will fail (we're not running a server), but we just want to
    # observe that the construction happened with the right pinned IP.
    with pytest.raises(FetchFailed):
        fetch("https://example.com/article")

    assert "203.0.113.5" in pinned_shim_records.dest_ips


def test_dns_rebinding_does_not_re_resolve(fake_dns, pinned_shim_records):
    """First DNS lookup returns global IP (passes validation).
    Second lookup (if it happened) would return 127.0.0.1.
    Pinned connect must ignore the second answer."""
    fake_dns.set_sequence("example.com", [["203.0.113.5"], ["127.0.0.1"]])
    pinned_shim_records.reset()

    with pytest.raises(FetchFailed):
        fetch("https://example.com/article")

    # Validator did exactly ONE getaddrinfo call (count is 1).
    assert fake_dns.lookup_count("example.com") == 1
    # Connection dest was the validated IP, not the rebound one.
    assert pinned_shim_records.dest_ips == ["203.0.113.5"]
    assert "127.0.0.1" not in pinned_shim_records.dest_ips
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/source_intake/test_fetch_pinned_ip.py -v`
Expected: FAIL with `AttributeError: module 'source_intake.fetch' has no attribute '_PinnedHTTPSConnection'` or similar.

- [ ] **Step 4: Implement `_PinnedHTTPSConnection`, `_PinnedHTTPConnection`, and `_open_pinned`**

Append to `source_intake/fetch.py`:

```python
import socket as _socket
from urllib.parse import urlparse, urlunparse, urljoin

import urllib3
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import (
    ConnectTimeoutError,
    NewConnectionError,
    ProtocolError,
    ReadTimeoutError,
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
```

- [ ] **Step 5: Stub `fetch()` minimally so the pinned tests can exercise it**

Append to `source_intake/fetch.py` (this is a temporary stub; full implementation in Task 13):

```python
def fetch(url: str) -> FetchedSource:
    """Stub — full implementation in Task 13. For now, exercises the
    validate→open_pinned path so pinned-IP tests can run."""
    validated_ips = _validate_outbound_target(url)
    response = _open_pinned(url, validated_ips)   # raises FetchFailed on connect failure
    response.release_conn()
    raise NotImplementedError("fetch() full lifecycle in Task 13")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/source_intake/test_fetch_pinned_ip.py -v`
Expected: 2 tests pass. The pinned shim records the dest_ip; DNS is called once.

Note: connections to `203.0.113.5` will fail with `NewConnectionError` (no route), which becomes `FetchFailed(cause="connect")` — this is the tests' expected behavior. Tests verify that the shim recorded the right IP regardless of actual connection failure.

- [ ] **Step 7: Commit**

```bash
git add source_intake/fetch.py tests/source_intake/conftest.py tests/source_intake/test_fetch_pinned_ip.py
git commit -m "$(cat <<'EOF'
feat(source-intake): implement pinned-IP connect (DNS rebinding closure)

_PinnedHTTPSConnection / _PinnedHTTPConnection subclass urllib3's connection
classes to override _new_conn — connect to the pre-validated IP while keeping
self.host (Host header, SNI, cert verification) as the original hostname.

Tests: pinned-shim records intended dest_ip; verifies DNS resolved exactly
once (no rebinding); verifies fetch() routes to validated IP, not whatever
DNS would return on re-resolve.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Local HTTP server fixtures + content-type / redirect / size-cap tests

**Files:**
- Modify: `tests/source_intake/conftest.py`
- Create: `tests/source_intake/test_fetch_content_type.py`
- Create: `tests/source_intake/test_fetch_redirect.py`
- Create: `tests/source_intake/test_fetch_size_cap.py`
- Modify: `source_intake/fetch.py` (full `fetch()` lifecycle)

- [ ] **Step 1: Add `local_http_server` and `local_redirect_server` fixtures to conftest.py**

Append to `tests/source_intake/conftest.py`:

```python
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
            # Stream slowly — used by size-cap test
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
```

- [ ] **Step 2: Implement the full `fetch()` lifecycle**

Replace the stub `fetch()` in `source_intake/fetch.py` with:

```python
import logging

from .errors import FetchFailed, UnsupportedContent

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

            # Reject server-side compression (Accept-Encoding: identity should prevent it,
            # but some servers ignore that — we never auto-decompress).
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
```

- [ ] **Step 3: Write content-type tests**

```python
# tests/source_intake/test_fetch_content_type.py
"""Tests for fetch content-type policing and HTTP error mapping."""

import pytest

from source_intake.errors import FetchFailed, UnsupportedContent
from source_intake.fetch import fetch


def test_404_raises_fetch_failed_http_4xx(local_http_server, fake_dns, pinned_shim_records):
    base_url, handler = local_http_server
    handler.SCRIPT["/missing"] = {"status": 404, "headers": {"Content-Type": "text/html"}, "body": b"not found"}
    fake_dns.set("test-server.example", ["127.0.0.1"])  # will fail validation; but base_url is 127.0.0.1
    # Better strategy: hit the local server through its 127.0.0.1 URL directly is impossible
    # because that IP is blocked. We use fake_dns to point a fake-public hostname at the
    # validated IP space, and the pinned shim physically routes to localhost.
    # See pinned-IP tests for the pattern. For content-type tests, a simpler approach:
    # patch _open_pinned to call urlopen directly on base_url.
    pytest.skip("content-type tests rewritten against shim infrastructure — see Task 12 step 4")
```

This skip is intentional — the local-server tests need a slightly different shim shape. Continue to step 4.

- [ ] **Step 4: Refactor pinned-shim fixture for full local-server testing**

Update `tests/source_intake/conftest.py` to add a richer fixture combining fake_dns + pinned shim + local server. Append:

```python
@pytest.fixture
def fetch_against_local(fake_dns, pinned_shim_records, local_http_server, monkeypatch):
    """Composite fixture for content-type / redirect / size-cap tests.

    Returns a function `_fetch(path: str)` that:
      - sets up fake_dns answer for "test.example" → 203.0.113.5 (validated)
      - patches _PinnedHTTPSConnection / _PinnedHTTPConnection to actually connect to localhost
      - calls fetch("http://test.example<path>")
    """
    base_url, handler = local_http_server
    # Extract the local server port for the redirection
    local_port = int(base_url.rsplit(":", 1)[1])

    fake_dns.set("test.example", ["203.0.113.5"])  # validator-accepted public test IP

    # Patch _new_conn on both pinned classes to connect to localhost on the test port,
    # ignoring self._dest_ip / self.port for the actual socket.
    from source_intake import fetch as fetch_mod

    def _shim_new_conn(self):
        return _socket.create_connection(("127.0.0.1", local_port), timeout=10)

    monkeypatch.setattr(fetch_mod._PinnedHTTPConnection, "_new_conn", _shim_new_conn)
    monkeypatch.setattr(fetch_mod._PinnedHTTPSConnection, "_new_conn", _shim_new_conn)

    # The pool builds the URL with parsed.hostname:parsed.port. Since we want HTTP to the
    # local server but the request URL says https://, we override the scheme handling by
    # using http://test.example/<path> as the fetch URL.

    def _fetch(path: str):
        return fetch_mod.fetch(f"http://test.example{path}")

    return _fetch, handler


# Need the import for _socket
import socket as _socket
```

- [ ] **Step 5: Rewrite content-type tests using `fetch_against_local`**

Replace `tests/source_intake/test_fetch_content_type.py`:

```python
# tests/source_intake/test_fetch_content_type.py
"""Tests for fetch content-type policing and HTTP error mapping."""

import pytest

from source_intake.errors import FetchFailed, UnsupportedContent


def test_404_raises_fetch_failed_http_4xx(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {"status": 404, "body": b"not found"}
    with pytest.raises(FetchFailed) as exc_info:
        _fetch("/missing")
    assert exc_info.value.cause == "http_4xx"


def test_503_raises_fetch_failed_http_5xx(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {"status": 503, "body": b"unavailable"}
    with pytest.raises(FetchFailed) as exc_info:
        _fetch("/")
    assert exc_info.value.cause == "http_5xx"


def test_unsupported_content_type_raises(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "application/pdf"},
        "body": b"%PDF-1.4 ...",
    }
    with pytest.raises(UnsupportedContent):
        _fetch("/")


def test_missing_content_type_header_raises(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {},  # no Content-Type at all
        "body": b"hi",
    }
    with pytest.raises(UnsupportedContent):
        _fetch("/")


def test_encoded_content_rejected(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {
            "Content-Type": "text/html",
            "Content-Encoding": "gzip",
        },
        "body": b"\x1f\x8b... fake gzip",
    }
    with pytest.raises(UnsupportedContent):
        _fetch("/")


def test_text_html_accepted(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": b"<html><body>" + b"<p>filler</p>" * 30 + b"</body></html>",
    }
    result = _fetch("/")
    assert result.content_type == "text/html"
    assert b"filler" in result.raw_bytes


def test_text_plain_accepted(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/plain"},
        "body": b"plain text content",
    }
    result = _fetch("/")
    assert result.content_type == "text/plain"
    assert result.raw_bytes == b"plain text content"


def test_final_url_carries_through_to_fetched_source(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": b"<html><body>" + b"<p>filler</p>" * 30 + b"</body></html>",
    }
    result = _fetch("/page")
    assert result.final_url == "http://test.example/page"


def test_headers_normalized_to_lowercase(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {
            "Content-Type": "text/html",
            "X-Custom-Header": "value",
        },
        "body": b"<html><body>" + b"<p>filler</p>" * 30 + b"</body></html>",
    }
    result = _fetch("/")
    assert "content-type" in result.headers
    assert "x-custom-header" in result.headers
    assert "Content-Type" not in result.headers  # uppercase keys absent
```

- [ ] **Step 6: Run content-type tests**

Run: `pytest tests/source_intake/test_fetch_content_type.py -v`
Expected: all 9 tests pass.

- [ ] **Step 7: Write redirect tests**

```python
# tests/source_intake/test_fetch_redirect.py
"""Tests for redirect re-validation."""

import pytest

from source_intake.errors import BlockedSource, FetchFailed


def test_simple_redirect_followed(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["/start"] = {"status": 302, "headers": {"Location": "/dest"}, "body": b""}
    handler.SCRIPT["/dest"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": b"<html><body>" + b"<p>filler</p>" * 30 + b"</body></html>",
    }
    result = _fetch("/start")
    assert result.final_url.endswith("/dest")
    assert b"filler" in result.raw_bytes


def test_redirect_to_private_ip_blocked(fetch_against_local, fake_dns):
    """302 to a hostname that resolves to private IP must be rejected."""
    fake_dns.set("internal.example", ["10.0.0.1"])  # private — must reject
    _fetch, handler = fetch_against_local
    handler.SCRIPT["/start"] = {
        "status": 302,
        "headers": {"Location": "http://internal.example/admin"},
        "body": b"",
    }
    with pytest.raises(BlockedSource) as exc_info:
        _fetch("/start")
    assert exc_info.value.reason == "private_address"


def test_redirect_to_blocked_scheme(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["/start"] = {
        "status": 302,
        "headers": {"Location": "file:///etc/passwd"},
        "body": b"",
    }
    with pytest.raises(BlockedSource) as exc_info:
        _fetch("/start")
    assert exc_info.value.reason == "blocked_scheme"


def test_max_redirects_enforced(fetch_against_local):
    _fetch, handler = fetch_against_local
    # Each /loop redirects to /loop again — would loop forever without cap.
    handler.SCRIPT["/loop"] = {"status": 302, "headers": {"Location": "/loop"}, "body": b""}
    with pytest.raises(FetchFailed) as exc_info:
        _fetch("/loop")
    assert exc_info.value.cause == "connect"
    assert "too many redirects" in str(exc_info.value).lower()


def test_3xx_without_location_raises(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["/bad"] = {"status": 302, "headers": {}, "body": b""}  # no Location header
    with pytest.raises(FetchFailed):
        _fetch("/bad")
```

- [ ] **Step 8: Run redirect tests**

Run: `pytest tests/source_intake/test_fetch_redirect.py -v`
Expected: all 5 tests pass.

- [ ] **Step 9: Write size-cap tests**

```python
# tests/source_intake/test_fetch_size_cap.py
"""Tests for streaming size cap (proves preload_content=False is in effect)."""

import time

import pytest

from source_intake.errors import TooLarge


def test_oversized_response_raises_too_large(fetch_against_local):
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": b"<html><body>" + (b"x" * 3_000_000) + b"</body></html>",  # > 2MB
    }
    with pytest.raises(TooLarge):
        _fetch("/")


def test_size_cap_aborts_before_full_read(fetch_against_local):
    """Slow streaming server: 10MB at ~100KB/s.
    Cap is 2MB, so abort must happen well before the full transfer time.
    Without preload_content=False, urllib3 would buffer the entire response
    before our cap check fires — this test catches that regression."""
    _fetch, handler = fetch_against_local
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": b"x" * 10_000_000,
        "delay_seconds_per_kb": 0.01,  # ~100KB/s
    }
    start = time.monotonic()
    with pytest.raises(TooLarge):
        _fetch("/")
    elapsed = time.monotonic() - start
    # Full transfer would take ~100s. We must abort within ~30s.
    assert elapsed < 30, f"size cap took too long ({elapsed:.1f}s) — likely buffered"


def test_at_cap_boundary_accepted(fetch_against_local):
    """A response exactly at 2MB is accepted."""
    _fetch, handler = fetch_against_local
    body = b"<html><body>" + (b"x" * (2_000_000 - 30)) + b"</body></html>"  # ~2MB total
    handler.SCRIPT["__default__"] = {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": body,
    }
    result = _fetch("/")
    assert len(result.raw_bytes) <= 2_000_000
```

- [ ] **Step 10: Run size-cap tests**

Run: `pytest tests/source_intake/test_fetch_size_cap.py -v`
Expected: all 3 tests pass within ~30s total.

- [ ] **Step 11: Run full source_intake suite to confirm no regression**

Run: `pytest tests/source_intake/ -v`
Expected: all tests green.

- [ ] **Step 12: Commit**

```bash
git add source_intake/fetch.py tests/source_intake/conftest.py tests/source_intake/test_fetch_content_type.py tests/source_intake/test_fetch_redirect.py tests/source_intake/test_fetch_size_cap.py
git commit -m "$(cat <<'EOF'
feat(source-intake): full fetch lifecycle with content-type, redirect, size cap

Replaces fetch() stub with full lifecycle:
- pinned-IP connect (validate → resolve once → connect to validated IP)
- redirect re-validation (every Location target re-runs full validation)
- 4xx/5xx → FetchFailed before content-type policing
- content-encoding != identity → UnsupportedContent (no decompression bombs)
- streaming byte cap with preload_content=False
- response.release_conn() on every early-exit branch (no socket leaks)
- header normalization to lowercase keys
- final_url carries through after redirects

Tests cover content-type policing (9), redirect re-validation including
SSRF block on redirect targets (5), and size-cap streaming abort (3).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Implement `from_url` and `from_text` facade

**Files:**
- Modify: `source_intake/__init__.py`
- Create: `tests/source_intake/test_facade.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/source_intake/test_facade.py
"""Tests for source_intake facade — from_url, from_text, ImportedSource."""

import pytest
from unittest.mock import patch

from source_intake import (
    ImportedSource,
    from_text,
    from_url,
)
from source_intake.errors import ParseEmpty
from source_intake.fetch import FetchedSource


# === ImportedSource value type ===

def test_to_dict_omits_is_remote_source():
    """REGRESSION: is_remote_source is internal; must never appear in API response."""
    src = ImportedSource(
        url="https://example.com",
        title="t",
        text="x" * 250,
        is_remote_source=True,
    )
    body = src.to_dict()
    assert "is_remote_source" not in body
    assert set(body.keys()) == {"url", "title", "text"}


def test_to_dict_includes_url_title_text():
    src = ImportedSource(
        url="https://example.com/page",
        title="Title",
        text="content",
        is_remote_source=True,
    )
    assert src.to_dict() == {"url": "https://example.com/page", "title": "Title", "text": "content"}


def test_imported_source_is_frozen():
    src = ImportedSource(url=None, title="t", text="x" * 250, is_remote_source=False)
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        src.title = "new"


# === from_text ===

def test_from_text_sets_is_remote_source_false():
    src = from_text("hello world content")
    assert src.is_remote_source is False


def test_from_text_url_is_none():
    src = from_text("hello world content")
    assert src.url is None


def test_from_text_default_min_length_one_accepts_short_text():
    """Wire-contract preservation: /api/extract accepts any non-empty text."""
    src = from_text("short")
    assert src.text == "short"


def test_from_text_raises_on_empty_text():
    with pytest.raises(ParseEmpty):
        from_text("")


def test_from_text_raises_on_whitespace_only():
    with pytest.raises(ParseEmpty):
        from_text("   \n  \n  ")


def test_from_text_explicit_min_text_length():
    """Caller can pass min_text_length=200 to enforce URL-path policy."""
    with pytest.raises(ParseEmpty):
        from_text("short", min_text_length=200)


# === from_url with patched fetch ===

def test_from_url_sets_is_remote_source_true():
    fake_html = b"<html><head><title>T</title></head><body>" + b"<p>filler</p>" * 30 + b"</body></html>"
    fake_fetched = FetchedSource(
        raw_bytes=fake_html,
        headers={"content-type": "text/html"},
        final_url="https://example.com/article",
        content_type="text/html",
    )
    with patch("source_intake.fetch.fetch", return_value=fake_fetched):
        src = from_url("https://example.com/article")
    assert src.is_remote_source is True


def test_from_url_uses_final_url_after_redirect():
    fake_html = b"<html><head><title>T</title></head><body>" + b"<p>filler</p>" * 30 + b"</body></html>"
    fake_fetched = FetchedSource(
        raw_bytes=fake_html,
        headers={"content-type": "text/html"},
        final_url="https://example.com/redirected",
        content_type="text/html",
    )
    with patch("source_intake.fetch.fetch", return_value=fake_fetched):
        src = from_url("https://example.com/start")
    assert src.url == "https://example.com/redirected"


def test_from_url_routes_text_plain_to_extract_plain():
    raw_text = ("This is plain text content. " * 30).encode("utf-8")
    fake_fetched = FetchedSource(
        raw_bytes=raw_text,
        headers={"content-type": "text/plain"},
        final_url="https://example.com/file.txt",
        content_type="text/plain",
    )
    with patch("source_intake.fetch.fetch", return_value=fake_fetched):
        src = from_url("https://example.com/file.txt")
    assert "plain text content" in src.text


def test_from_url_routes_html_to_extract_html():
    fake_html = b"<html><head><title>HTML Title</title></head><body>" + b"<p>filler</p>" * 30 + b"</body></html>"
    fake_fetched = FetchedSource(
        raw_bytes=fake_html,
        headers={"content-type": "text/html"},
        final_url="https://example.com/article",
        content_type="text/html",
    )
    with patch("source_intake.fetch.fetch", return_value=fake_fetched):
        src = from_url("https://example.com/article")
    assert src.title == "HTML Title"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/source_intake/test_facade.py -v`
Expected: tests for `from_url` / `from_text` FAIL with `ImportError` (functions don't exist yet). `to_dict_omits_is_remote_source` should already pass from Task 3.

- [ ] **Step 3: Implement `from_url` and `from_text` in `source_intake/__init__.py`**

Append to `source_intake/__init__.py`:

```python
from . import fetch, parse


def from_url(url: str) -> ImportedSource:
    """Fetch and parse a single web page.

    Raises (any of): InvalidUrl, BlockedSource, FetchFailed,
                     UnsupportedContent, TooLarge, ParseEmpty.
    """
    fetched = fetch.fetch(url)
    decoded = parse.decode(fetched.raw_bytes, fetched.headers)
    if fetched.content_type == "text/plain":
        parsed = parse.extract_plain(decoded, source_url=fetched.final_url)
    else:
        parsed = parse.extract_html(decoded, source_url=fetched.final_url)
    return ImportedSource(
        url=fetched.final_url,
        title=parsed.title,
        text=parsed.text,
        is_remote_source=True,
    )


def from_text(text: str, *, min_text_length: int = 1) -> ImportedSource:
    """Normalize a raw-text submission. No fetch.

    Default min_text_length=1 preserves /api/extract's current behavior of
    accepting any non-empty text. Callers wanting the URL-path floor pass
    min_text_length=200 explicitly.

    Raises: ParseEmpty.
    """
    parsed = parse.extract_plain(text, source_url=None, min_text_length=min_text_length)
    return ImportedSource(
        url=None,
        title=parsed.title,
        text=parsed.text,
        is_remote_source=False,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/source_intake/test_facade.py -v`
Expected: all 12 tests pass.

- [ ] **Step 5: Run full source_intake suite**

Run: `pytest tests/source_intake/ -v`
Expected: every source_intake test green.

- [ ] **Step 6: Commit**

```bash
git add source_intake/__init__.py tests/source_intake/test_facade.py
git commit -m "$(cat <<'EOF'
feat(source-intake): implement from_url / from_text facade

Orchestrates fetch → decode → extract_html|extract_plain → ImportedSource.
from_url sets is_remote_source=True; from_text sets it False with
min_text_length=1 default to preserve /api/extract wire contract.

Tests cover: is_remote_source flag, to_dict() regression (must omit
is_remote_source), final_url canonical URL after redirect, dispatch
between extract_html / extract_plain by content_type.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Route mapping function + parametrized table tests

**Files:**
- Modify: `main.py` (add `_map_intake_error` and `_summarize_url_for_log` helpers; do NOT yet replace route bodies)
- Create: `tests/test_intake_route_mapping.py`

- [ ] **Step 1: Add `_map_intake_error` and `_summarize_url_for_log` helpers to `main.py`**

Find the imports block at the top of `main.py` and add:

```python
from urllib.parse import urlparse  # if not already imported
import source_intake
from source_intake import (
    BlockedSource,
    FetchFailed,
    InvalidUrl,
    ParseEmpty,
    SourceIntakeError,
    TooLarge,
    UnsupportedContent,
)
```

Add these helper functions in `main.py`, after the existing `_resolve_node_mechanism` function (around line 250):

```python
def _map_intake_error(exc: SourceIntakeError) -> HTTPException:
    """Maps source_intake domain exception → HTTP response.

    Oracle defense: BlockedSource(private_address) and FetchFailed both
    surface as 502 with the same generic user-facing message, so an
    attacker cannot use response differences to map internal network state.
    """
    if isinstance(exc, InvalidUrl):
        return HTTPException(400, "Enter a valid http(s) URL.")
    if isinstance(exc, BlockedSource):
        if exc.reason == "private_address":
            return HTTPException(502, "We couldn't reach that URL.")
        if exc.reason == "blocked_port":
            return HTTPException(400, "Only standard web ports (80/443) are supported.")
        if exc.reason == "blocked_scheme":
            return HTTPException(400, "Only http and https URLs are supported.")
        if exc.reason == "blocked_video":
            return HTTPException(400, "Video links aren't supported. Paste the text directly instead.")
        return HTTPException(502, "We couldn't reach that URL.")  # unknown reason → fail closed
    if isinstance(exc, FetchFailed):
        return HTTPException(502, "We couldn't reach that URL.")
    if isinstance(exc, UnsupportedContent):
        return HTTPException(415, "We can only import HTML or plain-text pages.")
    if isinstance(exc, TooLarge):
        return HTTPException(413, "Page is too large to import.")
    if isinstance(exc, ParseEmpty):
        return HTTPException(422, "Couldn't extract enough readable text from that page.")
    logger.exception("Unmapped SourceIntakeError")
    return HTTPException(500, "Unexpected error while importing.")


def _summarize_url_for_log(url: str) -> dict:
    """Sanitized fields for logging. URLs can carry basic-auth credentials,
    signed query tokens, fragments, or private course links — never log raw URL.
    """
    try:
        parsed = urlparse(url)
        return {
            "scheme": parsed.scheme,
            "host": parsed.hostname,
            "port": parsed.port,
            "path_len": len(parsed.path or ""),
            "has_query": bool(parsed.query),
            "has_userinfo": bool(parsed.username or parsed.password),
        }
    except Exception:
        return {"unparseable": True, "len": len(url) if url else 0}
```

- [ ] **Step 2: Write parametrized mapping tests**

```python
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
    assert "user" not in str(summary)
    assert "pass" not in str(summary)
    assert "token" not in str(summary)
    assert "secret" not in str(summary)


def test_summarize_url_for_log_handles_malformed():
    from main import _summarize_url_for_log

    summary = _summarize_url_for_log("not a url at all")
    # Should not raise; returns something logger can serialize
    assert isinstance(summary, dict)
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_intake_route_mapping.py -v`
Expected: 17 tests pass.

- [ ] **Step 4: Run full pytest to confirm no regression**

Run: `pytest -v`
Expected: every test green; existing tests still pass; new helpers are added in `main.py` but not yet called by routes.

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_intake_route_mapping.py
git commit -m "$(cat <<'EOF'
feat(source-intake): add route mapping function and url log sanitizer

Adds _map_intake_error (domain-exception → HTTPException with oracle
defense) and _summarize_url_for_log (sanitized log fields — no raw URL).
Helpers are added but not yet called from routes; route swap in next task.

Tests: full mapping table (13 cases), oracle-defense equality between
private_address and FetchFailed responses, oracle-defense distinction
between private_address and blocked_port, fail-closed on unknown reasons,
and url-summary userinfo/query redaction.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: Route swap — replace `/api/extract-url` body

**Files:**
- Modify: `main.py:383-449` (the `extract_url` route body)
- Create: `tests/test_extract_url_route.py`

- [ ] **Step 1: Replace the `extract_url` route body**

In `main.py`, locate the `extract_url` function (around line 383-449) and replace the entire function body with:

```python
@app.post("/api/extract-url")
def extract_url(req: UrlExtractRequest):
    try:
        src = source_intake.from_url(req.url)
    except SourceIntakeError as exc:
        logger.info("intake_failed", extra={
            "exc_type": type(exc).__name__,
            "reason": getattr(exc, "reason", None),
            "cause": getattr(exc, "cause", None),
            "url_summary": _summarize_url_for_log(req.url),
        })
        raise _map_intake_error(exc)
    except Exception:
        logger.exception("intake_unexpected", extra={"url_summary": _summarize_url_for_log(req.url)})
        raise HTTPException(500, "Unexpected error while importing.")
    return src.to_dict()
```

**Do NOT delete `_extract_text_from_html`, `_is_blocked_video_url`, `_is_private_url`** at lines 285-345. They become orphaned for one commit (revert safety) and are removed in Task 17.

- [ ] **Step 2: Write end-to-end route tests**

```python
# tests/test_extract_url_route.py
"""End-to-end tests for /api/extract-url through FastAPI TestClient.

These are smoke-level — most behavior is tested in tests/source_intake/
at the facade and mapping-table levels. Catches wiring errors only.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from source_intake import ImportedSource
from source_intake.errors import BlockedSource, FetchFailed, ParseEmpty, TooLarge

client = TestClient(app)


def test_extract_url_returns_imported_source_dict():
    fake_src = ImportedSource(
        url="https://example.com/page",
        title="Title",
        text="x" * 250,
        is_remote_source=True,
    )
    with patch("source_intake.from_url", return_value=fake_src):
        response = client.post("/api/extract-url", json={"url": "https://example.com/page"})
    assert response.status_code == 200
    body = response.json()
    assert body == {"url": "https://example.com/page", "title": "Title", "text": "x" * 250}
    assert "is_remote_source" not in body


def test_extract_url_maps_private_address_to_502():
    with patch("source_intake.from_url", side_effect=BlockedSource("test", reason="private_address")):
        response = client.post("/api/extract-url", json={"url": "http://internal/"})
    assert response.status_code == 502
    assert "couldn't reach" in response.json()["detail"].lower()


def test_extract_url_maps_blocked_video_to_400():
    with patch("source_intake.from_url", side_effect=BlockedSource("test", reason="blocked_video")):
        response = client.post("/api/extract-url", json={"url": "https://youtu.be/abc"})
    assert response.status_code == 400
    assert "video" in response.json()["detail"].lower()


def test_extract_url_maps_too_large_to_413():
    with patch("source_intake.from_url", side_effect=TooLarge("test")):
        response = client.post("/api/extract-url", json={"url": "https://example.com/big"})
    assert response.status_code == 413


def test_extract_url_maps_parse_empty_to_422():
    with patch("source_intake.from_url", side_effect=ParseEmpty("test")):
        response = client.post("/api/extract-url", json={"url": "https://example.com/thin"})
    assert response.status_code == 422


def test_extract_url_oracle_defense_dns_and_private_indistinguishable():
    with patch("source_intake.from_url", side_effect=BlockedSource("test", reason="private_address")):
        r1 = client.post("/api/extract-url", json={"url": "http://internal/"})
    with patch("source_intake.from_url", side_effect=FetchFailed("test", cause="dns")):
        r2 = client.post("/api/extract-url", json={"url": "http://nonexistent/"})
    assert r1.status_code == r2.status_code
    assert r1.json()["detail"] == r2.json()["detail"]
```

- [ ] **Step 3: Run route tests**

Run: `pytest tests/test_extract_url_route.py -v`
Expected: all 6 tests pass.

- [ ] **Step 4: Run full pytest**

Run: `pytest -v`
Expected: every test green.

- [ ] **Step 5: Local smoke**

Start the dev server and exercise the route:

```bash
bash scripts/dev.sh &
SERVER_PID=$!
sleep 2

# Success case
curl -s -X POST http://localhost:8000/api/extract-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/"}'

# Video block
curl -s -X POST http://localhost:8000/api/extract-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtu.be/abc"}'

# Invalid URL
curl -s -X POST http://localhost:8000/api/extract-url \
  -H "Content-Type: application/json" \
  -d '{"url": "not-a-url"}'

kill $SERVER_PID
```

Expected: success returns `{url, title, text}`; video returns 400 with video message; invalid returns 400 with URL message.

- [ ] **Step 6: Run hosted smoke (REQUIRED — this is a high-risk `main.py` change)**

```bash
bash scripts/qa-smoke.sh local
```

Expected: passes.

- [ ] **Step 7: Commit**

```bash
git add main.py tests/test_extract_url_route.py
git commit -m "$(cat <<'EOF'
refactor(extract-url): swap to source_intake.from_url

Replaces the 67-line route body with a thin try/except → _map_intake_error
mapping. Old helpers (_extract_text_from_html, _is_blocked_video_url,
_is_private_url) remain in main.py for one commit as a revert anchor —
removed in the cleanup task.

Wire contract preserved: /api/extract-url still returns {url, title, text}
on success and the same status codes on errors (with oracle-defense
collapse on private_address + FetchFailed).

Tests: 6 end-to-end through FastAPI TestClient covering success path,
mapping table, and oracle defense. Hosted smoke ran clean.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 8: Deploy and run hosted smoke (gate before next task)**

```bash
git push  # deploy to Vercel via origin/main → app.socratink.ai
```

Wait for Vercel deploy. Then:

```bash
bash scripts/verify-deploy.sh HEAD
```

Expected: hosted smoke passes. Wait one observation window (or one usage cycle) before proceeding to Task 16.

---

## Task 16: Route swap — replace `/api/extract` body

**Files:**
- Modify: `main.py:263-282` (the `extract` route body)

- [ ] **Step 1: Replace the `extract` route body**

In `main.py`, locate the `extract` function and replace it with:

```python
@app.post("/api/extract")
def extract(req: ExtractRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided.")
    try:
        src = source_intake.from_text(req.text)   # default min_text_length=1 preserves wire contract
    except ParseEmpty as err:
        raise HTTPException(status_code=400, detail=str(err))
    try:
        knowledge_map = extract_knowledge_map(src.text, api_key=req.api_key)
        return {"knowledge_map": knowledge_map}
    except MissingAPIKeyError as err:
        raise HTTPException(status_code=401, detail=str(err))
    except GeminiRateLimitError as err:
        raise HTTPException(status_code=429, detail=str(err))
    except GeminiServiceError as err:
        raise HTTPException(status_code=503, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.exception("Unexpected failure in /api/extract")
        raise HTTPException(
            status_code=500, detail="Unexpected server error during extraction."
        ) from err
```

The existing Gemini error shell (`MissingAPIKeyError`, `GeminiRateLimitError`, `GeminiServiceError`, `ValueError`, generic) is preserved verbatim. Only the input changes from `req.text` to `src.text`.

- [ ] **Step 2: Verify wire contract via existing tests**

Run: `pytest tests/ -v -k "extract and not extract_url"`
Expected: existing /api/extract tests pass; the route still accepts short text.

- [ ] **Step 3: Run full pytest**

Run: `pytest -v`
Expected: green.

- [ ] **Step 4: Local smoke**

```bash
bash scripts/dev.sh &
SERVER_PID=$!
sleep 2

# Short text — must not 422
curl -s -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "short content"}'

# Empty text — should 400
curl -s -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"text": ""}'

kill $SERVER_PID
```

Expected: short text reaches Gemini (may fail on missing api_key in env, but does NOT fail at intake with 422); empty text returns 400.

- [ ] **Step 5: Run hosted smoke (REQUIRED — `main.py` change)**

```bash
bash scripts/qa-smoke.sh local
```

Expected: passes.

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "$(cat <<'EOF'
refactor(extract): normalize input through source_intake.from_text

/api/extract now routes raw-text submissions through from_text() before
calling extract_knowledge_map. Default min_text_length=1 preserves the
existing wire contract (any non-empty text accepted).

Gemini error shell unchanged: MissingAPIKeyError → 401, GeminiRateLimitError
→ 429, GeminiServiceError → 503, ValueError → 400, generic → 500.

Sets is_remote_source=False on the ImportedSource (downstream prompt-
injection awareness wiring lands in a separate change).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: Deploy and hosted smoke**

```bash
git push
bash scripts/verify-deploy.sh HEAD
```

Wait one observation window before Task 17.

---

## Task 17: Delete orphaned helpers from `main.py`

**Files:**
- Modify: `main.py:285-345` — DELETE `_extract_text_from_html`, `_is_blocked_video_url`, `_is_private_url`

- [ ] **Step 1: Delete the three orphaned helper functions**

Open `main.py` and delete the entire block (lines ~285 through ~345):

```python
def _extract_text_from_html(raw_html: str) -> str:
    cleaned = re.sub(...)
    ...
    return cleaned.strip()


def _is_blocked_video_url(url: str) -> bool:
    parsed = urlparse(url)
    ...


def _is_private_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname
    ...
    return any(...)
```

After deletion, also remove imports that are no longer used in `main.py`:
- `import ipaddress` — was only used by `_is_private_url`
- `import socket` — only used by `_is_private_url`
- `from html import unescape` — only used by `_extract_text_from_html`

Keep all other imports (`re` is still used elsewhere; `urlparse` is used by `_summarize_url_for_log`).

- [ ] **Step 2: Verify import cleanup did not break anything**

Run:
```bash
python -c "import main; print('main imports ok')"
```
Expected: prints `main imports ok` with no `ImportError`.

- [ ] **Step 3: Run full pytest**

Run: `pytest -v`
Expected: every test green. The deleted functions are not referenced anywhere; nothing breaks.

- [ ] **Step 4: Run preflight (validates Vercel package surface)**

Run: `bash scripts/preflight-deploy.sh`
Expected: passes.

- [ ] **Step 5: Local smoke**

```bash
bash scripts/qa-smoke.sh local
```
Expected: passes.

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "$(cat <<'EOF'
refactor(extract-url): remove orphaned regex/SSRF helpers from main.py

Deletes _extract_text_from_html, _is_blocked_video_url, _is_private_url
from main.py:285-345. Their behavior now lives in source_intake/parse.py
and source_intake/fetch.py with stronger guarantees (BS4 parsing instead
of regex; pinned-IP connect closes DNS rebinding; redirect re-validation
covers the line-404 audit-pass-1 SSRF gap).

Also removes now-unused imports: ipaddress, socket, html.unescape.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: Deploy and final hosted smoke**

```bash
git push
bash scripts/verify-deploy.sh HEAD
```

Expected: hosted smoke passes. Refactor complete.

---

## Done — what shipped

- 6 new files in `source_intake/` (4 module files + 2 init files)
- 12 new test files in `tests/source_intake/` + `tests/test_intake_route_mapping.py` + `tests/test_extract_url_route.py`
- 4 new HTML fixtures
- 3 new direct dependencies (exact-pinned)
- 1 glossary entry
- 80+ new tests
- 17 commits, 3 production deploys with hosted-smoke gates
- 60 lines of regex/SSRF helpers removed from `main.py`
- Wire contracts on `/api/extract` and `/api/extract-url` preserved bit-for-bit
- DNS rebinding closed via pinned-IP connect
- Redirect re-validation closes the line-404 SSRF gap

## Out of scope (per spec — separate follow-ups)

- Wiring `is_remote_source` flag into `ai_service.py` extraction prompt assembly
- Restructuring `/api/extract` response shape
- New structured-logging infrastructure
- Tests for `ai_service.py` extraction path (Candidates #2 / #3)
- Allowlist mechanism for non-standard ports if a real user hits the new SSRF tightening
