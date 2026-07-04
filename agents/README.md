# agents/

Canonical shared workflow truth for repo agents.

## What belongs here

- non-binding workflow learnings that may later be promoted
- shared decision rubrics

## What does not belong here

- runtime executables already owned by `scripts/`
- auth/session state
- caches
- tool-specific hooks/settings syntax

## Local substrate boundary

`.agents/` is not part of the shared canon.

- `.agents/skills/` is external project-local install-state only.
- `.agents/runtime/` is ignored runtime evidence only.
- nothing in `.agents/` should be required as binding doctrine for a fresh checkout.

## Authority rule

`agents/` is the shared workflow canon. `AGENTS.md` is the root repo entrypoint and still carries binding repo doctrine. `CLAUDE.md` is the active compatibility adapter into this canon. Tool-specific directories like `.claude/`, `.codex/`, and `.gemini/` are runtime/config/wrapper surfaces, not canonical doctrine.

`agents/LEARNINGS.md` is a special case: it lives in the canon tree so agents can find it, but its entries are non-binding until promoted into a canonical workflow, README, bootstrap doc, or other registered binding file.

## Migration rule

Migrate selectively. Promote only stable, high-signal, cross-model content. Preserve high-value tool-local content until its signal is captured or intentionally deprecated.

## Adapter budget

Adapters are allowed to contain only:

- minimal tool-specific activation or compatibility wording
- a pointer into the relevant shared canon file
- must-not-miss bootstrap lines when the tool would otherwise fail to load the canon

Adapters must not become a second doctrine surface. If a wrapper still contains the full decision logic, stop rules, verification sequence, or long-form workflow steps, it is no longer acting as an adapter.

## Workflow learning ledger

Use `agents/LEARNINGS.md` to capture reusable observations from real founder/agent workflow usage.

- Read it only when a task touches agent workflow design, bootstrap, publication safety, artifact placement, verification discipline, workflow-card creation, or recurring workflow friction.
- Write to it only when real usage exposes reusable workflow evidence. Do not log one-off task details, speculative ideas, or policy that already belongs directly in canon.
- Promote from it only through reviewed edits to the canonical destination.

The compounding rule is simple: repeated patterns become promotion candidates after 3 real sightings, or after 2 sightings when the pattern affects publication safety, verification integrity, bootstrap correctness, or canon boundaries. The ledger never mutates canon by itself.

## Git publication config

Trusted remote URL patterns for the founder git workflow live in `agents/founder/trusted-remotes.json`. Machine-local additions belong in the ignored `.agents/runtime/trusted-remotes.local.json` file.
