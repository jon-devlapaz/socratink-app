# Auth Rollout

This document is the implementation contract for introducing account identity and server-backed persistence without breaking the current MVP loop.

## Decision

- Provider: `WorkOS AuthKit`
- Session model: sealed, `HttpOnly` cookie session
- Auth methods in v1: Google + email magic link / code
- Guest mode stays available
- Passwords stay out of v1
- FastAPI remains the system boundary

## Why

- The app is `FastAPI + vanilla JS` on Vercel serverless.
- Current learner state is browser-local only, which is too fragile for sync and truthful history.
- The auth layer should preserve graph truth, not create onboarding friction.

## Product Rules

- Do not force login before first value.
- Require auth for save/sync, not for basic exploration.
- Do not auto-merge mastery upward when local and cloud state disagree.
- Signed-in state becomes server-authoritative only after the persistence phases are complete.

## Phases

### Phase 0

- Add auth feature flag and WorkOS session scaffolding.
- Add bespoke `/login`, `/auth/google`, `/auth/callback`, `/api/me`, `/api/auth/logout`.
- Add custom-ui passwordless email code flow via the AuthKit Magic Auth API.
- Add frontend auth bootstrap and account shell UI.
- Keep concept truth in `localStorage`.

Release gate:
- login, callback, `/api/me`, and logout work in local and Vercel preview
- auth off leaves the current guest app behavior unchanged

### Phase 1

- Ship guest-aware login UI
- Show `Save & sync` entry points
- Preserve deep return-to behavior after auth

Release gate:
- no regression to anonymous concept creation, study, or drill flows
- cookies persist correctly on refresh in Chrome and Safari

### Phase 2

- Add account-backed concept persistence
- Import local concepts one time after login
- Add explicit conflict choice: `Use cloud progress` or `Use this device's progress`

Release gate:
- import is idempotent
- no silent graph-state inflation

### Phase 3

- Move signed-in concept truth and drill events server-side
- Keep local storage only as transient cache and fallback

Release gate:
- signed-in users can refresh or switch devices without losing truthful state
- `locked -> primed -> drilled -> solidified` remains valid after sync

### Phase 4

- Replace hosted entry with fully bespoke branded login page if desired
- Add polish around account recovery, conflict UX, analytics scoping, and rate limits

## Test Plan

Local readiness:

- `bash scripts/dev.sh` (wraps `python scripts/check-local-auth.py`) validates Supabase + session env on localhost before starting Uvicorn, catching `.env` vs `.env.local` misconfiguration that breaks the Phase 0 release gate.
- `python scripts/check-local-auth.py --probe-guest` additionally calls `sign_in_anonymously()` against the configured Supabase project, proving the anon key actually works end-to-end — the strongest local check for the Phase 0 guest-session path.

Automate first:

- auth router behavior
- sealed-session load/refresh behavior
- callback return-path sanitization
- logout cookie clearing
- guest-mode regression checks

Manual hosted checks:

- Google login on localhost and Vercel preview
- email flow on preview
- refresh after callback
- logout
- return to the same concept/page after auth

## Deferred From Phase 0

- database writes
- concept import
- conflict resolution UI
- remote-authoritative graph persistence
- provider logout / remote session revocation
