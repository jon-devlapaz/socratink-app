# Schema Template (CLAUDE.md)

Use this template when initializing a new Socratink internal product-memory knowledge base.

---

```markdown
# {KB Name} — Socratink Product Memory

{One sentence explaining what this knowledge base covers and how it improves Socratink.}

## Purpose

This knowledge base exists to help Socratink improve from durable compiled product memory.
It compiles doctrine, mechanisms, decisions, issues, experiments, findings, syntheses,
and log-derived evidence into a persistent markdown substrate.

## Architecture

```
{kb-root}/
├── CLAUDE.md
├── raw/
│   ├── product-docs/
│   ├── research-notes/
│   ├── drill-chat-logs/
│   ├── product-chat-logs/
│   ├── test-replay-logs/
│   ├── bug-reports/
│   ├── screenshots/
│   └── experiment-notes/
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

## Layer Rules

- **raw/** — Immutable inputs. The compiler reads them but never mutates them.
- **wiki/** — Compiled product memory. The compiler creates and updates these pages.
- **CLAUDE.md** — The governing contract for structure, metadata, and workflow.

## Product Doctrine Constraints

- Generation Before Recognition is binding.
- The graph must tell the truth.
- Attempted is not mastered.
- Product claims must distinguish evidence, inference, and hypothesis.
- Missing instrumentation is a health gap and must be explicit.

## Page Types

- `doctrine`
- `mechanism`
- `decision`
- `issue`
- `experiment`
- `finding`
- `source`
- `synthesis`

## Metadata Contract

All curated pages must include:

```yaml
---
title: "Page Title"
type: doctrine | mechanism | decision | issue | experiment | finding | source | synthesis
updated: YYYY-MM-DD
sources: [relative/path.md]
related: [relative/path.md]
basis: sourced | inferred
workflow_status: {type-specific value}
flags: [hypothesis, open-question, contradiction]
---
```

Additional fields:
- Decision records require:

```yaml
review_after: YYYY-MM-DD
```

- Source pages require:

```yaml
source_kind: product-doc | research-note | drill-chat-log | drill-run-log | drill-turn-log | product-chat-log | test-replay-log | bug-report | screenshot | experiment-note
raw_artifacts: [raw/path.ext]
log_surface: drill | {other-surface}
evaluated_sessions: N
evaluated_runs: N
```

## Workflow Status Rules

- `doctrine`, `mechanism`, `source`: `active | deprecated | obsolete`
- `decision`, `issue`, `experiment`, `finding`, `synthesis`: `open | resolved | obsolete`

## Required Sections By Page Type

- `doctrine`: `## Principle`, `## Evidence`, `## Product Implication`
- `mechanism`: `## Mechanism`, `## Evidence`, `## Product Implication`
- `decision`: `## Decision`, `## Evidence`, `## Inference`, `## Product Implication`
- `issue`: `## What Broke`, `## Evidence`, `## Product Implication`
- `experiment`: `## Change`, `## Evidence`, `## Inference`, `## Product Implication`
- `finding`: `## Finding`, `## Evidence`, `## Product Implication`
- `source`: `## Summary`, `## Raw Artifacts`, `## Connections`
- `synthesis`: `## Pattern`, `## Evidence`, `## Inference`, `## Product Implication`

## Log Coverage Manifest

Maintain `wiki/log-coverage.md`.

Required frontmatter:

```yaml
---
title: "Socratink Log Coverage"
type: log-coverage
updated: YYYY-MM-DD
expected_chat_surfaces: [drill]
instrumented_chat_surfaces: [drill]
expected_test_surfaces: [replay]
instrumented_test_surfaces: [replay]
current_log_files: [logs/drill-chat-transcripts.jsonl, logs/drill-chat-turns.jsonl, logs/drill-runs.jsonl]
missing_instrumentation: []
---
```

Required sections:
- `## Current Log Adapters`
- `## Missing Instrumentation`
- `## Notes`

If Socratink has a conversational or test surface without instrumentation, list it explicitly.

## Operations

### Init
1. Create the directory structure.
2. Create `index.md`, `log.md`, and `log-coverage.md`.
3. Seed the doctrine constraints and known current log adapters.

### Ingest
1. Read the new raw artifact.
2. Read `wiki/index.md` and relevant existing pages.
3. Create or update source pages and any affected doctrine/mechanism/record/synthesis pages.
4. Update `wiki/index.md` and append to `wiki/log.md`.

### Evaluate Logs
1. Ingest Socratink chat/test log artifacts.
2. Create or update source pages for those log artifacts.
3. Derive findings/issues/experiments/syntheses from those logs.
4. Update `log-coverage.md` if new instrumentation truth is discovered.

### Query
1. Navigate from `wiki/index.md`.
2. Answer from compiled pages first.
3. Surface contradictions if present.
4. Fall back to raw material only when compiled memory is insufficient.

### Lint
Run deterministic validation only.

### Health-Check
Run LLM-driven semantic and epistemic review.

## Index Format (`wiki/index.md`)

Group entries by:
- Doctrine
- Mechanisms
- Records
- Sources
- Syntheses

Each entry uses:

```
- [Page Title](relative/path.md) — one-line summary
```

`log-coverage.md` must also appear in the index under a system section.

## Log Format (`wiki/log.md`)

Append-only. Each entry:

```
## [YYYY-MM-DD] operation | Subject
Brief description of what changed and which pages were affected.
```
```

---

## Template Notes

- Keep the contract small and explicit.
- Prefer durable product memory over generic note-taking.
- Never hide missing instrumentation.
- Never use `basis: mixed`.
