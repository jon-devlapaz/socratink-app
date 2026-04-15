# Socratink Log Surfaces

Use this reference when building or checking the log-coverage manifest.

## Current Known Log Files

These current repo paths are already emitted by Socratink:

- `logs/drill-chat-transcripts.jsonl`
  - appended in [main.py](../../../../main.py)
  - session-oriented drill transcript events
- `logs/drill-runs.jsonl`
  - appended in [ai_service.py](../../../../ai_service.py)
  - run-level drill summaries
- `logs/drill-chat-turns.jsonl`
  - appended in [ai_service.py](../../../../ai_service.py)
  - turn-level drill events

## Contract Rule

Socratink Brain must treat all Socratink chat surfaces and test/replay surfaces as required coverage.

If a surface exists conceptually but lacks instrumentation:
- list it under `missing_instrumentation`
- describe it in `wiki/log-coverage.md`
- treat it as a health-check gap

## Minimum V1 Coverage

At minimum, the KB should explicitly represent:
- drill chat coverage
- drill run coverage
- replay/test coverage expectations, even if current instrumentation is partial

## Operational Notes

- Do not assume logs are exhaustive.
- Do not silently infer coverage from one log file.
- A source page may summarize one log artifact or a small grouped set when the grouped pattern matters more than each file alone.

## Worked Example (Synthetic — Not A Real Ingestion)

This example is a fixture for agent behavior only. Do not create source pages, findings, or increment `evaluated_runs` / `evaluated_sessions` from this synthetic JSONL.

Input shape:

```jsonl
{"session_id":"fixture-001","node_id":"core-thesis","classification":"solid","termination_reason":"solid_reconstruction","session_start_iso":"2026-04-11T15:00:00Z"}
```

Ingestion path:
1. Copy a real log artifact to `raw/drill-chat-logs/drill-runs-YYYY-MM-DD.jsonl`.
2. Create `wiki/sources/drill-run-log-{slug}.md` with `source_kind: drill-run-log`, `log_surface: drill`, and accurate `evaluated_runs`.
3. Create `wiki/records/finding-{slug}.md` only when the real log changes instrumentation truth, release risk, or product understanding.
4. Update `wiki/log-coverage.md` only when the log changes what Socratink captures or fails to capture.
