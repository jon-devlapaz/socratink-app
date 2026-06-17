"""Factory for building the Gemini-backed LLMClient.

Reads:
  - ``LLM_MODEL`` (default ``"gemini-2.5-flash"``)

Optional ``api_key`` argument lets callers (e.g., the /api/extract route)
override the env-resolved key with a per-request key. The adapter still
falls back to the env var if neither is provided.
"""
from __future__ import annotations

import os

from .client import LLMClient
from .gemini_adapter import GeminiAdapter

_DEFAULT_MODEL = "gemini-2.5-flash"


def build_llm_client(*, api_key: str | None = None) -> LLMClient:
    """Construct the Gemini-backed LLMClient."""
    model = os.environ.get("LLM_MODEL", _DEFAULT_MODEL).strip()
    if not model:
        raise ValueError("LLM_MODEL must be non-empty.")
    adapter = GeminiAdapter(api_key=api_key, model=model)
    return LLMClient(adapter=adapter)
