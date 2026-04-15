# socratink — Progressive Disclosure

## Agent Summary

> **What this document is**: The implementation-facing product spec for how the graph, drill system, and learner progression work together. This is the document an engineer reads before touching state, routing, persistence, or graph rendering code. It defines the four-state model, valid state transitions, persisted fields, phase tracking, spacing validation, routing rules, progression layers, session guardrails, and the target happy-path flow.
>
> **When to read it**: Before changing node state derivation, routing semantics, unlock logic, graph rendering, drill-to-graph persistence, or phase transitions. Before implementing any part of the three-phase loop.
>
> **What it is NOT**: It is not the UX philosophy (read `ux-framework.md`), the post-drill result-state spec (read `post-drill-ux-spec.md`), or the engineering invariants (read `../drill/engineering.md`).
>
> **Key implementation constraints an agent must follow**:
> - Four states: `locked → primed → drilled → solidified`. No other transitions are valid.
> - `primed` can only result from a cold attempt. `solidified` can only result from a spaced re-drill with `solid` classification.
> - Spacing validation: the frontend must not offer re-drill before `re_drill_eligible_after` has passed.
> - Cold attempts are unscored: `classification`, `score_eligible`, `response_tier` must be null/false.
> - Session guardrails: 25-min cap, 4-node cap, 3-retrieval-per-node ceiling.
> - Backward compatibility: existing nodes without new fields must default gracefully.

---

This is the implementation-facing product spec.
It should stay closer to current truth than to aspirational philosophy.

For enduring UX principles, read:

- [ux-framework.md](ux-framework.md)
- [post-drill-ux-spec.md](post-drill-ux-spec.md)

For hard engineering rules, read:

- [engineering.md](../drill/engineering.md)

## Product Model

The graph is a progressively revealed map of verified understanding.

The learner should not be flooded with the full conceptual structure at once.
They should earn clarity node by node through the three-phase loop: cold attempt, targeted study, spaced re-drill.

## State Model

The graph uses four learner-facing node states:

### `locked`

- not yet reachable
- prerequisites not yet satisfied

### `primed`

- cold attempt completed
- study view unlocked for this node
- not yet eligible for mastery verification
- the learner has entered the room but not yet faced the boss

### `drilled`

- spaced re-drill attempted but not solid
- should feel in-progress, not punitive
- worth revisiting

### `solidified`

- mechanism successfully reconstructed from long-term memory on a spaced re-drill
- verified understanding
- downstream unlock checks may now re-evaluate

These states are projected from persisted knowledge-map data, not invented separately by Cytoscape.

### State Transitions

The only valid transitions are:

- `locked` → `primed` (cold attempt completed)
- `primed` → `drilled` (spaced re-drill attempted, non-solid classification)
- `primed` → `solidified` (spaced re-drill attempted, solid classification)
- `drilled` → `solidified` (subsequent re-drill, solid classification)

Invalid transitions that must never occur:

- `locked` → `drilled` (skipping the cold attempt)
- `locked` → `solidified` (skipping both cold attempt and spaced re-drill)
- `primed` → `solidified` without spacing (buffer-echo mastery)
- `solidified` → `drilled` (mastery regression without re-drill evidence)

## Source Of Truth

The knowledge map is the system of record.

Drill outcomes are written into `concept.graphData`.
The graph is then derived from that data.

### Persisted Drill Fields

For subnodes:

- `drill_status` (locked | primed | drilled | solidified)
- `drill_phase` (cold_attempt | study | re_drill)
- `gap_type`
- `gap_description`
- `last_drilled`
- `cold_attempt_at` (timestamp of first cold attempt)
- `study_completed_at` (timestamp of targeted study completion)
- `re_drill_eligible_after` (earliest timestamp for valid spaced re-drill)

For backbone and core-thesis behavior:

- metadata is still used in parts of the current implementation

Clusters are derived, not directly persisted as drill targets.

### Phase Tracking

Each node tracks its current phase within the three-phase loop:

- `cold_attempt`: the node is in Phase 1. The learner has not yet attempted or has just completed the cold attempt.
- `study`: the node is in Phase 2. The cold attempt is complete and the study view is available.
- `re_drill`: the node is in Phase 3. Study is complete and the node is eligible for spaced re-drill (subject to spacing constraints).

The frontend uses `drill_phase` to determine which UI mode to present in the side panel.

## Three-Phase Node Loop

Every node moves through three phases. This section describes the implementation behavior. For the product rationale, read [ux-framework.md](ux-framework.md).

### Phase 1: Cold Attempt

Trigger: learner selects a `locked` or newly available node and begins drill.

Backend behavior:

- `drill_mode` is `cold_attempt`
- the drill prompt asks an open exploratory question, not a mechanism-evaluation question
- the cold attempt is explicitly unscored: no `classification`, no `gap_type`, no `response_tier` should be persisted from this phase
- if the AI detects zero schema (total inability to produce relevant vocabulary), it pivots to scaffolded mode: seeds foundational concepts, then asks for a micro-generation
- the AI enforces a minimum generative commitment: if the learner provides a non-attempt, the AI nudges once for elaboration before transitioning

Persistence on completion:

- `drill_status` → `primed`
- `drill_phase` → `study`
- `cold_attempt_at` → current timestamp
- no downstream unlock evaluation

### Phase 2: Targeted Study

Trigger: cold attempt completes. The study view opens automatically for the attempted node.

Frontend behavior:

- the study view shows the mechanism text for this specific node
- the study view is anchored to the learner's cold attempt: where possible, highlight where the attempt diverged from the mechanism
- the study view must not show mechanism text for other unattempted nodes
- a 2-3 second transition beat before the study view appears (ADHD micro-delay accommodation)

Persistence on completion:

- `study_completed_at` → current timestamp
- `re_drill_eligible_after` → `study_completed_at` + minimum spacing interval
- `drill_phase` → `re_drill`
- `drill_status` remains `primed`

### Phase 3: Spaced Re-Drill

Trigger: learner selects a `primed` node whose `re_drill_eligible_after` timestamp has passed, OR who has completed sufficient interleaved work on other nodes.

Spacing validation:

- preferred: 10-15 minutes of elapsed time since `study_completed_at`, with cognitively demanding interpolated activity in between
- minimum acceptable: 5 minutes of elapsed time with interpolated activity
- the frontend should not offer re-drill on a node whose spacing requirement has not been met
- interleaving cold attempts and study on other nodes is the primary spacing mechanism — the system should recommend the next cold attempt or study before offering a re-drill if spacing is insufficient

Backend behavior:

- `drill_mode` is `re_drill`
- the drill prompt demands multi-step causal reconstruction
- the prompt angle should vary across re-drill attempts on the same node (self-explanation, summarization, teaching, problem-posing) to prevent linguistic mimicry
- scoring, classification, and routing operate normally
- on repeated non-solid results for the same node across sessions, the AI escalates scaffolding per the Bottleneck Recovery contract in `ux-framework.md`

Persistence on `routing === "NEXT"`:

- if `classification === "solid"`: `drill_status` → `solidified`, clear gap metadata, allow downstream unlock evaluation
- if `classification !== "solid"`: `drill_status` → `drilled`, persist gap, do not treat as mastered

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
- during cold attempts, `classification` and `score_eligible` should be null/false

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
- the study view must not be accessible for nodes still in `locked` state
- scaffolds and feedback may clarify the gap after an attempt, but must not silently change the target
- AI-generated explanation quality does not itself mutate graph state
- only persisted drill outcomes from spaced re-drills should affect node, cluster, and unlock state
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

### `routing === "NEXT"` with `classification === "solid"` (spaced re-drill only)

- mark the current node `solidified`
- persist the result
- clear gap metadata on that node
- allow downstream unlock evaluation
- trigger strongest sensory celebration

### `routing === "NEXT"` with non-solid classification (spaced re-drill only)

- mark the current node `drilled`
- persist the gap
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
- backbone principles remain locked until the core thesis is solidified through a spaced re-drill

### Backbone

Backbone principles are the second layer after the core thesis.

- they frame the structure of each branch
- their state should be persisted
- each backbone independently unlocks its own dependent clusters

One branch can open while another remains unresolved.

### Clusters

Clusters are containers, not primary drill targets.

A cluster branch is available only when both are true:

- its governing backbone is solidified
- all incoming prerequisite clusters are already solidified

Cluster state is derived from subnode outcomes:

- all subnodes solidified → cluster `solidified`
- some subnodes primed or drilled but not all solidified → cluster `drilled`
- some subnodes have completed cold attempts → cluster `primed`
- no subnodes attempted → cluster `locked`

### Subnodes

Subnodes are the main drill units.

They are the smallest meaningful mechanisms the learner must reconstruct through the full three-phase loop.

## Re-Drill Behavior

Re-drill is normal, not edge behavior.

If a learner returns to a previously `drilled` node and gets `solid` on a spaced re-drill:

1. the node flips to `solidified`
2. cluster state is recomputed
3. unlock conditions are re-evaluated

This visible conversion is part of the product payoff.

Per-node retrieval ceiling: three successful retrievals of the same node in one session is the maximum. Beyond three, the system should halt drilling on that node and schedule it for a later session.

## Visual Intent

### Locked

- low-information
- reduced contrast
- clearly unavailable

### Primed

- warm, open state
- should signal "entered but not yet challenged"
- visually distinct from both locked and drilled

### Drilled

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

- Hard session cap: 25 minutes default.
- Node cap: 4 nodes per session.
- Per-node retrieval ceiling: 3 successful retrievals per node per session.
- Session ending should feel like a save point, not a punishment.
- End at a point of engagement, not exhaustion.

## Current Target Flow

The intended happy path is:

1. learner creates a concept
2. extraction produces a knowledge map
3. graph renders from `concept.graphData`
4. learner begins cold attempt on first available node (core thesis)
5. cold attempt completes → node becomes `primed`, study view opens
6. learner reads targeted study
7. system recommends next cold attempt on a different node (interleaving)
8. learner completes 1-2 more cold attempts + studies (buffer flush period)
9. system recommends spaced re-drill on the first node
10. backend returns structured drill result
11. frontend patches the node based on classification
12. graph re-renders from persisted state

## Out Of Scope For This Document

This document should not become:

- a full UX manifesto
- a manual test checklist
- a low-level code walkthrough

Keep those in:

- [ux-framework.md](ux-framework.md)
- [evaluation.md](../drill/evaluation.md)
- [mvp-happy-path.md](../project/mvp-happy-path.md)
