---
title: "External Audit Promotion Policy"
type: decision
updated: 2026-04-08
sources: [../../../docs/project/state.md, ../../../docs/project/operations.md, ../../../docs/product/spec.md]
related: [../mechanisms/external-audit-triage-loop.md]
basis: inferred
confidence: high
workflow_status: resolved
flags: []
review_after: 2026-05-01
---

# External Audit Promotion Policy

## Decision
External repo audits will be stored in the Socratink Brain KB and triaged there. They will not become a separate standing backlog.

Only validated claims that materially affect the current MVP gate should be promoted into active work. For the current repo state, promotion is limited to:
- truthful loop breaks
- hosted versus local divergence risks
- SSRF or internal error leakage risks
- instrumentation gaps that block evidence capture
- CTA, state, or graph contradictions against the binding product contract

Everything else should remain in compiled memory until it becomes directly relevant.

## Evidence
The current project state and operations docs define a narrow release discipline centered on the thermostat loop, truthful state transitions, hosted caution, and evidence capture rather than broad scope expansion. See [docs/project/state.md](../../../docs/project/state.md) and [docs/project/operations.md](../../../docs/project/operations.md).

The product spec binds the team to Generation Before Recognition, truthful graph progression, and the three-phase loop. See [docs/product/spec.md](../../../docs/product/spec.md). Those constraints matter more than a generic external critique.

The intake mechanism for this policy is described in [External Audit Triage Loop](../mechanisms/external-audit-triage-loop.md).

## Inference
External audits can reveal real signal, but they also mix good diagnosis with weak inference, stale assumptions, and speculative architecture advice. Converting them directly into a broad todo list would create work inflation and dilute the current release gate.

The better pattern is to keep critique durable in memory while aggressively filtering what becomes active work.

## Product Implication
When a new audit arrives, the repo should capture it under `.socratink-brain/` and promote at most a few release-relevant items into active work. This keeps the project epistemically honest and operationally light.
