# Theta State

Last updated: 2026-04-11

## Current Evidence Posture

socratink's strongest science case is the code-verified loop of generation, correction, spacing, and retrieval. The learner first makes an unscored attempt, receives targeted corrective study, works other nodes so short-term fluency decays, then returns for effortful re-drill. The graph is an evidence-weighted map — it shows what Socratink has evidence for, not what the learner knows — and only marks mastery when a spaced, self-generated reconstruction is solid. See [../product/evidence-weighted-map.md](../product/evidence-weighted-map.md) for the binding doctrine.

The live product should be described as a retrieval-centered learning loop, not as a general AI tutor or a sleep-consolidation system. AI is a support layer for ingestion, routing, feedback, and friction reduction; it is not itself evidence that learning occurred.

## Verified Product Loop

Source of truth: Sherlock code audit of `public/js/app.js`, `public/js/graph-view.js`, `public/js/store.js`, `main.py`, and `ai_service.py`.

- Concept creation stores `graphData`; graph nodes begin mostly locked.
- Learner starts with the core thesis node, which is always the first available target.
- Cold attempt is open, exploratory, and unscored.
- Non-attempt or help request returns scaffold; the node stays locked.
- Substantive cold attempt makes the node `primed` and unlocks targeted study.
- Targeted study shows mechanism text; re-drill is gated by spacing plus interleaving.
- Traversal after `primed` is live behavior and should be understood as an interleaving device, not as mastery.
- Premature re-drill is blocked until both timer and interleaving conditions are satisfied.
- Spaced re-drill asks for causal reconstruction.
- Probe/scaffold during re-drill does not mutate node state; the backend caps probes at 3.
- Non-solid re-drill sets `drilled`, stores gap metadata, and applies backoff.
- Solid re-drill sets `solidified` and fires reward.
- `actualized` / hibernation is legacy or future-facing; it is not a live core loop path.

## Core Claim Ratings

### High Confidence

- Passive review and recognition-heavy study can create an illusion of competence that does not translate into durable retrieval.
  - Evidence basis: Dunlosky et al. 2013; Roediger and Karpicke 2006; broad retrieval-practice and spacing literature.

- Generation Before Recognition should remain a hard product constraint.
  - Evidence basis: testing effect, pretesting/generation effect, and prediction-error learning literature. Strongest product-relevant pattern is attempt first, corrective study second.

- Cold attempts are scientifically defensible when unscored and followed by corrective study.
  - Evidence basis: Kornell, Hays, and Bjork 2009; Richland, Kornell, and Kao 2009; Potts and Shanks 2014; Sinclair et al. 2021; Ketz, Morkonda, and O'Reilly 2013.

- Spaced retrieval is the right basis for `solidified`.
  - Evidence basis: Roediger and Karpicke 2006; Cepeda et al. 2006; Wing, Marsh, and Cabeza 2013; Dunlosky et al. 2013.

### Medium-High Confidence

- Immediate, specific feedback after a generation attempt is aligned with correction and misconception repair.
  - Evidence basis: Hattie and Timperley 2007; Butler and Roediger 2008; prediction-error and corrective-feedback literature.

- Targeted study should compare the learner's cold attempt against the correct mechanism when possible.
  - Evidence basis: corrective feedback after error, pretest-then-study effects, and comparison/analogical encoding research including Gentner and Loewenstein 2003. Product claim is strong directionally, but exact UI shape still needs product testing.

- Traversal after `primed`, before `solidified`, is preferable for spacing and interleaving.
  - Evidence basis: interleaving and spacing literature including Kornell and Bjork 2008, Dunlosky et al. 2013, Vlach and Sandhofer 2012, and Ebersbach et al. 2022. This supports movement to another node; it does not support saying the prerequisite is mastered.

- Non-solid re-drill should lead to gap repair plus delay, not immediate repeated retry loops.
  - Evidence basis: retrieval failure plus feedback can help, but spacing and repair matter. Code's `drilled` plus backoff direction is consistent with this; the UI must still make the next repair action clear.

### Medium Confidence

- Minimal scaffolding after a non-attempt is educationally sound if it preserves the cold-attempt demand.
  - Evidence basis: productive struggle and cognitive-load guidance, including Pasquale 2016, Baker 2023, Kalyuga 2007, and van Gog, Paas, and Sweller 2010. The scaffold should reduce entry friction, not reveal the mechanism.

- The graph can support orientation, relational encoding, and traversal.
  - Evidence basis: relational/compositional inference and analogical encoding literature, including Schwartenbeck et al. 2023 and Gentner and Loewenstein 2003. This is indirect evidence for graph navigation, not direct proof that this graph format improves learning.

- Sleep supports memory consolidation.
  - Evidence basis: Diekelmann and Born 2010; Rasch and Born 2013; Klinzing, Niethard, and Born 2019. This supports sleep-aware scheduling or messaging, not a hard `actualized` state in the live product.

### Low / Product Hypotheses

- The exact 5-minute re-drill delay is optimal.
- The exact 3-probe cap is optimal.
- Reward animation improves retention rather than only motivation.
- AI scoring is safe across phrasing, dialect, accessibility needs, and prompt conditions without a validation set.
- `actualized` / hibernation can be treated as a verified learning state.
- Graph topology alone can prove understanding.

## Phase Grounding

| Code phase | Neuroscience mechanism | Confidence | Product constraint |
| --- | --- | --- | --- |
| 1. Concept creation -> graphData | Orientation, relational framing, initial schema activation | Medium | Do not imply learning has occurred when a graph is generated. |
| 2. Core thesis selected first | Task focus and top-level schema anchoring | Medium | Make the target explicit, but keep it generative. |
| 3. Cold attempt | Pretesting, generation, prediction error | High | Keep unscored; do not show the answer before the attempt. |
| 4. Non-attempt -> scaffold | Load reduction and productive struggle support | Medium | Give minimal hints; node stays locked. |
| 5. Substantive attempt -> primed | Errorful generation followed by readiness for correction | High | `primed` means ready for study, not mastered. |
| 6. Targeted study | Corrective feedback and gap repair | Medium-high | Show the mechanism and, where possible, the attempt-vs-mechanism divergence. |
| 7. Traversal / interleaving | Interleaving, contextual variability, short-term fluency reduction | Medium-high | Unlock traversal after `primed`, but gate mastery claims on `solidified`. |
| 8. Spacing block | Distributed practice and retrieval spacing | High for spacing, medium for exact timer | Require elapsed time plus intervening work before re-drill. |
| 9. Spaced re-drill | Effortful retrieval and causal reconstruction | High | Score mastery only on spaced reconstruction, not exposure. |
| 10. Probe / scaffold in re-drill | Feedback-guided retrieval support | Medium | Keep probes sparse and gap-specific; avoid answer reveal. |
| 11. Non-solid -> drilled | Gap tagging, corrective repair, spaced retry | Medium-high | Store gap metadata and backoff; make the repair path visible. |
| 12. Solid -> solidified | Durable retrieval signal | High | `solidified` is the live mastery state. |

## Design Decisions From The Audit

- Treat the live core loop as cold attempt -> targeted study -> spaced re-drill.
- Treat node states as `locked -> primed -> drilled -> solidified`.
- Use `actualized` only as a legacy or future concept until the product has overnight retention evidence and a live implementation path.
- Resolve the docs conflict on traversal gates this way: traversal can unlock after `primed`; dependency or mastery claims require `solidified`.
- Add divergence highlighting to study when possible: "your attempt emphasized X; the mechanism turns on Y -> Z." This is a supported design direction, but the exact wording and UI need testing.
- Keep non-attempt scaffolds small. A good scaffold asks for a next micro-attempt; a bad scaffold reveals the mechanism.
- After non-solid re-drill, favor repair plus delay over immediate repeated retries. The implementation may set `drill_phase = null`, but the product must not hide the next gap-repair route.

## Product Language Rules

Use:

- "socratink uses generation, corrective study, spacing, and retrieval to make mastery claims harder to fake."
- "The graph does not show what the learner knows. It shows what Socratink has evidence for."
- "The map starts as a hypothesis. It earns trust through learner-generated evidence."
- "The starting map is an anchor, not a diagnostic."
- "`primed` means the learner has made a meaningful attempt and is ready for targeted study."
- "`solidified` means the learner produced a solid spaced reconstruction."

Avoid:

- "AI proves mastery."
- "Generated graphs mean understanding."
- "Socratink knows what you know."
- "The graph shows your understanding."
- "Diagnostic" as a product capability.
- Beginner/intermediate/advanced labels on the learner.
- "Primed means learned."
- "Study proves understanding."
- "Actualized means consolidated" unless and until a live sleep/retention gate exists.
- "The 5-minute interval is scientifically optimal."

## Open Scientific Questions

- What evaluation design is needed before AI scoring can be trusted across language, phrasing, dialect, and accessibility differences?
- Which exact feedback shapes best repair misconceptions without lowering the mastery bar?
- What spacing schedule is best for MVP constraints versus long-term retention?
- Which reward patterns support persistence without creating false progress signals?
- Does the product's specific graph topology improve transfer beyond serving as navigation and provenance?
- If `actualized` returns, what live retention measure justifies it: overnight delay, later retrieval, sleep self-report, or another consolidation proxy?

## Recent Decisions

### 2026-04-11

- Decision: upgrade the evidence posture for Generation Before Recognition, cold attempts followed by corrective study, and spaced retrieval to high confidence.
- Why: the code audit verified that the live loop centers on unscored generation, targeted study, interleaving/spacing, and scored re-drill. The research audit found strong support for that sequence from retrieval-practice, pretesting/generation, feedback, and spacing literature.

- Decision: treat traversal after `primed` as scientifically defensible and product-correct when framed as interleaving, not mastery.
- Why: spacing and interleaving evidence supports moving to another target before re-drill. The graph must still reserve mastery semantics for `solidified`.

- Decision: downgrade `actualized` / hibernation from core product claim to future hypothesis.
- Why: sleep consolidation has a strong neuroscience basis, but there is no live path from concept creation to `actualized` and no product evidence yet for a hard sleep-gated learning state.

- Decision: keep AI-evaluation claims low confidence until validated.
- Why: model scoring can be sensitive to expression, language, accessibility needs, and prompt conditions. The product needs human-labeled evaluation sets and bias checks before claiming reliable mastery classification.
