---
description: Heavy-planning pipeline (lite). Skips Step 3 hard gate unconditionally — for low-stakes runs.
---

# pipette-lite

Run the pipette pipeline without the Step 3 hard gate.

**When to use:** bug fixes, single-file features, dev-tooling — anything that
doesn't touch prod customer surface. F15's heuristic auto-pass already
short-circuits well-tested low-risk runs in default `/pipette`; reach for
`/pipette-lite` only when you've consciously decided the topic doesn't need
multi-reviewer review even if F15 wouldn't auto-pass.

**Cost:** ~60–100k tokens for a small task vs. ~500k for full pipette.

**What's preserved:** Steps 0, 1, 2, 4, 5, 6, 7. Single-subagent only — no
best-of-N. Lockfile, trace.jsonl, and audit trail behave identically to
default `/pipette`.

**What's skipped:** Step 3 hard gate (no reviewers, no verifier, no gemini
critique). The orchestrator records `step3_skipped reason=lite_mode` on the
trace so the audit log captures the override.

## Procedure

Invoke the same pipette orchestrator with `--lite` (or equivalent flag)
that calls `lite_pipeline_steps()` and `should_run_step3(..., lite_mode=True)`.
The orchestrator markdown for `/pipette` is the source of truth for the
step-by-step procedure; this command differs only in the Step 3 gate.

Before any reviewer dispatch, the markdown must record the lite-mode skip
on the trace:

```bash
pipette trace-append --folder "$PIPETTE_FOLDER" --step 3 --event step3_skipped
# Then pass --data 'reason=lite_mode' once Chunk B's trace-append --data flag lands
```

This emits `step3_skipped reason=lite_mode` to trace.jsonl so the audit log
captures the override. Do not silently skip — the trace event is the paper trail.

## Step subset

```bash
pipette lite-pipeline-steps
# stdout: [0, 1, 2, 4, 5, 6, 7]
```

## Gate query (for use in conditional markdown)

```bash
pipette should-run-step3 --folder "$PIPETTE_FOLDER" --lite
# stdout: false  (always — lite mode is an absolute override)
```
