"""Domain exceptions for source_intake.

These are the only exceptions raised by source_intake module functions.
Routes map them to HTTP responses via main._map_intake_error.
"""


class SourceIntakeError(Exception):
    """Base for all domain exceptions raised by source_intake."""


class InvalidUrl(SourceIntakeError):
    """Malformed URL, missing hostname, or invalid port.

    Note: scheme errors (file://, gopher://, etc.) are NOT InvalidUrl;
    they raise BlockedSource(reason="blocked_scheme").
    """


class BlockedSource(SourceIntakeError):
    """Source refused by policy: SSRF private address, port not in {80,443},
    unsupported scheme, or video denylist match.

    Reason attribute carries the specific category for server-side logging
    and route-layer UX differentiation. The route mapping collapses
    private_address to the same generic 502 response as FetchFailed (oracle
    defense); other reasons surface specific user messages.
    """

    def __init__(self, message: str, *, reason: str):
        super().__init__(message)
        # one of: "private_address" | "blocked_port" | "blocked_video" | "blocked_scheme"
        self.reason = reason


class FetchFailed(SourceIntakeError):
    """Network-layer failure: DNS, connect, timeout, or upstream HTTP error.

    Cause attribute carries the specific failure mode for server-side logging.
    All causes collapse to the same generic 502 response at the route layer
    (oracle defense — attacker cannot distinguish DNS from connect from 5xx).
    """

    def __init__(self, message: str, *, cause: str):
        super().__init__(message)
        # one of: "dns" | "connect" | "timeout" | "http_4xx" | "http_5xx"
        self.cause = cause


class UnsupportedContent(SourceIntakeError):
    """Content-type not in {text/html, text/plain}, or content-encoding != identity."""


class TooLarge(SourceIntakeError):
    """Streamed bytes exceeded MAX_BYTES (2 MB)."""


class ParseEmpty(SourceIntakeError):
    """Extracted text below min_text_length after parsing."""
