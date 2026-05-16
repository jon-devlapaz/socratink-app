---
title: Drill Data Model Design — Module 1
date: 2026-05-15
status: binding canon (supersedes docs/drill/contract.md)
scope: module 1 of 5 (drill refactor); data shape + state contract only
audit: agents/_logs/drill-pair-session-2026-05-15.md
persona: agents/_templates/customer-persona-prompt.md
---

# Drill Data Model — Module 1

This is the binding canon for the drill data model. It replaces the prior
`docs/drill/contract.md` contract on every point of disagreement. The audit log at
`agents/_logs/drill-pair-session-2026-05-15.md` is the motivating evidence; the
customer-persona prompt at `agents/_templates/customer-persona-prompt.md` is the
register against which copy and state decisions are tested.

## What this document is for

The 2026-05-15 pair-walkthrough audit found three structural failures in the live
drill flow:

1. The grader is uncalibrated — `/api/drill` accepts mechanism-wrong cold attempts
   with praise register.
2. The Library renders AI polish (`graphData.metadata.core_thesis`) as user
   reconstruction under the headline _"what you've reconstructed."_
3. Three parallel state machines (`concept.state`, `graphData.metadata.drill_status`,
   density-derived labels) disagree across Map / Library / Desk views.

All three are different surface symptoms of the same underlying disease: the
system has multiple mutable sources of state, none of which is bound to user
evidence. The fixes layered on top of that disease will all drift unless the
disease itself is treated.

This spec treats the disease. It defines a single source of truth (an
append-only event log per concept), a single canonical state machine derived
from it, and a rendering contract that binds every view to that derivation. The
three audit failures become structurally impossible — not "fixed in code,"
structurally absent from the model.

Modules 2 through 5 (grader rewrite, view re-binding, outer-loop scheduler,
repair surface) all consume this spec as their data contract.

## Scope

In scope:

- Schema for concepts, entries, and the event log
- Canonical state machine and derivation function
- Event payload contracts (especially the grader's `chamber_closed` writeback)
- Rendering contract (what surfaces bind to which derived fields)
- Migration plan from legacy shape to v1
- Forward compatibility with Supabase-backed persistence (when that lands)

Out of scope (deferred to other modules):

- Concrete grader prompt and rubric (module 2)
- UI visual treatment of badge / composition / next_action (module 3)
- Spaced-repetition scheduling curve (module 4)
- Repair surface UI (module 5)
- Server-side persistence (deferred past minimum remarkable product)

## Principles (binding)

These are the values the schema enforces. Every design choice below traces back
to one of them.

- **Evidence-truth.** The system cannot claim a user has reconstructed
  something it doesn't have user-produced evidence of. State is a function of
  events; events are user-produced or grader-produced; no mutable state field
  exists for the system to lie with.
- **Silent surface.** Every visible element earns its keep. Untested concepts
  render no badge. Trajectory and "improvement" signals are not rendered.
- **Single source of truth.** One mutable surface per concept (the event log).
  All other fields are pure derivations. Cross-view drift is structurally
  impossible.
- **Verbatim user reconstruction.** Library and other "what you've reconstructed"
  surfaces bind exclusively to user-written text. AI-generated text is never
  rendered as user content under any circumstance.
- **AI as sparse evaluator, not learning owner.** AI may help produce the
  provisional map before evidence exists and may extract a grader hinge after
  the learner reconstructs. It does not own the learning event. Cold
  reconstruction is learner-authored; repair artifacts render stored evidence
  plus grader metadata; no surface may present an AI tutor exchange, AI polish,
  or AI confidence as proof that learning happened.
- **Sketch as historical record.** The sketch is the user's pre-AI thinking,
  frozen at the moment the first chamber opens. Iterative learning lives in
  the repair surface, not in sketch revisions.
- **No fabricated evidence.** When migrating legacy data, we keep what we have
  (sketches, source graphs) and reset what we cannot honestly synthesize
  (attempt history). The system never invents evidence to keep continuity.

## §1 — Schema

Per concept (lives inside the existing localStorage blob):

```ts
Concept {
  id: string
  name: string                          // user-typed, lowercase preserved
  created_at: timestamp
  schema_version: number                // 1 for the new shape; migration trigger

  source: { type, filename?, preview, … }   // unchanged; from /api/extract intake

  // Knowledge graph (unchanged shape from provisional_map)
  graph: {
    backbone: Node[]
    clusters: Cluster[]
    metadata: { core_thesis, architecture_type, source_title, … }
    //         core_thesis stays in the blob as a system-internal grader-context
    //         reference. It MUST NOT be rendered as "what you've reconstructed."
  }

  // The single source of truth for everything stateful.
  events: Event[]                       // append-only, ordered by `seq`
}

Entry {
  // Identity = node_id from the graph.
  // No `state` field stored. State is derived from events.
  node_id: string                       // stable across the concept's lifetime
  label: string
  mechanism?: string                    // canonical mechanism reference (for grader)
}

Event {
  seq: number                           // monotonic local counter, 0-indexed per concept
  client_event_id: uuid                 // idempotency key; dedupes on append
  type: EventType
  node_id: string | null                // null only for concept-level events
  at: timestamp
  payload: object                       // shape per type — defined in §3
}

type EventType =
  | 'sketch_saved'        // first commit of the user's pre-AI thinking (concept-level)
  | 'sketch_revised'      // edits AFTER sketch_saved, BEFORE any chamber_opened
  | 'chamber_opened'      // user committed to cold attempt on a given entry
  | 'chamber_turn'        // each turn the user or agent sends inside the chamber
  | 'chamber_closed'      // grader's verdict (load-bearing for derivation)
  | 'study_revealed'      // user opened study material after chamber close
  | 'repair_committed'    // user wrote their post-chamber reconstruction
```

### Invariants

- **`node_id` is stable across the concept's lifetime.** Any future re-extraction
  must produce an explicit id-mapping table OR be treated as creating a new
  concept with the old one archived. No silent regeneration.
- **`events` is append-only.** Past events are never mutated. Edits = new events.
- **`seq` is monotonic per concept.** A new event's `seq` must equal
  `concept.events.length`.
- **`client_event_id` is unique within the log.** The append function rejects
  duplicates, providing idempotency for network retries.
- **Derived fields are never stored.** `entry.state`, `concept.badge`,
  `concept.composition`, `entry.next_action`, etc. are computed at render time
  by pure functions over `events`.

### What disappears from the blob

After migration (§5), these legacy fields are deleted:

- `concept.state` (the old source-state)
- `graph.metadata.drill_status`, `drill_phase`, `gap_type`, `gap_description`,
  `re_drill_count`, `re_drill_band`, `cold_attempt_at`, `study_completed_at`,
  `re_drill_eligible_after`, `last_drilled`
- The same fields on individual graph nodes (`backbone[*]`, `clusters[*].subnodes[*]`)

`graph.metadata.core_thesis` is kept in the blob — it remains useful as
grader-context reference — but loses all rendering rights per §4.

## §2 — State derivation

Pedagogical state is **always a pure function over events filtered by `node_id`**,
evaluated at render time (with per-entry memoization on event append). State is
never persisted.

### Per-entry derivation — a strict left-fold over `chamber_closed` events

```ts
type StateRecord = {
  state:           null | 'primed' | 'needs repair' | 'solidified'
  failure_streak:  number                  // consecutive non-strong closes
  prior_close:     ChamberClosedEvent | null
}

initial = { state: null, failure_streak: 0, prior_close: null }

fold(rec, close):
  let next_state = match close.classification:
    | 'strong':
        if rec.prior_close == null                                       → 'primed'
        else if rec.prior_close.classification == 'strong'
                AND spacing_ok(rec.prior_close, close)                    → 'solidified'
        else                                                              → 'primed'

    | 'partial':                                                          → 'primed'

    | 'thin' | 'wrong_direction':
        if rec.failure_streak >= 1         → 'needs repair'
        else if rec.state == null          → 'needs repair'   // no grace on first-ever
        else                                → 'primed'         // single-lapse grace

  let next_streak = match close.classification:
    | 'strong'                → 0                       // resets
    | 'partial'               → rec.failure_streak      // preserves (closes the partial pump)
    | _                       → rec.failure_streak + 1  // increments

  return {
    state:          next_state,
    failure_streak: next_streak,
    prior_close:    close
  }

state(entry) = (fold over chamber_closed events for this node_id).state

spacing_ok(prior, current) = (current.at - prior.at) >= 18 hours
// 18h is a wall-clock placeholder. Module 4's scheduler will replace this with
// a real spaced-repetition curve. The threshold is not load-bearing for the
// data model.
```

### Per-concept aggregation

```ts
concept.composition = {
  untested:     count(entries where state == null),
  primed:       count(entries where state == 'primed'),
  needs_repair: count(entries where state == 'needs repair'),
  solidified:   count(entries where state == 'solidified'),
  total:        count(entries)
}

concept.badge:
  let non_null = total - untested
  | non_null == 0           → null                  // no badge rendered
  | needs_repair > 0        → 'needs repair'        // weakest-link, honest
  | primed > 0              → 'primed'
  | otherwise               → 'solidified'
```

The weakest-link aggregation reflects the persona's evidence-truth principle: a
concept with a known broken entry cannot claim solidification. Module 3 pairs
this canonical badge with a composition view ("9 of 10 solidified · 1 needs
repair") so progress is visible alongside the gap.

### Why this shape

| Concern | Resolution |
|---|---|
| Three parallel state machines | One source (events), one derivation. Drift impossible. |
| "Locked" lying about agency | Replaced with `null`; UI renders no badge. |
| Solidified earned without spacing | Requires `strong → 18h+ → strong`. |
| Solidified earned via lucky cold attempt | First chamber close maxes at `primed`. |
| Partial pump (alternating thin/partial parks at primed forever) | `partial` preserves `failure_streak` rather than resetting. |
| Stumble-to-solidify (partial prior + strong current) | Solidification requires a `strong` prior, not `partial`. |
| Single-lapse on primed crashes to needs_repair | Symmetric grace: one non-strong from `primed` or `solidified` lands on `primed`. Two-in-a-row drops to `needs repair`. |
| 24h wall-clock punishes morning studiers | 18h elapsed (UTC subtraction; no calendar/timezone gymnastics). |
| Healing-by-addition (new strong entry flips broken concept to primed) | Weakest-link aggregation. Adding strong does not heal broken. |
| Cross-client drift on concept badge | Canonical badge defined in schema, not delegated to UI. |
| Recursive history walk on each render | Pure left-fold, O(n) once, memoizable on event append. |

### Pedagogical-soundness check

- **No claim of mastery without evidence.** `state ≠ null` requires at least one
  `chamber_closed` event for that node_id. Reading study material does not
  move state.
- **Solidified is unreachable on a single chamber close.** Durability proof
  requires two strong closes 18h+ apart.
- **No "AI tutor" praise on thin answers.** §3's `chamber_closed` payload
  forbids the register by field shape (gaps are structured, not prose).
- **No streaks, no XP, no improvement badges.** Trajectory and failure_streak
  exist for derivation logic only; they are not part of the rendering contract.
- **Grader misclassification has secondary defense.** Even if the grader
  produces a false strong, the 18h gap is required for solidification.

## §3 — Event payload contracts

Each event type's payload schema, write trigger, cardinality, and invariants.
All events share the §1 envelope: `{seq, client_event_id, type, node_id, at, payload}`.

### `sketch_saved`

```ts
payload: {
  text: string                           // verbatim user input
  concept_name: string                   // user-typed concept name at time of save
  source_ref: SourceRef | null           // existing shape from /api/extract intake
}
```

- `node_id`: MUST be `null` (concept-level event — entries don't exist yet)
- Trigger: user clicks "Save sketch" on the sketch screen, BEFORE `/api/extract` runs
- Cardinality: exactly one per concept lifetime
- Invariant: must precede any `chamber_opened` event in this concept

### `sketch_revised`

```ts
payload: {
  text: string                           // new verbatim user input
  reason: 'typo' | 'rewrite' | 'unspecified'   // optional UI hint
}
```

- `node_id`: MUST be `null`
- Trigger: user edits sketch from the post-extract view, BEFORE any `chamber_opened` event
- Invariant: **rejected (no-op, returns error) if any `chamber_opened` event exists
  in the concept's log.** Sketch is frozen at first chamber open per the
  evidence-truth principle: the cold attempt is the user's pre-AI commitment.
- Cardinality: zero or more, all prior to first chamber_opened

### `chamber_opened`

```ts
payload: {
  entry_label: string                    // e.g. "Core Thesis" — frozen at time of open
  mechanism_ref: string | null           // canonical mechanism, if extract has one
}
```

- `node_id`: REQUIRED, references graph node
- Trigger: user clicks the entry CTA to begin a cold attempt
- Cardinality: one or more per node_id (re-attempts are new chambers)
- Invariant: must be preceded by `sketch_saved` (concept-level)
- Side effect: locks the concept's sketch from further `sketch_revised` events
- A new `chamber_opened` on a node implicitly supersedes any unclosed prior
  session on the same node. Orphaned (in-flight, never closed) sessions are
  ignored by derivation. Module 3 may surface "you have an open chamber" if it
  detects an orphan, but the data model treats them as inert.

### `chamber_turn`

```ts
payload: {
  turn_index: number                     // 0-indexed within the chamber session
  role: 'user' | 'agent'
  text: string                           // verbatim message content
  chamber_session_id: uuid               // groups turns within a single chamber
}
```

- `node_id`: REQUIRED, must match the open `chamber_opened` on this node
- Trigger: every Send Turn (user) and every agent response (agent) inside the chamber
- Cardinality: many per chamber session
- Invariant: every `chamber_turn` must occur within an open chamber on the same
  node — between a `chamber_opened` and its matching `chamber_closed` (matched
  via `chamber_session_id`)

### `chamber_closed`

This is the load-bearing event for state derivation and Library rendering. It is
written by `/api/drill` on the chamber-close turn. Module 2's grader rewrite
binds to this contract.

```ts
payload: {
  chamber_session_id: uuid                                // matches the opened session
  classification: 'strong' | 'partial' | 'thin' | 'wrong_direction'
  gaps: Array<{
    mechanism: string                                     // canonical mechanism name
    user_said: string | null                              // verbatim what user said, or null if omitted
    correction: string                                    // 1-sentence honest correction
  }>
  strongest_turn: {
    turn_index: number                                    // references an actual chamber_turn
    text: string                                          // VERBATIM user text — Library renders this
  }
  sketch_to_final_delta: 'none' | 'small' | 'meaningful' | null
  next_action: 'study' | 'repair' | 'solidify'            // CTA hint for module-3
  grader_version: string                                  // e.g. "drill-system-v2" — schema evolution
}
```

- `node_id`: REQUIRED, must match the `chamber_opened`
- Trigger: written by `/api/drill` when the grader decides to close the chamber
- Cardinality: exactly one per `chamber_session_id`
- Invariants:
  - `strongest_turn.turn_index` must reference an actual `chamber_turn` event
    with `role == 'user'` in the same session
  - `classification == 'strong'` requires `gaps.length <= 1` (a strong answer
    cannot have multiple named gaps)
  - `classification ∈ {'thin', 'wrong_direction'}` requires `gaps.length >= 1`
    (a thin/wrong answer must produce structured named gaps; praise prose is
    forbidden by field shape)
  - `gaps[i].user_said` is `null` only when the gap is an omission; truthy
    when the gap is a misstatement
  - `grader_version` is required — pinning lets us replay/audit when we change
    the grader prompt

### `study_revealed`

```ts
payload: {
  reveal_source: 'auto' | 'user_action'      // auto = post-chamber; user = manual reveal
  content_ref: string                        // pointer to the study material section
}
```

- `node_id`: REQUIRED (study is per-entry, never concept-wide)
- Trigger: study material rendered for the user after chamber close (auto) or
  via explicit user action (manual)
- Cardinality: one or more per node_id (re-reveals are fine)
- Invariants:
  - At least one `chamber_closed` must exist for this node_id
  - **MUST NOT** occur on a node_id with an open chamber (chamber_opened
    without a matching chamber_closed). Prevents the "peek at study material
    mid-chamber" exploit. Module 3 surfaces this as study-button-disabled while
    a chamber is open.

### `repair_committed`

```ts
payload: {
  text: string                           // verbatim user reconstruction
  gap_refs: string[]                     // optional: which chamber_closed.gaps[i].mechanism
                                         // strings this repair addresses
}
```

- `node_id`: REQUIRED
- Trigger: user submits their post-chamber reconstruction on the repair surface
  (built in module 5)
- Cardinality: zero or more per node_id
- Invariant: at least one `chamber_closed` must exist for this node_id
- Note: `repair_committed` is **inert to state derivation**. State only moves
  on `chamber_closed`. Repairs are preparation for the next chamber; they
  cannot be used to pump state by repeated commitment.

### Append-function contract

```ts
appendEvent(concept, event):
  if event.client_event_id already exists in concept.events:
    return ok (idempotent dedupe)
  if event.seq != concept.events.length:
    return error 'seq-mismatch'
  if event violates the per-type preceding-event or node_id rules:
    return error '<specific invariant violated>'
  concept.events.push(event)
  return ok
```

The append function is the only entry point for adding to the log. Direct
mutation of `events` is forbidden by code review and (where possible) by
type-system encapsulation.

## §4 — Rendering contract

Module 3 binds to this contract. The contract structurally prevents the audit's
Library gaslighting failure and cross-view drift bug.

### The rendering primitives

```ts
EntryRender {
  state:               null | 'primed' | 'needs repair' | 'solidified'   // null ⟺ untested
  strongest_turn_text: string | null
  gaps:                Gap[]
  next_action:         'cold_attempt' | 'study' | 'repair' | 'solidify' | 'review' | null
  solidify_unlocks_at: timestamp | null
  last_close_at:       timestamp | null
}

ConceptStatus { badge, composition }   // bundled — always travel together

ConceptRender {
  status:  ConceptStatus
  entries: EntryRender[]
}
```

There is no `lifecycle` field. `state == null` is the canonical signal for
"untested," and the absence of the field prevents illegal combinations like
`tested + state=null`.

### `next_action` derivation

`'solidify'` is offered only when the upcoming chamber can actually advance
state to `solidified` per §2. That requires both spacing AND that the latest
chamber close was classified `strong` — otherwise the §2 fold's
`prior_close.classification == 'strong'` check fails and the new chamber lands
in `primed` again. The renderer must not promise a state change the derivation
will not deliver.

```ts
next_action(entry):
  | state == null                                                       → 'cold_attempt'
  | state == 'needs repair'                                             → 'repair'
  | state == 'primed' AND no study_revealed after latest chamber_closed → 'study'
  | state == 'primed' AND study_revealed
        AND spacing_ok(latest_close, now)
        AND latest_close.classification == 'strong'                     → 'solidify'
  | state == 'primed' AND study_revealed                                → 'review'
  | state == 'solidified'                                               → null

solidify_unlocks_at(entry):
  | state == 'primed' AND study_revealed
        AND latest_close.classification == 'strong'
        AND NOT spacing_ok(latest_close, now)
      → latest_close.at + 18h
  | otherwise → null
```

`'review'` is the calm holding state for everything that doesn't qualify for
`'solidify'` — either spacing isn't satisfied, or the latest close was
partial / thin / wrong_direction so a follow-up strong wouldn't solidify even
with spacing. In `'review'` the user can re-read study material or write
repair text, but a chamber right now will not advance state to solidified.
Module 3 may surface `solidify_unlocks_at` as a quiet "unlock at HH:MM"
affordance when one is available, or stay silent — its choice.

### Surface bindings

| Surface | Binds to | Notes |
|---|---|---|
| Map concept tile | `ConceptStatus.badge` | One vocabulary across all views. |
| Map entry chip | `EntryRender.state` (silent for null) | Replaces redundant counters like `entry 1 · ready for first attempt, current`. |
| Map primary CTA | `EntryRender.next_action` | Fixes the State 5 "Let's move on" and State 11 dead-click bugs. |
| Library card body | `EntryRender.strongest_turn_text` of the primary entry | When `null`, show empty-state copy. MUST NOT fall back to `core_thesis`. |
| Library card badge | `ConceptStatus.badge` | Same string as Map. |
| Library card composition | `ConceptStatus.composition` | "9 of 10 solidified · 1 needs repair" — pairs with badge for honest progress + honest gap. |
| Desk tile | `ConceptStatus.badge` (silent for null) | Untested concepts render no badge. |
| Sidebar concept list | `ConceptStatus.badge` as color / dot | Lightweight signal, same vocabulary. |

### Architectural enforcement

Module 3's renderers receive **only** `EntryRender` / `ConceptRender` objects.
They do not have access to the raw concept blob. There is a single derivation
function that produces these primitives from the concept; renderers import the
primitives and have no reference to `concept.events`, `concept.state` (legacy),
or `graph.metadata.core_thesis`. The forbidden bindings are not "MUST NOT"
conventions; they are physically unreachable.

Legacy fields are hard-deleted from the blob one release after migration ships
(§5). Until then they remain in `__legacy_concept_*` backups; after the cleanup
release, they are gone entirely.

### Empty-state contract

When evidence is absent, the renderer shows empty-state copy on-voice. It MUST
NOT fall back to AI-generated content.

| Field | When empty | Display |
|---|---|---|
| `strongest_turn_text` | null (no chamber_closed yet) | Persona-on-voice empty copy: e.g. _"no reconstruction yet — your first cold attempt will appear here."_ |
| `gaps` | `[]` after first chamber_closed | _"no named gaps from your last attempt."_ |
| `ConceptStatus.badge` | null (all entries untested) | No badge rendered. |
| `EntryRender.state` | null | No badge on entry chip. |

### Module 3's freedoms and constraints

Module 3 is free to choose:

- Visual treatment of the badge (color, type, dot, ribbon)
- Composition rendering (text, dots, mini-bar)
- Empty-state copy wording (within the silent-surface persona)
- Surfacing of `solidify_unlocks_at` (timestamp, relative time, or silence)
- Animation, layout, focus order

Module 3 is NOT free to invent:

- A new state vocabulary or label
- A new aggregation rule
- A fallback to legacy fields when current fields are empty
- A binding to `core_thesis` as user reconstruction

## §5 — Migration plan

### Honest principle

We do not synthesize evidence we don't have. Legacy concepts in production
localStorage carry `concept.state`, `drill_status` on nodes, and various
gap/timing fields — but they do not carry verbatim turn-by-turn user text from
past chambers. Without the verbatim text, we cannot honestly construct
`chamber_closed` events. So we don't.

Legacy concepts keep their sketch and graph but lose their attempt history. The
user re-attempts from cold on their first interaction with each existing
concept. Given current test data is a single user's machine, this is the
right trade.

### Migration boot flow

Runs once per concept on app boot. Idempotent (re-running on an already-migrated
concept is a no-op).

```ts
function migrateConcept(concept):
  if concept.schema_version >= 1:
    return  // already migrated

  // 1. Back up the entire blob to a versioned key for one release cycle
  localStorage.setItem(`__legacy_concept_${concept.id}`,
                       JSON.stringify(concept))

  // 2. Strip legacy top-level state field
  delete concept.state

  // 3. Strip legacy fields on graph nodes
  for each node in concept.graph.{backbone[*], clusters[*].subnodes[*]}:
    delete node.drill_status
    delete node.drill_phase
    delete node.gap_type
    delete node.gap_description
    delete node.re_drill_count
    delete node.re_drill_band
    delete node.last_drilled

  // 4. Strip legacy metadata fields
  // core_thesis is KEPT — used as grader-context reference per §1
  delete concept.graph.metadata.drill_status
  delete concept.graph.metadata.drill_phase
  delete concept.graph.metadata.cold_attempt_at
  delete concept.graph.metadata.study_completed_at
  delete concept.graph.metadata.re_drill_eligible_after
  delete concept.graph.metadata.re_drill_band
  delete concept.graph.metadata.gap_type
  delete concept.graph.metadata.gap_description
  delete concept.graph.metadata.last_drilled

  // 5. Init the event log with the only event we can honestly synthesize:
  //    sketch_saved (the user's original sketch text IS preserved in legacy data)
  concept.events = []
  if concept has a recoverable sketch text:
    appendEvent(concept, {
      seq: 0,
      client_event_id: `migration-${concept.id}-sketch`,
      type: 'sketch_saved',
      node_id: null,
      at: concept.created_at,
      payload: {
        text: recovered_sketch_text,
        concept_name: concept.name,
        source_ref: concept.source_ref || null
      }
    })

  // 6. Stamp the schema version
  concept.schema_version = 1

  // 7. Persist
  saveConcept(concept)
```

### User-facing surface

On first app boot after the migration ships, surface a single quiet notice
(persona-on-voice, one-time, dismissible):

> "We refactored how socratink tracks evidence. Your concepts and sketches are
> preserved. Past attempt history has been reset — re-drill to record evidence
> in the new model."

No badges, no celebrations, no "we improved!" register.

### Cleanup release (N+1)

One release after migration v1 ships, a follow-up release removes the legacy
backups:

```ts
function cleanupLegacyBackups():
  for each key matching /^__legacy_concept_/:
    localStorage.removeItem(key)
```

### Rollback path

The backup window (release N to N+1) is the rollback window. If a migration
bug is discovered post-release:

1. Stop the migration boot from running (feature flag or patch release)
2. Restore from `__legacy_concept_<id>` backups
3. Investigate, fix, re-roll

After N+1, recovery requires the user's browser to have the old version
cached, which is best-effort.

## §6 — Acceptance criteria

Restating the criteria from the brainstorming prompt and certifying §1–§5
satisfy each:

1. **"Let us delete `data-source-state` + `data-board-state` + 'thin sketch /
   growing / medium' labels without breaking any rendering contract."**
   - ✅ Satisfied by §4 (renderers bind to `EntryRender` / `ConceptRender`
     only) and §5 (migration deletes the source fields).

2. **"Define what the grader (module 2) writes back on chamber close."**
   - ✅ Satisfied by §3's `chamber_closed` payload contract.

3. **Single canonical state machine.**
   - ✅ `null | primed | needs repair | solidified`, with `null` for
     entries-without-evidence. Derivation per §2.

4. **Sketch mutability rule defined.**
   - ✅ Sketch is mutable until first `chamber_opened` event; frozen after.
     Post-chamber synthesis lives in `repair_committed`.

5. **Write-events per stage.**
   - ✅ §3 fully specifies `sketch_saved`, `sketch_revised`,
     `chamber_opened`, `chamber_turn`, `chamber_closed`, `study_revealed`,
     `repair_committed`.

## §7 — Persona-soundness summary

The persona at `agents/_templates/customer-persona-prompt.md` is a college
sophomore: anti-cramming, anti-flashcard-only, anti-cheat-with-AI,
anti-streaks/XP/badges, attracted to "write your own explanation before answer,"
"treats your guesses as data, not as right/wrong," "shows what you can
reconstruct from memory," "quiet scholarly register."

| Persona principle | Schema enforcement |
|---|---|
| Reconstruction evidence, not reading evidence | `state ≠ null` requires `chamber_closed` event. Reading study material (`study_revealed`) does not move state. |
| No "AI tutor" patronizing register | `chamber_closed.gaps` requires structured named gaps with mechanism + correction. Praise prose on a thin answer is forbidden by field shape. |
| "What you've reconstructed, not what you've saved" | Library binds to `strongest_turn_text` (verbatim user content). Cannot reach `core_thesis`. Empty state shows empty-state copy, never AI-generated fallback. |
| Quiet scholarly register / silent surface | Concept badge is null for all-untested concepts; renders no badge. Trajectory, failure_streak, and "improvement" signals are not in the rendering primitives. |
| Evidence-truth as principle | Solidification requires `strong → 18h+ → strong`. Stumble-prior cannot bootstrap durability. Partial cannot solidify. Aggregation is weakest-link. |
| Anti-gamification | No streaks. No XP. No "highest_ever." No "you've improved!" telemetry surfaced as UI. |
| No "completed/mastered by reading" | `study_revealed` is inert to derivation. Re-attempting after reading is what produces evidence. |
| Honest about gaps | `concept.badge = 'needs repair'` if any entry needs repair. Module 3 pairs with composition for honest progress alongside honest gap. |

## §8 — Forward compatibility (when Supabase comes)

This schema is designed so that the move to server-side persistence is a wiring
change, not a destructive rewrite.

| Today (localStorage v1) | Future (Supabase) | Migration shape |
|---|---|---|
| `events: Event[]` on concept blob | `events` table, one row per event | Bulk insert from blob; ordered by `seq` |
| `client_event_id: uuid` | Same; primary key with `concept_id` | Direct copy |
| `seq: number` per-concept | Same; allows `ORDER BY seq` queries | Direct copy |
| `node_id: string | null` | Same; nullable FK to `entries` table | Direct copy |
| Derivation functions in JS | Same JS, OR materialized via SQL view | Pure-function — runs anywhere |
| `__legacy_concept_*` backups | N/A (server is canonical from launch) | Discarded |

The `seq` field gives total ordering independent of client clock. The
`client_event_id` provides idempotency for batch inserts. The nullable
`node_id` allows concept-level events to coexist with entry-level events in
one events table. No destructive migration required when persistence moves.

## §9 — Relationship to prior canon

This spec supersedes `docs/drill/contract.md` on every point of disagreement.

Substantive deltas from the prior contract:

- **State vocabulary:** `locked | primed | drilled | solidified` →
  `null | primed | needs repair | solidified`. `drilled` renamed to
  `needs repair` to match the Desk legend already shown to learners and to
  drop the sci-fi register the persona rejects. `locked` replaced with `null`
  because the word lied about agency (the entry is exactly what the user
  should engage with next; it is not "locked" from them).

- **Cold-attempt contract:** prior contract required cold attempts to be
  "unscored" — no learner-facing score, classification, tier, or band. This
  spec interprets "unscored" as "no number/grade/tier rendered as a
  performance label," but reinstates structured gap-naming (mechanism +
  correction + verbatim user text) as a non-optional honest signal. The audit
  identified the prior unscored-cold-attempt rule as the structural enabler
  of the State 5 "very clear explanation" failure: when the grader cannot
  surface gaps, it falls back to encouragement. Gap-naming is honest
  reflection, not scoring.

- **Transition conditions:** prior contract restricted `drilled` to
  post-spaced-re-drill non-solid outcomes. This spec allows `needs repair` on
  the first chamber close if classification is `wrong_direction` (no grace
  from null state). The prior rule's effect was that a `wrong_direction`
  first attempt would land in `primed` — which lied about the user's actual
  position. The new rule is honest from the first close.

- **State as derived, not stored:** the prior contract described state as a
  property that gets mutated by transition rules. This spec defines state as
  a pure function over events. There are no transitions to authorize; there
  is only the fold and what it derives.

Action item out of this spec: `docs/drill/contract.md` should be updated to
point at this design doc as the new binding canon. That update is part of
this module's implementation plan.

---

End of spec.
