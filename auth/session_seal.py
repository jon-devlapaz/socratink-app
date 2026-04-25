"""Fernet-sealed session-token cookie payload."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet


def seal_session_tokens(tokens: dict[str, Any], *, key: str) -> str:
    """Seal {access_token, refresh_token, expires_at} into a Fernet token string."""
    payload = json.dumps(tokens, separators=(",", ":")).encode("utf-8")
    return Fernet(key.encode()).encrypt(payload).decode("ascii")


def unseal_session_tokens(blob: str, *, key: str) -> dict[str, Any]:
    """Decrypt and JSON-parse a sealed session blob.

    Raises cryptography.fernet.InvalidToken on tamper, bad key, or garbage.
    """
    raw = Fernet(key.encode()).decrypt(blob.encode("ascii"))
    return json.loads(raw.decode("utf-8"))
