# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## First principles for this repo
- Keep changes surgical and scope-locked. Do not broaden features or refactor unrelated areas.
- Prefer the simplest implementation that satisfies the task.
- For non-trivial work, convert the request into verifiable goals (typically via targeted tests).
- MVP doctrine applies: separate true blockers from nice-to-have polish.

## Code exploration and review workflow
- This repo is configured for a code-review knowledge graph. Use graph tools before grep/glob/read whenever available.
- Start with minimal graph context, then escalate only if needed:
  - `get_minimal_context_tool` for initial orientation
  - `detect_changes` and `get_review_context` for review
  - `get_impact_radius` and `get_affected_flows` for blast-radius analysis
  - `query_graph` / `semantic_search_nodes` for callers, callees, imports, and tests
- Use grep/glob/read only when graph coverage is insufficient.
- Caveat from project rules: call-count data can under-report; verify “single call site” claims with textual search.

## Common development commands
### Environment setup
```bash
pip install -r requirements-dev.txt
playwright install chromium
```

### Run locally
```bash
# Preferred: validates local auth env before starting the login-gated app.
bash scripts/dev.sh

# Direct fallback if you already ran the preflight:
python scripts/check-local-auth.py
uvicorn main:app --reload

# Opt out of .env.local on a localhost shell (test the production code path):
SOCRATINK_DISABLE_DOTENV_LOCAL=1 uvicorn main:app --reload
```

### Tests
```bash
# Full Python test suite
pytest

# Single test file
pytest tests/test_auth_gate_supabase.py -v

# Single test case
pytest tests/test_auth_gate_supabase.py::AuthGateRefreshWritebackTests::test_protected_api_writes_back_refreshed_session -v

# E2E smoke (local server running on localhost:8000)
bash scripts/qa-smoke.sh local

# E2E smoke (production)
bash scripts/qa-smoke.sh live

# Direct pytest smoke equivalent
SOCRATINK_BASE_URL=https://app.socratink.ai pytest tests/e2e/test_smoke.py -v
```

### Deploy verification
```bash
# Wait for Vercel deployment of origin/main and then run production smoke
bash scripts/verify-deploy.sh

# Verify a specific SHA or local HEAD
bash scripts/verify-deploy.sh <sha>
bash scripts/verify-deploy.sh HEAD
```

## Build / lint status
- There is no dedicated build step for local development; app runs directly via Uvicorn.
- There is no repository lint configuration checked in (no ruff/flake8/mypy config at repo root). Do not invent lint commands.
- Hosting/build behavior is defined by `vercel.json`:
  - all routes rewrite to `api/index.py`
  - serverless function bundles `public/**` and `app_prompts/**`

## Big-picture architecture
- Runtime surface is a single FastAPI app (`main.py`) deployed as a Vercel Python serverless entrypoint via `api/index.py`.
- Env loading is centralized in `runtime_env.py` (`load_app_env`); precedence is `process env > .env.local > .env`, and `.env.local` is skipped on Vercel/CI or when `SOCRATINK_DISABLE_DOTENV_LOCAL` is set. Auth startup depends on this ordering.
- `main.py` wires:
  - CORS middleware
  - sensitive static-file blocking middleware
  - auth/session gate middleware for protected HTML + selected API routes
  - app endpoints (`/api/extract`, `/api/extract-url`, `/api/drill`, `/api/repair-reps`, `/api/health`)
  - static frontend mount from `public/` for local serving
- AI behavior is centralized in `ai_service.py`:
  - Gemini client/retry/error normalization
  - extraction pipeline producing knowledge maps
  - drill evaluation/routing logic with session caps
  - repair-reps generation with strict structured output validation
  - prompt assets loaded from `app_prompts/`
- Auth is encapsulated under `auth/`:
  - `router.py` exposes login, guest, Google OAuth start/callback, `/api/me`, and logout routes
  - `service.py` implements `SupabaseAuthService` with sealed-cookie session handling, token verification/refresh, and OAuth state validation
  - `supabase_client.py` creates per-request stateless Supabase clients (session persistence disabled), which is important for Vercel safety
- Frontend is vanilla JS/HTML/CSS in `public/`; backend and frontend are tightly coupled through the above `/api/*` routes and auth redirects.
- `tools/pipette/` is a separate orchestration subsystem (CLI + lockfile + trace model) used by the `/pipette` workflow, with tests under `tests/pipette/`.

## QA expectations that matter in this repo
- Browser smoke (`tests/e2e/test_smoke.py`) is the load-bearing hosted verification signal.
- Use `bash scripts/qa-smoke.sh` for quick local/prod checks; use `bash scripts/verify-deploy.sh` when validating a deployed commit.
- Treat local success as insufficient proof of hosted correctness.

## /pipette note
- Before invoking `/pipette`, read:
  - `docs/superpowers/specs/2026-04-28-pipette-design.md`
  - `docs/superpowers/plans/2026-04-28-pipette.md`
- Operational commands are exposed via `python -m tools.pipette ...` and wrapped by slash-command flows.
