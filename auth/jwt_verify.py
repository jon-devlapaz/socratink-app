"""Supabase access-token JWT verification.

Auto-selects between two verification paths based on the JWT header:

  - **Legacy HS256** (no `kid` claim): symmetric verification with the
    project's `SUPABASE_JWT_SECRET`. Default for older Supabase projects.
  - **Asymmetric ES256 / RS256 / EdDSA** (`kid` claim present): public-key
    verification via the project's JWKS endpoint at
    `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. Default for new Supabase
    projects (signing-keys feature, late 2024+).

Callers pass both `jwt_secret` (legacy) and `supabase_url` (JWKS discovery).
The verifier picks the right path automatically from the JWT header.
"""

from __future__ import annotations

from typing import Any

import jwt


class InvalidAccessToken(Exception):
    """Raised when the access token is structurally invalid, wrong audience/issuer/role,
    missing required claims, or has a bad signature."""


class TokenExpired(Exception):
    """Raised specifically when the token signature is valid but exp is past now."""


# Module-level cache: one PyJWKClient per JWKS URL. PyJWKClient caches
# fetched keys internally with a default TTL.
_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def _get_jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = jwt.PyJWKClient(jwks_url, cache_keys=True)
        _jwks_clients[jwks_url] = client
    return client


_ASYMMETRIC_ALGS = {"ES256", "RS256", "EdDSA"}


def verify_access_token(
    token: str,
    *,
    jwt_secret: str | None = None,
    supabase_url: str | None = None,
    issuer: str,
) -> dict[str, Any]:
    """Verify a Supabase access token and return its claims.

    Validates signature, audience (`authenticated`), issuer (must match the
    project), required `sub`, and `role == "authenticated"`. Raises
    `TokenExpired` on expiry, `InvalidAccessToken` otherwise.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as err:
        raise InvalidAccessToken(f"could not decode JWT header: {err}") from err

    alg = header.get("alg")
    kid = header.get("kid")

    try:
        if kid and supabase_url and alg in _ASYMMETRIC_ALGS:
            jwks_url = (
                f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            )
            client = _get_jwks_client(jwks_url)
            signing_key = client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[alg],
                audience="authenticated",
                issuer=issuer,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            )
        elif jwt_secret:
            claims = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                issuer=issuer,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            )
        else:
            raise InvalidAccessToken(
                f"no signing key available: alg={alg} kid={kid} "
                f"jwt_secret={'set' if jwt_secret else 'unset'} "
                f"supabase_url={'set' if supabase_url else 'unset'}"
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
