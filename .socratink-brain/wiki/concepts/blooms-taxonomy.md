---
title: "Bloom's Taxonomy"
type: concept
updated: 2026-04-18
sources: [../sources/research-note-blooms-taxonomy.md]
related: [../concepts/zone-of-proximal-development.md, ../concepts/desirable-difficulty.md, ../concepts/generation-effect.md, ../concepts/testing-effect.md]
basis: sourced
workflow_status: active
flags: []
confidence: medium
domain_axes: [learning-science, product-design]
key_researchers: [Benjamin Bloom, Lorin Anderson, David Krathwohl]
relevance: peripheral
---

# Bloom's Taxonomy

## Definition

Bloom's Taxonomy is a hierarchical classification of cognitive processes involved in learning, originally published by Benjamin Bloom and colleagues in 1956 and revised by Anderson and Krathwohl in 2001. It orders thinking skills from lower-order (recall) to higher-order (creation), providing a shared vocabulary for what "understanding" actually means at different depths.

The revised taxonomy (2001) uses verbs instead of nouns, reflecting that cognition is an active process:

1. **Remember** — retrieve relevant knowledge from long-term memory (recognize, recall)
2. **Understand** — construct meaning from information (explain, classify, summarize, compare)
3. **Apply** — carry out a procedure in a given situation (execute, implement)
4. **Analyze** — break material into parts and determine relationships (differentiate, organize, attribute)
5. **Evaluate** — make judgments based on criteria (check, critique)
6. **Create** — put elements together to form a coherent whole or produce something new (generate, plan, produce)

## Key Mechanisms

- **Cumulative hierarchy** — higher levels generally require competence at lower levels. You can't analyze what you can't remember, and you can't evaluate what you haven't analyzed. However, the revised taxonomy acknowledges that the order isn't strictly linear — learners move fluidly between levels.
- **Knowledge dimension** — the 2001 revision added a second axis: factual, conceptual, procedural, and metacognitive knowledge. A learner can *remember* factual knowledge while *analyzing* conceptual knowledge in the same session.
- **Assessment alignment** — Bloom's gives instructors a way to check whether their assessments actually test the cognitive level they intend. A question that asks "list the steps" tests Remember; "why does this approach fail?" tests Evaluate.

## Relationship to Other Concepts

- **Desirable difficulty** — higher Bloom's levels are inherently more effortful. Pushing a learner from Remember to Analyze for the same material introduces desirable difficulty by design.
- **Zone of Proximal Development** — Bloom's levels help locate *where* the ZPD boundary sits. If a learner can Understand a concept but not Apply it, the ZPD for that node spans Apply through Analyze. Scaffolding should target that range.
- **Retrieval practice** — retrieval can operate at any Bloom's level. Recalling a fact is Remember-level retrieval; generating an explanation from memory is Understand-level retrieval. Higher-level retrieval produces stronger encoding.

## Why This Matters for Socratink

**Important framing (per source review):** Bloom's Taxonomy is *pedagogical classification*, not cognitive-science mechanism. It is useful as shared vocabulary for prompt design and node typing, not as a predictive model of how learning happens. When Socratink's drill claims to "produce deeper learning by targeting higher Bloom's levels," the actual mechanism is generation, retrieval practice, and elaborative interrogation — not Bloom's itself. Any product claim about drill depth should cite the specific mechanism, not the Bloom's level.

With that caveat, Bloom's provides a useful vocabulary surface:

- **Prompt-design vocabulary.** Bloom's verbs give a shared language for whether a Socratic prompt is asking for recall ("what is X?"), construction ("explain why X"), application ("what would change if Y?"), or evaluation ("is this account complete?"). This is vocabulary, not mechanism.
- **Sanity check on prompt variety.** A drill session that sits exclusively at Remember-level prompts is almost certainly under-drilling the concept. Bloom's levels give a coarse audit surface for prompt diversity.
- **Node typing at the margins.** Definition nodes, process nodes, and causal-mechanism nodes have different default prompt centers of gravity. Bloom's is one reasonable way to describe those defaults, though generation/elaboration descriptors work equally well.

**What Bloom's does NOT support (reconciled 2026-04-18):**

- Bloom's does *not* supply the mechanism by which higher-order prompts produce better learning — that evidence lives in the generation, retrieval, and elaborative-interrogation literatures. Citing "higher Bloom's level" as if it were the cause is a category error.
- The `primed → drilled → solidified` state machine is *not* a gated Bloom's climb. Krathwohl (2002) himself weakens the cumulative hierarchy claim in the revision; treating state transitions as Bloom's-level promotions over-claims the taxonomy's predictive power.
- Bloom's is *not* suitable as an analytics aggregation key or an automated drill-depth routing input. Inter-rater reliability on Bloom's-level coding is consistently poor (Stanny 2016). Using it as a data field encodes coder disagreement as signal.

## Connections

- Desirable difficulty — the mechanism-level account of why effortful prompts produce durable learning
- Generation effect / Testing effect — the actual mechanisms behind "higher-order drill" benefits
- Zone of Proximal Development — a different lens on prompt calibration (support level, not cognitive-operation type)

## Source

- [Bloom's Taxonomy Research Note](../sources/research-note-blooms-taxonomy.md) — primary-literature review establishing Bloom's as pedagogical classification (not cognitive mechanism), Krathwohl 2002 on the weakened hierarchy claim, and Stanny 2016 on inter-rater reliability limits for Bloom's-level coding.
