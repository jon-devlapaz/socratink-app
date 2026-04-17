from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import secrets
from typing import Any

from cryptography.fernet import Fernet


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


@dataclass(slots=True)
class MagicAuthStartState:
    auth_enabled: bool
    pending: bool
    email: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "auth_enabled": self.auth_enabled,
            "pending": self.pending,
            "email": self.email,
        }


@dataclass(slots=True)
class OAuthState:
    nonce: str
    return_to: str
    issued_at: int


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


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _build_redirect_uri(base_url: str, callback_path: str) -> str:
    return f"{_normalize_base_url(base_url)}{callback_path}"


class WorkOSAuthService:
    def __init__(
        self,
        *,
        enabled: bool,
        api_key: str | None,
        client_id: str | None,
        cookie_password: str | None,
        cookie_name: str = "wos_session",
        callback_path: str = "/auth/callback",
        cookie_secure: str = "auto",
        cookie_samesite: str = "lax",
        cookie_max_age: int = 60 * 60 * 24 * 14,
        oauth_state_cookie_name: str = "wos_oauth_state",
        oauth_state_ttl_seconds: int = 60 * 10,
    ) -> None:
        self.enabled = enabled
        self.api_key = api_key
        self.client_id = client_id
        self.cookie_password = cookie_password
        self.cookie_name = cookie_name
        self.callback_path = callback_path
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite
        self.cookie_max_age = cookie_max_age
        self.oauth_state_cookie_name = oauth_state_cookie_name
        self.oauth_state_ttl_seconds = oauth_state_ttl_seconds
        self._workos: Any | None = None

    def require_enabled(self) -> None:
        if not self.enabled:
            raise AuthConfigurationError("Auth is disabled.")
        missing = [
            name
            for name, value in [
                ("WORKOS_API_KEY", self.api_key),
                ("WORKOS_CLIENT_ID", self.client_id),
                ("WORKOS_COOKIE_PASSWORD", self.cookie_password),
            ]
            if not value
        ]
        if missing:
            raise AuthConfigurationError(
                f"Auth is enabled but missing required settings: {', '.join(missing)}."
            )
        if self.cookie_password:
            if len(self.cookie_password) < 32:
                raise AuthConfigurationError(
                    "WORKOS_COOKIE_PASSWORD must be a Fernet key, not a short password."
                )
            if not _is_valid_fernet_key(self.cookie_password):
                raise AuthConfigurationError(
                    "WORKOS_COOKIE_PASSWORD must be a valid Fernet key. Generate one with "
                    "`python3 - <<'PY'\nfrom cryptography.fernet import Fernet\nprint(Fernet.generate_key().decode())\nPY`."
                )

    def _client(self) -> Any:
        self.require_enabled()
        if self._workos is not None:
            return self._workos
        try:
            from workos import WorkOSClient
        except ImportError as err:
            raise AuthConfigurationError(
                "The `workos` package is required when auth is enabled."
            ) from err
        self._workos = WorkOSClient(api_key=self.api_key, client_id=self.client_id)
        return self._workos

    def get_login_url(
        self,
        *,
        base_url: str,
        return_to: str | None = None,
        provider: str = "authkit",
    ) -> str:
        client = self._client()
        return _call_sdk_method(
            client.user_management,
            "get_authorization_url",
            "getAuthorizationUrl",
            provider=provider,
            redirect_uri=_build_redirect_uri(base_url, self.callback_path),
            state=return_to,
        )

    def exchange_code(
        self,
        *,
        code: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSessionState:
        client = self._client()
        auth_response = _call_sdk_method(
            client.user_management,
            "authenticate_with_code",
            "authenticateWithCode",
            code=code,
            ip_address=ip_address,
            user_agent=user_agent,
            session={"seal_session": True, "cookie_password": self.cookie_password},
        )
        user = getattr(auth_response, "user", None)
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=_map_workos_user(user),
            sealed_session=getattr(auth_response, "sealed_session", None),
        )

    def load_session(self, sealed_session: str | None) -> AuthSessionState:
        if not self.enabled:
            return AuthSessionState(auth_enabled=False, authenticated=False)
        if not sealed_session:
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                error_reason="no_session_cookie_provided",
            )

        client = self._client()
        session = _call_sdk_method(
            client.user_management,
            "load_sealed_session",
            "loadSealedSession",
            sealed_session=sealed_session,
            cookie_password=self.cookie_password,
        )
        auth_response = session.authenticate()
        if getattr(auth_response, "authenticated", False):
            return AuthSessionState(
                auth_enabled=True,
                authenticated=True,
                user=_map_workos_user(getattr(auth_response, "user", None)),
            )

        if getattr(auth_response, "reason", None) == "no_session_cookie_provided":
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                error_reason="no_session_cookie_provided",
                should_clear_cookie=True,
            )

        try:
            refreshed = session.refresh()
        except Exception:
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                should_clear_cookie=True,
                error_reason="session_refresh_failed",
            )

        if not getattr(refreshed, "authenticated", False):
            return AuthSessionState(
                auth_enabled=True,
                authenticated=False,
                should_clear_cookie=True,
                error_reason=getattr(refreshed, "reason", "session_refresh_failed"),
            )

        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=_map_workos_user(getattr(refreshed, "user", None)),
            sealed_session=getattr(refreshed, "sealed_session", None),
        )

    def logout(self, sealed_session: str | None) -> None:
        # Phase 0 clears the local session cookie. Remote session revocation can be
        # added once protected routes and persistence are live.
        _ = sealed_session

    def send_magic_auth_code(self, *, email: str) -> MagicAuthStartState:
        client = self._client()
        _call_sdk_method(
            client.user_management,
            "create_magic_auth",
            "createMagicAuth",
            email=email,
        )
        return MagicAuthStartState(
            auth_enabled=True,
            pending=True,
            email=email,
        )

    def authenticate_with_magic_auth(
        self,
        *,
        email: str,
        code: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSessionState:
        client = self._client()
        auth_response = _call_sdk_method(
            client.user_management,
            "authenticate_with_magic_auth",
            "authenticateWithMagicAuth",
            email=email,
            code=code,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        user = getattr(auth_response, "user", None)
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=_map_workos_user(user),
            sealed_session=getattr(auth_response, "sealed_session", None),
        )

    def resolve_cookie_secure(self, base_url: str) -> bool:
        mode = (self.cookie_secure or "auto").strip().lower()
        if mode == "true":
            return True
        if mode == "false":
            return False
        return _normalize_base_url(base_url).startswith("https://")

    def build_oauth_state(self, *, return_to: str) -> tuple[str, str]:
        self.require_enabled()
        issued_at = int(datetime.now(timezone.utc).timestamp())
        state = OAuthState(
            nonce=secrets.token_urlsafe(24),
            return_to=return_to,
            issued_at=issued_at,
        )
        return state.nonce, _sign_oauth_state(state, self.cookie_password or "")

    def verify_oauth_state(
        self, *, state: str | None, signed_cookie: str | None
    ) -> str | None:
        self.require_enabled()
        if not state or not signed_cookie:
            return None
        payload = _verify_oauth_state(
            signed_cookie,
            secret=self.cookie_password or "",
            max_age_seconds=self.oauth_state_ttl_seconds,
        )
        if not payload:
            return None
        if not secrets.compare_digest(payload.nonce, state):
            return None
        return payload.return_to


def _call_sdk_method(target: Any, snake_name: str, camel_name: str, **kwargs):
    method = getattr(target, snake_name, None) or getattr(target, camel_name, None)
    if method is None:
        raise AuthConfigurationError(
            f"Installed WorkOS SDK is missing `{snake_name}` / `{camel_name}`."
        )
    return method(**kwargs)


def _is_valid_fernet_key(value: str) -> bool:
    try:
        Fernet(value.encode())
        return True
    except Exception:
        return False


def _sign_oauth_state(payload: OAuthState, secret: str) -> str:
    raw = json.dumps(
        {
            "nonce": payload.nonce,
            "return_to": payload.return_to,
            "issued_at": payload.issued_at,
        },
        separators=(",", ":"),
    )
    signature = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return json.dumps({"payload": raw, "sig": signature}, separators=(",", ":"))


def _verify_oauth_state(
    token: str, *, secret: str, max_age_seconds: int
) -> OAuthState | None:
    try:
        wrapper = json.loads(token)
        raw = wrapper["payload"]
        sig = wrapper["sig"]
        expected = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(raw)
        issued_at = int(payload["issued_at"])
        now = int(datetime.now(timezone.utc).timestamp())
        if now - issued_at > max_age_seconds:
            return None
        return OAuthState(
            nonce=str(payload["nonce"]),
            return_to=str(payload["return_to"]),
            issued_at=issued_at,
        )
    except Exception:
        return None


def _map_workos_user(user: Any | None) -> AuthUser | None:
    if user is None:
        return None
    return AuthUser(
        id=str(getattr(user, "id", "")),
        email=getattr(user, "email", None),
        first_name=getattr(user, "first_name", None),
        last_name=getattr(user, "last_name", None),
    )


def build_auth_service_from_env() -> WorkOSAuthService:
    return WorkOSAuthService(
        enabled=_env_flag("AUTH_ENABLED", False),
        api_key=_env_value("WORKOS_API_KEY"),
        client_id=_env_value("WORKOS_CLIENT_ID"),
        cookie_password=_env_value("WORKOS_COOKIE_PASSWORD"),
        cookie_name=_env_value("AUTH_COOKIE_NAME", "wos_session") or "wos_session",
        callback_path=_env_value("AUTH_CALLBACK_PATH", "/auth/callback")
        or "/auth/callback",
        cookie_secure=_env_value("AUTH_COOKIE_SECURE", "auto") or "auto",
        cookie_samesite=_env_value("AUTH_COOKIE_SAMESITE", "lax") or "lax",
        cookie_max_age=int(
            _env_value("AUTH_COOKIE_MAX_AGE", str(60 * 60 * 24 * 14))
            or str(60 * 60 * 24 * 14)
        ),
        oauth_state_cookie_name=_env_value("AUTH_STATE_COOKIE_NAME", "wos_oauth_state")
        or "wos_oauth_state",
        oauth_state_ttl_seconds=int(
            _env_value("AUTH_STATE_TTL_SECONDS", str(60 * 10)) or str(60 * 10)
        ),
    )
