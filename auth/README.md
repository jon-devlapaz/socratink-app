# auth/

Supabase-backed authentication seam. Owns session encryption, JWT
verification, OAuth state, and the FastAPI router that exposes auth routes.

## Public surface

Import from `auth` directly. Submodule paths are implementation detail.

| Export | What it is |
| :--- | :--- |
| `AuthConfigurationError` | Raised when auth is enabled but the provider is misconfigured. |
| `AuthSessionState` | Dataclass: `auth_enabled`, `authenticated`, `user`, `guest_mode`, `sealed_session`, `should_clear_cookie`, `error_reason`. The truth-bearing object the rest of the app reads. |
| `AuthUser` | Dataclass: `id`, `email`, optional names. |
| `SupabaseAuthService` | The provider implementation. Hold one instance per app via `build_auth_service_from_env`. |
| `auth_router` | FastAPI router registering `/auth/*` and `/api/me`. |
| `build_auth_service_from_env()` | Reads `SUPABASE_*`, `AUTH_ENABLED`, cookie config. Returns a `SupabaseAuthService`. |
| `load_current_session_state(request)` | Read-only seam used by every protected handler. Never raises — failures collapse into `AuthSessionState` with `should_clear_cookie=True`. |

## Files

| File | Role |
| :--- | :--- |
| `service.py` | `SupabaseAuthService`, dataclasses, env wiring. |
| `router.py` | All `/auth/*` HTTP handlers + `load_current_session_state`. |
| `jwt_verify.py` | Supabase JWT verification (ES256 via JWKS or HS256 fallback). |
| `session_seal.py` | Fernet-sealed cookie payload. |
| `oauth_state.py` | OAuth state token signing + verification. |
| `pkce.py` | PKCE code-verifier / challenge helpers. |
| `supabase_client.py` | HTTP client wrapper over the Supabase REST surface. |
| `supabase_urls.py` | URL builders for Supabase auth endpoints. |

## Footguns

- **`AUTH_ENABLED=false` is real.** When disabled, the service still returns a coherent `AuthSessionState` with `auth_enabled=False`. Routes branch on this, not on whether `service is None`. Don't add `if service:` guards.
- **`SOCRATINK_DEV_AUTOGUEST` is gated against deployed environments.** It is hard-disabled when `VERCEL`, `VERCEL_ENV`, or `CI` env vars are present. Read the SECURITY ASSUMPTION docstring in `runtime_env.dev_autoguest_enabled` before touching the guard.
- **JWT signing mode varies by Supabase project.** New projects sign with ES256 (JWKS); older projects use HS256 with `SUPABASE_JWT_SECRET`. `jwt_verify.py` handles both. `SUPABASE_JWT_SECRET` must be a non-empty placeholder even on ES256-only projects (env var presence is checked, value is not).
- **Cookie key rotation requires a deploy.** `SESSION_COOKIE_KEY` is a Fernet key; rotating it invalidates all outstanding sessions. There is no graceful old-key fallback.
- **`load_current_session_state` must not raise.** Any uncaught exception inside that function lets a 500 reach a route that expected an `AuthSessionState`. Catch broadly and return a degraded state with `error_reason` set.
- **`AUTH_ENABLED=true` + missing Supabase env = startup failure**, by design. Don't paper over `AuthConfigurationError`.

## Related

- Env contract: see `.env.example` (lines 1–22).
- Cookie sealing tests: `tests/test_supabase_load_session.py`.
- Anti-pattern guard: don't import from `auth.<submodule>` outside `auth/` — go through the package surface.
