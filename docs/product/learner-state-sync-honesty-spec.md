# Learner-state sync honesty

```yaml
title: Learner-state sync honesty
date: 2026-07-14
status: accepted implementation spec
scope: signed-in learner state across local persistence and remote sync
priority: P1
```

## Product decision

`Signed in`, `saved locally` and `synced` are different claims. The interface
must not imply remote continuity when learner-state sync is unavailable.

Local persistence remains the immediate write path. Remote sync adds account
continuity; it does not decide whether a learner attempt exists in the current
browser.

## Production evidence

During authenticated production QA on 14 July 2026:

- learner-state GET returned 503 on load
- learner-state PUT returned 503 after session creation and learner events
- the interface continued to show the learner as signed in
- the new session survived reload in the same browser

This proves local persistence worked. It does not prove account sync or
cross-device recovery.

## Invariants

- Local save success and remote sync success have separate states.
- A sync failure must not roll back or hide a successful local save.
- A signed-in learner can see whether current work is local-only, syncing or
  synced.
- Sync retries are idempotent and must not duplicate attempts or overwrite
  newer local evidence.
- A remote snapshot must not replace newer local evidence without a defined
  merge result.
- Error copy must describe continuity, not blame the learner or claim data loss
  before it is known.

## Merge and concurrency contract

- Attempts and repairs are append-only evidence, merged by stable event ID.
- The same ID with the same material payload is one event and is deduplicated.
- The same ID with different learner text, node, classification or gaps is a
  sync conflict. Do not choose a copy by timestamp. Keep local evidence intact,
  leave remote state unchanged and retry only after reloading remote state.
- Distinct local and remote evidence IDs are unioned; neither side wins by
  whole-snapshot recency.
- `study_revealed_at` keeps the earliest valid timestamp because a later sync
  cannot make prior exposure un-happen.
- Concept presentation metadata may use the newer valid `updated_at` value,
  but it must not replace or delete training evidence.
- GET returns an opaque remote revision. PUT includes the revision it merged
  from. A stale revision returns 409 without writing, then the client fetches,
  merges and retries idempotently.

## Learner-visible states

| State | Required copy posture |
| --- | --- |
| local save pending | `Saving in this browser…` |
| local save complete, sync pending | `Saved in this browser. Syncing…` |
| local save complete, sync failed | `Saved in this browser. Not synced to your account.` |
| sync complete | quiet confirmation or no persistent warning |
| local save failed | block progression and keep the learner text editable |

The initial Taste Gate on 14 July 2026 accepted the failed-sync copy `Saved in
this browser. Not synced to your account.` and the action `Try syncing again`.
Show this state beside the settled learner action until sync succeeds, then
remove it. The distinction between local save and account sync is binding.

## Acceptance scenarios

### SH1 GET failure

Given a signed-in learner and remote GET 503, when the app loads, then local
state remains available and the UI does not claim it is synced.

### SH2 PUT failure

Given a successful local save and remote PUT 503, when the learner continues,
then the attempt remains available after reload and the UI reports local-only
continuity.

### SH3 Retry success

Given a pending local-only change, when a later sync succeeds, then the warning
clears and one copy of each learner event exists remotely.

### SH4 Concurrent state

Given local and remote state both advanced, when sync resumes, then the merge
unions distinct evidence IDs. A conflicting payload under the same ID or a
stale remote revision leaves the local state intact, writes nothing remotely
and retries only after a fresh GET.

### SH5 Local save failure

Given local persistence fails, when the learner submits, then Socratink keeps
the text visible, records no evidence and offers retry.

## Implementation boundary

Likely owners:

- `public/js/learner-state-sync.js`
- the local training-store serialization and merge helpers
- signed-in account and sync-status surfaces in `public/js/app.js`
- `/api/learner-state` revision handling in `main.py`
- `tests/test_learner_state_sync.py`, `tests/test_learner_state_api.py` and
  browser persistence tests

Do not redesign authentication, change the remote storage provider or add a new
sync engine in this slice.

## Required proof

- deterministic GET 503 and PUT 503 tests
- local reload persistence with remote sync disabled
- idempotent retry, append-only merge, conflicting-ID and stale-revision tests
- a signed-in browser proof showing local-only and synced states
- `bash scripts/doctor.sh` and targeted auth/session checks
