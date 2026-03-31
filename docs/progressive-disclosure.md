# LearnOps Progressive Disclosure

## Purpose

This document defines the current MVP logic for how the knowledge graph, drill system, and learner progression fit together.

Use it when changing:

- `public/js/app.js`
- `public/js/graph-view.js`
- `ai_service.py`
- any prompt, routing, or unlock logic related to Stage 3 drill

This version is intentionally current-state and execution-focused.

It replaces the older hidden-payload model with the structured drill-response model now used by the app.

## Product Thesis

The graph is not a content browser.

It is not a completion checklist.

It is a progressively revealed map of verified understanding.

The learner should never be flooded with the entire conceptual structure at once.

They should earn clarity node by node.

## Core UX Principles

### 1. Progressive Disclosure Over Cognitive Dumping

The graph should reveal complexity gradually.

At first glance, the learner should see:

- a core thesis
- a bounded set of reachable concepts
- a clear sense of what is locked, in progress, and mastered

They should not need to parse a 50-node spiderweb to begin learning.

### 2. Generation Before Recognition

During drill, the learner should reconstruct the mechanism from memory.

The active drill node is a room boss.

The graph and the drill must stay locked to that same target until the cycle resolves.

### 3. The Graph Must Tell The Truth

The graph reflects epistemic state, not effort expenditure.

That means:

- attempted is not mastered
- session advance is not understanding
- only verified understanding should unlock downstream territory

## Current State Model

The graph uses three learner-facing states:

### `locked`

- not yet reachable
- prerequisites not yet satisfied

### `drilled`

- attempted but not solid
- should feel in-progress, not punitive

### `solidified`

- mechanism successfully reconstructed
- verified understanding

These states are projected from the knowledge map, not invented separately by Cytoscape.

## Source Of Truth

The knowledge map is the system of record.

Drill results are written into `concept.graphData`, then the graph is derived from that data.

For subnodes, the persisted fields are:

- `drill_status`
- `gap_type`
- `gap_description`
- `last_drilled`

Backbone/core-thesis drill metadata is currently stored under `metadata`.

Clusters are derived, not directly persisted as drill targets.

## Drill Contract

The backend returns a structured drill result.

The important fields are:

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
- recompute graph state
- allow downstream unlock logic to evaluate

### `routing === "NEXT"` with non-solid classification

- mark the current node `drilled`
- persist the gap
- do not pretend the node is mastered
- keep downstream gating honest

### `routing === "SESSION_COMPLETE"`

- end or pause the session
- do not imply mastery by itself

## Graph-Drill Lockstep

The graph highlight, the backend drill target, and the node being patched must always be the same node id.

That is a hard invariant.

If the learner cannot answer:

- what node am I drilling?
- what happened to that node?
- what changed in the graph because of that node?

then the UX is out of sync.

## Progression Model

### Core Thesis

The core thesis is the absolute starting room.

It is the first drill target because it establishes the top-level causal claim that the rest of the map depends on.

Until the core thesis is solid:

- backbone principles should remain locked
- the graph should communicate "start here" clearly

### Backbone

Backbone principles are the next progression layer after the core thesis.

Backbone understanding matters because it frames the rest of the map.

Backbone drill state should be visible and persisted, but it should not collapse the distinction between attempted and mastered.

Each backbone independently unlocks its own dependent clusters.

That means:

- `b1` solid -> clusters governed by `b1` can reveal
- `b2` can remain locked or unresolved without blocking the `b1` branch

This preserves meaningful branching without fake openness.

### Clusters

Clusters are containers, not the primary drill targets.

A cluster branch is available only when both are true:

- its governing backbone principle is solid
- all incoming prerequisite clusters are already solidified

Cluster status is derived from subnode outcomes:

- all subnodes solid -> cluster is `solidified`
- some subnodes attempted but not all solid -> cluster is `drilled`
- no subnodes attempted -> cluster is `locked`

### Subnodes

Subnodes are the true drill units.

They are the smallest meaningful mechanisms the learner must reconstruct.

Once a cluster branch is available, its subnodes become the drillable rooms inside that territory.

## Re-Drill Logic

Re-drill is core product behavior, not edge behavior.

If a learner returns to a previously `drilled` node and later gets `solid`:

1. the subnode flips to `solidified`
2. cluster status is recomputed
3. any newly satisfied unlock conditions should be evaluated

That visible conversion from "attempted" to "mastered" is part of the product payoff.

## Visual Design Intent

### Locked

- low-information
- inaccessible
- reduced contrast

### Drilled

- warm amber / in-progress tone
- should signal "come back here"
- should not read as error red or shame state

### Solidified

- confident, stable, rewarding
- should feel like a room has been cleared

Gap taxonomy belongs in detail surfaces, not in a complex graph-wide color legend.

The graph should be legible at a glance.

## Current MVP Architecture

Today, the happy path is:

1. learner creates concept
2. extraction produces knowledge map JSON
3. graph renders from `concept.graphData`
4. learner starts drill on a specific node
5. backend evaluates that node and returns structured output
6. frontend patches `concept.graphData`
7. graph syncs from the patched map without full remount

This is the correct MVP loop.

## Known MVP Limits

These are accepted for now:

### 1. Mechanism Over The Wire

The frontend still sends `node_mechanism` to the backend.

Long-term fix:

- resolve mechanism server-side from `knowledge_map` + `node_id`

### 2. Session State Is Not Fully Durable

Session continuity still depends partly on browser memory.

Graph outcomes persist through `graphData`, but active chat/session state is not fully durable across refresh.

### 3. Full Unlock Cascade Is Still Evolving

The graph now reflects drill outcomes honestly.

The complete downstream unlock cascade remains a follow-up implementation slice.

## YC-Ready Product Standard

When evaluating new changes, optimize for:

- clarity over cleverness
- truthful progress over gamified illusion
- fast learner comprehension over feature density
- visible state transitions over hidden magic

This product should feel:

- precise
- legible
- trustworthy
- momentum-building

Not:

- mysterious
- overloaded
- over-animated
- fake-progress-driven

## Quick Review Checklist

Before merging drill or graph changes, ask:

1. What exact node is being drilled?
2. Where is that result persisted?
3. Does the graph reflect understanding or just activity?
4. Can the learner tell what is locked, attempted, and mastered at a glance?
5. Will the graph still tell the truth after a re-render?
6. Does this change preserve drill-graph lockstep?

If not, the implementation is not aligned with the product.
