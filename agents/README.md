# agents/

Canonical shared workflow truth for repo agents.

## What belongs here

- workflow cards
- templates
- migration ledgers
- founder orchestration doctrine
- prompt batteries
- shared decision rubrics

## What does not belong here

- runtime executables already owned by `scripts/`
- auth/session state
- caches
- tool-specific hooks/settings syntax

## Authority rule

`agents/` is the shared canon. `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` are entrypoint adapters into this canon. Tool-specific directories like `.claude/`, `.codex/`, and `.gemini/` are runtime/config/wrapper surfaces, not canonical doctrine.

## Migration rule

Migrate selectively. Promote only stable, high-signal, cross-model content. Preserve high-value tool-local content until its signal is captured or intentionally deprecated.
