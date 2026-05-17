# Project State

## Snapshot
- Product: socratink
- Stage: Build-Measure-Learn
- Core architecture: cold attempt -> targeted study -> spaced re-drill
- Core derived training states: `null | primed | needs repair | solidified`
- Agent architecture: `socratinker` is the default execution agent; Socratink Brain (`.socratink-brain/`, `$socratink-brain`) is the durable product-memory substrate and maintenance skill
- Hosted runtime: Vercel serverless
- Current persistence: browser `localStorage`; concepts live in `learnops_concepts`, training evidence lives under `socratink:training:v1:<conceptId>`
- Evidence source of truth: live logs plus the operational docs in this repo

## Current Phase
The original thermostat starter-map MVP loop shipped. Per [ADR-0004](../adr/0004-library-is-users-work-only.md), Library now shows only the user's own reconstructed work — both the multi-concept starter shelf and the curated Hermes Agent fixture have been removed. Current smoke tests seed a concept directly into `learnops_concepts` localStorage. The product is now in Build-Measure-Learn: build features, measure with instrumentation and Socratink Brain, learn from compiled evidence.

## Active Risks
- Hosted behavior may still diverge from local behavior.
- `localStorage` is fragile and easy to wipe.
- Chat/test instrumentation is incomplete, so some regressions will still be harder to reconstruct than they should be.
- External ingestion paths still need defensive hosted behavior and graceful fallback.
- Library shows only the user's own reconstructed work (ADR-0004); there are no checked-in Library fixtures. A first-run user with no concepts must bring their own source.

## Product Constraints
- Generation Before Recognition is non-negotiable.
- The graph is an evidence-weighted map. It shows what Socratink has evidence for, not what the learner knows.
- The map starts as a hypothesis; the starting map is an anchor, not a diagnostic.
- Cold attempts are learner-facing unscored; private classification may drive repair/study routing.
- `solidified` can only result from spaced strong reconstruction evidence. Study and Repair Reps must not produce `solidified`.
- Clusters are containers in MVP, not primary drill targets.
- Drill-session caps remain backend/doctrinal guardrails, but the current frontend MVP bypasses duration, node-count, and per-node retrieval enforcement while inline reconstruction is validated.

## Current Priorities
- keep graph state and persisted state aligned
- improve instrumentation
- validate hosted behavior before treating local success as done

## Use These Docs
- [docs/product/evidence-weighted-map.md](../product/evidence-weighted-map.md): binding doctrine for what the graph may/must not claim
- [docs/product/spec.md](../product/spec.md): binding product contract
- [docs/superpowers/specs/2026-05-15-drill-data-model-design.md](../superpowers/specs/2026-05-15-drill-data-model-design.md): current binding drill data-model canon
- [docs/drill/contract.md](../drill/contract.md): compatibility redirect and runtime summary
- [docs/project/doc-map.md](doc-map.md): curated index of canonical entry points and deep-dives, with precedence rules at the top
- [docs/project/mvp-happy-path.md](mvp-happy-path.md): current manual release gate
- [docs/project/operations.md](operations.md): merge and stabilization criteria
- `logs/drill-runs.jsonl` and screenshots: current release evidence and gaps

## Environment Lessons
- Local success is not deployment validation.
- Vercel serverless file writes are not durable release evidence; export Socratink Brain-marked runtime logs or use a durable store for hosted drill telemetry.
- Hosted YouTube transcript retrieval can fail because cloud/serverless IPs are blocked.
- Manual transcript paste remains the hosted fallback.
- External calls must be reviewed for SSRF risk and error leakage.
