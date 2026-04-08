# socratink — Drill & Graph Evaluation

This document defines the smallest useful evaluation set for the current MVP loop.

Use the `Thermostat Control Loop` starter map unless the task specifically targets extraction or ingestion.

## 1. Manual Eval Set

### Eval 1: Core Thesis Cold Attempt
- Goal: verify unscored cold attempt -> `primed` -> study
- Strong answer: "A thermostat compares the current room temperature to the set point, turns the heater on when there is a gap, and turns it off once the gap closes."
- Expectation: no score shown, Core Thesis becomes `primed`, study opens

### Eval 2: Backbone Unlock Path
- Goal: verify the next branch can actually be traversed
- Strong answer: "Feedback control means the system measures the current state, compares it to a target, acts when there is a gap, and stops once that gap is closed."
- Expectation: backbone becomes `primed`; returning from study opens the cluster; cluster child rooms are selectable

### Eval 3: Child Room Cold Attempt
- Goal: verify drillability inside the cluster
- Example target: `Temperature Comparison` or `Call For Heat`
- Expectation: child cold attempt resolves cleanly, study opens, graph remains stable

### Eval 4: Spaced Re-Drill Truth
- Goal: verify earlier room cannot be re-drilled too early and can later resolve truthfully
- Expectation: premature return is blocked; later re-drill ends in `drilled` or `solidified` without lying

## 2. Answer Modes

| Turn Type | Expected Routing | Sample Answer |
|---|---|---|
| Explicit unknown | `SCAFFOLD` | "I don't know." |
| Shallow attempt | `PROBE` | "It checks if the room is cold and turns the heat on." |
| Partial causal attempt | `PROBE` | "It compares the current temperature to a target and triggers heating when there is a difference." |
| Solid attempt | `NEXT` | "It measures the room temperature, compares it to the set point, triggers heating when the room is below target, and stops once the target is reached." |

## 3. Obvious-Break Checklist

Treat the build as unhealthy if any occur:
- stale drill transcript remains after returning to map
- graph highlights one node while the backend evaluates another
- a cluster opens but its child rooms cannot be selected
- cold attempt shows a score or classification
- graph state contradicts what just happened
- a node reaches `solidified` from a non-solid path

## 4. Evidence Capture

After a meaningful eval run, keep:
- `logs/drill-runs.jsonl`
- any transcript logs that exist
- screenshots of visual contradictions
- a short note on what broke or what felt truthful

Record durable findings in the branch docs or merge note, alongside the supporting logs and screenshots.
