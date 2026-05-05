from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


class AuthConfigurationError(RuntimeError):
    """Raised when auth is enabled but the provider is not configured correctly."""


@dataclass(slots=True)
class AuthUser:
    id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }


@dataclass(slots=True)
class AuthSessionState:
    auth_enabled: bool
    authenticated: bool
    user: AuthUser | None = None
    guest_mode: bool = False
    sealed_session: str | None = None
    should_clear_cookie: bool = False
    error_reason: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "auth_enabled": self.auth_enabled,
            "authenticated": self.authenticated,
            "guest_mode": self.guest_mode,
            "user": self.user.to_dict() if self.user else None,
        }

def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_value(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    trimmed = raw.strip()
    return trimmed or default


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


def _should_clear_refresh_cookie(error: Exception) -> bool:
    import httpx
    from supabase import AuthApiError, AuthRetryableError, AuthSessionMissingError

    if isinstance(error, (AuthRetryableError, httpx.TransportError)):
        return False
    if isinstance(error, AuthSessionMissingError):
        return True
    if isinstance(error, AuthApiError):
        return getattr(error, "status", None) in {400, 401, 403}
    return False


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
        missing = self.missing_required_settings()
        if missing:
            raise AuthConfigurationError(
                f"Auth is enabled but missing: {', '.join(missing)}"
            )
        if self.session_cookie_key:
            from auth.session_seal import validate_session_cookie_key
            try:
                validate_session_cookie_key(self.session_cookie_key)
            except ValueError as err:
                raise AuthConfigurationError("SESSION_COOKIE_KEY is not a valid Fernet key.") from err

    def missing_required_settings(self) -> list[str]:
        return [
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

    def build_oauth_state(self, *, return_to: str) -> tuple[str, str, str]:
        """Build (verifier, challenge, signed_state_cookie) for /auth/google.

        We do NOT pass a `state` query param to Supabase — Supabase manages its
        own JWT-encoded state cookie internally and rejects flows where our
        nonce collides with theirs. CSRF protection comes from the HMAC-signed
        cookie, which carries return_to + the PKCE verifier; the verifier is
        what binds the callback to this specific session.
        """
        from auth.oauth_state import OAuthState, sign_state
        from auth.pkce import challenge_from_verifier, generate_verifier
        import time

        self._require_enabled()
        assert self.session_cookie_key
        verifier = generate_verifier()
        challenge = challenge_from_verifier(verifier)
        state = OAuthState(
            nonce="",  # unused; retained in dataclass for sign/verify symmetry
            return_to=return_to,
            code_verifier=verifier,
            issued_at=int(time.time()),
        )
        return verifier, challenge, sign_state(state, self.session_cookie_key)

    def get_login_url(self, *, code_challenge: str) -> str:
        from auth.supabase_urls import build_google_authorize_url

        self._require_enabled()
        assert self.supabase_url
        return build_google_authorize_url(
            supabase_url=self.supabase_url,
            redirect_to=self.callback_redirect_uri(),
            code_challenge=code_challenge,
        )

    def verify_oauth_state(
        self, *, signed_cookie: str | None
    ) -> tuple[str, str] | None:
        """Return (return_to, code_verifier) on success, else None.

        CSRF binding is the HMAC over the cookie payload (validated by
        verify_state) plus the embedded code_verifier (validated by Supabase
        when we exchange). No URL-borne state to match.
        """
        from auth.oauth_state import verify_state

        self._require_enabled()
        assert self.session_cookie_key
        if not signed_cookie:
            return None
        decoded = verify_state(
            signed_cookie,
            secret=self.session_cookie_key,
            max_age_seconds=self.oauth_state_ttl_seconds,
        )
        if decoded is None:
            return None
        return decoded.return_to, decoded.code_verifier

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
            client.auth.sign_out()
        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("Remote Supabase sign-out failed", exc_info=True)

    def _unseal_or_none(self, sealed_session: str):
        from auth.session_seal import unseal_session_tokens

        try:
            assert self.session_cookie_key
            return unseal_session_tokens(sealed_session, key=self.session_cookie_key)
        except ValueError:
            return None

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

    def sign_in_anonymously(self) -> AuthSessionState:
        self._require_enabled()
        client = self._make_supabase_client()
        response = client.auth.sign_in_anonymously()
        return self._state_from_response(response)

    def load_session(self, sealed_session: str | None) -> AuthSessionState:
        if not self.enabled:
            return AuthSessionState(auth_enabled=False, authenticated=False)
        if not sealed_session:
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                error_reason="no_session_cookie_provided",
            )

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
        except ValueError:
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                should_clear_cookie=True,
                error_reason="session_cookie_invalid",
            )

        issuer = f"{self.supabase_url.rstrip('/')}/auth/v1"
        try:
            claims = verify_access_token(
                tokens["access_token"],
                jwt_secret=self.jwt_secret,
                supabase_url=self.supabase_url,
                issuer=issuer,
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
            guest_mode=bool(claims.get("is_anonymous", False)),
        )

    def _refresh_session(self, refresh_token: str) -> AuthSessionState:
        try:
            client = self._make_supabase_client()
            # Explicit refresh_token arg: SDK has no stored session; the sealed
            # cookie is our source of truth. Don't "fix" this to the no-arg form.
            response = client.auth.refresh_session(refresh_token)
        except Exception as err:
            should_clear = _should_clear_refresh_cookie(err)
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                should_clear_cookie=should_clear,
                error_reason=(
                    "session_refresh_invalid"
                    if should_clear
                    else "session_refresh_unavailable"
                ),
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
        authenticated = bool(sealed)
        is_anon = (
            bool(getattr(user, "is_anonymous", False))
            if authenticated and user is not None
            else False
        )
        return AuthSessionState(
            auth_enabled=True,
            authenticated=authenticated,
            user=_map_supabase_user(user) if authenticated else None,
            guest_mode=is_anon,
            sealed_session=sealed,
        )


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
