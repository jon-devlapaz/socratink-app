"""Tests for the Learning Commons HTTP client + cache."""
from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from learning_commons import LCClient, LCSearchResult, LCStandard


@pytest.fixture(autouse=True)
def clear_lc_cache():
    LCClient._cache.clear()
    yield
    LCClient._cache.clear()


# Realistic sample, sourced verbatim from the brainstorm verification log.
_PHOTOSYNTHESIS_RESPONSE = json.dumps([
    {
        "caseIdentifierUUID": "03e3c05a-b2f6-11e9-b131-0242ac150005",
        "statementCode": None,
        "description": "Plants, algae, and many microorganisms use the energy from light to make sugars from carbon dioxide and water through photosynthesis.",
        "jurisdiction": "Multi-State",
        "score": 0.7599,
    },
    {
        "caseIdentifierUUID": "abc-uuid-2",
        "statementCode": None,
        "description": "The process of photosynthesis converts light energy to stored chemical energy.",
        "jurisdiction": "Multi-State",
        "score": 0.7395,
    },
]).encode("utf-8")


def _fake_urlopen_returning(body: bytes, status: int = 200):
    fake_response = MagicMock()
    fake_response.read.return_value = body
    fake_response.status = status
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=fake_response)


def test_search_concept_happy_path():
    fake = _fake_urlopen_returning(_PHOTOSYNTHESIS_RESPONSE)
    client = LCClient(api_key="sk_test_xxx", urlopen=fake)

    result = client.search_concept("photosynthesis")

    assert isinstance(result, LCSearchResult)
    assert len(result.standards) == 2
    assert result.standards[0].score == pytest.approx(0.7599)
    assert result.standards[0].description.startswith("Plants, algae")
    assert result.standards[0].jurisdiction == "Multi-State"
    assert result.top_score == pytest.approx(0.7599)


def test_search_concept_missing_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("LEARNING_COMMONS_API_KEY", raising=False)
    client = LCClient(api_key=None, urlopen=_fake_urlopen_returning(b"[]"))
    assert client.search_concept("photosynthesis") is None


def test_search_concept_empty_query_returns_none():
    client = LCClient(api_key="sk_test_xxx", urlopen=_fake_urlopen_returning(b"[]"))
    assert client.search_concept("") is None
    assert client.search_concept("   ") is None
    assert client.search_concept(None) is None  # type: ignore[arg-type]


def test_search_concept_http_error_returns_none():
    from urllib.error import HTTPError
    fake = MagicMock(side_effect=HTTPError(
        url="https://api.learningcommons.org/", code=503, msg="Service Unavailable",
        hdrs=None, fp=None
    ))
    client = LCClient(api_key="sk_test_xxx", urlopen=fake)
    assert client.search_concept("photosynthesis") is None


def test_search_concept_timeout_returns_none():
    from socket import timeout as SocketTimeout
    fake = MagicMock(side_effect=SocketTimeout("timed out"))
    client = LCClient(api_key="sk_test_xxx", urlopen=fake)
    assert client.search_concept("photosynthesis") is None


def test_search_concept_malformed_json_returns_none():
    fake = _fake_urlopen_returning(b"not json {{")
    client = LCClient(api_key="sk_test_xxx", urlopen=fake)
    assert client.search_concept("photosynthesis") is None


def test_search_concept_uses_cache_on_repeat():
    fake = _fake_urlopen_returning(_PHOTOSYNTHESIS_RESPONSE)
    client = LCClient(api_key="sk_test_xxx", urlopen=fake)

    client.search_concept("Photosynthesis")  # warms cache (lowercased)
    client.search_concept("photosynthesis")  # hit
    client.search_concept("PHOTOSYNTHESIS  ")  # hit (whitespace + case normalized)

    assert fake.call_count == 1, "cache should collapse repeated normalized queries"


def test_authorization_header_uses_bearer_scheme():
    fake = _fake_urlopen_returning(_PHOTOSYNTHESIS_RESPONSE)
    client = LCClient(api_key="sk_test_xxx", urlopen=fake)
    client.search_concept("photosynthesis")

    request = fake.call_args.args[0]
    assert request.get_header("Authorization") == "Bearer sk_test_xxx"
