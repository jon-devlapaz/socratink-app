# Theta State

## Product-science snapshot

- LearnOps-tamagachi is a retrieval-centered learning product. The product is trying to improve durable understanding by forcing generation before recognition, giving specific feedback after the attempt, and using spacing/consolidation to distinguish short-term access from retained knowledge.

## Current claims

### Strongly supported

- Claim: passive review and recognition-heavy study can create an illusion of competence that does not translate into durable retrieval.
- Evidence: broad retrieval-practice and spacing literature, plus existing repo doctrine in [docs/product/ux-framework.md](../product/ux-framework.md).
- Confidence: medium

### Moderately supported

- Claim: active retrieval and spaced practice are aligned with the product's intended learning loop.
- Evidence: primary literature remains the right basis; the current repo uses these mechanisms as the core justification for drill and graph truth.
- Confidence: medium

### Weak / speculative

- Claim: r/GetStudying-derived personas and behavioral segments are sufficient to define the product's learning mechanism.
- Why weak: the report is useful market synthesis and directional qualitative input, but it is not direct evidence for the four-phase model or for causal learning outcomes.
- What would strengthen it: triangulation with primary learning-science literature, direct user research, and product data showing that the identified pain patterns map to better retrieval behavior rather than only better engagement.

## Product implications

- Design: automate ingestion, drill generation, scheduling, and provenance, but keep the learner's generation attempt as the core event.
- Messaging: position AI as prep-friction removal plus truthful retrieval support, not as answer generation or learning substitution.
- Research: keep citing active retrieval and spacing from primary literature, and treat Reddit/persona synthesis as hypothesis input for prioritization rather than mechanistic proof.
- UX: accountability, pacing, and motivational scaffolds are acceptable only when they help learners enter the loop without altering graph truth or mastery semantics.

## Open scientific questions

- Which parts of the current four-phase framing are directly evidenced versus product-level synthesis?
- What kind of feedback best repairs misconceptions without lowering the mastery bar?
- Which accountability mechanisms improve follow-through without producing false progress signals?

## Recent decisions

### 2026-04-02

- Decision: treat the r/GetStudying market analysis as product-framing input for messaging and UX prioritization, not as evidence-grade proof of the learning model.
- Why: the strongest signals are qualitative user pain patterns around friction, AI distrust, and accountability needs; those help shape positioning but do not validate causal learning claims.
- Evidence basis: indirect market/user synthesis from the "AI Platform Research for Students" PDF, combined with existing product doctrine around generation-before-recognition and truthful graph progression.
