# Theta State

## Product-science snapshot

- socratink is a retrieval-centered learning product. The product is trying to improve durable understanding by forcing generation before recognition, giving specific feedback after the attempt, and using spacing/consolidation to distinguish short-term access from retained knowledge.
- Current product framing treats AI as a support layer around that loop: useful for adaptation, feedback, access, and operator leverage, but not itself evidence of learning.

## Current claims

### Strongly supported

- Claim: passive review and recognition-heavy study can create an illusion of competence that does not translate into durable retrieval.
- Evidence: broad retrieval-practice and spacing literature, plus existing repo doctrine in [docs/product/ux-framework.md](../product/ux-framework.md).
- Confidence: medium

- Claim: the product should keep generation before recognition as a core learning constraint.
- Evidence: this follows directly from the retrieval-centered model the product is built around; showing the answer before an attempt would collapse the intended mechanism.
- Confidence: medium

### Moderately supported

- Claim: active retrieval and spaced practice are aligned with the product's intended learning loop.
- Evidence: primary literature remains the right basis; the current repo uses these mechanisms as the core justification for drill and graph truth.
- Confidence: medium

- Claim: immediate, specific feedback after a generation attempt is directionally aligned with misconception repair and continued learning.
- Evidence: this is consistent with the repo's four-phase framing, especially the feedback and repair phase, but the current state file does not yet cite durable paper notes for exact feedback-shape claims.
- Confidence: low-to-medium

### Weak / speculative

- Claim: r/GetStudying-derived personas and behavioral segments are sufficient to define the product's learning mechanism.
- Why weak: the report is useful market synthesis and directional qualitative input, but it is not direct evidence for the four-phase model or for causal learning outcomes.
- What would strengthen it: triangulation with primary learning-science literature, direct user research, and product data showing that the identified pain patterns map to better retrieval behavior rather than only better engagement.

- Claim: AI personalization, accessibility layers, concept rendering, and content generation will improve outcomes in this product if they are wrapped around the truthful retrieval loop.
- Why weak: this is a plausible product hypothesis, but the repo has not yet established durable evidence notes showing which AI-mediated supports causally improve learning rather than convenience, engagement, or completion.
- What would strengthen it: primary studies or strong reviews on feedback timing, adaptive support, accessibility interventions, and human-AI tutoring patterns that preserve learner generation.

- Claim: AI can be safely used as part of mastery evaluation without introducing unacceptable bias or misclassification.
- Why weak: model judgments are likely sensitive to language, phrasing, dialect, accessibility needs, and prompt conditions; robust fairness evidence and evaluation procedures are not yet documented in-repo.
- What would strengthen it: explicit evaluation datasets, bias audits, human-review fallbacks, and evidence showing stable scoring across diverse learner populations.

## Product implications

- Design: automate ingestion, drill generation, scheduling, and provenance, but keep the learner's generation attempt as the core event.
- Messaging: position AI as prep-friction removal plus truthful retrieval support, not as answer generation, mastery proof, or learning substitution.
- Research: keep citing active retrieval and spacing from primary literature, and treat Reddit/persona synthesis as hypothesis input for prioritization rather than mechanistic proof.
- UX: accountability, pacing, accessibility support, and motivational scaffolds are acceptable only when they help learners enter the loop without altering graph truth or mastery semantics.
- Trust: privacy, bias risk, and model inaccuracy are not secondary implementation concerns; they shape whether AI-enabled evaluation and feedback are acceptable at all.

## Open scientific questions

- Which parts of the current four-phase framing are directly evidenced versus product-level synthesis?
- What kind of feedback best repairs misconceptions without lowering the mastery bar?
- Which accountability mechanisms improve follow-through without producing false progress signals?
- Which AI-mediated supports improve learning outcomes versus merely improving convenience or engagement?
- What evaluation design is needed to prevent AI scoring bias across language, phrasing, and accessibility differences?

## Recent decisions

### 2026-04-05

- Decision: the April 2026 research synthesis is complete. The three-phase node loop (cold attempt → targeted study → spaced re-drill), four-state model, and evidence-based UX framework are now codified in `docs/product/ux-framework.md`, `progressive-disclosure.md`, and `post-drill-ux-spec.md`.
- Why: the research track produced sufficient evidence to commit to the three-phase architecture. Pretesting effect, prediction error learning, spaced retrieval, and social normalization are all supported by multiple RCTs and meta-analyses.
- Evidence basis: full research synthesis documented in the rewritten UX framework and the current product specification.

### 2026-04-02

- Decision: treat the r/GetStudying market analysis as product-framing input for messaging and UX prioritization, not as evidence-grade proof of the learning model.
- Why: the strongest signals are qualitative user pain patterns around friction, AI distrust, and accountability needs; those help shape positioning but do not validate causal learning claims.
- Evidence basis: indirect market/user synthesis from the "AI Platform Research for Students" PDF, combined with existing product doctrine around generation-before-recognition and truthful graph progression.

### 2026-04-02

- Decision: add AI value and risk language to product doctrine, but classify most AI-product efficacy claims as indirect or speculative until stronger evidence notes are built.
- Why: the product needs clearer guidance on desirable AI support patterns without overstating what the current evidence base proves.
- Evidence basis: direct support for retrieval-centered learning, indirect support for post-attempt feedback and scaffolding, and currently incomplete evidence for AI-specific outcome claims.
