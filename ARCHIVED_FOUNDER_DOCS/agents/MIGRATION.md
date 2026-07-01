# Agent Canon Migration

The row-by-row migration ledger has served its purpose. Do not rebuild it as a
second registry of canon surfaces.

Current rule:

- shared workflow canon lives in `agents/`
- `AGENTS.md` is the root repo entrypoint and still carries binding repo doctrine
- `CLAUDE.md` and `GEMINI.md` are compatibility adapters only
- `.claude/`, `.codex/`, `.gemini/`, and other tool-specific directories are runtime/config/wrapper surfaces
- `.agents/` is local substrate only
- durable product canon lives in `PRODUCT.md`, `DESIGN.md`, `UBIQUITOUS_LANGUAGE.md`, `AGENTS.md`, and `docs/project/doc-map.md`

If a future migration is needed, make it time-boxed: name the owner, review date,
scope, and exit condition in the owning canonical file instead of accumulating
historical rows here.
