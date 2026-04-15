---
title: "Socratink LLM KB and MemPalace PRD"
type: source
updated: 2026-04-13
sources: []
related: [../syntheses/mempalace-kb-prd-is-post-mvp-memory-hypothesis.md]
basis: sourced
workflow_status: active
flags: [hypothesis, open-question]
source_kind: product-doc
raw_artifacts: [raw/product-docs/socratink-llm-kb-mempalace-prd.md]
log_surface: none
evaluated_sessions: 0
evaluated_runs: 0
---

# Socratink LLM KB and MemPalace PRD

## Summary
This raw artifact is a product requirements draft for adding a Karpathy-style LLM knowledge-base compilation layer plus MemPalace persistent memory/retrieval to Socratink. It proposes agentic ingest, wiki compilation, semantic/KG retrieval, MemPalace wings, Chroma/SQLite storage, lint and health-check automation, and a vault-oriented user experience for product memory and learner recall.

The draft is useful as a strategic product-memory and persistence proposal. Its agent happy path overlaps with the existing Socratink Brain workflow: raw artifact intake, source page creation, compiled wiki implications, health checks, and cited query responses. That part is already compatible with the current `.socratink-brain/` structure and the repository's preference for durable evidence over repeated re-derivation.

The learner-facing MemPalace portion is not yet validated product truth. The PRD makes success-metric claims about graph rebuild accuracy, quiz personalization, recall lift, hallucination rate, and token efficiency, but the artifact itself is a proposal rather than measurement. Treat those metrics as targets or hypotheses until there are logs, experiments, or evaluation sets.

The main constraint conflict is deployment reality. The PRD says MVP should add KB+Palace to the core upload->graph->quiz flow while also requiring 100% local/offline privacy and no API keys. Current project state says Socratink is in MVP stabilization, deploys on Vercel serverless, currently persists in browser `localStorage`, and should avoid broad expansion before the thermostat loop is healthy. A local Chroma/SQLite MemPalace stack may be reasonable for founder/dev workflows, but it is not automatically compatible with a hosted SaaS path without a separate storage, privacy, tenant-isolation, and Vercel runtime design.

## Raw Artifacts
- `raw/product-docs/socratink-llm-kb-mempalace-prd.md`

## Connections
- Related pages: [MemPalace KB PRD Is Post-MVP Memory Hypothesis](../syntheses/mempalace-kb-prd-is-post-mvp-memory-hypothesis.md)
