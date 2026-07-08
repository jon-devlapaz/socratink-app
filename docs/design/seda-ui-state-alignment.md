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

## Current implementation caveat

The app-local SEDA path projects evidence only when `data.caseComplete` is true.
`public/js/seda-evidence-projection.js` re-stamps backend attempts to wall-clock
time so one sitting cannot falsely derive `solidified`.

The first UI implementation should therefore prove only:

```text
one room -> cold attempt -> completed evidence projection -> derived next action
```

Do not build journey-wide chrome until this path passes the Taste Gate.
