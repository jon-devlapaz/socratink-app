---
title: "Bloom's Taxonomy Research Note"
type: source
updated: 2026-04-18
sources: []
related: [../concepts/blooms-taxonomy.md, ../concepts/generation-effect.md, ../concepts/testing-effect.md, ../concepts/zone-of-proximal-development.md]
basis: sourced
workflow_status: active
flags: [open-question]
source_kind: research-note
raw_artifacts: [raw/research-notes/2026-04-18-blooms-taxonomy.md]
log_surface: none
evaluated_sessions: 0
evaluated_runs: 0
---

# Bloom's Taxonomy Research Note

## Summary

This source is the 2026-04-18 theta primary-literature review of Bloom's Taxonomy — both the original Bloom et al. (1956) *Taxonomy of Educational Objectives* and the Anderson & Krathwohl (2001) revision. The note's load-bearing conclusion is that **Bloom's is pedagogical classification, not cognitive-science mechanism**. It is useful to Socratink as shared vocabulary for prompt design and node typing, but it is not a scientific theory of how learning happens, and product claims should not cite it as if it were.

The note's critical corrections to the current concept page: the claim that Socratink's drill "operates at higher Bloom's levels" draws its actual evidence from the generation effect, retrieval practice, and elaborative-interrogation literatures — not from Bloom's. Bloom's provides useful labels for the *kind* of question being asked; it does not supply the mechanism by which those questions produce learning. The state machine (`locked → primed → drilled → solidified`) should not be treated as a gated Bloom's climb — Krathwohl (2002) himself explicitly weakens the cumulative hierarchy claim in the revision, acknowledging that the taxonomy is a flexible matrix rather than a strict progression.

Two additional practical cautions: (1) inter-rater reliability on Bloom's level coding is consistently poor (Stanny 2016 review) — this makes Bloom's unsuitable as an analytics aggregation key or as a stable input to automated drill-depth routing; different coders will disagree on whether a given question is Apply vs. Analyze, so treating Bloom's level as a data field risks encoding noise as signal. (2) The popular claim that "higher-order Bloom's levels produce stronger retention" is not directly supported by Bloom's-specific studies; it is instead an import from retrieval-practice and elaborative-interrogation findings that happen to use higher-order prompts.

The note's framing for Socratink: use Bloom's as prompt-design vocabulary (a way to talk about whether a question demands recall vs. analysis vs. evaluation) and as a sanity check on drill question variety. Do not use it as a predictive model, a mastery gate, or an analytics category. Any product claim about drill depth should cite the specific mechanism (generation, retrieval, elaboration) rather than Bloom's level.

## Raw Artifacts
- `raw/research-notes/2026-04-18-blooms-taxonomy.md`

## Connections
- Concept page: [Bloom's Taxonomy](../concepts/blooms-taxonomy.md)
- Related concepts: [Generation Effect](../concepts/generation-effect.md), [Testing Effect](../concepts/testing-effect.md), [Zone of Proximal Development](../concepts/zone-of-proximal-development.md)
