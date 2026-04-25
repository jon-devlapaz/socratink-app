"""Sign + verify a single OAuth state cookie carrying nonce, return_to, code_verifier.

One signed cookie covers CSRF (nonce) + open-redirect protection (return_to)
+ PKCE verifier persistence — no server-side state needed.

The token is base64url-encoded so the cookie value contains only safe ASCII
characters and avoids Python's `http.cookies.SimpleCookie` octal/backslash
escaping (which browsers do not unescape — RFC 6265 vs RFC 2109 mismatch).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import asdict, dataclass


@dataclass(slots=True)
class OAuthState:
    nonce: str
    return_to: str
    code_verifier: str
    issued_at: int


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(token: str) -> bytes:
    padded = token + "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def sign_state(state: OAuthState, secret: str) -> str:
    """Return a base64url-encoded HMAC-SHA256-signed payload safe for cookies."""
    raw = json.dumps(asdict(state), separators=(",", ":"))
    sig = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    wrapper = json.dumps({"payload": raw, "sig": sig}, separators=(",", ":"))
    return _b64url_encode(wrapper.encode("utf-8"))


def verify_state(token: str, *, secret: str, max_age_seconds: int) -> OAuthState | None:
    """Return the decoded OAuthState, or None on tamper / expiry / garbage."""
    try:
        wrapper_json = _b64url_decode(token).decode("utf-8")
        wrapper = json.loads(wrapper_json)
        raw = wrapper["payload"]
        sig = wrapper["sig"]
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, base64.binascii.Error):
        return None

    expected = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None

    try:
        payload = json.loads(raw)
        issued_at = int(payload["issued_at"])
        if int(time.time()) - issued_at > max_age_seconds:
            return None
        return OAuthState(
            nonce=str(payload["nonce"]),
            return_to=str(payload["return_to"]),
            code_verifier=str(payload["code_verifier"]),
            issued_at=issued_at,
        )
    except (ValueError, KeyError, TypeError):
        return None
