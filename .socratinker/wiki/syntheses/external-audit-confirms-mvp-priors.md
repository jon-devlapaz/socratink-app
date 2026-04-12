---
title: "External Audit Confirms MVP Priors"
type: synthesis
updated: 2026-04-08
sources: [../sources/product-chat-log-chatgpt-repo-audit-2026-04-08.md]
related: [../records/issue-replay-coverage-below-truth-bar.md, ../records/decision-external-audit-promotion-policy.md]
basis: inferred
confidence: medium
workflow_status: open
flags: []
---

# External Audit Confirms MVP Priors

## Pattern
The external audit is most useful as confirmation and prioritization pressure, not as a source of new architectural truth. Its strongest claims largely restate risks the repo already documents: local-only persistence is fragile, hosted behavior can diverge from local, replay coverage is incomplete, and the current release gate is narrow rather than growth-oriented.

## Evidence
The raw audit argues that persistence is the largest strategic product gap and that replay automation is weaker than the product's truth claims require. Those statements align with [ChatGPT Repo Audit 2026-04-08](../sources/product-chat-log-chatgpt-repo-audit-2026-04-08.md), [docs/project/state.md](../../../docs/project/state.md), and [docs/project/operations.md](../../../docs/project/operations.md). The repo already records `localStorage` as the current persistence layer, already treats hosted validation as mandatory, and already admits incomplete replay/test coverage.

## Inference
The audit should influence prioritization, but it should not overwrite the current operating rule. The correct read is: persistence is the biggest strategic gap, but replayable thermostat verification is the more immediate release-facing gap. Promoting Postgres directly into active work right now would collapse the repo's own stabilization discipline.

## Product Implication
Keep persistence and account memory in durable product memory as a near-future strategic track. Keep the active queue narrow and release-facing until the thermostat loop is healthy enough to merge.
