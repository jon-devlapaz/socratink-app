"""Supabase access-token JWT verification (HS256)."""

from __future__ import annotations

from typing import Any

import jwt


class InvalidAccessToken(Exception):
    """Raised when the access token is structurally invalid, wrong audience/issuer/role,
    missing required claims, or has a bad signature."""


class TokenExpired(Exception):
    """Raised specifically when the token signature is valid but exp is past now."""


def verify_access_token(
    token: str, *, jwt_secret: str, issuer: str
) -> dict[str, Any]:
    """Verify a Supabase access token and return its claims.

    Validates signature (HS256), audience ("authenticated"), issuer (must match
    project), required `sub`, and `role == "authenticated"`. Raises TokenExpired
    on expiry, InvalidAccessToken otherwise.
    """
    try:
        claims = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=issuer,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.ExpiredSignatureError as err:
        raise TokenExpired(str(err)) from err
    except jwt.PyJWTError as err:
        raise InvalidAccessToken(str(err)) from err

    if claims.get("role") != "authenticated":
        raise InvalidAccessToken("role claim is not 'authenticated'")
    if not claims.get("sub"):
        raise InvalidAccessToken("missing sub claim")
    return claims
