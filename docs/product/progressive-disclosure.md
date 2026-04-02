# Progressive Disclosure

Purpose: current-state product and progression spec for how the graph, drill system, and learner progression work together in the MVP.

Use this document when changing:

- node state derivation
- routing semantics
- unlock logic
- graph rendering logic
- drill-to-graph persistence behavior

This is the implementation-facing product spec.
It should stay closer to current truth than to aspirational philosophy.

For enduring UX principles, read:

- [ux-framework.md](ux-framework.md)

For hard engineering rules, read:

- [graph-invariants.md](../drill/graph-invariants.md)

## Product Model

The graph is a progressively revealed map of verified understanding.

The learner should not be flooded with the full conceptual structure at once.
They should earn clarity node by node.

## State Model

The graph uses three learner-facing node states:

### `locked`

- not yet reachable
- prerequisites not yet satisfied

### `drilled`

- attempted but not solid
- should feel in-progress, not punitive

### `solidified`

- mechanism successfully reconstructed
- verified understanding

These states are projected from persisted knowledge-map data, not invented separately by Cytoscape.

## Source Of Truth

The knowledge map is the system of record.

Drill outcomes are written into `concept.graphData`.
The graph is then derived from that data.

### Persisted Drill Fields

For subnodes:

- `drill_status`
- `gap_type`
- `gap_description`
- `last_drilled`

For backbone and core-thesis behavior:

- metadata is still used in parts of the current implementation

Clusters are derived, not directly persisted as drill targets.

## Drill Contract

The backend returns a structured drill result.

Important fields:

- `agent_response`
- `classification`
- `gap_description`
- `routing`
- `node_id`

Interpretation:

- `classification` describes the quality of understanding
- `routing` describes what the conversation should do next

These are not interchangeable.

## Routing Rules

### `routing === "PROBE"`

- stay on the same node
- no graph mutation

### `routing === "SCAFFOLD"`

- stay on the same node
- no graph mutation

### `routing === "NEXT"` with `classification === "solid"`

- mark the current node `solidified`
- persist the result
- clear gap metadata on that node
- allow downstream unlock evaluation

### `routing === "NEXT"` with non-solid classification

- mark the current node `drilled`
- persist the gap
- do not treat the node as mastered
- do not fake unlocks

### `routing === "SESSION_COMPLETE"`

- end or pause the session
- do not imply mastery by itself

## Progression Layers

### Core Thesis

The core thesis is the starting room.

- it is the first drill target
- backbone principles remain locked until the core thesis is solid

### Backbone

Backbone principles are the second layer after the core thesis.

- they frame the structure of each branch
- their state should be persisted
- each backbone independently unlocks its own dependent clusters

This means one branch can open while another remains unresolved.

### Clusters

Clusters are containers, not primary drill targets.

A cluster branch is available only when both are true:

- its governing backbone is solid
- all incoming prerequisite clusters are already solidified

Cluster state is derived from subnode outcomes:

- all subnodes solid -> cluster `solidified`
- some subnodes attempted but not all solid -> cluster `drilled`
- no subnodes attempted -> cluster `locked`

### Subnodes

Subnodes are the main drill units.

They are the smallest meaningful mechanisms the learner must reconstruct.

## Re-Drill Behavior

Re-drill is normal, not edge behavior.

If a learner returns to a previously `drilled` node and later gets `solid`:

1. the node flips to `solidified`
2. cluster state is recomputed
3. unlock conditions are re-evaluated

This visible conversion is part of the product payoff.

## Visual Intent

### Locked

- low-information
- reduced contrast
- clearly unavailable

### Drilled

- warm in-progress state
- should signal “come back here”
- should not read as failure

### Solidified

- stable
- rewarding
- clearly cleared

Detailed gap taxonomy belongs in the side panel or detail surfaces, not in a graph-wide legend.

## Current MVP Flow

Today, the intended happy path is:

1. learner creates a concept
2. extraction produces a knowledge map
3. graph renders from `concept.graphData`
4. learner drills exactly one active node
5. backend returns a structured drill result
6. frontend patches the active node only
7. graph re-renders from persisted state

## Out Of Scope For This Document

This document should not become:

- a full UX manifesto
- a manual test checklist
- a low-level code walkthrough

Keep those in:

- [ux-framework.md](ux-framework.md)
- [happy-path-evals.md](../drill/happy-path-evals.md)
- [mvp-happy-path.md](../project/mvp-happy-path.md)
