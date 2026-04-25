"""Sign + verify a single OAuth state cookie carrying nonce, return_to, code_verifier.

One signed cookie covers CSRF (nonce) + open-redirect protection (return_to)
+ PKCE verifier persistence — no server-side state needed.
"""

from __future__ import annotations

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


def sign_state(state: OAuthState, secret: str) -> str:
    """Return a JSON-wrapped HMAC-SHA256-signed payload."""
    raw = json.dumps(asdict(state), separators=(",", ":"))
    sig = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return json.dumps({"payload": raw, "sig": sig}, separators=(",", ":"))


def verify_state(token: str, *, secret: str, max_age_seconds: int) -> OAuthState | None:
    """Return the decoded OAuthState, or None on tamper / expiry / garbage."""
    try:
        wrapper = json.loads(token)
        raw = wrapper["payload"]
        sig = wrapper["sig"]
    except (ValueError, KeyError, TypeError):
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
