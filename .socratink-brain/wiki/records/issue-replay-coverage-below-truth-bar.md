---
title: "Replay Coverage Below Truth Bar"
type: issue
updated: 2026-04-14
sources: [../sources/product-chat-log-chatgpt-repo-audit-2026-04-08.md]
related: [../syntheses/external-audit-confirms-mvp-priors.md]
basis: sourced
confidence: high
workflow_status: resolved
closed_date: 2026-04-13
closed_reason: "Replay mechanism verified sound; automated test coverage deferred to DB milestone"
flags: []
---

# Replay Coverage Below Truth Bar

## What Broke
The repo has real manual release discipline and an internal tasting fixture, but it still lacks enough automated replay coverage to fully support the product claim that the graph tells the truth under regression pressure.

## Evidence
The external audit explicitly called out missing automated core-loop tests and weak replay coverage. That claim is validated by current repo state rather than contradicted by it. [docs/project/state.md](../../../docs/project/state.md) says transcript-level drill coverage and replay/test coverage are still incomplete. [docs/project/operations.md](../../../docs/project/operations.md) describes the thermostat path as a narrow manual release gate and says evidence must be captured explicitly. [scripts/run_tasting_fixture.py](../../../scripts/run_tasting_fixture.py) shows there is fixture infrastructure for internal tasting, but it is not yet the same thing as an enforced release harness.

## Product Implication
This issue is no longer an active Brain queue item. Replay mechanism soundness was verified, while automated test coverage was explicitly deferred to the DB milestone. Future work should still preserve the underlying truth bar: repeatable thermostat verification matters, but it should not displace the current "continue measuring runs" direction unless new evidence promotes it again.
