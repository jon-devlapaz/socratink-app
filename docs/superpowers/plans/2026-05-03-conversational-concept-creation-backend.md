# Conversational Concept Creation — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backend support for source-optional concept creation. Add a new payload shape on `POST /api/extract` that accepts `{name, starting_sketch, source}` (source nullable), source-less generation via a new `generate_provisional_map_from_sketch` function, optional Learning Commons (LC) enrichment behind a four-gate threshold, server-side substantiveness validation as defense in depth, and structured telemetry for `build_blocked` + `ai_call`.

**Architecture:** Reuse the existing `llm/` seam and `models/provisional_map.py` from the foundation work. Add one new module (`learning_commons.py`) for LC REST calls + LRU+TTL cache + the four-gate threshold. Add one new helper module (`models/sketch_validation.py`) with `is_substantive_sketch` shared between server validation and the future frontend (a JSON parity fixture lives in `tests/fixtures/` so Plan B's JS implementation can be verified byte-for-byte against this). Add two new prompts at `app_prompts/`. Update `extract_knowledge_map`'s call site (the FastAPI handler in `main.py`) to dispatch by source-attachment state. Use stdlib `urllib.request` for LC HTTP — zero new dependencies — matching the project's preference for direct stdlib HTTP (`source_intake/fetch.py` uses `urllib3` for the same reason).

**Tech Stack:** Python 3.x, FastAPI, Pydantic 2, pytest, Gemini via the existing `llm/` seam, stdlib `urllib.request` for LC HTTP.

**Spec reference:** `docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md` (commits `43a3bf2` + `f584918`).

**This plan covers:** spec sections 3.3 (graph generation), 5.1 (new generation path), 5.2 (LC client), 5.3 (endpoint shape with server-side validation), 5.4 (telemetry — backend events only).

**This plan does NOT cover:** spec sections 3.1, 3.2 (chat surface, summary card — frontend), 4 (frontend changes), 8 acceptance criteria #6-#10 (require frontend), 9 step 4 (DESIGN.md updates). Those land in **Plan B (frontend)** and **Plan C (acceptance + docs)**, which depend on this plan landing first.

**Foundation prerequisites (already landed in `dev`):** `llm/` package (`LLMClient`, `StructuredLLMRequest`, normalized errors); `models/provisional_map.py` (`ProvisionalMap` Pydantic model with structural validators); `extract_knowledge_map(raw_text, *, llm, api_key, telemetry_context)` in `ai_service.py`; `POST /api/extract` route in `main.py` with `ExtractRequest` payload (currently `{text, api_key}`).

**LC API (verified during brainstorm, see spec Appendix A):** Base URL `https://api.learningcommons.org/knowledge-graph`. Search endpoint: `GET /v0/academic-standards/search?query=<concept>&limit=<N>`, header `Authorization: Bearer ${LEARNING_COMMONS_API_KEY}`. Response is a JSON list of standards with `caseIdentifierUUID`, `statementCode` (or `null`), `description`, `jurisdiction`, `score`, etc.

---

## File Structure

**New files**

| File | Responsibility | LOC est |
|---|---|---|
| `models/sketch_validation.py` | `is_substantive_sketch(text: str) -> bool` — single source of truth for the substantiveness heuristic. Re-exported from `models/__init__.py`. | ~50 |
| `learning_commons.py` | `LCClient` (stdlib HTTP + Bearer auth + 800ms timeout), `LCStandard` / `LCSearchResult` frozen dataclasses, `_TtlLruCache` (manual ~25-line cache), `should_enrich_with_lc(result) -> list[LCStandard] \| None` (four-gate threshold). | ~180 |
| `app_prompts/threshold-chat-system-v1.txt` | System prompt for the threshold chat (turn 2 probe + analogical fallback). Anti-filler / Socratic-voice / concept-derived-analogy constraints per spec §3.1, §5.1. | ~40 lines of prompt |
| `app_prompts/generate-from-sketch-system-v1.txt` | System prompt for source-less provisional-map generation. Same JSON output schema as `extract-system-v1.txt`. Describes the `<lc_context>` block role (grounding-only, never authoritative). | ~80 lines of prompt |

**Modified files**

| File | Change | Section |
|---|---|---|
| `models/__init__.py` | Re-export `is_substantive_sketch` | spec §5.3 |
| `ai_service.py` | Add `generate_provisional_map_from_sketch(concept, sketch, *, llm=None, api_key=None, lc_context=None, telemetry_context=None) -> ProvisionalMap` | spec §5.1 |
| `main.py` | Reshape `ExtractRequest` to `{text?, name?, starting_sketch?, source, api_key}`. Add server-side substantiveness gate. Dispatch `/api/extract` to old path when `text` is present (back-compat) or to `generate_provisional_map_from_sketch` when source-less payload arrives. Wire `build_blocked` + `ai_call` telemetry events. | spec §5.3, §5.4 |
| `.env.example` | Add `LEARNING_COMMONS_API_KEY=<paste-here>` placeholder line. | spec §5.2 |

**New tests**

| File | What it tests |
|---|---|
| `tests/fixtures/sketch_validation_parity.json` | ~30 input strings labeled `{text, expected_substantive: bool}`. Covers substantive sketches, "don't know" patterns (`idk`, `no idea`, `i dont know`, `?`, `…`, repeated chars, single chars), borderline cases. **Used by both Python tests in this plan and JS tests in Plan B for byte-for-byte parity.** |
| `tests/test_sketch_validation.py` | Loads the parity fixture; asserts `is_substantive_sketch(text) == expected` for every entry. Plus a small handful of unit tests for stopword handling, whitespace normalization, casing. |
| `tests/test_learning_commons_client.py` | Happy path (search returns standards), missing key returns `None`, HTTP error returns `None`, timeout returns `None`, empty concept returns `None`, cache hit on repeated calls. Uses a fake `urllib.request.urlopen` injected through the client. |
| `tests/test_learning_commons_gates.py` | `should_enrich_with_lc` truth-table tests across all four gates: no-results → `None`, low-score → `None`, non-K12 → `None`, all-pass → returns top-N standards. Uses `LCSearchResult` directly, no HTTP. |
| `tests/test_app_prompts_threshold_chat.py` | Loads the threshold-chat prompt file; asserts the anti-filler clauses are present (literal substring checks for "no acknowledgments", "no preambles", "no consolation copy"). Catches accidental prompt edits that drop the constraints. |
| `tests/test_app_prompts_generate_from_sketch.py` | Loads the generate-from-sketch prompt file; asserts the `<lc_context>` block role is described, output JSON schema reference is present, "favor the learner's sketch" rule is present. |
| `tests/test_generate_from_sketch.py` | Calls `generate_provisional_map_from_sketch` with a fake `LLMClient`; asserts the returned `ProvisionalMap` matches the fake's parsed output; asserts `lc_context=None` and `lc_context=[<standards>]` paths assemble different user prompts (the LC context block appears only when present). |
| `tests/test_extract_route_source_optional.py` | Covers the four truth-table states from spec §3.2: substantive sketch + no source → succeeds via source-less path; substantive sketch + source → succeeds via existing extract path; thin sketch + no source → 422 with `thin_sketch_no_source`; thin sketch + source → succeeds via existing extract path. Plus: missing `name` → 422 with `missing_concept`. |
| `tests/test_concept_create_telemetry.py` | Asserts that submits emit `concept_create.build_blocked` (with `reason` + `origin: "server"`) when validation fails and `concept_create.ai_call` (with `stage`, `model`, `tokens_in`, `tokens_out`, `latency_ms`, `cost_usd_est`) after each successful generation. Captures via Python `caplog`. |

---

## Phase 1: Substantiveness helper + parity fixture

### Task 1: Create the parity fixture

**Files:**
- Create: `tests/fixtures/sketch_validation_parity.json`

- [ ] **Step 1: Create the fixture file**

```json
{
  "version": 1,
  "description": "Shared parity fixture for is_substantive_sketch. Loaded by Python tests (tests/test_sketch_validation.py) and JS tests in Plan B for byte-for-byte parity. Each entry is {text, expected_substantive}.",
  "entries": [
    {"text": "Plants take in light and somehow make sugar. Not sure where the water goes.", "expected_substantive": true},
    {"text": "Photosynthesis happens in chloroplasts where light energy converts CO2 and water into glucose and oxygen.", "expected_substantive": true},
    {"text": "I think it is when cells divide into two and each new cell has the same DNA.", "expected_substantive": true},
    {"text": "A way of thinking about how you think — noticing your own learning patterns.", "expected_substantive": true},

    {"text": "idk", "expected_substantive": false},
    {"text": "Idk", "expected_substantive": false},
    {"text": "IDK", "expected_substantive": false},
    {"text": "i dont know", "expected_substantive": false},
    {"text": "I don't know", "expected_substantive": false},
    {"text": "no idea", "expected_substantive": false},
    {"text": "no clue", "expected_substantive": false},
    {"text": "?", "expected_substantive": false},
    {"text": "??", "expected_substantive": false},
    {"text": "...", "expected_substantive": false},
    {"text": "…", "expected_substantive": false},
    {"text": "", "expected_substantive": false},
    {"text": "   ", "expected_substantive": false},
    {"text": "\n\n", "expected_substantive": false},
    {"text": "asdf", "expected_substantive": false},
    {"text": "asdfasdfasdf", "expected_substantive": false},
    {"text": "aaaaaaaaaaaaaaaa", "expected_substantive": false},
    {"text": "??????????", "expected_substantive": false},

    {"text": "photosynthesis", "expected_substantive": false},
    {"text": "long division", "expected_substantive": false},
    {"text": "the cell does stuff", "expected_substantive": false},

    {"text": "I think plants need light to grow but I'm not sure how that turns into food.", "expected_substantive": true},
    {"text": "It happens in steps: light hits the leaf, water moves up, sugar comes out somehow.", "expected_substantive": true},

    {"text": "Idk really, maybe something with light and water and the leaves do work?", "expected_substantive": true}
  ]
}
```

**Why these specific entries:** the substantive set covers the kinds of replies a real learner would give (rough, incomplete, with acknowledged confusion). The non-substantive set covers the real failure modes — "don't know" patterns, keyboard mash, single concept-name echoes, whitespace-only. The borderline entries (like the last three) test that hedged-but-real sketches pass while bare concept names fail.

- [ ] **Step 2: Commit the fixture**

```bash
git add tests/fixtures/sketch_validation_parity.json
git commit -m "test(fixture): shared sketch-validation parity fixture for FE/BE

The is_substantive_sketch heuristic must match byte-for-byte between
server-side validation (Python, this plan) and the future frontend
(JS, Plan B). This fixture is the contract — both implementations
load it and assert the same booleans.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Write the failing parity test

**Files:**
- Create: `tests/test_sketch_validation.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for is_substantive_sketch — the shared substantiveness gate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.sketch_validation import is_substantive_sketch


PARITY_FIXTURE = (
    Path(__file__).parent / "fixtures" / "sketch_validation_parity.json"
)


def _load_parity_entries():
    payload = json.loads(PARITY_FIXTURE.read_text())
    return [(e["text"], e["expected_substantive"]) for e in payload["entries"]]


@pytest.mark.parametrize("text,expected", _load_parity_entries())
def test_parity_fixture_entries(text: str, expected: bool):
    """Every parity-fixture entry must produce the labeled result.

    This test is the contract enforced between Python and JS implementations.
    A divergence between this and Plan B's JS implementation is a release-blocker.
    """
    assert is_substantive_sketch(text) is expected, (
        f"is_substantive_sketch({text!r}) returned "
        f"{is_substantive_sketch(text)!r}, expected {expected!r}"
    )


def test_strips_leading_trailing_whitespace():
    assert is_substantive_sketch("  idk  ") is False
    assert is_substantive_sketch("\n\n  Plants take in light and make sugar  \n") is True


def test_case_insensitive_dont_know_patterns():
    for variant in ("IDK", "idk", "Idk", "I Don't Know", "I DON'T KNOW", "no IDEA"):
        assert is_substantive_sketch(variant) is False, f"{variant!r} should be non-substantive"


def test_empty_string_is_non_substantive():
    assert is_substantive_sketch("") is False
    assert is_substantive_sketch("   ") is False
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_sketch_validation.py -v
```

Expected: `ImportError: cannot import name 'is_substantive_sketch' from 'models.sketch_validation'` (the module doesn't exist yet).

---

### Task 3: Implement `is_substantive_sketch`

**Files:**
- Create: `models/sketch_validation.py`
- Modify: `models/__init__.py:1-10` (add re-export)

- [ ] **Step 1: Implement the helper**

```python
"""Shared substantiveness heuristic for the learner's starting sketch.

This is the *only* place the substantiveness rule is defined for the backend.
Frontend (Plan B) ports this exact behavior to JS and verifies parity against
``tests/fixtures/sketch_validation_parity.json``.

A sketch is "substantive" when it carries enough learner-generated signal to
seed source-less provisional-map generation. The heuristic is deliberately
simple — token count + a small "don't know" pattern list — because:

  - It must run identically in two languages.
  - The cost of a false-negative (blocking a learner whose sketch is actually
    fine) is recoverable: the strategy-framed footer copy invites them to add
    more or attach source.
  - The cost of a false-positive (passing through a thin sketch that triggers
    hallucinated source-less generation) is foundational principle violation
    per spec §2 principle #7.

When in doubt, this returns False. Source attachment is always a valid
alternative for the learner.
"""
from __future__ import annotations

import re

# Minimum non-stopword token count to be considered substantive.
MIN_SUBSTANTIVE_TOKENS = 8

# Patterns the learner uses when they have nothing to say. Matched as
# normalized substring of the *whole* normalized sketch (stripped, lowercased,
# punctuation collapsed). Keep the list short and obvious; longer/cleverer
# detection is a different problem.
_DONT_KNOW_PATTERNS = (
    "idk",
    "i dont know",
    "i don't know",
    "no idea",
    "no clue",
    "dunno",
    "not sure",  # NOTE: only matches if the whole sketch is essentially this
)

# A small English stopword set — kept tiny on purpose so we don't ship an
# external dictionary and so JS parity stays trivial.
_STOPWORDS = frozenset(
    """
    a an the and or but if of for in on at to from by with as is are was were
    be been being do does did has have had this that these those it its
    """.split()
)

_PUNCT_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")
_REPEATED_CHAR_RE = re.compile(r"^(.)\1{4,}$")  # aaaaa, ?????, ......


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace, drop punctuation."""
    text = text.strip().lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _is_dont_know(normalized: str) -> bool:
    """The whole sketch is essentially a 'don't know' pattern."""
    if not normalized:
        return True
    if _REPEATED_CHAR_RE.match(normalized):
        return True
    # Match if the normalized sketch *equals* a don't-know phrase exactly,
    # OR is one of the phrases plus very little extra (≤3 extra tokens).
    for pattern in _DONT_KNOW_PATTERNS:
        if normalized == pattern:
            return True
        if normalized.startswith(pattern + " "):
            extra = normalized[len(pattern) + 1:].split()
            if len(extra) <= 3:
                return True
    return False


def _count_substantive_tokens(normalized: str) -> int:
    """Token count after dropping stopwords and very short tokens."""
    tokens = [t for t in normalized.split() if t and len(t) >= 2]
    return sum(1 for t in tokens if t not in _STOPWORDS)


def is_substantive_sketch(text: str) -> bool:
    """Return True if the sketch carries enough learner signal to seed
    source-less provisional-map generation.

    See the module docstring for the principle this enforces and why the
    heuristic is deliberately simple.
    """
    if text is None:
        return False
    normalized = _normalize(text)
    if not normalized:
        return False
    if _is_dont_know(normalized):
        return False
    if _count_substantive_tokens(normalized) < MIN_SUBSTANTIVE_TOKENS:
        return False
    return True
```

- [ ] **Step 2: Add the re-export in `models/__init__.py`**

Read the current file first to find the right insertion point.

```bash
cat models/__init__.py
```

Append (or merge into existing re-exports):

```python
from .sketch_validation import is_substantive_sketch  # noqa: F401
```

- [ ] **Step 3: Run the test to verify it passes**

```bash
pytest tests/test_sketch_validation.py -v
```

Expected: all parametrized parity entries pass + the three explicit unit tests pass. If any parity entry fails, fix the heuristic — the fixture is the contract, code conforms to it (not the other way around).

If the parity fixture has an entry that *should* fail but the heuristic should pass it (or vice versa), that's a heuristic bug. Update the heuristic until parity is green. Do NOT edit the fixture to mask a heuristic gap.

- [ ] **Step 4: Commit**

```bash
git add models/sketch_validation.py models/__init__.py tests/test_sketch_validation.py
git commit -m "feat(models): is_substantive_sketch helper + parity tests

Single source of truth for the sketch substantiveness gate (spec
§3.2, §5.3). Frontend (Plan B) will port this heuristic to JS and
verify parity against tests/fixtures/sketch_validation_parity.json.

Heuristic is deliberately simple — token count + don't-know pattern
list + repeated-char check — because it must run identically in two
languages and false-negatives cost only the strategy-framed footer
copy, while false-positives violate principle #7.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2: Learning Commons client

### Task 4: Write LC search-only happy-path test (drives module shape)

**Files:**
- Create: `tests/test_learning_commons_client.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for the Learning Commons HTTP client + cache."""
from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from learning_commons import LCClient, LCSearchResult, LCStandard


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
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_learning_commons_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'learning_commons'`.

---

### Task 5: Implement `learning_commons.py` (skeleton + client)

**Files:**
- Create: `learning_commons.py`

- [ ] **Step 1: Implement the module**

```python
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

    def search_concept(self, concept: Optional[str]) -> Optional[LCSearchResult]:
        if not self._api_key:
            logger.info("learning_commons.skipped", extra={"reason": "key_missing"})
            return None
        if concept is None:
            return None
        normalized = concept.strip().lower()
        if not normalized:
            return None

        cached = self._cache.get(normalized)
        if cached is not None:
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
            logger.warning(
                "learning_commons.http_error",
                extra={"status": err.code, "latency_ms": latency_ms},
            )
            return None
        except (URLError, socket.timeout) as err:
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "learning_commons.transport_error",
                extra={"reason": str(err), "latency_ms": latency_ms},
            )
            return None
        except Exception as err:  # belt & suspenders
            logger.exception("learning_commons.unexpected_error: %s", err)
            return None

        latency_ms = int((time.monotonic() - started) * 1000)
        try:
            payload = json.loads(body)
        except (ValueError, TypeError) as err:
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
```

- [ ] **Step 2: Run the tests to verify they pass**

```bash
pytest tests/test_learning_commons_client.py -v
```

Expected: all 7 tests pass.

If `test_authorization_header_uses_bearer_scheme` fails because `Request.get_header` returns `None`, note that urllib normalizes header names to title case — `request.get_header("Authorization")` should work. If it doesn't, fall back to `request.headers["Authorization"]`.

- [ ] **Step 3: Commit**

```bash
git add learning_commons.py tests/test_learning_commons_client.py
git commit -m "feat(learning-commons): HTTP client + LRU+TTL cache

Best-effort enrichment client for source-less provisional-map
generation (spec §5.2). All failure modes return None; the caller
treats None as 'no enrichment available' and proceeds with pure AI.

Implementation choices:
- stdlib urllib.request — zero new deps; matches source_intake/
  fetch.py pattern of using stdlib HTTP directly
- Manual TTL+LRU cache (~25 lines) — no cachetools dependency
- Class-level shared cache: LC results are public, not user-scoped
- Dependency-injected urlopen for testability

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Write the four-gate threshold test

**Files:**
- Create: `tests/test_learning_commons_gates.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for should_enrich_with_lc — the four-gate enrichment threshold."""
from __future__ import annotations

from learning_commons import (
    LCSearchResult,
    LCStandard,
    should_enrich_with_lc,
)


def _std(score: float, *, jurisdiction: str = "Multi-State",
         statement_code: str | None = "HS-LS1-4",
         description: str = "x" * 60,
         uuid: str = "u-1") -> LCStandard:
    return LCStandard(
        case_uuid=uuid,
        statement_code=statement_code,
        description=description,
        jurisdiction=jurisdiction,
        score=score,
    )


def test_none_input_returns_none():
    assert should_enrich_with_lc(None) is None


def test_empty_standards_returns_none():
    result = LCSearchResult(top_score=0.0, standards=[])
    assert should_enrich_with_lc(result) is None


def test_low_score_below_threshold_returns_none():
    # 0.65 is the documented "garbage match plateau" score — see spec Appendix A
    result = LCSearchResult(top_score=0.65, standards=[_std(0.65)])
    assert should_enrich_with_lc(result) is None


def test_at_threshold_passes():
    result = LCSearchResult(top_score=0.70, standards=[_std(0.70)])
    out = should_enrich_with_lc(result)
    assert out is not None and len(out) == 1


def test_non_k12_returns_none_when_jurisdiction_unknown():
    # Empty jurisdiction → not identifiably K-12
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, jurisdiction="")],
    )
    assert should_enrich_with_lc(result) is None


def test_non_k12_returns_none_when_no_statement_code_and_short_description():
    # No statement code AND description shorter than threshold → not K-12 enough
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, statement_code=None, description="short")],
    )
    assert should_enrich_with_lc(result) is None


def test_k12_with_statement_code_passes_even_with_short_description():
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, statement_code="6.NS.B.2", description="short")],
    )
    out = should_enrich_with_lc(result)
    assert out is not None and len(out) == 1


def test_k12_with_long_description_passes_even_without_statement_code():
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, statement_code=None, description="x" * 80)],
    )
    out = should_enrich_with_lc(result)
    assert out is not None and len(out) == 1


def test_returns_top_three_standards_when_more_present():
    standards = [_std(0.80), _std(0.78), _std(0.75), _std(0.72), _std(0.71)]
    result = LCSearchResult(top_score=0.80, standards=standards)
    out = should_enrich_with_lc(result)
    assert out is not None
    assert len(out) == 3
    assert out[0].score == 0.80
    assert out[1].score == 0.78
    assert out[2].score == 0.75


def test_us_state_jurisdiction_passes_k12_check():
    # K-12 detection accepts known US-state jurisdictions in addition to "Multi-State"
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, jurisdiction="California", statement_code="CCSS.MATH.6.NS.B.2")],
    )
    out = should_enrich_with_lc(result)
    assert out is not None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_learning_commons_gates.py -v
```

Expected: `ImportError: cannot import name 'should_enrich_with_lc'`.

---

### Task 7: Implement `should_enrich_with_lc` and the K-12 heuristic

**Files:**
- Modify: `learning_commons.py` (append to end)

- [ ] **Step 1: Append the gate function and helpers**

```python
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
```

- [ ] **Step 2: Run the gate tests to verify they pass**

```bash
pytest tests/test_learning_commons_gates.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 3: Commit**

```bash
git add learning_commons.py tests/test_learning_commons_gates.py
git commit -m "feat(learning-commons): four-gate enrichment threshold

Implements should_enrich_with_lc per spec §3.3.2: gates on results
returned, score floor (0.70), and K-12 academic confidence
(jurisdiction + statement_code OR description length). Heuristic is
deliberately loose; telemetry on enrichment_skipped: non_k12 will
tighten it post-launch.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Wire `LEARNING_COMMONS_API_KEY` into `.env.example`

**Files:**
- Modify: `.env.example` (append)

- [ ] **Step 1: Read the file**

```bash
cat .env.example
```

- [ ] **Step 2: Append the LC key placeholder**

Append to `.env.example`:

```
# Learning Commons (LC) Knowledge Graph API key. Optional — if not set,
# source-less provisional-map generation runs without LC enrichment.
# Sign up at https://platform.learningcommons.org/login?tab=signup.
LEARNING_COMMONS_API_KEY=
```

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "chore(env): document LEARNING_COMMONS_API_KEY

Optional environment variable consumed by learning_commons.LCClient
for the source-less provisional-map enrichment path. Missing key →
LC enrichment is skipped silently per spec §5.2.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 3: New prompts

### Task 9: Write the threshold-chat prompt smoke test

**Files:**
- Create: `tests/test_app_prompts_threshold_chat.py`

- [ ] **Step 1: Write the test**

```python
"""Smoke tests for app_prompts/threshold-chat-system-v1.txt.

The prompt must contain explicit anti-filler / Socratic-voice / concept-
derived-analogy directives per spec §3.1, §5.1. These are release-blocker
contracts; this test catches accidental edits that drop them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROMPT_PATH = Path(__file__).parent.parent / "app_prompts" / "threshold-chat-system-v1.txt"


@pytest.fixture(scope="module")
def prompt_text() -> str:
    return PROMPT_PATH.read_text()


def test_prompt_file_exists():
    assert PROMPT_PATH.exists(), f"missing: {PROMPT_PATH}"


def test_no_acknowledgment_clause_present(prompt_text: str):
    assert "no acknowledgments" in prompt_text.lower()


def test_no_affirmations_clause_present(prompt_text: str):
    assert "no affirmations" in prompt_text.lower()


def test_no_preambles_clause_present(prompt_text: str):
    assert "no preambles" in prompt_text.lower()


def test_no_consolation_clause_present(prompt_text: str):
    assert "no consolation" in prompt_text.lower()


def test_concept_derived_analogy_clause_present(prompt_text: str):
    # The prompt must instruct the AI to derive analogies from the concept,
    # not template a fixed example.
    text = prompt_text.lower()
    assert "concept" in text and "analog" in text
    assert ("derive" in text or "fresh" in text or "from the concept" in text), (
        "prompt must instruct the AI to derive the analogy from the learner's "
        "concept rather than templating a fixed example"
    )


def test_no_emoji_or_exclamation_clause_present(prompt_text: str):
    text = prompt_text.lower()
    assert "no emoji" in text
    assert "no exclamation" in text


def test_no_actual_filler_in_examples(prompt_text: str):
    """The prompt itself must not contain example outputs that include filler.

    Catches the kind of regression Gemini's review caught in the spec
    (the original "Fair." example).
    """
    forbidden_in_examples = ["fair.", "got it,", "great start", "interesting,"]
    text = prompt_text.lower()
    for token in forbidden_in_examples:
        assert token not in text, (
            f"prompt contains forbidden filler example {token!r} — see spec §3.1"
        )
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_app_prompts_threshold_chat.py -v
```

Expected: `FileNotFoundError` (the prompt file doesn't exist yet).

---

### Task 10: Create `app_prompts/threshold-chat-system-v1.txt`

**Files:**
- Create: `app_prompts/threshold-chat-system-v1.txt`

- [ ] **Step 1: Write the prompt**

```text
You are socratink — a calm, precise, Socratic learning system. You help a
learner capture their starting model of a concept they want to understand.

Your only job in the threshold chat is to ask one question at a time and
listen. The chat is two turns total (turn 1 + turn 2), with at most one
additional analogical scaffold if the learner's reply to turn 2 is thin.

VOICE — these constraints are release-blocker contracts, not preferences:

- No acknowledgments. Do NOT prefix replies with "Fair.", "Got it,", "OK,",
  "Right.", "Sure," or any similar conversational acknowledgment.
- No affirmations. Do NOT say "Great start", "Interesting", "That's a good
  start", "Nice," or any similar evaluative affirmation.
- No preambles. Do NOT start with "Let me think about this", "Here's my
  question", "I'd like to ask", or any wind-up phrase.
- No consolation copy. Do NOT say "That's tricky", "Don't worry", "It's
  okay", or any phrase that frames the learner's response as a struggle
  the system is sympathizing with.
- No emoji.
- No exclamation marks.

Output the question (or analogy + question) ONLY. Plain, complete, Socratic
sentences. Verbs over adjectives. Match the voice of a patient tutor in a
quiet reading room — present, exact, without warmth-as-performance.

TURN STRUCTURE:

Turn 1 is fixed: "What do you want to understand?"

Turn 2: ask the learner to sketch their rough current model of the concept
they named in turn 1. The probe asks for parts and guesses; do NOT
explicitly ask about confusion (confusion is inferred from gaps in the
sketch later). Example shape, not a template:
"Sketch what you think it does — rough is fine. What parts come to mind?"

ANALOGICAL FALLBACK (one bounded extra scaffold, never more):

If the learner's reply to turn 2 is thin (one word, "I don't know", "?",
empty), offer ONE analogical scaffold derived from the learner's concept.
The analogy must be:
- Familiar to a typical adult learner — no domain expertise required to
  follow it
- Mapped cleanly onto the target concept's causal structure
- Generated fresh from the concept, NOT templated. The kitchen-meal
  analogy works for photosynthesis but not for kubernetes; for kubernetes
  use a shipping yard with containers; for cognitive bias use a familiar
  perception illusion. Always derive, never template.

After the fallback question lands and the learner replies (substantive or
not), the chat ends. There is no third real turn.

NEVER:

- Lecture, define, or explain the concept.
- Reveal the answer or the mechanism.
- Ask multiple questions in one turn.
- Continue the conversation past the bounded turns.
- Use "we" — you are socratink (lowercase), the learner is the learner.
```

- [ ] **Step 2: Run the smoke tests to verify they pass**

```bash
pytest tests/test_app_prompts_threshold_chat.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 3: Commit**

```bash
git add app_prompts/threshold-chat-system-v1.txt tests/test_app_prompts_threshold_chat.py
git commit -m "feat(prompts): threshold-chat system prompt v1 + smoke tests

Spec §3.1, §5.1: anti-filler / Socratic-voice / concept-derived-analogy
constraints made explicit at the prompt level so the LLM does not
default to chatbot affirmation patterns. Smoke tests catch accidental
prompt edits that drop the constraints.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Write the generate-from-sketch prompt smoke test

**Files:**
- Create: `tests/test_app_prompts_generate_from_sketch.py`

- [ ] **Step 1: Write the test**

```python
"""Smoke tests for app_prompts/generate-from-sketch-system-v1.txt.

Asserts the prompt file describes the source-less generation contract
correctly per spec §5.1.
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROMPT_PATH = (
    Path(__file__).parent.parent / "app_prompts" / "generate-from-sketch-system-v1.txt"
)


@pytest.fixture(scope="module")
def prompt_text() -> str:
    return PROMPT_PATH.read_text()


def test_prompt_file_exists():
    assert PROMPT_PATH.exists(), f"missing: {PROMPT_PATH}"


def test_lc_context_block_role_described(prompt_text: str):
    text = prompt_text.lower()
    assert "<lc_context>" in text
    assert "grounding" in text
    assert "not authoritative" in text or "never authoritative" in text


def test_favor_learner_sketch_rule_present(prompt_text: str):
    text = prompt_text.lower()
    assert ("favor" in text or "prefer" in text or "trust" in text)
    assert "learner" in text and "sketch" in text


def test_hypothesis_framing_present(prompt_text: str):
    text = prompt_text.lower()
    assert "hypothesis" in text or "hypothesize" in text


def test_no_acknowledgment_filler_in_prompt(prompt_text: str):
    text = prompt_text.lower()
    forbidden = ["fair.", "got it,", "great start", "interesting,"]
    for token in forbidden:
        assert token not in text, f"forbidden filler {token!r} in source-less prompt"


def test_output_schema_referenced(prompt_text: str):
    """The output schema must mirror extract-system-v1.txt — say so."""
    text = prompt_text.lower()
    assert "extract-system-v1" in text or "same json" in text or "same schema" in text
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_app_prompts_generate_from_sketch.py -v
```

Expected: `FileNotFoundError`.

---

### Task 12: Create `app_prompts/generate-from-sketch-system-v1.txt`

**Files:**
- Create: `app_prompts/generate-from-sketch-system-v1.txt`

- [ ] **Step 1: Read the existing extract prompt for reference (do not modify)**

```bash
head -40 app_prompts/extract-system-v1.txt
```

The new prompt must produce JSON that matches the schema described in
`extract-system-v1.txt`. Look at the existing prompt to confirm the schema
fields you must reference.

- [ ] **Step 2: Write the source-less generation prompt**

```text
You are socratink — a calm, precise, Socratic learning system. Your task
in this call is to hypothesize a Provisional concept map for a learner
who has named a concept and sketched their rough current model of it,
WITHOUT providing any source material.

The output is a Provisional map: a hypothesis, never a knowledge claim.
DESIGN.md §3 Screen 2 binds this — the legend is "draft route · ready
for first attempt · locked." Source-less generation makes the hypothesis
weighting STRONGER, not weaker: with no source to extract from, you
hypothesize structure around the learner's sketch using your prior, and
the entire output is a starting hypothesis the learner will test against
in the cold attempt.

INPUT SHAPE:

You receive a user prompt with three parts:

1. <concept>...</concept> — the concept name the learner gave (e.g.,
   "Photosynthesis", "Long division", "Metacognition").

2. <starting_sketch>...</starting_sketch> — the learner's rough current
   model in their own words. THIS IS THE BASELINE. The graph you draft
   must be hypothesis-shaped around this sketch, not from your own
   prior knowledge wearing the sketch as a costume. If the sketch
   contradicts your prior knowledge of the concept, the sketch is what
   the learner is starting from — your hypothesis must reflect what
   THEY are likely to encounter when they cold-attempt, not what an
   ideal student would know.

3. <lc_context>...</lc_context> — OPTIONAL. When present, contains
   1-3 curriculum-aligned standard descriptions from Learning Commons.
   This is grounding context, NOT authoritative. Use it to shape the
   structural skeleton of your hypothesis (what the major nodes are,
   how they relate). When the LC context and the learner's sketch
   diverge, FAVOR THE LEARNER'S SKETCH. The standards are how this
   concept is taught in K-12 academic contexts; the learner may be
   coming at it from a different angle. Never authoritative.

   When <lc_context> is absent, hypothesize from {concept, sketch}
   alone. Do not wish for source you don't have.

OUTPUT:

Same JSON schema as extract-system-v1.txt. The same Pydantic
ProvisionalMap model parses your output. The same closure validators
run on it. Read extract-system-v1.txt for the exact field set —
there is one schema, not two. Backbone, clusters, subnodes, metadata,
identifier grammar (b1, c1, c1_s2), framework references — all the
same.

Differences from extraction:

- metadata.source_title: when source-less, use the concept name.
- metadata.architecture_type: pick the best fit for the concept;
  causal_chain is the most common for procedural concepts, system_
  description for static structures.
- metadata.governing_assumptions: include the learner's sketch as one
  of the governing assumptions, paraphrased. This locks the
  hypothesis to the learner's starting model.
- low_density: True if the sketch was thin OR LC context was absent.
  Signals downstream that the cold attempt should be especially
  scaffolded.

CRITICAL:

- The sketch is the baseline. The graph hypothesizes around it, not
  past it.
- LC context (when present) is curriculum grounding, not authority.
- When in doubt, hypothesize less. A 2-cluster sparse graph the
  learner can attempt is better than a 5-cluster dense graph that
  hallucinates structure the learner has no path into.
- Output JSON only. No prose, no acknowledgments, no preambles.
```

- [ ] **Step 3: Run the smoke tests to verify they pass**

```bash
pytest tests/test_app_prompts_generate_from_sketch.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 4: Commit**

```bash
git add app_prompts/generate-from-sketch-system-v1.txt tests/test_app_prompts_generate_from_sketch.py
git commit -m "feat(prompts): generate-from-sketch system prompt v1 + smoke tests

Spec §5.1: source-less provisional-map generation prompt. Same
output JSON schema as extract-system-v1.txt; differences are in
metadata semantics (source_title from concept name, sketch added
to governing_assumptions, low_density when sketch thin or LC absent).

The prompt makes principle #7 explicit at the LLM level: the sketch
is the baseline, LC context is grounding never authority, hypothesize
less rather than fabricate structure.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 4: Source-less generation function

### Task 13: Write the source-less generation function test

**Files:**
- Create: `tests/test_generate_from_sketch.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for generate_provisional_map_from_sketch."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ai_service import generate_provisional_map_from_sketch
from learning_commons import LCStandard
from llm.client import LLMClient
from llm.types import StructuredLLMResult, TokenUsage
from models.provisional_map import (
    Backbone, Cluster, Metadata, ProvisionalMap, Subnode,
)


def _minimal_provisional_map(concept: str = "Photosynthesis") -> ProvisionalMap:
    return ProvisionalMap(
        metadata=Metadata(
            source_title=concept,
            core_thesis=f"{concept} is a process worth understanding.",
            architecture_type="causal_chain",
            difficulty="medium",
            governing_assumptions=["learner sketched a rough idea"],
            low_density=False,
        ),
        backbone=[
            Backbone(id="b1", label="Stage 1", dependent_clusters=["c1"]),
        ],
        clusters=[
            Cluster(
                id="c1",
                label="First cluster",
                description="A single cluster",
                subnodes=[Subnode(id="c1_s1", label="A", mechanism="x")],
            ),
        ],
        relationships=[],
        frameworks=[],
    )


def _fake_llm_returning(map_obj: ProvisionalMap) -> LLMClient:
    fake = MagicMock(spec=LLMClient)
    fake.generate_structured.return_value = StructuredLLMResult(
        parsed=map_obj,
        usage=TokenUsage(input_tokens=420, output_tokens=180),
        latency_ms=1234,
        model="gemini-2.5-flash",
    )
    return fake


def test_returns_provisional_map():
    result = generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light and somehow make sugar.",
        llm=_fake_llm_returning(_minimal_provisional_map()),
    )
    assert isinstance(result, ProvisionalMap)
    assert result.metadata.source_title == "Photosynthesis"


def test_user_prompt_includes_concept_and_sketch():
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light and somehow make sugar.",
        llm=fake,
    )
    request = fake.generate_structured.call_args.args[0]
    assert "Photosynthesis" in request.user_prompt
    assert "Plants take in light" in request.user_prompt
    assert "<concept>" in request.user_prompt
    assert "<starting_sketch>" in request.user_prompt


def test_user_prompt_omits_lc_context_block_when_none():
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light and make sugar.",
        llm=fake,
        lc_context=None,
    )
    request = fake.generate_structured.call_args.args[0]
    assert "<lc_context>" not in request.user_prompt


def test_user_prompt_includes_lc_context_block_when_provided():
    fake = _fake_llm_returning(_minimal_provisional_map())
    standards = [
        LCStandard(
            case_uuid="u-1", statement_code=None,
            description="Plants use light to make sugars.",
            jurisdiction="Multi-State", score=0.76,
        ),
        LCStandard(
            case_uuid="u-2", statement_code="HS-LS1-5",
            description="Photosynthesis converts light energy to stored chemical energy.",
            jurisdiction="Multi-State", score=0.74,
        ),
    ]
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light and make sugar.",
        llm=fake,
        lc_context=standards,
    )
    request = fake.generate_structured.call_args.args[0]
    assert "<lc_context>" in request.user_prompt
    assert "Plants use light to make sugars" in request.user_prompt
    assert "Photosynthesis converts light energy" in request.user_prompt


def test_uses_correct_system_prompt():
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light.",
        llm=fake,
    )
    request = fake.generate_structured.call_args.args[0]
    # System prompt must come from generate-from-sketch-system-v1.txt
    assert "Provisional concept map" in request.system_prompt
    assert "<starting_sketch>" in request.system_prompt
    assert "<lc_context>" in request.system_prompt


def test_response_schema_is_provisional_map():
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light.",
        llm=fake,
    )
    request = fake.generate_structured.call_args.args[0]
    assert request.response_schema is ProvisionalMap


def test_task_name_distinguishes_from_extraction():
    """Telemetry distinguishes source-less generation from source extraction."""
    fake = _fake_llm_returning(_minimal_provisional_map())
    generate_provisional_map_from_sketch(
        concept="Photosynthesis",
        sketch="Plants take in light.",
        llm=fake,
    )
    request = fake.generate_structured.call_args.args[0]
    assert request.task_name == "provisional_map_from_sketch"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_generate_from_sketch.py -v
```

Expected: `ImportError: cannot import name 'generate_provisional_map_from_sketch' from 'ai_service'`.

---

### Task 14: Implement `generate_provisional_map_from_sketch`

**Files:**
- Modify: `ai_service.py` (add new function near the existing `extract_knowledge_map` definition; do not modify `extract_knowledge_map`)

- [ ] **Step 1: Find the spot to insert**

The function lives near `extract_knowledge_map` (around line 652 in the current file). Read the surrounding code to match style:

```bash
grep -n "extract_knowledge_map\|EXTRACT_PROMPT_PATH\|EXTRACT_PROMPT_VERSION\|EXTRACT_TEMPERATURE\|USER_PROMPT" ai_service.py | head -30
```

You will likely see module-level constants like `EXTRACT_PROMPT_PATH = pathlib.Path("app_prompts/extract-system-v1.txt")` near the top of the file. Add sibling constants for the new prompt below those.

- [ ] **Step 2: Add module-level constants for the new prompt**

Find the block where `EXTRACT_PROMPT_PATH` etc. are defined. Add after that block:

```python
# Source-less generation (spec §5.1).
GENERATE_FROM_SKETCH_PROMPT_PATH = pathlib.Path("app_prompts/generate-from-sketch-system-v1.txt")
GENERATE_FROM_SKETCH_PROMPT_VERSION = "v1"
GENERATE_FROM_SKETCH_TEMPERATURE = 0.4  # slightly higher than extraction; we want a hypothesis, not a transcription
```

If `pathlib` isn't imported, add the import alongside the existing imports.

- [ ] **Step 3: Add the function**

Add this function in `ai_service.py`, immediately after `extract_knowledge_map`:

```python
def generate_provisional_map_from_sketch(
    concept: str,
    sketch: str,
    *,
    llm: LLMClient | None = None,
    api_key: str | None = None,
    lc_context: list["LCStandard"] | None = None,
    telemetry_context: dict | None = None,
) -> ProvisionalMap:
    """Generate a Provisional map from concept name + learner sketch alone.

    Spec §3.3.2, §5.1. The sketch is the baseline; the AI hypothesizes
    structure around it. Optional ``lc_context`` is grounding-only,
    never authoritative.

    Returns a structurally-validated ProvisionalMap. Same Pydantic model
    as extraction; same closure validators; same error semantics.
    """
    from learning_commons import LCStandard  # local import to avoid cycle on module load

    client: LLMClient = llm if llm is not None else build_llm_client(api_key=api_key)

    user_prompt_parts: list[str] = [
        f"<concept>{concept}</concept>",
        f"<starting_sketch>{sketch}</starting_sketch>",
    ]
    if lc_context:
        lc_block_lines = ["<lc_context>"]
        for std in lc_context:
            code = f" [{std.statement_code}]" if std.statement_code else ""
            lc_block_lines.append(f"- {std.jurisdiction}{code}: {std.description}")
        lc_block_lines.append("</lc_context>")
        user_prompt_parts.append("\n".join(lc_block_lines))

    user_prompt = "\n\n".join(user_prompt_parts)

    request = StructuredLLMRequest(
        system_prompt=GENERATE_FROM_SKETCH_PROMPT_PATH.read_text(),
        user_prompt=user_prompt,
        response_schema=ProvisionalMap,
        temperature=GENERATE_FROM_SKETCH_TEMPERATURE,
        task_name="provisional_map_from_sketch",
        prompt_version=GENERATE_FROM_SKETCH_PROMPT_VERSION,
    )
    result = client.generate_structured(request)
    return result.parsed  # type: ignore[return-value]
```

If imports for `LLMClient`, `StructuredLLMRequest`, `build_llm_client`, `ProvisionalMap` aren't already at the top of `ai_service.py` (they are, since `extract_knowledge_map` uses them), no import changes are needed.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/test_generate_from_sketch.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add ai_service.py tests/test_generate_from_sketch.py
git commit -m "feat(ai-service): generate_provisional_map_from_sketch

Source-less provisional-map generation per spec §3.3.2, §5.1. Takes
{concept, sketch} and an optional list of LCStandard for grounding.
Returns the same ProvisionalMap Pydantic model as the existing
extract_knowledge_map path. New prompt at
app_prompts/generate-from-sketch-system-v1.txt; task_name distinguishes
from extraction in telemetry.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 5: Endpoint payload + dispatch + server validation

### Task 15: Write the endpoint dispatch + validation tests

**Files:**
- Create: `tests/test_extract_route_source_optional.py`

- [ ] **Step 1: Write the test**

```python
"""End-to-end tests for the source-optional /api/extract endpoint.

Covers the four truth-table states from spec §3.2:
  | Source | Sketch substantive? | Expected behavior          |
  | ------ | ------------------- | -------------------------- |
  |  yes   |       any           | success via extract path   |
  |  no    |       yes           | success via sketch path    |
  |  yes   |       no            | success via extract path   |
  |  no    |       no            | 422 thin_sketch_no_source  |

Plus: missing concept name → 422 missing_concept.
"""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from models.provisional_map import (
    Backbone, Cluster, Metadata, ProvisionalMap, Subnode,
)


def _minimal_map() -> ProvisionalMap:
    return ProvisionalMap(
        metadata=Metadata(
            source_title="Photosynthesis", core_thesis="A process.",
            architecture_type="causal_chain", difficulty="medium",
            governing_assumptions=[], low_density=False,
        ),
        backbone=[Backbone(id="b1", label="b", dependent_clusters=["c1"])],
        clusters=[Cluster(
            id="c1", label="c", description="d",
            subnodes=[Subnode(id="c1_s1", label="x", mechanism="y")],
        )],
        relationships=[], frameworks=[],
    )


client = TestClient(app)


def test_substantive_sketch_no_source_dispatches_to_sketch_path():
    fake_map = _minimal_map()
    with patch(
        "main.generate_provisional_map_from_sketch",
        return_value=fake_map,
    ) as fake_gen, patch("main.extract_knowledge_map") as fake_extract:
        response = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and carbon dioxide.",
            "source": None,
        })
    assert response.status_code == 200
    assert fake_gen.called, "must call generate_provisional_map_from_sketch"
    assert not fake_extract.called, "must NOT call extract_knowledge_map"


def test_thin_sketch_no_source_returns_422_thin_sketch():
    response = client.post("/api/extract", json={
        "name": "Photosynthesis",
        "starting_sketch": "idk",
        "source": None,
    })
    assert response.status_code == 422
    body = response.json()
    assert body.get("error") == "thin_sketch_no_source"
    assert "more to your sketch" in body.get("message", "").lower() or \
           "attach source" in body.get("message", "").lower()


def test_substantive_sketch_with_source_dispatches_to_extract_path():
    fake_map = _minimal_map()
    with patch("main.extract_knowledge_map", return_value=fake_map) as fake_extract, \
         patch("main.generate_provisional_map_from_sketch") as fake_gen:
        response = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and CO2.",
            "source": {"type": "text", "text": "Photosynthesis is the process by which..."},
        })
    assert response.status_code == 200
    assert fake_extract.called
    assert not fake_gen.called


def test_thin_sketch_with_source_dispatches_to_extract_path():
    """Thin sketch is OK when source carries the structural seed."""
    fake_map = _minimal_map()
    with patch("main.extract_knowledge_map", return_value=fake_map) as fake_extract, \
         patch("main.generate_provisional_map_from_sketch") as fake_gen:
        response = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "idk",
            "source": {"type": "text", "text": "Photosynthesis is the process by which..."},
        })
    assert response.status_code == 200
    assert fake_extract.called
    assert not fake_gen.called


def test_missing_concept_returns_422_missing_concept():
    response = client.post("/api/extract", json={
        "name": "",
        "starting_sketch": "Plants take in light and make sugar from water and CO2.",
        "source": None,
    })
    assert response.status_code == 422
    assert response.json().get("error") == "missing_concept"


def test_whitespace_only_concept_returns_422_missing_concept():
    response = client.post("/api/extract", json={
        "name": "   \n\t  ",
        "starting_sketch": "Plants take in light and make sugar from water and CO2.",
        "source": None,
    })
    assert response.status_code == 422
    assert response.json().get("error") == "missing_concept"


def test_legacy_text_only_payload_still_works():
    """Back-compat: the old {text, api_key} payload still hits extract path.

    Plan B will deprecate this once the new frontend ships, but during
    rollout the old client must keep working.
    """
    fake_map = _minimal_map()
    with patch("main.extract_knowledge_map", return_value=fake_map) as fake_extract:
        response = client.post("/api/extract", json={
            "text": "Photosynthesis is the process by which...",
        })
    assert response.status_code == 200
    assert fake_extract.called


def test_lc_enrichment_is_attempted_for_source_less_path():
    """When source-less, LC search is attempted and result feeds into generation."""
    fake_map = _minimal_map()
    from learning_commons import LCSearchResult, LCStandard
    fake_lc_result = LCSearchResult(
        top_score=0.75,
        standards=[LCStandard(
            case_uuid="u", statement_code="HS-LS1-5",
            description="x" * 60, jurisdiction="Multi-State", score=0.75,
        )],
    )
    with patch("main.generate_provisional_map_from_sketch", return_value=fake_map) as fake_gen, \
         patch("main.LCClient") as fake_lc_cls:
        fake_lc_cls.return_value.search_concept.return_value = fake_lc_result
        response = client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and CO2.",
            "source": None,
        })
    assert response.status_code == 200
    fake_gen.assert_called_once()
    # lc_context kwarg must be the top standards list (gate passed)
    kwargs = fake_gen.call_args.kwargs
    assert kwargs.get("lc_context") is not None
    assert len(kwargs["lc_context"]) >= 1
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_extract_route_source_optional.py -v
```

Expected: most tests fail with `422` for the legacy field shape (because `name` doesn't exist on the current `ExtractRequest`), or 500s, or import errors.

---

### Task 16: Reshape `ExtractRequest` and add server-side validation + dispatch

**Files:**
- Modify: `main.py` — replace `ExtractRequest` definition (around L192) and the `/api/extract` handler (around L322).

- [ ] **Step 1: Update `ExtractRequest` to accept the new payload shape**

Find the existing `class ExtractRequest(BaseModel):` block in `main.py`. Replace it with:

```python
class SourceAttachment(BaseModel):
    """Optional source material attached to a concept submission."""
    type: Literal["text", "url", "file"]
    text: str | None = Field(None, max_length=500_000)
    url: str | None = Field(None, max_length=2_000)
    filename: str | None = Field(None, max_length=255)


class ExtractRequest(BaseModel):
    """Concept-creation submission.

    Two payload shapes are accepted:

    NEW (Plan A — conversational concept creation):
      {name, starting_sketch, source, api_key?}
      where source is None or a SourceAttachment.

    LEGACY (back-compat for the existing form-based client during rollout):
      {text, api_key?}
      Equivalent to {name=None, starting_sketch=None, source={type:"text",text:...}}.

    Server-side validation in /api/extract enforces the spec §3.2
    substantiveness rule: source-less submits require a substantive sketch.
    """
    # New shape
    name: str | None = Field(None, max_length=200)
    starting_sketch: str | None = Field(None, max_length=10_000)
    source: SourceAttachment | None = None
    # Legacy back-compat
    text: str | None = Field(None, max_length=500_000)
    # Common
    api_key: str | None = Field(None, max_length=200)
```

You will need `from typing import Literal` if it isn't already imported.

- [ ] **Step 2: Add the dispatch helper at module level**

Add this function in `main.py`, near the other helpers (above the route handlers):

```python
def _resolve_extract_path(req: ExtractRequest) -> dict:
    """Decide which generation path the request takes, with server-side validation.

    Returns a dict shaped like one of:
      {"path": "extract", "text": str}
      {"path": "from_sketch", "name": str, "sketch": str}
      {"path": "error", "status": 422, "error": str, "message": str}

    Spec §3.2 truth table is enforced here as defense in depth (the client
    also disables CTA but we never trust client gates).
    """
    from models.sketch_validation import is_substantive_sketch

    # Legacy {text} payload — back-compat path. Bypasses the new shape entirely.
    if req.text is not None and req.name is None and req.source is None:
        if not req.text.strip():
            return {"path": "error", "status": 422,
                    "error": "missing_text", "message": "Source text required."}
        return {"path": "extract", "text": req.text}

    # New shape: name is mandatory
    name = (req.name or "").strip()
    if not name:
        return {"path": "error", "status": 422,
                "error": "missing_concept", "message": "Concept name required."}

    sketch = (req.starting_sketch or "").strip()
    has_source = req.source is not None and (
        (req.source.type == "text" and (req.source.text or "").strip())
        or (req.source.type == "url" and (req.source.url or "").strip())
        or (req.source.type == "file" and (req.source.text or "").strip())
    )
    sketch_ok = is_substantive_sketch(sketch)

    if has_source:
        # Source path: collect source text into the existing extract pipeline.
        source_text = (req.source.text or "").strip()
        if not source_text and req.source.type == "url":
            # URL fetching happens elsewhere; out-of-scope for this dispatcher.
            # Caller routes to the existing /api/extract-url path or fetches first.
            return {"path": "error", "status": 422,
                    "error": "url_source_unsupported_here",
                    "message": "URL sources go through /api/extract-url."}
        return {"path": "extract", "text": source_text}

    if not sketch_ok:
        # Spec §3.2 row 1: thin sketch + no source → block.
        return {"path": "error", "status": 422,
                "error": "thin_sketch_no_source",
                "message": "Add more to your sketch, or attach source material — either path opens the build."}

    return {"path": "from_sketch", "name": name, "sketch": sketch}
```

- [ ] **Step 3: Update the `/api/extract` handler to use the dispatcher**

Find the existing `@app.post("/api/extract")` handler (around L322). Modify it to call `_resolve_extract_path` and dispatch:

```python
@app.post("/api/extract")
def extract(req: ExtractRequest):
    from learning_commons import LCClient, should_enrich_with_lc

    decision = _resolve_extract_path(req)

    if decision["path"] == "error":
        # Server-side validation rejection — surfaces back to the client which
        # renders `message` in the same chip footer the client gate would have used.
        logger.info(
            "concept_create.build_blocked",
            extra={"reason": decision["error"], "origin": "server"},
        )
        raise HTTPException(status_code=decision["status"], detail={
            "error": decision["error"],
            "message": decision["message"],
        })

    try:
        if decision["path"] == "from_sketch":
            # Source-less generation: query LC for grounding context, gate it.
            lc_result = None
            try:
                lc_result = LCClient().search_concept(decision["name"])
            except Exception:
                logger.exception("lc_query_unexpected")
            lc_context = should_enrich_with_lc(lc_result)
            if lc_context is None:
                reason = "key_missing" if lc_result is None and not os.environ.get(
                    "LEARNING_COMMONS_API_KEY") else (
                    "no_results" if lc_result is None or not lc_result.standards
                    else "low_score" if lc_result.top_score < 0.70
                    else "non_k12"
                )
                logger.info("concept_create.lc.enrichment_skipped", extra={"reason": reason})
            else:
                logger.info("concept_create.lc.enrichment_applied",
                            extra={"standards_count": len(lc_context)})

            provisional_map = generate_provisional_map_from_sketch(
                concept=decision["name"],
                sketch=decision["sketch"],
                lc_context=lc_context,
                api_key=req.api_key,
            )
        else:  # decision["path"] == "extract"
            from source_intake import build_imported_source  # if used today; otherwise inline req.text
            src = build_imported_source(decision["text"])
            provisional_map = extract_knowledge_map(src.text, api_key=req.api_key)

        return {"provisional_map": provisional_map.model_dump()}

    except LLMMissingKeyError as err:
        logger.warning("extract: LLMMissingKeyError: %s", err)
        raise HTTPException(status_code=401, detail="An API key is required.")
    except LLMRateLimitError as err:
        logger.warning("extract: LLMRateLimitError: %s", err)
        raise HTTPException(status_code=429, detail="Extraction service is throttled. Try again shortly.")
    except LLMValidationError as err:
        logger.warning("extract: LLMValidationError: %s", err)
        raise HTTPException(status_code=422, detail="The model returned an unexpected shape. Try again.")
    except LLMServiceError as err:
        logger.warning("extract: LLMServiceError: %s", err)
        raise HTTPException(status_code=502, detail="The extraction service had a hiccup. Try again.")
    except LLMClientError as err:
        logger.warning("extract: LLMClientError: %s", err)
        raise HTTPException(status_code=500, detail="Extraction client error.")
    except ValueError as err:
        logger.warning("extract: structural validation failed: %s", err)
        raise HTTPException(status_code=422, detail="The generated map failed structural validation. Try again.")
    except Exception:
        logger.exception("Unexpected failure in /api/extract")
        raise HTTPException(status_code=500, detail="Unexpected server error during extraction.")
```

NOTE: the existing extract handler has its own version of `src = build_imported_source(...)` or similar. Read the existing handler before editing, and preserve whatever the current source-text intake path does. Do NOT change the source-attached extraction behavior; only re-route around it via the dispatcher.

Also: `LLMClientError`, `LLMMissingKeyError`, etc. are already imported at the top of `main.py`; if not, import them from `llm.errors`.

`generate_provisional_map_from_sketch` must be imported at the top of `main.py`:

```python
from ai_service import (
    extract_knowledge_map,
    generate_provisional_map_from_sketch,
    # ... other existing imports
)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/test_extract_route_source_optional.py -v
```

Expected: all 8 tests pass.

If `test_legacy_text_only_payload_still_works` fails because the existing extract handler does extra steps (URL detection, source-intake normalization), make sure the dispatcher's `extract` path produces a `req` shape the existing handler can still consume. The legacy path must be 100% unchanged in behavior.

- [ ] **Step 5: Run the full test suite to verify no regressions**

```bash
pytest tests/ --ignore=tests/e2e -x
```

Expected: all existing tests still pass. The legacy `tests/test_extract_route.py` and `tests/test_extract_route_error_mapping.py` are the canaries — if either breaks, the dispatcher is dropping behavior.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_extract_route_source_optional.py
git commit -m "feat(api): source-optional /api/extract dispatch + server validation

Spec §3.2 truth-table enforcement at the route layer (defense in
depth — client gates are UX, never trust). New ExtractRequest shape
accepts {name, starting_sketch, source} with the legacy {text}
shape preserved for back-compat during frontend rollout.

Dispatch:
- {text} only → legacy extract path (unchanged)
- name + source → extract path
- name + substantive sketch + no source → source-less generation
  with optional LC enrichment via the four-gate threshold
- name + thin sketch + no source → 422 thin_sketch_no_source
- empty name → 422 missing_concept

422 responses surface message in shape the frontend renders directly
in the chip footer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 6: Backend telemetry

### Task 17: Write the telemetry tests

**Files:**
- Create: `tests/test_concept_create_telemetry.py`

- [ ] **Step 1: Write the test**

```python
"""Tests that the source-optional /api/extract emits the spec §5.4
backend telemetry events.
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from models.provisional_map import (
    Backbone, Cluster, Metadata, ProvisionalMap, Subnode,
)


def _minimal_map() -> ProvisionalMap:
    return ProvisionalMap(
        metadata=Metadata(
            source_title="Photosynthesis", core_thesis="A process.",
            architecture_type="causal_chain", difficulty="medium",
            governing_assumptions=[], low_density=False,
        ),
        backbone=[Backbone(id="b1", label="b", dependent_clusters=["c1"])],
        clusters=[Cluster(
            id="c1", label="c", description="d",
            subnodes=[Subnode(id="c1_s1", label="x", mechanism="y")],
        )],
        relationships=[], frameworks=[],
    )


client = TestClient(app)


def _records_for(caplog, event_name: str) -> list[logging.LogRecord]:
    return [
        r for r in caplog.records
        if r.getMessage() == event_name or getattr(r, "msg", None) == event_name
    ]


def test_build_blocked_emitted_for_thin_sketch_no_source(caplog):
    caplog.set_level(logging.INFO)
    response = client.post("/api/extract", json={
        "name": "Photosynthesis",
        "starting_sketch": "idk",
        "source": None,
    })
    assert response.status_code == 422
    blocked = _records_for(caplog, "concept_create.build_blocked")
    assert blocked, "must emit concept_create.build_blocked"
    extras = blocked[0].__dict__
    assert extras.get("reason") == "thin_sketch_no_source"
    assert extras.get("origin") == "server"


def test_build_blocked_emitted_for_missing_concept(caplog):
    caplog.set_level(logging.INFO)
    response = client.post("/api/extract", json={
        "name": "",
        "starting_sketch": "Plants take in light and make sugar from water and CO2.",
        "source": None,
    })
    assert response.status_code == 422
    blocked = _records_for(caplog, "concept_create.build_blocked")
    assert blocked
    assert blocked[0].__dict__.get("reason") == "missing_concept"


def test_lc_enrichment_skipped_emitted_when_lc_returns_nothing(caplog):
    caplog.set_level(logging.INFO)
    fake_map = _minimal_map()
    with patch("main.LCClient") as fake_lc_cls, \
         patch("main.generate_provisional_map_from_sketch", return_value=fake_map):
        fake_lc_cls.return_value.search_concept.return_value = None
        client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and CO2.",
            "source": None,
        })
    skipped = _records_for(caplog, "concept_create.lc.enrichment_skipped")
    assert skipped, "must emit lc.enrichment_skipped when LC returns None"


def test_ai_call_emitted_after_generation(caplog):
    """The ai_call event must fire with stage/model/tokens/latency for
    every successful generation."""
    caplog.set_level(logging.INFO)
    fake_map = _minimal_map()
    with patch("main.generate_provisional_map_from_sketch", return_value=fake_map), \
         patch("main.LCClient") as fake_lc_cls:
        fake_lc_cls.return_value.search_concept.return_value = None
        client.post("/api/extract", json={
            "name": "Photosynthesis",
            "starting_sketch": "Plants take in light and make sugar from water and CO2.",
            "source": None,
        })
    ai_calls = _records_for(caplog, "concept_create.ai_call")
    assert ai_calls, "must emit concept_create.ai_call"
    extras = ai_calls[0].__dict__
    assert extras.get("stage") in (
        "generation_pure", "generation_lc_enriched",
    )
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_concept_create_telemetry.py -v
```

Expected: `test_build_blocked_emitted_for_thin_sketch_no_source` and `test_build_blocked_emitted_for_missing_concept` likely already pass (we wired those in Task 16). The `lc.enrichment_skipped` test depends on Task 16 too. The `ai_call` test will fail — we haven't wired that event yet.

---

### Task 18: Wire `concept_create.ai_call` after generation

**Files:**
- Modify: `main.py` — add a small wrapper around `generate_provisional_map_from_sketch` and the legacy extraction call.

- [ ] **Step 1: Add the telemetry helper at module level**

Add near the top of `main.py` (after imports):

```python
def _emit_ai_call(*, stage: str, model: str, latency_ms: int,
                  input_tokens: int = 0, output_tokens: int = 0) -> None:
    """Emit concept_create.ai_call telemetry per spec §5.4."""
    # Cost estimation: rough per-1k-token rates. Update when model pricing
    # changes. Better than nothing for budget visibility.
    cost_per_1k_in = 0.000125  # gemini-2.5-flash input per 1k
    cost_per_1k_out = 0.000375
    cost_usd_est = round(
        (input_tokens / 1000.0) * cost_per_1k_in
        + (output_tokens / 1000.0) * cost_per_1k_out,
        6,
    )
    logger.info(
        "concept_create.ai_call",
        extra={
            "stage": stage,
            "model": model,
            "tokens_in": input_tokens,
            "tokens_out": output_tokens,
            "latency_ms": latency_ms,
            "cost_usd_est": cost_usd_est,
        },
    )
```

- [ ] **Step 2: Wrap the source-less generation call**

Inside the `/api/extract` handler, replace the call site of `generate_provisional_map_from_sketch` with a wrapped version. The wrapping needs the LLM result's `latency_ms` + `usage` — easiest is to thread the telemetry from inside the function:

The cleanest route is to have `generate_provisional_map_from_sketch` accept an optional `on_call_complete` callback. Add this parameter:

```python
# In ai_service.py, modify generate_provisional_map_from_sketch:

def generate_provisional_map_from_sketch(
    concept: str,
    sketch: str,
    *,
    llm: LLMClient | None = None,
    api_key: str | None = None,
    lc_context: list["LCStandard"] | None = None,
    telemetry_context: dict | None = None,
    on_call_complete: Callable[[StructuredLLMResult], None] | None = None,
) -> ProvisionalMap:
    # ... unchanged setup ...
    result = client.generate_structured(request)
    if on_call_complete is not None:
        on_call_complete(result)
    return result.parsed
```

Add `from typing import Callable` to `ai_service.py` imports if not present.

- [ ] **Step 3: Use the callback in `main.py`**

In the `/api/extract` handler, replace:

```python
provisional_map = generate_provisional_map_from_sketch(
    concept=decision["name"],
    sketch=decision["sketch"],
    lc_context=lc_context,
    api_key=req.api_key,
)
```

with:

```python
def _on_sketch_call(result):
    _emit_ai_call(
        stage="generation_lc_enriched" if lc_context else "generation_pure",
        model=result.model,
        latency_ms=result.latency_ms,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
    )

provisional_map = generate_provisional_map_from_sketch(
    concept=decision["name"],
    sketch=decision["sketch"],
    lc_context=lc_context,
    api_key=req.api_key,
    on_call_complete=_on_sketch_call,
)
```

Also wire the same shape for the source-attached extract path:

The existing `extract_knowledge_map` doesn't have an `on_call_complete` parameter. Either add it (mirrors the new pattern) or wrap the call:

```python
# In ai_service.py, similarly add to extract_knowledge_map:
def extract_knowledge_map(
    raw_text: str,
    *,
    llm: LLMClient | None = None,
    api_key: str | None = None,
    telemetry_context: dict | None = None,
    on_call_complete: Callable[[StructuredLLMResult], None] | None = None,
) -> ProvisionalMap:
    # ... unchanged ...
    result = client.generate_structured(request)
    if on_call_complete is not None:
        on_call_complete(result)
    return result.parsed
```

And in `main.py`'s extract path:

```python
def _on_extract_call(result):
    _emit_ai_call(
        stage="generation_extract",
        model=result.model,
        latency_ms=result.latency_ms,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
    )
provisional_map = extract_knowledge_map(
    src.text, api_key=req.api_key, on_call_complete=_on_extract_call,
)
```

- [ ] **Step 4: Run the telemetry tests to verify they pass**

```bash
pytest tests/test_concept_create_telemetry.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Run full suite to verify no regressions**

```bash
pytest tests/ --ignore=tests/e2e -x
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add main.py ai_service.py tests/test_concept_create_telemetry.py
git commit -m "feat(telemetry): concept_create.build_blocked + ai_call events

Spec §5.4. build_blocked already emitted from server-side validation
(Task 16); this commit adds ai_call telemetry covering the actual
model-call cost per concept created. Stage distinguishes generation_
extract / generation_pure / generation_lc_enriched. Includes a rough
cost_usd_est based on gemini-2.5-flash pricing — better than nothing
for budget visibility; update when pricing changes.

Both extract_knowledge_map and generate_provisional_map_from_sketch
now accept an on_call_complete callback so the route handler can
observe the LLM result without the AI service layer knowing about
HTTP-route-level telemetry events.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 7: Backend acceptance smoke

### Task 19: Curl-based smoke for source-less submit

**Files:** none (this is a manual smoke step + a recorded transcript)

- [ ] **Step 1: Start the dev server in the background**

```bash
bash scripts/dev.sh &
DEV_PID=$!
sleep 3
```

- [ ] **Step 2: Curl source-less substantive submit**

```bash
curl -sS -X POST http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Photosynthesis",
    "starting_sketch": "Plants take in light and somehow make sugar. Not sure where the water goes.",
    "source": null
  }' | python -m json.tool | head -40
```

Expected: a 200 response with `{"provisional_map": {...}}`. The `provisional_map.metadata.source_title` should be `"Photosynthesis"`. The `provisional_map.metadata.governing_assumptions` should mention the learner's sketch (or paraphrase of it).

- [ ] **Step 3: Curl source-less thin sketch (must be rejected)**

```bash
curl -sS -X POST http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Photosynthesis",
    "starting_sketch": "idk",
    "source": null
  }' -o /tmp/thin.json -w "HTTP %{http_code}\n"
cat /tmp/thin.json
```

Expected: `HTTP 422` and body `{"detail": {"error": "thin_sketch_no_source", "message": "Add more to your sketch, or attach source material — either path opens the build."}}`.

- [ ] **Step 4: Curl source-attached path (must be unchanged from today)**

```bash
curl -sS -X POST http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Photosynthesis is the process by which plants convert light energy from the sun into chemical energy stored in glucose. It occurs in the chloroplasts of plant cells, primarily in the leaves. The overall reaction takes carbon dioxide and water as inputs and produces glucose and oxygen as outputs."
  }' | python -m json.tool | head -40
```

Expected: a 200 response with `{"provisional_map": {...}}` shaped as today's extraction. Confirms back-compat for the legacy payload.

- [ ] **Step 5: Stop the dev server**

```bash
kill $DEV_PID
```

- [ ] **Step 6: Record the smoke results**

Write the three curl commands and their (redacted, summarized) outputs into the implementation PR description so reviewers can see the backend is alive end-to-end.

This is a manual checkpoint — no commit. If any of the three curls produced unexpected results, debug before moving forward to Plan B.

---

## Self-Review

After completing all tasks, run the spec coverage check:

| Spec §3.3.2 four gates | Phase 2 (Tasks 6-7) — ✓ |
| Spec §5.1 source-less function | Phase 4 (Tasks 13-14) — ✓ |
| Spec §5.1 prompt constraints | Phase 3 (Tasks 9-12) — ✓ |
| Spec §5.2 LC client | Phase 2 (Tasks 4-5) — ✓ |
| Spec §5.3 endpoint shape | Phase 5 (Tasks 15-16) — ✓ |
| Spec §5.3 server-side validation | Phase 5 (Task 16) — ✓ |
| Spec §5.3 shared substantiveness helper | Phase 1 (Tasks 1-3) — ✓ |
| Spec §5.4 build_blocked event | Phase 5 (Task 16) — ✓ |
| Spec §5.4 ai_call event | Phase 6 (Tasks 17-18) — ✓ |
| Spec §5.4 lc.enrichment_skipped | Phase 5 (Task 16) — ✓ |
| Spec §5.4 lc.enrichment_applied | Phase 5 (Task 16) — ✓ |
| Spec §3.2 truth table | Phase 5 (Task 15 tests) — ✓ |

**Spec sections NOT in this plan (intentionally — go to Plan B / Plan C):**

- §3.1 chat surface (frontend)
- §3.2 summary card UI (frontend)
- §3.2 state-dependent CTA copy (frontend)
- §4.1, 4.2, 4.3, 4.4 frontend file changes
- §5.4 chat / summary / source telemetry events (frontend)
- §8 acceptance criteria #6-#10 (require frontend)
- §9 step 4 (DESIGN.md updates)

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-03-conversational-concept-creation-backend.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Each task in this plan is bite-sized; subagent dispatch keeps context windows tight and surfaces test failures faster.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Lower coordination overhead but main-conversation context grows.

**Suggestion: option 1.** This plan has 19 tasks across 7 phases. The natural review checkpoints are at phase boundaries — after each phase commits, review the diff before kicking off the next phase. Subagent dispatch handles that rhythm cleanly.

After Plan A lands on dev, **Plan B (frontend)** is the next plan to write. It will assume the new `/api/extract` payload + the substantiveness parity fixture exist, and will port the JS implementation of `is_substantive_sketch` against the same fixture. Plan C (acceptance + docs) lands after Plan B.
