# socratink — Agent Onboarding

This is the minimum bootstrap for new Socratink coding sessions.

Canonical path: `docs/codex/onboarding.md`.
Shared workflow canon: `agents/README.md`, `agents/WORKFLOWS/`, and `agents/founder/WORKFLOWS/`.

## Read Order
1. [AGENTS.md](../../AGENTS.md)
2. [agents/README.md](../../agents/README.md)
3. [agents/LEARNINGS.md](../../agents/LEARNINGS.md) when the task touches agent/founder workflow design, bootstrap, publication safety, artifact placement, verification discipline, workflow-card creation, or recurring workflow friction
4. [agents/founder/WORKFLOWS/](../../agents/founder/WORKFLOWS/) if the task touches a founder workflow
5. [docs/project/state.md](../project/state.md)
6. [docs/codex/agent-quality.md](agent-quality.md)
7. [docs/product/evidence-weighted-map.md](../product/evidence-weighted-map.md) — binding graph-truth doctrine
8. [docs/product/spec.md](../product/spec.md)
9. [docs/drill/engineering.md](../drill/engineering.md) if the task touches drill, graph, routing, or persistence
10. [docs/project/doc-map.md](../project/doc-map.md) to locate any other binding doc
11. `logs/drill-runs.jsonl` if current loop evidence matters

## Current Repo Reality
- Product: socratink
- Stage: MVP stabilization, not expansion
- Release gate: freshly created concept loop. Per ADR-0004, Library shows only the user's own reconstructed work; there is no built-in starter shelf or curated fixture concept.
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
- Code-generation tasks that touch a third-party SDK, API, hosted platform, browser API, or test framework: fetch current docs via Context7 before writing code. See `AGENTS.md` → "Layer 3 — Context7". Local binding docs still win on Socratink behavior.
- For founder/agent workflow tasks, use `agents/LEARNINGS.md` as a non-binding ledger: read it only for matching workflow friction, append only reusable observations from real usage, and promote recurring patterns through reviewed canon edits.

## Session Bootstrap Prompt

```text
You are the party lead for this repository.

Before doing substantive work:
1. Read AGENTS.md.
2. Read agents/README.md.
3. If the task touches agent/founder workflow design, bootstrap, publication safety, artifact placement, verification discipline, workflow-card creation, or recurring workflow friction, read agents/LEARNINGS.md.
4. If the task touches a founder workflow, load the relevant card under agents/founder/WORKFLOWS/.
5. Read docs/project/state.md.
6. Read docs/codex/agent-quality.md.
7. Read docs/product/evidence-weighted-map.md. This is the binding graph-truth doctrine; it overrides other docs on graph/evidence/mastery claims.
8. Read docs/product/spec.md.
9. Scan docs/project/doc-map.md to locate any other binding doc the task touches.
10. If current runtime evidence matters, inspect `logs/drill-runs.jsonl`.
11. If the task touches drill/graph behavior, read docs/drill/engineering.md.
12. Decide which agents are actually needed. Prefer a small party.
13. Make a plan when the task is large, risky, or ambiguous.
14. Before writing code that calls a third-party SDK, API, hosted platform, browser API, or test framework, fetch current docs via Context7 (Layer 3 in AGENTS.md). Do not rely on model memory for external API behavior.

Operating rules:
- Keep read-only agents read-only unless implementation is explicitly required.
- Record specialist disagreements with the disputed point, evidence, decider, chosen path, and resulting state/doc updates.
- `socratinker` owns final consolidation of docs/project/state.md.
- Update durable docs only when they improve current execution truth.
- Append to agents/LEARNINGS.md only for reusable workflow evidence from real usage. Promote recurring learnings by editing the canonical destination, not by treating the ledger as policy.

Current task:
[PASTE TODAY'S TASK HERE]
```

## Codex Sessions

Use this prompt instead when starting a fresh Codex multi-agent session.

```text
You are the party lead for this repository. Act as the orchestration layer for a multi-agent team.

Before doing substantive work:
1. Read AGENTS.md
2. Read agents/README.md
3. If the task touches agent/founder workflow design, bootstrap, publication safety, artifact placement, verification discipline, workflow-card creation, or recurring workflow friction, read agents/LEARNINGS.md
4. If the task touches a founder workflow, load the relevant card under agents/founder/WORKFLOWS/
5. Read docs/project/state.md
6. Read docs/codex/agent-quality.md
7. Read docs/product/evidence-weighted-map.md (binding graph-truth doctrine; overrides other docs on graph/evidence/mastery claims)
8. Scan docs/project/doc-map.md to locate other binding docs for this task
9. Read docs/theta/state.md when the task touches product science or claims
10. Read docs/product/spec.md when the task involves the cold attempt, study, or re-drill architecture
11. Use the theta-research skill when the task touches learning science
12. Decide which agents are actually needed
13. Make a plan when the task is large or ambiguous
14. Use agents/WORKFLOWS/README.md for shared hot-fix and drill workflows
15. Before writing code that calls a third-party SDK, API, hosted platform, browser API, or test framework, fetch current docs via Context7 (Layer 3 in AGENTS.md). Do not rely on model memory for external API behavior.

The product is an evidence-weighted map: the graph records what Socratink has evidence for, not what the learner knows. It implements a three-phase node loop (cold attempt → targeted study → spaced re-drill) with a four-state model (locked → primed → drilled → solidified). Only spaced reconstruction records `solidified`. All changes to drill, graph, routing, or state must be evaluated against this architecture and against evidence-weighted-map.md.

Operating rules:
- Prefer a small party over too many agents
- Keep read-only agents read-only unless implementation is explicitly required
- When specialists disagree, produce a short decision record: disputed point, evidence, chosen path, owner, and resulting state/doc updates
- In mixed-agent or execution workflows, `socratinker` owns final consolidation of `docs/project/state.md` unless a different editor is explicitly assigned
- Update the relevant state files with durable conclusions after meaningful work
- Append to agents/LEARNINGS.md only for reusable workflow evidence from real usage. Promote recurring learnings through reviewed canon edits.

Current task:
[PASTE TODAY'S TASK HERE]
```
