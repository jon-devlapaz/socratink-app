# AGENTS.md

This file is the lightweight local operating guide for this repository.

## Core instruction source
- `CLAUDE.md` is the primary entry file for agent-facing context and lint checks.
- If this file is missing, use `README.md` and `.github/workflows/`.

## Scope
- Keep changes scoped to the explicit request.
- Prefer small, reversible edits over broad refactors.
- Record blockers and follow-ups in the task summary.

## Read this before edits
- Current architecture/truth lives in `README.md`, `docs/project/doc-map.md`, and `docs/project/state.md`.
- Runtime and deployment notes are in `.github/workflows/` and related scripts.
- Product doctrine lives in `PRODUCT.md`, `DESIGN.md`, and `UBIQUITOUS_LANGUAGE.md`.

## Safe change sequence
- Confirm branch and dirty state before touching files.
- Prefer docs/config edits before runtime commands for repo-level hygiene tasks.
- Run the documented local checks before opening a PR.

## Commands
- Setup: `bash scripts/bootstrap-python.sh`
- Local checks: `bash scripts/doctor.sh`
- App smoke: `bash scripts/qa-smoke.sh`

## Practical constraints
- Avoid editing generated artifacts.
- Keep dependency/security edits deliberate and version-aware.
- Ask before introducing new cross-platform behavior outside this repo workflow.

## Communication defaults
- Keep responses concise and action-oriented.
- Cite exact files and commands in changes and handoffs.
