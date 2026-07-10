# Project State

## Snapshot
- Product: socratink
- Stage: Build-Measure-Learn
- Core architecture: cold attempt -> targeted study -> spaced re-drill
- Core derived training states: `null | primed | needs repair | solidified`
- Agent architecture: `socratinker` is the default execution agent; Socratink Brain (`.socratink-brain/`, `$socratink-brain`) is the durable product-memory substrate and maintenance skill
- Hosted runtime: Vercel serverless
- Current persistence: concepts and app-shell training evidence are browser
  `localStorage` (`learnops_concepts`, `socratink:training:v1:<conceptId>`).
  The browser keeps the app-local SEDA resume pointer in `localStorage`
  (`socratink:seda-session:v1:<conceptId>`). Locally, the loop runtime writes
  journals to `SOCRATINK_LOOP_SESSION_STORE_DIR` or the OS temporary default.
  On Vercel, FastAPI sends session calls to the configured HTTPS loop service;
  its journals use the RLS-scoped Supabase `loop_sessions` table after
  `db/loop_sessions.sql` is applied. Production does not fall back to `/tmp`.
  This is durable session history, not complete cross-device learner state.
- Evidence source of truth: live logs plus the operational docs in this repo

## Current Phase
The original thermostat starter-map MVP loop shipped. Per [ADR-0004](../adr/0004-library-is-users-work-only.md), Library now shows only the user's own reconstructed work; both the multi-concept starter shelf and the curated Hermes Agent fixture have been removed. Current smoke tests seed a concept directly into `learnops_concepts` localStorage. The product is now in Build-Measure-Learn: build features, measure with instrumentation and Socratink Brain, learn from compiled evidence.

## Active Risks
- Hosted behavior may still diverge from local behavior.
- Browser concepts, training evidence, and SEDA resume pointers remain easy to
  wipe and do not yet provide full cross-browser continuity. Hosted session
  journals also remain unavailable until `db/loop_sessions.sql` is applied and
  the trusted loop service is deployed and configured.
- Chat/test instrumentation is incomplete, so some regressions will still be harder to reconstruct than they should be.
- External ingestion paths still need defensive hosted behavior and graceful fallback.
- Library shows only the user's own reconstructed work (ADR-0004); there are no checked-in Library fixtures. A first-run user may start source-less through Door -> Launch pad -> non-empty Launch attempt -> Smallest actionable route.
- `ai_service.py` still imports Gemini directly for `drill_chat` and `generate_repair_reps`; ADR-0002's temporary LLM seam exception remains unresolved until those paths migrate through `llm/`.
- The app-local SEDA runtime now lives in root-level `lib/seda/`,
  `lib/loop-server/`, `bridge.py`, `bridge_lib/`, `vendor/python/`,
  `learning_cases/`, and `pedagogical_agents/`. Treat `scripts/socratink_tui/`
  as legacy CLI surface unless a task explicitly targets it.

## Product Constraints
- Generation Before Recognition is non-negotiable.
- The graph is an evidence-weighted map. It shows what Socratink has evidence for, not what the learner knows.
- The map starts as a hypothesis; the starting map is an anchor, not a diagnostic.
- Cold attempts are learner-facing unscored; private classification may drive repair/study routing.
- `solidified` can only result from spaced strong reconstruction evidence. Study, Repair Reps, and Gap drills must not produce `solidified`.
- Clusters are containers in MVP, not primary drill targets.
- Drill-session caps remain backend/doctrinal guardrails, but the current frontend MVP bypasses duration, node-count, and per-node retrieval enforcement while inline reconstruction is validated.

## Current Priorities
- keep graph state and persisted state aligned
- improve instrumentation
- validate hosted behavior before treating local success as done

## Use These Docs
- [docs/product/evidence-weighted-map.md](../product/evidence-weighted-map.md): binding doctrine for what the graph may/must not claim
- [docs/product/spec.md](../product/spec.md): binding product contract for the three-phase loop, routing, progression layers, inline concept-entry/result-surface modes, and guardrails
- [docs/superpowers/specs/2026-05-15-drill-data-model-design.md](../superpowers/specs/2026-05-15-drill-data-model-design.md): binding drill data-model canon for training evidence, derivation math, and rendering fields
- [docs/project/doc-map.md](doc-map.md): curated index of canonical entry points and deep-dives, with precedence rules at the top
- `logs/drill-runs.jsonl` and screenshots: current release evidence and gaps

## Environment Lessons
- Local success is not deployment validation.
- Vercel session durability depends on the RLS-scoped Supabase store and its
  deployment-time schema/config proof; local file-store success is not enough.
- Hosted YouTube transcript retrieval can fail because cloud/serverless IPs are blocked.
- Manual transcript paste remains the hosted fallback.
- External calls must be reviewed for SSRF risk and error leakage.
