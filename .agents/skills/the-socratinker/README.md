# The Socratinker

`The Socratinker` is Socratink's internal product-memory skill.

Its job is to turn scattered product evidence into durable, inspectable understanding:
- doctrine
- mechanisms
- decisions
- issues
- experiments
- findings
- syntheses
- explicit log coverage

This is not a generic research wiki. It is meant to become the memory layer that helps Socratink improve over time.

## Why It Exists

As founder, the core problem you are solving is not just feature development. It is product learning.

Socratink generates evidence in many forms:
- product docs
- UX doctrine
- neurocognitive research notes
- drill chats
- test and replay traces
- bug reports
- screenshots
- experiment notes

Without a durable compilation layer, that evidence stays fragmented. Each future session has to reconstruct context from scratch, and the product cannot compound its own learning. The Socratinker exists to prevent that.

The guiding idea is simple:

1. collect raw evidence once
2. compile it into durable product memory
3. query and update the compiled state instead of repeatedly re-deriving truth
4. use the compiled state to make better product decisions

## What It Is

The Socratinker is a repo-local skill under:

- [SKILL.md](/Users/jondev/dev/socratink/prod/socratink-app/.agents/skills/the-socratinker/SKILL.md)

It includes:

- a skill contract
- a KB schema template
- page conventions
- log-surface guidance
- a deterministic validator
- a stats script
- a healthy fixture KB for regression checking

Primary files:

- [schema-template.md](/Users/jondev/dev/socratink/prod/socratink-app/.agents/skills/the-socratinker/references/schema-template.md)
- [page-conventions.md](/Users/jondev/dev/socratink/prod/socratink-app/.agents/skills/the-socratinker/references/page-conventions.md)
- [log-surfaces.md](/Users/jondev/dev/socratink/prod/socratink-app/.agents/skills/the-socratinker/references/log-surfaces.md)
- [validate_wiki.py](/Users/jondev/dev/socratink/prod/socratink-app/.agents/skills/the-socratinker/scripts/validate_wiki.py)
- [wiki_stats.py](/Users/jondev/dev/socratink/prod/socratink-app/.agents/skills/the-socratinker/scripts/wiki_stats.py)
- [healthy-kb](/Users/jondev/dev/socratink/prod/socratink-app/.agents/skills/the-socratinker/fixtures/healthy-kb)

## What It Can Do

The Socratinker is designed around seven operations:

1. `init`
Create a Socratink product-memory KB with the expected `raw/` and `wiki/` structure.

2. `ingest`
Register new raw evidence and update the compiled memory deliberately.

3. `compile`
Convert raw evidence into durable pages: doctrine, mechanisms, records, sources, and syntheses.

4. `query`
Answer from compiled memory first. Fall back to raw artifacts only when the compiled state is insufficient.

5. `lint`
Run deterministic structural validation. This is not semantic judgment.

6. `health-check`
Run semantic and epistemic review. This is where hidden contradictions, weak provenance, or missing instrumentation should surface.

7. `evaluate-logs`
Treat chats and test traces as first-class product evidence and turn them into findings, issues, experiments, and syntheses.

## What It Is Not

It is not:
- a learner-facing feature in v1
- a replacement for product judgment
- a generic note-taking system
- a place to hide ambiguity behind vague summaries

It should stay explicit, provenance-heavy, and aligned with Socratink doctrine.

## The First-Principles Model

The Socratinker should help you answer a small set of recurring founder questions:

- What must remain true in Socratink?
- How does a product or learning mechanism actually work?
- What did we decide, and why?
- What broke, under what conditions?
- What did the chats and tests actually teach us?
- What pattern changes what we should build next?
- What are we not instrumenting yet?

That is why the KB is organized around:
- doctrine
- mechanisms
- records
- sources
- syntheses

And why page types are explicit:
- `doctrine`
- `mechanism`
- `decision`
- `issue`
- `experiment`
- `finding`
- `source`
- `synthesis`

## Why Logs Matter So Much

For Socratink, logs are not just telemetry. They are evidence about the game-truth loop.

This skill is explicitly designed to ingest and evaluate:
- drill chats
- drill run logs
- test and replay traces
- future Socratink conversational surfaces

The key contract is:

- if a chat surface exists and is instrumented, The Socratinker should be able to ingest and evaluate it
- if a chat surface exists conceptually but is not instrumented, The Socratinker should record that as a gap

That makes the skill useful as a long-term product-improvement engine rather than just a wiki wrapper.

## Knowledge Base Shape

The intended KB shape is:

```text
{kb-root}/
├── CLAUDE.md
├── raw/
└── wiki/
    ├── index.md
    ├── log.md
    ├── log-coverage.md
    ├── doctrine/
    ├── mechanisms/
    ├── records/
    ├── sources/
    └── syntheses/
```

Important design choices:

- `raw/` is immutable evidence
- `wiki/` is compiled understanding
- `log-coverage.md` makes instrumentation truth explicit
- `basis: mixed` is forbidden
- `Product Implication` is required on non-source pages so the KB drives real work

## Metadata Model

Curated pages separate three different concerns:

1. page type
What kind of page is this?

2. epistemic basis
Is this page primarily `sourced` or `inferred`?

3. workflow state
Is this page `active`, `open`, `resolved`, `deprecated`, or `obsolete`, depending on page type?

This matters because a page can be:
- inferred but still valid
- sourced but still unresolved
- active but carrying an open question

The skill is designed to keep those distinctions explicit instead of collapsing them into one muddy field.

## How You Should Use It

As founder, the strongest uses are:

1. After a bug hunt
Ask The Socratinker to ingest logs, screenshots, and notes and compile:
- issue record
- finding record
- maybe a synthesis if the bug reveals a bigger pattern

2. After a product decision
Capture the decision and the evidence behind it so future sessions do not re-litigate it blindly.

3. After UX or loop testing
Feed it the traces and have it turn them into findings, experiments, and product implications.

4. During product research
Compile doctrine and mechanisms from your docs and research so the product keeps a stable conceptual core.

5. During instrumentation work
Use `log-coverage.md` to keep explicit track of what Socratink does and does not capture.

## Validation and Regression Safety

The skill includes a deterministic validator:

```bash
python3 -B .agents/skills/the-socratinker/scripts/validate_wiki.py .agents/skills/the-socratinker/fixtures/healthy-kb
```

And a stats script:

```bash
python3 -B .agents/skills/the-socratinker/scripts/wiki_stats.py .agents/skills/the-socratinker/fixtures/healthy-kb
```

The fixture KB exists so this skill can be regression-checked over time instead of drifting silently.

The validator currently enforces:
- required files/directories
- required frontmatter fields
- valid enums
- required sections
- reachable curated pages
- `review_after` on decision records
- log-coverage manifest completeness

The stats script currently reports:
- page counts by type
- unresolved issues
- stale decisions
- contradiction/open-question/hypothesis flags
- provenance coverage
- raw-artifact reference rate
- chat/test surface coverage
- evaluated sessions and runs

## Current Strengths

Right now, the skill is strong at:
- defining the contract clearly
- preventing silent structure drift
- making logging coverage explicit
- giving you a durable internal memory substrate

## Current Limits

Right now, it does not yet:
- auto-generate pages from real Socratink logs end-to-end
- maintain a live KB for the product automatically
- semantically judge every subtle contradiction on its own without a health-check pass

So the current version is a well-defined foundation, not the final autonomous system.

## What To Build Next

If you want this to live with the project indefinitely, the best next steps are:

1. Create a real Socratink internal KB in-repo or adjacent to the repo.
2. Point The Socratinker at actual drill logs and replay traces.
3. Start compiling issue/finding/decision pages from real work.
4. Expand `log-coverage.md` as new chat or test surfaces appear.
5. Eventually add an automated replay/evaluation loop on top of this KB.

That is the path from “skill contract” to “self-improving product memory.”

## Short Version

If you want the shortest founder mental model:

The Socratinker is the memory layer that lets Socratink learn from its own evidence.

Not just docs.
Not just chats.
Not just tests.

All of it, compiled into a form that can actually improve the product.
