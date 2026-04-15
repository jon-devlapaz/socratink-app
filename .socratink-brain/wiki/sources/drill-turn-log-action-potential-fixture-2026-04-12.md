---
title: "Action Potential Fixture Drill Turn Log 2026-04-12"
type: source
updated: 2026-04-12
related: [../records/finding-action-potential-fixture-solid-redrill.md, ../log-coverage.md]
basis: sourced
workflow_status: active
flags: []
source_kind: drill-turn-log
raw_artifacts: [raw/drill-chat-logs/2026-04-12-drill-chat-turns-action-potential-fixture.jsonl]
log_surface: drill
evaluated_sessions: 1
evaluated_runs: 0
---

# Action Potential Fixture Drill Turn Log 2026-04-12

## Summary
This source registers the turn-level drill telemetry from `logs/drill-chat-turns.jsonl` as of 2026-04-12. The artifact contains two successful sandbox fixture rows for `fixture_id: action-potential-core`, both tied to one `core-thesis` session in `drill_mode: re_drill`.

The init row records the assistant's reconstruction prompt without classification or mutation. The turn row records the learner's generated explanation of the action-potential mechanism and the model's `solid` classification with `routing: NEXT`, `score_eligible: true`, and `graph_mutated: true`.

The artifact preserves the learner and assistant transcript at the service turn layer, but it is still fixture evidence. It does not prove hosted endpoint logging, cold-attempt coverage, study coverage, spacing enforcement, or replay/test coverage.

## Raw Artifacts
- `raw/drill-chat-logs/2026-04-12-drill-chat-turns-action-potential-fixture.jsonl`

## Connections
- Related finding: [Action Potential Fixture Solid Re-Drill](../records/finding-action-potential-fixture-solid-redrill.md)
- Coverage manifest: [Socratink Log Coverage](../log-coverage.md)
