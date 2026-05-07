# Progressive Route Materialization — Agent Brief

Date: 2026-05-07
Status: implementation-facing handoff
Primary spec: `docs/superpowers/specs/2026-05-07-progressive-route-materialization-design.md`

## Why this brief exists

This captures the product decision that emerged from the 2026-05-07 loop-entry design review. Read it before changing concept entry, source-less concept creation, `/api/extract` dispatch, launch-pad copy, or graph materialization.

The short version:

> Socratink progressively discloses the learning loop to the learner while progressively materializing the route from learner-generated evidence.

This is not a new product mode. It is the corrected framing for concept entry: keep the door small, but never generate a graph or thesis from a concept name alone.

## The learning contract

There are two different entry contracts.

**No source attached:** start from the learner's current model.

- The learner gives a concept name.
- Socratink asks for a Feynman-style launch attempt: what the learner already thinks is inside the concept.
- Only after that learner-authored seed does the model generate a smallest route.
- The route is hypothesis, not evidence.

**Source attached:** start from the material, but learning still starts from reconstruction.

- The learner gives a concept name and source material.
- Socratink can extract a fuller provisional map from the source.
- The graph is still hypothesis.
- Reading or extraction never changes graph truth.

In both cases, graph truth changes only after learner-generated reconstruction: cold attempts and later spaced re-drills.

## Final C-prime flow

The accepted flow is C-prime: launch pad, not graph.

1. **Door**
   - Learner sees one required field: concept name.
   - Source attach is optional.
   - CTA is visually arrow-only, but must have an accessible name.
   - No eyebrow, voice line, descriptive paragraph, or sketch field.

2. **Source-attached branch**
   - Text/file source posts through the existing `/api/extract` path.
   - URL source first materializes through `/api/extract-url`, then posts returned text to `/api/extract`.
   - The backend returns the existing map response shape.
   - Frontend persists the concept into the existing browser store.

3. **Source-less branch**
   - Door submit writes `{ name, ts }` to `sessionStorage` under `socratink:pendingShell`.
   - No server concept is created. No graph is generated.
   - The learner lands on the launch pad.

4. **Launch pad**
   - Copy: `What do you already think is inside this concept?`
   - Helper: `Name the parts, guesses, examples, or confusions you have.`
   - This launch attempt is threshold capture, not a cold attempt.
   - It mutates no node state and unlocks no study.
   - Submit posts to `/api/extract` with `{ name, source: null, starting_sketch: threshold }`.

5. **Smallest route**
   - Backend route generation is stateless.
   - It returns a `ProvisionalMap`, not a new model.
   - It must be a smallest route: core thesis as the suggested first target, plus at most three backbone hints.
   - The frontend persists the concept only after receiving and validating the map, then clears `socratink:pendingShell`.

6. **Route view**
   - Shows the skeleton framing line: `This is the skeleton. It will grow as you reconstruct.`
   - Then the normal cold-attempt loop begins.

7. **First cold attempt**
   - Local, node-scoped, and unscored.
   - A substantive attempt moves the target `locked -> primed`.
   - Study remains locked until that attempt exists.

## Non-negotiable guardrails

- No graph, no core thesis, no one-node placeholder, and no AI-generated learner-facing artifact from concept name alone.
- Do not collapse launch attempt and cold attempt. Launch attempt is global threshold capture; cold attempt is local reconstruction.
- Do not add progressive expansion logic in v1. The smallest route is terminal for this slice.
- Do not add `creation_phase`, `/api/concepts/shell`, or `/api/concepts/<id>/route` for v1.
- `/api/extract` must reject name-only/source-null/thin-sketch bypasses with `422` and `error: "name_only_bypass"`.
- The source-less route must be `ProvisionalMap`-compatible because current graph rendering and drill flows consume that shape.
- Keep the source-attached URL two-step. Raw URL source directly to `/api/extract` remains rejected.
- Keep graph truth language evidence-bound. Never imply the graph knows what the learner knows.

## Key copy decisions

- Home/desk noun: `Your concepts`, not `Your library`.
- Door title: `What do you want to understand?`
- Door CTA: arrow icon only, with accessible label.
- Launch pad title: `What do you already think is inside this concept?`
- Launch pad helper: `Name the parts, guesses, examples, or confusions you have.`
- Route framing line: `This is the skeleton. It will grow as you reconstruct.`
- Avoid: `Show me your starting map`, `draft path` on home/desk, `prove what you know`, `diagnostic`, `mastery`, `completed`, or any claim that reading/extraction changed learner evidence.

## Rejected paths

**Concept-name-only full graph:** rejected because it is provider-prior knowledge dressed as learner-seeded structure.

**Concept-name-only thesis plus one node:** also rejected. Smallness does not make provider-prior generation truthful.

**Cold attempt as threshold:** rejected for v1. It collapses the global threshold and local cold attempt distinction that the product doctrine depends on.

**Server-persisted shell state in v1:** rejected as unnecessary scope. The shell is just the concept name before threshold; `sessionStorage` is enough for dogfood.

**New `SmallestRoute` model:** rejected because the existing graph/drill surface consumes `ProvisionalMap`.

## Implementation notes for future agents

- Treat `docs/superpowers/specs/2026-05-07-progressive-route-materialization-design.md` as the implementation contract.
- Keep `/api/extract` response shape aligned with current frontend expectations: `{ provisional_map }` for source-less generation and `{ knowledge_map }` for extraction.
- Do not write code that assumes the server persists concepts. The current persistence model is browser storage.
- If the source panel is reused on the door, extract the existing `concept-create.js::beginEditSource` behavior into a shared module and smoke-test the existing modal afterward.
- If the smallest route cap is enforced, count drillable nodes the way the current app does: `core-thesis` is drillable.
- Add parity tests for the threshold substantiveness helper. Do not reuse the old `is_substantive_sketch` contract blindly if the new threshold gate is 3+ words / no-idk.

## What to measure

- Source-less door submit rate.
- Launch-pad abandonment rate.
- Thin-threshold rejection rate, client and server.
- Time from door submit to first substantive cold attempt.
- Whether source-less learners treat launch pad as friction by submitting very thin attempts.
- Whether smallest routes produce useful first cold attempts.

If telemetry shows the launch pad is treated as a tax, revisit the launch/cold-attempt split. Do not solve that by generating from the concept name alone.
