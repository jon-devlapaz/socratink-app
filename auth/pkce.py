"""PKCE primitives per RFC 7636. Pure functions, no IO."""

from __future__ import annotations

import base64
import hashlib
import secrets


def generate_verifier() -> str:
    """Return a high-entropy code_verifier in the PKCE-spec length range (43–128 chars)."""
    # secrets.token_urlsafe(64) yields ~86 url-safe chars, well within [43, 128].
    return secrets.token_urlsafe(64)


def challenge_from_verifier(verifier: str) -> str:
    """Return the S256 code_challenge for the given verifier (no padding, url-safe)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
