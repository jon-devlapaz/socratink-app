# Socratink Brain

Socratink Brain is Socratink's internal product-memory skill. It turns scattered product evidence into durable, inspectable memory so future sessions do not re-derive the same product truth.

Use [SKILL.md](SKILL.md) as the agent contract. This README is the founder-facing overview.

Live KB:

- `.socratink-brain/`

Core skill files:

- [schema-template.md](references/schema-template.md)
- [page-conventions.md](references/page-conventions.md)
- [log-surfaces.md](references/log-surfaces.md)
- [validate_wiki.py](scripts/validate_wiki.py)
- [wiki_stats.py](scripts/wiki_stats.py)
- [healthy-kb](fixtures/healthy-kb)

## Model

Raw evidence goes into `raw/`. Compiled product memory goes into `wiki/`.

Every meaningful artifact should get at most one source page by default. Add derived pages only when the artifact changes doctrine, mechanism, release risk, decision state, instrumentation truth, or active MVP priorities.

The KB page types are:

- `doctrine`
- `mechanism`
- `decision`
- `issue`
- `experiment`
- `finding`
- `source`
- `synthesis`

Important metadata distinctions:

- `basis: sourced | inferred` records provenance mode.
- `confidence: high | medium | low | speculative` records claim strength on non-source pages.
- `basis: mixed` is forbidden.
- Source pages carry provenance primarily through `raw_artifacts`.
- Non-source pages cite source pages or repo docs through `sources`.

## Operations

Socratink Brain recognizes six operations:

- `init`: create the KB structure and seed the contract.
- `ingest`: register raw evidence, create or update one source page, then promote only meaningful derived memory.
- `query`: answer from compiled memory first, then fall back to raw artifacts only when needed.
- `lint`: run deterministic structural validation only.
- `health-check`: review stale claims, contradictions, weak provenance, over-promoted active work, orphaned sources, and missing instrumentation.
- `evaluate-logs`: turn Socratink chat/test logs into findings, issues, experiments, syntheses, and log-coverage updates.

Founder prompt examples:

- "Feed this artifact to Socratink Brain."
- "Ask Socratink Brain what we know about spacing."
- "Have Socratink Brain evaluate these drill logs."
- "Run a Socratink Brain health check."
- "Promote this only if it affects the MVP gate."

## Active Queue

Use `.socratink-brain/ACTIVE.md` only for validated, release-relevant work.

Each active item must:

- link to a curated wiki page
- cite `docs/project/state.md#current-release-goal` inline
- map to one of the eight current release-goal loop behaviors

Interesting but non-release-relevant material stays in `wiki/`, not `ACTIVE.md`.

## Validation

Run both the live KB and fixture checks after structural changes:

```bash
python3 -B .agents/skills/socratink-brain/scripts/validate_wiki.py .socratink-brain
python3 -B .agents/skills/socratink-brain/scripts/validate_wiki.py .agents/skills/socratink-brain/fixtures/healthy-kb
python3 -B .agents/skills/socratink-brain/scripts/wiki_stats.py .socratink-brain
python3 -B .agents/skills/socratink-brain/scripts/wiki_stats.py .agents/skills/socratink-brain/fixtures/healthy-kb
```

The validator enforces structure. The stats script reports health signals such as provenance coverage, raw-artifact reference rate, surface coverage, stale pages, missing instrumentation, and evaluated sessions/runs.

## Current Limits

The skill has a clear KB contract, deterministic validation, stats, and a regression fixture.

It still does not auto-generate pages from real Socratink logs end-to-end. Treat log-ingest examples as fixtures unless they are tied to real `raw/` artifacts and real source pages.
