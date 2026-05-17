# socratink — Evidence-Weighted Map Doctrine

This document is the canonical doctrine for what the Socratink graph is and what it is allowed to claim. It is binding. When other docs conflict with this one on claims about the graph, evidence, or mastery, this doc wins.

For supporting context, read:

- [spec.md](spec.md) — binding product contract (three-phase loop, derived training state model)
- [/DESIGN.md](../../DESIGN.md) — canonical UX doctrine
- [progressive-disclosure.md](progressive-disclosure.md) — implementation-facing state and routing spec
- [starting-map-flow-artifact.md](starting-map-flow-artifact.md) — concept-entry storyboard that operationalizes this doctrine
- [../superpowers/specs/2026-05-15-drill-data-model-design.md](../superpowers/specs/2026-05-15-drill-data-model-design.md) — current binding drill data-model canon

---

## 1. Core Claim

**Socratink is not an AI tutor that claims to know what the learner knows. Socratink is an evidence-weighted map of understanding.**

- The graph does not show what the learner knows. It shows what Socratink has evidence for.
- The map starts as a hypothesis. It earns trust through learner-generated evidence.
- The starting map is an anchor, not a diagnostic.
- Your starting map shapes the route; it does not prove mastery.
- Study creates a repair opportunity. Re-drill provides evidence.
- Mastery requires spaced reconstruction, not reading.

Every surface and state in the product must preserve this doctrine.

---

## 2. The True Game Loop

```text
hypothesis -> attempt -> delta -> repair -> spacing -> proof -> trust
```

| Step | What happens | What the system may infer | Graph-truth change |
| --- | --- | --- | --- |
| hypothesis | Draft map proposed from source + starting-map anchor | routing emphasis, prompt shape | none |
| attempt | Learner exposes current model on a local node (cold attempt) | learner text, private classification, named gaps | training record append; derived `primed` or `needs repair` |
| delta | System surfaces where the attempt diverges from mechanism | gap emphasis for study | none |
| repair | Targeted study; optional Repair Reps practice | encoding opportunity, not mastery | none |
| spacing | Interleaved work on other nodes; elapsed time | re-drill eligibility | none (timers only) |
| proof | Spaced re-drill; multi-step causal reconstruction | classification of the attempt | `solidified` only from spaced strong reconstruction evidence |
| trust | Graph accumulates solidified evidence | durable, inspectable record | evidence-weighted map |

The loop is the product. Anything that lets the learner skip a step, or that mutates graph truth without proof, violates the doctrine.

---

## 3. Starting Map As Anchor, Not Diagnostic

Concept entry must onboard the learner into their own current model, not into the content. The concept page is not where the learner goes to read. It is where their current model becomes inspectable.

Without the anchor, cold attempt can feel like the product is saying, "You don't know this? Prove it." With the anchor, the same pedagogical move becomes collaborative: "Show me where you're starting from so the path has something to repair."

Rules:

- The starting-map threshold captures a global current model before recognition-heavy content appears.
- Threshold input may shape routing, prompt emphasis, fuzzy-area flags, and repair focus.
- Threshold input must not produce a learner-visible schema label (beginner/intermediate/advanced, "diagnosed level", "skill tier").
- Threshold input must not mutate graph truth. No node may gain training state from threshold capture alone.
- Confidence/fuzzy-area prompts are routing hints, not mastery evidence.

The first cold attempt is still the first evidence event. The starting map makes that event feel less like an exam and more like collaborative repair.

---

## 4. Proposed Structure vs Verified Learning State

Two different things live on the graph. Do not collapse them.

### Proposed structure
- What the extractor thinks the domain looks like.
- Derived from source material, starting map, and stated goal.
- Hypothesis only. Topology does not prove anything about the learner.

### Verified learning state
- What Socratink has evidence for about the learner's understanding.
- Encoded as per-node derived training state: `null`, `primed`, `needs repair`, `solidified`.
- Only spaced reconstruction can move a node to `solidified`.

The graph is the union of these two layers. The UI must never render them as the same thing.

---

## 5. Map Maturity Language

Use these names when talking about where a map sits in its lifecycle. These are product words, not new states.

| Name | Meaning | Produced by |
| --- | --- | --- |
| **Draft map** | Just extracted from source; no starting-map collision yet | Extraction |
| **Provisional map** | Starting-map anchor applied; routing shaped but no evidence | Starting-map capture |
| **Tested map** | Some nodes have learner reconstruction attempts on record | First cold attempts |
| **Repaired map** | At least one node has gone through attempt + study + repair | Targeted study / Repair Reps |
| **Verified map** | At least one node has moved to `solidified` through spaced re-drill | Spaced re-drill |

A map is never "complete." It accumulates evidence. Evidence can decay (re-drill may later yield a non-solid; `solidified` still holds until a re-drill explicitly contradicts it, per existing engineering rules).

---

## 6. App State vs Learner Capability Evidence

Two different state clocks run in this product. Keep them in different columns.

| App state (engineering) | Learner capability evidence (doctrine) |
| --- | --- |
| `null`, `primed`, `needs repair`, `solidified` | attempted, repaired, reconstructed |
| Driven by training records and spacing checks | Driven by the quality of the learner's own retrieval |
| Persistable, machine-checkable | Interpretive; only partially observable |

The persisted node states are the machine-readable projection of the capability evidence the system has seen. They are the best available estimate of what the learner can reconstruct — never a claim about the learner's mind.

Specifically:

- `primed` means "learner reconstruction evidence exists and the next action is not currently a durable repair state." It does not mean "the learner learned this."
- `needs repair` means "the latest evidence has named gaps to repair." It does not mean "the learner failed."
- `solidified` means "on at least one spaced reconstruction, the learner reconstructed the mechanism from long-term memory." It does not mean "the learner has mastered this forever."

---

## 7. Confidence / Evidence Language

When talking to the learner or to future agents, describe the graph in evidence terms.

Use:

- "The map starts as a hypothesis. It earns trust through learner-generated evidence."
- "The graph does not show what the learner knows. It shows what Socratink has evidence for."
- "Your starting map shapes the route; it does not prove mastery."
- "Study creates a repair opportunity. Re-drill provides evidence."
- "Mastery requires spaced reconstruction, not reading."
- "Solidified means the learner reconstructed the mechanism under spacing — not that they know it forever."

Avoid:

- "Socratink knows what you know."
- "The graph shows your understanding."
- "Diagnostic" (as a product capability)
- "Beginner / intermediate / advanced" labels on the learner
- "Completed means learned"
- "Study proves understanding"
- "The AI evaluated your current knowledge" as a standing claim

---

## 8. What The Graph May Claim

The graph may show:

- proposed structure for the domain
- suggested first node
- which nodes the learner has attempted (`primed`)
- which nodes have named gaps to repair (`needs repair`)
- which nodes the learner reconstructed solidly under spacing (`solidified`)
- traversal and unlock affordances derived from the above
- trajectory contrast *after* a re-drill resolves (e.g., "cold attempt: spark → re-drill: chain")
- draft / provisional / tested / repaired / verified map state in editorial copy

The graph may highlight the active node, dim others, and recommend an interleaving target.

---

## 9. What The Graph Must Never Claim

The graph must not say or imply:

- that the learner knows, understands, has mastered, or has completed any node based on topology alone
- that generation of the graph itself proves any learning
- that reading study content, dismissing study, or closing a panel equals mastery
- that a starting-map threshold produced a mastery claim
- that confidence ratings, fuzzy-area prompts, or self-assessed skill sliders are evidence of understanding
- that Repair Reps, self-ratings, or practice history produced `solidified`
- that `solidified` can be reached without a spaced re-drill returning a solid classification
- that a node can derive `solidified` without spaced strong reconstruction evidence
- that a rollback from `solidified` occurs without a contradicting re-drill
- learner-facing diagnostic categories ("beginner", "intermediate", "advanced", "misconception detected")

If the UI or copy ever makes a claim not in §8 and absent from §9, assume it is out of scope and treat it as a bug.

---

## 10. Relation To The Derived State Model

The doctrine preserves a four-outcome projection, but state is derived from the training record rather than stored as mutable graph truth.

| State | Doctrine meaning | Evidence basis |
| --- | --- | --- |
| `null` | No learner reconstruction attempt on record | no evidence |
| `primed` | Learner reconstruction evidence exists; study/repair/review routing is derived from it | attempt event that is not currently durable repair or solidified |
| `needs repair` | Current evidence has named gaps requiring repair | thin/wrong-direction or repeated non-strong evidence with gaps |
| `solidified` | Learner reconstructed the mechanism from long-term memory under spacing | spaced strong reconstruction evidence |

Engineering rules carry:

- no attempts derive `null`
- strong or partial attempts derive `primed` unless later evidence changes the fold
- thin or wrong-direction evidence can derive `needs repair`
- `solidified` requires spaced strong reconstruction evidence
- All other solidification claims are invalid.

`solidified` is the only graph-truth mutation that requires spaced reconstruction. Study completion, repair reps, self-ratings, and threshold capture must not mutate graph truth.

Study may mutate the learner. The study view may not mutate graph truth.

---

## 11. How Starting Map Flow Fits The Doctrine

[starting-map-flow-artifact.md](starting-map-flow-artifact.md) operationalizes this doctrine at concept entry. Reading it alongside this doctrine, the contract is:

- **Threshold capture** = hypothesis-shaping input. No graph mutation.
- **Provisional graph** = draft path. No graph mutation.
- **Locked study silhouette** = absence of explanatory content is intentional. No graph mutation.
- **First cold attempt** = the first evidence event. It appends learner reconstruction evidence and derives `primed` or `needs repair`.
- **Repair artifact (study)** = targeted corrective feedback. No graph mutation.
- **Interleaving bridge** = routing hint. No graph mutation.
- **Spaced re-drill** = the only step that may derive graph truth as `solidified`.

If a screen in that flow starts making mastery claims, it has left the doctrine.

---

## 12. MVP-Safe Version Of The Model

The full doctrine is large. The MVP must ship a credible subset without over-promising.

Required in MVP:

- The existing three-phase loop (cold attempt → targeted study → spaced re-drill) must preserve Generation Before Recognition.
- The derived training state model is authoritative for graph truth: `null | primed | needs repair | solidified`.
- The graph must show proposed structure and verified evidence using existing node state visuals.
- Cold attempts remain learner-facing unscored; private classification may drive honest repair/study routing.
- `solidified` can only result from spaced reconstruction.
- Study does not mutate graph truth.
- Repair Reps do not mutate graph truth.

Allowed in MVP, required later:

- A starting-map threshold screen that captures a global current model before any explanatory content appears. If not built yet, the existing cold-attempt-first entry still satisfies the doctrine as long as the entry is framed collaboratively, not diagnostically.
- Editorial copy on the graph page that uses "draft path" / "ready for first attempt" / "solidified through spaced reconstruction" language instead of completion/knowledge language.
- Trajectory contrast language that describes evidence accumulation, not mastery accrual.

Explicitly out of scope for MVP (but named so we do not drift):

- Learner-visible schema labels, skill tiers, or diagnostic categories.
- Cross-concept mastery summaries presented as knowledge claims.
- Any confidence input that produces a learner-facing "you know X" claim.
- Any path that lets study completion or threshold capture reach `solidified`.

---

## 13. Legacy Shorthand Replacement Table (Agent Reference)

These are soft-drift phrases that surface in this repo's older docs, UI copy, and agent transcripts. They are not always wrong, but they are the exact framings that slip into "graph shows understanding" if not anchored. When authoring or reviewing any learner-facing copy or binding doc, translate as follows.

| Legacy phrase (do not reuse) | First-principles replacement |
| --- | --- |
| "verified understanding" | "solid spaced reconstruction recorded" |
| "mastered" (as node claim) | "`solidified` — at least one solid spaced reconstruction is on record" |
| "cleared" (as knowledge claim) | UI shorthand only for the `solidified` record; never a knowledge claim |
| "proved it" / "proven" | "the learner produced reconstruction evidence Socratink recorded" |
| "real learning" (trajectory claim) | "stronger reconstruction evidence on record" |
| "completed the concept" / "completed" | "reached the current end of the recorded path"; mastery is not implied by completion |
| "progress" (as capability growth) | "evidence accumulation" or "records added to the map" |
| "possess the mechanism" / "already possess" | "Socratink already has solid reconstruction evidence for this node" |
| "you know X" / "the learner knows X" | "Socratink has evidence for X" |
| "Socratink evaluated your understanding" | "Socratink recorded and, when applicable, classified a reconstruction attempt under the drill rubric" |
| "understanding becomes inspectable" | "current model becomes inspectable" or "attempt evidence becomes inspectable" |
| "quality of understanding" | "quality of this reconstruction attempt" |
| "diagnostic" (as product capability) | "routing hint" or "anchor input" |
| "beginner / intermediate / advanced" (learner label) | do not use; replace with node-state language or remove |
| "primed means learned" | "`primed` means learner reconstruction evidence is on record; it is not a mastery claim" |
| "study proves understanding" | "study is a repair opportunity; it does not mutate graph truth" |
| "mastery regression" | contradicting re-drill evidence; state may change only under existing engineering rules |

Agents: when any of the left-column phrases appear in a PR diff, copy review, or proposed change, replace them or reject the change. The phrases are not individually catastrophic — they are load-bearing when they accumulate.

## 14. Binding Principles (Quick Reference)

- Generation Before Recognition is non-negotiable.
- Explanatory content must not appear before the learner exposes a current model or makes a local cold attempt.
- A generated graph is a provisional hypothesis, not verified knowledge.
- Prior-model capture can shape routing, prompt emphasis, and repair focus, but must not create mastery claims.
- Study is a repair artifact, not proof of understanding.
- The study view may mutate the learner, but it may not mutate graph truth.
- Only spaced reconstruction can derive graph truth as `solidified`.
- Do not collapse "attempted," "studied," "repaired," and "mastered."
- Preserve the derived training-state model: `null | primed | needs repair | solidified`.

If a feature violates any of these, the feature is misaligned.
