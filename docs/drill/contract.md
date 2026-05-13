# socratink — Drill Contract

This document is the current binding drill contract.

Use it before changing drill state, drill-to-graph persistence, post-attempt mutation, study unlock behavior, or re-drill eligibility.

For graph-truth doctrine, read [../product/evidence-weighted-map.md](../product/evidence-weighted-map.md).
For the broader product contract, read [../product/spec.md](../product/spec.md).
For learner-facing post-phase UX, read [../product/post-drill-ux-spec.md](../product/post-drill-ux-spec.md).

## Core Loop

Every drillable node moves through the same three-phase loop:

1. cold attempt
2. targeted study
3. spaced re-drill

The loop is evidence-producing, not diagnostic. It records what Socratink has evidence for, not what the learner knows.

## State Meanings

### `locked`

- no substantive cold attempt is on record
- the node has not yet entered the loop

### `primed`

- a substantive cold attempt is on record
- targeted study is now unlocked
- no spaced reconstruction evidence is on record yet

### `drilled`

- a spaced re-drill occurred
- the reconstruction was non-solid
- the node remains return-worthy

### `solidified`

- a spaced re-drill occurred
- the reconstruction was solid
- this is recorded evidence, not a claim of permanent mastery

## Valid Mutations

The only valid node-state transitions are:

- `locked -> primed` after a substantive cold attempt
- `primed -> drilled` after a spaced re-drill with a non-solid outcome
- `primed -> solidified` after a spaced re-drill with a solid outcome
- `drilled -> solidified` after a later spaced re-drill with a solid outcome

The phase contract is:

- cold attempt completion unlocks study
- study completion prepares spaced re-drill eligibility
- only spaced re-drill may produce `drilled` or `solidified`

## Invalid Mutations

These transitions are out of contract:

- `locked -> drilled`
- `locked -> solidified`
- `primed -> solidified` without valid spacing
- any study-only or Repair Reps flow mutating graph truth
- any cold attempt mutating a node directly to `drilled` or `solidified`

## Cold Attempt Contract

Cold attempts are unscored.

That means:

- no learner-facing score
- no learner-facing classification
- no learner-facing tier or band
- no product claim that the learner was strong or weak

A cold attempt may record that the learner made a substantive attempt and may unlock study. It may not present itself as graded performance.

## Re-Drill Contract

Spaced re-drill is the only phase that may produce durable reconstruction evidence beyond `primed`.

- non-solid spaced re-drill may produce `drilled`
- solid spaced re-drill may produce `solidified`
- `solidified` must never come from reading, study, extraction, threshold capture, or Repair Reps

## Cluster Contract

Clusters are containers in MVP, not primary drill targets.

- graph truth lives on child or node-level evidence
- clusters may reflect downstream availability
- clusters must not become independent proof surfaces

## Known Live Drift

Current runtime evidence shows a known drift under investigation.

From `.qa-runs/browser-ground-truth/2026-05-13T13-36-47/`:

- a cold attempt appeared to patch backend/frontend state toward study
- the learner then saw study-phase copy
- but the map still appeared visually `locked` with `Try from memory ->`
- the cold-attempt copy also appeared to include scored praise language

Until that runtime behavior is resolved, this contract remains authoritative:

- substantive cold attempt should materialize visible `primed` truth
- study unlock must align with graph state
- cold attempts remain unscored
