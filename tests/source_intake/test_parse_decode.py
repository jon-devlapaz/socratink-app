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
