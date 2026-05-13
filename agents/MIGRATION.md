# Agent Canon Migration Ledger

Use this ledger to track migration from tool-specific surfaces into `agents/`.

## Status vocabulary

- `promoted`
- `adapter-only`
- `tool-specific`
- `preserved-pending-review`
- `deprecated`

## Entry hygiene

For any non-terminal entry (`adapter-only` or `preserved-pending-review`), record in the notes:

- current owner of the migration decision
- last review date
- exit condition that would move the surface to `promoted`, `tool-specific`, or `deprecated`

## Initial entries

| Surface | Status | Notes |
| --- | --- | --- |
| `AGENTS.md` | `preserved-pending-review` | cross-agent root entrypoint and still-binding repo doctrine surface; owner: founder canon migration, reviewed_at: 2026-05-13, exit: either shrink to a true entrypoint or explicitly retain as the intentional binding root alongside `agents/` |
| `CLAUDE.md` | `adapter-only` | Claude compatibility pointer into canon |
| `GEMINI.md` | `adapter-only` | Gemini compatibility pointer into canon |
| `docs/codex/onboarding.md` | `promoted` | shared bootstrap doctrine moved to `agents/ONBOARDING.md`; old Codex namespace no longer authoritative |
| `docs/codex/agent-quality.md` | `promoted` | shared quality doctrine moved to `agents/QUALITY.md`; old Codex namespace no longer authoritative |
| `docs/codex/decision-log.md` | `promoted` | append-only decision record moved to `agents/_logs/decision-log.md` |
| `docs/codex/agent-review-log.md` | `promoted` | append-only agent review record moved to `agents/_logs/agent-review-log.md` |
| `docs/codex/customer-persona-prompt-template.md` | `promoted` | reusable agent template moved to `agents/_templates/customer-persona-prompt.md` |
| `docs/codex/socratink-brain-workflow-architecture.md` | `deprecated` | deleted deprecated stub; authority remains `.socratink-brain/CLAUDE.md` |
| `.claude/` | `tool-specific` | runtime skills/settings surface |
| `.claude/friction-log.md` | `preserved-pending-review` | raw sediment log; curate repeated workflow patterns into `agents/LEARNINGS.md`, but do not treat the source log as canon |
| `.claude/settings.json` | `tool-specific` | Claude runtime hook/config surface; do not migrate into `agents/` |
| `.claude/settings.local.json` | `tool-specific` | local Claude runtime/config surface; do not migrate |
| `.claude/settings.example.json` | `tool-specific` | Claude setup example, not shared workflow doctrine |
| `.claude/skills/git-order/SKILL.md` | `adapter-only` | workflow doctrine promoted into `agents/founder/WORKFLOWS/02-git-homeostasis.md`; owner: founder canon migration, reviewed_at: 2026-05-13, exit: wrapper contains only packaging pointer plus trigger metadata |
| `.claude/skills/prototype/SKILL.md` | `adapter-only` | workflow doctrine promoted into `agents/founder/WORKFLOWS/03-prototyping.md`; owner: founder canon migration, reviewed_at: 2026-05-13, exit: wrapper contains only packaging pointer plus trigger metadata |
| `.claude/skills/prototype/LOGIC.md` | `deprecated` | logic branch absorbed into `agents/founder/WORKFLOWS/03-prototyping.md`; keep only for backward compatibility until no references remain |
| `.claude/skills/prototype/UI.md` | `deprecated` | UI branch absorbed into `agents/founder/WORKFLOWS/03-prototyping.md`; keep only for backward compatibility until no references remain |
| `.claude/skills/verify-deploy.md` | `adapter-only` | workflow doctrine promoted into `agents/founder/WORKFLOWS/04-deploy-verification.md`; owner: founder canon migration, reviewed_at: 2026-05-13, exit: wrapper contains only packaging pointer plus trigger metadata |
| `.claude/skills/use-context7.md` | `tool-specific` | mostly redundant with current `AGENTS.md` Layer 3 policy; keep as a Claude wrapper |
| `.claude/skills/review/SKILL.md` | `tool-specific` | Claude-packaged review wrapper, not shared canon |
| `.claude/skills/debug-issue.md` | `tool-specific` | tool wrapper for graph-based debugging, not shared canon |
| `.claude/skills/explore-codebase.md` | `tool-specific` | tool wrapper for graph-based exploration, not shared canon |
| `.claude/skills/refactor-safely.md` | `tool-specific` | tool wrapper for graph-assisted refactoring, not shared canon |
| `.claude/skills/review-changes.md` | `tool-specific` | tool wrapper for graph-based review, not shared canon |
| `.claude/skills/socratink-design/SKILL.md` | `tool-specific` | wrapper over already-canonical design docs, not a new canon surface |
| `.claude/skills/empirical-grill/SKILL.md` | `tool-specific` | slash-command-heavy Claude workflow; not ready for cross-model canon |
| `.codex/` | `tool-specific` | runtime/config/memory surface |
| `.gemini/` | `tool-specific` | runtime/config/auth surface |
| `.agents/` | `tool-specific` | local substrate only; use only for external install-state under `.agents/skills/` and ignored runtime evidence under `.agents/runtime/` |
| `.agents/skills/fastapi/` | `tool-specific` | external project-local installed skill; keep out of shared canon |
| `.agents/skills/gemini-interactions-api/` | `tool-specific` | external project-local installed skill; keep out of shared canon |
| `.agents/skills/playwright-cli/` | `tool-specific` | external project-local installed skill; keep out of shared canon |
