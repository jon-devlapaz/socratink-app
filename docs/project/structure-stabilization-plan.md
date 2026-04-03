# Structure Stabilization Plan

Purpose: keep MVP stabilization focused on the smallest structural changes that improve product truth and deployment safety.

Read this when:

- planning architectural cleanup
- deciding what refactor is worth doing next
- reducing hosted risk without reopening product scope

Read these first if you need deeper context:

- [state.md](state.md)
- [ux-framework.md](../product/ux-framework.md)
- [graph-invariants.md](../drill/graph-invariants.md)

## Current Truth

- Hosted runtime is Vercel serverless.
- The graph must tell the truth.
- Generation before recognition is non-negotiable.
- Runtime shape is still simple enough for MVP: Vercel entrypoint -> FastAPI app -> static browser client.
- Frontend product logic remains too centralized in `public/js/app.js`.
- Server-side drill integrity still needs stronger ownership over evaluation-critical inputs.
- Hosted ingestion failure handling must stay narrow, explicit, and safe.

## Current Next Actions

### 1. Extract a frontend product-state layer

- Move drill session state, active target state, and graph patching rules out of `public/js/app.js`.
- Keep `public/js/graph-view.js` focused on rendering and derivation, not product truth.
- Preserve one active cognitive target, no silent node switching, and no unlocks from non-solid outcomes.

### 2. Make the server resolve drill evaluation inputs

- Resolve drill targets from `knowledge_map` plus `node_id` on the server.
- Stop treating client-sent mechanism text as authoritative.
- Keep backend patch rules aligned with [graph-invariants.md](../drill/graph-invariants.md).

### 3. Extract ingestion adapters out of `main.py`

- Isolate URL fetch, YouTube transcript fetch, and provider-specific error mapping into helpers.
- Preserve existing SSRF blocking and manual transcript fallback behavior.
- Keep API handlers thin and user-facing failure messages explicit.

## Unresolved Architecture Decision

- Decide whether MVP truth is still temporary browser-only persistence or whether the project has crossed into server-backed persistence.
- Do not let that boundary remain implicit; new features should not assume multi-device truth until the decision is made.

## What Not To Do

- Do not start a framework rewrite to solve a boundary problem.
- Do not add reward systems that blur attempted, drilled, and solidified states.
- Do not expand product scope before the persistence boundary is explicit.
- Do not assume local ingestion behavior predicts hosted behavior.
