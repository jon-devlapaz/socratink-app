---
title: "Socratink Log Coverage"
type: log-coverage
updated: 2026-04-08
expected_chat_surfaces: [drill]
instrumented_chat_surfaces: [drill]
expected_test_surfaces: [replay]
instrumented_test_surfaces: []
current_log_files: [logs/drill-chat-transcripts.jsonl, logs/drill-chat-turns.jsonl, logs/drill-runs.jsonl]
missing_instrumentation: [replay]
---

# Socratink Log Coverage

## Current Log Adapters
Current repo instrumentation covers drill transcripts, drill turns, and drill runs. These remain the minimum evidence sink for MVP stabilization work.

## Missing Instrumentation
Replay or test-surface evidence is still an explicit gap. External audit documents may identify that gap, but they do not substitute for direct product evidence.

## Notes
This KB can ingest external critique documents, but the graph and release state must still be grounded in product logs, screenshots, and hosted verification.
