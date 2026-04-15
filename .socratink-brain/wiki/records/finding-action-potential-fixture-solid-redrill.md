---
title: "Action Potential Fixture Solid Re-Drill"
type: finding
updated: 2026-04-12
related: [../log-coverage.md]
basis: sourced
workflow_status: open
flags: [open-question]
sources: [../sources/drill-run-log-action-potential-fixture-2026-04-12.md, ../sources/drill-turn-log-action-potential-fixture-2026-04-12.md]
confidence: medium
---

# Action Potential Fixture Solid Re-Drill

## Finding
The 2026-04-12 action-potential fixture produced one scored `solid` re-drill outcome for `core-thesis`. The run summary and turn log agree on the key product signals: the learner made a generative attempt, the response was score-eligible, classification was `solid`, routing advanced with `NEXT`, and the graph mutation flag was true.

This is positive but narrow evidence. It supports a single sandbox fixture's solid re-drill path, not the full MVP loop or hosted release gate.

## Evidence
Direct evidence:
- `drill-runs.jsonl`: 2 successful run rows; 1 init row, 1 scored turn row; 1 `solid` classification; 1 `NEXT` routing; 1 graph mutation; 1 reward emission; `run_mode: fixture`; `sandbox: true`.
- `drill-chat-turns.jsonl`: 2 successful turn rows; 1 init row, 1 scored turn row; 1 `solid` classification; 1 `NEXT` routing; 1 graph mutation; `run_mode: fixture`; `sandbox: true`.

Source pages:
- [Action Potential Fixture Drill Run Log 2026-04-12](../sources/drill-run-log-action-potential-fixture-2026-04-12.md)
- [Action Potential Fixture Drill Turn Log 2026-04-12](../sources/drill-turn-log-action-potential-fixture-2026-04-12.md)

Inference:
- The fixture demonstrates that the service-level drill evaluator can accept a causal reconstruction and emit the expected solid re-drill control signals for this scripted case.
- The evidence does not demonstrate cold attempt, targeted study, elapsed spacing, interleaving, endpoint transcript logging, replay/test coverage, or Vercel-hosted behavior.

## Product Implication
Treat this as a useful release-evidence fragment, not a mastery of the release gate. The graph-truth bar still requires evidence for the full cold attempt to study to spaced re-drill loop and for replay or hosted verification where production behavior can diverge from local fixture behavior.
