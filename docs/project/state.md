# Project State

## Snapshot
- Product: socratink
- Stage: MVP stabilization
- Release gate: the thermostat starter-map loop
- Core architecture: cold attempt -> targeted study -> spaced re-drill
- Core node states: `locked -> primed -> drilled -> solidified`
- Hosted runtime: Vercel serverless
- Current persistence: browser `localStorage`
- Evidence source of truth: live logs plus the operational docs in this repo

## Current Release Goal
Ship a workable loop to `main` with no obvious breaks. For this branch, "working" means:
- core thesis cold attempt resolves cleanly
- study and return-to-map work
- backbone cold attempt resolves cleanly
- cluster opens after backbone study
- child drill nodes are selectable inside the cluster
- spacing/interleaving truthfully block premature re-drill
- re-drill can end in `drilled` or `solidified`
- graph state matches persisted truth throughout

## Known Live Evidence
- The latest thermostat evidence should be captured in live logs and summarized in the operational docs before merge.
- Current strong signal: a thermostat session reached a scored `solid` re-drill.
- Current weak signal: transcript-level drill coverage and replay/test coverage are still incomplete.

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
- keep the thermostat loop healthy enough to merge
- remove CTA/progression contradictions
- keep graph state and persisted state aligned
- improve instrumentation without blocking the narrow release gate
- validate hosted behavior before treating local success as done

## Use These Docs
- [docs/product/spec.md](../product/spec.md): binding product contract
- [docs/drill/engineering.md](../drill/engineering.md): graph/drill invariants
- [docs/project/mvp-happy-path.md](mvp-happy-path.md): current manual release gate
- [docs/project/operations.md](operations.md): merge and stabilization criteria
- `logs/drill-runs.jsonl` and screenshots: current release evidence and gaps

## Environment Lessons
- Local success is not deployment validation.
- Hosted YouTube transcript retrieval can fail because cloud/serverless IPs are blocked.
- Manual transcript paste remains the hosted fallback.
- External calls must be reviewed for SSRF risk and error leakage.
