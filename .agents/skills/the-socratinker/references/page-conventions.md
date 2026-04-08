# Page Conventions — The Socratinker

## Filename Rules

All filenames are lowercase, hyphen-separated, and ASCII only.

| Page Type | Directory | Pattern | Example |
|-----------|-----------|---------|---------|
| Doctrine | `wiki/doctrine/` | `{slug}.md` | `generation-before-recognition.md` |
| Mechanism | `wiki/mechanisms/` | `{slug}.md` | `three-phase-node-loop.md` |
| Decision | `wiki/records/` | `decision-{slug}.md` | `decision-time-gate-policy.md` |
| Issue | `wiki/records/` | `issue-{slug}.md` | `issue-session-complete-drops-outcome.md` |
| Experiment | `wiki/records/` | `experiment-{slug}.md` | `experiment-primed-bloom-reward.md` |
| Finding | `wiki/records/` | `finding-{slug}.md` | `finding-drill-chat-log-gaps.md` |
| Source | `wiki/sources/` | `{source-kind}-{slug}.md` | `drill-chat-log-thermostat-session-1.md` |
| Synthesis | `wiki/syntheses/` | `{slug}.md` | `spacing-vs-interleaving-tradeoffs.md` |
| Coverage Manifest | `wiki/` | `log-coverage.md` | `log-coverage.md` |

## Shared Frontmatter

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

### Allowed `workflow_status` values

- `doctrine`, `mechanism`, `source`: `active | deprecated | obsolete`
- `decision`, `issue`, `experiment`, `finding`, `synthesis`: `open | resolved | obsolete`

### Additional fields

**Decision records**
```yaml
review_after: YYYY-MM-DD
```

**Source pages**
```yaml
source_kind: product-doc | research-note | drill-chat-log | drill-run-log | drill-turn-log | product-chat-log | test-replay-log | bug-report | screenshot | experiment-note
raw_artifacts: [raw/path.ext]
log_surface: drill | {other-surface}
evaluated_sessions: N
evaluated_runs: N
```

## Page Bodies

### Doctrine Page

```markdown
# {Title}

## Principle
{What must remain true in Socratink.}

## Evidence
{Why this principle exists. Cite sources and prior decisions.}

## Product Implication
{How this should constrain feature, UX, or implementation work.}
```

### Mechanism Page

```markdown
# {Title}

## Mechanism
{How this product or learning mechanism actually works.}

## Evidence
{What sources support this mechanism description.}

## Product Implication
{What this changes in implementation or UX.}
```

### Decision Record

```markdown
# {Title}

## Decision
{The chosen path.}

## Evidence
{The evidence and constraints that mattered.}

## Inference
{The reasoning that connected the evidence to the choice.}

## Product Implication
{What this changes now.}
```

### Issue Record

```markdown
# {Title}

## What Broke
{Concrete failure description.}

## Evidence
{Observed traces, logs, screenshots, repro conditions.}

## Product Implication
{Why this matters for Socratink and what must be guarded.}
```

### Experiment Record

```markdown
# {Title}

## Change
{What changed in the product or process.}

## Evidence
{Logs, observations, metrics, or traces collected.}

## Inference
{What the evidence suggests, including uncertainty.}

## Product Implication
{What should happen next.}
```

### Finding Record

```markdown
# {Title}

## Finding
{What chats, tests, or evidence taught us.}

## Evidence
{The raw basis for the finding.}

## Product Implication
{Why this should change product, UX, or implementation work.}
```

### Source Page

```markdown
# {Title}

## Summary
{2-4 paragraphs summarizing the source or log artifact.}

## Raw Artifacts
- `raw/path.ext`

## Connections
- Related pages: [Page](../records/example.md)
```

### Synthesis Page

```markdown
# {Title}

## Pattern
{The cross-cutting pattern or strategic insight.}

## Evidence
{Which pages and sources support this pattern.}

## Inference
{What is being concluded beyond direct evidence.}

## Product Implication
{What Socratink should change next.}
```

## Coverage Manifest

`wiki/log-coverage.md` is required and uses:

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

Body:

```markdown
# Socratink Log Coverage

## Current Log Adapters
{What is currently instrumented and where it lands.}

## Missing Instrumentation
{What Socratink surfaces are not yet captured.}

## Notes
{Operational caveats and follow-up work.}
```

## Cross-Reference Rules

1. Every curated page must reference at least one other page or source.
2. Every curated page must be reachable from `wiki/index.md` directly or transitively.
3. Source pages should be the bridge from raw artifacts into derived records.
4. Findings/issues/experiments derived from logs should reference the relevant source page(s), not only the raw path.
5. Contradictions must be surfaced through `flags`, not hidden in prose.
6. `basis: mixed` is never allowed.
