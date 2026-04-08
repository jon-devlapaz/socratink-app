# socratink — Drill & Graph Engineering

This document defines the hard engineering rules for keeping drill behavior, graph state, and persisted learner state in sync.

## Core Invariants

### 1. One Active Node At A Time
A drill session is always bound to exactly one node. The highlighted graph node, the active drill target, the backend evaluation, and the persisted result must all refer to the same `node_id`.

### 2. Derived Graph State
Cytoscape is a projection layer, not the system of record. Persist drill results into `concept.graphData` first, then derive graph state from that data.

### 3. Patch by `node_id`, Never Position
Always use stable node identifiers for patching. Extraction ordering is not guaranteed to be stable.

### 4. Derived Cluster State
Clusters are containers, not primary drill targets in MVP. Their state is derived from subnode outcomes:
- All subnodes solidified -> cluster `solidified`
- Some attempted (`primed` or `drilled`) -> cluster `primed` or `drilled`
- No attempts -> cluster `locked`

### 5. Unlocking Must Match Product Truth
There are two different unlock concepts and they must not be conflated:
- **Traversal unlock**: the next branch/container may open once the orienting parent room has been genuinely engaged. In the current MVP, a backbone room becoming `primed` can open its cluster.
- **Adjacent cluster traversal**: when one cluster depends on another, the next cluster may open once every child room in the prerequisite cluster has been genuinely worked (`primed`, `drilled`, or `solidified`). This preserves loop momentum without claiming mastery.
- **Mastery unlock**: mastery-gated progression only happens when the prerequisite room is genuinely `solidified`.

Do not write graph logic that uses mastery rules for basic branch opening, and do not write branch-opening logic that inflates mastery.

## Four-State Model Mutation Rules

| Action | State Change | Metadata Changes |
|---|---|---|
| Cold Attempt Complete | `locked` -> `primed` | `drill_phase = "study"`, `cold_attempt_at = now` |
| Study Complete | no state change (`primed`) | `drill_phase = "re_drill"`, `re_drill_eligible_after = now + 5m` |
| Re-Drill (Solid) | `primed` or `drilled` -> `solidified` | `drill_phase = null`, gap metadata cleared |
| Re-Drill (Non-Solid) | `primed` -> `drilled` | `drill_phase = "re_drill"`, gap metadata updated |

### Prohibited Mutations
- No graph mutation on `PROBE` or `SCAFFOLD`
- No `locked` -> `solidified`
- No scoring of cold attempts
- No re-drill if `re_drill_eligible_after` is in the future

## Pre-Change Checklist

Before shipping a drill or graph change, verify:
1. One active node remains clearly identified.
2. The backend evaluates that same node.
3. Only that node is patched on completion.
4. Non-solid completion does not masquerade as mastery.
5. Derived cluster state still matches subnode truth.
6. CTA affordances do not offer actions the routing layer will reject.
7. Graph re-rendering does not lose persisted state.
8. Local behavior matches hosted (Vercel) behavior for the change.
