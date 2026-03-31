# Drill-Graph Invariants

This document is the context hub for any agent working on drill UX, graph UX, prompt logic, or drill-state persistence in LearnOps Theta.

Read this before changing:
- `public/js/app.js`
- `public/js/graph-view.js`
- `ai_service.py`
- any prompt or routing logic related to Stage 3 drill

The goal is to keep the Socratic drill and the graph in strict conceptual lockstep.

## Core Product Thesis

Theta is not a progress tracker.

Theta is an epistemic map.

The graph must represent what the learner has actually demonstrated they understand, not merely what they have clicked through, attempted, or spent time on.

If the graph advances when understanding has not been verified, the graph is lying.

That breaks the core product promise.

## Primary Metaphor

Treat the graph like a dungeon.

- Each graph node is a room.
- The active drill target is the room's boss.
- The learner must beat that boss before the room is considered cleared.
- A room can be entered without being cleared.
- New rooms unlock only when prerequisite rooms are truly cleared.

This metaphor should guide both UX and logic decisions.

If a proposed implementation makes the learner feel like they are fighting one boss while the map updates a different room, the implementation is wrong.

## Non-Negotiable Invariants

### 1. One Active Room At A Time

A drill session is always bound to exactly one graph node.

- The selected node is the current drill target.
- The backend evaluates that node only.
- The returned classification applies to that node only.
- The frontend patches that node only.

No silent target switching.

### 2. Drill And Graph Must Stay In Lockstep

At any given moment, these must all refer to the same node id:

- the highlighted graph node
- the active drill target
- the node being evaluated by the backend
- the node whose drill outcome is being persisted

If those drift apart, the learner loses trust in the system.

### 3. Session Routing Is Not The Same As Mastery

`routing === "NEXT"` means:

- move the conversation or session forward

It does **not** automatically mean:

- the learner understood the node
- the graph should unlock downstream content

Only verified understanding should unlock the map.

### 4. The Graph Must Tell The Truth

The graph is not a timeline of activity.

It is a map of verified understanding.

That means:

- a node may be attempted without being mastered
- a node may be revisited and later mastered
- unlocks must follow mastery, not mere exposure

## State Model

The graph should use three learner-facing node states:

### `locked`

Meaning:

- not yet available
- prerequisite understanding has not been established

Visual intent:

- obscured
- inaccessible
- low-information

### `drilled`

Meaning:

- the learner attempted this node
- the learner did not yet demonstrate solid understanding

Visual intent:

- warm, in-progress, return-worthy
- not punitive
- should not read as failure

Important:

- use a single base visual state
- do not force the learner to decode three gap colors on the map
- detailed gap information belongs in hover, click, or side-panel detail

### `solidified`

Meaning:

- the learner successfully reconstructed the mechanism
- this node is verified understanding

Visual intent:

- stable
- clear
- rewarding

## Backend Classification Semantics

The drill backend returns a classification:

- `solid`
- `shallow`
- `deep`
- `misconception`
- `null` only for init/opening moves or non-evaluative phases

Interpretation:

- `solid` = boss defeated
- `shallow` / `deep` / `misconception` = boss encountered, not defeated

## Routing-To-Graph Rules

These are the canonical rules for graph mutation:

### `routing === "NEXT"` and `classification === "solid"`

- mark the active node `solidified`
- persist the node's `drill_status = "solid"`
- clear gap metadata on that node
- check whether this completion unlocks downstream content

### `routing === "NEXT"` and classification is non-solid

- mark the active node `drilled`
- persist the node's non-solid `drill_status`
- persist `gap_type`
- persist `gap_description`
- do **not** unlock downstream nodes

This is a session advance, not a mastery advance.

### `routing === "PROBE"` or `routing === "SCAFFOLD"`

- no graph mutation
- keep the learner in the same room

### `routing === "SESSION_COMPLETE"`

- end or pause the session
- do not imply mastery unless the current node was already classified `solid`

## Knowledge Map As Source Of Truth

The knowledge map is the progression model.

Do not treat Cytoscape state as the authoritative record of learner understanding.

Persist drill outcomes into the knowledge map, then derive graph visuals from that data.

For subnodes, the relevant fields are:

- `drill_status`
- `gap_type`
- `gap_description`
- `last_drilled`

Current nested path:

- `concept.graphData.clusters[i].subnodes[j].drill_status`
- `concept.graphData.clusters[i].subnodes[j].gap_type`
- `concept.graphData.clusters[i].subnodes[j].gap_description`
- `concept.graphData.clusters[i].subnodes[j].last_drilled`

Patch by `node_id`, never by array position.

Do not assume extraction ordering is stable.

## Derived Cluster Logic

Clusters are containers, not direct drill targets.

Do not store cluster `drill_status` as source-of-truth state.

Derive cluster state from its subnodes:

- all subnodes solid -> cluster is `solidified`
- some subnodes attempted but not all solid -> cluster is `drilled`
- no subnodes attempted -> cluster is `locked`

This prevents sync problems and makes the graph a projection of the knowledge map.

## Unlock Logic

### Core Thesis

`core-thesis` is the absolute starting room.

- it is always the first intentional drill target
- backbone principles remain locked until `core-thesis` is solid
- the UI should make this obvious without explanatory text dumps

The graph should not imply that the learner can skip the core thesis and enter branches freely.

### Backbone / Core Thesis

Backbone principles are the second layer of progression, not the starting layer.

When a backbone principle is verified:

- dependent clusters can unlock

Important:

- each backbone independently unlocks its own `dependent_clusters`
- the learner does **not** need to solidify every backbone before any branch can open
- the learner does need to solidify the governing backbone before entering that branch

Backbone drilling exists to establish the structural foundation of each branch of the map.

### Cluster Progression

A cluster is not a primary drill target.

A cluster becomes available only when:

- its governing backbone branch is solid
- all incoming prerequisite clusters are already solidified

A cluster is considered cleared only when all of its subnodes are solid.

When a cluster becomes solidified:

- evaluate whether downstream clusters in `learning_prerequisites` should unlock

### Subnodes

Subnodes are the actual room bosses.

The learner drills subnodes, not clusters.

Subnode results roll up into cluster state.

## Re-Drill Cascade

A re-drill is not a special case.

If a previously `drilled` node later becomes `solid`, the full cascade must occur:

1. subnode transitions from `drilled` to `solidified`
2. cluster status is recomputed
3. if that was the last non-solid subnode, cluster becomes `solidified`
4. downstream prerequisite-gated content may unlock

This is one of the most important payoff moments in the product.

The learner should visibly feel:

"I came back, fixed a hole, and new territory opened."

## UX Philosophy

### The Graph Should Be Scannable

At a glance, the learner should be able to answer:

- what is still locked
- what I have attempted
- what I have truly mastered

If the graph requires decoding a legend before it is useful, the UX is too dense.

### Gap Detail Belongs In Interaction, Not Global Color Taxonomy

Use one visual `drilled` state.

Expose the difference between:

- shallow
- deep
- misconception

through:

- hover detail
- click detail
- side panel
- node metadata

Do not overload the graph itself with too many semantic colors.

### Avoid Shame Signals

Nodes that were attempted but not mastered should not look like failure states.

They should look like:

- in progress
- ready to revisit
- concrete next targets

Warm amber is better than warning red.

The learner should think:

"I've started this; I'll come back."

Not:

"I failed here."

## Current Accepted Design Debt

These issues are known and accepted for now:

### Mechanism Travels Over The Wire

The frontend currently sends `node_mechanism` to the backend on drill requests.

This exposes the answer key in browser state and the network payload.

Long-term fix:

- resolve the mechanism server-side from `knowledge_map` + `node_id`

### Session State Lives In Browser Memory

Current drill session continuity depends on in-memory frontend state.

A refresh can break continuity.

Long-term fix:

- add durable session persistence if needed

### Backbone Pruning Is Intentionally Broader

Backbone drill context currently keeps broader relationship/framework context than cluster drill context.

This is acceptable for now because backbone questions are structural.

If token cost becomes a problem, this is a likely optimization target.

## Implementation Guardrails

When editing drill or graph logic:

- do not let graph unlocks depend on `routing` alone
- do not let Cytoscape be the only source of state
- do not patch by positional array index
- do not let one node's result mutate a different node
- do not introduce visual semantics that imply mastery when classification was non-solid

## Quick Decision Tests

Before merging any drill-graph change, ask:

1. What exact node is being evaluated?
2. Where is that result persisted?
3. Does the graph state reflect mastery or mere activity?
4. If the learner refreshes or re-renders, does the truth survive?
5. If a learner returns to a flagged node and gets solid, does the unlock cascade happen?
6. Can the learner always tell what room they are in and whether they beat the boss?

If any answer is unclear, the implementation is not aligned yet.
