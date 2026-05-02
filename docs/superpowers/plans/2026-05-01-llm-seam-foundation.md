# LLM Seam Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `llm/` seam so application code asks for validated cognitive artifacts (Pydantic models), never for "Gemini output." Migrate `extract_knowledge_map` through the seam as proof.

**Architecture:** New `llm/` package with three layers: (1) typed request/result dataclasses + normalized error hierarchy; (2) `LLMAdapter` Protocol that providers satisfy and a concrete `LLMClient` that wraps an adapter with retry policy + telemetry; (3) `GeminiAdapter` that translates `google-genai` SDK quirks into the normalized shape. An architectural isolation test enforces that no application code outside `llm/gemini_adapter.py` imports the Gemini SDK. `ProvisionalMap` Pydantic model becomes the typed return shape of extraction.

**Tech Stack:** Python 3.x, FastAPI, `google-genai` SDK (the modern `google.genai` package, not legacy `google.generativeai`), Pydantic 2, pytest.

**Spec reference:** `docs/superpowers/specs/2026-05-01-foundation-design.md` — first execution sweep covers spec sections 5.1, 5.2, 5.3, plus enough of 5.4/5.6 to validate the seam end-to-end.

---

## File Structure

**New package: `llm/`**

| File | Responsibility | LOC est |
|---|---|---|
| `llm/__init__.py` | Public API re-exports (`LLMClient`, `StructuredLLMRequest`, `StructuredLLMResult`, `TokenUsage`, error classes, `build_llm_client`). The single import surface for application code. | ~25 |
| `llm/types.py` | Request, Result, TokenUsage frozen dataclasses. No imports from other `llm/` modules. | ~50 |
| `llm/errors.py` | Normalized exception hierarchy: `LLMError` base, `LLMMissingKeyError`, `LLMRateLimitError`, `LLMServiceError`, `LLMValidationError`. | ~25 |
| `llm/adapter.py` | `LLMAdapter` Protocol — single primitive `_call_once(request) -> result` or raises a normalized error. `runtime_checkable` so tests can verify any class satisfies it. | ~30 |
| `llm/client.py` | Concrete `LLMClient` wrapping an `LLMAdapter`. Owns the retry loop, exponential backoff on `LLMRateLimitError`/`LLMServiceError`, structured logging per call, latency measurement. Public `generate_structured(request)` method. | ~100 |
| `llm/gemini_adapter.py` | `GeminiAdapter(LLMAdapter)`. Translates `StructuredLLMRequest` → `client.models.generate_content(...)` with `response_schema` + `response_mime_type`. Maps `google.genai.errors.APIError` codes to normalized errors (429 → RateLimit, 503/500 → Service, anything else → Service). Validates `response.parsed` is the requested Pydantic class; raises `LLMValidationError` if missing/wrong type. | ~150 |
| `llm/factory.py` | `build_llm_client(api_key=None) -> LLMClient` — reads `LLM_PROVIDER` (default `gemini`), `LLM_MODEL` (default `gemini-2.5-flash`), and the appropriate per-provider API key env var. Constructs the right adapter and wraps it in `LLMClient`. | ~40 |

**New module: `models/` (or single file)**

| File | Responsibility | LOC est |
|---|---|---|
| `models/__init__.py` | Re-exports `ProvisionalMap`, identifier types. | ~10 |
| `models/identifiers.py` | `BackboneId`, `ClusterId`, `SubnodeId` typed wrappers + `parse_id(s) -> IdKind` parser. Rejects malformed IDs. | ~70 |
| `models/provisional_map.py` | `ProvisionalMap` Pydantic model + Pydantic validators for reference closure (every subnode → existing cluster; every cluster → existing backbone). | ~120 |

**New tests**

| File | What it tests |
|---|---|
| `tests/test_llm_types.py` | Request/result/usage dataclasses construct, are frozen, have correct defaults |
| `tests/test_llm_errors.py` | Inheritance graph; each error is catchable as `LLMError` |
| `tests/test_llm_adapter_protocol.py` | A fake adapter class satisfies `LLMAdapter` via `isinstance` (runtime_checkable) |
| `tests/test_llm_client.py` | Happy path; retry on RateLimit; no retry on Validation; logging emits per call; latency measured |
| `tests/test_gemini_adapter.py` | Missing key → MissingKey; 429 → RateLimit; 503/500 → Service; bad parsed → Validation; happy path returns StructuredLLMResult with parsed Pydantic + token counts |
| `tests/test_llm_seam_isolation.py` | **Architectural invariant**: no `.py` outside `llm/gemini_adapter.py` imports `google.genai` or `google.generativeai` |
| `tests/test_provisional_map.py` | Identifier parsing, valid map parses, invalid map raises, closure violation raises |
| `tests/test_extract_knowledge_map_migration.py` | Extraction via fake `LLMClient` returns `ProvisionalMap` instance |

**Modified files**

| File | Change |
|---|---|
| `ai_service.py` | `extract_knowledge_map` rewrites to use `LLMClient.generate_structured(...)` returning a `ProvisionalMap`. Removes `_clean_response`, `_log_extract_failure`, the local `_validate_knowledge_map` (inline-shape version), and the local `MissingAPIKeyError`/`GeminiRateLimitError`/`GeminiServiceError` for the extract path. Drill and repair-reps stay on the legacy path for now (separate task). |
| `main.py` | `/api/extract` route updated to catch normalized `llm.errors.*` and map them to HTTP statuses. Uses `build_llm_client(api_key=req.api_key)` to construct a client per request. |

---

## Task 1: `llm/types.py` — Request, Result, TokenUsage

**Files:**
- Create: `llm/__init__.py` (placeholder)
- Create: `llm/types.py`
- Create: `tests/test_llm_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_types.py
import pytest
from pydantic import BaseModel

from llm.types import StructuredLLMRequest, StructuredLLMResult, TokenUsage


class _DummySchema(BaseModel):
    foo: str


def test_request_constructs_with_required_and_defaults():
    req = StructuredLLMRequest(
        system_prompt="sys",
        user_prompt="user",
        response_schema=_DummySchema,
    )
    assert req.system_prompt == "sys"
    assert req.user_prompt == "user"
    assert req.response_schema is _DummySchema
    assert req.temperature == 0.0
    assert req.max_retries == 2
    assert req.task_name is None
    assert req.prompt_version is None


def test_request_is_frozen():
    req = StructuredLLMRequest(
        system_prompt="s", user_prompt="u", response_schema=_DummySchema
    )
    with pytest.raises(Exception):
        req.temperature = 0.5  # frozen dataclass disallows mutation


def test_token_usage_constructs():
    usage = TokenUsage(input_tokens=100, output_tokens=50)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50


def test_result_constructs():
    parsed = _DummySchema(foo="bar")
    usage = TokenUsage(input_tokens=10, output_tokens=20)
    result = StructuredLLMResult(
        parsed=parsed,
        raw_text='{"foo": "bar"}',
        usage=usage,
        model="gemini-2.5-flash",
        provider="gemini",
        latency_ms=123.4,
    )
    assert result.parsed is parsed
    assert result.usage.input_tokens == 10
    assert result.provider == "gemini"
    assert result.raw_provider_metadata is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_types.py -v`
Expected: `ModuleNotFoundError: No module named 'llm'`

- [ ] **Step 3: Create empty `llm/__init__.py`**

```python
# llm/__init__.py
```

(Empty for now; populated in Task 6.)

- [ ] **Step 4: Implement `llm/types.py`**

```python
# llm/types.py
"""Request / result / usage types for the LLM seam.

These are the contract between application code and any LLM provider.
The application sees only these shapes, never provider-native objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class StructuredLLMRequest:
    """A request for a validated cognitive artifact.

    The application asks for a Pydantic model; the adapter returns one
    or raises a normalized error. The application never sees raw text
    unless it explicitly inspects `StructuredLLMResult.raw_text`.
    """

    system_prompt: str
    user_prompt: str
    response_schema: type[BaseModel]
    temperature: float = 0.0
    max_retries: int = 2
    task_name: str | None = None
    prompt_version: str | None = None


@dataclass(frozen=True)
class TokenUsage:
    """Provider-agnostic token usage."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class StructuredLLMResult:
    """A validated cognitive artifact, plus the metadata to debug it.

    `parsed` is already a Pydantic instance of the requested schema.
    `raw_text` is preserved for logging / golden-fixture refresh.
    `raw_provider_metadata` is an escape hatch — provider-specific data
    that would otherwise pollute the normalized shape.
    """

    parsed: BaseModel
    raw_text: str
    usage: TokenUsage
    model: str
    provider: str
    latency_ms: float
    raw_provider_metadata: dict[str, Any] | None = None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_llm_types.py -v`
Expected: 4 PASS

- [ ] **Step 6: Commit**

```bash
git add llm/__init__.py llm/types.py tests/test_llm_types.py
git commit -m "feat(llm): add typed request/result/usage dataclasses"
```

---

## Task 2: `llm/errors.py` — normalized exception hierarchy

**Files:**
- Create: `llm/errors.py`
- Create: `tests/test_llm_errors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_errors.py
import pytest

from llm.errors import (
    LLMError,
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)


def test_all_subclasses_inherit_from_llm_error():
    for cls in (
        LLMMissingKeyError,
        LLMRateLimitError,
        LLMServiceError,
        LLMValidationError,
    ):
        assert issubclass(cls, LLMError)
        assert issubclass(cls, Exception)


def test_subclasses_are_distinct():
    classes = {
        LLMMissingKeyError,
        LLMRateLimitError,
        LLMServiceError,
        LLMValidationError,
    }
    assert len(classes) == 4
    # And they don't share parents (besides LLMError):
    assert not issubclass(LLMValidationError, LLMServiceError)
    assert not issubclass(LLMRateLimitError, LLMServiceError)


def test_validation_error_carries_message_and_optional_raw_text():
    err = LLMValidationError("bad shape", raw_text='{"oops":')
    assert "bad shape" in str(err)
    assert err.raw_text == '{"oops":'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_errors.py -v`
Expected: `ImportError: cannot import name 'LLMError' from 'llm.errors'`

- [ ] **Step 3: Implement `llm/errors.py`**

```python
# llm/errors.py
"""Normalized exception hierarchy for the LLM seam.

Application code catches these. Adapter code raises these. The mapping
from provider-specific exceptions to these lives inside each adapter.
"""
from __future__ import annotations


class LLMError(Exception):
    """Base for all errors raised through the LLM seam."""


class LLMMissingKeyError(LLMError):
    """The configured provider has no API key."""


class LLMRateLimitError(LLMError):
    """The provider rate-limited the request (e.g., Gemini 429)."""


class LLMServiceError(LLMError):
    """The provider returned a transport-level / upstream failure
    (Gemini 5xx, network timeouts, malformed transport response).
    Distinct from LLMValidationError — the model produced no usable content."""


class LLMValidationError(LLMError):
    """The provider returned content but it failed schema validation.
    Distinct from LLMServiceError — content arrived; it just wasn't shaped
    like the requested Pydantic model.

    Carries `raw_text` so callers can log / record / refresh fixtures.
    """

    def __init__(self, message: str, *, raw_text: str | None = None):
        super().__init__(message)
        self.raw_text = raw_text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_errors.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add llm/errors.py tests/test_llm_errors.py
git commit -m "feat(llm): add normalized error hierarchy with LLMValidationError"
```

---

## Task 3: `llm/adapter.py` — `LLMAdapter` Protocol

**Files:**
- Create: `llm/adapter.py`
- Create: `tests/test_llm_adapter_protocol.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_adapter_protocol.py
from pydantic import BaseModel

from llm.adapter import LLMAdapter
from llm.types import StructuredLLMRequest, StructuredLLMResult, TokenUsage


class _Schema(BaseModel):
    x: str


class FakeAdapter:
    """A duck-typed adapter that should satisfy the Protocol."""

    def call_once(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        parsed = _Schema(x="ok")
        return StructuredLLMResult(
            parsed=parsed,
            raw_text='{"x":"ok"}',
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            model="fake",
            provider="fake",
            latency_ms=1.0,
        )


def test_fake_adapter_satisfies_protocol_at_runtime():
    adapter = FakeAdapter()
    assert isinstance(adapter, LLMAdapter)


def test_protocol_is_documented():
    assert LLMAdapter.__doc__ is not None
    assert "call_once" in LLMAdapter.__doc__ or hasattr(LLMAdapter, "call_once")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_adapter_protocol.py -v`
Expected: `ImportError: cannot import name 'LLMAdapter' from 'llm.adapter'`

- [ ] **Step 3: Implement `llm/adapter.py`**

```python
# llm/adapter.py
"""The LLMAdapter Protocol.

An adapter is the *single* place provider-specific code lives. It must:
  - translate a StructuredLLMRequest into a provider SDK call
  - extract a StructuredLLMResult from the provider's response
  - classify provider exceptions into normalized LLMError subclasses
  - validate the parsed content matches the requested schema, or raise LLMValidationError

It does NOT:
  - retry (LLMClient owns retry policy)
  - log (LLMClient owns telemetry)
  - cache (out of scope for MVP)
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import StructuredLLMRequest, StructuredLLMResult


@runtime_checkable
class LLMAdapter(Protocol):
    """Provider adapter. Implements one primitive: call_once.

    Adapters MUST raise normalized errors from llm.errors:
      - LLMMissingKeyError when no API key is configured
      - LLMRateLimitError on 429 / equivalent
      - LLMServiceError on 5xx / transport / unknown failure
      - LLMValidationError when response cannot be parsed as request.response_schema

    Adapters MUST populate StructuredLLMResult.parsed with an instance of
    request.response_schema, never a dict.
    """

    def call_once(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_adapter_protocol.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add llm/adapter.py tests/test_llm_adapter_protocol.py
git commit -m "feat(llm): add LLMAdapter Protocol with call_once primitive"
```

---

## Task 4: `llm/client.py` — `LLMClient` with retry + telemetry

This task has multiple TDD micro-cycles (one per behavior). Commit after each green.

**Files:**
- Create: `llm/client.py`
- Create: `tests/test_llm_client.py`

### 4.1 — Happy path delegation

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_client.py
from dataclasses import replace

import pytest
from pydantic import BaseModel

from llm.client import LLMClient
from llm.errors import LLMRateLimitError, LLMServiceError, LLMValidationError
from llm.types import StructuredLLMRequest, StructuredLLMResult, TokenUsage


class _Schema(BaseModel):
    x: str


def _ok_result() -> StructuredLLMResult:
    return StructuredLLMResult(
        parsed=_Schema(x="ok"),
        raw_text='{"x":"ok"}',
        usage=TokenUsage(input_tokens=1, output_tokens=1),
        model="fake",
        provider="fake",
        latency_ms=10.0,
    )


def _request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        system_prompt="sys",
        user_prompt="user",
        response_schema=_Schema,
        max_retries=2,
        task_name="test_task",
        prompt_version="v1",
    )


class _CountingAdapter:
    def __init__(self, *, raises=None, returns=None):
        self.calls = 0
        self._raises = list(raises) if raises else []
        self._returns = returns

    def call_once(self, request):
        self.calls += 1
        if self._raises:
            exc = self._raises.pop(0)
            if exc is not None:
                raise exc
        return self._returns or _ok_result()


def test_happy_path_delegates_once():
    adapter = _CountingAdapter()
    client = LLMClient(adapter=adapter)
    result = client.generate_structured(_request())
    assert result.parsed.x == "ok"
    assert adapter.calls == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_client.py::test_happy_path_delegates_once -v`
Expected: `ImportError: cannot import name 'LLMClient' from 'llm.client'`

- [ ] **Step 3: Implement minimal `llm/client.py`**

```python
# llm/client.py
"""LLMClient — wraps an adapter with retry, telemetry, and timing.

This is the public surface application code uses.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, replace

from .adapter import LLMAdapter
from .errors import LLMRateLimitError, LLMServiceError, LLMValidationError
from .types import StructuredLLMRequest, StructuredLLMResult

logger = logging.getLogger(__name__)


@dataclass
class LLMClient:
    """Application-facing client. Owns retry policy + telemetry."""

    adapter: LLMAdapter

    def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        return self.adapter.call_once(request)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_client.py::test_happy_path_delegates_once -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add llm/client.py tests/test_llm_client.py
git commit -m "feat(llm): add LLMClient happy-path delegation"
```

### 4.2 — Retry on `LLMRateLimitError`

- [ ] **Step 1: Append failing test**

```python
# tests/test_llm_client.py — add this test
def test_retries_on_rate_limit_then_succeeds():
    adapter = _CountingAdapter(raises=[LLMRateLimitError("rate"), None])
    client = LLMClient(adapter=adapter)
    result = client.generate_structured(_request())
    assert result.parsed.x == "ok"
    assert adapter.calls == 2  # one fail + one success


def test_gives_up_after_max_retries_on_rate_limit():
    adapter = _CountingAdapter(
        raises=[LLMRateLimitError("r1"), LLMRateLimitError("r2"), LLMRateLimitError("r3")]
    )
    client = LLMClient(adapter=adapter)
    with pytest.raises(LLMRateLimitError):
        client.generate_structured(_request())
    # max_retries=2 → up to 2 retries beyond initial → 3 total calls
    assert adapter.calls == 3
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_llm_client.py -v -k retries`
Expected: `test_retries_on_rate_limit_then_succeeds` FAILS (LLMRateLimitError propagates immediately)

- [ ] **Step 3: Implement retry logic with exponential backoff**

Replace the body of `generate_structured` in `llm/client.py`:

```python
# llm/client.py — replace generate_structured
    def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        last_exc: Exception | None = None
        for attempt in range(request.max_retries + 1):
            try:
                start = time.perf_counter()
                result = self.adapter.call_once(request)
                latency_ms = (time.perf_counter() - start) * 1000.0
                # Adapter populates latency in result; we override with our wall-clock
                # measurement (covers any adapter-side overhead).
                return replace(result, latency_ms=latency_ms)
            except (LLMRateLimitError, LLMServiceError) as exc:
                last_exc = exc
                if attempt < request.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                raise
            # Validation, MissingKey, and any other LLMError do NOT retry.
        # Unreachable when max_retries >= 0, but kept for type completeness:
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("LLMClient exhausted retries without raising")  # pragma: no cover

    @staticmethod
    def _sleep_backoff(attempt: int) -> None:
        time.sleep(2 ** attempt)
```

Note: in tests, monkeypatch `time.sleep` to keep them fast.

- [ ] **Step 4: Add a conftest fixture so tests run instantly**

```python
# tests/conftest.py — append (create if it does not exist)
import pytest


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Backoff sleeps would slow tests; replace with no-op for the LLMClient."""
    import llm.client
    monkeypatch.setattr(llm.client.LLMClient, "_sleep_backoff", staticmethod(lambda attempt: None))
```

If `tests/conftest.py` already exists, append the fixture body inside it instead.

- [ ] **Step 5: Run all client tests**

Run: `pytest tests/test_llm_client.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add llm/client.py tests/test_llm_client.py tests/conftest.py
git commit -m "feat(llm): retry rate-limit/service errors with exponential backoff"
```

### 4.3 — No retry on `LLMValidationError` and `LLMMissingKeyError`

- [ ] **Step 1: Append failing tests**

```python
# tests/test_llm_client.py — add
from llm.errors import LLMMissingKeyError


def test_does_not_retry_on_validation_error():
    adapter = _CountingAdapter(raises=[LLMValidationError("bad shape")])
    client = LLMClient(adapter=adapter)
    with pytest.raises(LLMValidationError):
        client.generate_structured(_request())
    assert adapter.calls == 1


def test_does_not_retry_on_missing_key_error():
    adapter = _CountingAdapter(raises=[LLMMissingKeyError("no key")])
    client = LLMClient(adapter=adapter)
    with pytest.raises(LLMMissingKeyError):
        client.generate_structured(_request())
    assert adapter.calls == 1
```

- [ ] **Step 2: Run — they should already pass**

Run: `pytest tests/test_llm_client.py -v -k "validation_error or missing_key"`
Expected: 2 PASS (the existing implementation only catches RateLimit + Service)

- [ ] **Step 3: Commit (no-code commit; new tests confirm behavior)**

```bash
git add tests/test_llm_client.py
git commit -m "test(llm): assert validation and missing-key errors do not retry"
```

### 4.4 — Telemetry log emitted per call

- [ ] **Step 1: Append failing test**

```python
# tests/test_llm_client.py — add
import logging


def test_emits_structured_log_on_success(caplog):
    adapter = _CountingAdapter()
    client = LLMClient(adapter=adapter)
    with caplog.at_level(logging.INFO, logger="llm.client"):
        client.generate_structured(_request())
    records = [r for r in caplog.records if r.name == "llm.client"]
    assert any(
        getattr(r, "task_name", None) == "test_task"
        and getattr(r, "prompt_version", None) == "v1"
        and getattr(r, "provider", None) == "fake"
        and getattr(r, "input_tokens", None) == 1
        and getattr(r, "output_tokens", None) == 1
        for r in records
    ), f"no structured log record matched. records: {records}"


def test_emits_structured_log_on_failure(caplog):
    adapter = _CountingAdapter(raises=[LLMValidationError("bad")])
    client = LLMClient(adapter=adapter)
    with caplog.at_level(logging.WARNING, logger="llm.client"):
        with pytest.raises(LLMValidationError):
            client.generate_structured(_request())
    assert any(
        getattr(r, "task_name", None) == "test_task"
        and getattr(r, "error_class", None) == "LLMValidationError"
        for r in caplog.records
        if r.name == "llm.client"
    )
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_llm_client.py -v -k "structured_log"`
Expected: 2 FAIL

- [ ] **Step 3: Implement structured logging in `LLMClient.generate_structured`**

Replace the body again:

```python
# llm/client.py — replace generate_structured (full)
    def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        last_exc: Exception | None = None
        for attempt in range(request.max_retries + 1):
            start = time.perf_counter()
            try:
                result = self.adapter.call_once(request)
            except (LLMRateLimitError, LLMServiceError) as exc:
                latency_ms = (time.perf_counter() - start) * 1000.0
                self._log_failure(request, exc, attempt=attempt, latency_ms=latency_ms)
                last_exc = exc
                if attempt < request.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                raise
            except Exception as exc:
                latency_ms = (time.perf_counter() - start) * 1000.0
                self._log_failure(request, exc, attempt=attempt, latency_ms=latency_ms)
                raise
            else:
                latency_ms = (time.perf_counter() - start) * 1000.0
                final_result = replace(result, latency_ms=latency_ms)
                self._log_success(request, final_result, attempt=attempt)
                return final_result
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("LLMClient exhausted retries without raising")  # pragma: no cover

    @staticmethod
    def _log_success(
        request: StructuredLLMRequest,
        result: StructuredLLMResult,
        *,
        attempt: int,
    ) -> None:
        logger.info(
            "llm.call_succeeded",
            extra={
                "task_name": request.task_name,
                "prompt_version": request.prompt_version,
                "provider": result.provider,
                "model": result.model,
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "latency_ms": result.latency_ms,
                "attempt": attempt,
            },
        )

    @staticmethod
    def _log_failure(
        request: StructuredLLMRequest,
        exc: Exception,
        *,
        attempt: int,
        latency_ms: float,
    ) -> None:
        logger.warning(
            "llm.call_failed",
            extra={
                "task_name": request.task_name,
                "prompt_version": request.prompt_version,
                "error_class": type(exc).__name__,
                "error_message": str(exc),
                "attempt": attempt,
                "latency_ms": latency_ms,
            },
        )
```

- [ ] **Step 4: Run all client tests**

Run: `pytest tests/test_llm_client.py -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add llm/client.py tests/test_llm_client.py
git commit -m "feat(llm): emit structured success/failure log per call"
```

---

## Task 5: `llm/gemini_adapter.py` — Gemini provider translation

This task also has multiple TDD micro-cycles. Commit after each green.

**Files:**
- Create: `llm/gemini_adapter.py`
- Create: `tests/test_gemini_adapter.py`

**Important context — the SDK:**
The repo uses the *modern* `google-genai` SDK (imported as `from google import genai`), NOT the legacy `google.generativeai`. The relevant call shape (from `ai_service.py:670-694`) is:

```python
from google import genai
from google.genai import types
from google.genai.errors import APIError

client = genai.Client(api_key=key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=user_prompt_text,
    config=types.GenerateContentConfig(
        system_instruction=system_prompt_text,
        temperature=0.2,
        response_schema=PydanticModelClass,         # for structured output
        response_mime_type="application/json",      # required when response_schema is set
    ),
)
# response.text — raw JSON string
# response.parsed — Pydantic instance (when response_schema set, modern SDK populates this)
# response.usage_metadata.prompt_token_count
# response.usage_metadata.candidates_token_count
# APIError has .code (HTTP status int) and .message (str)
```

If `response.parsed` is None or wrong type, raise `LLMValidationError(raw_text=response.text)`. If `response.text` is also empty → `LLMServiceError`.

### 5.1 — Missing API key

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gemini_adapter.py
import pytest
from pydantic import BaseModel

from llm.errors import (
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)
from llm.gemini_adapter import GeminiAdapter
from llm.types import StructuredLLMRequest


class _Schema(BaseModel):
    x: str


def _request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        system_prompt="sys", user_prompt="user", response_schema=_Schema
    )


def test_missing_key_raises_missing_key_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    adapter = GeminiAdapter(api_key=None, model="gemini-2.5-flash")
    with pytest.raises(LLMMissingKeyError):
        adapter.call_once(_request())
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_gemini_adapter.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `llm/gemini_adapter.py`**

```python
# llm/gemini_adapter.py
"""Gemini provider adapter.

This is the ONLY file in the repo that imports google.genai (enforced by
tests/test_llm_seam_isolation.py). All Gemini-specific quirks live here:
SDK call shape, error code classification, response.parsed extraction,
token usage extraction.
"""
from __future__ import annotations

import os
import time
from typing import Any

from google import genai
from google.genai import types as genai_types
from google.genai.errors import APIError

from .errors import (
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)
from .types import StructuredLLMRequest, StructuredLLMResult, TokenUsage


_PROVIDER = "gemini"
_RATE_LIMIT_CODE = 429
_RETRYABLE_SERVICE_CODES = {500, 503}


class GeminiAdapter:
    """Translates StructuredLLMRequest into a google-genai SDK call."""

    def __init__(self, *, api_key: str | None = None, model: str):
        self._explicit_key = api_key
        self._model = model

    def _resolve_key(self) -> str:
        key = self._explicit_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise LLMMissingKeyError(
                "No Gemini API key configured. Set GEMINI_API_KEY or pass api_key."
            )
        return key

    def call_once(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        key = self._resolve_key()
        client = genai.Client(api_key=key)
        config = genai_types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            temperature=request.temperature,
            response_schema=request.response_schema,
            response_mime_type="application/json",
        )

        start = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=request.user_prompt,
                config=config,
            )
        except APIError as err:
            self._raise_normalized(err)
        latency_ms = (time.perf_counter() - start) * 1000.0

        parsed = getattr(response, "parsed", None)
        if not isinstance(parsed, request.response_schema):
            raw_text = getattr(response, "text", None) or ""
            if not raw_text:
                raise LLMServiceError("Gemini returned an empty response.")
            raise LLMValidationError(
                f"Gemini response did not match {request.response_schema.__name__}.",
                raw_text=raw_text,
            )

        usage = self._extract_usage(response)
        raw_text = getattr(response, "text", "") or ""

        return StructuredLLMResult(
            parsed=parsed,
            raw_text=raw_text,
            usage=usage,
            model=self._model,
            provider=_PROVIDER,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _raise_normalized(err: APIError) -> None:
        code = getattr(err, "code", None)
        message = getattr(err, "message", None) or str(err)
        if code == _RATE_LIMIT_CODE:
            raise LLMRateLimitError(f"Gemini rate-limited: {message}") from err
        if code in _RETRYABLE_SERVICE_CODES:
            raise LLMServiceError(f"Gemini service error (HTTP {code}): {message}") from err
        raise LLMServiceError(f"Gemini API error (HTTP {code}): {message}") from err

    @staticmethod
    def _extract_usage(response: Any) -> TokenUsage:
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return TokenUsage(input_tokens=0, output_tokens=0)
        return TokenUsage(
            input_tokens=getattr(meta, "prompt_token_count", 0) or 0,
            output_tokens=getattr(meta, "candidates_token_count", 0) or 0,
        )
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/test_gemini_adapter.py::test_missing_key_raises_missing_key_error -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add llm/gemini_adapter.py tests/test_gemini_adapter.py
git commit -m "feat(llm): add GeminiAdapter with missing-key handling"
```

### 5.2 — Error code classification

- [ ] **Step 1: Append failing tests**

```python
# tests/test_gemini_adapter.py — add
from unittest.mock import MagicMock
import pytest


class _FakeAPIError(Exception):
    """Stand-in for google.genai.errors.APIError; same .code/.message contract."""

    def __init__(self, code: int, message: str = "boom"):
        super().__init__(message)
        self.code = code
        self.message = message


def _patch_genai_client(monkeypatch, *, raises=None, response=None):
    """Replace genai.Client(...) construction with a fake whose
    .models.generate_content either raises or returns response.
    """
    fake_models = MagicMock()
    if raises is not None:
        fake_models.generate_content.side_effect = raises
    else:
        fake_models.generate_content.return_value = response
    fake_client = MagicMock()
    fake_client.models = fake_models

    import llm.gemini_adapter as ga
    monkeypatch.setattr(ga.genai, "Client", lambda **kwargs: fake_client)


def test_429_maps_to_rate_limit_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    # Patch APIError detection: GeminiAdapter catches APIError; we need our
    # fake to BE an APIError subclass at runtime. Replace the imported APIError.
    import llm.gemini_adapter as ga
    monkeypatch.setattr(ga, "APIError", _FakeAPIError)
    _patch_genai_client(monkeypatch, raises=_FakeAPIError(429))

    adapter = ga.GeminiAdapter(model="gemini-2.5-flash")
    with pytest.raises(LLMRateLimitError):
        adapter.call_once(_request())


@pytest.mark.parametrize("code", [500, 503, 504, 401, 400])
def test_other_codes_map_to_service_error(monkeypatch, code):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import llm.gemini_adapter as ga
    monkeypatch.setattr(ga, "APIError", _FakeAPIError)
    _patch_genai_client(monkeypatch, raises=_FakeAPIError(code))

    adapter = ga.GeminiAdapter(model="gemini-2.5-flash")
    with pytest.raises(LLMServiceError):
        adapter.call_once(_request())
```

- [ ] **Step 2: Run to verify pass**

Run: `pytest tests/test_gemini_adapter.py -v -k "rate_limit_error or service_error"`
Expected: 6 PASS (1 + 5 parametrized)

- [ ] **Step 3: Commit (no production code change — error mapping was already implemented)**

```bash
git add tests/test_gemini_adapter.py
git commit -m "test(llm): assert Gemini API error codes map to normalized errors"
```

### 5.3 — Schema validation failure

- [ ] **Step 1: Append failing test**

```python
# tests/test_gemini_adapter.py — add
def test_parsed_none_raises_validation_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import llm.gemini_adapter as ga

    fake_response = MagicMock()
    fake_response.parsed = None
    fake_response.text = '{"oops": "wrong shape"}'
    fake_response.usage_metadata = MagicMock(
        prompt_token_count=10, candidates_token_count=5
    )
    _patch_genai_client(monkeypatch, response=fake_response)

    adapter = ga.GeminiAdapter(model="gemini-2.5-flash")
    with pytest.raises(LLMValidationError) as exc_info:
        adapter.call_once(_request())
    assert exc_info.value.raw_text == '{"oops": "wrong shape"}'


def test_empty_text_raises_service_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import llm.gemini_adapter as ga

    fake_response = MagicMock()
    fake_response.parsed = None
    fake_response.text = ""
    _patch_genai_client(monkeypatch, response=fake_response)

    adapter = ga.GeminiAdapter(model="gemini-2.5-flash")
    with pytest.raises(LLMServiceError):
        adapter.call_once(_request())
```

- [ ] **Step 2: Run to verify pass**

Run: `pytest tests/test_gemini_adapter.py -v -k "validation_error or empty_text"`
Expected: 2 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_gemini_adapter.py
git commit -m "test(llm): assert validation failure → LLMValidationError, empty → LLMServiceError"
```

### 5.4 — Happy path with parsed Pydantic + token usage

- [ ] **Step 1: Append failing test**

```python
# tests/test_gemini_adapter.py — add
def test_happy_path_returns_structured_result(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import llm.gemini_adapter as ga

    fake_response = MagicMock()
    fake_response.parsed = _Schema(x="hello")
    fake_response.text = '{"x": "hello"}'
    fake_response.usage_metadata = MagicMock(
        prompt_token_count=42, candidates_token_count=7
    )
    _patch_genai_client(monkeypatch, response=fake_response)

    adapter = ga.GeminiAdapter(model="gemini-2.5-flash")
    result = adapter.call_once(_request())

    assert isinstance(result.parsed, _Schema)
    assert result.parsed.x == "hello"
    assert result.raw_text == '{"x": "hello"}'
    assert result.usage.input_tokens == 42
    assert result.usage.output_tokens == 7
    assert result.model == "gemini-2.5-flash"
    assert result.provider == "gemini"
    assert result.latency_ms >= 0.0
```

- [ ] **Step 2: Run to verify pass**

Run: `pytest tests/test_gemini_adapter.py -v -k happy_path`
Expected: PASS

- [ ] **Step 3: Run full Gemini-adapter suite**

Run: `pytest tests/test_gemini_adapter.py -v`
Expected: 9 PASS total

- [ ] **Step 4: Commit**

```bash
git add tests/test_gemini_adapter.py
git commit -m "test(llm): assert GeminiAdapter happy path returns parsed + usage"
```

---

## Task 6: `llm/__init__.py` and `llm/factory.py` — public API + builder

**Files:**
- Modify: `llm/__init__.py`
- Create: `llm/factory.py`
- Create: `tests/test_llm_factory.py` (small)

- [ ] **Step 1: Write the failing test for re-exports**

```python
# tests/test_llm_factory.py
import pytest


def test_public_imports_resolve():
    # These names must all be importable from `llm` directly.
    from llm import (
        LLMClient,
        StructuredLLMRequest,
        StructuredLLMResult,
        TokenUsage,
        LLMError,
        LLMMissingKeyError,
        LLMRateLimitError,
        LLMServiceError,
        LLMValidationError,
        build_llm_client,
    )
    assert callable(build_llm_client)


def test_build_llm_client_default_provider_is_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    from llm import build_llm_client, LLMClient
    client = build_llm_client()
    assert isinstance(client, LLMClient)


def test_build_llm_client_unknown_provider_errors(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    from llm import build_llm_client
    with pytest.raises(NotImplementedError):
        build_llm_client()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_llm_factory.py -v`
Expected: ImportError on `build_llm_client`

- [ ] **Step 3: Create `llm/factory.py`**

```python
# llm/factory.py
"""Factory for building the configured LLMClient.

Reads:
  - LLM_PROVIDER (default: "gemini")
  - LLM_MODEL (default: "gemini-2.5-flash" for gemini)

Optional per-call api_key override (used by routes that accept the
learner's own key per request).
"""
from __future__ import annotations

import os

from .client import LLMClient
from .gemini_adapter import GeminiAdapter

_DEFAULT_PROVIDER = "gemini"
_DEFAULT_MODELS = {"gemini": "gemini-2.5-flash"}


def build_llm_client(*, api_key: str | None = None) -> LLMClient:
    provider = os.environ.get("LLM_PROVIDER", _DEFAULT_PROVIDER).strip().lower()
    model = os.environ.get("LLM_MODEL", _DEFAULT_MODELS.get(provider, "")).strip()
    if not model:
        raise ValueError(
            f"LLM_MODEL not set and no default for provider {provider!r}."
        )
    if provider == "gemini":
        adapter = GeminiAdapter(api_key=api_key, model=model)
    else:
        raise NotImplementedError(
            f"LLM provider {provider!r} not implemented. "
            f"Currently supported: 'gemini'."
        )
    return LLMClient(adapter=adapter)
```

- [ ] **Step 4: Update `llm/__init__.py` with re-exports**

```python
# llm/__init__.py
"""Public API for the LLM seam.

Application code should import everything it needs from `llm` directly.
Submodules (types, errors, adapter, client, gemini_adapter, factory) are
implementation detail; importing from them outside of `llm/` itself is
discouraged.
"""
from .client import LLMClient
from .errors import (
    LLMError,
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)
from .factory import build_llm_client
from .types import StructuredLLMRequest, StructuredLLMResult, TokenUsage

__all__ = [
    "LLMClient",
    "StructuredLLMRequest",
    "StructuredLLMResult",
    "TokenUsage",
    "LLMError",
    "LLMMissingKeyError",
    "LLMRateLimitError",
    "LLMServiceError",
    "LLMValidationError",
    "build_llm_client",
]
```

- [ ] **Step 5: Run all factory tests**

Run: `pytest tests/test_llm_factory.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add llm/__init__.py llm/factory.py tests/test_llm_factory.py
git commit -m "feat(llm): add build_llm_client factory and public re-exports"
```

---

## Task 7: `tests/test_llm_seam_isolation.py` — architectural invariant

**Files:**
- Create: `tests/test_llm_seam_isolation.py`

- [ ] **Step 1: Write the test (which should already pass)**

```python
# tests/test_llm_seam_isolation.py
"""Architectural invariant: the Gemini SDK lives ONLY behind the seam.

If this test fails, application code re-coupled to a provider. The fix is
NOT to add the file to `_ALLOWED`; it is to route the call through
llm.LLMClient instead.

See ADR-0003 for the rationale.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Paths that may import the Gemini SDK directly. Keep this set MINIMAL.
_ALLOWED = {"llm/gemini_adapter.py"}

# Substrings that indicate a Gemini-SDK import.
_FORBIDDEN_IMPORT_NEEDLES = (
    "from google import genai",
    "from google.genai",
    "import google.genai",
    "from google.generativeai",
    "import google.generativeai",
)

# Directories to skip entirely.
_SKIP_DIR_PARTS = {
    ".venv", "venv", ".git", "node_modules", "__pycache__", "tmp",
    ".pytest_cache", "test-results", "logs",
}


def _iter_repo_python_files():
    for py_path in REPO_ROOT.rglob("*.py"):
        if any(part in _SKIP_DIR_PARTS for part in py_path.parts):
            continue
        yield py_path


def test_gemini_sdk_only_imported_in_adapter():
    violations: list[str] = []
    for py_path in _iter_repo_python_files():
        rel = py_path.relative_to(REPO_ROOT).as_posix()
        if rel in _ALLOWED:
            continue
        # ai_service.py is allowed to keep legacy Gemini imports until the
        # drill_chat / generate_repair_reps migrations land. Track that
        # exception explicitly here so it's a known concession, not invisible.
        if rel == "ai_service.py":
            continue
        try:
            text = py_path.read_text(encoding="utf-8")
        except Exception:
            continue
        for needle in _FORBIDDEN_IMPORT_NEEDLES:
            if needle in text:
                violations.append(f"{rel}: contains {needle!r}")
    assert not violations, (
        "LLM seam violation — provider import outside the adapter:\n  "
        + "\n  ".join(violations)
    )


def test_extract_knowledge_map_does_not_import_gemini_directly():
    """Stronger invariant after Task 9: ai_service.py's extract path
    must use llm.LLMClient, not google.genai. This test passes once
    Task 9 lands; it acts as the regression gate."""
    ai_service = (REPO_ROOT / "ai_service.py").read_text(encoding="utf-8")
    # Once extract is migrated, the file may STILL import google.genai
    # for the drill / repair-reps paths. We loosen the assertion to the
    # module: exempted in test_gemini_sdk_only_imported_in_adapter above.
    # This test exists as a placeholder; tighten it to a stricter check
    # (e.g., extract function body must not reference 'genai') once
    # downstream paths migrate too.
    # For now: assert llm.LLMClient is referenced somewhere in ai_service.
    assert (
        "from llm" in ai_service or "import llm" in ai_service
    ), "ai_service.py must use llm.LLMClient at least for the extract path"
```

- [ ] **Step 2: Run — first test should pass; second fails until Task 9**

Run: `pytest tests/test_llm_seam_isolation.py::test_gemini_sdk_only_imported_in_adapter -v`
Expected: PASS

Run: `pytest tests/test_llm_seam_isolation.py::test_extract_knowledge_map_does_not_import_gemini_directly -v`
Expected: FAIL ("ai_service.py must use llm.LLMClient...") — this is the regression gate Task 9 will close.

- [ ] **Step 3: Commit (with the second test marked xfail until Task 9)**

Update the second test to use `@pytest.mark.xfail`:

```python
@pytest.mark.xfail(
    reason="Closes after Task 9 migrates extract_knowledge_map onto llm.LLMClient",
    strict=True,
)
def test_extract_knowledge_map_does_not_import_gemini_directly():
    ...
```

```bash
git add tests/test_llm_seam_isolation.py
git commit -m "test(llm): architectural isolation test — Gemini SDK only in adapter"
```

---

## Task 8: `models/provisional_map.py` — `ProvisionalMap` Pydantic contract

This task has multiple TDD sub-cycles.

**Files:**
- Create: `models/__init__.py`
- Create: `models/identifiers.py`
- Create: `models/provisional_map.py`
- Create: `tests/test_provisional_map.py`

### 8.1 — Identifier grammar

- [ ] **Step 1: Write the failing test**

```python
# tests/test_provisional_map.py
import pytest

from models.identifiers import (
    BackboneId,
    ClusterId,
    SubnodeId,
    parse_id,
    IdKind,
)


def test_core_thesis_is_a_known_id():
    kind, parsed = parse_id("core-thesis")
    assert kind is IdKind.CORE_THESIS
    assert parsed == "core-thesis"


@pytest.mark.parametrize("good_id", ["b1", "b2", "b10"])
def test_backbone_ids_parse(good_id):
    kind, parsed = parse_id(good_id)
    assert kind is IdKind.BACKBONE
    assert isinstance(parsed, BackboneId)
    assert str(parsed) == good_id


@pytest.mark.parametrize("good_id", ["c1", "c2", "c10"])
def test_cluster_ids_parse(good_id):
    kind, parsed = parse_id(good_id)
    assert kind is IdKind.CLUSTER
    assert isinstance(parsed, ClusterId)
    assert str(parsed) == good_id


@pytest.mark.parametrize("good_id", ["c1_s1", "c2_s5", "c10_s12"])
def test_subnode_ids_parse(good_id):
    kind, parsed = parse_id(good_id)
    assert kind is IdKind.SUBNODE
    assert isinstance(parsed, SubnodeId)
    assert parsed.cluster_id == good_id.split("_")[0]
    assert str(parsed) == good_id


@pytest.mark.parametrize("bad_id", ["", "x1", "B1", "b", "c", "c1_s", "c1_s_1", "c-1", "1"])
def test_invalid_ids_raise(bad_id):
    with pytest.raises(ValueError):
        parse_id(bad_id)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_provisional_map.py -v`
Expected: ImportError

- [ ] **Step 3: Implement `models/identifiers.py`**

```python
# models/identifiers.py
"""Identifier grammar for ProvisionalMap nodes.

Grammar:
  - "core-thesis" — the single root concept of a map
  - "b<N>" — backbone node, N in 1..99
  - "c<N>" — cluster node, N in 1..99
  - "c<N>_s<M>" — subnode of cluster c<N>, M in 1..99

Parsing rejects everything else. This is the contract enforced at the
ProvisionalMap boundary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Union

CORE_THESIS = "core-thesis"

_BACKBONE_RE = re.compile(r"^b(\d{1,2})$")
_CLUSTER_RE = re.compile(r"^c(\d{1,2})$")
_SUBNODE_RE = re.compile(r"^(c\d{1,2})_s(\d{1,2})$")


class IdKind(Enum):
    CORE_THESIS = "core-thesis"
    BACKBONE = "backbone"
    CLUSTER = "cluster"
    SUBNODE = "subnode"


@dataclass(frozen=True)
class BackboneId:
    raw: str

    def __str__(self) -> str:
        return self.raw


@dataclass(frozen=True)
class ClusterId:
    raw: str

    def __str__(self) -> str:
        return self.raw


@dataclass(frozen=True)
class SubnodeId:
    raw: str
    cluster_id: str

    def __str__(self) -> str:
        return self.raw


ParsedId = Union[str, BackboneId, ClusterId, SubnodeId]


def parse_id(value: str) -> Tuple[IdKind, ParsedId]:
    """Return (kind, parsed). Raises ValueError on malformed input."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"id must be a non-empty string, got {value!r}")
    if value == CORE_THESIS:
        return IdKind.CORE_THESIS, value
    if _BACKBONE_RE.match(value):
        return IdKind.BACKBONE, BackboneId(raw=value)
    if _CLUSTER_RE.match(value):
        return IdKind.CLUSTER, ClusterId(raw=value)
    m = _SUBNODE_RE.match(value)
    if m:
        return IdKind.SUBNODE, SubnodeId(raw=value, cluster_id=m.group(1))
    raise ValueError(f"unrecognized id grammar: {value!r}")
```

- [ ] **Step 4: Create empty `models/__init__.py`**

```python
# models/__init__.py
from .identifiers import (
    BackboneId,
    ClusterId,
    IdKind,
    SubnodeId,
    parse_id,
    CORE_THESIS,
)
```

- [ ] **Step 5: Run identifier tests**

Run: `pytest tests/test_provisional_map.py -v -k "id"`
Expected: ~22 PASS (5 parametrized x ~3 + the rest)

- [ ] **Step 6: Commit**

```bash
git add models/__init__.py models/identifiers.py tests/test_provisional_map.py
git commit -m "feat(models): add identifier grammar (BackboneId/ClusterId/SubnodeId)"
```

### 8.2 — `ProvisionalMap` Pydantic shape (matches `extract-system-v1.txt`)

**The output schema is defined in `app_prompts/extract-system-v1.txt:171-235`. ProvisionalMap MUST match that schema exactly — Pydantic's `extra="forbid"` will reject any mismatch.** Key fields the prompt produces:

- Metadata: `source_title`, `core_thesis`, `architecture_type` (lowercase enum), `difficulty` (lowercase enum), `governing_assumptions: list[str]`, `low_density: bool`
- Backbone item: `id` (b<N>), `principle: str`, `dependent_clusters: list[str]` — backbone *owns* the cluster references, not the other way around
- Cluster: `id` (c<N>), `label`, `description`, `subnodes: list[Subnode]` — clusters do **not** carry `source_backbone`
- Subnode: `id` (c<N>_s<M>), `label`, `mechanism`, plus four nullable drill-state fields (`drill_status`, `gap_type`, `gap_description`, `last_drilled`) — all null on extraction
- Relationships: `domain_mechanics: list[DomainMechanic]`, `learning_prerequisites: list[LearningPrereq]`
- Frameworks: `list[Framework]` (may be empty)

The closure rules in the prompt (output rules section, lines 246-257) define exactly what the validator enforces.

- [ ] **Step 1: Append failing tests**

```python
# tests/test_provisional_map.py — add
import pytest

from models.provisional_map import ProvisionalMap


VALID_MAP = {
    "metadata": {
        "source_title": "Entropy in closed systems",
        "core_thesis": "Entropy increases in closed systems.",
        "architecture_type": "system_description",
        "difficulty": "medium",
        "governing_assumptions": ["The system is closed."],
        "low_density": False,
    },
    "backbone": [
        {
            "id": "b1",
            "principle": "Disorder grows over time in isolated systems.",
            "dependent_clusters": ["c1"],
        }
    ],
    "clusters": [
        {
            "id": "c1",
            "label": "Microstate counting drives entropy",
            "description": "Each macrostate corresponds to many microstates; entropy reflects that count.",
            "subnodes": [
                {
                    "id": "c1_s1",
                    "label": "Boltzmann distribution",
                    "mechanism": "Probability of a microstate is weighted by its energy.",
                    "drill_status": None,
                    "gap_type": None,
                    "gap_description": None,
                    "last_drilled": None,
                }
            ],
        }
    ],
    "relationships": {
        "domain_mechanics": [],
        "learning_prerequisites": [],
    },
    "frameworks": [],
}


def test_provisional_map_parses_valid_input():
    m = ProvisionalMap.model_validate(VALID_MAP)
    assert m.metadata.core_thesis.startswith("Entropy")
    assert len(m.backbone) == 1
    assert len(m.clusters) == 1
    assert len(m.clusters[0].subnodes) == 1
    assert m.frameworks == []


def test_provisional_map_rejects_bad_id():
    bad = {
        **VALID_MAP,
        "backbone": [{"id": "X1", "principle": "x", "dependent_clusters": ["c1"]}],
    }
    with pytest.raises(ValueError):
        ProvisionalMap.model_validate(bad)


def test_provisional_map_rejects_missing_metadata():
    bad = {k: v for k, v in VALID_MAP.items() if k != "metadata"}
    with pytest.raises(ValueError):
        ProvisionalMap.model_validate(bad)


def test_provisional_map_tolerates_unknown_field_for_gemini_compat():
    """Unknown fields must NOT raise — Gemini rejects extra='forbid' schemas
    (additionalProperties: false in JSON Schema). Field-level correctness is
    governed by the prompt + closure validators, not by extra='forbid'.
    See ai_service.py:_parse_repair_reps_response for precedent.
    """
    permissive = {**VALID_MAP, "unexpected_top_level": "ignored"}
    m = ProvisionalMap.model_validate(permissive)
    assert m.metadata.core_thesis == "Entropy increases in closed systems."
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_provisional_map.py -v -k provisional_map`
Expected: ImportError

- [ ] **Step 3: Implement `models/provisional_map.py`**

```python
# models/provisional_map.py
"""ProvisionalMap — the typed cognitive artifact contract.

Mirrors the JSON schema described in app_prompts/extract-system-v1.txt.
Application code that consumes extraction output sees this type, never a
dict. Structural integrity is enforced at parse time:

  - Every id (backbone, cluster, subnode) matches the identifier grammar
  - Every subnode lives in its declared cluster (c1_s2 must be inside c1)
  - Every cluster id referenced by backbone, relationships, or frameworks exists
  - Every cluster is covered by at least one backbone's dependent_clusters
  - Every cluster has at least one subnode
  - Learning-prerequisite edges form a DAG (no self-loops, no cycles, no reciprocals)

What is NOT enforced here:
  - Quality minimums (≥N nodes total): governed by the prompt
  - Framework quality gates: governed by the prompt
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .identifiers import IdKind, parse_id


# --- Leaf shapes -------------------------------------------------------------


class Metadata(BaseModel):
    # NOTE: extra="forbid" is intentionally NOT set. Pydantic emits
    # additionalProperties: false in JSON Schema when extra="forbid" is set,
    # and Gemini's response_schema parameter rejects schemas containing that.
    # See ai_service.py:_parse_repair_reps_response for the existing precedent.
    # Field-level correctness is enforced by the prompt + closure validators.
    model_config = ConfigDict()

    source_title: str
    core_thesis: str
    architecture_type: Literal[
        "causal_chain", "problem_solution", "comparison", "system_description"
    ]
    difficulty: Literal["easy", "medium", "hard"]
    governing_assumptions: List[str] = Field(default_factory=list)
    low_density: bool = False


class Subnode(BaseModel):
    # NOTE: extra="forbid" is intentionally NOT set. Pydantic emits
    # additionalProperties: false in JSON Schema when extra="forbid" is set,
    # and Gemini's response_schema parameter rejects schemas containing that.
    # See ai_service.py:_parse_repair_reps_response for the existing precedent.
    # Field-level correctness is enforced by the prompt + closure validators.
    model_config = ConfigDict()

    id: str
    label: str
    mechanism: str
    drill_status: Optional[str] = None
    gap_type: Optional[str] = None
    gap_description: Optional[str] = None
    last_drilled: Optional[str] = None

    @field_validator("id")
    @classmethod
    def _subnode_only(cls, v: str) -> str:
        kind, _ = parse_id(v)
        if kind is not IdKind.SUBNODE:
            raise ValueError(f"subnode id must match c<N>_s<M>, got {v!r}")
        return v


class Cluster(BaseModel):
    # NOTE: extra="forbid" is intentionally NOT set. Pydantic emits
    # additionalProperties: false in JSON Schema when extra="forbid" is set,
    # and Gemini's response_schema parameter rejects schemas containing that.
    # See ai_service.py:_parse_repair_reps_response for the existing precedent.
    # Field-level correctness is enforced by the prompt + closure validators.
    model_config = ConfigDict()

    id: str
    label: str
    description: str
    subnodes: List[Subnode] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _cluster_only(cls, v: str) -> str:
        kind, _ = parse_id(v)
        if kind is not IdKind.CLUSTER:
            raise ValueError(f"cluster id must match c<N>, got {v!r}")
        return v

    @model_validator(mode="after")
    def _subnodes_belong_to_this_cluster(self) -> "Cluster":
        for sn in self.subnodes:
            kind, parsed = parse_id(sn.id)
            assert kind is IdKind.SUBNODE
            if parsed.cluster_id != self.id:
                raise ValueError(
                    f"subnode {sn.id!r} does not belong to cluster {self.id!r}"
                )
        return self

    @model_validator(mode="after")
    def _at_least_one_subnode(self) -> "Cluster":
        # Per extract prompt MINIMUM DRILLABILITY RULE.
        if not self.subnodes:
            raise ValueError(
                f"cluster {self.id!r} must contain at least one subnode (drillability rule)"
            )
        return self


class BackboneItem(BaseModel):
    # NOTE: extra="forbid" is intentionally NOT set. Pydantic emits
    # additionalProperties: false in JSON Schema when extra="forbid" is set,
    # and Gemini's response_schema parameter rejects schemas containing that.
    # See ai_service.py:_parse_repair_reps_response for the existing precedent.
    # Field-level correctness is enforced by the prompt + closure validators.
    model_config = ConfigDict()

    id: str
    principle: str
    dependent_clusters: List[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _backbone_only(cls, v: str) -> str:
        kind, _ = parse_id(v)
        if kind is not IdKind.BACKBONE:
            raise ValueError(f"backbone id must match b<N>, got {v!r}")
        return v


class DomainMechanic(BaseModel):
    # populate_by_name lets construction via from_=... work even though the
    # JSON key is "from" (a Python keyword). Validation accepts either.
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    type: Literal["causal", "bidirectional", "amplifies", "suppresses", "tension"]
    mechanism: str


class LearningPrereq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    rationale: str


class Relationships(BaseModel):
    # NOTE: extra="forbid" is intentionally NOT set. Pydantic emits
    # additionalProperties: false in JSON Schema when extra="forbid" is set,
    # and Gemini's response_schema parameter rejects schemas containing that.
    # See ai_service.py:_parse_repair_reps_response for the existing precedent.
    # Field-level correctness is enforced by the prompt + closure validators.
    model_config = ConfigDict()

    domain_mechanics: List[DomainMechanic] = Field(default_factory=list)
    learning_prerequisites: List[LearningPrereq] = Field(default_factory=list)


class Framework(BaseModel):
    # NOTE: extra="forbid" is intentionally NOT set. Pydantic emits
    # additionalProperties: false in JSON Schema when extra="forbid" is set,
    # and Gemini's response_schema parameter rejects schemas containing that.
    # See ai_service.py:_parse_repair_reps_response for the existing precedent.
    # Field-level correctness is enforced by the prompt + closure validators.
    model_config = ConfigDict()

    id: str
    name: str
    statement: str
    source_clusters: List[str] = Field(default_factory=list)
    external_application: str


# --- Top-level shape ---------------------------------------------------------


class ProvisionalMap(BaseModel):
    """A typed knowledge map. Consumed by drill, repair-reps, traversal."""

    # NOTE: extra="forbid" is intentionally NOT set. Pydantic emits
    # additionalProperties: false in JSON Schema when extra="forbid" is set,
    # and Gemini's response_schema parameter rejects schemas containing that.
    # See ai_service.py:_parse_repair_reps_response for the existing precedent.
    # Field-level correctness is enforced by the prompt + closure validators.
    model_config = ConfigDict()

    metadata: Metadata
    backbone: List[BackboneItem]
    clusters: List[Cluster]
    relationships: Relationships
    frameworks: List[Framework] = Field(default_factory=list)

    # --- Closure validators ---

    @model_validator(mode="after")
    def _every_cluster_has_unique_id(self) -> "ProvisionalMap":
        ids = [c.id for c in self.clusters]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate cluster ids")
        bb_ids = [b.id for b in self.backbone]
        if len(bb_ids) != len(set(bb_ids)):
            raise ValueError("duplicate backbone ids")
        return self

    @model_validator(mode="after")
    def _backbone_dependent_clusters_exist(self) -> "ProvisionalMap":
        cluster_ids = {c.id for c in self.clusters}
        for bb in self.backbone:
            for ref in bb.dependent_clusters:
                if ref not in cluster_ids:
                    raise ValueError(
                        f"backbone {bb.id!r} lists unknown dependent_cluster {ref!r}"
                    )
        return self

    @model_validator(mode="after")
    def _every_cluster_covered_by_some_backbone(self) -> "ProvisionalMap":
        # Per BACKBONE COVERAGE RULE in extract-system-v1.txt.
        covered: set[str] = set()
        for bb in self.backbone:
            covered.update(bb.dependent_clusters)
        cluster_ids = {c.id for c in self.clusters}
        orphans = cluster_ids - covered
        if orphans:
            raise ValueError(
                f"clusters not covered by any backbone: {sorted(orphans)}"
            )
        return self

    @model_validator(mode="after")
    def _relationship_endpoints_exist(self) -> "ProvisionalMap":
        cluster_ids = {c.id for c in self.clusters}
        for dm in self.relationships.domain_mechanics:
            for ref in (dm.from_, dm.to):
                if ref not in cluster_ids:
                    raise ValueError(
                        f"domain_mechanics edge references unknown cluster {ref!r}"
                    )
        for lp in self.relationships.learning_prerequisites:
            for ref in (lp.from_, lp.to):
                if ref not in cluster_ids:
                    raise ValueError(
                        f"learning_prerequisites edge references unknown cluster {ref!r}"
                    )
            if lp.from_ == lp.to:
                raise ValueError(f"learning_prerequisite self-loop on {lp.from_!r}")
        return self

    @model_validator(mode="after")
    def _learning_prerequisites_acyclic(self) -> "ProvisionalMap":
        # Per GRAPH-SAFETY RULES FOR PREREQUISITES.
        edges: dict[str, list[str]] = {}
        for lp in self.relationships.learning_prerequisites:
            edges.setdefault(lp.from_, []).append(lp.to)
            # Reciprocal pair check
            for back in self.relationships.learning_prerequisites:
                if back is lp:
                    continue
                if back.from_ == lp.to and back.to == lp.from_:
                    raise ValueError(
                        f"reciprocal learning prerequisite: {lp.from_!r}<->{lp.to!r}"
                    )
        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        colors: dict[str, int] = {n: WHITE for n in edges}

        def visit(n: str) -> None:
            colors[n] = GRAY
            for nb in edges.get(n, []):
                if colors.get(nb, WHITE) == GRAY:
                    raise ValueError(f"learning prerequisite cycle through {n!r}->{nb!r}")
                if colors.get(nb, WHITE) == WHITE:
                    colors.setdefault(nb, WHITE)
                    visit(nb)
            colors[n] = BLACK

        for n in list(edges.keys()):
            if colors[n] == WHITE:
                visit(n)
        return self

    @model_validator(mode="after")
    def _framework_source_clusters_exist(self) -> "ProvisionalMap":
        cluster_ids = {c.id for c in self.clusters}
        for fw in self.frameworks:
            for ref in fw.source_clusters:
                if ref not in cluster_ids:
                    raise ValueError(
                        f"framework {fw.id!r} references unknown cluster {ref!r}"
                    )
        return self
```

Update `models/__init__.py` to export everything:

```python
# models/__init__.py — replace with:
from .identifiers import (
    BackboneId,
    ClusterId,
    IdKind,
    SubnodeId,
    parse_id,
    CORE_THESIS,
)
from .provisional_map import (
    BackboneItem,
    Cluster,
    DomainMechanic,
    Framework,
    LearningPrereq,
    Metadata,
    ProvisionalMap,
    Relationships,
    Subnode,
)

__all__ = [
    "BackboneId",
    "ClusterId",
    "IdKind",
    "SubnodeId",
    "parse_id",
    "CORE_THESIS",
    "BackboneItem",
    "Cluster",
    "DomainMechanic",
    "Framework",
    "LearningPrereq",
    "Metadata",
    "ProvisionalMap",
    "Relationships",
    "Subnode",
]
```

- [ ] **Step 4: Run all provisional-map tests**

Run: `pytest tests/test_provisional_map.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add models/__init__.py models/provisional_map.py tests/test_provisional_map.py
git commit -m "feat(models): add ProvisionalMap matching extract-system-v1 schema"
```

### 8.3 — Closure-violation tests

- [ ] **Step 1: Append failing tests**

```python
# tests/test_provisional_map.py — add
def test_subnode_in_wrong_cluster_rejected():
    bad = {
        **VALID_MAP,
        "clusters": [
            {
                "id": "c2",
                "label": "x",
                "description": "x",
                "subnodes": [
                    {
                        "id": "c1_s1",  # belongs to c1, but cluster is c2
                        "label": "x",
                        "mechanism": "x",
                        "drill_status": None,
                        "gap_type": None,
                        "gap_description": None,
                        "last_drilled": None,
                    }
                ],
            }
        ],
        "backbone": [{"id": "b1", "principle": "x", "dependent_clusters": ["c2"]}],
    }
    with pytest.raises(ValueError, match="does not belong to cluster"):
        ProvisionalMap.model_validate(bad)


def test_backbone_pointing_at_unknown_cluster_rejected():
    bad = {
        **VALID_MAP,
        "backbone": [
            {"id": "b1", "principle": "x", "dependent_clusters": ["c9"]}
        ],
    }
    with pytest.raises(ValueError, match="unknown dependent_cluster"):
        ProvisionalMap.model_validate(bad)


def test_orphan_cluster_rejected():
    bad = {
        **VALID_MAP,
        "backbone": [
            {"id": "b1", "principle": "x", "dependent_clusters": []}  # covers nothing
        ],
    }
    with pytest.raises(ValueError, match="not covered by any backbone"):
        ProvisionalMap.model_validate(bad)


def test_cluster_without_subnode_rejected():
    bad = {
        **VALID_MAP,
        "clusters": [
            {"id": "c1", "label": "x", "description": "x", "subnodes": []}
        ],
    }
    with pytest.raises(ValueError, match="must contain at least one subnode"):
        ProvisionalMap.model_validate(bad)


def test_learning_prerequisite_cycle_rejected():
    bad = {
        **VALID_MAP,
        "clusters": [
            {
                "id": "c1",
                "label": "x",
                "description": "x",
                "subnodes": [{
                    "id": "c1_s1", "label": "x", "mechanism": "x",
                    "drill_status": None, "gap_type": None,
                    "gap_description": None, "last_drilled": None,
                }],
            },
            {
                "id": "c2",
                "label": "y",
                "description": "y",
                "subnodes": [{
                    "id": "c2_s1", "label": "y", "mechanism": "y",
                    "drill_status": None, "gap_type": None,
                    "gap_description": None, "last_drilled": None,
                }],
            },
        ],
        "backbone": [
            {"id": "b1", "principle": "x", "dependent_clusters": ["c1", "c2"]}
        ],
        "relationships": {
            "domain_mechanics": [],
            "learning_prerequisites": [
                {"from": "c1", "to": "c2", "rationale": "x"},
                {"from": "c2", "to": "c1", "rationale": "y"},  # reciprocal!
            ],
        },
    }
    with pytest.raises(ValueError, match="reciprocal"):
        ProvisionalMap.model_validate(bad)
```

- [ ] **Step 2: Run — should pass with the validators implemented**

Run: `pytest tests/test_provisional_map.py -v`
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_provisional_map.py
git commit -m "test(models): assert ProvisionalMap closure rules from extract-system-v1"
```

---

## Task 9: Migrate `extract_knowledge_map` onto the LLM seam

**Files:**
- Modify: `ai_service.py` (replace `extract_knowledge_map`; remove `_clean_response`, `_log_extract_failure`)
- Modify: `app_prompts/extract-system-v1.txt` *(no edit; just referenced)*
- Create: `tests/test_extract_knowledge_map_migration.py`

- [ ] **Step 1: Write the failing test using a fake LLMClient**

```python
# tests/test_extract_knowledge_map_migration.py
from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from llm.types import StructuredLLMRequest, StructuredLLMResult, TokenUsage
from llm.errors import LLMValidationError, LLMRateLimitError, LLMMissingKeyError
from models import ProvisionalMap


VALID_MAP_DICT = {
    "metadata": {
        "source_title": "Test source",
        "core_thesis": "Test thesis.",
        "architecture_type": "system_description",
        "difficulty": "easy",
        "governing_assumptions": [],
        "low_density": False,
    },
    "backbone": [
        {"id": "b1", "principle": "test principle", "dependent_clusters": ["c1"]}
    ],
    "clusters": [
        {
            "id": "c1",
            "label": "x",
            "description": "x",
            "subnodes": [
                {
                    "id": "c1_s1",
                    "label": "x",
                    "mechanism": "x",
                    "drill_status": None,
                    "gap_type": None,
                    "gap_description": None,
                    "last_drilled": None,
                }
            ],
        }
    ],
    "relationships": {"domain_mechanics": [], "learning_prerequisites": []},
    "frameworks": [],
}


@dataclass
class _FakeClient:
    """Captures calls; returns a pre-built ProvisionalMap."""
    response: StructuredLLMResult | None = None
    raises: Exception | None = None
    last_request: StructuredLLMRequest | None = None

    def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        self.last_request = request
        if self.raises is not None:
            raise self.raises
        return self.response  # type: ignore


def _ok_result() -> StructuredLLMResult:
    return StructuredLLMResult(
        parsed=ProvisionalMap.model_validate(VALID_MAP_DICT),
        raw_text="{}",
        usage=TokenUsage(input_tokens=10, output_tokens=20),
        model="gemini-2.5-flash",
        provider="gemini",
        latency_ms=12.0,
    )


def test_extract_returns_provisional_map(monkeypatch):
    from ai_service import extract_knowledge_map

    fake = _FakeClient(response=_ok_result())
    result = extract_knowledge_map(
        "raw text input here for extraction",
        llm=fake,
    )
    assert isinstance(result, ProvisionalMap)
    assert result.metadata.core_thesis == "Test thesis."
    # Request shape:
    assert fake.last_request is not None
    assert fake.last_request.response_schema is ProvisionalMap
    assert fake.last_request.task_name == "provisional_map_generation"
    assert "raw text input here" in fake.last_request.user_prompt


def test_extract_propagates_validation_error():
    from ai_service import extract_knowledge_map

    fake = _FakeClient(raises=LLMValidationError("bad shape", raw_text="{...}"))
    with pytest.raises(LLMValidationError):
        extract_knowledge_map("text", llm=fake)


def test_extract_propagates_rate_limit_and_missing_key():
    from ai_service import extract_knowledge_map

    for exc in (LLMRateLimitError("r"), LLMMissingKeyError("k")):
        fake = _FakeClient(raises=exc)
        with pytest.raises(type(exc)):
            extract_knowledge_map("text", llm=fake)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_extract_knowledge_map_migration.py -v`
Expected: FAIL — `extract_knowledge_map` does not accept `llm=` kwarg and does not return `ProvisionalMap`.

- [ ] **Step 3: Rewrite `extract_knowledge_map` in `ai_service.py`**

Replace the function (currently at `ai_service.py:679-725`) with:

```python
# ai_service.py — replace extract_knowledge_map
def extract_knowledge_map(
    raw_text: str,
    *,
    llm: "LLMClient | None" = None,
    api_key: str | None = None,
    telemetry_context: dict | None = None,
) -> ProvisionalMap:
    """Generate a Provisional map from learner-supplied text.

    The application sees a typed ProvisionalMap, never a dict and never
    a Gemini-shaped response. All provider-specific behavior lives behind
    the LLMClient seam.
    """
    from llm import (
        LLMClient,
        StructuredLLMRequest,
        build_llm_client,
    )

    client: LLMClient = llm if llm is not None else build_llm_client(api_key=api_key)

    user_prompt = USER_PROMPT.format(text=raw_text)
    system_prompt = EXTRACT_PROMPT_PATH.read_text()
    request = StructuredLLMRequest(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=ProvisionalMap,
        temperature=EXTRACT_TEMPERATURE,
        task_name="provisional_map_generation",
        prompt_version=EXTRACT_PROMPT_VERSION,
    )
    result = client.generate_structured(request)
    # The adapter validates parsed type; LLMClient retried as configured.
    return result.parsed  # type: ignore[return-value]
```

Add import near the top of `ai_service.py` (after the existing imports block, before `USER_PROMPT`):

```python
# ai_service.py — add near top
from models import ProvisionalMap
```

Remove (delete) the now-unused helpers in `ai_service.py`:
- `_clean_response`
- `_log_extract_failure`

Do NOT remove `_validate_knowledge_map` yet — drill_chat and generate_repair_reps still call it. (It will be removed in a later task when those paths migrate.)

Do NOT remove `MissingAPIKeyError`, `GeminiRateLimitError`, `GeminiServiceError` yet — they are still raised by `_get_client` and `_call_gemini_with_retry`, used by drill and repair-reps. Removal happens after Task 10's downstream migrations.

- [ ] **Step 4: Run the migration test**

Run: `pytest tests/test_extract_knowledge_map_migration.py -v`
Expected: 4 PASS (3 + the parametric)

- [ ] **Step 5: Run the architectural isolation test that was xfail-marked**

Edit `tests/test_llm_seam_isolation.py` and remove the `@pytest.mark.xfail` decorator from `test_extract_knowledge_map_does_not_import_gemini_directly`. Run:

Run: `pytest tests/test_llm_seam_isolation.py -v`
Expected: 2 PASS

- [ ] **Step 6: Run the broader test suite for regression check**

Run: `pytest tests/ -v --ignore=tests/e2e`
Expected: all green except possibly tests that asserted the old `dict` return shape. If any test fails because it expected a dict, that's expected — fix it as part of this task by either updating the assertion to `.model_dump()` equivalence, or by leaving the failure visible for Task 10.

- [ ] **Step 7: Commit**

```bash
git add ai_service.py tests/test_extract_knowledge_map_migration.py tests/test_llm_seam_isolation.py
git commit -m "feat(extract): migrate extract_knowledge_map onto llm seam — returns ProvisionalMap"
```

---

## Task 10: Update `/api/extract` route to use normalized errors

**Files:**
- Modify: `main.py` — `/api/extract` route handler
- Modify: any existing `tests/test_*.py` that assert on `/api/extract` error shapes (discovered via grep in Step 1 below)

- [ ] **Step 1: Find existing extract-route tests**

Run: `grep -rn "/api/extract" tests/ | head -20`

Note any test that asserts on the old `MissingAPIKeyError`/`GeminiRateLimitError`/`GeminiServiceError` mapping. Plan to update them.

- [ ] **Step 2: Write a test for the new error mapping**

```python
# tests/test_extract_route_error_mapping.py
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from llm.errors import (
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def _post(client, **kwargs):
    return client.post(
        "/api/extract", json={"text": "x" * 250, **kwargs}
    )


@pytest.mark.parametrize(
    "exc_cls, expected_status",
    [
        (LLMMissingKeyError, 401),
        (LLMRateLimitError, 429),
        (LLMServiceError, 503),
        (LLMValidationError, 502),
    ],
)
def test_route_maps_normalized_errors_to_http(client, exc_cls, expected_status):
    with patch("ai_service.extract_knowledge_map") as fake:
        fake.side_effect = exc_cls("boom")
        resp = _post(client)
    assert resp.status_code == expected_status
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_extract_route_error_mapping.py -v`
Expected: 4 FAIL (current handler maps the OLD error types)

- [ ] **Step 4: Update `main.py` `/api/extract` route**

Replace the body of `extract` (currently at `main.py:315-341`):

```python
# main.py — replace the extract route
@app.post("/api/extract")
def extract(req: ExtractRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided.")
    try:
        src = source_intake.from_text(req.text)
    except ParseEmpty:
        raise HTTPException(
            status_code=422,
            detail="Couldn't find enough readable text in what you pasted.",
        )

    from llm.errors import (
        LLMMissingKeyError,
        LLMRateLimitError,
        LLMServiceError,
        LLMValidationError,
    )

    try:
        provisional_map = extract_knowledge_map(src.text, api_key=req.api_key)
        # Wire-shape: keep `knowledge_map` key for back-compat with the frontend.
        return {"knowledge_map": provisional_map.model_dump()}
    except LLMMissingKeyError as err:
        raise HTTPException(status_code=401, detail=str(err))
    except LLMRateLimitError as err:
        raise HTTPException(status_code=429, detail=str(err))
    except LLMValidationError as err:
        # Provider returned content but it didn't match the schema.
        # 502 Bad Gateway: upstream returned an unusable payload.
        raise HTTPException(
            status_code=502,
            detail="Extraction returned malformed structure. Please retry.",
        )
    except LLMServiceError as err:
        raise HTTPException(status_code=503, detail=str(err))
    except ValueError as err:
        # Pydantic validation errors raised by ProvisionalMap (e.g., closure failure).
        raise HTTPException(status_code=422, detail=str(err))
    except Exception as err:
        logger.exception("Unexpected failure in /api/extract")
        raise HTTPException(
            status_code=500, detail="Unexpected server error during extraction."
        ) from err
```

- [ ] **Step 5: Run the new error-mapping tests**

Run: `pytest tests/test_extract_route_error_mapping.py -v`
Expected: 4 PASS

- [ ] **Step 6: Run the broader suite**

Run: `pytest tests/ -v --ignore=tests/e2e`
Expected: green except possibly tests that asserted the old wire shape. Fix any frontend-expectation tests if needed (the response body keeps `knowledge_map` as a dict, so JSON consumers should be unchanged).

- [ ] **Step 7: Commit**

```bash
git add main.py tests/test_extract_route_error_mapping.py
git commit -m "feat(extract-route): map normalized LLM errors to HTTP statuses"
```

---

## Self-Review

After tasks 1-10 are implemented, re-read this plan against `docs/superpowers/specs/2026-05-01-foundation-design.md`:

- **Spec 5.1 — cognitive artifact contract**: covered by Task 8 (ProvisionalMap + identifiers + closure)
- **Spec 5.2 — LLM seam**: covered by Tasks 1-6 (types, errors, adapter, client, gemini_adapter, factory)
- **Spec 5.3 — architectural invariant**: covered by Task 7 (isolation test)
- **Spec 5.4 — prompt registry**: NOT in this plan. Deferred to a follow-up plan; the `EXTRACT_PROMPT_PATH.read_text()` call in Task 9 still uses the legacy direct file read.
- **Spec 5.5 — model selection**: partially covered by Task 6 (`build_llm_client` reads `LLM_PROVIDER`/`LLM_MODEL`); per-stage override env vars are not yet implemented.
- **Spec 5.6 — golden fixtures**: NOT in this plan. Deferred to a follow-up plan.
- **Spec 5.7 — Stage 0 intake_mode**: NOT in this plan.
- **Spec 5.8 — static analysis**: NOT in this plan.

The first execution sweep (Tasks 1-10) implements the LLM seam, the `ProvisionalMap` contract, and the first migration. Follow-up plans will cover prompt registry, golden fixtures, intake_mode, drill/repair-reps migration, and static analysis.

After all tasks land, write **ADR-0001** (ProvisionalMap as typed contract) and **ADR-0003** (LLM seam — application asks for cognitive artifacts) under `docs/adr/`. ADR-0002 (prompt registry shape) waits for the registry implementation.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-01-llm-seam-foundation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
