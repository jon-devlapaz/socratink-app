# Socratink Brain Workflow Architecture

Socratink Brain is the durable product-memory substrate for Socratink. It is not an executor and not a second planning system. `socratinker` remains the default execution owner; the Brain stores compiled evidence, doctrine, decisions, findings, and syntheses that make future work less dependent on chat-history memory.

This document captures the workflow architecture represented in the local diagram originally drafted at `.claude/worktrees/determined-bhaskara/socratink-architecture.html`. The `.claude/` copy is local scratch output; this Markdown file is the canonical tracked version.

## Operation Router

The `$socratink-brain` skill routes user intent into six operations:

- `init`: create a new Brain KB using the schema contract.
- `ingest`: register raw artifacts, create source pages, and promote derived memory only when warranted.
- `query`: answer from compiled pages first, then fall back to raw artifacts only when compiled memory is insufficient.
- `evaluate-logs`: ingest drill or replay logs and derive traceable findings, issues, experiments, or syntheses.
- `lint`: run deterministic structural validation.
- `health-check`: run semantic and epistemic review for stale claims, contradictions, weak provenance, over-promotion, orphaned sources, missing instrumentation, and basis drift.

## Data Layers

`raw/` contains immutable inputs. Raw artifacts are copied into category folders and are not rewritten after intake:

- `product-docs/`
- `research-notes/`
- `drill-chat-logs/`
- `product-chat-logs/`
- `test-replay-logs/`
- `bug-reports/`
- `screenshots/`
- `experiment-notes/`

`wiki/` contains compiled product memory:

- `sources/`: bridges from raw artifacts into curated memory.
- `doctrine/`: binding principles.
- `mechanisms/`: how product or learning mechanisms work.
- `records/`: decisions, issues, experiments, and findings.
- `syntheses/`: cross-cutting patterns.
- `index.md`: table of contents and query entrypoint.
- `log.md`: append-only changelog.
- `log-coverage.md`: instrumentation truth.

`ACTIVE.md` is a promoted work queue, not a backlog. It must stay capped at five items, and each item must cite `docs/project/state.md#current-release-goal`.

## Ingest Workflow

1. Register the raw artifact under `raw/{category}/`.
2. Create or update a source page under `wiki/sources/` with a `raw_artifacts` link.
3. Promote to doctrine, mechanism, decision, finding, issue, experiment, or synthesis only if the artifact changes doctrine, mechanism, release risk, decision state, instrumentation truth, or active MVP priorities.
4. Update `wiki/index.md` and append to `wiki/log.md`.

Artifacts that do not cross the promotion threshold stay represented by their source page only.

## Query Workflow

1. Navigate from `wiki/index.md`.
2. Answer from compiled pages first.
3. Surface contradictions explicitly.
4. Read raw artifacts only when compiled memory is insufficient.

## Validation

Lint is deterministic:

```bash
python3 .agents/skills/socratink-brain/scripts/validate_wiki.py .socratink-brain
```

Stats are reporting-only:

```bash
python3 .agents/skills/socratink-brain/scripts/wiki_stats.py .socratink-brain
```

Health-check is LLM-driven and separate from lint. It reviews stale claims, contradictions, provenance strength, over-promotion, missing instrumentation, orphaned sources, and basis drift.

## Git Tracking Policy

Track the Brain operating system and compiled memory:

- `.socratink-brain/CLAUDE.md`
- `.socratink-brain/ACTIVE.md`
- `.socratink-brain/wiki/**`
- `.agents/skills/socratink-brain/**`
- durable docs under `docs/`
- `AGENTS.md`

Track raw artifacts only when they are intentionally promoted evidence required by current source pages or fixtures. Keep runtime exports, private chat dumps, local agent state, and environment state ignored.

## Non-Negotiables

- Generation Before Recognition is binding.
- The graph must tell the truth.
- Attempted is not mastered.
- Evidence, inference, and hypothesis must be distinguished.
- `basis: mixed` is never allowed.
- Missing instrumentation is a health gap, not a silent omission.
