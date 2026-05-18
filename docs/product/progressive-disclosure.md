# socratink — Progressive Disclosure

## Agent Summary

> **What this document is**: The implementation-facing product spec for how the graph, drill system, and learner progression work together. This is the document an engineer reads before touching state, routing, persistence, or graph rendering code. It now delegates the data-model contract to `docs/superpowers/specs/2026-05-15-drill-data-model-design.md` and summarizes how the live UI derives state from training evidence.
>
> **When to read it**: Before changing node state derivation, routing semantics, unlock logic, graph rendering, drill-to-graph persistence, or phase transitions. Before implementing any part of the three-phase loop.
>
> **What it is NOT**: It is not the UX doctrine (read `/DESIGN.md`), the post-drill result-state spec (read `post-drill-ux-spec.md`), or the binding drill data-model canon (read `../superpowers/specs/2026-05-15-drill-data-model-design.md`).
>
> **Key implementation constraints an agent must follow**:
> - Derived training states: `null | primed | needs repair | solidified`.
> - `solidified` can only result from spaced strong reconstruction evidence.
> - Study reveal and repair text are recorded in the training store but do not themselves solidify a node.
> - Cold attempts stay learner-facing unscored: do not show scores, tiers, or ability labels. Private classification may drive repair/study routing.
> - Session guardrails: duration, node-count, and per-node retrieval caps remain backend/doctrinal guardrails, but the current frontend MVP bypasses enforcement while inline reconstruction is validated.
> - Backward compatibility: existing nodes without new fields must default gracefully.

---

This is the implementation-facing product spec.
It should stay closer to current truth than to aspirational philosophy.

For the binding graph-truth doctrine, read:

- [evidence-weighted-map.md](evidence-weighted-map.md)

For enduring UX principles, read:

- [/DESIGN.md](../../DESIGN.md)
- [post-drill-ux-spec.md](post-drill-ux-spec.md)

For the current drill data-model contract, read:

- [../superpowers/specs/2026-05-15-drill-data-model-design.md](../superpowers/specs/2026-05-15-drill-data-model-design.md)

## Product Model

The graph is a progressively revealed, evidence-weighted map. It records what Socratink has evidence for — not what the learner knows. See [evidence-weighted-map.md](evidence-weighted-map.md) for the binding doctrine.

The learner advances node by node through the three-phase loop: cold attempt, targeted study, spaced re-drill. Each node state is derived from the training evidence record:

- `primed` derives from learner reconstruction evidence that is not yet solidified and not currently in persistent repair.
- `needs repair` derives from learner reconstruction evidence with named gaps requiring repair.
- `solidified` derives only from spaced strong reconstruction evidence.

No other path mutates graph truth. Study, Repair Reps, starting-map capture, and confidence ratings must not change node state.

## State Model

Each state is a render-time derivation from `socratink:training:v1:<conceptId>`. States describe what Socratink has on record for this node — not what the learner knows. See [evidence-weighted-map.md](evidence-weighted-map.md) for the binding doctrine.

### `null`

- no learner reconstruction attempt is recorded for this node
- UI may render the next available node as "ready to reconstruct" and blocked successors as "locked"

### `primed`

- learner reconstruction evidence is recorded
- next action may be study, repair, review, or spaced reconstruction depending on study reveal, classification, and spacing
- no mastery is implied

### `needs repair`

- current evidence contains named gaps that need repair
- return-worthy, not punitive

### `solidified`

- at least one solid spaced reconstruction is recorded
- downstream unlock checks may re-evaluate
- evidence event, not a mastery claim about the learner

These states are derived from browser-local training records, not invented separately by the rendering surface. The knowledge map remains the provisional structure and legacy compatibility surface until every view is rebound to the training derivation.

### State Transitions

The valid derivation rules are:

- no attempts → `null`
- strong or partial attempt → `primed`
- thin or wrong-direction first attempt → `needs repair`
- a single non-strong lapse after prior evidence → `primed`
- repeated non-strong evidence → `needs repair`
- strong attempt followed by another strong attempt after spacing → `solidified`

Invalid claims that must never occur:

- `solidified` without spaced strong reconstruction evidence
- study, reading, graph generation, sketch capture, or Repair Reps producing `solidified`
- Library rendering AI-generated `core_thesis` as learner reconstruction

## Source Of Truth

The provisional graph is the structure hypothesis. The training store is the
evidence system of record.

Drill outcomes are written into browser-local training records keyed as
`socratink:training:v1:<conceptId>`. The shipped rollout derives concept-page
entry state, next actions, inline reconstruction, study reveal, and repair
panels from those records. The Library card body uses the same records for
learner reconstruction text; Library badges, Desk tiles, Sidebar concept
markers, and Map/graph badges still use legacy `concept.state` until the full
binding rollout lands.

### Persisted Drill Fields

For training records:

- concept provenance: `source_mode`, `grounding`, `source_ref`
- learner sketch: `{ text, at }`
- per-node attempts with `kind`, `user_text`, private `classification`, `gaps`, and `grader_version`
- per-node `study_revealed_at`
- per-node repair records

Clusters are derived, not directly persisted as drill targets.

Concept pages render source-less provenance from the training record: when
`source_mode === "source_less"`, show `Shaped from your launch attempt, not
verified against a source.` before the active entry block.

### Phase Tracking

Each node derives its next action within the three-phase loop:

- `cold_attempt`: no learner attempt is on record.
- `study`: an attempt exists and study has not been revealed.
- `repair`: current evidence has named gaps after study reveal.
- `review`: study has been revealed but spacing or evidence conditions do not yet support solidification.
- `spaced_attempt`: a new reconstruction attempt is available.

The frontend uses derived `next_action`, not persisted `drill_phase`, to choose the concept-page mode.

## Three-Phase Node Loop

Every node moves through three phases. This section describes the implementation behavior. For the product rationale, read [/DESIGN.md](../../DESIGN.md).

### Phase 1: Cold Attempt

Trigger: learner selects a ready-to-reconstruct node and begins drill.

Backend behavior:

- `drill_mode` is `cold_attempt`
- the drill prompt asks an open exploratory question, not a mechanism-evaluation question
- the cold attempt is learner-facing unscored: no score, tier, band, or ability label is shown
- private classification and named gaps may be stored to keep study/repair routing honest
- if the AI detects zero schema (total inability to produce relevant vocabulary), it pivots to scaffolded mode: seeds foundational concepts, then asks for a micro-generation
- the AI enforces a minimum generative commitment: if the learner provides a non-attempt, the AI nudges once for elaboration before transitioning

Persistence on completion:

- append an attempt to the node's training record
- derive the next action from the attempt classification and study reveal status
- no downstream mastery unlock evaluation

### Phase 2: Targeted Study

Trigger: cold attempt completes. The concept page offers `Compare with notes` for the attempted node; study is recorded only after that explicit reveal.

Frontend behavior:

- the study view shows the mechanism text for this specific node after the learner reveals it
- the study view is anchored to the learner's cold attempt: where possible, highlight where the attempt diverged from the mechanism
- once the learner focuses or types in the repair field, the revealed study note collapses behind a manual show/hide toggle so the learner writes from memory rather than copying visible mechanism text
- the study view must not show mechanism text for other unattempted nodes
- future treatment may add a 2-3 second transition beat before the study view appears; the shipped inline flow uses an explicit reveal CTA

Persistence on completion:

- `study_revealed_at` is recorded on the node's training record
- derived state remains evidence-based; study reveal alone cannot solidify a node

### Phase 3: Spaced Re-Drill

Trigger: learner selects a `primed` node whose spacing interval has passed.

Spacing validation:

- current runtime: fixed 18-hour elapsed interval after the latest strong attempt, with no interleaved-work check
- future scheduler intent: elapsed time after study reveal, with cognitively demanding interpolated activity in between
- the frontend should not offer a solidifying spaced attempt on a node whose current spacing requirement has not been met
- interleaving cold attempts and study on other nodes remains product intent for the future scheduler; it is not enforced by the shipped derivation

Backend behavior:

- `drill_mode` is `re_drill`
- the drill prompt demands multi-step causal reconstruction
- the prompt angle should vary across re-drill attempts on the same node (self-explanation, summarization, teaching, problem-posing) to prevent linguistic mimicry
- scoring, classification, and routing operate normally
- on repeated non-solid results for the same node across sessions, the AI escalates scaffolding per the Bottleneck Recovery contract in [`docs/design/socratink-ux.md`](../design/socratink-ux.md) §6

Persistence on a recordable reconstruction:

- append the learner's text, private classification, gaps, and grader version to the node's training record
- derive `solidified` only when the spaced strong-evidence rule is satisfied
- derive `needs repair` when named gaps persist
- do not treat non-solid evidence as mastery

## Drill Contract

The backend returns a structured drill result.

Important fields:

- `agent_response`
- `classification`
- `gap_description`
- `routing`
- `node_id`
- `answer_mode`
- `score_eligible`
- `response_tier`
- `response_band`

Interpretation:

- `classification` describes the quality of understanding
- `routing` describes what the conversation should do next
- `response_tier` and `response_band` describe the transient quality of the attempt for trajectory contrast display
- during cold attempts, classification may be stored privately for routing; learner-facing score/tier/band surfaces stay absent

These are not interchangeable.

### Classification Sufficiency

The `solid` classification answers one question: did the learner reconstruct the causal mechanism from long-term memory, in their own words, with the critical links intact?

Three conditions must all be satisfied:

1. **Causal chain, not vocabulary.** The learner connected the steps in the correct directional sequence. Right keywords with no causal links = not solid.
2. **Spacing was satisfied.** Structural precondition enforced before the re-drill fires. Not an AI judgment.
3. **The attempt was self-generated.** If the AI's scaffolding essentially walked the learner through the mechanism during this drill turn, the classification should reflect assisted generation, not independent reconstruction.

The classification rubric in the system prompt must be concrete: "Does the response contain (a) the initiating condition, (b) the causal transition, and (c) the resulting state? If all three are present and correctly linked, classify as solid."

The system should err toward false negatives. A slightly strict gate protects graph credibility better than a slightly loose one.

## AI Assistance Guardrails

AI support is allowed only if it preserves the three-phase loop, the drill contract, and graph truth.

That means:

- the learner must complete the cold attempt before the study view is shown
- the study view must not be accessible before a learner reconstruction attempt exists
- scaffolds and feedback may clarify the gap after an attempt, but must not silently change the target
- AI-generated explanation quality does not itself mutate graph state
- only persisted learner reconstruction evidence can derive `primed`, `needs repair`, or `solidified`. Study, Repair Reps, starting-map capture, confidence ratings, and AI scaffolding must not produce `solidified`.
- the AI must remain sparse during drill — if the AI talks more than the learner, the passive trap has been triggered
- the AI must detect zero-schema states and pivot to scaffolded generation

## Routing Rules

### `routing === "PROBE"`

- stay on the same node
- no graph mutation

### `routing === "SCAFFOLD"`

- stay on the same node
- no graph mutation
- may provide narrower help or alternate framing, but must not convert the interaction into answer exposure

### Recordable attempt with spaced strong reconstruction evidence

- append the attempt
- derive the current node as `solidified`
- allow downstream unlock evaluation
- trigger strongest sensory celebration

### Recordable attempt with non-solid evidence

- append the attempt and structured gaps
- derive `needs repair` when the gap evidence warrants it
- do not treat the node as mastered
- do not fake unlocks
- no sensory celebration — copy and framing handle affect
- use wise feedback: high standards + belief + specific next step

### `routing === "SESSION_COMPLETE"`

- end or pause the session
- do not imply mastery by itself
- frame as save point

## Progression Layers

### Core Thesis

The core thesis is the starting room.

- it is the first cold attempt target
- successor entries remain unavailable until their predecessors have learner reconstruction evidence; mastery-gated routes still require `solidified`

### Backbone

Backbone principles are the second layer after the core thesis.

- they frame the structure of each branch
- their learner evidence should be persisted; state is derived from training records
- each backbone independently unlocks its own dependent clusters

One branch can open while another remains unresolved.

### Clusters

Clusters are containers, not primary drill targets.

A cluster branch is available only when both are true:

- its governing backbone is solidified
- all incoming prerequisite clusters are already solidified

Cluster state is derived from subnode outcomes:

- all subnodes solidified → cluster derives `solidified`
- any subnode needs repair → cluster derives `needs repair`
- some subnodes have attempts but not all solidified → cluster derives `primed`
- no subnodes attempted → cluster derives no badge / unavailable state

### Subnodes

Subnodes are the main drill units.

They are the smallest meaningful mechanisms the learner must reconstruct through the full three-phase loop.

## Re-Drill Behavior

Re-drill is normal, not edge behavior.

If a learner repairs a `needs repair` node and later gets spaced strong evidence:

1. the node flips to `solidified`
2. cluster state is recomputed
3. unlock conditions are re-evaluated

This visible conversion is part of the product payoff.

Per-node retrieval ceiling: three successful retrievals of the same node in one session remains the intended backend/doctrinal maximum. The current frontend MVP bypasses this enforcement and should reintroduce it as a soft save-point once inline reconstruction behavior is settled.

## Visual Intent

### No Training Evidence

- low-information
- reduced contrast
- available only when predecessor evidence allows it; otherwise clearly unavailable

### Primed

- warm, open state
- should signal "entered but not yet challenged"
- visually distinct from both unavailable/no-evidence and needs-repair states

### Needs Repair

- warm in-progress state
- should signal "come back here"
- should not read as failure

### Solidified

- stable
- rewarding
- clearly cleared
- receives strongest sensory celebration on transition

Show next-horizon nodes (3-5 adjacent available items) rather than the entire remaining graph. Detailed gap taxonomy belongs in the side panel.

## Session Guardrails

- Hard wall-clock session cap: backend-configurable via `DRILL_SESSION_TIME_LIMIT_SECONDS`, but bypassed by the current frontend MVP.
- Node cap: 4 nodes per session remains the intended guardrail, currently bypassed by the frontend.
- Per-node retrieval ceiling: 3 successful retrievals per node per session remains the intended guardrail, currently bypassed by the frontend.
- Session ending should feel like a save point, not a punishment.
- End at a point of engagement, not exhaustion.

## Current Target Flow

The intended happy path is:

1. learner creates a concept
2. extraction produces a knowledge map
3. graph renders from `concept.graphData`; training evidence initializes under `socratink:training:v1:<conceptId>`
4. learner writes a reconstruction on the first available node
5. recordable attempt is stored; derived state and next action update; study can reveal
6. learner reads targeted study
7. system recommends next cold attempt on a different node (interleaving)
8. learner completes 1-2 more cold attempts + studies (buffer flush period)
9. system recommends spaced re-drill on the first node
10. backend returns structured drill result
11. frontend appends the attempt to the training store
12. concept page and Library reconstruction body re-render from training evidence; legacy Map/Desk badges continue to reflect `concept.state` until the full binding rollout

## Out Of Scope For This Document

This document should not become:

- a full UX manifesto
- a manual test checklist
- a low-level code walkthrough

Keep those in:

- [/DESIGN.md](../../DESIGN.md)
- [mvp-happy-path.md](../project/mvp-happy-path.md)
- [mvp-happy-path.md](../project/mvp-happy-path.md)
