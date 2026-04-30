# Agent Quality Doctrine

This document makes agent behavior deterministic across Codex, Claude, Cursor, Warp, and future coding agents.

## Agent Contract

Every agent must be able to answer these before editing:

1. **What docs are binding for this task?**
2. **What source file is authoritative?**
3. **What command proves the change did not break the deploy, agent bootstrap, or product invariant?**

If any answer is unclear, inspect `docs/project/doc-map.md` before changing code.

## Source Of Truth Rules

- Runtime dependencies: `requirements.txt`.
- Local/test dependencies: `requirements-dev.txt`.
- Hosted routing and bundle behavior: `vercel.json`.
- Current product/deploy state: `docs/project/state.md`.
- Graph truth and mastery claims: `docs/product/evidence-weighted-map.md`.
- Cold attempt, study, and re-drill contract: `docs/product/spec.md`.
- Agent bootstrap: `docs/codex/onboarding.md`.

Do not create parallel source-of-truth files unless the user explicitly asks for a migration and the old path is removed or reduced to a redirect.

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

## Verification Matrix

| Change type | Minimum verification |
| --- | --- |
| Agent docs or bootstrap | `bash scripts/doctor.sh` |
| Deploy docs or dependency instructions | `bash scripts/doctor.sh`; use `bash scripts/preflight-deploy.sh` if the command/path affects Vercel build readiness |
| Dependencies or Vercel config | `bash scripts/preflight-deploy.sh` |
| Auth/session behavior | targeted auth pytest plus `bash scripts/doctor.sh` |
| Drill, graph, or mastery behavior | targeted pytest plus review against `docs/product/evidence-weighted-map.md` |
| Hosted release confidence | `bash scripts/verify-deploy.sh HEAD` after deployment |
