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
    """The provider returned a transport-level or upstream failure
    (Gemini 5xx, network timeouts, malformed transport response).

    Distinct from ``LLMValidationError`` — the model produced no usable content.
    """


class LLMValidationError(LLMError):
    """The provider returned content but it failed schema validation.

    Distinct from ``LLMServiceError`` — content arrived; it just was not
    shaped like the requested Pydantic model. Carries ``raw_text`` so callers
    can log, record, or refresh fixtures.
    """

    def __init__(self, message: str, *, raw_text: str | None = None):
        super().__init__(message)
        self.raw_text = raw_text
