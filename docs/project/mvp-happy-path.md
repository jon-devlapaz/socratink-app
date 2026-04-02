# MVP Happy Path

Purpose: current end-to-end tester flow for the MVP branch.

Read this when:

- validating whether the current MVP is healthy enough for sharing
- running manual smoke tests
- checking what "working" means right now for testers

Read these first if you need deeper context:

- [project/state.md](state.md)
- [product/progressive-disclosure.md](../product/progressive-disclosure.md)
- [drill/graph-invariants.md](../drill/graph-invariants.md)

This document describes the intended end-to-end flow for today's MVP tester share.

It is not the full future-state product spec.

It is the concrete "what should work right now" path for manual testing and bug reporting.

## Goal

A tester should be able to:

1. add a concept
2. extract a knowledge map
3. open the graph
4. start a drill on the core thesis or a subnode
5. complete at least one drill cycle
6. see the graph update without crashing
7. refresh confidence that drill outcomes are reflected in the graph state

## Current Product Truth

The graph is an epistemic map, not a progress tracker.

That means:

- `locked` = not yet available
- `drilled` = attempted but not solid
- `solidified` = verified understanding

The graph should update based on structured drill results, not hidden `[SYSTEM_ACTION]` payloads.

This document is intentionally operational.
It should not become the source of truth for UX philosophy or low-level drill invariants.

## Happy Path: Manual Test

### 1. Start The App

Run:

```bash
uvicorn main:app --reload
```

Open:

```text
http://localhost:8000
```

### 2. Configure API Access

Open Settings and add a valid Gemini API key.

Expected result:

- extraction requests can succeed
- drill requests can succeed

### 3. Create A Concept

Use the drawer flow:

- paste source text or upload a supported file
- enter a concept name
- create the concept

Expected result:

- concept is created in `growing`
- content preview is stored
- the concept appears in the sidebar/grid

### 4. Extract The Knowledge Map

Run extraction for the concept.

Expected result:

- `/api/extract` returns a knowledge map
- `concept.graphData` is populated
- map view becomes available

### 5. Open The Graph

Open the map view and switch to graph mode.

Expected result:

- graph renders without console errors
- core thesis node is visible
- clusters and subnodes render with current derived states
- graph should not crash when opening/closing quickly

### 6. Start A Drill

Preferred tester path for MVP:

- start drill from the core thesis first
- then try a visible subnode

Expected result:

- exactly one active drill node is highlighted
- drill title matches the node being drilled
- backend receives that node id as the drill target

### 7. Complete One Drill Cycle

Answer until the backend returns a `NEXT` response.

Expected result:

- the currently drilled node is the only node patched
- if classification is `solid`, that node becomes `solidified`
- if classification is non-solid, that node becomes `drilled`
- graph updates without a full remount
- drill panel remains open
- no Cytoscape teardown error appears in console

### 8. Verify Persistence During The Session

After the graph updates:

- click around the graph
- switch map modes
- reopen graph view if needed

Expected result:

- patched node state remains visible
- cluster state reflects subnode outcomes
- no state is lost on graph refresh/re-render inside the current browser session

## What Is In Scope Today

- structured drill response handling
- node-level graph updates from drill outcomes
- derived cluster state from subnode `drill_status`
- backbone and subnode drill persistence
- session fatigue guardrail
- retry/error handling for Gemini API failures

## Known MVP Limitations

These are known and acceptable for this tester share:

### 1. Mechanism Travels Over The Wire

The frontend still sends `node_mechanism` to `/api/drill`.

This is known design debt, not a surprise bug.

### 2. Session State Lives In Browser Memory

Refresh can interrupt continuity of the active drill session.

Persisted graph outcomes survive because they are patched into `concept.graphData`, but in-progress chat/session state does not fully persist.

### 3. Unlock Cascade Is Not Fully Built

The graph now reflects drill outcomes and derived cluster state, but the full downstream unlock cascade is still a follow-up slice.

For today's MVP, the main success criterion is:

- no crash
- truthful node state updates
- graph/drill lockstep

### 4. Legacy `SYSTEM_ACTION` Parsing Still Exists

The frontend still contains the old parsing path, but the new happy path should not depend on it.

## What Testers Should Report

Ask testers to report:

- which node they were drilling
- what they answered in plain language
- whether the graph updated
- whether the update matched their experience
- whether the app crashed or the graph disappeared
- any confusing mismatch between the active drill target and the highlighted graph node

## Failure Conditions

The MVP should be considered unhealthy if any of these occur:

- graph crashes when opening, closing, or updating
- drill result updates the wrong node
- graph changes but `concept.graphData` does not persist the change
- active drill highlight does not match the node being evaluated
- node becomes `solidified` on a non-solid classification
- backend returns success but the graph remains stale

## Minimum Demo Narrative

This is the shortest coherent demo:

1. Create concept
2. Extract map
3. Open graph
4. Start drill on core thesis
5. Get one `NEXT` result
6. Show node state update in graph
7. Start drill on a subnode
8. Get one more `NEXT` result
9. Show graph update without crash

If those nine steps work, the MVP is ready for external qualitative feedback.
