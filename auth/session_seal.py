"""Fernet-sealed session-token cookie payload."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet


def validate_session_cookie_key(key: str) -> None:
    """Validate that the given key is a valid Fernet key."""
    try:
        Fernet(key.encode())
    except Exception as err:
        raise ValueError("Invalid Fernet key") from err


def seal_session_tokens(tokens: dict[str, Any], *, key: str) -> str:
    """Seal {access_token, refresh_token, expires_at} into a Fernet token string."""
    payload = json.dumps(tokens, separators=(",", ":")).encode("utf-8")
    return Fernet(key.encode()).encrypt(payload).decode("ascii")


def unseal_session_tokens(blob: str, *, key: str) -> dict[str, Any]:
    """Decrypt and JSON-parse a sealed session blob.

    Raises ValueError on tamper, bad key, or garbage.
    """
    try:
        raw = Fernet(key.encode()).decrypt(blob.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except Exception as err:
        raise ValueError("Invalid sealed session blob") from err
