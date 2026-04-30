"""source_intake — unified content intake module.

Public surface:
    ImportedSource          — value type (URL or text → normalized text source)
    from_url(url)           — fetch + parse
    from_text(text)         — normalize raw text submission
    errors (re-exported)    — SourceIntakeError + 6 subclasses
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import (
    BlockedSource,
    FetchFailed,
    InvalidUrl,
    ParseEmpty,
    SourceIntakeError,
    TooLarge,
    UnsupportedContent,
)

__all__ = [
    "ImportedSource",
    "from_url",
    "from_text",
    "SourceIntakeError",
    "InvalidUrl",
    "BlockedSource",
    "FetchFailed",
    "UnsupportedContent",
    "TooLarge",
    "ParseEmpty",
]


@dataclass(frozen=True)
class ImportedSource:
    """An imported text source, ready for Gemini extraction.

    Either fetched from a URL (via from_url) or supplied as raw text
    (via from_text). Carries the canonical (post-redirect) URL when present.

    is_remote_source flags content as remote-attacker-controllable for
    downstream prompt-injection awareness in ai_service.py extraction prompt
    assembly. Per OWASP LLM01.
    """
    url: str | None             # final_url after redirects, or None for from_text
    title: str                  # max 200 chars, never empty
    text: str                   # max 500_000 chars
    is_remote_source: bool      # True from from_url, False from from_text

    def to_dict(self) -> dict:
        """JSON shape for the /api/extract-url response.

        Intentionally omits is_remote_source — that flag is internal-only.
        Regression test test_to_dict_omits_is_remote_source enforces this.
        """
        return {"url": self.url, "title": self.title, "text": self.text}


# from_url and from_text implemented in Task 13 (facade).
