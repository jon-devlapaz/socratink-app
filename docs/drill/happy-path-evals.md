# Drill Happy Path Evals

Purpose: manual evaluation guide for validating drill outcomes and graph-state updates.

Read this when:

- manually evaluating drill quality and graph truthfulness
- testing solid vs non-solid outcomes
- verifying re-drill conversion and force-advance behavior

Read these first if you need system context:

- [graph-invariants.md](graph-invariants.md)
- [product/progressive-disclosure.md](../product/progressive-disclosure.md)
- [project/mvp-happy-path.md](../project/mvp-happy-path.md)

This document is for manual testing of drill behavior and graph updates.

Use the `Thermostat Control Loop` starter map for the cleanest evals.

Why this map:

- simple causal chain
- easy for a tester to answer intentionally well or poorly
- low domain expertise required
- clear difference between shallow recognition and causal understanding

## What Actually Causes The Graph To Update

The graph updates only when the backend returns:

- `routing === "NEXT"`

No graph mutation happens on:

- `PROBE`
- `SCAFFOLD`

When `routing === "NEXT"`:

- `classification === "solid"` -> node becomes `solidified`
- non-solid classification -> node becomes `drilled`

The frontend patches `concept.graphData`, then the graph re-renders from that patched state.

This document should stay concrete and test-oriented.
Do not expand it into a product manifesto or implementation spec.

## Session Rules To Remember

- init turn asks the opening question only
- graph state should not change on init
- a node can be force-advanced after 3 probes
- force-advance still produces graph mutation only once routing becomes `NEXT`
- session can end after:
  - 4 drilled nodes total in one session
  - 35 minutes elapsed

## Recommended Starter Node

Use:

- `Thermostat Control Loop`
- first target subnode: `Temperature Comparison`

This node is easy to test because the mechanism is compact:

- thermostat measures room temperature
- compares it to the set point
- detects a gap when current temperature is below target

## Eval 1: Solid Success Path

Goal:

- produce `classification = solid`
- produce `routing = NEXT`
- observe node `solidified`

Suggested answer:

> The thermostat keeps checking the current room temperature against the temperature you set. If the room is colder than the target, it detects a gap that needs to be corrected, which is why it knows to trigger heating.

What to expect:

- AI should acknowledge real reconstruction
- backend should eventually return `NEXT`
- node becomes `solidified`
- right panel enters post-drill state
- clicking `Continue` returns to inspect mode

## Eval 2: Shallow Recognition Path

Goal:

- produce non-solid classification with eventual `NEXT`
- observe node `drilled`, not `solidified`

Suggested answer:

> The thermostat checks if the room is cold and turns the heat on.

Why this is shallow:

- captures the high-level idea
- does not explain comparison to set point
- does not explain the causal role of the temperature gap

What to expect:

- likely `PROBE` or `SCAFFOLD` first
- after more weak answers, eventual `NEXT`
- node becomes `drilled`
- cluster should derive to `drilled` if this is the first attempted subnode

## Eval 3: Misconception Path

Goal:

- produce a clearly wrong causal model
- observe non-solid result and no false mastery

Suggested answer:

> The thermostat makes the heater hotter or cooler directly depending on how cold the room feels.

Why this is a misconception:

- thermostat does not modulate how hot the heater burns
- it switches the heating system on or off based on the threshold comparison

What to expect:

- AI should push back or scaffold
- after enough unresolved turns, backend may force `NEXT`
- node becomes `drilled`
- graph should not mark it `solidified`

## Eval 4: Probe Cap Force-Advance

Goal:

- confirm non-solid learners are not trapped forever
- confirm graph still tells the truth

Method:

1. Start a drill on the thermostat node
2. Give 3 weak or incorrect answers in a row
3. Watch for the backend to force `routing = NEXT`

Suggested weak sequence:

1. `It just knows when the room is cold.`
2. `It sends more power into the heater.`
3. `It works like a temperature dial on the heater itself.`

What to expect:

- conversation advances
- node becomes `drilled`
- node does not become `solidified`
- downstream truth should remain intact

## Eval 5: Re-Drill Conversion

Goal:

- confirm a previously non-solid node can later flip to solid

Method:

1. First get a node into `drilled`
2. Reopen the same node later
3. Give a strong causal answer

Suggested strong answer for `Call For Heat`:

> Once the thermostat detects that the room is below the set point, it closes the control circuit and sends a signal that tells the furnace to start running. It is not creating heat itself, it is triggering the heating system.

What to expect:

- node flips from `drilled` to `solidified`
- gap metadata clears
- if this completes the cluster, cluster should derive to `solidified`

## What To Watch In The UI

During drill:

- right panel should not show the mechanism text
- active node should remain identifiable
- graph should recede rather than act like a cheat sheet

After drill:

- `solid` -> post-drill panel should read as affirming and specific
- non-solid -> post-drill panel should read as neutral and return-worthy
- `Continue` should be required to exit post-drill mode

## Current Best Manual Eval Sequence

For the cleanest demo:

1. Import `Thermostat Control Loop`
2. Open graph view
3. Start drill on `Temperature Comparison`
4. Give a strong causal answer
5. Confirm `solidified`
6. Drill `Call For Heat`
7. Give a shallow answer first
8. Confirm probing/scaffolding
9. Continue weakly until force-advance
10. Confirm `drilled`
11. Re-drill that same node later with a strong answer
12. Confirm conversion to `solidified`

This sequence shows:

- one-step mastery
- non-solid truthful marking
- force-advance without fake mastery
- re-drill conversion
