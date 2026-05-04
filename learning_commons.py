"""Learning Commons (LC) Knowledge Graph client.

Spec reference: docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md
sections 3.3.2 (the four enrichment gates) and 5.2 (client surface,
timeout budget, cache).

This module is best-effort enrichment for source-less provisional-map
generation. Every failure path returns ``None`` — the calling code
treats ``None`` as "no enrichment available" and proceeds with pure-AI
generation.

Verification log: see spec Appendix A. Score >= 0.70 is the empirical
floor for "real semantic match" vs "closest-substring noise" against
the LC dataset as of 2026-05-02. Prerequisites/related-standards endpoints
are populated empty today and are deliberately not used.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# --- Status sentinels for LCClient.last_status ------------------------------
# These values are read by the route handler to emit the correct telemetry
# reason from spec §5.4 vocabulary.

LC_STATUS_OK = "ok"
LC_STATUS_KEY_MISSING = "key_missing"
LC_STATUS_TIMEOUT = "timeout"
LC_STATUS_TRANSPORT_ERROR = "transport_error"
LC_STATUS_HTTP_ERROR = "http_error"
LC_STATUS_PARSE_ERROR = "parse_error"
LC_STATUS_EMPTY_QUERY = "empty_query"


# --- Configuration -----------------------------------------------------------

LC_BASE_URL = "https://api.learningcommons.org/knowledge-graph"
LC_SEARCH_PATH = "/v0/academic-standards/search"
LC_TIMEOUT_SECONDS = 0.8
LC_RELEVANCE_THRESHOLD = 0.70
LC_K12_DESCRIPTION_MIN_LEN = 40

LC_CACHE_SIZE = 256
LC_CACHE_TTL_SECONDS = 86_400  # 24h

LC_SEARCH_LIMIT = 5  # request enough to pick top 2-3 after ranking


# --- Data shapes -------------------------------------------------------------


@dataclass(frozen=True)
class LCStandard:
    case_uuid: str
    statement_code: Optional[str]
    description: str
    jurisdiction: str
    score: float


@dataclass(frozen=True)
class LCSearchResult:
    top_score: float
    standards: list[LCStandard]


# --- TTL+LRU cache (tiny manual implementation, no external deps) -----------


class _TtlLruCache:
    """In-process cache with both a max-size LRU bound and per-entry TTL.

    Manual implementation to avoid pulling cachetools or functools.lru_cache
    (which has no TTL). Thread-safe via a single internal lock.
    """

    def __init__(self, max_size: int, ttl_seconds: float):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._data: dict = {}  # key -> (timestamp, value)
        self._order: list = []  # LRU order, oldest first
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            ts, value = entry
            if time.monotonic() - ts > self._ttl:
                self._data.pop(key, None)
                if key in self._order:
                    self._order.remove(key)
                return None
            # bump LRU order
            if key in self._order:
                self._order.remove(key)
            self._order.append(key)
            return value

    def set(self, key, value):
        with self._lock:
            self._data[key] = (time.monotonic(), value)
            if key in self._order:
                self._order.remove(key)
            self._order.append(key)
            # evict oldest if over size
            while len(self._order) > self._max_size:
                evict = self._order.pop(0)
                self._data.pop(evict, None)

    def clear(self):
        with self._lock:
            self._data.clear()
            self._order.clear()


# --- LC HTTP client ---------------------------------------------------------


class LCClient:
    """HTTP client for the Learning Commons Knowledge Graph search endpoint.

    Best-effort: every failure mode returns ``None``. The caller treats ``None``
    as "LC unavailable / unusable, proceed with pure AI generation."
    """

    # Single shared cache across instances (LC results are public, not user-scoped).
    _cache = _TtlLruCache(max_size=LC_CACHE_SIZE, ttl_seconds=LC_CACHE_TTL_SECONDS)

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        urlopen: Optional[Callable] = None,
    ):
        """:param api_key: defaults to ``LEARNING_COMMONS_API_KEY`` env var.
        :param urlopen: dependency-injected HTTP fetcher for tests; defaults to
                        ``urllib.request.urlopen``.
        """
        self._api_key = api_key if api_key is not None else os.environ.get("LEARNING_COMMONS_API_KEY")
        self._urlopen = urlopen if urlopen is not None else urlrequest.urlopen
        self.last_status: str = LC_STATUS_OK

    def search_concept(self, concept: Optional[str]) -> Optional[LCSearchResult]:
        self.last_status = LC_STATUS_OK
        if not self._api_key:
            self.last_status = LC_STATUS_KEY_MISSING
            logger.info("learning_commons.skipped", extra={"reason": "key_missing"})
            return None
        if concept is None:
            self.last_status = LC_STATUS_EMPTY_QUERY
            return None
        normalized = concept.strip().lower()
        if not normalized:
            self.last_status = LC_STATUS_EMPTY_QUERY
            return None

        cached = self._cache.get(normalized)
        if cached is not None:
            # Cache hit: status stays LC_STATUS_OK
            return cached

        result = self._fetch(normalized)
        if result is not None:
            self._cache.set(normalized, result)
        return result

    def _fetch(self, normalized_concept: str) -> Optional[LCSearchResult]:
        query = urlencode({"query": normalized_concept, "limit": LC_SEARCH_LIMIT})
        url = f"{LC_BASE_URL}{LC_SEARCH_PATH}?{query}"
        req = urlrequest.Request(url, headers={"Authorization": f"Bearer {self._api_key}"})
        started = time.monotonic()
        try:
            with self._urlopen(req, timeout=LC_TIMEOUT_SECONDS) as response:
                body = response.read()
        except HTTPError as err:
            latency_ms = int((time.monotonic() - started) * 1000)
            self.last_status = LC_STATUS_HTTP_ERROR
            logger.warning(
                "learning_commons.http_error",
                extra={"status": err.code, "latency_ms": latency_ms},
            )
            return None
        except socket.timeout as err:
            latency_ms = int((time.monotonic() - started) * 1000)
            self.last_status = LC_STATUS_TIMEOUT
            logger.warning(
                "learning_commons.transport_error",
                extra={"reason": str(err), "latency_ms": latency_ms},
            )
            return None
        except URLError as err:
            latency_ms = int((time.monotonic() - started) * 1000)
            self.last_status = LC_STATUS_TRANSPORT_ERROR
            logger.warning(
                "learning_commons.transport_error",
                extra={"reason": str(err), "latency_ms": latency_ms},
            )
            return None
        except Exception as err:  # belt & suspenders
            self.last_status = LC_STATUS_TRANSPORT_ERROR
            logger.exception("learning_commons.unexpected_error: %s", err)
            return None

        latency_ms = int((time.monotonic() - started) * 1000)
        try:
            payload = json.loads(body)
        except (ValueError, TypeError) as err:
            self.last_status = LC_STATUS_PARSE_ERROR
            logger.warning(
                "learning_commons.parse_error",
                extra={"reason": str(err), "latency_ms": latency_ms},
            )
            return None

        if not isinstance(payload, list) or not payload:
            return LCSearchResult(top_score=0.0, standards=[])

        standards = []
        for entry in payload:
            try:
                standards.append(LCStandard(
                    case_uuid=str(entry.get("caseIdentifierUUID", "")),
                    statement_code=entry.get("statementCode"),
                    description=str(entry.get("description", "")),
                    jurisdiction=str(entry.get("jurisdiction", "")),
                    score=float(entry.get("score", 0.0)),
                ))
            except (TypeError, ValueError):
                continue  # skip malformed entries; keep the rest

        standards.sort(key=lambda s: s.score, reverse=True)
        top_score = standards[0].score if standards else 0.0
        return LCSearchResult(top_score=top_score, standards=standards)


# --- Four-gate threshold ----------------------------------------------------

# Initial K-12 jurisdiction allowlist. "Multi-State" is the most common
# value in LC's NGSS / CCSS aggregations. US state names cover the
# state-specific frameworks. Heuristic is deliberately loose; tighten
# from telemetry on `enrichment_skipped: non_k12`.
_US_STATES = frozenset({
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming", "District of Columbia",
})


def _looks_k12(standard: LCStandard) -> bool:
    """Heuristic: gate 4 from spec §3.3.2.

    Initial implementation: jurisdiction is "Multi-State" or a US state name,
    AND (statement_code is non-null OR description is non-empty and >= a
    minimum length). Telemetry on `enrichment_skipped: non_k12` reveals
    where this under-fires; tighten or loosen from there.
    """
    juris = (standard.jurisdiction or "").strip()
    if juris != "Multi-State" and juris not in _US_STATES:
        return False
    if standard.statement_code:
        return True
    if standard.description and len(standard.description) >= LC_K12_DESCRIPTION_MIN_LEN:
        return True
    return False


def should_enrich_with_lc(
    result: Optional[LCSearchResult],
) -> Optional[list[LCStandard]]:
    """Apply the four enrichment gates from spec §3.3.2.

    Returns the top 2-3 standards when all gates pass, ``None`` otherwise.
    The caller passes the returned list (or ``None``) into
    ``generate_provisional_map_from_sketch(..., lc_context=...)``.
    """
    # Gate 1 (API responded) is implicit: if this function received a
    # result at all, the call returned successfully. Network/timeout
    # failures upstream produce result=None.
    if result is None:
        return None
    # Gate 2: results returned
    if not result.standards:
        return None
    top = result.standards[0]
    # Gate 3: score floor
    if top.score < LC_RELEVANCE_THRESHOLD:
        return None
    # Gate 4: K-12 academic confidence
    if not _looks_k12(top):
        return None
    return result.standards[:3]
