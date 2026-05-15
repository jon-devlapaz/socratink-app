# Prototyping

## Trigger

Any request to prototype, mock up, sanity-check a state model, compare several UI directions, or answer "what should this look like?" / "does this logic feel right?" before committing to production code.

## Goal

Use throwaway artifacts to answer one concrete question quickly, then promote only the answer into durable repo truth. The prototype exists to reduce uncertainty, not to become production code by accident.

## Inputs To Inspect

- the exact question the prototype is meant to answer
- whether the question is about `logic/state` or `UI/copy`
- the closest real repo surface the prototype can sit beside
- the existing runtime/task runner that can launch it in one command
- whether the result needs a durable verdict file, ADR, or glossary update

## Risk Classification

- `safe`: choosing prototype shape, creating a throwaway local artifact, iterating on non-production prototype code
- `confirm`: absorbing a winning prototype into real code, deleting losing variants, keeping a load-bearing verdict in repo docs
- `hard-confirm`: replacing a live production surface directly from prototype code without a proper production rewrite, or introducing persistent infrastructure just to support a prototype

## Recommended Route

Choose the branch based on the question:

### `logic/state` prototype

Use when the question is about business logic, state transitions, or data shape.

- build the smallest possible interactive harness close to the real code
- keep the actual logic behind a portable module or pure interface
- keep the shell throwaway
- render the full relevant state after each action
- avoid persistence unless persistence itself is the thing being tested

### `UI/copy` prototype

Use when the question is about what a surface should look or read like.

- prefer several radically different variants over one polished guess
- for this repo, default to a single `?v=A|B|C|D` route under `public/_lab/<surface>-variants.html`
- use `scripts/snap.py` to sweep variants
- use `scripts/persona.sh` when persona-based review would sharpen the verdict
- capture the decision in a sibling `<surface>-variants.NOTES.md`

If the question is ambiguous, stop and classify it explicitly before building.

## Required Confirmation

- no prototype should quietly become production code
- if a prototype result changes load-bearing domain meaning, capture that decision durably
- if the prototype needs to cross from throwaway into real code, pause and rewrite it properly instead of shipping the prototype shell

## Verification

- the prototype can be run in one obvious command
- the current question is stated clearly at the top of the artifact or in a nearby note
- for logic prototypes, state changes are visible after every action
- for UI prototypes, variants are easily switchable and comparable
- when the prototype is done, the answer is captured durably before deletion or absorption

## Stop Rules

- stop if you are building a prototype without a specific question
- stop if the prototype is accumulating production-hardening work instead of answering the question
- stop if the result needs persistence, auth, or backend integration that is unrelated to the question being asked
- stop if the "prototype" is really a hidden implementation branch pretending to be throwaway

## Artifact Destination

- shared workflow truth: this file
- UI prototype artifacts: `public/_lab/<surface>-variants.html` plus sibling `<surface>-variants.NOTES.md`
- durable follow-up when load-bearing: `UBIQUITOUS_LANGUAGE.md` for term-meaning changes, `DESIGN.md` §4 for design principles, an ADR for architectural decisions
