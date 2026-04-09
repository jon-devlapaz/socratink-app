# Founder Handoff

## Next Session Action Item

Read `AGENTS.md`, `docs/project/state.md`, and `docs/codex/session-bootstrap.md`, then review `.socratinker/ACTIVE.md` and implement the smallest thermostat replay verifier.

Concrete first slice:
- add `public/data/taste-fixtures/thermostat-loop.json`
- add assertion mode to `scripts/run_tasting_fixture.py`
- add `scripts/verify_thermostat_loop.py`

Guardrail:
- do not expand into persistence or auth unless you are explicitly choosing to override the current MVP release gate
