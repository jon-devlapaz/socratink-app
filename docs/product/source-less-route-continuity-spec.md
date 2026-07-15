# Source-less route continuity and evidence preservation

```yaml
title: Source-less route continuity and evidence preservation
date: 2026-07-14
status: accepted implementation spec
scope: source-less Door sessions from first prompt through route completion
priority: P1
```

## Product decision

Once Socratink tells a learner that an attempt is saved or recorded, the exact
learner text must survive navigation, reload, resume and route recovery.

A route-binding failure must not append evidence, discard a draft, move the
learner to another node or claim that work remains available when it cannot be
retrieved.

The concept-level route and a node-level SEDA case are different identities.
The route stays stable across the concept. Each SEDA case binds to exactly one
node on that route and may project evidence only for that node.

This contract is governed by
[`evidence-weighted-map.md`](evidence-weighted-map.md). It narrows the
source-less handoff rules in
[`first-session-momentum-spec.md`](first-session-momentum-spec.md) and
[`seda-ui-state-alignment.md`](../design/seda-ui-state-alignment.md).

## Production evidence

Chrome QA against `https://app.socratink.ai` on 14 July 2026 reproduced this
sequence:

1. A signed-in learner created a source-less session.
2. The first reconstruction, verdict and study comparison completed.
3. The learner continued to a second node, requested a cue and saved a draft.
4. The app showed `This learning route cannot be resumed. Your recorded work is
   still on the map.`
5. The console reported `Source-less route unavailable: bound_node_mismatch`
   from `loadOrCreateSedaResponse` through `submitInlineAttemptForEntry`.
6. Reload and resume reopened the second prompt with an empty composer. The
   second draft was not retrievable.

The first attempt remained available in Desk and Library. This proves local
partial persistence, not successful route continuity.

## Invariants

### Stable route identity

- A source-less concept binds to one versioned route.
- A SEDA session or case binds to one node on that route.
- Moving to another node creates or resumes a case explicitly bound to that
  node. It must not reuse the first node's case or regenerate the route.
- Recorded evidence freezes the route version, node, case and submission
  identity required to interpret that evidence.
- Recovery must not silently bind the session to a different node or route.
- A bound node mismatch is a typed recovery condition, not a generic dead end.

### Save means retrievable

- The UI may say `saved`, `recorded` or equivalent only after durable local
  persistence succeeds.
- The saved learner text must be retrievable by session, route and node ID.
- Reload and resume must restore the same draft or recorded attempt.
- Desk, Library and the active room must project the same evidence.
- Text awaiting validation or persistence is a pending draft, not training
  evidence. The interface may say it is kept in this browser, but not recorded.

### Fail before mutation

- Validate route, session and node identity before appending learner evidence.
- A failed validation leaves the draft in the composer and appends no attempt,
  repair, study or graph-truth event.
- The learner can retry against the recovered route or return to the map with
  the draft still available.
- Do not show `Your recorded work is still on the map` unless the work can be
  reopened from the map.

### Idempotent continuation

- Retrying the same save reuses the submission identity.
- A successful retry records one attempt.
- Repeated clicks, transport retries and reload recovery must not duplicate
  evidence.

## Learner-visible states

| State | Required surface |
| --- | --- |
| route ready | current prompt, enabled composer and stable node context |
| saving | learner text remains visible; controls prevent duplicate submission |
| next-node case starting | selected node and draft remain visible; no first-node case reuse |
| recoverable mismatch | draft remains visible; `Retry` and `Return to map` are available |
| unrecoverable mismatch with no evidence | preserve the Door sketch and offer a fresh route |
| unrecoverable mismatch with evidence | preserve recorded evidence and return to its bound node |

Internal reason strings such as `bound_node_mismatch` must not appear in
learner-facing copy.

The initial Taste Gate on 14 July 2026 accepted this recoverable-mismatch
surface:

- heading: `This answer was not recorded.`
- supporting text: `Your draft is still here. Earlier recorded work is unchanged.`
- actions: `Try this question again` and `Return to map`

The exact draft must be visibly restored before this copy appears. Retry may
recover the route and reopen the composer, but it must not silently submit the
draft. If the draft cannot be restored, the supporting text is false and must
not render.

## Acceptance scenarios

### RC1 Second-node continuation

Given a source-less route with one completed node, when the learner enters the
second node, then Socratink creates or resumes a case bound to that node. When
the learner saves a substantive reconstruction, Socratink records it exactly
once without changing the first node's evidence or replacing the route.

### RC2 Mismatch before save

Given the active node does not match the bound SEDA node, when the learner
submits a draft, then Socratink records no evidence, keeps the draft visible and
offers recovery.

### RC3 Reload after save

Given Socratink acknowledged a saved second-node attempt, when the page reloads
and the learner resumes the session, then the same attempt and route position
are restored.

### RC4 Duplicate submission

Given a save is in flight, when the learner retries or clicks again, then one
attempt exists after the request settles.

### RC5 Projection agreement

Given an attempt is recorded, when the learner opens Desk, Library and the
concept room, then all 3 surfaces show compatible evidence and next actions.

### RC6 Honest failure copy

Given recovery cannot continue, when Socratink returns the learner to the map,
then the UI names what was saved locally and does not claim missing work is
available.

## Implementation boundary

Likely owners:

- `public/js/app.js`: `submitInlineAttemptForEntry`, `loadOrCreateSedaResponse`
  and `routeUnavailableError`
- `public/js/seda-route-binding.js`: binding validation and typed failures
- `public/js/seda-evidence-projection.js`: idempotent evidence projection
- training-store and resume-state helpers used by Desk, Library and concept view

Do not change graph derivation, spacing rules, learner-facing mastery language
or route topology as part of this slice.

Do not fix the failure by mutating the concept-level bound node in place,
reusing the first node's SEDA case, deleting earlier evidence or generating a
replacement route. Keep route identity separate from the active node case.

## Required proof

- a focused regression test that completes the first node, enters the second
  node and reproduces `bound_node_mismatch` before the fix
- a contract test that proves the second node uses its own case while the route
  identity stays unchanged
- a browser test for launch, first comparison, second save, reload and resume
- an idempotency test for retrying the second save
- browser screenshots at desktop and 390 by 844
- `bash scripts/doctor.sh` and the relevant frontend/e2e gates
