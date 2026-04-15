---
title: "Socratink Log Coverage"
type: log-coverage
updated: 2026-04-12
expected_chat_surfaces: [drill]
instrumented_chat_surfaces: [drill]
expected_test_surfaces: [replay]
instrumented_test_surfaces: []
current_log_files: [logs/drill-chat-turns.jsonl, logs/drill-runs.jsonl]
missing_instrumentation: [replay (deferred to DB milestone)]
---

# Socratink Log Coverage

## Current Log Adapters
Current repo instrumentation covers drill transcripts through `/api/drill`, service-level drill turns, and service-level drill runs. These remain the minimum evidence sink for MVP stabilization work.

The 2026-04-12 evaluated drill artifacts in `logs/` include `logs/drill-runs.jsonl` and `logs/drill-chat-turns.jsonl`. They do not include a current `logs/drill-chat-transcripts.jsonl` artifact, which means this fixture run appears to have exercised the lower-level service path rather than the full endpoint transcript adapter.

Hosted `/api/drill` now also emits structured `socratink_event` runtime logs for drill chat events. Summary capture is on by default; full learner/assistant transcript capture requires `SOCRATINK_CAPTURE_DRILL_TRANSCRIPTS=true` in the Vercel environment. Use `scripts/export_socratink_brain_vercel_logs.py` to convert Vercel JSON logs into `.socratink-brain/raw/drill-chat-logs/` artifacts for evaluation.

The newest evaluated hosted drill-chat export, `raw/drill-chat-logs/2026-04-12T220245Z-vercel-drill-chat-events.jsonl`, contains a full production cold-attempt transcript and is byte-identical to the earlier `raw/drill-chat-logs/2026-04-12T213919Z-vercel-drill-chat-events.jsonl` export. The adjacent `2026-04-12T220040Z` and `2026-04-12T220130Z` files are zero-byte exports and should be treated as non-evidence rather than behavior regressions.

## Missing Instrumentation
Replay test coverage is deferred to the DB milestone. The replay mechanism itself has been verified sound (deterministic persist → restore → derive). Automated regression tests will be added when the persistence layer moves from localStorage to a database.

## Notes
This KB can ingest external critique documents, fixture logs, and live drill logs, but the graph and release state must still be grounded in product logs, screenshots, replay/test traces, and hosted verification. Fixture logs should be marked as fixture evidence and should not be promoted as full release validation.
