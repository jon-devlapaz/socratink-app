# Lego-ification Roadmap

> **Note for agentic workers:** This is a **strategic roadmap**, not a directly-executable bite-sized plan. Each phase gets its own detailed implementation plan written when picked up (use `superpowers:writing-plans`). Phases must be executed in order — Phase 1 → Phase 5 — because later phases depend on contracts established earlier.

## ⚠️ Update: Analytics Removed (2026-04-27)

The entire analytics surface was torn out in commits `b5ac709` (frontend), `9c973b4` (backend package + endpoints + tests), and `03d416a` (telemetry writers in ai_service.py and main.py) to clear cognitive load before fleshing out the core game loop. Total: ~3,650 LOC removed across 13 deleted files + 6 modified.

**Implications for this roadmap:**

- **Phase 1's `analytics/` package no longer exists.** The "scripts/ → production" rule it established still stands as roadmap doctrine, but the specific package that proved the rule is gone. Re-adding analytics later means re-instrumenting from scratch.
- **The "Production imports from scripts/" success-metric row is no longer meaningful** (no scripts/ → production smell exists anymore — the script that caused it is also deleted). Treat that row as historical.
- **Phase 4's reference to `scripts/run_tasting_fixture.py`** (in the "public entrypoints stay stable" section) is unaffected — that script is unrelated to the deleted analytics CLI.
- **Phase 5's analytics work** (Section 2 of Phase 5) is voided. Telemetry no longer exists; if it returns, that's a fresh design.

**Goal:** Convert the `socratink-app` god-files into small, single-responsibility modules with explicit contracts, while preserving single-repo + no-build-step deploy.

**Architecture:** Browser-native ES modules on the frontend; small typed function boundaries on the backend. No new framework, no bundler, no service split. The unit of decomposition is **responsibility + contract**, not technical layer.

**Tech Stack:** Python 3 / FastAPI (backend), vanilla JavaScript (frontend), Supabase (auth), Cytoscape (graph rendering), Vercel (hosting).

---

## Diagnosis

Static graph analysis (2026-04-26 snapshot, commit `e6a220d`):

- **869 nodes / 7,078 edges / 47 source files** across 6 communities (Leiden clustering).
- **Cross-community coupling is already low** — only ~9 production-code edges between communities.
- **One genuine architectural smell**: `main.py → scripts/summarize_ai_runs.py::{build_summary_payload, build_learner_summary_payload}` (production importing from `scripts/`). 4 call sites total — the graph reported 2 because it only saw `build_summary_payload`. Closed in Phase 1 (`75d0c6c`).
- **The real fat is intra-file**, not inter-module:

| File | Lines |
|---|---|
| `public/js/app.js` | 4,059 |
| `public/js/graph-view.js` | 2,709 |
| `ai_service.py` | 1,470 |
| `auth/router.py` | 965 |
| `scripts/summarize_ai_runs.py` | 887 |
| `public/js/learner-analytics.js` | 842 |
| `main.py` | 699 |
| `public/js/browser-analytics.js` | 646 |
| `auth/service.py` | 443 |

**Therefore:** the "lego-ify" instinct is correct, but the scope is **inside the god-files**, not "rearrange the modules." The plan does not introduce packages, services, a frontend framework, or a build system.

---

## Cross-Cutting Rules

These apply to **every phase**. Violating them silently re-creates the god-file problem under prettier filenames.

1. **Extract, preserve behavior, verify** — never change behavior in the same session as moving code. Behavior changes get their own plan.
2. **Split by responsibility, not technical layer.** Forbidden file names: `utils.js`, `helpers.js`, `services.js`, `lib.js`, `common.py`. Required pattern: name the module after what it owns (`api-client.js`, `drill-state.js`, `concept-storage.js`).
3. **Browser-native ES modules only** — no bundler, no transpiler, no React/Vue. If a phase needs a build step, that's a separate decision documented in its own plan.
4. **Public entrypoints stay stable during a phase.** Internal restructuring is invisible to callers. Contract changes happen in a follow-up.
5. **No new `window.*` globals.** Every cross-module dependency is an explicit `import`.
6. **The graph never owns truth.** Cytoscape is a projection layer. UI emits intents (`selectNode`, `startColdAttempt`); never mutates mastery/evidence directly.
7. **Scripts call production. Production never calls scripts.**

---

## Success Metric

Track per session, in the plan's checkpoint section:

```
largest_file_loc + implicit_cross_module_globals + behavior_changing_regressions
```

Targets (over the full roadmap):

| Metric | Baseline (2026-04-26) | Phase 2 target | Phase 3 target | End-state target |
|---|---|---|---|---|
| `app.js` LOC | 4,059 | < 1,500 | < 1,200 | < 800 |
| `graph-view.js` LOC | 2,709 | — | < 1,200 | < 700 |
| `ai_service.py` LOC | 1,470 | — | — | < 800 |
| `auth/router.py` LOC | 965 | — | — | < 500 |
| Production imports from `scripts/` | 4 (graph said 2) | **0** ✅ Phase 1 | 0 | 0 |
| New modules with implicit globals | n/a | 0 | 0 | 0 |
| Behavior-changing regressions per session | n/a | 0 | 0 | 0 |

**The win is not "more files." The win is that a future change to drill state, graph rendering, AI evaluation, auth, or telemetry has one obvious owner and one obvious contract to verify.**

---

## Anti-Patterns to Reject

- ❌ Adding React / Vue / Vite / esbuild "to make files smaller"
- ❌ One file per tiny helper (confetti repo)
- ❌ A `services/` or `helpers/` directory split by technical layer
- ❌ Smuggling state into the graph renderer because it's "convenient"
- ❌ Renaming every analytics event in the same PR as moving the code
- ❌ Speculative plugin-swappability for things that will never be swapped
- ❌ "Cleanup as I go" edits to neighboring files outside the phase scope

The only legitimate replacement boundaries (where swap-ability is real, not theoretical):

1. AI provider client
2. External-source ingestion
3. Persistence (localStorage today, server-side later)
4. Graph renderer (Cytoscape today, could be other)
5. Telemetry transport

Anything else extracted "for swap-ability" is theater.

---

## Phase 1 — Reverse the `scripts/ → production` Smell

**Status:** ✅ Complete (`75d0c6c`). Warm-up lap. See `docs/superpowers/plans/2026-04-26-phase1-extract-run-summary.md` for the executed plan.

**Scope (as executed):**
- Moved both `build_summary_payload` AND `build_learner_summary_payload` (4 call sites in `main.py`, not the 2 the initial graph reported) into `analytics/run_summary.py` (740 LOC).
- Updated `main.py:35-36` to import from `analytics.run_summary`.
- `scripts/summarize_ai_runs.py` is now a 162-line CLI shim (was 882) that imports from `analytics.run_summary`. Includes a 3-line `sys.path` shim so `python scripts/summarize_ai_runs.py` keeps working alongside `python -m scripts.summarize_ai_runs`.
- 8 characterization tests in `tests/test_run_summary.py` strengthened post-Gemini-review (n≥2 fixtures, exact path equality) — they pass against both the old and new module locations, proving behavior preservation.

**Contract:**
- Input: stored run / eval data (already-loaded objects, no filesystem assumptions, no request objects).
- Output: serializable summary payload (the same shape `analytics_ai_runs` returns today).
- No CLI defaults, argparse, or `print()` in the production module.

**Why first:** Establishes the rule "scripts call production, not the reverse" before any large refactor depends on stable import directions. Tiny scope (≈2 calls + 1 function) makes it a safe workflow validation.

**Main risk:** Overshooting into a broad `analytics/` services layer. **Resist.** This is one function moving one directory — not a backend redesign.

**Pre-flight before writing the detailed plan:**
- Read `scripts/summarize_ai_runs.py` end-to-end to identify which functions are production-callable vs CLI-only.
- Read `main.py::analytics_ai_runs` to confirm the exact call surface.

**Detailed plan:** TBW (use `superpowers:writing-plans` when starting).

---

## Phase 2 — Shrink `app.js` to a Shell

**Status:** Blocked on Phase 1 + a 30-min audit (see "Pre-flight").

**Scope:**
Extract from `public/js/app.js` (4,059 LOC) into separate ES modules. **Leaf logic first** — things that can be verified independently:
1. **API client** — every `fetch()` call + error normalization. Module: `public/js/api-client.js`.
2. **Persistence adapter** — every `localStorage` read/write + schema version handling. Module: `public/js/concept-storage.js`.
3. **Drill state reducer** — pure state transitions (no DOM, no network). Module: `public/js/drill-state.js`.
4. **DOM render helpers** — non-graph-specific render utilities. Module: `public/js/dom-render.js` *(naming TBD — must describe what it owns, not "helpers")*.

`app.js` keeps event wiring + SPA coordination until extracted modules are proven.

**Contracts (sketch — finalized in the detailed plan):**
- `apiClient.evaluateAttempt(payload) → Promise<EvalResult>`
- `apiClient.createConcept(payload) → Promise<Concept>`
- `storage.loadConceptState(conceptId) → ConceptState | null`
- `storage.saveConceptState(conceptId, state) → void`
- `drillState.applyEvent(state, event) → newState` (pure function)

**Why second:** Largest file, but riskiest. Frontend behavior depends on subtle script load order. Phase 1 validates the workflow first; this phase needs its own pre-flight audit.

**Main risk:** Implicit globals. `app.js` may rely on globals set by Cytoscape, Supabase client, analytics scripts, or other `<script>` tags. Flipping to `type="module"` without inventorying these is a stealth behavior change.

**Pre-flight before writing the detailed plan:**
- Read every `<script>` tag in the HTML that includes `app.js` or runs before it.
- `grep` for `window.*` reads/writes across `public/js/`.
- Decide: switch `app.js` to `type="module"` (and convert peers), or use named ES modules called from a non-module `app.js` shim. The choice changes the plan structure.

### Pre-flight audit results (2026-04-26)

**Surprise: `app.js` is already an ES module.** `public/index.html:547` loads it as `<script type="module" src="js/app.js?v=41"></script>`, and the file's first three lines are real `import` statements pulling from `bus.js`, `graph-view.js?v=7`, and `auth.js?v=2`. The roadmap's framing of "decide ESM strategy" was based on a false premise — the strategy is already in place.

The real Phase 2 problem is **finishing what's already started**:

#### Module-status inventory (`public/js/`)

| File | Loaded as | Exports | Imports | Notes |
|---|---|---|---|---|
| `app.js` | `type="module"` | 0 | 8 | SPA shell; already ESM |
| `auth.js` | (via app.js) | 6 | 0 | Pure ESM |
| `bus.js` | (via app.js) | 1 | 0 | Pure ESM |
| `dom.js` | (via app.js) | 22 | 0 | Pure ESM (cached DOM lookups) |
| `graph-view.js` | (via app.js) | 3 | 0 | Pure ESM |
| `store.js` | (via app.js) | 11 | 0 | Pure ESM |
| `welcome.js` | (via app.js) | 1 | 0 | Pure ESM |
| `tooltips.js` | `type="module"` | 1 | 1 | Pure ESM |
| `login.js` | `type="module"` | 0 | 0 | Module shell, no contracts |
| `learner-analytics.js` | (via dashboard) | 1 | 3 | Pure ESM |
| `browser-analytics.js` | ? | 6 | 0 | Pure ESM |
| `ai-runs-dashboard.js` | ? | 0 | 1 | Pure ESM |
| **`ai_service.js`** | **classic `<script>`** | **0** | **0** | **Sets `window.AIService` — implicit-global smell** |
| **`intro-particles.js`** | **classic `<script>`** | **0** | **0** | **Visual effect; may set globals** |

#### Custom `window.*` globals (the real implicit dependency surface)

`app.js` reads:
- `window.AIService.generateKnowledgeMap(...)` at line 1510 — **the only real implicit-global dependency.** Set by the classic-script `ai_service.js`.
- `window.testGraph(name)` at line 912 — debug helper.
- `window.__creationDialogTrigger` at lines 1088, 1176 — used as cross-render state stash. Could be a module-scope variable in `app.js` itself; a window global here is a code smell, not a dependency.

`app.js` sets:
- `window.App = App` (line 4056)
- `window.SocratinkApp = App` (line 4057)
- `window.startSettings = () => App.showSettings()` (line 4058)

**Why these globals exist:** `public/index.html` uses `<a onclick="App.showDashboard()">` style inline handlers throughout the bottom-nav and (likely) elsewhere. Those inline handlers can only see `window.*` — they cannot import. **This is the real coupling that holds the global exports in place.** A pure ESM app.js would break every inline `onclick`.

#### HTML inline scripts (in `public/index.html`)

- Lines 30-39: theme preload (`localStorage.getItem('learnops-theme')` → set `dataset.theme`). Tiny, runs before module loads to avoid flash. Defensible.
- Lines 552-554: Vercel Speed Insights stub. Standard third-party shim.

Neither is a Phase 2 concern.

#### Cache-busting

Imports use ad-hoc `?v=N` query strings (`graph-view.js?v=7`, `auth.js?v=2`, `app.js?v=41`, etc.). Manual versioning per file. Easy to forget. Worth standardizing during Phase 2 (e.g., one global build-id) but not blocking.

### Decision: ESM strategy for Phase 2

**ESM is already chosen.** Phase 2 should focus on:

1. **Convert `ai_service.js` from classic script to ES module.** Replace `window.AIService.generateKnowledgeMap` reads in `app.js` (and any other readers) with explicit `import`. **One real implicit-global dependency removed.** This is the highest-leverage move — likely doable in one session.
2. **Decide what to do about `App` window globals + inline `onclick=`.** Two paths:
   - **(a)** Keep `window.App` deliberately as the documented "HTML→JS bridge" with a 1-line shim `app.js` exports. Accept that inline `onclick` is the simpler pattern for this app. Document it as the only legitimate use of a custom window global.
   - **(b)** Sweep through the HTML and replace every inline `onclick="App.foo()"` with `addEventListener` wired from app.js after load. Cleaner but multi-session work touching every nav button, drawer, modal trigger, etc.
   - **Recommendation:** (a) for this phase — preserve the `App` bridge intentionally, drop the redundant `SocratinkApp` and `startSettings` globals if they're not referenced from HTML (verify with grep). (b) is a Phase 3 candidate or its own micro-phase.
3. **Continue intra-`app.js` decomposition** — `app.js` is 4,059 LOC even though it's already a module. Extract leaf responsibilities (api client, persistence, drill state reducer) per the original roadmap. Same pattern just used for `analytics/run_summary.py`: extract leaf module → import → run smoke → commit.
4. **Convert `intro-particles.js` to `type="module"` (or leave alone).** It's a one-shot visual effect; if it doesn't set globals or have peers, no benefit to converting. Verify with grep, then decide.

**Phase 2 ordering (revised):**
- 2.1 — ✅ Complete (`68383b1`). Converted `ai_service.js` to ESM; dropped `window.AIService` global; replaced the single call site in `app.js`. Bumped `app.js` cache version 41 → 42.
- 2.2 — ✅ Complete (`c7858d3`). Dropped unused `window.startSettings`. **Audit was wrong about `SocratinkApp`** — Gemini-verified that `graph-view.js` reads it 17 times via optional chaining; it's the de facto renderer→app intent bridge that Phase 3 formalizes. Both surviving globals (`App`, `SocratinkApp`) now have a documented contract above the assignment with the silent-failure risk called out explicitly. Bumped `app.js` cache version 42 → 43.
- 2.3 — Begin intra-`app.js` extracts: API client first (cleanest leaf), then persistence, then drill state reducer.
  - 2.3.1 — ✅ Complete (`dec1509`). Extracted `public/js/api-client.js` (70 LOC) with 5 exports for the socratink backend (`/api/health`, `/api/extract-url`, `/api/repair-reps`, `/api/drill`, `/data/library/${filename}`). Replaced 6 inline `fetch()` call sites in `app.js`. Module is pure — no localStorage/cookie reads. Wikipedia fetches stay inline as a separate micro-phase. Gemini caught a `payload`-vs-`data` variable-name bug in the proposal before execute. `app.js`: 4,063 → 4,054 LOC. Bumped app.js cache version 43 → 44.
  - 2.3.2 — Persistence (localStorage reads/writes — `concept-storage.js`).
  - 2.3.3 — Drill state reducer (pure state transitions — `drill-state.js`).
- 2.4 — DOM/render helpers extract.
- (Defer: HTML inline-handler cleanup — own micro-phase if pursued.)

### Audit metrics snapshot (2026-04-26)

| Metric | Value | Note |
|---|---|---|
| `public/js/app.js` LOC | 4,059 | Phase 2 baseline |
| `app.js` already ES module | yes | reframes scope |
| Classic-script `.js` files | 2 (`ai_service.js`, `intro-particles.js`) | conversion candidates |
| Custom `window.*` globals SET by app.js | 3 (`App`, `SocratinkApp`, `startSettings`) | coupling to inline `onclick=` |
| Custom `window.*` globals READ by app.js | 1 production (`AIService`) + 2 internal-state stashes (`testGraph`, `__creationDialogTrigger`) | only `AIService` is a real cross-file dependency |
| HTML files loading `app.js` | 1 (`public/index.html`) | single load site simplifies coordination |

**Detailed plan:** TBW (when starting Phase 2 — write a per-step bite-sized plan covering at minimum task 2.1).

---

## Phase 3 — Graph Contract: Renderer ≠ Source of Truth

**Status:** Blocked on Phase 2 (needs `drill-state.js` + `concept-storage.js` to exist as authority).

**Scope:**
Split `public/js/graph-view.js` (2,709 LOC) into:
1. **Graph data normalization** — concept-graph data → Cytoscape-shaped nodes/edges
2. **State projection** — persisted drill states → visual state (color, halo, badge)
3. **Cytoscape rendering adapter** — initialization + style application
4. **Layout / config** — algorithm choice, spacing, animation
5. **Interaction handlers** — click/hover → emit intents (no state mutations)
6. **Drill-state visual mapping** — pure function: `(drillStates) → cyStyleOverrides`

**Contract (the load-bearing one for the whole roadmap):**
```
Inputs to graph module:
  - canonical concept.graphData
  - active node id
  - persisted drill states (read-only)

Outputs from graph module (intents only):
  - selectNode(nodeId)
  - startColdAttempt(nodeId)
  - requestStudy(nodeId)

Imperative adapter exposed to caller:
  - renderGraph(state)
  - highlightNode(nodeId)
  - destroy()

INVARIANT: graph module NEVER mutates mastery, evidence, or persisted concept state.
           All mutations happen in the caller, in response to intents.
```

**Why third:** This contract is the most product-doctrine-load-bearing piece in the roadmap. Done correctly, it locks in "Cytoscape is a projection, not the system of record" for all future graph work. Done incorrectly, it makes the file structure prettier while making truth violations easier.

**Main risk:** Convenience drift. When the renderer needs derived state (e.g. "is this node currently highlighted?"), the temptation is to store it on the Cytoscape node. **Reject.** Derived state lives in the projection function, not the renderer.

**Pre-flight before writing the detailed plan:**
- Inventory every place in `graph-view.js` that writes to anything outside Cytoscape (localStorage, server, `window.*`, app state). Each one is a call site that becomes an intent.
- Whiteboard the intent list with the user (use `whiteboarding` skill) before writing the plan.

**Detailed plan:** TBW.

---

## Phase 4 — Split `ai_service.py` by Failure Domain

**Status:** Blocked on Phases 1–3 (frontend contracts must be stable so backend changes don't ripple visibly).

**Scope:**
Decompose `ai_service.py` (1,470 LOC) along **operational boundaries**, not abstract nouns. Proposed modules:
1. `ai/provider_client.py` — model-call wrapper (timeouts, retries, error normalization)
2. `ai/prompts.py` — prompt builders + rubrics (pure data + format strings)
3. `ai/extraction.py` — knowledge-map extraction orchestration
4. `ai/drill_evaluation.py` — drill attempt routing + evaluation orchestration
5. `ai/output_parser.py` — structured-output parsing + validation (Pydantic models)
6. `ai/source_ingestion.py` — external transcript / source fetching with fallback handling

**Contract:**
- Public entrypoints (`extract_knowledge_map`, `evaluate_attempt`, etc.) keep their current signatures — `main.py` and `scripts/run_tasting_fixture.py` are not touched in this phase.
- Behind the entrypoints, internal calls use typed request/result objects with **explicit failure modes**:
  - `extract_knowledge_map(...) → ExtractionResult{success | partial | fallback | error}`
  - `evaluate_attempt(...) → EvaluationResult{ok | rubric_failed | provider_error}`
  - `fetch_source(...) → SourceResult{ok | blocked | needs_manual_fallback | safe_user_facing_error}`

**Why fourth:** AI behavior is the highest-operational-risk surface. Refactoring it requires the rest of the app to be stable so regressions are isolable. Also: prompt/parser bugs are hard to detect without fixtures, so this phase needs investment in deterministic test cases first.

**Main risks:**
- **Prompt regressions** — moving a prompt builder can subtly change whitespace and break model output. Snapshot-test all prompts before moving them.
- **Parser regressions** — same for output parsing. Pin known-good model responses as fixtures.
- **SSRF on `fetch_source`** — current behavior must be preserved exactly (allowlist, timeout, response size cap).
- **Internal error leakage** — moving error-handling code can change which errors reach the user. Audit every `except Exception` for what it returns.

**Pre-flight before writing the detailed plan:**
- Run every public entrypoint against a small fixture set, snapshot the output. These become the regression suite.
- Read the existing SSRF + retry handling end-to-end.

**Detailed plan:** TBW.

---

## Phase 5 — Auth Routes, Analytics Schemas, Runtime Config

**Status:** Blocked on Phases 1–4. Lowest priority but real value once core surfaces are clean.

**Scope:**
1. **`auth/router.py`** (965 LOC): keep route handlers thin (HTTP → service call → response). Move every business decision into `auth/service.py`. Routes should not touch session structures, cookie policies, or redirect URL composition — those become service methods.
2. **Analytics JS** (`browser-analytics.js` 646 LOC + `learner-analytics.js` 842 LOC): define **one telemetry event contract** with stable schemas. Separate three concerns: (a) collection (where events originate), (b) enrichment (adding context: user, session, build), (c) transport (where events go). Today these are tangled.
3. **Runtime config**: centralize environment-derived behavior (Vercel vs local) so feature differences are explicit, not scattered through `if os.getenv(...)`.

**Contracts:**
- Auth routes: `(Request, params) → service.method(...) → Response`. No business logic in the route body.
- Analytics: `emit(eventName, payload)` where `eventName` is from a stable enum and `payload` matches a schema (Zod-style at runtime, doc'd at design time).
- Runtime config: a single `runtime_config` object queried via named methods (`config.is_vercel()`, `config.session_cookie_secure()`, etc.) — never raw `os.getenv` in business code.

**Why last:** Auth and analytics are important but not the modularity bottleneck. Auth is already the most cohesive production cluster (cohesion 0.24, highest of any prod community) — it's pulling its weight. Telemetry churn is risky (breaks log queries / dashboards) and has low payoff until the stuff it instruments is cleaner.

**Main risks:**
- **Auth regressions** — auth has the highest blast radius. Every move needs a test exercising the affected flow.
- **Analytics rename churn** — if event names change, existing log queries / dashboards / alerts break silently. Either keep names stable, or ship a documented rename + grace period.

**Pre-flight before writing the detailed plan:**
- Inventory all `auth/router.py` business logic that needs to move.
- Inventory all analytics event names currently emitted; decide which (if any) need renaming and document the rationale.
- Find every `os.getenv(...)` outside `auth/service.py::build_auth_service_from_env`.

**Detailed plan:** TBW.

---

## Execution Order — Hard Constraint

Phases must execute **in order**:

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
```

Each phase establishes a contract or rule that later phases assume:
- Phase 1 establishes "scripts call production" rule → Phases 4 + 5 depend on it.
- Phase 2 establishes ESM + leaf-module pattern → Phase 3 plugs into the pattern.
- Phase 3 establishes "graph projects truth" → Phase 4 backend changes don't have to second-guess frontend ownership.
- Phase 4 stabilizes AI contracts → Phase 5 telemetry can instrument them with confidence.

**Out-of-order execution destroys the leverage.**

---

## Per-Phase Deliverables Checklist

When picking up any phase, the detailed plan must include:

- [ ] Pre-flight audit results (the items listed in each phase's "Pre-flight" section)
- [ ] Concrete file structure (exact paths for every new/modified file)
- [ ] Bite-sized TDD tasks (one action each, ~2-5 minutes — see `superpowers:writing-plans`)
- [ ] Test strategy for the phase (manual MVP happy-path always; automated where the surface permits)
- [ ] Rollback plan if the phase is half-done at session end
- [ ] Post-phase metric snapshot (LOC counts, global counts) — appended to this roadmap

---

## Roadmap Maintenance

After each phase completes, update **this file**:

1. Mark the phase status `Complete` with the commit SHA.
2. Append the post-phase metric snapshot to the success-metric table.
3. Note any contract changes the phase actually shipped (vs what was planned).
4. Update later phases if their preconditions changed.

---

## Source

- Codex consultation 2026-04-26 (saved at `/tmp/codex-lego-plan.md`).
- Architecture snapshot from code-review-graph at commit `e6a220d` (2026-04-25 23:48 build).
- Cross-community edge analysis from `mcp__code-review-graph__get_architecture_overview_tool`.
