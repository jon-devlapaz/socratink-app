# Agent Canon Migration Ledger

Use this ledger to track migration from tool-specific surfaces into `agents/`.

## Status vocabulary

- `promoted`
- `adapter-only`
- `tool-specific`
- `preserved-pending-review`
- `deprecated`

## Initial entries

| Surface | Status | Notes |
| --- | --- | --- |
| `AGENTS.md` | `adapter-only` | repo root entrypoint; retains must-not-miss bootstrap rules |
| `CLAUDE.md` | `adapter-only` | Claude compatibility pointer into canon |
| `GEMINI.md` | `adapter-only` | Gemini compatibility pointer into canon |
| `docs/codex/onboarding.md` | `preserved-pending-review` | currently binding bootstrap surface; must point into canon |
| `docs/codex/agent-quality.md` | `preserved-pending-review` | currently binding quality/source-of-truth surface; must reflect canon |
| `.claude/` | `tool-specific` | runtime skills/settings surface |
| `.codex/` | `tool-specific` | runtime/config/memory surface |
| `.gemini/` | `tool-specific` | runtime/config/auth surface |
