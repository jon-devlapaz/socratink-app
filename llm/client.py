"""LLMClient — wraps an adapter with retry, telemetry, and timing.

This is the public surface application code uses. The application calls
``client.generate_structured(request)`` and gets a ``StructuredLLMResult``
or one of the normalized exceptions from ``llm.errors``.

The adapter does one thing: translate request -> SDK call -> result, or
raise a normalized error. The client does policy: retry on transient
provider failures (rate-limit, service errors), but never retry on
schema-validation or missing-key failures.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, replace

from .adapter import LLMAdapter
from .errors import LLMRateLimitError, LLMServiceError
from .types import StructuredLLMRequest, StructuredLLMResult


@dataclass
class LLMClient:
    """Application-facing client. Owns retry policy and telemetry."""

    adapter: LLMAdapter

    def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        last_exc: Exception | None = None
        for attempt in range(request.max_retries + 1):
            start = time.perf_counter()
            try:
                result = self.adapter.call_once(request)
            except (LLMRateLimitError, LLMServiceError) as exc:
                last_exc = exc
                if attempt < request.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                raise
            # Adapter populates latency; we override with our wall-clock
            # measurement so retries do not inflate the figure.
            latency_ms = (time.perf_counter() - start) * 1000.0
            return replace(result, latency_ms=latency_ms)
        # Defensive — only reachable if max_retries < 0, which the dataclass
        # default does not allow.
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("LLMClient exhausted retries without raising")  # pragma: no cover

    @staticmethod
    def _sleep_backoff(attempt: int) -> None:
        time.sleep(2 ** attempt)
