# MVP Happy Path

Purpose: the narrow manual release gate for Socratink right now.

Use this document when:
- deciding if the current branch is healthy enough to merge
- running a manual smoke test
- asking what "working loop" means for the MVP

Read first:
- [project/state.md](state.md)
- [product/spec.md](../product/spec.md)
- [drill/engineering.md](../drill/engineering.md)
- `logs/drill-runs.jsonl`

## Release Gate

For this branch, a workable MVP means a freshly created concept with a clear causal structure supports this loop without obvious breaks:

1. Core Thesis cold attempt
2. Core Thesis study and return to map
3. Backbone cold attempt
4. Backbone study unlocks the cluster
5. Cluster exposes child drill rooms
6. Child cold attempt resolves cleanly
7. Original node can later re-drill after spacing/interleaving
8. Graph truthfully ends in `drilled` or `solidified`

## Manual Test

### 1. Start The App

Run:

```bash
bash scripts/dev.sh
```

`scripts/dev.sh` runs the local-auth preflight (`scripts/check-local-auth.py`) before starting Uvicorn, catching the common `.env` vs `.env.local` Supabase/session misconfiguration that would otherwise break guest sign-in mid-smoke.

Open:

```text
http://localhost:8000
```

### 2. Configure API Access

Open Settings and add a valid Gemini API key.

Expected:
- drill requests succeed
- no internal errors are exposed in the learner UI

### 3. Create Or Open A Test Concept

Create a concept from source material that should extract into a Core Thesis, backbone rooms, clusters, and child drill rooms, or open the curated Hermes Agent documentation concept from the Library. The previous multi-concept starter shelf has been removed while the Library model is being revamped.

Expected:
- graph loads without crashing
- Core Thesis is the first reachable room
- unreachable nodes are visibly ghosted, not deceptively clickable

### 4. Cold Attempt On Core Thesis

Start Core Thesis and give a real answer.

Expected:
- exactly one active drill target
- cold attempt is unscored
- successful completion moves Core Thesis to `primed`
- Targeted Study opens

### 5. Return From Core Thesis Study

Complete study and return to the graph.

Expected:
- stale drill transcript is gone
- next reachable branch is visible
- graph does not still offer Core Thesis as a fresh start

### 6. Cold Attempt On Backbone

Start the reachable backbone room and complete the cold attempt and study.

Expected:
- backbone becomes `primed`
- cluster opens after backbone study
- cluster itself is inspect-only in MVP

### 7. Enter The Cluster

Select the opened cluster.

Expected:
- the cluster explains that the drill happens in its child rooms
- child drill rooms are selectable
- the graph does not dead-end here

### 8. Cold Attempt On A Child Room

Start one child room such as `Temperature Comparison` or `Call For Heat`.

Expected:
- child room cold attempt resolves cleanly
- child room can enter study
- parent graph state stays truthful

### 9. Re-Drill Readiness

Return to an earlier room only after spacing and interleaving requirements are met.

Expected:
- premature re-drill is blocked with truthful copy
- eligible re-drill becomes available later
- a strong re-drill can end in `solidified`
- a non-solid re-drill ends in `drilled`

## Go / No-Go Criteria

Ship if all are true:
- no graph crash
- no CTA offers an impossible action
- no stale drill panel remains mounted after returning to map
- no cold attempt leaks a score or classification
- graph and side panel agree on node truth
- cluster unlock and child-room selection work

Do not ship if any occur:
- wrong node patched
- graph remains stale after a successful transition
- node jumps from `locked` straight to `drilled` or `solidified`
- re-drill is offered before spacing truth is satisfied
- cluster opens but child rooms cannot be selected

## Evidence To Capture

For each serious test run, keep:
- `logs/drill-runs.jsonl`
- any transcript logs that exist
- screenshots for UI contradictions
- a short note on where the loop felt false or blocked

Keep the release evidence with the branch:
- `logs/drill-runs.jsonl`
- any transcript logs that exist
- screenshots of contradictions
- a short merge note summarizing what passed or failed
