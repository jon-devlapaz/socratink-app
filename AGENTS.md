# AGENTS.md

This file provides guidance to all coding agents and automation working in this repository.

## Shared Agent Canon

The canonical shared workflow truth for repo agents now lives in `agents/`.

- Use `agents/README.md` for the boundary contract.
- Use `agents/founder/WORKFLOWS/` for founder workflow cards.
- Use `agents/LEARNINGS.md` only as the non-binding learning ledger for recurring founder/agent workflow friction; promote repeated patterns into canon before treating them as policy.
- Treat tool-specific directories (`.claude/`, `.codex/`, `.gemini/`) as runtime/config surfaces unless a migration ledger entry says otherwise.
- Treat `.agents/` as local substrate only: `.agents/skills/` is external install-state, `.agents/runtime/` is ignored runtime evidence, and neither is canonical doctrine.

### Boil the ocean

The marginal cost of completeness is near zero with AI. Do the whole thing. Do it right. Do it with tests. Do it with documentation. Do it so well that Jon is genuinely impressed, not politely satisfied, actually impressed.

Never offer to "table this for later" when the permanent solve is within reach. Never leave a dangling thread when tying it off takes five more minutes. Never present a workaround when the real fix exists. The standard isn't "good enough" — it's "holy shit, that's done."

Search before building. Test before shipping. Ship the complete thing. When Jon asks for something, the answer is the finished product, not a plan to build it. Time is not an excuse. Fatigue is not an excuse. Complexity is not an excuse. Boil the ocean.

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
- **`get_minimal_context` returns generic suggestions on small diffs.** When the diff is two JS files, it can surface unrelated Python flows. Skip it; go straight to `query_graph importers_of <file>`.

## Common development commands
### Local AI review
```bash
# Read-only advisory reviewer backed by local Ollama DeepSeek R1.
# Use canned modes; do not call raw Ollama for repo workflow review.
scripts/local-ai-review.sh check
scripts/local-ai-review.sh staged
scripts/local-ai-review.sh diff
scripts/local-ai-review.sh wip
scripts/local-ai-review.sh publish-preview
scripts/local-ai-review.sh smoke-local
scripts/local-ai-review.sh pytest -- .venv/bin/pytest tests/path/test_file.py -q --tb=short
```

- This command is advisory only. Verify findings against repo files, tests, browser checks, or deterministic helpers before acting.
- `publish-preview` still does not push or edit files, but it delegates to `scripts/agent-push.py` and may refresh local remote-tracking refs such as `origin/dev` and `no-mistakes/dev` before printing the preview.
- It must not replace `scripts/agent-push.py`, `scripts/no-mistakes-finish-dev.sh`, `scripts/git-wip-explain.sh`, `scripts/qa-smoke.sh`, or `./scripts/check-coverage.sh`.
- Do not pipe its output into shell commands or use it to generate/modify ack tokens.
- Keep Ollama local-only (`127.0.0.1` / `localhost`). Do not expose the local model server to LAN or public interfaces for this workflow.
- The wrapper refuses likely secrets and oversized payloads; narrow the diff or test output instead of bypassing those checks.

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
# scripts/dev.sh also sets SOCRATINK_E2E_LOCAL_GUEST=1 by default. Local
# browser tests use /auth/e2e/guest to mint a loopback-only guest cookie
# without creating real Supabase anonymous users or burning auth rate limits.
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

# Type-check baseline. PRIMARY gate is pyrefly; mypy stays on as a
# cross-check. Both are run by scripts/doctor.sh and by the GitHub
# Actions preflight workflow. Run BOTH locally before pushing.
#
# pyrefly takes no positional arg — it honors project-includes in
# pyrefly.toml. Passing `.` would silently override that scope.
.venv/bin/pyrefly check
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
# cobertura, then runs diff-cover against COMPARE_BRANCH when set or
# origin/main / main locally with --fail-under=100.
# Fails the script (exit 1) with the offending file and line numbers if any
# new line in the diff lacks a covering test.
./scripts/check-coverage.sh
```
- Threshold is on the diff, not the project total. Brand-new code without coverage fails; existing legacy gaps are not scored.
- Pure-deletion diffs, doc-only diffs, and config-only diffs are correctly no-ops — diff-cover only scores added/modified executable lines.
- Backend scope is `api auth db llm models source_intake` (see `scripts/test-cov.sh`). Frontend scope is `public/js/**` (see the URL filter in `scripts/generate-frontend-coverage.js`).
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
than "what should this do," follow `agents/founder/WORKFLOWS/03-prototyping.md`:
build several variants on a single
`?v=A|B|C|D` route under `public/_lab/<surface>-variants.html`, then capture and
review them. Two scripts compress the loop:

```bash
# Sweep the variants and screenshot each (defaults: dark mode, full page).
# Pre-flight checks: dev server reachable, surface exists in public/_lab/,
# every -v token actually has a `data-variant=...` attribute on the page.
scripts/snap.py library-empty-variants
scripts/snap.py library-empty-variants -v A,D,E --open    # custom variants + auto-Preview (macOS)
scripts/snap.py --list                                    # what _lab surfaces exist?

# Share one _lab prototype to a phone over the internet. This serves only
# public/ through a loopback static server, then opens a temporary ngrok URL.
# Keep the command running while reviewing; Ctrl-C closes the tunnel.
scripts/share-lab.sh minimal-gestalt-overview
scripts/share-lab.sh --list

# Pipe a customer-persona prompt through Gemini, filtered and auto-logged
# to .playwright-mcp/persona-<timestamp>.txt. Methodology and reusable
# template lives at agents/_templates/customer-persona-prompt.md.
scripts/persona.sh <prompt-file>
cat prompt.txt | scripts/persona.sh
scripts/persona.sh --template      # print template path
```

Capture the verdict in a sibling `<surface>-variants.NOTES.md` next to the
prototype HTML so the answer survives the lab being deleted (the shared
prototype workflow's "delete or absorb when done" rule). When a variant choice is
load-bearing for the domain — i.e., the meaning of a surface or term
changes — also update `UBIQUITOUS_LANGUAGE.md` and write an ADR in `docs/adr/`. If
the decision elevates a non-obvious design principle, surface it in `DESIGN.md` §4.

## Build / lint status
- There is no dedicated build step for local development; app runs directly via Uvicorn.
- Type-check baseline is two-tool: **pyrefly is the primary gate**, **mypy is the cross-check**. Both must be green. They run side-by-side in `scripts/doctor.sh` and in CI; agents/humans must run both before pushing.
  - **pyrefly** (Python 3.13, `preset = "legacy"`, `check-unannotated-defs = true`) — config in `pyrefly.toml`. Canonical invocation: `.venv/bin/pyrefly check` (no positional arg — `pyrefly check .` would override `project-includes` and pick up `tests/` and `api/`, both of which we intentionally exclude to mirror mypy's `[mypy-tests.*]` / `[mypy-api.*]` posture). Version is pinned in `scripts/doctor.sh` (`PYREFLY_VERSION`) — keep it there, not in `requirements-dev.txt`, so the gate auto-bootstraps the exact version.
  - **mypy** (Python 3.13, `warn_unreachable`, `strict_optional`, `check_untyped_defs`, `warn_return_any`) — config in `mypy.ini`. Canonical invocation: `mypy .`. Honors `mypy.ini` exclude list (`.venv/`, `tests/e2e/`, `public/`, `scripts/`, generated trees) plus per-module `ignore_errors` for `tests.*` and `api.*`.
  - **Scope must stay aligned** between the two configs. If you change one exclude list, change the other. `pyrefly.toml` uses positive `project-includes` (`main.py`, `ai_service.py`, `learning_commons.py`, `runtime_env.py`, `auth`, `llm`, `source_intake`, `models`) — add new top-level modules there if you create them, otherwise pyrefly silently skips them.
- No ruff/flake8 config is checked in. Do not invent lint commands beyond `pyrefly check` and `mypy .`.
- CI gate: `.github/workflows/preflight.yml` runs on every `pull_request` and on pushes to `main`/`dev`. The `preflight` job runs the repo bootstrap (`bash scripts/bootstrap-python.sh`), `bash scripts/doctor.sh`, and `.venv/bin/pytest -q --ignore=tests/e2e`; the `coverage` job installs Node/Chromium, starts a loopback app with `SOCRATINK_E2E_LOCAL_GUEST=1`, selects `COMPARE_BRANCH`, and runs `bash scripts/check-coverage.sh`. It generates a throwaway `SESSION_COOKIE_KEY` Fernet key plus CI-safe dummy auth env so the gates exercise bootstrap/auth paths without real Supabase credentials. This workflow is intentionally narrower than `scripts/preflight-deploy.sh`, which stays local-only because it also runs `vercel build` against real Vercel credentials.
- Hosting/build behavior is defined by `vercel.json`:
  - all routes rewrite to `api/index.py`
  - serverless function explicitly includes `public/**` and `app_prompts/**`
  - serverless function excludes everything else (tests, docs, scripts, db, agents, node_modules, dotfiles, and root-level config/docs like `*.md`, `*.yaml`, `*.json`, `*.ini`); see `vercel.json` for the canonical glob

### Stylesheet cache-bust discipline
- Stylesheets in `public/` are loaded via a chain: `<link rel="stylesheet" href="/css/index.css?v=N">` in `public/index.html` → `public/css/index.css` → `public/styles.css` → `public/css/*.css`, with `antigravity.css` and `paper.css` still imported directly by `public/css/index.css`.
- **When editing a stylesheet imported by `public/styles.css`, bump all THREE version pins:**
  1. The component import in `public/styles.css` (e.g., `./css/concept-page.css?v=9` → `?v=10`).
  2. The `../styles.css?v=M` import in `public/css/index.css`.
  3. The outer `/css/index.css?v=N` link in `public/index.html`.
- For stylesheets imported directly by `public/css/index.css` (currently `antigravity.css` and `paper.css`), bump that import pin plus the outer `/css/index.css?v=N` link.
- Bumping only the inner pin is **not enough** — the browser keeps serving the cached parent CSS file, which still points at the previous child `?v=` value.
- The numbers don't have to match — only that each relevant parent and child pin changes when its file changes. When in doubt, trace the import chain from `public/index.html` and bump every parent link on that path.
- Catch missed bumps in pre-commit by grepping `@import url(.*\?v=` and `<link rel="stylesheet"` for the version strings you expect.

## Agent bootstrap discovery
- Canonical session bootstrap: `agents/ONBOARDING.md`.
- Deterministic agent quality rules live in `agents/QUALITY.md`.
- Do not create parallel agent source-of-truth files. If compatibility is needed, keep a tiny redirect file pointing to `AGENTS.md` or the canonical bootstrap.
- Before substantive work, read the binding docs for the task. At minimum for cross-agent or product-science work, read `AGENTS.md`, `docs/project/state.md`, and `agents/ONBOARDING.md`.
- For *structural* orientation — what files are load-bearing, what depends on what, where coverage gaps live — use the live Code Review Graph flow in `docs/project/code-review-graph-sop.md` rather than relying on stale point-in-time snapshots.

## Project-local agent skills (skills.sh marketplace)

Three community skills are installed project-local under `.agents/skills/`, symlinked into `.claude/skills/` for Claude Code discovery. Install is local-machine state only (`.agents/` is gitignored, no lockfile carried) — re-install on a new machine via the commands below if ever needed. Do not treat `.agents/skills/` as repo canon.

The repository also tracks `agents/superpowers` as a Git submodule pointing at
the upstream Superpowers skill source. It is reference material, not runtime
canon and not a replacement for this repo's `agents/` workflow docs. In a fresh
checkout, initialize it only when you need to inspect that upstream source:

```bash
git submodule update --init -- agents/superpowers
```

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

For a current architecture overview, use the Code Review Graph tools described in §Code exploration (`get_architecture_overview_tool`, `list_graph_stats_tool`, `query_graph_tool`) and the founder FAQ at `agents/founder/CODE-REVIEW-GRAPH-FAQ.md`. Static file-path maps go stale fast; the graph is rebuilt on every change.

## QA expectations that matter in this repo
- Browser smoke (`tests/e2e/test_smoke.py`) is the load-bearing hosted verification signal.
- Use `bash scripts/qa-smoke.sh` for quick local/prod checks; use `bash scripts/verify-deploy.sh` when validating a deployed commit.
- Treat local success as insufficient proof of hosted correctness.
- Run browser smoke without being asked after deploys, merges to `main`, `git push origin main` with verification framing, before claiming "the site works" or "X is live", when investigating hosted-only symptoms, and after high-risk changes to `main.py`, `api/index.py`, or `public/index.html`.
- Same-origin browser console errors and asset failures are real bugs. Cross-origin noise is filtered by the smoke suite; the only same-origin requestfailure exception is narrow Chromium `ERR_ABORTED` bootstrap noise for `/api/health` and `/api/me`, not HTTP failures or app assets.
- On smoke failure, report the pytest output and inspect the Playwright trace at `test-results/<test>/trace.zip` with `playwright show-trace`.
- The smoke suite checks `/api/health`, critical homepage DOM, guest session labeling, source-less launch/compare flow, Constellation route view, training-derived concept evidence paths, corrupt-training recovery, non-score-eligible attempts, drawer visibility after concept entry, feedback modal/sidebar behavior, library card reopen behavior, active-concept delete/reset behavior, same-origin console errors, same-origin asset failures, and theme preloader resilience.
- Before declaring an implementation task complete on production code — Python under the backend scope (`api/`, `auth/`, `db/`, `llm/`, `models/`, `source_intake/`) or JS under `public/js/**` — run `./scripts/check-coverage.sh` and confirm exit 0. The gate enforces 100% coverage on the diff against `COMPARE_BRANCH` when set or `origin/main` / `main` locally using V8-via-CDP for the frontend and pytest for the backend; see "Coverage gate" under common dev commands. Skip only for doc-only, config-only, prototype-only (`public/_lab/`), or pure-deletion diffs. Treat a coverage failure the same way you would treat a smoke-test failure: fix the gap before declaring done, do not bypass.

## Audit log 2026-05-12

- Claims checked: 12
- Verified: 12
- Stale: 0
- Indeterminate: 0
- Stale claims with line refs: none found in the audited set.

Any meaningful product/architecture change must update exactly one canonical doc: project/state.md, an ADR, the relevant product/design spec, or project/doc-map.md.
