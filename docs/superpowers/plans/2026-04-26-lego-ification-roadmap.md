# Lego-ification Roadmap

> **Note for agentic workers:** This is a **strategic roadmap**, not a directly-executable bite-sized plan. Each phase gets its own detailed implementation plan written when picked up (use `superpowers:writing-plans`). Phases must be executed in order — Phase 1 → Phase 5 — because later phases depend on contracts established earlier.

**Goal:** Convert the `socratink-app` god-files into small, single-responsibility modules with explicit contracts, while preserving single-repo + no-build-step deploy.

**Architecture:** Browser-native ES modules on the frontend; small typed function boundaries on the backend. No new framework, no bundler, no service split. The unit of decomposition is **responsibility + contract**, not technical layer.

**Tech Stack:** Python 3 / FastAPI (backend), vanilla JavaScript (frontend), Supabase (auth), Cytoscape (graph rendering), Vercel (hosting).

---

## Diagnosis

Static graph analysis (2026-04-26 snapshot, commit `e6a220d`):

- **869 nodes / 7,078 edges / 47 source files** across 6 communities (Leiden clustering).
- **Cross-community coupling is already low** — only ~9 production-code edges between communities.
- **One genuine architectural smell**: `main.py → scripts/summarize_ai_runs.py::build_summary_payload` (production importing from `scripts/`). 2 calls.
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
| Production imports from `scripts/` | 2 | 0 | 0 | 0 |
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

**Status:** Ready to execute. Smallest phase; warm-up lap.

**Scope:**
- Move `scripts/summarize_ai_runs.py::build_summary_payload` (and any data-shape helpers it depends on) into a production-owned module — proposed `analytics/run_summary.py`.
- Update `main.py::analytics_ai_runs` to import from the new location.
- Leave `scripts/summarize_ai_runs.py` as a thin CLI wrapper that imports from production.
- Update tests if any reference the old path.

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

**Detailed plan:** TBW.

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
