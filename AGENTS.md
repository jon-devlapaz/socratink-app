# AGENTS.md

This file provides guidance to all coding agents and automation working in this repository.

## Shared Agent Canon

The canonical shared workflow truth for repo agents now lives in `agents/`.

- Use `agents/README.md` for the boundary contract.
- Use `agents/founder/WORKFLOWS/` for founder workflow cards.
- Treat tool-specific directories (`.claude/`, `.codex/`, `.gemini/`) as runtime/config surfaces unless a migration ledger entry says otherwise.

### Boil the ocean

The marginal cost of completeness is
near zero with AI. Do the whole thing.
Do it right. Do it with tests. Do it
with documentation. Do it so well that
Jon is genuinely impressed, not
politely satisfied, actually impressed.
Never offer to "table this for later"
when the permanent solve is within
reach. Never leave a dangling thread
when tying it off takes five more
minutes. Never present a workaround
when the real fix exists. The standard
isn't "good enough" it's "holy shit,
that's done." Search before building.
Test before shipping. Ship the
complete thing. When Jon asks for
something, the answer is the finished
product, not a plan to build it. Time
is not an excuse. Fatigue is not an
excuse. Complexity is not an excuse.
Boil the ocean.

## First principles for this repo
- Keep changes surgical and scope-locked. Do not broaden features or refactor unrelated areas.
- Prefer the simplest implementation that satisfies the task.
- For non-trivial work, convert the request into verifiable goals (typically via targeted tests).
- MVP doctrine applies: separate true blockers from nice-to-have polish.
- Preserve product truth: never fake mastery, graph progress, or learner knowledge.
- `UBIQUITOUS_LANGUAGE.md` is the glossary authority; use its terms verbatim in code and docs, and do not invent synonyms.
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

This repo is configured for two complementary code-intelligence layers. Use them in sequence, not in competition. Both exist to keep the working context window small and the structural reasoning honest.

### Layer 1 — Claude Context (semantic discovery)
Use the `claude-context` MCP server (`search_code`, `index_codebase`, `get_indexing_status`, `clear_index`) for fuzzy, conceptual orientation when you do not yet know the file or symbol. It replaces blind `grep`/`glob` sweeps that bloat context.
- Use it for needle-in-haystack questions: "find the logic that handles guest users", "where do we validate Supabase JWTs", "code that throttles drill cadence", "the place we normalize Gemini API errors".
- Output is vector chunks ranked by semantic similarity. Treat them as leads to verify, not ground truth.
- Re-index after large refactors or before relying on search results in a long-running session (`get_indexing_status` to confirm freshness).

### Layer 2 — Code-Review Graph (deterministic structure)
Once a candidate file or symbol is in hand, switch to the code-review graph for caller/callee, blast-radius, and review safety. The graph gives structural guarantees that semantic search cannot.
- `get_minimal_context_tool` for initial orientation on a known node
- `detect_changes` and `get_review_context` for review
- `get_impact_radius` and `get_affected_flows` for blast-radius analysis
- `query_graph` / `semantic_search_nodes` for callers, callees, imports, and tests

### Layer 3 — Context7 (external API documentation, biased liberal)
Local layers cover code that lives in this repo. They do not know what a third-party SDK, platform, framework, or CLI does today. Reach for Context7 liberally — **prefer fetching current docs over relying on model memory whenever the answer hinges on a third-party surface**. Use it even when you think you know the answer; training data lags behind real APIs by months, and silent staleness is the failure mode.

Trigger Context7 for any of:
- **Research questions** about a library/framework/SDK/CLI/platform, even without a pending edit ("how does Supabase RLS work?", "what's the FastAPI lifespan API?", "Playwright trace viewer options").
- **Code generation** that imports or calls a third-party surface — including writing new code from scratch, not just edits to existing code.
- **Edits** that touch a third-party surface, especially version-sensitive ones.
- **Setup / configuration / migration** questions for any installed library or hosted platform.
- **Debugging** that suspects library-specific behavior (auth flow, response shape, error semantics, deprecation).

Concrete surfaces in this repo that should route through Context7:
- **Python**: `fastapi`, `starlette`, `pydantic`, `uvicorn`, `google-genai` (Gemini), `supabase` (supabase-py), `pyjwt`, `cryptography`, `beautifulsoup4`, `youtube-transcript-api`, `aiofiles`, `urllib3`, `charset-normalizer`.
- **Platform**: Vercel (routing, serverless function limits, build, env vars, `vercel.json`), Supabase (auth, RLS, storage, OAuth providers).
- **AI APIs**: Gemini, OpenAI, Anthropic — model IDs, tool use, structured output, prompt caching, streaming.
- **Test / browser**: Playwright APIs, traces, fixtures, the browser DOM/Web APIs called from `public/*.js`.
- **CLI tools** the agent invokes directly (e.g., `vercel`, `playwright`, `supabase`, `gh`) when behavior matters.

How to query well:
1. Start with `resolve-library-id` unless the user gave an exact `/org/project` ID. Pick by exact name match, description fit, snippet count, source reputation, benchmark score. Try alternate names if results look off ("next.js" not "nextjs"; "supabase-py" not just "supabase").
2. Inspect the installed version first (`requirements.txt`, `requirements-dev.txt`, `package.json`, `vercel.json`) and prefer a version-pinned library ID where available.
3. Pass the user's full question to `query-docs`, not a single keyword.
4. If Context7 docs do not obviously match the installed version, state the uncertainty before editing or generating code.

Out of scope for Context7:
- Socratink product doctrine, graph truth, drill behavior, source ownership, architecture decisions, verification policy. Local binding docs (`AGENTS.md`, `docs/product/evidence-weighted-map.md`, `docs/product/spec.md`, the rest of the canonical doc set) remain authoritative on what Socratink should build.
- Refactoring local code, writing scripts from scratch with no third-party dependency, debugging business logic, code review, general programming concepts.
- Never send secrets, private source, customer data, or internal implementation details to Context7.

### Handoff rule
Discover with Claude Context → confirm structure with the graph → fetch external API docs with Context7 when the edit touches a third-party surface → only then read source. Skipping the graph step on a non-trivial change is how unsafe edits ship. Skipping the Context7 step on a third-party-SDK edit is how stale-API breakage ships. Reading source files top-to-bottom without these layers is the worst of all worlds: high context cost, no structural guarantee, no current-API guarantee.

### Hard rules
- Default to minimal graph detail first. Escalate to full source snippets only when the minimal view is insufficient.
- Reach for `grep`/`glob`/`Read` only when both layers above are insufficient, or to verify a specific claim.
- Call-count data from the graph can under-report. Always verify "single call site" or "only caller" claims with textual search such as `rg "<symbol>"` before acting on them — this rule survives the Claude Context addition; semantic similarity is even less authoritative for call-site enumeration than the graph.
- Local-first search applies: check local docs, scripts, and skills before remote sources or external agents. Before building new functionality, verify there is not already a local script, command, or documented workflow that does it.

### Known caveat — doc-heavy corpus skews semantic results
This repo carries a large body of markdown (handoffs, design specs, ADRs, ubiquitous-language docs) alongside ~96 Python files. In practice, Claude Context's `search_code` consistently ranks markdown chunks above Python source even for queries naming literal class or function symbols (e.g. `SupabaseAuthService`). Treat this as a feature for *intent* discovery and a limitation for *symbol* discovery.

### Practical query routing (what to reach for first)
Empirical comparison run on 2026-05-04 against this codebase:

1. **Known symbol or filename** → `rg "<symbol>"` or CRG `semantic_search_nodes` (FTS5 alone). Both return the real Python file as the first hit in <100ms. Skip Claude Context here — it returns docs first.
2. **Multi-word natural-language concept where you don't know the symbol** → Claude Context `search_code`. CRG's FTS5 falls back to AND-matching word-by-word and returns 0 hits for queries like "sealed cookie session" or "drill evaluation routing". CC at least surfaces the relevant handoff/spec doc, which usually names the symbol you actually want.
3. **Blast radius, callers, callees, affected flows, tests-for** → CRG graph tools (`get_impact_radius`, `query_graph`, `get_affected_flows`). No alternative tool produces this.
4. **"Where does our spec say…"** → Claude Context `search_code` (this is its strongest mode on this corpus).
5. **"Single call site" claims** → always verify with `rg "<symbol>"`. Both CRG and CC are floors, not ceilings.

When CC returns sources only, pass `extensionFilter: [".py"]` (or `.js`, `.css`). But note: in observed cases the result list often becomes empty rather than reordering — the underlying Voyage embedding for the query just doesn't score the Python chunks above the threshold. Falling back to CRG/`rg` is the right move.

### Pitfalls observed in practice
- **Frontend bundle topology inflates risk scores.** `get_impact_radius` on any file imported into `public/js/app.js` reports HIGH risk and 50+ affected files. That is a topology artifact, not a real blast radius. Trust the callers/callees list, distrust the headline risk score for client JS.
- **Symbol-shaped queries beat prose for semantic search.** "AudioFX bindUnlock" finds nodes; "threshold sound autoplay unlock" returns 0. When `semantic_search_nodes` falls back to keyword mode, prose queries silently fail.
- **JS parser under-reports more than Python.** `query_graph file_summary` on `public/js/audio.js` lists 4 of its functions and misses the `play*` helpers. The floor-not-ceiling rule is sharper for JS files than for Python.
- **`get_minimal_context` returns generic suggestions on small diffs.** When the diff is two JS files, it surfaces unrelated admin Python flows. Skip it; go straight to `query_graph importers_of <file>`.

## Common development commands
### Environment setup
```bash
bash scripts/bootstrap-python.sh
playwright install chromium
```

### Run locally
```bash
# Preferred: validates local auth env before starting the login-gated app.
# Binds Uvicorn to 127.0.0.1 by default (loopback-only). For on-device mobile
# QA (see docs/qa/antigravity-mobile-qa-prompt.md), override with
# HOST=0.0.0.0 bash scripts/dev.sh so it's reachable at http://<your-LAN-IP>:8000.
bash scripts/dev.sh

# Direct fallback if you already ran the preflight:
python scripts/check-local-auth.py
uvicorn main:app --reload

# Opt out of .env.local on a localhost shell (test the production code path):
SOCRATINK_DISABLE_DOTENV_LOCAL=1 uvicorn main:app --reload

# Opt out of the auto-guest dev escape hatch (test the /login wall locally).
# scripts/dev.sh sets SOCRATINK_DEV_AUTOGUEST=1 by default. Two effects, both
# gated on this single env var (and hard-disabled in any VERCEL / VERCEL_ENV
# / CI runtime):
#   1. The auth gate trampolines protected GETs through /auth/guest instead
#      of /login, so agents and ad-hoc local browsing skip the wall.
#   2. /api/me returns dev_mode: true, which lets the frontend allow guest
#      sessions through the concept-create dialog. Without dev_mode the
#      dialog shows "Guest mode uses sample maps. Sign in to extract your
#      own content into a draft map." and blocks the LLM extract path.
# Restart the server after toggling — uvicorn --reload reloads code, not env.
SOCRATINK_DEV_AUTOGUEST=0 bash scripts/dev.sh

# Free localhost:8000–8009 if a previous uvicorn / smoke run left a listener
# behind. SIGTERM first, then SIGKILL only for survivors.
bash scripts/kill-800x.sh
```

### Tests
```bash
# Agent docs / bootstrap minimum verification
bash scripts/doctor.sh

# Type-check baseline (honors mypy.ini exclude list; also run by
# scripts/doctor.sh and by the GitHub Actions preflight workflow).
mypy .

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

# Manual AI pipeline validation against a fixture (extract + drill in terminal,
# tagged run_mode=fixture in telemetry). Use before merging changes to
# ai_service.py or ProvisionalMap.
python scripts/run_tasting_fixture.py
```

### Coverage gate
```bash
# Full-stack diff-coverage gate. Runs the Python suite with coverage.xml,
# captures Chromium V8 coverage from the e2e smoke run via the Chrome
# DevTools Protocol, normalizes it through monocart-coverage-reports into
# cobertura, then runs diff-cover against origin/main with --fail-under=100.
# Fails the script (exit 1) with the offending file and line numbers if any
# new line in the diff lacks a covering test.
./scripts/check-coverage.sh
```
- Threshold is on the diff, not the project total. Brand-new code without coverage fails; existing legacy gaps are not scored.
- Pure-deletion diffs, doc-only diffs, and config-only diffs are correctly no-ops — diff-cover only scores added/modified executable lines.
- Backend scope is `admin api auth db llm models source_intake` (see `scripts/test-cov.sh`). Frontend scope is `public/js/**` (see the URL filter in `scripts/generate-frontend-coverage.js`).
- If the script crashes outside of a coverage failure (missing V8 data, missing `coverage.xml`), inspect `.qa-runs/v8-coverage/*.json` and `.qa-runs/coverage-reports/cobertura-coverage.xml` before reaching for `--no-verify`-style escapes. The gate is the brake; do not bypass it silently.

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

### Variant prototyping (UI register / copy decisions)
For UI surfaces where the right answer is "what should this look/read like" rather
than "what should this do," follow the `prototype` skill at
`.claude/skills/prototype/SKILL.md`: build several variants on a single
`?v=A|B|C|D` route under `public/_lab/<surface>-variants.html`, then capture and
review them. Two scripts compress the loop:

```bash
# Sweep the variants and screenshot each (defaults: dark mode, full page).
# Pre-flight checks: dev server reachable, surface exists in public/_lab/,
# every -v token actually has a `data-variant=...` attribute on the page.
scripts/snap.py library-empty-variants
scripts/snap.py library-empty-variants -v A,D,E --open    # custom variants + auto-Preview (macOS)
scripts/snap.py --list                                    # what _lab surfaces exist?

# Pipe a customer-persona prompt through Gemini, filtered and auto-logged
# to .playwright-mcp/persona-<timestamp>.txt. Methodology and reusable
# template live at docs/codex/customer-persona-prompt-template.md.
scripts/persona.sh <prompt-file>
cat prompt.txt | scripts/persona.sh
scripts/persona.sh --template      # print template path
```

Capture the verdict in a sibling `<surface>-variants.NOTES.md` next to the
prototype HTML so the answer survives the lab being deleted (the prototype
skill's "delete or absorb when done" rule). When a variant choice is
load-bearing for the domain — i.e., the meaning of a surface or term
changes — also update `CONTEXT.md` and write an ADR in `docs/adr/`.

## Build / lint status
- There is no dedicated build step for local development; app runs directly via Uvicorn.
- Type-check baseline lives in `mypy.ini` at the repo root (Python 3.13, `warn_unreachable`, `strict_optional`, `check_untyped_defs`, `warn_return_any`, etc.). The canonical invocation is `mypy .`, which honors the `mypy.ini` exclude list (`.venv/`, `tests/e2e/`, `public/`, `scripts/`, generated trees). The same command is run by `scripts/doctor.sh` and by CI.
- No ruff/flake8 config is checked in. Do not invent lint commands beyond `mypy .`.
- CI gate: `.github/workflows/preflight.yml` runs `mypy .` + `pytest -q --ignore=tests/e2e` on every `pull_request` and on pushes to `main`/`dev`. It generates a throwaway `SESSION_COOKIE_KEY` Fernet key for the run; production sets the real key via Vercel env. This workflow is intentionally narrower than `scripts/preflight-deploy.sh`, which stays local-only because it also runs `vercel build` against real Vercel credentials.
- Hosting/build behavior is defined by `vercel.json`:
  - all routes rewrite to `api/index.py`
  - serverless function explicitly includes `public/**` and `app_prompts/**`
  - serverless function excludes tests, docs, logs, local env files, caches, and agent/tooling artifacts

### Stylesheet cache-bust discipline
- Stylesheets in `public/` are loaded via a chain: `<link rel="stylesheet" href="/css/index.css?v=N">` in `public/index.html` → `index.css` `@imports` `tokens.css`, `styles.css`, `antigravity.css`, `paper.css` (each with their own `?v=M` cache-bust pins).
- **When editing a stylesheet that's imported via `@import` in `index.css`, bump BOTH version pins:**
  1. The inner `?v=M` on the `@import` line inside `public/css/index.css` (e.g., `?v=14` → `?v=15` for an antigravity edit).
  2. The outer `?v=N` on the `<link>` to `/css/index.css` inside `public/index.html` (e.g., `?v=3` → `?v=4`).
- Bumping only the inner pin is **not enough** — the browser keeps serving the cached `index.css?v=N`, which still has the old `?v=M-1` import baked in. The cached outer file points at the cached inner file; bumping only one breaks the chain at the wrong link.
- The two numbers don't have to match — only that each changes when its file changes. When in doubt, bump both.
- Catch missed bumps in pre-commit by grepping `@import url(.*\?v=` and `<link rel="stylesheet"` for the version strings you expect.

## Agent bootstrap discovery
- Canonical session bootstrap: `docs/codex/onboarding.md`.
- Legacy compatibility path: `docs/codex/session-bootstrap.md` redirects agents to onboarding.
- If an agent instruction references `docs/codex/session-bootstrap.md`, treat that as `docs/codex/onboarding.md`.
- Deterministic agent quality rules live in `docs/codex/agent-quality.md`.
- Do not create parallel agent source-of-truth files. If compatibility is needed, keep a tiny redirect file pointing to `AGENTS.md` or the canonical bootstrap.
- Before substantive work, read the binding docs for the task. At minimum for cross-agent or product-science work, read `AGENTS.md`, `docs/project/state.md`, and `docs/codex/onboarding.md`.
- For *structural* orientation — what files are load-bearing, what depends on what, where coverage gaps live — read `docs/project/crg-architecture-snapshot-2026-05-04.md` first. It's a CRG-derived briefing that gives you the shape of the codebase in ~3 minutes so you don't have to grep your way to it. Re-generated after major refactors; the underlying graph itself is always live (auto-updated on every `Edit|Write|Bash` via `.claude/settings.json` `PostToolUse` hook), so the snapshot is the periodic crystallisation, not a cache.

## Project-local agent skills (skills.sh marketplace)

Three community skills are installed project-local under `.agents/skills/`, symlinked into `.claude/skills/` for Claude Code discovery. Install is local-machine state (`.agents/` is gitignored, no lockfile carried) — re-install on a new machine via the commands below if ever needed.

| Skill | Source | When to invoke | Trust signals |
|---|---|---|---|
| `playwright-cli` | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) — **official Microsoft** | Authoring or debugging Playwright tests, smoke flows (`scripts/qa-smoke.sh`, `tests/e2e/`), persona automation, trace inspection, browser context configuration. Pairs with the `playwright` MCP for live browser work. | 33.1K installs; Socket 0 alerts; **Snyk flagged High Risk** — accepted given Microsoft as publisher, but glance at `SKILL.md` before relying on it for novel patterns. |
| `gemini-interactions-api` | [google-gemini/gemini-skills](https://github.com/google-gemini/gemini-skills) — **official Google** | Writing or refactoring code that calls `google-genai` (drill evaluation in `ai_service.py`, extraction pipeline, any new Gemini API surface). Covers text/multi-turn/multimodal/streaming/function calling/structured output, and migration from the legacy `generateContent` API. | 3.3K installs; Socket 0 alerts; Snyk Medium. |
| `fastapi` | [fastapi/fastapi](https://github.com/fastapi/fastapi) — **official maintainers** | Designing or refactoring FastAPI routes and Pydantic models — keeps endpoint and schema patterns aligned with current FastAPI features rather than memory of older idioms. Use proactively when touching `main.py`, `routes/`, or any `pydantic` model. | 2.4K installs; Socket 0 alerts; Snyk Low. |

These skills are **complementary to Context7, not a replacement**: skills carry curated patterns and conventions; Context7 fetches the current public API reference. For an unfamiliar feature in any of these surfaces, invoke the skill first for conventions, then Context7 for the version-pinned API shape if needed.

### Install / remove
- `npx skills add <owner/repo> -s <skill> -y` from this repo root — installs project-local.
- `npx skills list` — see what's installed.
- `npx skills remove <name>` — uninstall if a skill stops paying off.

Each project-local skill consumes session-start token budget. Treat installs as deliberate; remove ones that aren't firing usefully during quarterly `session-retro` curation.

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

## QA expectations that matter in this repo
- Browser smoke (`tests/e2e/test_smoke.py`) is the load-bearing hosted verification signal.
- Use `bash scripts/qa-smoke.sh` for quick local/prod checks; use `bash scripts/verify-deploy.sh` when validating a deployed commit.
- Treat local success as insufficient proof of hosted correctness.
- Run browser smoke without being asked after deploys, merges to `main`, `git push origin main` with verification framing, before claiming "the site works" or "X is live", when investigating hosted-only symptoms, and after high-risk changes to `main.py`, `api/index.py`, or `public/index.html`.
- Same-origin browser console errors and asset failures are real bugs. Cross-origin noise is filtered by the smoke suite; do not allow-list failures unless they are proven third-party.
- On smoke failure, report the pytest output and inspect the Playwright trace at `test-results/<test>/trace.zip` with `playwright show-trace`.
- The smoke suite checks `/api/health`, critical homepage DOM, guest session labeling, drawer visibility after concept entry, library card reopen behavior, active-concept delete/reset behavior, same-origin console errors, same-origin asset failures, and theme preloader resilience.
- Before declaring an implementation task complete on production code — Python under the backend scope (`admin/`, `api/`, `auth/`, `db/`, `llm/`, `models/`, `source_intake/`) or JS under `public/js/**` — run `./scripts/check-coverage.sh` and confirm exit 0. The gate enforces 100% coverage on the diff against `origin/main` using V8-via-CDP for the frontend and pytest for the backend; see "Coverage gate" under common dev commands. Skip only for doc-only, config-only, prototype-only (`public/_lab/`), or pure-deletion diffs. Treat a coverage failure the same way you would treat a smoke-test failure: fix the gap before declaring done, do not bypass.
