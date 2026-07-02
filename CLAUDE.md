# CLAUDE.md

Socratink App is a production learning platform with FastAPI-backed APIs, auth, and prompt-heavy frontend workflows.

This repository is the primary source for AI-agent routing and safe editing instructions.

## Session checklist
- Before coding, read this file and `AGENTS.md`.
- Verify runtime commands and dependency bootstraps before changes.
- Run the documented local fast tests before opening a PR.
- Keep edits scoped to the user request and avoid speculative refactors.

## If session state is unclear
- If this file is not available, fall back to `AGENTS.md` and then `README.md`.
- If this is a read-only review mode, avoid commands that write to files unless explicitly requested.
- If test runs are unavailable, document blocked checks in the task summary.

## Build commands
- `bash scripts/bootstrap-python.sh`
- `bash scripts/dev.sh`

## Test commands
- `npm test`
- `.venv/bin/pytest -q --strict-markers`
- `bash scripts/doctor.sh`

## Local test
```bash
.venv/bin/pytest -q tests/unit
.venv/bin/pytest -q tests/unit -k "not slow"
```

## How to start
- If you need reproducible local smoke checks, run `bash scripts/qa-smoke.sh`.

## Routing commands
- Confirm working directory with `pwd` and repository root with `git rev-parse --show-toplevel`.
- Confirm status and diff scope before touching files.
- Confirm test target and command with this file before every commit.

## Conditional loading guidance
- If the machine is CPU-limited or offline, skip `.venv/bin/playwright install chromium`.
- If local dependencies are unavailable, skip browser-heavy coverage and run API-only checks.
- If this is a read-only environment, avoid bootstrap and migration commands.

## Rules with reasons
- Don't run full `npm test` without filtering; this can consume expensive resources and mask targeted failures.
  Because: fast local feedback should run first before expensive integration commands.
- Don't edit auto-generated coverage artifacts in `coverage/` or `.pytest_cache/`.
  Because: these folders are disposable and not part of source truth.
- Don't assume every workflow is required for every task.
  Because: focused work reduces churn and keeps CI noise low.
- Do not change `.env` values in tracked files.
  Because: environment files are runtime secrets policy.

## Work commands
- Server start: `bash scripts/bootstrap-python.sh` then `bash scripts/dev.sh`.
- Deploy preflight: `bash scripts/preflight-deploy.sh` when needed.
- Frontend smoke: `bash scripts/qa-smoke.sh local` with the dev server running.

## Development constraints
- Keep changes minimal and reversible when possible.
- Prefer config over behavior edits if a request is infrastructure-only.
- Avoid editing tests for speculative or unrelated paths.

## Code style conventions
- Use existing async style and existing response schemas.
- Keep Python changes compatible with existing `ruff` and `pytest` conventions.
- Preserve established route and agent boundaries.

## Commit workflow notes
- Keep task notes brief and link to evidence when reporting changes.
- Log blockers and manual follow-ups in the task summary so the next session can continue.
- Update `docs/project/state.md` for larger direction changes.

## Operational notes
- `AGENTS.md` contains broader policy and long-form operating contracts.
- `docs/project/doc-map.md` routes product-moving documents.
- Do not change `.env` values in tracked files.
  Because: environment files are runtime secrets policy.
