# AGENTS.md

This file provides guidance to all coding agents and automation working in this repository.

## First principles for this repo
- Keep changes surgical and scope-locked. Do not broaden features or refactor unrelated areas.
- Prefer the simplest implementation that satisfies the task.
- For non-trivial work, convert the request into verifiable goals (typically via targeted tests).
- MVP doctrine applies: separate true blockers from nice-to-have polish.
- Preserve product truth: never fake mastery, graph progress, or learner knowledge.
- State assumptions before acting when the task is ambiguous. If multiple reasonable interpretations exist, present them instead of silently choosing.
- Push back when a simpler approach satisfies the goal or when the requested path risks product truth, deployment safety, or unnecessary scope expansion.

## Execution discipline
- No features beyond the ask.
- No abstractions, configurability, or generic frameworks for single-use code.
- Match the existing style and ownership boundaries.
- Do not refactor adjacent code, comments, or formatting unless required to satisfy the request.
- Mention unrelated dead code or defects, but do not delete or fix them unless asked.
- Remove orphaned code, docs, or tests created by your own change.
- Every changed line should trace back to the user request or to required verification.
- If the task is multi-step, state a short plan with the verification for each major step.
- For fixes, prefer a reproducing test when practical; for refactors, preserve behavior and run before/after-relevant checks when practical.

## Code exploration and review workflow
- This repo is configured for a code-review knowledge graph. Use graph tools before grep/glob/read whenever available.
- Start with minimal graph context, then escalate only if needed:
  - `get_minimal_context_tool` for initial orientation
  - `detect_changes` and `get_review_context` for review
  - `get_impact_radius` and `get_affected_flows` for blast-radius analysis
  - `query_graph` / `semantic_search_nodes` for callers, callees, imports, and tests
- Use grep/glob/read only when graph coverage is insufficient.
- Default to minimal graph detail first. Escalate to full source snippets only when the minimal view is insufficient.
- Caveat from project rules: call-count data can under-report; verify "single call site" claims with textual search such as `rg "<symbol>"`.
- Local-first search applies: check local docs, scripts, and skills before remote sources or external agents. Before building new functionality, verify there is not already a local script, command, or documented workflow that does it.

## Common development commands
### Environment setup
```bash
bash scripts/bootstrap-python.sh
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
# Agent docs / bootstrap minimum verification
bash scripts/doctor.sh

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

# E2E smoke (explicit URL)
bash scripts/qa-smoke.sh https://custom-url.com

# Direct pytest smoke equivalent
SOCRATINK_BASE_URL=https://app.socratink.ai pytest tests/e2e/test_smoke.py -v
```

### Deploy verification
```bash
# Validate the same dependency/build surface Vercel will use
bash scripts/preflight-deploy.sh

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
  - serverless function explicitly includes `public/**` and `app_prompts/**`
  - serverless function excludes tests, docs, logs, local env files, caches, and agent/tooling artifacts

## Agent bootstrap discovery
- Canonical session bootstrap: `docs/codex/onboarding.md`.
- Legacy compatibility path: `docs/codex/session-bootstrap.md` redirects agents to onboarding.
- If an agent instruction references `docs/codex/session-bootstrap.md`, treat that as `docs/codex/onboarding.md`.
- Deterministic agent quality rules live in `docs/codex/agent-quality.md`.
- Do not create parallel agent source-of-truth files. If compatibility is needed, keep a tiny redirect file pointing to `AGENTS.md` or the canonical bootstrap.
- Before substantive work, read the binding docs for the task. At minimum for cross-agent or product-science work, read `AGENTS.md`, `docs/project/state.md`, and `docs/codex/onboarding.md`.

## Multi-agent and worktree safety
- Prefer a small party. Pull in `theta`, `elliot`, `sherlock`, or `thurman` only when the task actually needs that specialty.
- Keep read-only agents read-only unless implementation is explicitly required.
- Code-modifying agents must verify against the latest uncommitted state, not just `HEAD`.
- Worktree, branch, or ownership conflicts must be surfaced honestly. Never fabricate a resolution.
- For multi-phase refactors, get peer review before merge when the change crosses ownership boundaries or product invariants.
- When specialists disagree, record the disputed point, evidence, decision owner, chosen path, and resulting state/doc updates.

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
- Run browser smoke without being asked after deploys, merges to `main`, `git push origin main` with verification framing, before claiming "the site works" or "X is live", when investigating hosted-only symptoms, and after high-risk changes to `main.py`, `api/index.py`, or `public/index.html`.
- Same-origin browser console errors and asset failures are real bugs. Cross-origin noise is filtered by the smoke suite; do not allow-list failures unless they are proven third-party.
- On smoke failure, report the pytest output and inspect the Playwright trace at `test-results/<test>/trace.zip` with `playwright show-trace`.
- The smoke suite checks `/api/health`, critical homepage DOM, guest session labeling, drawer visibility after concept entry, library card reopen behavior, active-concept delete/reset behavior, same-origin console errors, same-origin asset failures, and theme preloader resilience.

## /pipette note
- Before invoking `/pipette`, read:
  - `docs/superpowers/specs/2026-04-28-pipette-design.md`
  - `docs/superpowers/plans/2026-04-28-pipette.md`
- `/pipette doctor` validates prerequisites before heavy planning.
- `/pipette <topic>` runs Steps -1 through 7 with deterministic gates and per-feature artifacts under `docs/pipeline/`.
- Pause/resume via `/pipette resume <topic>`; abort via `/pipette abort <topic>`.
- Operational commands are exposed via `python -m tools.pipette ...` and wrapped by slash-command flows.
