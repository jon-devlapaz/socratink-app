# socratink — Decision Principles

## Agent Summary

> **What this document is**: The tradeoff resolution framework for socratink. When a proposed feature, change, or priority creates tension between competing values, this document answers: which value wins? It codifies how the product trades off truth vs delight, what qualifies as real learner value, what makes a feature anti-cheat vs cheat-adjacent, when AI is support vs substitution, what MVP stabilization means in concrete terms, and the promotion gates a feature must pass before shipping.
>
> **When to read it**: Before making any decision where two good things conflict. Before scoping a feature. Before deciding whether to ship, delay, or cut something. Before arguing that a UX compromise is "acceptable."
>
> **What it is NOT**: It is not the UX design contract (read `ux-framework.md`), the strategic positioning (read `north-star.md`), or the current execution priorities (read `current-bets.md`).
>
> **Key decision rules an agent must follow**:
> - Truth wins over delight. Always. But the fix for "too hard" is better framing, not weaker truth.
> - If a feature doesn't require the learner to think in order to benefit from it, it is cheat-adjacent.
> - If the AI talks more than the learner during drill, the generation effect is compromised.
> - MVP stabilization has eight concrete conditions. All must be met before new features are added.
> - No feature ships without hosted (Vercel) verification. Local success does not count.

---

## How We Trade Off Truth Vs Delight

Truth wins. Always.

But truth and delight are not opposites. The product's job is to make truth *feel* magnetic — not to choose between an honest product and a fun product.

When they genuinely conflict:

- A feature that makes the product more fun but makes the graph less truthful is rejected.
- A feature that makes the graph more truthful but makes the product feel punitive needs a framing fix, not a truth compromise.
- The right response to "this feels too hard" is better attribution management, not easier mastery.
- The right response to "learners aren't returning" is better session endings and social normalization, not inflated progress signals.

The fluency trap is the specific failure mode: the conditions that feel easiest produce the worst long-term learning. Any decision that optimizes for immediate comfort at the cost of durable understanding is misaligned, even if engagement metrics improve.

## What Qualifies As Real Learner Value

A feature delivers real learner value if and only if it makes one of these things true:

1. The learner understands a mechanism they didn't understand before, and the graph reflects that truthfully.
2. The learner can enter the learning loop faster, with less setup friction, without skipping the cognitive work.
3. The learner can access the learning loop across more contexts (devices, modalities, reading levels, accessibility needs) without the mastery standard being lowered.
4. The learner gets more accurate feedback about what they actually know, not more flattering feedback.
5. The learner returns for spaced practice because the product earns it, not because loss aversion or streak anxiety compels it.

A feature that increases time-on-platform, session count, or activity volume without producing any of these five outcomes is not delivering learner value. It is delivering engagement theater.

## What Makes A Feature Anti-Cheat Vs Cheat-Adjacent

The test: does this feature make it easier to demonstrate genuine understanding, or does it make it easier to *appear* to understand without doing the cognitive work?

Anti-cheat features:

- Gating the study view behind the cold attempt (can't read the answer before trying)
- Requiring a minimum generative commitment before study unlocks (can't type "idk" and skip)
- Spacing the re-drill behind interleaved work (can't echo from buffer)
- Demanding multi-step causal reconstruction, not fact recall (can't pattern-match a keyword)
- Keeping the AI sparse during drill (can't passively absorb the AI's explanation)
- Enforcing the three-phase loop without skip (can't jump from locked to solidified)
- Varying the re-drill prompt angle across attempts (can't memorize one phrasing and reproduce it)

Cheat-adjacent features:

- Showing mechanism text for unattempted nodes (preview the answer key)
- Allowing immediate re-drill after study (test buffer, not memory)
- Accepting "I don't know" as sufficient to trigger the AI to explain (outsource generation)
- Celebrating activity or session completion as if it were mastery (fake the graph)
- Rich AI responses during drill that do the reconstruction work for the learner (passive trap)
- Awarding `solidified` after accumulated effort rather than demonstrated reconstruction (effort ≠ mastery)

When in doubt, ask: if a learner used this feature optimally, would they *have to think* to benefit from it? If no, it is cheat-adjacent.

## When AI Is Support Vs Substitution

AI is support when it:

- reduces the overhead around the learning loop (setup, authoring, scheduling, access)
- provides faster, more specific feedback after the learner has generated their attempt
- detects the learner's schema state and calibrates the difficulty of the cold attempt
- adapts the drill prompt to use the right Generative Learning Strategy for the material
- offers accessibility aids that let more learners participate in the same real task
- generates alternate explanations, analogies, or representations that help the learner return for another genuine attempt

AI is substitution when it:

- generates the mechanism explanation before the learner has attempted
- responds so verbosely that the learner shifts from generating to reading
- accepts "explain it to me" and complies without requiring a prior attempt
- provides enough information in its scaffold that the learner can reconstruct the answer from the AI's words rather than from their own memory
- produces a "correct" summary that the learner can parrot without understanding

The bright line: the learner must remain the primary generator of the target mechanism. If the AI talks more than the learner during a drill, the generation effect has been compromised.

## What "MVP Stabilization" Means In Practice

MVP stabilization means the following things are true before new features are added:

1. The three-phase loop works end to end: cold attempt → targeted study → spaced re-drill → truthful graph update.
2. The four-state model persists correctly: `locked → primed → drilled → solidified` with no invalid transitions.
3. Spacing validation prevents buffer-echo mastery: the frontend does not offer re-drill before the minimum spacing requirement is met.
4. The graph updates the correct node without crashing, tearing down Cytoscape, or losing state.
5. Hosted behavior on Vercel matches local behavior for the happy path.
6. The extraction pipeline produces valid knowledge maps from pasted text, uploaded files, and URL ingestion (with manual fallback for YouTube).
7. The session guardrails enforce: 25-minute time cap, 4-node cap, 3-retrieval-per-node ceiling.
8. Error handling for Gemini API failures does not expose internal errors to the learner.

New features are not added until all eight conditions are met and manually verified. Local success does not count as verification — hosted behavior must be confirmed.

## What Must Be Proven Before A Feature Gets Promoted

A feature moves from hypothesis to shipped when:

### From Idea → Spec

- The feature passes the 13-question evaluation checklist in `ux-framework.md`.
- The feature has an identified agent owner (usually elliot for spec, orchestrator for implementation).
- The feature does not violate the three-phase loop, the four-state model, or the attribution management contract.
- The feature does not create a new way to game the system without genuine cognitive effort.

### From Spec → Build

- The feature has a concrete implementation plan with identified persistence, routing, and UI changes.
- The feature has been evaluated for Vercel deployment behavior (not just local).
- If the feature touches AI evaluation or feedback, fairness, bias, and misclassification risks have been explicitly called out.
- If the feature touches reward or sensory feedback, it follows the inverted-U rule (moderate, success-dependent, calibrated to cognitive load).

### From Build → Ship

- The happy path works end to end on hosted.
- The feature does not break any of the eight MVP stabilization conditions.
- At least one manual test confirms the graph updates truthfully and the learner-facing state is correct.
- The feature does not introduce new cheat-adjacent behavior.

### From Ship → Permanent

- At least three real learners have used the feature without confusion or misattribution.
- The feature does not increase attrition among anxious or neurodivergent learners.
- The feature's sensory/reward treatment follows the inverted-U rule.
- The feature does not cause session deadlock for learners stuck on gating nodes.

Features that cannot demonstrate truthful graph behavior on hosted do not ship, regardless of how polished they are locally.
