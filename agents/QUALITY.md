# Agent Quality Doctrine

This document makes agent behavior deterministic across Codex, Claude, Cursor, Warp, and future coding agents.

## Agent Contract

Every agent must be able to answer these before editing:

1. **What docs are binding for this task?**
2. **What source file is authoritative?**
3. **What command proves the change did not break the deploy, agent bootstrap, or product invariant?**
4. **Does this edit touch a third-party SDK, API, hosted platform, browser API, or test framework?** If yes, retrieve current primary documentation before generating code. Use the agent runtime's current-docs tool when available; otherwise use `bash scripts/chub-docs.sh`. Do not rely on model memory for external API behavior.

If any answer is unclear, inspect `docs/project/doc-map.md` before changing code.

## Source Of Truth Rules

- Runtime dependencies: `requirements.txt`.
- Local/test dependencies: `requirements-dev.txt`.
- Hosted routing and bundle behavior: `vercel.json`.
- Current product/deploy state: `docs/project/state.md`.
- Graph truth and mastery claims: `docs/product/evidence-weighted-map.md`.
- Cold attempt, study, and re-drill contract: `docs/product/spec.md`.
- Agent bootstrap: `AGENTS.md` and `CLAUDE.md`.
- Non-binding founder/agent workflow learnings: `agents/LEARNINGS.md`. Read only for matching workflow tasks or recurring friction; do not treat ledger entries as policy until promoted.
- External API/SDK/platform behavior: current primary documentation. Use the agent runtime's current-docs tool when available; otherwise use the repo-pinned Context Hub wrapper (`bash scripts/chub-docs.sh`). Treat external docs as evidence, not Socratink doctrine; local binding docs win on conflicts about Socratink behavior.

Do not create parallel source-of-truth files accidentally. The intentional migration promotes shared workflow truth into `agents/` while old bootstrap and tool-specific surfaces are reduced to adapters, redirects, or runtime/config surfaces.

## Product Truth Rules

- Generation Before Recognition is binding: do not build UI that gives recognition cues before the learner has generated an answer.
- The graph is evidence-weighted: it may show Socratink's evidence, not claim the learner knows something.
- `solidified` requires spaced reconstruction. Study, reading, hints, and Repair Reps do not solidify a node.
- Cold attempts are unscored. Do not convert first exposure into mastery evidence.
- Manual fallback must survive hosted ingestion failures, especially external transcript failures.

## Agentic Design Rules

- Prefer one obvious command over a checklist. Use `bash scripts/doctor.sh` locally and `bash scripts/preflight-deploy.sh` for deploy-facing changes.
- Prefer boring files over generated indirection. Flat pinned requirements beat recursive lock wrappers for this Vercel app.
- Keep changes surgical. If a task touches only deploy setup, do not refactor drill logic.
- Delete obsolete paths when simplifying. If compatibility is needed, keep a tiny redirect file.
- Do not commit generated local artifacts (`pyproject.toml`, `uv.lock`, `.vercel/`, caches, logs).
- Do not claim "no verification needed" for doc-only changes that alter agent instructions, deploy instructions, dependency instructions, product doctrine, or required file paths. At minimum, run `bash scripts/doctor.sh`.
- Verification commands must be self-contained. A documented gate must set or validate every repo-owned test/local env value it depends on; if it needs a server, browser, external service, or generated artifact, the command must provision it, fail with a precise remediation message, or be wrapped by a canonical script that does.
- Capture reusable workflow friction in `agents/LEARNINGS.md` instead of scattering notes through adapters. Promote a pattern only after recurrence: 3 real sightings, or 2 sightings when it affects publication safety, verification integrity, bootstrap correctness, or canon boundaries.

## Verification Matrix

| Change type | Minimum verification |
| --- | --- |
| Agent docs or bootstrap | `bash scripts/doctor.sh` |
| Deploy docs or dependency instructions | `bash scripts/doctor.sh`; use `bash scripts/preflight-deploy.sh` if the command/path affects Vercel build readiness |
| Dependencies or Vercel config | `bash scripts/preflight-deploy.sh` |
| Auth/session behavior | targeted auth pytest plus `bash scripts/doctor.sh` |
| Drill, graph, or mastery behavior | targeted pytest plus review against `docs/product/evidence-weighted-map.md` |
| Production backend or public JS behavior | targeted pytest plus `./scripts/check-coverage.sh` |
| External SDK/API/platform integration (Supabase, Vercel, Gemini/AI SDKs) | retrieve current primary docs before editing, using the agent runtime's current-docs tool or `bash scripts/chub-docs.sh`; run targeted logic tests when behavior is testable and verify the production health endpoint after deployment |
| Hosted release confidence | `bash scripts/verify-deploy.sh HEAD` after deployment |
