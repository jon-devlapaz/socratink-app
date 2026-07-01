# Repository index

## Canonical docs
- `AGENTS.md` — binding instructions for all work in this repo.
- `CLAUDE.md` — compatibility adapter for Claude sessions.
- `GEMINI.md` — compatibility adapter for Gemini sessions.
- `agents/` — shared workflow canon and process scaffolding.

## Runtime hotspots
- `main.py` — FastAPI application and route wiring.
- `ai_service.py` — AI orchestration and drill evaluation.
- `auth/`, `db/`, `llm/`, `models/`, `source_intake/` — backend service modules.
- `public/` — frontend shell and app assets.
- `scripts/` — local dev/lint/deploy utilities.

## Verification entrypoints
- `tests/` + `pytest`.
- `scripts/doctor.sh` — preflight checks.
- `scripts/qa-smoke.sh` — browser smoke coverage.
- `scripts/check-coverage.sh` — diff coverage gate.
