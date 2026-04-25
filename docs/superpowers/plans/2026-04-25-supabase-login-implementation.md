# Supabase Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace WorkOS auth with Supabase Auth (Google OAuth + Supabase anonymous sign-in for guest mode), preserving the server-side httpOnly sealed-cookie session model.

**Architecture:** PKCE-flavored server-side OAuth: `/auth/google` builds a PKCE verifier + challenge, signs both into a single state cookie, and redirects to Supabase's `/auth/v1/authorize`. `/auth/callback` verifies the state cookie, exchanges the code via `supabase-py`, seals `{access_token, refresh_token, expires_at}` into a Fernet cookie, and redirects to `return_to`. `/auth/guest` calls `client.auth.sign_in_anonymously()` and seals into the same cookie shape. `load_session` verifies the access JWT locally with HS256 + `SUPABASE_JWT_SECRET`; on expiry it refreshes via `supabase-py` and re-seals.

**Tech Stack:** FastAPI + static HTML on Vercel; Python `supabase` (>=2.3) for OAuth code exchange + refresh; `pyjwt[crypto]` for HS256 verification; `cryptography.fernet` for cookie sealing.

**Spec source of truth:** `docs/project/supabase-auth-swap.md` (original spec + 2026-04-25 amendment for anonymous sign-in).

---

## Prerequisites (manual, before Task 1)

Complete Phase 0 from the spec:

- [ ] **P0.1** Create Supabase project; note region.
- [ ] **P0.2** GCP Console: create OAuth 2.0 Web Client ID. Authorized redirect URI: `https://<project-ref>.supabase.co/auth/v1/callback`.
- [ ] **P0.3** Supabase Dashboard → Authentication → Providers → Google → paste GCP client ID + secret → enable.
- [ ] **P0.3a** Supabase Dashboard → Authentication → Providers → Email → enable **"Allow anonymous sign-ins"** (per amendment D9).
- [ ] **P0.4** Supabase Dashboard → Authentication → URL Configuration:
  - Site URL: `http://localhost:8000`
  - Redirect URLs allow-list: `http://localhost:8000/auth/callback`, `https://<vercel-prod>.vercel.app/auth/callback`, `https://socratink.app/auth/callback`
- [ ] **P0.5** Supabase Dashboard → Project Settings → API → copy `Project URL`, `anon`/`publishable` key, `JWT secret`.
- [ ] **P0.6** Generate Fernet key locally:
  ```
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- [ ] **P0.7** Set local env vars (`.env` for dev):
  ```
  AUTH_ENABLED=true
  SUPABASE_URL=https://<project-ref>.supabase.co
  SUPABASE_PUBLISHABLE_KEY=<anon key>
  SUPABASE_JWT_SECRET=<JWT secret>
  APP_BASE_URL=http://localhost:8000
  SESSION_COOKIE_KEY=<Fernet key from P0.6>
  ```

**Gate:** before Task 1, manually hit `https://<project-ref>.supabase.co/auth/v1/authorize?provider=google&redirect_to=http://localhost:8000/auth/callback` in a browser; confirm Google consent flow lands at `localhost:8000/auth/callback?code=...`.

---

## File structure

**New files (created across S1–S6, S18):**
- `auth/pkce.py` — PKCE primitives (verifier + challenge). 30 lines, pure.
- `auth/oauth_state.py` — OAuth state cookie sign/verify carrying nonce + return_to + PKCE verifier. 60 lines, pure HMAC.
- `auth/supabase_urls.py` — `/auth/v1/authorize` URL builder. 25 lines, pure.
- `auth/jwt_verify.py` — HS256 access-token verification. 40 lines.
- `auth/session_seal.py` — Fernet seal/unseal of `{access_token, refresh_token, expires_at}`. 30 lines.
- `auth/supabase_client.py` — Stateless `build_supabase_client()` factory. 25 lines.
- `tests/test_supabase_anonymous.py` — Anonymous sign-in service-method tests (S18).

**Modified files:**
- `auth/service.py` — `WorkOSAuthService` deleted; `SupabaseAuthService` added (constructor, `build_oauth_state`, `get_login_url`, `verify_oauth_state`, `exchange_code`, `sign_in_anonymously`, `load_session`, `logout`, `resolve_cookie_secure`, `callback_redirect_uri`).
- `auth/router.py` — handler bodies updated to the new service signatures; `auth_guest` rewritten to call `sign_in_anonymously`; cookie name moves to `sb_session` via service constant.
- `auth/__init__.py` — exports `SupabaseAuthService` instead of `WorkOSAuthService`; `MagicAuthStartState` retained.
- `main.py` — middleware gate writes back refreshed sealed cookie when `state.sealed_session` is non-None.
- `requirements.txt` — `workos` removed; `supabase`, `pyjwt[crypto]`, `cryptography` added.
- `.env.example` — WorkOS keys swapped for Supabase keys.
- `tests/test_auth_router_supabase.py` — extended with `AnonymousGuestTests` (S19).
- `tests/test_supabase_load_session.py` — extended with `AnonymousSessionTests` (S20).
- `tests/test_jwt_verify.py` — extended with `is_anonymous` claim cases (S20).

**Deleted files (in S15):**
- `tests/test_auth_router.py` (WorkOS-shaped, obsolete)
- `tests/test_auth_gate.py` (WorkOS-shaped, obsolete)

---

## Task 1: PKCE primitives (S1)

**Files:**
- Create: `auth/pkce.py`
- Test (already exists, RED): `tests/test_pkce.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_pkce.py -v
```

Expected: `ModuleNotFoundError: No module named 'auth.pkce'` or `ImportError: cannot import name 'generate_verifier'`.

- [ ] **Step 2: Create `auth/pkce.py`**

```python
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
```

- [ ] **Step 3: Run test to verify GREEN**

```bash
pytest tests/test_pkce.py -v
```

Expected: 7 tests pass.

- [ ] **Step 4: Commit**

```bash
git add auth/pkce.py
git commit -m "feat(auth): add PKCE primitives (S1)"
```

---

## Task 2: JWT access-token verifier (S4)

**Files:**
- Create: `auth/jwt_verify.py`
- Test (already exists, RED): `tests/test_jwt_verify.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_jwt_verify.py -v
```

Expected: `ImportError` for `auth.jwt_verify` or its names.

- [ ] **Step 2: Create `auth/jwt_verify.py`**

```python
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
```

- [ ] **Step 3: Run test GREEN**

```bash
pytest tests/test_jwt_verify.py -v
```

Expected: 8 tests pass.

- [ ] **Step 4: Commit**

```bash
git add auth/jwt_verify.py
git commit -m "feat(auth): add Supabase JWT HS256 verifier (S4)"
```

---

## Task 3: Session token sealing (S5)

**Files:**
- Create: `auth/session_seal.py`
- Test (already exists, RED): `tests/test_session_seal.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_session_seal.py -v
```

Expected: import error.

- [ ] **Step 2: Create `auth/session_seal.py`**

```python
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
```

- [ ] **Step 3: Run test GREEN**

```bash
pytest tests/test_session_seal.py -v
```

Expected: 4 tests pass.

- [ ] **Step 4: Commit**

```bash
git add auth/session_seal.py
git commit -m "feat(auth): add Fernet session-token sealing (S5)"
```

---

## Task 4: Supabase authorize URL builder (S3)

**Files:**
- Create: `auth/supabase_urls.py`
- Test (already exists, RED): `tests/test_supabase_authorize_url.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_supabase_authorize_url.py -v
```

Expected: import error.

- [ ] **Step 2: Create `auth/supabase_urls.py`**

```python
"""URL builders for Supabase auth endpoints."""

from __future__ import annotations

from urllib.parse import urlencode


def build_google_authorize_url(
    *,
    supabase_url: str,
    redirect_to: str,
    state_nonce: str,
    code_challenge: str,
) -> str:
    """Return the GET URL for `/auth/v1/authorize` with provider=google + PKCE params."""
    base = supabase_url.rstrip("/")
    qs = urlencode(
        {
            "provider": "google",
            "redirect_to": redirect_to,
            "state": state_nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{base}/auth/v1/authorize?{qs}"
```

- [ ] **Step 3: Run test GREEN**

```bash
pytest tests/test_supabase_authorize_url.py -v
```

Expected: 6 tests pass.

- [ ] **Step 4: Commit**

```bash
git add auth/supabase_urls.py
git commit -m "feat(auth): add Supabase authorize URL builder (S3)"
```

---

## Task 5: Supabase client factory (S6)

**Files:**
- Create: `auth/supabase_client.py`
- Modify: `auth/service.py` (export `AuthConfigurationError` so `auth/supabase_client.py` can re-import; it already exists in `WorkOSAuthService` module — leave it during the migration. The test imports `from auth.service import AuthConfigurationError` which works today.)
- Test (already exists, RED): `tests/test_supabase_client_factory.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_supabase_client_factory.py -v
```

Expected: import error.

- [ ] **Step 2: Create `auth/supabase_client.py`**

```python
"""Stateless per-call Supabase client factory.

Vercel-serverless-safe: never reuse client across requests; never persist sessions.
"""

from __future__ import annotations

from supabase import ClientOptions, create_client

from auth.service import AuthConfigurationError


def build_supabase_client(supabase_url: str, publishable_key: str):
    """Return a fresh Supabase client with persist_session and auto_refresh disabled."""
    if not supabase_url:
        raise AuthConfigurationError("SUPABASE_URL is required.")
    if not publishable_key:
        raise AuthConfigurationError("SUPABASE_PUBLISHABLE_KEY is required.")
    options = ClientOptions(persist_session=False, auto_refresh_token=False)
    return create_client(supabase_url, publishable_key, options=options)
```

- [ ] **Step 3: Run test GREEN**

```bash
pytest tests/test_supabase_client_factory.py -v
```

Expected: 4 tests pass.

- [ ] **Step 4: Commit**

```bash
git add auth/supabase_client.py
git commit -m "feat(auth): add Supabase client factory (S6)"
```

---

## Task 6: OAuth state cookie with PKCE verifier (S2)

**Files:**
- Create: `auth/oauth_state.py`
- Test (already exists, RED): `tests/test_oauth_state_pkce.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_oauth_state_pkce.py -v
```

Expected: import error.

- [ ] **Step 2: Create `auth/oauth_state.py`**

```python
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
```

- [ ] **Step 3: Run test GREEN**

```bash
pytest tests/test_oauth_state_pkce.py -v
```

Expected: 5 tests pass.

- [ ] **Step 4: Commit**

```bash
git add auth/oauth_state.py
git commit -m "feat(auth): add OAuth state cookie with PKCE verifier (S2)"
```

---

## Task 7: SupabaseAuthService skeleton + exchange_code (S7 + S16)

**Files:**
- Modify: `auth/service.py` — append `SupabaseAuthService` alongside existing `WorkOSAuthService` (do NOT delete WorkOS yet; deleted in S15). Keep `AuthUser`, `AuthSessionState`, `AuthConfigurationError`, `MagicAuthStartState` shared.
- Test (already exists, RED): `tests/test_supabase_exchange.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_supabase_exchange.py -v
```

Expected: `ImportError: cannot import name 'SupabaseAuthService'`.

- [ ] **Step 2: Append `SupabaseAuthService` to `auth/service.py`**

Add this near the bottom of `auth/service.py`, **before** `build_auth_service_from_env`:

```python
class SupabaseAuthService:
    """Server-side Supabase auth flow with sealed-cookie sessions."""

    def __init__(
        self,
        *,
        enabled: bool,
        supabase_url: str | None,
        publishable_key: str | None,
        jwt_secret: str | None,
        session_cookie_key: str | None,
        app_base_url: str | None,
        cookie_name: str = "sb_session",
        callback_path: str = "/auth/callback",
        cookie_secure: str = "auto",
        cookie_samesite: str = "lax",
        cookie_max_age: int = 60 * 60 * 24 * 14,
        oauth_state_cookie_name: str = "sb_oauth_state",
        oauth_state_ttl_seconds: int = 60 * 10,
    ) -> None:
        self.enabled = enabled
        self.supabase_url = supabase_url
        self.publishable_key = publishable_key
        self.jwt_secret = jwt_secret
        self.session_cookie_key = session_cookie_key
        self.app_base_url = app_base_url
        self.cookie_name = cookie_name
        self.callback_path = callback_path
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite
        self.cookie_max_age = cookie_max_age
        self.oauth_state_cookie_name = oauth_state_cookie_name
        self.oauth_state_ttl_seconds = oauth_state_ttl_seconds

    # --- configuration helpers ---

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise AuthConfigurationError("Auth is disabled.")
        missing = [
            name
            for name, value in [
                ("SUPABASE_URL", self.supabase_url),
                ("SUPABASE_PUBLISHABLE_KEY", self.publishable_key),
                ("SUPABASE_JWT_SECRET", self.jwt_secret),
                ("SESSION_COOKIE_KEY", self.session_cookie_key),
                ("APP_BASE_URL", self.app_base_url),
            ]
            if not value
        ]
        if missing:
            raise AuthConfigurationError(
                f"Auth is enabled but missing: {', '.join(missing)}"
            )

    def _make_supabase_client(self):
        # Late import keeps test patch surface working & avoids importing supabase
        # at module load time.
        from auth.supabase_client import build_supabase_client

        self._require_enabled()
        assert self.supabase_url and self.publishable_key
        return build_supabase_client(self.supabase_url, self.publishable_key)

    def callback_redirect_uri(self) -> str:
        self._require_enabled()
        assert self.app_base_url
        return f"{self.app_base_url.rstrip('/')}{self.callback_path}"

    def resolve_cookie_secure(self, base_url: str) -> bool:
        mode = (self.cookie_secure or "auto").strip().lower()
        if mode == "true":
            return True
        if mode == "false":
            return False
        return base_url.rstrip("/").startswith("https://")

    # --- exchange ---

    def exchange_code(
        self, *, code: str, code_verifier: str, redirect_uri: str
    ) -> AuthSessionState:
        self._require_enabled()
        client = self._make_supabase_client()
        response = client.auth.exchange_code_for_session(
            {
                "auth_code": code,
                "code_verifier": code_verifier,
                "redirect_to": redirect_uri,
            }
        )
        return self._state_from_response(response)

    # --- shared response → state mapping (used by exchange_code, sign_in_anonymously, refresh) ---

    def _state_from_response(self, response: Any) -> AuthSessionState:
        from auth.session_seal import seal_session_tokens

        session = getattr(response, "session", None)
        user = getattr(response, "user", None)
        access_token = getattr(session, "access_token", None) if session else None
        refresh_token = getattr(session, "refresh_token", None) if session else None
        expires_at = getattr(session, "expires_at", None) if session else None

        sealed = None
        if access_token and refresh_token:
            assert self.session_cookie_key
            sealed = seal_session_tokens(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at,
                },
                key=self.session_cookie_key,
            )
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=_map_supabase_user(user),
            sealed_session=sealed,
        )
```

Also add at the bottom of `auth/service.py`, replacing or alongside `_map_workos_user`:

```python
def _map_supabase_user(user: Any | None) -> AuthUser | None:
    if user is None:
        return None
    metadata = getattr(user, "user_metadata", None) or {}
    full_name = metadata.get("full_name")
    given = metadata.get("given_name")
    family = metadata.get("family_name")

    first_name: str | None = None
    last_name: str | None = None
    if isinstance(full_name, str) and full_name.strip():
        parts = full_name.strip().split(None, 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else None
    elif isinstance(given, str) and given.strip():
        first_name = given.strip()
        last_name = family.strip() if isinstance(family, str) and family.strip() else None

    return AuthUser(
        id=str(getattr(user, "id", "")),
        email=getattr(user, "email", None),
        first_name=first_name,
        last_name=last_name,
    )
```

- [ ] **Step 3: Run test GREEN**

```bash
pytest tests/test_supabase_exchange.py -v
```

Expected: 8 tests pass (5 in `ExchangeCodeTests` + 3 in `UserMetadataMappingTests`).

- [ ] **Step 4: Commit**

```bash
git add auth/service.py
git commit -m "feat(auth): add SupabaseAuthService.exchange_code + user metadata mapping (S7+S16)"
```

---

## Task 8: load_session with refresh + re-seal (S8)

**Files:**
- Modify: `auth/service.py` — add `load_session` method on `SupabaseAuthService`.
- Test (already exists, RED): `tests/test_supabase_load_session.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_supabase_load_session.py -v
```

Expected: `AttributeError: 'SupabaseAuthService' object has no attribute 'load_session'`.

- [ ] **Step 2: Add `load_session` to `SupabaseAuthService` in `auth/service.py`**

Insert after `exchange_code`, before `_state_from_response`:

```python
    def load_session(self, sealed_session: str | None) -> AuthSessionState:
        if not self.enabled:
            return AuthSessionState(auth_enabled=False, authenticated=False)
        if not sealed_session:
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                error_reason="no_session_cookie_provided",
            )

        from cryptography.fernet import InvalidToken

        from auth.jwt_verify import (
            InvalidAccessToken,
            TokenExpired,
            verify_access_token,
        )
        from auth.session_seal import unseal_session_tokens

        self._require_enabled()
        assert self.session_cookie_key and self.jwt_secret and self.supabase_url

        try:
            tokens = unseal_session_tokens(sealed_session, key=self.session_cookie_key)
        except InvalidToken:
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                should_clear_cookie=True,
                error_reason="session_cookie_invalid",
            )

        issuer = f"{self.supabase_url.rstrip('/')}/auth/v1"
        try:
            claims = verify_access_token(
                tokens["access_token"], jwt_secret=self.jwt_secret, issuer=issuer
            )
        except TokenExpired:
            return self._refresh_session(tokens["refresh_token"])
        except InvalidAccessToken:
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                should_clear_cookie=True,
                error_reason="access_token_invalid",
            )

        user_metadata = claims.get("user_metadata") or {}
        # Build a minimal user-shaped object the mapper can read.
        from types import SimpleNamespace

        user = SimpleNamespace(
            id=claims["sub"],
            email=claims.get("email"),
            user_metadata=user_metadata,
        )
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=_map_supabase_user(user),
        )

    def _refresh_session(self, refresh_token: str) -> AuthSessionState:
        try:
            client = self._make_supabase_client()
            response = client.auth.refresh_session(refresh_token)
        except Exception:
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                should_clear_cookie=True,
                error_reason="session_refresh_failed",
            )
        return self._state_from_response(response)
```

- [ ] **Step 3: Run test GREEN**

```bash
pytest tests/test_supabase_load_session.py -v
```

Expected: 6 tests pass.

- [ ] **Step 4: Commit**

```bash
git add auth/service.py
git commit -m "feat(auth): add SupabaseAuthService.load_session with refresh+re-seal (S8)"
```

---

## Task 9: sign_in_anonymously service method (S18, NEW)

**Files:**
- Modify: `auth/service.py` — add `sign_in_anonymously` to `SupabaseAuthService`.
- Create: `tests/test_supabase_anonymous.py`

- [ ] **Step 1: Write the failing test at `tests/test_supabase_anonymous.py`**

```python
"""S18 — sign_in_anonymously: Supabase anonymous user → sealed session."""

import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.fernet import Fernet

from auth.service import AuthConfigurationError, SupabaseAuthService
from auth.session_seal import unseal_session_tokens


SESSION_KEY = Fernet.generate_key().decode()
JWT_SECRET = "jwt-secret"


def _build_service() -> SupabaseAuthService:
    return SupabaseAuthService(
        enabled=True,
        supabase_url="https://abc123.supabase.co",
        publishable_key="pk_test",
        jwt_secret=JWT_SECRET,
        session_cookie_key=SESSION_KEY,
        app_base_url="http://localhost:8000",
    )


def _fake_anon_response():
    user = SimpleNamespace(
        id="anon_uuid_456",
        email=None,
        user_metadata={},
    )
    session = SimpleNamespace(
        access_token="anon.access.jwt",
        refresh_token="anon-refresh-rt",
        expires_at=int(time.time()) + 3600,
    )
    return SimpleNamespace(user=user, session=session)


class SignInAnonymouslyTests(unittest.TestCase):
    def test_returns_authenticated_state_with_sealed_session(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.sign_in_anonymously.return_value = (
                _fake_anon_response()
            )
            state = svc.sign_in_anonymously()
        self.assertTrue(state.authenticated)
        self.assertIsNotNone(state.sealed_session)
        self.assertEqual(state.user.id, "anon_uuid_456")
        self.assertIsNone(state.user.email)

    def test_sdk_called_with_no_arguments(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.sign_in_anonymously.return_value = (
                _fake_anon_response()
            )
            svc.sign_in_anonymously()
            factory.return_value.auth.sign_in_anonymously.assert_called_once_with()

    def test_sealed_session_round_trips_to_anon_tokens(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.sign_in_anonymously.return_value = (
                _fake_anon_response()
            )
            state = svc.sign_in_anonymously()
        decoded = unseal_session_tokens(state.sealed_session, key=SESSION_KEY)
        self.assertEqual(decoded["access_token"], "anon.access.jwt")
        self.assertEqual(decoded["refresh_token"], "anon-refresh-rt")

    def test_sdk_failure_propagates(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.sign_in_anonymously.side_effect = RuntimeError(
                "supabase down"
            )
            with self.assertRaises(Exception):
                svc.sign_in_anonymously()

    def test_disabled_service_raises_configuration_error(self):
        svc = SupabaseAuthService(
            enabled=False,
            supabase_url=None,
            publishable_key=None,
            jwt_secret=None,
            session_cookie_key=None,
            app_base_url=None,
        )
        with self.assertRaises(AuthConfigurationError):
            svc.sign_in_anonymously()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Confirm test is RED**

```bash
pytest tests/test_supabase_anonymous.py -v
```

Expected: `AttributeError: 'SupabaseAuthService' object has no attribute 'sign_in_anonymously'`.

- [ ] **Step 3: Add `sign_in_anonymously` to `SupabaseAuthService` in `auth/service.py`**

Insert after `exchange_code`:

```python
    def sign_in_anonymously(self) -> AuthSessionState:
        self._require_enabled()
        client = self._make_supabase_client()
        response = client.auth.sign_in_anonymously()
        return self._state_from_response(response)
```

- [ ] **Step 4: Run test GREEN**

```bash
pytest tests/test_supabase_anonymous.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_supabase_anonymous.py auth/service.py
git commit -m "feat(auth): add SupabaseAuthService.sign_in_anonymously (S18)"
```

---

## Task 10: is_anonymous JWT claim propagation (S20, NEW)

**Files:**
- Modify: `auth/jwt_verify.py` — surface `is_anonymous` flag (boolean, defaulting False if absent).
- Modify: `auth/service.py` — read `is_anonymous` from claims in `load_session`; set `AuthSessionState.guest_mode` from it.
- Modify: `tests/test_jwt_verify.py` — extend with anonymous-claim cases.
- Modify: `tests/test_supabase_load_session.py` — extend with `AnonymousSessionTests`.

- [ ] **Step 1: Append failing tests to `tests/test_jwt_verify.py`**

Add these cases after `class VerifyAccessTokenTests` (before the `if __name__` block):

```python
class IsAnonymousClaimTests(unittest.TestCase):
    def test_is_anonymous_true_surfaced_in_claims(self):
        token = _make_token(is_anonymous=True)
        claims = verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)
        self.assertTrue(claims.get("is_anonymous"))

    def test_is_anonymous_false_when_absent(self):
        token = _make_token()
        claims = verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)
        # Treat absence as False; explicit False also acceptable.
        self.assertFalse(claims.get("is_anonymous", False))
```

- [ ] **Step 2: Append failing tests to `tests/test_supabase_load_session.py`**

Add this class after `class LoadSessionTests` (before the `if __name__` block):

```python
class AnonymousSessionTests(unittest.TestCase):
    def test_anonymous_session_sets_guest_mode(self):
        svc = _make_service()
        sealed = seal_session_tokens(
            {
                "access_token": jwt.encode(
                    {
                        "aud": "authenticated",
                        "iss": ISSUER,
                        "sub": "anon_uuid_456",
                        "role": "authenticated",
                        "iat": int(time.time()),
                        "exp": int(time.time()) + 3600,
                        "is_anonymous": True,
                    },
                    JWT_SECRET,
                    algorithm="HS256",
                ),
                "refresh_token": "rt_anon",
                "expires_at": int(time.time()) + 3600,
            },
            key=SESSION_KEY,
        )
        state = svc.load_session(sealed)
        self.assertTrue(state.authenticated)
        self.assertTrue(state.guest_mode)
        self.assertEqual(state.user.id, "anon_uuid_456")

    def test_authenticated_session_keeps_guest_mode_false(self):
        svc = _make_service()
        state = svc.load_session(_seal())
        self.assertTrue(state.authenticated)
        self.assertFalse(state.guest_mode)
```

- [ ] **Step 3: Confirm both test files RED**

```bash
pytest tests/test_jwt_verify.py::IsAnonymousClaimTests tests/test_supabase_load_session.py::AnonymousSessionTests -v
```

Expected: `IsAnonymousClaimTests` passes (it just reads what's in claims dict — already happens via `jwt.decode`), `AnonymousSessionTests` fails because `guest_mode` is never set.

- [ ] **Step 4: Update `auth/service.py` `load_session` to set `guest_mode`**

In `load_session`, replace the trailing `return AuthSessionState(...)` block (the success-after-verify branch) with:

```python
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=_map_supabase_user(user),
            guest_mode=bool(claims.get("is_anonymous", False)),
        )
```

Also update `_state_from_response` to propagate `is_anonymous` from the user object when present (the SDK exposes it as `user.is_anonymous`). Replace the existing return statement at the end of `_state_from_response`:

```python
        is_anon = bool(getattr(user, "is_anonymous", False)) if user is not None else False
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=_map_supabase_user(user),
            guest_mode=is_anon,
            sealed_session=sealed,
        )
```

- [ ] **Step 5: Run tests GREEN**

```bash
pytest tests/test_jwt_verify.py tests/test_supabase_load_session.py tests/test_supabase_anonymous.py tests/test_supabase_exchange.py -v
```

Expected: all pass; no regressions in `ExchangeCodeTests` or `LoadSessionTests` (existing tests don't set `guest_mode`, and `AuthSessionState.guest_mode` defaults to `False`).

- [ ] **Step 6: Commit**

```bash
git add auth/service.py tests/test_jwt_verify.py tests/test_supabase_load_session.py
git commit -m "feat(auth): propagate is_anonymous claim into guest_mode (S20)"
```

---

## Task 11: APP_BASE_URL host hardening (S13)

**Files:**
- Modify: `auth/service.py` — `callback_redirect_uri()` already added in Task 7; verify the test passes against the existing impl.
- Test (already exists, RED): `tests/test_app_base_url.py`

- [ ] **Step 1: Run the test**

```bash
pytest tests/test_app_base_url.py -v
```

Expected: tests pass — `callback_redirect_uri()` was added in Task 7 and already raises `AuthConfigurationError` when `app_base_url` is None (via `_require_enabled` checking missing keys).

- [ ] **Step 2: If any test fails, inspect and patch `callback_redirect_uri()`**

The test at `tests/test_app_base_url.py:46-55` expects: when `enabled=True` but `app_base_url=None`, calling `callback_redirect_uri()` raises `AuthConfigurationError`. The Task 7 implementation does this via `_require_enabled` (which lists `APP_BASE_URL` in the missing-fields check). Confirm.

- [ ] **Step 3: Commit (only if changes were needed)**

If the test already passes, no commit needed — note in the commit log of the next task.

```bash
# Only if any code changed:
git add auth/service.py
git commit -m "feat(auth): harden callback_redirect_uri against host spoofing (S13)"
```

---

## Task 12: build_auth_service_from_env rewrite (S14)

**Files:**
- Modify: `auth/__init__.py` — re-export `SupabaseAuthService`.
- Modify: `auth/service.py` — replace `build_auth_service_from_env` body with Supabase env-var reads. Keep the function name + signature; tests + `main.py` import it.
- Test (already exists, RED): `tests/test_auth_factory.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_auth_factory.py -v
```

Expected: tests fail because `build_auth_service_from_env()` returns a `WorkOSAuthService`, not a `SupabaseAuthService`.

- [ ] **Step 2: Replace `build_auth_service_from_env` body in `auth/service.py`**

Replace the existing function with:

```python
def build_auth_service_from_env() -> "SupabaseAuthService":
    return SupabaseAuthService(
        enabled=_env_flag("AUTH_ENABLED", False),
        supabase_url=_env_value("SUPABASE_URL"),
        publishable_key=_env_value("SUPABASE_PUBLISHABLE_KEY"),
        jwt_secret=_env_value("SUPABASE_JWT_SECRET"),
        session_cookie_key=_env_value("SESSION_COOKIE_KEY"),
        app_base_url=_env_value("APP_BASE_URL"),
        cookie_name=_env_value("AUTH_COOKIE_NAME", "sb_session") or "sb_session",
        callback_path=_env_value("AUTH_CALLBACK_PATH", "/auth/callback")
        or "/auth/callback",
        cookie_secure=_env_value("AUTH_COOKIE_SECURE", "auto") or "auto",
        cookie_samesite=_env_value("AUTH_COOKIE_SAMESITE", "lax") or "lax",
        cookie_max_age=int(
            _env_value("AUTH_COOKIE_MAX_AGE", str(60 * 60 * 24 * 14))
            or str(60 * 60 * 24 * 14)
        ),
        oauth_state_cookie_name=_env_value("AUTH_STATE_COOKIE_NAME", "sb_oauth_state")
        or "sb_oauth_state",
        oauth_state_ttl_seconds=int(
            _env_value("AUTH_STATE_TTL_SECONDS", str(60 * 10)) or str(60 * 10)
        ),
    )
```

- [ ] **Step 3: Update `auth/__init__.py` exports**

Replace contents:

```python
from .router import GUEST_COOKIE_NAME, GUEST_COOKIE_VALUE, auth_router
from .service import (
    AuthConfigurationError,
    AuthSessionState,
    AuthUser,
    MagicAuthStartState,
    SupabaseAuthService,
    build_auth_service_from_env,
)

__all__ = [
    "AuthConfigurationError",
    "AuthSessionState",
    "AuthUser",
    "GUEST_COOKIE_NAME",
    "GUEST_COOKIE_VALUE",
    "MagicAuthStartState",
    "SupabaseAuthService",
    "auth_router",
    "build_auth_service_from_env",
]
```

(Keep `GUEST_COOKIE_NAME` / `GUEST_COOKIE_VALUE` exports for now — Task 18 cleans them up after the router rewrite.)

- [ ] **Step 4: Run tests GREEN**

```bash
pytest tests/test_auth_factory.py tests/test_supabase_exchange.py tests/test_supabase_load_session.py -v
```

Expected: factory tests pass; no regressions.

- [ ] **Step 5: Commit**

```bash
git add auth/service.py auth/__init__.py
git commit -m "feat(auth): build Supabase service from env (S14)"
```

---

## Task 13: build_oauth_state + get_login_url + verify_oauth_state on SupabaseAuthService (S9 prep)

**Files:**
- Modify: `auth/service.py` — add the three OAuth-state-related methods to `SupabaseAuthService`.

The `auth_router_supabase` test in Task 14 expects:
- `service.build_oauth_state(return_to=...)` returns 4-tuple `(nonce, code_verifier, code_challenge, signed_state_cookie)`
- `service.get_login_url(state_nonce=..., code_challenge=...)` returns the Supabase authorize URL
- `service.verify_oauth_state(state=..., signed_cookie=...)` returns `(return_to, code_verifier)` on success or `None` on failure

This task is a preparatory refactor with no test of its own; it gets exercised in Task 14.

- [ ] **Step 1: Add methods to `SupabaseAuthService` in `auth/service.py`**

Insert after `_require_enabled`:

```python
    def build_oauth_state(self, *, return_to: str) -> tuple[str, str, str, str]:
        """Build (nonce, verifier, challenge, signed_state_cookie) for /auth/google."""
        from auth.oauth_state import OAuthState, sign_state
        from auth.pkce import challenge_from_verifier, generate_verifier
        import secrets
        import time

        self._require_enabled()
        assert self.session_cookie_key
        nonce = secrets.token_urlsafe(24)
        verifier = generate_verifier()
        challenge = challenge_from_verifier(verifier)
        state = OAuthState(
            nonce=nonce,
            return_to=return_to,
            code_verifier=verifier,
            issued_at=int(time.time()),
        )
        return nonce, verifier, challenge, sign_state(state, self.session_cookie_key)

    def get_login_url(self, *, state_nonce: str, code_challenge: str) -> str:
        from auth.supabase_urls import build_google_authorize_url

        self._require_enabled()
        assert self.supabase_url
        return build_google_authorize_url(
            supabase_url=self.supabase_url,
            redirect_to=self.callback_redirect_uri(),
            state_nonce=state_nonce,
            code_challenge=code_challenge,
        )

    def verify_oauth_state(
        self, *, state: str | None, signed_cookie: str | None
    ) -> tuple[str, str] | None:
        """Return (return_to, code_verifier) on success, else None."""
        import secrets

        from auth.oauth_state import verify_state

        self._require_enabled()
        assert self.session_cookie_key
        if not state or not signed_cookie:
            return None
        decoded = verify_state(
            signed_cookie,
            secret=self.session_cookie_key,
            max_age_seconds=self.oauth_state_ttl_seconds,
        )
        if decoded is None:
            return None
        if not secrets.compare_digest(decoded.nonce, state):
            return None
        return decoded.return_to, decoded.code_verifier
```

- [ ] **Step 2: Add `logout` method (called by router in Task 14)**

Insert after `verify_oauth_state`:

```python
    def logout(self, sealed_session: str | None) -> None:
        # Best-effort remote sign-out; failures are not fatal because the cookie
        # is being cleared regardless.
        if not self.enabled or not sealed_session:
            return
        try:
            tokens = self._unseal_or_none(sealed_session)
            if tokens is None:
                return
            client = self._make_supabase_client()
            # supabase-py global sign_out is fine; access token scoped on client.
            client.auth.sign_out()
        except Exception:
            pass

    def _unseal_or_none(self, sealed_session: str):
        from cryptography.fernet import InvalidToken

        from auth.session_seal import unseal_session_tokens

        try:
            assert self.session_cookie_key
            return unseal_session_tokens(sealed_session, key=self.session_cookie_key)
        except InvalidToken:
            return None
```

- [ ] **Step 3: Smoke-check service-level tests still green**

```bash
pytest tests/test_supabase_exchange.py tests/test_supabase_load_session.py tests/test_supabase_anonymous.py tests/test_app_base_url.py tests/test_auth_factory.py -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add auth/service.py
git commit -m "feat(auth): add OAuth-state + login-url + logout helpers to SupabaseAuthService (S9 prep)"
```

---

## Task 14: Rewrite auth/router.py for Supabase (S9 + S10 + S11)

**Files:**
- Modify: `auth/router.py` — replace handler bodies. Keep magic-auth 503 endpoints. Keep `GUEST_COOKIE_NAME` constant + `_apply_guest_cookie` for now (removed in Task 18).
- Test (already exists, RED): `tests/test_auth_router_supabase.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_auth_router_supabase.py -v
```

Expected: many failures because router calls today's WorkOS-shaped service interface.

- [ ] **Step 2: Replace `auth/router.py`**

Open `auth/router.py`. Replace **all five handler bodies + the helpers feeding them** with the Supabase-shaped versions below. Leave the embedded login HTML / CSS / JS, `_render_login_html`, `sanitize_return_to_path`, and the magic-auth 503 endpoints **unchanged**.

Replace the handlers `auth_google`, `auth_callback`, `get_current_user`, `logout`, and the cookie helpers `_apply_session_cookie`, `_clear_session_cookie`, `_apply_oauth_state_cookie`, `_clear_oauth_state_cookie`, `_load_current_session_state` with:

```python
def _apply_session_cookie(
    response: Response, request: Request, sealed_session: str
) -> None:
    service = _get_auth_service(request)
    response.set_cookie(
        service.cookie_name,
        sealed_session,
        secure=service.resolve_cookie_secure(_base_url(request)),
        httponly=True,
        samesite=service.cookie_samesite,
        max_age=service.cookie_max_age,
        path="/",
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    service = _get_auth_service(request)
    response.delete_cookie(service.cookie_name, path="/")


def _apply_oauth_state_cookie(
    response: Response, request: Request, signed_state: str
) -> None:
    service = _get_auth_service(request)
    response.set_cookie(
        service.oauth_state_cookie_name,
        signed_state,
        secure=service.resolve_cookie_secure(_base_url(request)),
        httponly=True,
        samesite=service.cookie_samesite,
        max_age=service.oauth_state_ttl_seconds,
        path="/",
    )


def _clear_oauth_state_cookie(response: Response, request: Request) -> None:
    service = _get_auth_service(request)
    response.delete_cookie(service.oauth_state_cookie_name, path="/")


def _load_current_session_state(request: Request) -> AuthSessionState:
    service = _get_auth_service(request)
    sealed_session = request.cookies.get(service.cookie_name)
    guest_mode = _has_guest_session(request)
    try:
        state = service.load_session(sealed_session)
    except AuthConfigurationError:
        logger.warning("Auth session load failed because auth is not configured.")
        state = AuthSessionState(
            auth_enabled=service.enabled,
            authenticated=False,
            guest_mode=guest_mode,
            should_clear_cookie=bool(sealed_session),
            error_reason="auth_unavailable",
        )
    except Exception:
        logger.exception("Auth session load failed unexpectedly.")
        state = AuthSessionState(
            auth_enabled=service.enabled,
            authenticated=False,
            guest_mode=guest_mode,
            should_clear_cookie=bool(sealed_session),
            error_reason="auth_session_unavailable",
        )
    if not state.authenticated and guest_mode:
        state.guest_mode = True
    return state


@auth_router.get("/api/me")
def get_current_user(request: Request):
    state = _load_current_session_state(request)
    response = JSONResponse(state.to_public_dict())
    if state.sealed_session:
        _apply_session_cookie(response, request, state.sealed_session)
    elif state.should_clear_cookie:
        _clear_session_cookie(response, request)
    return response


@auth_router.get("/login")
def login(request: Request, return_to: str | None = None):
    current = _load_current_session_state(request)
    sanitized_return_to = sanitize_return_to_path(return_to)
    if current.authenticated or current.guest_mode:
        response = RedirectResponse(url=sanitized_return_to, status_code=302)
    else:
        response = HTMLResponse(_render_login_html())
    if current.should_clear_cookie:
        _clear_session_cookie(response, request)
    return response


@auth_router.get("/auth/guest")
def auth_guest(request: Request, return_to: str | None = None):
    sanitized_return_to = sanitize_return_to_path(return_to)
    response = RedirectResponse(url=sanitized_return_to, status_code=302)
    _apply_guest_cookie(response, request)
    return response


@auth_router.get("/auth/google")
def auth_google(request: Request, return_to: str | None = None):
    service = _get_auth_service(request)
    sanitized_return_to = sanitize_return_to_path(return_to)
    try:
        nonce, _verifier, challenge, signed_state = service.build_oauth_state(
            return_to=sanitized_return_to
        )
        authorization_url = service.get_login_url(
            state_nonce=nonce, code_challenge=challenge
        )
    except AuthConfigurationError as err:
        logger.warning("Google auth start failed: %s", err)
        return RedirectResponse(
            url=_build_login_redirect(
                return_to=sanitized_return_to,
                auth_error="authentication_unavailable",
            ),
            status_code=302,
        )
    response = RedirectResponse(url=authorization_url, status_code=302)
    _apply_oauth_state_cookie(response, request, signed_state)
    return response


@auth_router.get("/auth/callback")
def auth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    service = _get_auth_service(request)
    verified = service.verify_oauth_state(
        state=state,
        signed_cookie=request.cookies.get(service.oauth_state_cookie_name),
    )
    return_to = verified[0] if verified else "/"
    if error:
        logger.info(
            "Auth callback returned error=%s description=%s", error, error_description
        )
        response = RedirectResponse(
            url=_build_login_redirect(return_to=return_to, auth_error=error),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response
    if not code:
        response = RedirectResponse(
            url=_build_login_redirect(return_to=return_to, auth_error="missing_code"),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response
    if verified is None:
        logger.warning("Auth callback failed state verification")
        response = RedirectResponse(
            url=_build_login_redirect(return_to="/", auth_error="invalid_state"),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response
    return_to, code_verifier = verified
    try:
        auth_state = service.exchange_code(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=service.callback_redirect_uri(),
        )
    except AuthConfigurationError as err:
        logger.warning("Auth callback configuration failed: %s", err)
        response = RedirectResponse(
            url=_build_login_redirect(
                return_to=return_to,
                auth_error="authentication_unavailable",
            ),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response
    except Exception:
        logger.exception("Auth callback code exchange failed")
        response = RedirectResponse(
            url=_build_login_redirect(
                return_to=return_to, auth_error="authentication_failed"
            ),
            status_code=302,
        )
        _clear_oauth_state_cookie(response, request)
        return response

    response = RedirectResponse(url=return_to, status_code=302)
    if auth_state.sealed_session:
        _apply_session_cookie(response, request, auth_state.sealed_session)
    _clear_guest_cookie(response)
    _clear_oauth_state_cookie(response, request)
    return response


@auth_router.post("/api/auth/logout")
def logout(request: Request):
    service = _get_auth_service(request)
    service.logout(request.cookies.get(service.cookie_name))
    response = JSONResponse({"ok": True, "auth_enabled": service.enabled})
    _clear_session_cookie(response, request)
    _clear_guest_cookie(response)
    return response
```

Leave the magic-auth 503 endpoints as-is.

- [ ] **Step 3: Run tests GREEN**

```bash
pytest tests/test_auth_router_supabase.py -v
```

Expected: all classes pass — `GoogleAuthStartTests`, `CallbackTests`, `ApiMeAndLogoutTests`.

- [ ] **Step 4: Commit**

```bash
git add auth/router.py
git commit -m "feat(auth): rewrite auth router under SupabaseAuthService (S9+S10+S11)"
```

---

## Task 15: /auth/guest rewiring to anonymous sign-in (S19, NEW)

**Files:**
- Modify: `auth/router.py` — `auth_guest` body calls `service.sign_in_anonymously()` and seals into session cookie. Remove `_apply_guest_cookie` from the redirect path; logout still clears `socratink_guest` for legacy cookies.
- Modify: `tests/test_auth_router_supabase.py` — append `AnonymousGuestTests` class.

- [ ] **Step 1: Append failing test class to `tests/test_auth_router_supabase.py`**

Add this class after `class ApiMeAndLogoutTests` (before `if __name__`):

```python
class AnonymousGuestTests(unittest.TestCase):
    def test_guest_calls_sign_in_anonymously_and_sets_session_cookie(self):
        service = FakeSupabaseAuthService(enabled=True)
        called = {}

        def fake_anon():
            called["yes"] = True
            return AuthSessionState(
                auth_enabled=True,
                authenticated=True,
                user=AuthUser(id="anon_uuid_456"),
                guest_mode=True,
                sealed_session="sealed-anon-blob",
            )

        service.sign_in_anonymously = fake_anon  # type: ignore[assignment]
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/library", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")
        self.assertTrue(called.get("yes"))
        self.assertIn(
            "sb_session=sealed-anon-blob", response.headers.get("set-cookie", "")
        )

    def test_guest_open_redirect_sanitized(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.sign_in_anonymously = lambda: AuthSessionState(  # type: ignore[assignment]
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="anon_uuid_456"),
            guest_mode=True,
            sealed_session="sealed-anon-blob",
        )
        client = build_client(service)

        response = client.get(
            "/auth/guest?return_to=https://evil.test", follow_redirects=False
        )

        self.assertEqual(response.headers["location"], "/")

    def test_guest_failure_redirects_to_login_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise RuntimeError("supabase down")

        service.sign_in_anonymously = boom  # type: ignore[assignment]
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])
```

- [ ] **Step 2: Confirm tests RED**

```bash
pytest tests/test_auth_router_supabase.py::AnonymousGuestTests -v
```

Expected: failures because `auth_guest` still sets the local guest cookie, not the sb_session.

- [ ] **Step 3: Replace `auth_guest` body in `auth/router.py`**

Replace the existing `auth_guest` function (added in Task 14) with:

```python
@auth_router.get("/auth/guest")
def auth_guest(request: Request, return_to: str | None = None):
    service = _get_auth_service(request)
    sanitized_return_to = sanitize_return_to_path(return_to)
    try:
        auth_state = service.sign_in_anonymously()
    except AuthConfigurationError as err:
        logger.warning("Anonymous sign-in failed (config): %s", err)
        return RedirectResponse(
            url=_build_login_redirect(
                return_to=sanitized_return_to,
                auth_error="authentication_unavailable",
            ),
            status_code=302,
        )
    except Exception:
        logger.exception("Anonymous sign-in failed unexpectedly")
        return RedirectResponse(
            url=_build_login_redirect(
                return_to=sanitized_return_to,
                auth_error="authentication_failed",
            ),
            status_code=302,
        )

    response = RedirectResponse(url=sanitized_return_to, status_code=302)
    if auth_state.sealed_session:
        _apply_session_cookie(response, request, auth_state.sealed_session)
    _clear_guest_cookie(response)
    return response
```

- [ ] **Step 4: Run tests GREEN**

```bash
pytest tests/test_auth_router_supabase.py -v
```

Expected: all classes pass, including `AnonymousGuestTests`.

- [ ] **Step 5: Commit**

```bash
git add auth/router.py tests/test_auth_router_supabase.py
git commit -m "feat(auth): wire /auth/guest to Supabase anonymous sign-in (S19)"
```

---

## Task 16: Middleware refresh writeback (S12)

**Files:**
- Modify: `main.py` — middleware gate calls `service.load_session()`, and when `state.sealed_session` is set, applies that cookie to the outgoing response.
- Test (already exists, RED): `tests/test_auth_gate_supabase.py`

- [ ] **Step 1: Confirm test is RED**

```bash
pytest tests/test_auth_gate_supabase.py -v
```

Expected: failures on `test_protected_html_writes_back_refreshed_session` and `test_protected_api_writes_back_refreshed_session`.

- [ ] **Step 2: Refactor `main.py` middleware to write back refreshed cookie**

Replace `_has_app_entry_session` and `require_login_or_guest_entry` (around `main.py:108-142`):

```python
def _resolve_session_state(request: Request):
    """Returns AuthSessionState (or None if no service / disabled)."""
    service = getattr(request.app.state, "auth_service", None)
    if service is None:
        return None
    sealed_session = request.cookies.get(service.cookie_name)
    try:
        return service.load_session(sealed_session)
    except Exception:
        logger.exception("Auth session gate failed for path=%s", request.url.path)
        return None


def _has_app_entry_session(request: Request, state) -> bool:
    if request.cookies.get(GUEST_COOKIE_NAME) == GUEST_COOKIE_VALUE:
        return True
    return bool(state and getattr(state, "authenticated", False))


def _apply_writeback(request: Request, response, state) -> None:
    """Apply refreshed sealed cookie to response if Supabase rotated tokens."""
    if state is None:
        return
    service = request.app.state.auth_service
    sealed = getattr(state, "sealed_session", None)
    if sealed:
        response.set_cookie(
            service.cookie_name,
            sealed,
            secure=service.resolve_cookie_secure(str(request.base_url).rstrip("/")),
            httponly=True,
            samesite=service.cookie_samesite,
            max_age=service.cookie_max_age,
            path="/",
        )
    elif getattr(state, "should_clear_cookie", False):
        response.delete_cookie(service.cookie_name, path="/")


@app.middleware("http")
async def require_login_or_guest_entry(request: Request, call_next):
    path = request.url.path
    if path == "/login.html":
        query = f"?{request.url.query}" if request.url.query else ""
        return RedirectResponse(url=f"/login{query}", status_code=302)

    state = _resolve_session_state(request)
    is_protected = _is_protected_html_request(request) or _is_protected_api_request(
        request
    )

    if is_protected and not _has_app_entry_session(request, state):
        if path.startswith("/api/"):
            return JSONResponse(
                {
                    "detail": "Choose Google sign-in or continue as guest before using the app."
                },
                status_code=401,
            )
        return RedirectResponse(
            url=f"/login?return_to={quote(_request_return_to(request), safe='')}",
            status_code=302,
        )

    response = await call_next(request)
    _apply_writeback(request, response, state)
    return response
```

- [ ] **Step 3: Run tests GREEN**

```bash
pytest tests/test_auth_gate_supabase.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 4: Smoke-check the rest of the suite**

```bash
pytest tests/ -v -x --ignore=tests/test_auth_router.py --ignore=tests/test_auth_gate.py
```

Expected: green (we ignore the WorkOS-specific tests; they're deleted in Task 17).

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "fix(auth): middleware writes back refreshed sealed cookie (S12)"
```

---

## Task 17: Cleanup — delete WorkOS, swap deps, remove guest cookie code (S15)

**Files:**
- Modify: `auth/service.py` — delete `WorkOSAuthService` class and `_map_workos_user`, `_call_sdk_method`, `_is_valid_fernet_key`, `_sign_oauth_state`, `_verify_oauth_state`, `OAuthState` (the WorkOS one — Supabase has its own in `auth/oauth_state.py`). Keep `AuthUser`, `AuthSessionState`, `AuthConfigurationError`, `MagicAuthStartState`, `_env_flag`, `_env_value`, `_normalize_base_url`, `_build_redirect_uri`, `_map_supabase_user`, `SupabaseAuthService`, `build_auth_service_from_env`.
- Modify: `auth/router.py` — delete guest-cookie helpers `_apply_guest_cookie`, `_clear_guest_cookie`, `_has_guest_session`. Remove their call sites: `_clear_guest_cookie(response)` in `auth_callback` (no-op since cookie no longer set), in `logout` (replace with explicit `response.delete_cookie(GUEST_COOKIE_NAME, path="/")` for legacy cleanup), and in `_load_current_session_state` (remove the `_has_guest_session(request)` call and the trailing guest-mode override; trust `state.guest_mode` from `load_session`).
- Modify: `auth/__init__.py` — remove `GUEST_COOKIE_NAME` and `GUEST_COOKIE_VALUE` exports.
- Modify: `main.py` — replace `from auth import GUEST_COOKIE_NAME, GUEST_COOKIE_VALUE, ...` with `from auth import ...` (no guest-cookie imports). Replace `_has_app_entry_session` body to drop the guest-cookie short-circuit; rely on `state.authenticated or state.guest_mode`.
- Delete: `tests/test_auth_router.py`, `tests/test_auth_gate.py` (WorkOS-shaped, obsolete).
- Modify: `requirements.txt` — remove `workos`; add `supabase`, `pyjwt[crypto]`, `cryptography`.
- Modify: `.env.example` — swap WorkOS keys for Supabase keys.

- [ ] **Step 1: Delete obsolete WorkOS test files**

```bash
git rm tests/test_auth_router.py tests/test_auth_gate.py
```

- [ ] **Step 2: Update `requirements.txt`**

Replace contents:

```
fastapi
uvicorn
google-genai
python-dotenv
aiofiles
youtube-transcript-api
supabase
pyjwt[crypto]
cryptography
```

- [ ] **Step 3: Update `.env.example`**

Replace contents:

```
GEMINI_API_KEY=your_key_here
AUTH_ENABLED=false
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_JWT_SECRET=
APP_BASE_URL=http://localhost:8000
SESSION_COOKIE_KEY=
AUTH_COOKIE_NAME=sb_session
AUTH_COOKIE_SECURE=auto
AUTH_COOKIE_SAMESITE=lax
AUTH_COOKIE_MAX_AGE=1209600
```

- [ ] **Step 4: Delete WorkOS code from `auth/service.py`**

Open `auth/service.py`. Delete in this order (use Edit tool with exact text matches):

1. Delete the `WorkOSAuthService` class (the entire class body).
2. Delete helper `_call_sdk_method`.
3. Delete helper `_is_valid_fernet_key`.
4. Delete the WorkOS `OAuthState` dataclass (lines 68-72 in original file). The Supabase `OAuthState` lives in `auth/oauth_state.py`; this WorkOS one is now unused.
5. Delete helpers `_sign_oauth_state` and `_verify_oauth_state` (WorkOS-specific HMAC helpers; the Supabase equivalents are in `auth/oauth_state.py`).
6. Delete `_map_workos_user`.
7. Remove the `from cryptography.fernet import Fernet` import line at the top — no longer used directly in this module.

- [ ] **Step 5: Delete guest-cookie helpers from `auth/router.py`**

Delete:
- `_apply_guest_cookie`
- `_clear_guest_cookie`
- `_has_guest_session`

Update call sites:
- In `auth_callback`, change `_clear_guest_cookie(response)` to `response.delete_cookie(GUEST_COOKIE_NAME, path="/")`.
- In `logout`, change `_clear_guest_cookie(response)` to `response.delete_cookie(GUEST_COOKIE_NAME, path="/")`.
- In `_load_current_session_state`, remove the `guest_mode = _has_guest_session(request)` line and the trailing `state.guest_mode = ...` override; the `state.guest_mode` from `service.load_session()` (set by S20's `is_anonymous` propagation) is now authoritative.

- [ ] **Step 6: Update `auth/__init__.py`**

Replace contents:

```python
from .router import auth_router
from .service import (
    AuthConfigurationError,
    AuthSessionState,
    AuthUser,
    MagicAuthStartState,
    SupabaseAuthService,
    build_auth_service_from_env,
)

__all__ = [
    "AuthConfigurationError",
    "AuthSessionState",
    "AuthUser",
    "MagicAuthStartState",
    "SupabaseAuthService",
    "auth_router",
    "build_auth_service_from_env",
]
```

- [ ] **Step 7: Update `main.py` imports + `_has_app_entry_session`**

Replace the auth import block:

```python
from auth import (
    auth_router,
    build_auth_service_from_env,
)
```

Replace `_has_app_entry_session`:

```python
def _has_app_entry_session(request, state) -> bool:
    if state is None:
        return False
    return bool(
        getattr(state, "authenticated", False) or getattr(state, "guest_mode", False)
    )
```

Remove the `GUEST_COOKIE_NAME` cookie read from `_resolve_session_state` (no need; `guest_mode` flows through state).

- [ ] **Step 7b: Update `tests/test_auth_gate_supabase.py` to drop the legacy-cookie expectation**

The existing `test_guest_cookie_still_unlocks` test (at the bottom of `AuthGateRefreshWritebackTests`) asserts the legacy `socratink_guest` cookie unlocks the gate. After this task removes the legacy short-circuit, the cookie alone no longer unlocks anything — anonymous users now hold a Supabase-sealed `sb_session` instead.

Change the import line:

```python
# Before:
from auth import GUEST_COOKIE_NAME
# After:
# (delete the line — no longer needed)
```

Replace `test_guest_cookie_still_unlocks` with `test_anonymous_session_unlocks_gate`:

```python
    def test_anonymous_session_unlocks_gate(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            guest_mode=True,
            user=AuthUser(id="anon_uuid_456"),
        )
        client = self.build_client(service)
        client.cookies.set(service.cookie_name, "sealed-anon-blob")

        response = client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 8: Verify cleanup is complete**

```bash
grep -rn "GUEST_COOKIE_NAME\|GUEST_COOKIE_VALUE\|socratink_guest\|WorkOS\|workos" --include="*.py" --include="*.txt" --include="*.example" .
```

Expected: zero matches outside `docs/` and `__pycache__/`.

- [ ] **Step 9: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all green; no orphaned WorkOS-shaped tests; no `socratink_guest` references in any test that's still in the repo.

- [ ] **Step 10: Commit**

```bash
git add -u
git add auth/__init__.py auth/service.py auth/router.py main.py requirements.txt .env.example
git commit -m "chore(auth): remove WorkOS code + guest cookie machinery (S15)"
```

---

## Task 18: Update install + smoke-test

**Files:**
- No code changes; this is verification.

- [ ] **Step 1: Reinstall dependencies**

```bash
pip install -r requirements.txt
```

Expected: `supabase`, `pyjwt`, `cryptography` install; `workos` is no longer installed (or remains as a leftover that we can `pip uninstall workos` separately).

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all green.

- [ ] **Step 3: Confirm no `workos` import survives anywhere**

```bash
grep -rn "import workos\|from workos" --include="*.py" .
```

Expected: zero matches.

- [ ] **Step 4: Commit (only if pip-freeze pinning is desired)**

If you maintain pinned versions: regenerate any lockfiles/pin file. Otherwise no commit.

---

## Task 19: Manual E2E gate (S17)

**Files:** none (manual checklist).

Spin up the app:

```bash
uvicorn main:app --reload
```

- [ ] **Local: /login renders**

Visit `http://localhost:8000/login` → page loads with Google + guest buttons.

- [ ] **Local: Google sign-in round-trip**

Click "Continue with Google" → Google consent → land back on `/` authenticated. `curl http://localhost:8000/api/me -b /path/to/cookie-jar` returns `authenticated: true`, `user.email`, `user.first_name`.

- [ ] **Local: Reload preserves session**

Refresh `/` → still authenticated.

- [ ] **Local: Logout works**

`curl -X POST http://localhost:8000/api/auth/logout -b /tmp/cookies` → 200 OK; subsequent `/api/me` returns `authenticated: false`.

- [ ] **Local: Guest button → anonymous user**

Click "continue as guest" → land on `/`. `/api/me` returns `authenticated: true`, `guest_mode: true`, `user.id` is a Supabase UUID.

- [ ] **Local: Anon → Google replaces session**

While guest-signed-in, click Google sign-in → complete flow → `/api/me` returns the Google user. Note: `user.id` is **different** from the anon UUID (D11 — fresh user, no link).

- [ ] **Local: Refresh-on-expiry**

Manually mutate `expires_at` in the sealed cookie payload to a past time (or wait for actual 1-hour expiry). Next `/` request triggers refresh; new `sb_session` cookie written; no re-login required.

- [ ] **Hosted (Vercel preview): all of the above**

Deploy preview, set `APP_BASE_URL` to the preview URL in Vercel env vars, add the preview URL to Supabase Authentication → URL Configuration allow-list, repeat the above seven checks under HTTPS.

- [ ] **Security: tampered session cookie**

Mutate `sb_session` cookie value → `/api/me` returns `authenticated: false`, response sets `Set-Cookie: sb_session=; Max-Age=0`.

- [ ] **Security: tampered OAuth state cookie**

Start `/auth/google`, mutate `sb_oauth_state` cookie before completing flow → callback redirects to `/login?auth_error=invalid_state`.

- [ ] **Security: open-redirect**

Visit `/auth/google?return_to=https://evil.test` → `return_to` sanitized to `/`; final redirect lands at `/`, not at `evil.test`.

- [ ] **Security: host-header spoofing**

`curl -H "Host: evil.test" http://localhost:8000/auth/google` → redirect URI in Supabase URL still uses `APP_BASE_URL`, not the spoofed host.

---

## Self-review

**Spec coverage check:**

| Spec slice | Plan task |
|------------|-----------|
| S1 PKCE | Task 1 |
| S2 OAuth state | Task 6 |
| S3 Authorize URL | Task 4 |
| S4 JWT verify | Task 2 |
| S5 Session seal | Task 3 |
| S6 Client factory | Task 5 |
| S7 + S16 Exchange + user mapping | Task 7 |
| S8 Load + refresh | Task 8 |
| S9 + S10 + S11 Router | Task 14 |
| S12 Middleware writeback | Task 16 |
| S13 APP_BASE_URL | Task 11 (verified in Task 7) |
| S14 Factory env | Task 12 |
| S15 Cleanup | Task 17 |
| S17 Manual E2E | Task 19 |
| S18 sign_in_anonymously | Task 9 |
| S19 /auth/guest rewiring | Task 15 |
| S20 is_anonymous propagation | Task 10 |
| Phase 0 dashboard setup | Prerequisites |

All slices covered.

**Method-name consistency check:**

- `SupabaseAuthService` constructor params consistent across Tasks 7, 9, 10, 11, 12 ✓
- `build_oauth_state` returns 4-tuple in Task 13; Task 14 destructures into 4 (`nonce, _verifier, challenge, signed_state`) ✓
- `verify_oauth_state` returns `(return_to, code_verifier) | None` in Task 13; Task 14 destructures `(return_to, code_verifier) = verified` ✓
- `exchange_code(code, code_verifier, redirect_uri)` consistent in Tasks 7, 14 ✓
- `sign_in_anonymously()` no args in Tasks 9, 15 ✓
- `load_session(sealed_session)` returns `AuthSessionState` in Tasks 8, 14, 16 ✓
- `_state_from_response` updated in Task 10 to add `guest_mode=is_anon`; consistent for both `exchange_code` and refresh paths ✓
- Cookie names: `sb_session` and `sb_oauth_state` consistent across all tasks ✓
- `GUEST_COOKIE_NAME` survives Tasks 14–16 (referenced by tests + cookie-clear paths); removed in Task 17 ✓

**No placeholders:** every code step has full code; every commit step has the exact message; every test step has the exact pytest command + expected output.

---

## Execution

Plan complete and saved to `docs/superpowers/plans/2026-04-25-supabase-login-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
