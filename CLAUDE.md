# CLAUDE.md

Behavioral rules. Trivial task → judgment override OK.

## 1. Think Before Coding
- State assumptions. Uncertain → ask.
- Multiple interpretations → present all, don't pick silently.
- Simpler approach exists → say so. Push back when warranted.
- Unclear → stop. Name the confusion. Ask.

## 2. Simplicity First
- No features beyond ask.
- No abstractions for single-use code.
- No flexibility/configurability not requested.
- No error handling for impossible scenarios.
- 200 lines that could be 50 → rewrite.

## 3. Surgical Changes
- Don't "improve" adjacent code/comments/formatting.
- Don't refactor what isn't broken.
- Match existing style.
- Unrelated dead code → mention, don't delete.
- Remove orphans YOUR change created. Pre-existing dead code stays unless asked.
- Test: every changed line traces to user request.

## 4. Goal-Driven Execution
Transform tasks → verifiable goals:
- "Add validation" → write tests for invalid inputs, make pass.
- "Fix bug" → write reproducing test, make pass.
- "Refactor X" → tests pass before+after.

Multi-step → state plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

## MCP: code-review-graph

ALWAYS use graph tools BEFORE Grep/Glob/Read. Faster, cheaper, gives callers/dependents/test coverage.

| Tool | Use when |
|------|----------|
| `get_minimal_context_tool` | START HERE — ~100 tokens, returns risk+communities+flows+next_tool_suggestions |
| `detect_changes` | Reviewing changes — risk-scored |
| `get_review_context` | Need source snippets — token-efficient |
| `get_impact_radius` | Blast radius |
| `get_affected_flows` | Impacted execution paths |
| `query_graph` | callers/callees/imports/tests/deps; prefer `target=...` over broad `list_*` |
| `semantic_search_nodes` | Find by name/keyword |
| `get_architecture_overview` | High-level structure |
| `refactor_tool` | Renames, dead code |

Rules:
- Default `detail_level="minimal"`. Escalate to `"standard"` only if insufficient.
- Graph auto-updates via hooks.
- **Floor caveat:** CALLS counts under-report. For "only call site" claims, `rg "<symbol>"` first.
- Fallback to Grep/Glob/Read ONLY when graph doesn't cover.

Project skills (`.claude/skills/`): `review-changes`, `explore-codebase`, `debug-issue`, `refactor-safely`. Runbook: `docs/code-review-graph-sop.md`.

## /pipette

User-invokable heavy-planning pipeline. Read `docs/superpowers/specs/2026-04-28-pipette-design.md` and `docs/superpowers/plans/2026-04-28-pipette.md` before invoking. `/pipette doctor` validates prerequisites; `/pipette <topic>` runs Steps −1→7 with deterministic gates and per-feature artifacts under `docs/pipeline/`. Pause/resume via `/pipette resume <topic>`; abort via `/pipette abort <topic>`.

## QA: Browser Smoke

Load-bearing deploy verification. "Pushed to main" ≠ "verified."

```bash
bash scripts/qa-smoke.sh live                         # production (https://app.socratink.ai)
bash scripts/qa-smoke.sh local                        # local (uvicorn must be running)
bash scripts/qa-smoke.sh https://custom-url.com       # explicit URL
bash scripts/qa-smoke.sh                              # local (default)
```

Stack: pytest + playwright-python. Suite: `tests/e2e/test_smoke.py` (9 tests, ~15s warm / ~40s cold). Read-only — safe against prod.

9 checks: `/api/health` shape, homepage critical DOM (`#drawer`, `#bottom-nav`, `#concept-list`, brand mark), guest sessions labeled as guest, drawer toggle stays visible after entering a concept, saved library cards reopen the concept-map view, deleting the active concept confirms then resets to the desk, zero same-origin console errors on first paint, zero same-origin asset failures, theme-preloader resilient to blank `localStorage`.

Run WITHOUT being asked when:
- After deploy / merge to main / `git push origin main` + any verification framing
- Before claiming "the site works" / "X is live" / "deploy is healthy"
- When user reports "is prod broken?" or describes a hosted-only symptom
- After a CRG-flagged high-risk change to `main.py`, `api/index.py`, or `public/index.html`

Rules:
- Same-origin failures are real bugs. Cross-origin noise is already filtered — don't allow-list it unless proven third-party.
- On failure: paste the pytest output verbatim. Trace at `test-results/<test>/trace.zip` (`playwright show-trace ...`).
- Project doctrine: **local success ≠ hosted validation**. The smoke is the cheapest hosted-validation signal we have.
- Extension: `authenticated_page` fixture (see `tests/e2e/README.md`) for future flow tests against `selectTile` / `runHeroAction` / `toggleTheme` / `importLibraryConcept`.

Three entry points:
- `/verify-deploy` (skill) — waits for Vercel to finish then runs smoke. Use after a push to confirm a specific commit is live. Wrapper: `scripts/verify-deploy.sh`.
- `bash scripts/qa-smoke.sh local|live|<url>` — immediate smoke, no Vercel wait. Use when prod is already up and you just want a health check.
- Hourly synthetic monitor (trigger `socratink-app-qa-smoke`, id `trig_01Xkjm7rEufGE2SbTv9Eaxe7`) — runs every hour against prod. Manage at https://claude.ai/code/scheduled.

Docs: `tests/e2e/README.md`.

## Local-First Search
- Check `~/.claude/skills/` + local resources BEFORE remote/agents.
- Before building new functionality, verify no existing skill/script does it.
- "How do I X" / "what does X do" / "is there a way to…" → FIRST run:
  ```bash
  ls ~/.claude/skills/ && grep -r <keyword> ~/.claude/skills/ .claude/ docs/ 2>/dev/null
  ```
  Remote (WebFetch/WebSearch/claude-code-guide) only if local empty.

## Multi-Agent & Worktree Safety
- Code-modifying agents → verify against latest uncommitted state, not just HEAD.
- Worktree/branch conflicts → surface honestly. Never fabricate resolutions.
- Multi-phase refactors → peer review (codex/gemini) before merge.

## MVP Scope Discipline
- Deployment blockers vs nice-to-have polish — conservative on blockers.
- MVP: accept tradeoffs unless data loss / security hole / core flow breakage.
- User/Codex classifies issue acceptable → defer.
