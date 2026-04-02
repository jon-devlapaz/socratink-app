# Structure Stabilization Plan

Purpose: turn the current codebase evaluation into a concrete execution plan for MVP stabilization.

Read this when:

- deciding what to refactor next
- planning drill/graph state ownership changes
- reducing deployment risk without reopening product scope
- routing work between `elliot`, `sherlock`, `rob`, and `thurman`

Read these first if you need deeper context:

- [state.md](state.md)
- [ux-framework.md](../product/ux-framework.md)
- [progressive-disclosure.md](../product/progressive-disclosure.md)
- [graph-invariants.md](../drill/graph-invariants.md)

This document is an implementation plan, not an enduring philosophy doc.

It should stay aligned with current MVP constraints:

- Vercel serverless is the hosted runtime
- the graph must tell the truth
- generation before recognition is non-negotiable
- local success does not validate hosted behavior

## Current Structural Read

Confirmed:

- runtime shape is simple and legible: Vercel entrypoint -> FastAPI app -> static browser client
- backend split is acceptable for MVP: API/ingestion in `main.py`, model-facing logic in `ai_service.py`
- frontend split is weaker: `public/js/app.js` is carrying too much orchestration and product logic
- graph rendering and progression logic are not cleanly separated; `public/js/graph-view.js` still owns meaningful state interpretation
- learner progress truth is primarily browser-owned today through `localStorage` and client-side graph patching
- external fetches, YouTube transcript retrieval, and model calls remain inline on user request paths

## Key Structural Risks

### 1. Product Truth Is Not Cleanly Owned

The repo's product rules say the graph should represent verified understanding.

Today, that truth is too easy to mutate from the browser layer.

Risk:

- attempted state can drift from persisted epistemic state
- future multi-session or multi-device behavior will be structurally weak
- graph projection logic can accidentally become the source of truth

### 2. Frontend Product Logic Is Too Centralized

`public/js/app.js` is the practical coordinator for:

- ingestion flow
- concept lifecycle
- drill UI flow
- persistence glue
- graph refresh behavior

Risk:

- feature work will keep landing in one file
- regression review becomes expensive
- drill and graph invariants will be easier to violate accidentally

### 3. Server-Side Drill Integrity Is Incomplete

The backend still accepts answer-key-like mechanism data from the client.

Risk:

- drill integrity is weaker than the UX philosophy implies
- browser state remains too privileged in a system that claims truthful verification

### 4. Hosted Risk Is Still Embedded In Request Paths

The current MVP already handles some hosted failures well, especially YouTube fallback and SSRF blocking.

Risk:

- more ingestion/provider edge cases will accumulate inside `main.py`
- local debugging can mask hosted fragility

### 5. Repo Identity Is Slightly Mixed

This repo contains both:

- a deployable hosted app
- a reusable LearnOps skill corpus under `learnops/`

Risk:

- future sessions may not know whether they are editing product runtime, skill assets, or both

## Immediate Assumptions To Resolve

The biggest unresolved product/architecture assumption is this:

Is MVP truth still "single-browser prototype truth" or has the project crossed into "account-backed product truth"?

If the answer is:

- single-browser prototype truth: `localStorage` can remain temporarily acceptable, but only if the graph is still derived from persisted `graphData` and in-progress session state is treated as disposable
- account-backed product truth: client-owned persistence is no longer an acceptable primary boundary

Do not let this remain implicit.

## Now

These are the highest-leverage moves for the next implementation slice.

### 1. Extract A Frontend Product-State Layer

Goal:

- make graph state a projection, not a decision engine

Do:

- move drill session state, active target state, and graph patching rules out of `public/js/app.js`
- keep `public/js/graph-view.js` focused on deriving and rendering graph projection from persisted knowledge-map data
- centralize node patching by `node_id`
- make cluster state purely derived

Must preserve:

- one active cognitive target
- no silent node switching
- no unlocks from non-solid outcomes

Recommended agent flow:

1. `elliot` defines the intended module boundaries and ownership
2. `sherlock` traces current state mutation paths in frontend
3. `rob` extracts the modules without changing product behavior
4. `thurman` validates graph/drill lockstep after refactor

### 2. Make The Server Resolve Drill Evaluation Inputs

Goal:

- remove browser ownership over evaluation-critical mechanism data

Do:

- resolve the drill target from `knowledge_map` plus `node_id` on the server
- stop treating client-sent `node_mechanism` as authoritative
- keep patching rules aligned with [graph-invariants.md](../drill/graph-invariants.md)

Must preserve:

- backend and frontend refer to the same active node
- only the active node is patched on completion
- `routing` and mastery remain separate concepts

Recommended agent flow:

1. `elliot` confirms the contract change
2. `sherlock` verifies all current drill target paths
3. `rob` implements the server-owned resolution
4. `thurman` tests local and hosted behavior separately

### 3. Split Ingestion Adapters Out Of `main.py`

Goal:

- keep hosted edge-case handling narrow and testable

Do:

- extract URL fetch, YouTube transcript fetch, and provider-specific error mapping into dedicated adapter helpers
- preserve existing SSRF blocking and manual transcript fallback behavior
- keep API handlers thin

Must preserve:

- no internal error leakage
- no relaxation of private-address blocking
- clear user-facing fallback messaging when hosted providers fail

Recommended agent flow:

1. `sherlock` identifies current hosted failure surfaces
2. `rob` extracts adapters with behavior parity
3. `thurman` reviews fallback-path integrity

## Next

These are the next high-value decisions once the current truth boundary is cleaner.

### 4. Decide And Document The Persistence Boundary

Choose explicitly between:

- temporary browser-only persistence for MVP
- real server-backed concept and drill persistence

If browser-only remains the choice:

- document it as intentional temporary debt
- constrain new features so they do not assume multi-device truth

If server-backed truth becomes the choice:

- define the minimum persistence model first
- store concept graph truth and drill outcomes server-side before adding broader feature scope

Owner:

- `elliot` for decision framing
- `rob` for implementation once decided
- `thurman` for release-risk review

### 5. Clarify Repo Boundaries In Docs

Goal:

- make future sessions immediately understand what lives where

Do:

- document the boundary between hosted app code and `learnops/` skill assets
- keep runtime docs under `docs/project/` and product/drill rules in their current homes
- avoid expanding `AGENTS.md` into a large architecture dump

Owner:

- `elliot` for framing
- `rob` for docs updates

## Later

These moves matter, but they should follow the state-ownership cleanup.

### 6. Reduce Inline Request Dependency On Slow External Work

Possible directions:

- background extraction jobs
- retriable queued work
- more explicit timeout/failure surfaces in the UI

This is valuable because Vercel serverless plus third-party providers creates failure modes that do not show up in local happy paths.

### 7. Add Narrow Validation Around Structural Invariants

Focus on:

- patch-by-`node_id`
- single active drill target
- cluster derivation from persisted subnode truth
- no false unlock on non-solid `NEXT`

This should be lightweight and targeted.
Do not balloon the MVP into a broad test harness before the state boundary is cleaner.

### 8. Add An MVP Settings Surface

Goal:

- give testers and early users more control, trust, and recovery without weakening product truth

Settings TODO:

- add API key and provider status so users can see whether model access is configured and healthy
- add provider or model selection only if multiple hosted paths are genuinely supported
- add a fallback preference for failed ingestion, especially a clear manual transcript-paste path for YouTube failures
- add session length options such as short, standard, and deep
- add drill intensity or tone options such as gentle, standard, and rigorous without changing mastery truth
- add a reveal preference for post-attempt help, such as brief hint first versus fuller explanation after a genuine attempt
- add graph display controls such as minimal, detailed, or labels-on-hover
- add a focus mode toggle for reducing graph noise while drilling one target
- add a reset local session state action for recovering from browser-memory issues
- add export concept data so testers can keep a local backup of their work
- add import or restore local backup only if the export shape is stable enough to be safe
- add clear cached concepts or local data recovery actions
- add a debug info toggle for testers to inspect request status, recent sync events, or safe error context
- add a beta-features toggle only for genuinely optional, unstable flows
- add a feedback or report-issue path that captures enough context to be actionable

Settings To Avoid For Now:

- mastery threshold sliders
- settings that make drills easier in ways that fake progression
- theme customization that does not improve trust or usability
- notification systems that imply durable account-backed state before persistence is real
- settings that blur the line between attempted, drilled, and solidified

Must preserve:

- generation before recognition
- the graph tells the truth
- local settings do not imply multi-device persistence if the app is still browser-first
- hosted failure paths stay explicit and recoverable

## Recommended Execution Sequence

If the goal is "highest value with lowest architectural thrash," do the work in this order:

1. frontend product-state extraction
2. server-owned drill input resolution
3. ingestion adapter extraction
4. persistence-boundary decision
5. repo/docs clarification

## What Not To Do

Do not:

- move to a large framework rewrite to solve a boundary problem
- add decorative graph reward systems before truth ownership is cleaner
- treat Cytoscape classes as learner state
- expand product scope before the persistence boundary is explicit
- assume local ingestion behavior predicts hosted behavior

## Decision Trigger

Before the next major drill or graph feature, answer this in writing:

"What is the source of truth for learner understanding in this MVP, and which layer is allowed to mutate it?"

If that answer is still ambiguous, the next feature slice should be planning and boundary cleanup, not net-new behavior.
