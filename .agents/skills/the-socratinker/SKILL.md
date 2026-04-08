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

Workflow:
1. Read `references/schema-template.md` before initializing or reshaping a KB.
2. Read `references/page-conventions.md` before creating or updating compiled pages.
3. Read `references/log-surfaces.md` when the task touches logs, coverage, or missing instrumentation.
4. For `init`, create the KB contract exactly as described in the schema template.
5. For `ingest`, register raw artifacts first, then update compiled pages deliberately.
6. For `query`, navigate from `wiki/index.md` and answer from compiled pages before touching raw artifacts.
7. For `evaluate-logs`, ingest known log files, derive findings/issues/experiments/syntheses, and update `wiki/log-coverage.md`.
8. For `lint`, use `scripts/validate_wiki.py` only for deterministic structural checks.
9. For `health-check`, do semantic and epistemic review separately from `lint`.
10. If a Socratink chat or test surface is expected but not instrumented, record it explicitly as missing coverage.

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
- `compile`: convert raw evidence into doctrine, mechanisms, records, sources, and syntheses.
- `query`: answer from compiled memory first and surface contradictions.
- `lint`: run deterministic structural validation only.
- `health-check`: run LLM-driven semantic and epistemic evaluation.
- `evaluate-logs`: turn Socratink chat/test logs into product memory.

Output expectations:
- Prefer compact, explicit pages over broad summaries.
- Every non-source page must state the product implication.
- Every log-derived conclusion must be traceable back to a source page and raw artifact path.
