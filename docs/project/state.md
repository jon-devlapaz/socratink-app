# Project State

## Snapshot
- Product: socratink
- Stage: Build-Measure-Learn
- Core architecture: cold attempt -> targeted study -> spaced re-drill
- Core node states: `locked -> primed -> drilled -> solidified`
- Agent architecture: `socratinker` is the default execution agent; Socratink Brain (`.socratink-brain/`, `$socratink-brain`) is the durable product-memory substrate and maintenance skill
- Hosted runtime: Vercel serverless
- Current persistence: browser `localStorage`
- Evidence source of truth: live logs plus the operational docs in this repo

## Current Phase
The thermostat starter-map MVP loop shipped. The product is now in Build-Measure-Learn: build features, measure with instrumentation and Socratink Brain, learn from compiled evidence.

## Active Risks
- Hosted behavior may still diverge from local behavior.
- `localStorage` is fragile and easy to wipe.
- Chat/test instrumentation is incomplete, so some regressions will still be harder to reconstruct than they should be.
- External ingestion paths still need defensive hosted behavior and graceful fallback.

## Product Constraints
- Generation Before Recognition is non-negotiable.
- The graph must tell the truth.
- Cold attempts are unscored.
- `solidified` can only result from spaced re-drill.
- Clusters are containers in MVP, not primary drill targets.

## Current Priorities
- keep graph state and persisted state aligned
- improve instrumentation
- validate hosted behavior before treating local success as done

## Use These Docs
- [docs/product/spec.md](../product/spec.md): binding product contract
- [docs/drill/engineering.md](../drill/engineering.md): graph/drill invariants
- [docs/project/mvp-happy-path.md](mvp-happy-path.md): current manual release gate
- [docs/project/operations.md](operations.md): merge and stabilization criteria
- `logs/drill-runs.jsonl` and screenshots: current release evidence and gaps

## Environment Lessons
- Local success is not deployment validation.
- Vercel serverless file writes are not durable release evidence; export Socratink Brain-marked runtime logs or use a durable store for hosted drill telemetry.
- Hosted YouTube transcript retrieval can fail because cloud/serverless IPs are blocked.
- Manual transcript paste remains the hosted fallback.
- External calls must be reviewed for SSRF risk and error leakage.
