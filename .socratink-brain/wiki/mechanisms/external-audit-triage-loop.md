---
title: "External Audit Triage Loop"
type: mechanism
updated: 2026-04-08
sources: [../../../docs/project/state.md, ../../../docs/project/operations.md, ../../../docs/product/spec.md]
related: [../records/decision-external-audit-promotion-policy.md]
basis: inferred
confidence: medium
workflow_status: active
flags: []
---

# External Audit Triage Loop

## Mechanism
External repo critiques should enter Socratink as raw artifacts first, not as project truth and not as an immediate task list.

The promotion path is:
1. store the original audit under `raw/product-chat-logs/`
2. create a source page if the audit is worth keeping
3. split claims into evidence, inference, and speculation
4. promote only validated claims into `finding`, `issue`, `decision`, or `synthesis` records
5. convert only the small subset that affects the current MVP release gate into active work, following the policy in [External Audit Promotion Policy](../records/decision-external-audit-promotion-policy.md)

## Evidence
The current repo state is MVP stabilization with a narrow thermostat release gate rather than broad feature expansion. [docs/project/state.md](../../../docs/project/state.md) and [docs/project/operations.md](../../../docs/project/operations.md) both emphasize hosted verification, truthful graph state, instrumentation gaps, and explicit evidence capture over broad speculative planning.

The product doctrine also requires Generation Before Recognition and truthful graph progression. [docs/product/spec.md](../../../docs/product/spec.md) makes those constraints binding, which means external critique cannot be accepted wholesale if it conflicts with the product contract.

## Product Implication
Treat external audits as high-value prompts for inspection, not as backlog authority. The KB should preserve their signal, but active work should stay small and tied to actual release risk.
