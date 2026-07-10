# SEDA UI state alignment

This contract keeps SEDA loop logic, graph truth, and learner-visible UI states
from collapsing into one enum.

## Rule

SEDA chooses the next pedagogical move. The training store derives graph truth.
The UI renders the next honest room action.

Do not model this as:

```text
SEDA phase = graph state = UI state
```

Model it as:

```text
SEDA awaiting key + training record -> room surface
training record -> derived graph state
```

## Ownership

| Layer | Owner | May decide | Must not decide |
| --- | --- | --- | --- |
| Pedagogical route | `lib/seda/` and `lib/loop-server/` | next SEDA prompt or pause | learner-visible graph truth |
| Evidence projection | `public/js/seda-evidence-projection.js` | whether a completed SEDA record appends training evidence | UI layout or labels |
| Graph truth | `public/js/training-derive.js` | `null`, `primed`, `needs repair`, `solidified`, `next_action` | SEDA prompt sequence |
| Room UI | concept page and Drill Chamber | the surface for the next learner action | state mutation |

## Alignment matrix

| Moment | Current code signal | Room surface | Evidence mutation | Derived graph state |
| --- | --- | --- | --- | --- |
| Provisional route | map generated, no node training record | route hint | none | `null` |
| Global launch attempt | SEDA `awaiting.key === "launch_attempt"` | threshold sketch | none | unchanged |
| Local cold attempt | SEDA `awaiting.key === "cold_attempt"` or app cold-attempt drill | north-star writing room | record only if substantive | `primed` or `needs repair` |
| Study reveal | `deriveNodeTraining(...).next_action === "study"` | hinge and causal spine | `study_revealed_at` only | no solidification |
| SEDA completed case | `data.caseComplete && data.record` | return to concept | append projected attempts and repairs; set `study_revealed_at` if present | `primed` or `needs repair`; `solidified` only if the new strong attempt is spaced from prior evidence |
| Repair | SEDA repair keys or `next_action === "repair"` | missing-link repair | repair text or repair check only | usually stays `needs repair` or `primed` |
| Gap drill / pressure-check | graph-neutral drill context | transfer check | no graph-truth mutation | unchanged |
| Settle / review wait | `next_action === "review"` with `solidify_unlocks_at` | leave room or choose next room | none | `primed` |
| Spaced re-drill | `next_action === "spaced_attempt"` or SEDA `awaiting.key === "spaced_attempt"` | memory check | append spaced attempt | `solidified` only if strong and spaced |

## Room surfaces

Use one room frame with different inner states:

| Room state | Learner action | Copy posture |
| --- | --- | --- |
| `write` | write before content appears | "Write what you can explain now." |
| `study` | inspect the hinge exposed by the attempt | "Study has a target now." |
| `repair` | repair one missing causal link | "Repair one missing link." |
| `bridge` | leave the room, choose another room, or stop | "Let this settle." |
| `return` | reconstruct after spacing | "From memory, explain it again." |

The accepted north-star image applies to `write`. It is not the whole app shell.

## Guardrails

- Do not show study content before a local cold attempt.
- Do not render `solidified` from reading, repair, same-sitting practice, or a
  backend simulated spacing timestamp.
- Do not expose SEDA internal keys to the learner.
- Do not use `primed` as a reward. It means reconstruction evidence exists and
  the next action can be routed.
- Do not make the map the main surface during `write`; it is peripheral context.

## Source-less route handoff

The app opens the first composer only from the versioned session response
contract, not by interpreting the raw SEDA event journal:

```text
sourceLessRoute.contractVersion = 1
sourceLessRoute.status = ready
awaiting.key = cold_attempt
```

`ready` carries the validated first node and provisional map. Backend route
validation and frontend binding require the same fields, topology, and exactly
one occurrence of the first node. A non-empty Door sketch may satisfy routing
substrate only when the session was explicitly created with the source-less
Door bootstrap option. That sketch remains graph-neutral and non-recordable.
The preceding app-shell save persists a deterministic graph-neutral shell only;
it performs no second model route generation. Until `ready`, learner copy says
only `Preparing your first question…` and the composer remains closed.
`route_status: pending_seda` plus `graph_neutral: true` is the durable recovery
marker: reload may rebuild the route only while no attempt or repair evidence
exists, and any shell-written draft stays unrecorded until the learner reviews
the authoritative question.

Route generation or contract failure returns typed `route_unavailable`. The
composer stays closed and no evidence is projected. Recovery preserves the
Door sketch:

- no recorded evidence: discard only the stale route/session binding and build
  a fresh first question;
- any recorded evidence: return to the map without replacing the bound route or
  its evidence.

An unbound source-less map is eligible for automatic binding only when the
current Door flow created it. Legacy unbound maps require an explicit recovery
action, and any existing attempts or repairs force a return to the map. Once a
route is bound, only that bound node may use its session.

Each prompt response carries `sessionVersion`. Every submitted turn echoes that
nonnegative version as `expectedVersion` and carries a UUID request ID. A
transport retry reuses both values; a new learner submission gets a new ID. The
server checks an idempotent replay before rejecting a stale version, then
rejects a version mismatch before rehydrating or advancing the session. On a
typed 409, the app fetches the current prompt, keeps the draft unrecorded, and
requires the learner to submit it explicitly with a new ID and current version.

## Current implementation caveat

The app-local SEDA path projects a recordable cold-attempt event before case
completion so study can open after the first answer. Completed record
projection later reconciles that event and re-stamps all attempts to the real
sitting time; it must not append the cold answer twice or manufacture spacing.
`public/js/seda-evidence-projection.js` re-stamps backend attempts to wall-clock
time so one sitting cannot falsely derive `solidified`.

The first UI implementation should therefore prove only:

```text
one room -> cold attempt -> completed evidence projection -> derived next action
```

Do not build journey-wide chrome until this path passes the Taste Gate.
