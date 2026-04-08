# Socratink Log Surfaces

Use this reference when building or checking the log-coverage manifest.

## Current Known Log Files

These current repo paths are already emitted by Socratink:

- `logs/drill-chat-transcripts.jsonl`
  - appended in [main.py](/Users/jondev/dev/socratink/prod/socratink-app/main.py)
  - session-oriented drill transcript events
- `logs/drill-runs.jsonl`
  - appended in [ai_service.py](/Users/jondev/dev/socratink/prod/socratink-app/ai_service.py)
  - run-level drill summaries
- `logs/drill-chat-turns.jsonl`
  - appended in [ai_service.py](/Users/jondev/dev/socratink/prod/socratink-app/ai_service.py)
  - turn-level drill events

## Contract Rule

The Socratinker must treat all Socratink chat surfaces and test/replay surfaces as required coverage.

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
