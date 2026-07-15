# Learner wait and recovery

```yaml
title: Learner wait and recovery
date: 2026-07-14
status: accepted implementation spec
scope: model-backed preparation, checking and study transitions
priority: P2
```

## Product decision

Model latency must not look like a frozen learner loop. Socratink must confirm
the learner action immediately, explain the current work and provide a safe
exit before uncertainty becomes abandonment.

Waiting states must not reveal study content, diagnose the attempt or mutate
graph truth.

## Production evidence

The first source-less question took about 28 seconds to become available during
production QA on 14 July 2026. During that time the interface showed
`Preparing your first question…` and disabled the reply, mic and submit
controls. It offered no progress detail, retry or return action.

Answer checking and route transitions also settled asynchronously. Immediate
DOM state was not always the final state.

## Timing contract

The 1.2-second answer-check cue already exists in the first-session contract.
The initial Taste Gate on 14 July 2026 accepted a 10-second return action and a
30-second retry action as the implementation defaults.

| Operation | Elapsed time | Required behaviour |
| --- | --- | --- |
| any learner submission | immediately | acknowledge the action and preserve learner text |
| answer checking | after 1.2 seconds | show `Answer received • Checking the link you wrote.` |
| prompt or route preparation | after 1.2 seconds | show a neutral pending explanation |
| prompt or route preparation | after 10 seconds | show that preparation is still active and offer `Return to map` |
| prompt or route preparation | after 30 seconds | offer an idempotent `Retry` and `Return to map` |
| any model-backed operation | terminal failure | show typed recovery copy and keep all learner-authored text |

Keep these thresholds as named constants covered by fake-timer tests. They are
elapsed-state cues, not progress estimates. A later production-latency review
may change the defaults without changing the state contract.

## Invariants

- Pending copy describes work, not learner ability or correctness.
- The learner's text remains visible throughout saving and checking.
- Retry reuses the same request identity unless the learner edits the answer.
- Navigation away from a pending request does not create evidence.
- A late response cannot overwrite a newer route, prompt or learner draft.
- `Return to map` invalidates the pending UI generation. A late result may be
  used only if the concept, route operation and generation token are still
  current; otherwise the client discards it without evidence mutation.
- Mic and tutor-voice controls clearly state when they are unavailable during a
  pending transition.

## Acceptance scenarios

### WR1 Slow first prompt

Given prompt preparation lasts 28 seconds, when the learner waits, then they see
the staged pending states and can return to the map without losing the Door
sketch.

### WR2 Retry in flight

Given the first request is still in flight, when the learner retries, then the
app reuses the operation identity, creates no second session or route and
renders at most one resulting route.

### WR3 Late response

Given the learner has moved to a newer route state, when an older response
arrives, then the app ignores it and preserves the newer state.

### WR4 Checking delay

Given answer evaluation exceeds 1.2 seconds, when the learner submits, then the
app shows neutral pending copy without exposing classification or study.

### WR5 Terminal failure

Given preparation or checking fails, when the request settles, then the learner
can retry or return and all authored text remains available.

## Implementation boundary

Likely owners:

- pending and request-state handling in `public/js/app.js`
- Drill Chamber status and completion controls
- request IDs and session-version checks in the source-less SEDA path

Do not add speculative progress percentages, background-job infrastructure or
a new notification system.

## Required proof

- fake-timer tests for 1.2-second, 10-second and 30-second states
- stale-response and idempotent-retry tests
- browser proof at desktop and 390 by 844
- one production-like delayed-response run
- `bash scripts/doctor.sh` and relevant frontend/e2e checks
