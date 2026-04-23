# Supabase Auth Swap — Implementation Plan

**Status:** drafted, not started
**Owner:** socratinker
**Branch model:** one branch per slice, dev → main
**Confidence:** MEDIUM (82%) after codex crit
**Last updated:** 2026-04-22

---

## Goal

Replace WorkOS with Supabase Auth. Google OAuth only. No persistent user table — Supabase `auth.users` is built-in. Guest mode preserved. Same backend-owned httpOnly cookie session shape, same middleware gate.

## Out of scope

- Supabase as a database (telemetry/persistence) — separate slice in P2.
- Magic link / email auth — keep current 503 stubs.
- User profile UI changes beyond `first_name` mapping.
- Migration of existing WorkOS-authenticated users — zero users in scope, accept fresh login on cutover.

## Why now

- WorkOS is overprovisioned for current MVP. Supabase aligns with planned P2 telemetry vendor.
- One vendor for auth + future telemetry = one config, one dashboard.
- Cleans environment variables before hosted-validation gate.

---

## Design decisions (locked)

| ID | Decision | Reason |
|----|----------|--------|
| D1 | Server-side OAuth flow mirroring current `/auth/google` → provider → `/auth/callback` shape | Closest to existing architecture; avoids client-side token storage |
| D2 | Session cookie = Fernet-sealed JSON of `{access_token, refresh_token, expires_at}` | Reuses existing Fernet infrastructure; httpOnly stays |
| D3 | JWT verification via pyjwt HS256 + `SUPABASE_JWT_SECRET` initially; abstract behind `verify_access_token()` so JWKS swap is a one-line change | HS256 is current Supabase default; codex flagged future asymmetric move |
| D4 | `supabase-py` for code exchange + refresh only; verification stays in pyjwt | Thin SDK use; keeps verification path serverless-cold-start-safe |
| D5 | Supabase client instantiated per request with `persist_session=False`, `auto_refresh_token=False` | No stateful singleton; Vercel serverless safe |
| D6 | PKCE code_verifier stored in extended OAuth state cookie alongside nonce + return_to | Single signed cookie covers CSRF + PKCE; no server-side storage needed |
| D7 | Redirect URIs derived from required `APP_BASE_URL` env, not `request.base_url` | Closes host-header spoofing on Vercel |
| D8 | Middleware gate writes back refreshed sealed cookie (fixes pre-existing latent bug) | Refresh-token rotation requires it; without this, Supabase rotation = silent session loss |

## Open questions

- **Q1** — Keep magic-auth 503 stub routes? **A:** Yes (codex). Tested surface, not load-bearing churn to remove.
- **Q2** — `APP_BASE_URL` required in dev too? **A:** Yes. Removes host-header attack surface even locally and matches prod path.
- **Q3** — JWKS-only from day 1 or HS256 fallback? **A:** HS256 first (Supabase default), JWKS swap later. `verify_access_token()` interface stable across both.

---

## Phase 0 — Supabase dashboard setup (manual, you do)

1. Create Supabase project. Note region.
2. GCP Console: create OAuth 2.0 Client ID (Web). Authorized redirect URI: `https://<project-ref>.supabase.co/auth/v1/callback`.
3. Supabase Dashboard → Authentication → Providers → Google. Paste client ID + secret. Enable.
4. Supabase Dashboard → Authentication → URL Configuration:
   - Site URL: `http://localhost:8000` (dev)
   - Redirect URLs (allow-list): `http://localhost:8000/auth/callback`, `https://<vercel-prod>.vercel.app/auth/callback`, `https://socratink.app/auth/callback`
5. Supabase Dashboard → Project Settings → API:
   - Copy `Project URL` → `SUPABASE_URL`
   - Copy `anon` / `publishable` key → `SUPABASE_PUBLISHABLE_KEY`
   - Copy JWT secret → `SUPABASE_JWT_SECRET`
6. Generate Fernet key locally:
   ```
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   → `SESSION_COOKIE_KEY`

**Gate:** can manually hit `https://<project-ref>.supabase.co/auth/v1/authorize?provider=google&redirect_to=...` and complete a Google flow ending at the callback URL with `?code=...`.

---

## Phase 1 — Backend slices (TDD)

Each slice = failing test → minimum impl → green → commit. One branch per slice. Test files already written (red).

### Dependency graph

```
S1 PKCE prims  ─┐
S4 JWT verify  ─┤
S5 Sess seal   ─┼──► S7 Exchange ──► S8 Load+refresh ──┐
S6 Client fctry┤                                       │
S3 Authorize   ─┘                                      │
S2 OAuth state ──────────────────────────► S9 Router ◄─┤
                                           S10 Callback│
                                           S11 /api/me ┤
                                                       │
S13 APP_BASE_URL ────────────────────► S14 Factory ◄───┤
                                                       │
                                       S12 Mw writeback┘
                                       S15 Cleanup (mech.)
                                       S17 Manual E2E
```

Parallelizable (independent pure slices): S1, S3, S4, S5, S6, S13.

### Slice table

| ID | Title | Adds module | Test file | Deps |
|----|-------|-------------|-----------|------|
| S1 | PKCE primitives | `auth/pkce.py` | `tests/test_pkce.py` | — |
| S2 | OAuth state +verifier | `auth/oauth_state.py` | `tests/test_oauth_state_pkce.py` | S1 |
| S3 | Supabase authorize URL builder | `auth/supabase_urls.py` | `tests/test_supabase_authorize_url.py` | — |
| S4 | JWT access-token verifier | `auth/jwt_verify.py` | `tests/test_jwt_verify.py` | — |
| S5 | Session token sealing | `auth/session_seal.py` | `tests/test_session_seal.py` | — |
| S6 | Supabase client factory | `auth/supabase_client.py` | `tests/test_supabase_client_factory.py` | — |
| S7 | `exchange_code` + user mapping (S16) | `auth/service.py` (`SupabaseAuthService.exchange_code`) | `tests/test_supabase_exchange.py` | S5, S6 |
| S8 | `load_session` + refresh + re-seal | `auth/service.py` (`SupabaseAuthService.load_session`) | `tests/test_supabase_load_session.py` | S4, S5, S6 |
| S9 | `/auth/google` router wiring | `auth/router.py` | `tests/test_auth_router_supabase.py` (`GoogleAuthStartTests`) | S1, S2, S3 |
| S10 | `/auth/callback` router wiring | `auth/router.py` | `tests/test_auth_router_supabase.py` (`CallbackTests`) | S7, S2 |
| S11 | `/api/me` + logout under new service | `auth/router.py` | `tests/test_auth_router_supabase.py` (`ApiMeAndLogoutTests`) | S8 |
| S12 | Middleware refresh writeback fix | `main.py`, `auth/router.py:login` | `tests/test_auth_gate_supabase.py` | S8 |
| S13 | `APP_BASE_URL` host hardening | `auth/service.py` | `tests/test_app_base_url.py` | — |
| S14 | `build_auth_service_from_env` rewritten | `auth/__init__.py` | `tests/test_auth_factory.py` | S13 |
| S15 | Cleanup | `requirements.txt`, `.env.example`, delete WorkOS code & old tests | smoke `pytest tests/` green | S1–S14 |
| S16 | First-name mapping (folded into S7) | (in S7) | (in S7 `UserMetadataMappingTests`) | S7 |
| S17 | Manual E2E gate (Phase 3) | n/a | manual checklist | S1–S15 |

### Per-slice TDD loop

```
1. checkout -b claude/supabase-auth-S<n>-<slug>
2. confirm test file is RED
3. minimum impl to GREEN
4. refactor if needed
5. one commit, push, PR to dev
6. merge after self-review
```

### Slice execution order

`S1 → S4 → S5 → S3 → S6 → S2 → S7 (+S16) → S8 → S13 → S14 → S9 → S10 → S11 → S12 → S15 → S17`

S1+S3+S4+S5+S6+S13 may run as parallel agents (fully independent).

---

## Phase 2 — Frontend

No changes. Existing `login.js` / login HTML hits `/auth/google` and `/api/me` — unchanged contract.

`public/js/auth.js:74` reads `user.first_name || user.email` — S16 (folded into S7) maps Supabase `user_metadata.full_name`/`given_name` so name shows correctly instead of email-only fallback.

---

## Phase 3 — Manual E2E gate (S17)

Block merge to main until all pass. Log gaps to `.socratink-brain/raw/auth-swap-<date>.md`.

**Local (`uvicorn main:app --reload`):**
- [ ] `/login` page renders
- [ ] Click Google → land on `/` authenticated
- [ ] `/api/me` returns user with email + first_name
- [ ] Reload page, still authenticated
- [ ] Logout clears cookie, returns to `/login`
- [ ] Guest button still works, drill works under guest
- [ ] Force expiry of access token (mutate cookie or short TTL) → next request triggers refresh, new cookie written, no re-login

**Hosted (Vercel preview deployment):**
- [ ] Same six checks above
- [ ] Confirm `APP_BASE_URL` and Supabase redirect allow-list both updated for preview hostname
- [ ] OAuth state cookie SameSite/Secure correct under HTTPS

**Security spot checks:**
- [ ] Tampered session cookie → unauthenticated, cookie cleared
- [ ] Tampered OAuth state cookie → callback rejected with `invalid_state`
- [ ] `return_to=https://evil.test` → sanitized to `/`
- [ ] Spoofed `Host:` header on `/auth/google` → redirect URI still uses `APP_BASE_URL`

---

## Environment variables

### Remove

```
WORKOS_API_KEY
WORKOS_CLIENT_ID
WORKOS_COOKIE_PASSWORD
AUTH_COOKIE_NAME
AUTH_STATE_COOKIE_NAME
```

### Add

```
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<anon/publishable key>
SUPABASE_JWT_SECRET=<HS256 secret from Supabase Settings>
APP_BASE_URL=http://localhost:8000   # dev; set per-environment
SESSION_COOKIE_KEY=<Fernet key — see Phase 0 step 6>
```

### Keep

```
AUTH_ENABLED=true
AUTH_COOKIE_SECURE=auto
AUTH_COOKIE_SAMESITE=lax
AUTH_COOKIE_MAX_AGE=1209600
AUTH_CALLBACK_PATH=/auth/callback
AUTH_STATE_TTL_SECONDS=600
```

### Vercel

Set `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_JWT_SECRET`, `APP_BASE_URL`, `SESSION_COOKIE_KEY` as Vercel project env vars before deploy. `APP_BASE_URL` differs per environment (preview vs prod).

---

## Dependency changes

`requirements.txt`:

```diff
- workos
+ supabase
+ pyjwt[crypto]
+ cryptography  # already used implicitly via Fernet, now explicit
```

---

## Risk register

| Risk | Severity | Mitigation |
|------|----------|------------|
| PKCE verifier lost between authorize and callback | High | Sealed in extended OAuth state cookie (S2) |
| Refresh-token rotation invalidates session on next request | High | Middleware writeback fix (S12); pre-existing latent bug confirmed by failing test today |
| Host-header spoofing redirects OAuth to attacker domain | High | `APP_BASE_URL` env required (S13) |
| Vercel cold-start instantiates Supabase SDK with stale state | Medium | Fresh client per op, `persist_session=False` (S6, D5) |
| `SUPABASE_JWT_SECRET` deprecated in favor of asymmetric signing | Medium | `verify_access_token()` abstracts mechanism; HS256 → JWKS swap is one-line |
| Supabase URL Config redirect allow-list missing prod entry | Medium | Phase 0 step 4 explicit; Phase 3 hosted gate verifies |
| Tampered Fernet cookie crashes app | Low | `should_clear_cookie=True`, return unauthenticated (S8) |
| Old WorkOS sessions invalid post-cutover | Low | Accepted; zero hosted users; first request bounces to login |

---

## Files touched (final state)

**New:**
- `auth/pkce.py`
- `auth/oauth_state.py`
- `auth/supabase_urls.py`
- `auth/jwt_verify.py`
- `auth/session_seal.py`
- `auth/supabase_client.py`
- 12 new test files in `tests/`
- `docs/project/supabase-auth-swap.md` (this file)

**Modified:**
- `auth/service.py` — `WorkOSAuthService` removed, `SupabaseAuthService` added; `AuthUser`, `AuthSessionState`, `AuthConfigurationError` retained
- `auth/__init__.py` — factory rewritten
- `auth/router.py` — handler bodies updated; cookie name `wos_session` → `sb_session`
- `main.py` — middleware gate writes back refreshed cookie; cookie name constant via service
- `requirements.txt`
- `.env.example`

**Deleted:**
- `tests/test_auth_router.py` (WorkOS-shaped, replaced by `test_auth_router_supabase.py`)
- `tests/test_auth_gate.py` (WorkOS-shaped, replaced by `test_auth_gate_supabase.py`)

---

## Done definition

- All 64 new tests green
- All pre-existing tests green
- Phase 3 manual E2E checklist all green (local + hosted)
- `.env.example` matches deployed env
- WorkOS code removed (no `workos` import survives)
- `docs/project/state.md` Active Risks updated to remove WorkOS reference if any
- One brain-promotion item logged if any new evidence (e.g., hosted divergence) surfaced during S17

---

## References

- `auth/service.py` — current WorkOSAuthService (to replace)
- `auth/router.py:675` — current `/auth/google` handler
- `main.py:123` — current middleware gate (refresh writeback bug here)
- `public/js/auth.js:74` — frontend user-name read site
- `docs/project/auth-rollout.md` — historical WorkOS rollout doc
- Supabase Python `exchange_code_for_session`: https://supabase.com/docs/reference/python/auth-exchangecodeforsession
- Supabase JWT fields: https://supabase.com/docs/guides/auth/jwt-fields
- Supabase sessions/refresh: https://supabase.com/docs/guides/auth/sessions
- RFC 7636 (PKCE): https://www.rfc-editor.org/rfc/rfc7636
