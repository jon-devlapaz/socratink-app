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
    """The provider returned a transient transport / upstream failure
    (Gemini 5xx, network timeouts, malformed transport response).

    These ARE retried by ``LLMClient``. Distinct from ``LLMClientError``,
    which is permanent (no retry), and ``LLMValidationError``, which means
    the provider returned content but it failed schema validation.
    """


class LLMClientError(LLMError):
    """A permanent client-side failure: Gemini rejected the request
    (HTTP 4xx other than 429). Causes include expired/invalid API key,
    unknown model name, malformed request, quota exhausted (non-rate-limit).

    NOT retried by ``LLMClient`` — retrying a 4xx wastes quota and time.
    The route layer should map this to a 503 to the learner (the cause is
    operator-misconfiguration, not a learner action) and surface the
    underlying message to the operator's logs.
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
