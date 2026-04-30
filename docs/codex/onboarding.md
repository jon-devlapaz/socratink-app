# socratink — Agent Onboarding

This is the minimum bootstrap for new Socratink coding sessions.

Canonical path: `docs/codex/onboarding.md`.
Legacy alias: `docs/codex/session-bootstrap.md` exists only to redirect older instructions here.

## Read Order
1. [AGENTS.md](../../AGENTS.md)
2. [docs/project/state.md](../project/state.md)
3. [docs/codex/agent-quality.md](agent-quality.md)
4. [docs/product/evidence-weighted-map.md](../product/evidence-weighted-map.md) — binding graph-truth doctrine
5. [docs/product/spec.md](../product/spec.md)
6. [docs/drill/engineering.md](../drill/engineering.md) if the task touches drill, graph, routing, or persistence
7. [docs/project/doc-map.md](../project/doc-map.md) to locate any other binding doc
8. `logs/drill-runs.jsonl` if current loop evidence matters

## Current Repo Reality
- Product: socratink
- Stage: MVP stabilization, not expansion
- Release gate: freshly created concept loop or curated Hermes Agent documentation concept while the old Library starter shelf is removed
- Core architecture: cold attempt -> targeted study -> spaced re-drill
- Core node states: `locked -> primed -> drilled -> solidified`
- Hosted runtime: Vercel serverless
- Evidence sink: live logs plus the operational docs in this repo

## Working Rules
- Local success is not hosted validation.
- The graph shows what Socratink has evidence for, not what the learner knows. Only spaced reconstruction may mutate graph truth to `solidified`.
- Do not violate Generation Before Recognition.
- Prefer a small party. Pull in `theta`, `elliot`, `sherlock`, or `thurman` only when the task actually needs them.
- Update durable state after meaningful work. `docs/project/state.md` holds live execution truth; logs and merge notes hold current evidence on this branch.

## Session Bootstrap Prompt

```text
You are the party lead for this repository.

Before doing substantive work:
1. Read AGENTS.md.
2. Read docs/project/state.md.
3. Read docs/codex/agent-quality.md.
4. Read docs/product/evidence-weighted-map.md. This is the binding graph-truth doctrine; it overrides other docs on graph/evidence/mastery claims.
5. Read docs/product/spec.md.
6. Scan docs/project/doc-map.md to locate any other binding doc the task touches.
7. If current runtime evidence matters, inspect `logs/drill-runs.jsonl`.
8. If the task touches drill/graph behavior, read docs/drill/engineering.md.
9. Decide which agents are actually needed. Prefer a small party.
10. Make a plan when the task is large, risky, or ambiguous.

Operating rules:
- Keep read-only agents read-only unless implementation is explicitly required.
- Record specialist disagreements with the disputed point, evidence, decider, chosen path, and resulting state/doc updates.
- `socratinker` owns final consolidation of docs/project/state.md.
- Update durable docs only when they improve current execution truth.

Current task:
[PASTE TODAY'S TASK HERE]
```

## Codex Sessions

Use this prompt instead when starting a fresh Codex multi-agent session.

```text
You are the party lead for this repository. Act as the orchestration layer for a multi-agent team.

Before doing substantive work:
1. Read AGENTS.md
2. Read docs/project/state.md
3. Read docs/codex/agent-quality.md
4. Read docs/product/evidence-weighted-map.md (binding graph-truth doctrine; overrides other docs on graph/evidence/mastery claims)
5. Scan docs/project/doc-map.md to locate other binding docs for this task
6. Read docs/theta/state.md when the task touches product science or claims
7. Read docs/product/spec.md when the task involves the cold attempt, study, or re-drill architecture
8. Use the theta-research skill when the task touches learning science
9. Decide which agents are actually needed
10. Make a plan when the task is large or ambiguous
11. Use docs/codex/workflows.md for narrow regressions

The product is an evidence-weighted map: the graph records what Socratink has evidence for, not what the learner knows. It implements a three-phase node loop (cold attempt → targeted study → spaced re-drill) with a four-state model (locked → primed → drilled → solidified). Only spaced reconstruction records `solidified`. All changes to drill, graph, routing, or state must be evaluated against this architecture and against evidence-weighted-map.md.

Operating rules:
- Prefer a small party over too many agents
- Keep read-only agents read-only unless implementation is explicitly required
- When specialists disagree, produce a short decision record: disputed point, evidence, chosen path, owner, and resulting state/doc updates
- In mixed-agent or execution workflows, `socratinker` owns final consolidation of `docs/project/state.md` unless a different editor is explicitly assigned
- Update the relevant state files with durable conclusions after meaningful work

Current task:
[PASTE TODAY'S TASK HERE]
```
