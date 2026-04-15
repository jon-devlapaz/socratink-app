---
title: "Hosted Cold Attempt Transcript Evidence"
type: finding
updated: 2026-04-12
related: [../log-coverage.md, issue-replay-coverage-below-truth-bar.md]
basis: sourced
workflow_status: open
flags: [open-question]
sources: [../sources/drill-chat-log-hosted-modularity-cold-attempt-2026-04-12.md]
confidence: medium
---

# Hosted Cold Attempt Transcript Evidence

## Finding
The newest non-empty hosted drill-chat export shows one production cold-attempt path resolving with the right narrow control signals: the learner generated an answer before recognition, the turn stayed unscored, no classification or reward was emitted, and the backend routed with `NEXT`.

The log is positive but narrow. It is transcript evidence for hosted cold-attempt handling and Vercel runtime-log capture, not evidence that the full MVP loop is healthy.

## Evidence
Direct evidence:
- `2026-04-12T220245Z-vercel-drill-chat-events.jsonl`: 2 successful production `drill_chat` rows; 1 init row; 1 cold-attempt learner turn; 1 `generative_commitment: true`; 1 `routing: NEXT`; `score_eligible: false`; `classification: null`; `ux_reward_emitted: false`.
- `2026-04-12T213919Z-vercel-drill-chat-events.jsonl`: byte-identical duplicate of the newest non-empty artifact.
- `2026-04-12T220040Z-vercel-drill-chat-events.jsonl` and `2026-04-12T220130Z-vercel-drill-chat-events.jsonl`: zero-byte exports; no behavioral evidence.

Source page:
- [Hosted Modularity Cold Attempt Drill Chat Log 2026-04-12](../sources/drill-chat-log-hosted-modularity-cold-attempt-2026-04-12.md)

Inference:
- Hosted transcript capture is working for this `/api/drill` session when full transcript capture is enabled.
- The `graph_mutated: true` field is a backend result flag tied to `routing: NEXT`; it is not a post-persist frontend graph snapshot.
- The cold-attempt response is affirming, but the logged control fields do not treat the attempt as scored mastery.

## Product Implication
Treat this as one useful hosted evidence fragment for cold-attempt behavior. It should not close the release gate, because it does not prove study, spacing, re-drill, cluster traversal, localStorage persistence, or graph state after frontend mutation.

No code hot-fix is warranted from this artifact alone. The smallest workflow fix is to dedupe duplicate Vercel exports during evaluation and ignore zero-byte exports as non-evidence, while the next BML run should capture a full cold attempt to study to spaced re-drill path with post-action graph state.
