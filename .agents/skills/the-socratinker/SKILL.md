---
name: the-socratinker
description: Use when building, maintaining, querying, linting, or health-checking Socratink's internal product-memory knowledge base; when ingesting product docs, research notes, drill or other product chat logs, test/replay traces, bug reports, screenshots, and experiment notes; or when evaluating those artifacts to produce durable doctrine, mechanisms, decisions, issues, findings, experiments, and syntheses for Socratink.
---

You are using The Socratinker skill.

Purpose:
- Build and maintain Socratink's internal product-memory knowledge base.
- Compile durable understanding from raw artifacts instead of re-deriving product truth on every query.
- Treat chat logs and test logs as first-class product evidence.

Use this skill for Socratink internal work only in v1. Do not use it to build learner-facing knowledge bases yet.

Default KB root:
- Use `.socratinker/` when it exists.
- If `.socratinker/` is missing, search for a nearby `wiki/index.md`.
- If more than one candidate KB exists, ask which one to use before writing.

Operation router:
- "feed this", "ingest this", "add this research/log/note" -> `ingest`
- "what do we know about X?", "query Socratinker" -> `query`
- "evaluate these logs/traces/replays" -> `evaluate-logs`
- "validate", "lint", "is the KB structurally healthy?" -> `lint`
- "health check", "review the KB", "find contradictions/stale memory" -> `health-check`
- "compile this into product memory" -> `ingest`
- "promote this", "add to active queue" -> update `ACTIVE.md` only if the item affects one of the eight loop behaviors under `docs/project/state.md#current-release-goal`
- "demote this", "drop from active", "done" -> remove the `ACTIVE.md` item or point back to compiled wiki memory

Workflow:
1. Read `references/schema-template.md` before initializing or reshaping a KB.
2. Read `references/page-conventions.md` before creating or updating compiled pages.
3. Read `references/log-surfaces.md` when the task touches logs, coverage, or missing instrumentation.
4. For `init`, create the KB contract exactly as described in the schema template.
5. For `ingest`, register raw artifacts first, create or update a source page, then promote derived pages only when the artifact changes doctrine, mechanism, release risk, decision state, instrumentation truth, or active MVP priorities.
6. For `query`, navigate from `wiki/index.md` and answer from compiled pages before touching raw artifacts.
7. For `evaluate-logs`, ingest known log files, derive findings/issues/experiments/syntheses, and update `wiki/log-coverage.md`.
8. For `lint`, use `scripts/validate_wiki.py` only for deterministic structural checks.
9. For `health-check`, do semantic and epistemic review separately from `lint`: check stale claims, hidden contradictions, weak provenance, over-promoted active work, source pages without compiled implications, and missing instrumentation.
10. If a Socratink chat or test surface is expected but not instrumented, record it explicitly as missing coverage.

`ACTIVE.md` contract:
- Keep at most 5 promoted items.
- Each item must link to a curated wiki page and cite `docs/project/state.md#current-release-goal` inline.
- The release-goal validation standard is the eight loop behaviors listed under that exact heading.
- Interesting but non-release-relevant artifacts stay in `wiki/`, not `ACTIVE.md`.

Non-negotiable constraints:
- Generation Before Recognition is binding.
- The graph must tell the truth.
- Attempted is not mastered.
- Distinguish evidence, inference, and hypothesis explicitly.
- `basis: mixed` is not allowed.
- Missing instrumentation is a health gap, not a silent omission.

Operations:
- `init`: create the KB structure and seed the contract.
- `ingest`: add raw artifacts and update compiled memory.
- `query`: answer from compiled memory first and surface contradictions.
- `lint`: run deterministic structural validation only.
- `health-check`: run LLM-driven semantic and epistemic evaluation.
- `evaluate-logs`: turn Socratink chat/test logs into product memory.

Output expectations:
- Prefer compact, explicit pages over broad summaries.
- Every non-source page must state the product implication.
- Every log-derived conclusion must be traceable back to a source page and raw artifact path.
