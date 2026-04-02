# Graph Traversal

Purpose: define how the learner moves between drill targets on the knowledge graph without violating truthful progression, generation-before-recognition, or the current MVP state model.

Use this document when changing:

- post-drill "what next" behavior
- route recommendation logic
- branch progression and return-path behavior
- graph travel UI language

Read these first for neighboring constraints:

- [ux-framework.md](ux-framework.md)
- [progressive-disclosure.md](progressive-disclosure.md)
- [graph-invariants.md](../drill/graph-invariants.md)

This document is a current-state product spec.
It should stay implementation-facing and MVP-calibrated.

## What "Route" Means

In this repo, "route" can refer to three different layers.
They must not be collapsed into one concept.

### 1. In-Node Routing

This is the conversation flow inside a single drill:

- `PROBE`
- `SCAFFOLD`
- `NEXT`
- `SESSION_COMPLETE`

This routing is node-local.
It does not decide graph travel by itself.

### 2. Session Traversal

This is the learner's next graph target after a drill resolves.

Examples:

- continue deeper in the current branch
- revisit an earlier unresolved node
- enter a newly unlocked branch

### 3. Return Scheduling

This is the later resurfacing of previously `drilled` nodes for repair and consolidation.

This layer should influence recommendations.
It should not silently override the active drill target.

## Core Traversal Principle

Traversal should make the next truthful cognitive move obvious.

That means:

- one active node at a time
- no silent target switching
- no fake unlocks from weak answers
- no graph travel that acts like a content browser

The graph is an epistemic map, not a free-roam syllabus.

## Route Types

The MVP should support four route types.

### `repair`

Return to a previously attempted node that is still `drilled`.

Use when:

- the learner left a node unresolved
- the graph needs to surface unfinished understanding honestly
- the product wants to convert an old weak point into visible mastery later

This is a normal path, not remediation-only edge behavior.

### `advance`

Move deeper within the learner's current unlocked branch.

Use when:

- the current node just became `solidified`
- a downstream subnode is already valid under current unlock rules
- continuing forward keeps the current conceptual thread coherent

### `return`

Surface an older `drilled` node because it is due for revisiting.

Use when:

- unresolved nodes are accumulating
- the learner has recently advanced and now benefits from a spaced reattempt
- the route reinforces truthful retention rather than one-pass clearing

`return` differs from `repair` only in timing.
`repair` is the unresolved state itself.
`return` is the system surfacing that unresolved state later as the next best move.

### `branch`

Enter a newly unlocked area of the graph.

Use when:

- the dependency chain is actually satisfied
- the learner has earned meaningful new territory
- the move expands the map truthfully rather than adding novelty for its own sake

Branch entry is a reward for verified understanding, not for activity.

## Route Selection Policy

After a drill resolves with `routing === "NEXT"`, choose the next recommended route using this priority order.

### Rule 1: Non-Solid Results Do Not Advance Territory

If the node resolves as non-solid:

- persist it as `drilled`
- do not unlock downstream territory from that result
- keep it eligible for future `repair` and `return`

The learner may still end the session or choose another already-available node.
The system must not present this result as a cleared path.

### Rule 2: Clean Solid Results Prefer Local Continuity

If the node becomes `solidified` and there is a valid next subnode in the same unlocked branch:

- recommend `advance` first

This preserves momentum and keeps the learner oriented inside the current branch.

### Rule 3: Unresolved Debt Must Reappear

If reachable `drilled` nodes exist, at least one should remain visible as a high-value next move.

That recommendation is a `return` route.

This keeps unresolved understanding present in the product without making it punitive.

### Rule 4: Branch Expansion Comes After Truth, Not Before It

Recommend `branch` only when:

- the governing backbone is `solidified`
- prerequisite clusters are satisfied
- the newly available territory is genuinely unlocked by current graph truth

Do not use branch expansion as consolation or generic encouragement.

### Rule 5: Never Autopilot The Learner To Another Node

The system may recommend a route.
It must not silently retarget the drill.

At all times, the chosen node must remain explicit before the next drill begins.

## Default Recommendation Order

For MVP, the default recommendation heuristic should be:

1. prefer `advance` after a clean `solidified` result
2. otherwise prefer a due `return` to a reachable `drilled` node
3. otherwise offer `branch` if new territory is truly unlocked
4. otherwise stay idle and let the learner choose from already reachable nodes

In plain terms:

- depth first
- then repair unresolved understanding
- then expand territory

## UI Contract

The post-drill surface should recommend routes, not expose the whole graph as a navigation menu.

Preferred actions:

- `Continue current path`
- `Revisit weak point`
- `Enter newly unlocked area`

Guidelines:

- show only valid actions
- keep the action count small, usually 1 to 3
- name the target node clearly before starting the next drill
- never reveal answer-rich mechanism text in the route chooser

The graph may orient the learner.
It must not collapse into a cheat sheet or open-world browser.

## State Model Implications

Traversal must stay downstream of persisted graph truth.

That means:

- route suggestions read from persisted node state
- route suggestions do not invent mastery
- cluster availability remains derived from node outcomes
- traversal logic never patches graph truth on its own

The graph remains a projection of the knowledge map.
Traversal chooses among truthful next moves inside that projection.

## MVP Boundaries

This document does not introduce:

- autonomous drill retargeting
- decorative reward paths
- comparison-based hopping as a default traversal mode
- broad exploration menus
- unlocks based on time spent or session completion

Those may be explored later, but they are not part of the current MVP traversal model.

## Evidence Posture

This section is intentionally calibrated to the current state of the repo's research notes.

### Directly Supported

- retrieval practice supports reconstruction-first drill rather than recognition-first browsing
- spaced return is more defensible than one-pass clearing for durable retention

### Indirectly Supported

- occasional contrastive movement between nearby concepts may help discrimination and transfer

### Still A Product Hypothesis

- a traversal rhythm of `advance -> return -> branch` will feel better and teach better than either strict linear progression or free roaming inside this specific product

Do not market the exact traversal policy as settled science.

## Open Questions

- how soon a `drilled` node becomes "due" for `return`
- whether backbone nodes should ever be recommended ahead of subnode repair debt
- whether contrastive sibling hops deserve a later, explicit route type
- how much route choice the learner should see before the graph starts to feel like a content browser

## Working Assumptions

This spec assumes:

- subnodes remain the primary drill targets
- clusters remain derived containers, not primary drill targets
- route recommendation is allowed, but silent retargeting is not
- truthful progression matters more than novelty or volume of available choices
