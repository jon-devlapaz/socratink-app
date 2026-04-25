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
