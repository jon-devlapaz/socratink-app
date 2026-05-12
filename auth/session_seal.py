"""Fernet-sealed session-token cookie payload."""

from __future__ import annotations

import json
from typing import TypedDict

from cryptography.fernet import Fernet


class SessionTokenPayload(TypedDict):
    access_token: str
    refresh_token: str
    expires_at: int | None


def validate_session_cookie_key(key: str) -> None:
    """Validate that the given key is a valid Fernet key."""
    try:
        Fernet(key.encode())
    except Exception as err:
        raise ValueError("Invalid Fernet key") from err


def seal_session_tokens(tokens: SessionTokenPayload, *, key: str) -> str:
    """Seal {access_token, refresh_token, expires_at} into a Fernet token string."""
    payload = json.dumps(tokens, separators=(",", ":")).encode("utf-8")
    return Fernet(key.encode()).encrypt(payload).decode("ascii")


def _coerce_session_token_payload(payload: object) -> SessionTokenPayload:
    if not isinstance(payload, dict):
        raise ValueError("Invalid sealed session blob")
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_at = payload.get("expires_at")
    if not isinstance(access_token, str) or not isinstance(refresh_token, str):
        raise ValueError("Invalid sealed session blob")
    if expires_at is not None and not isinstance(expires_at, int):
        raise ValueError("Invalid sealed session blob")
    return SessionTokenPayload(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )


def unseal_session_tokens(blob: str, *, key: str) -> SessionTokenPayload:
    """Decrypt and JSON-parse a sealed session blob.

    Raises ValueError on tamper, bad key, or garbage.
    """
    try:
        raw = Fernet(key.encode()).decrypt(blob.encode("ascii"))
        return _coerce_session_token_payload(json.loads(raw.decode("utf-8")))
    except Exception as err:
        raise ValueError("Invalid sealed session blob") from err
