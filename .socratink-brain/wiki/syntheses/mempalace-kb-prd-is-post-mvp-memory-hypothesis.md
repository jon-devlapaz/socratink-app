---
title: "MemPalace KB PRD Is Post-MVP Memory Hypothesis"
type: synthesis
updated: 2026-04-13
sources: [../sources/product-doc-socratink-llm-kb-mempalace-prd.md, ../../../docs/project/state.md, ../../../docs/product/spec.md, ../../../docs/theta/state.md]
related: []
basis: inferred
confidence: medium
workflow_status: open
flags: [hypothesis, open-question]
---

# MemPalace KB PRD Is Post-MVP Memory Hypothesis

## Pattern
The MemPalace PRD should be preserved as a future memory and retrieval architecture hypothesis, not promoted into the current active MVP gate. It contains two different ideas that should remain separated: improving internal product memory for agents, and adding persistent learner-facing semantic/KG memory to graph and quiz generation.

## Evidence
[Socratink LLM KB and MemPalace PRD](../sources/product-doc-socratink-llm-kb-mempalace-prd.md) proposes a raw->wiki->Palace ingest/query loop, local Chroma and SQLite storage, MemPalace wings, MCP tools, vault selection, and product metrics for graph rebuild accuracy, quiz personalization, agent autonomy, and token efficiency.

[docs/project/state.md](../../../docs/project/state.md) says the repo is in MVP stabilization, with a current release gate around the thermostat starter-map loop, Vercel serverless hosted behavior, browser `localStorage` persistence, incomplete instrumentation, and explicit caution that local behavior does not prove hosted behavior.

[docs/product/spec.md](../../../docs/product/spec.md) and [docs/theta/state.md](../../../docs/theta/state.md) bind learner-facing changes to Generation Before Recognition, truthful graph state, unscored cold attempts, targeted study, spacing, and spaced reconstruction before `solidified`. They also caution that AI supports ingestion, routing, feedback, and friction reduction, but AI itself is not evidence that learning occurred.

## Inference
The internal Socratink Brain half of the PRD is close to existing practice and can continue improving incrementally inside `.socratink-brain/`. It should not require a parallel `kb/` root unless there is a deliberate migration decision, because the current KB already has raw artifacts, compiled wiki pages, source pages, syntheses, health-check/lint conventions, and an active-queue policy.

The learner-facing MemPalace half needs a separate product and deployment design before implementation. The open questions are not just library wiring; they include hosted storage durability, tenant isolation, privacy promises, Vercel compatibility, SSRF/error-leakage review for any external ingestion, and the truthful-graph rule for using retrieved priors. A semantic or temporal KG prior may personalize prompts, but it must not pre-answer the target, inflate mastery, or let generated graph structure count as understanding.

The PRD's metrics are useful as desired evaluation targets, but they are not evidence yet. Recall lift, hallucination rate, token efficiency, and graph rebuild accuracy need instrumented baselines before they can be used as product truth.

## Product Implication
Keep the current active queue focused on the thermostat loop and evidence capture. Preserve this PRD as a post-MVP memory track: continue using Socratink Brain for internal product memory now, and only move learner-facing MemPalace/KG integration into implementation after there is an explicit architecture decision covering Vercel deployment, privacy, persistence, evaluation metrics, and how KG retrieval preserves Generation Before Recognition and truthful graph progression.
