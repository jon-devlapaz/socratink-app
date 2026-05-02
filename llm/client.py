"""LLMClient — wraps an adapter with retry, telemetry, and timing.

This is the public surface application code uses. The application calls
``client.generate_structured(request)`` and gets a ``StructuredLLMResult``
or one of the normalized exceptions from ``llm.errors``.
"""
from __future__ import annotations

from dataclasses import dataclass

from .adapter import LLMAdapter
from .types import StructuredLLMRequest, StructuredLLMResult


@dataclass
class LLMClient:
    """Application-facing client. Owns retry policy and telemetry.

    Construct via ``llm.build_llm_client(...)`` for the configured provider.
    """

    adapter: LLMAdapter

    def generate_structured(self, request: StructuredLLMRequest) -> StructuredLLMResult:
        return self.adapter.call_once(request)
