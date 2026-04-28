# CODEX REVIEW — pipette Phase F + A0 (Milestone 4)

You are an independent reviewer. The pipette implementation plan
(`docs/superpowers/plans/2026-04-28-pipette.md`) was hardened over 28
rounds of prior gemini sanity-checks plus a ChatGPT audit. Phases B, C,
S already shipped (codex prompts at
`2026-04-28-phase-{b,c,s}-review.md`).

This review covers Phase F (slash command + weekly aggregator + CLAUDE.md
reference) and Task A0 (fake end-to-end integration test). The remaining
A1 dogfood is user-driven and out of scope here.

## What was supposed to deliver

- **F1** `.claude/commands/pipette.md` — verbatim transcription of the
  plan's Appendix A (~296 lines). Frontmatter `name: pipette`,
  user-invocable. Body covers Step −1 through Step 7. Tests at
  `tests/pipette/test_command_file.py`: 2 tests (frontmatter present,
  every step section referenced).

- **F2.a** `.claude/commands/pipette-weekly.md` — frontmatter
  `name: pipette-weekly`, `user-invocable: false`. Procedure has 5
  numbered steps (glob, parse, aggregate, write, commit). The cron
  registration (F2.b) was DEFERRED to the user per the project's
  pause-before-persistent-system-state policy.

- **F3** Append a 4-line `## /pipette` section to `CLAUDE.md` between
  the existing "MCP: code-review-graph" and "QA: Browser Smoke" sections.

- **A0** `tests/pipette/test_e2e_integration.py` — 5 tests exercising
  the slash-command-to-CLI contract end-to-end against fake everything
  (no real gemini, no real subagents, no real graph). Catches
  command-name and file-path drift between Appendix A and the Python
  CLI surface.

**Real defects surfaced and fixed mid-Phase-F:**

- `.gitignore` was blocking `.claude/commands/`. F1's implementer added
  whitelist patterns; later cleaned to `!.claude/commands/*.md` glob.
- `research_gate.write_brief` / `write_findings` / `_bump_caps` named
  files as `1.0-slug.md` because `argparse type=float` coerces `--step 1`
  to `1.0`. Fixed via a `_fmt_step()` helper that normalizes whole
  numbers (`1.0 → 1`) while preserving substeps (`1.5`).
- `orchestrator.archive_for_loop_back` had the same float-coercion bug
  on its `_attempts/<jump>-<ts>/` directory naming. Fixed inline.

Total after Phase F + A0: **88 tests pass**, `python -m tools.pipette
doctor` exits 0 with all 10 checks ✅ + structural validation passing.

## What to flag

Real defects only:

- `.claude/commands/pipette.md` content diverging from Appendix A
  (excluding the documented Step −1 ASCII vs. Unicode minus handling)
- Frontmatter shape wrong (must have `name: pipette`, valid YAML)
- Missing step references (the test catches Step -1, 0, 1, 1.5, 2, 3, 4,
  5, 6, 7 — but if any step section's body is empty or stub-only, that's
  a real defect)
- `pipette-weekly.md` schema wrong (must have `name: pipette-weekly`,
  `user-invocable: false`)
- CLAUDE.md `/pipette` section in the wrong location, or with wrong
  command-name references
- Integration test that mocks instead of actually exercises the CLI
  (each `_run()` call must shell out to `python -m tools.pipette`)
- The `_fmt_step` fix breaking substep handling (`1.5` MUST still
  produce `1.5-slug.md`, not `1-slug.md` or `1.5-slug.md` with extra
  decimals)
- `.gitignore` accidentally re-ignoring committed files

What NOT to flag:

- The cron registration not being done — that's deferred to the user
- Style preferences in the slash command markdown
- Locked decisions
- Stylistic gitignore organization (multiple negation lines vs. one
  glob — both work)

## Required output

Emit ONE YAML object and nothing else:

```yaml
verdict: PASS | NEEDS_CHANGES
confidence: 0.0–1.0
findings:
  - severity: critical | high | medium | low
    location: <commit SHA + file path>
    claim: <one sentence>
    evidence: <quoted line from diff>
    suggested_fix: <concrete>
notes: <one paragraph if cross-cutting>
```

`PASS` with empty findings is allowed. `NEEDS_CHANGES` requires ≥1
critical or high finding.

## Git range

Phase F + A0 starts immediately after Phase S's last commit (`f9bca55`
was the codex-prompt for Phase S; the last code commit was `b5490ed` —
pipeline_graph + validator). Phase F + A0 ends at A0's commit
(`8193dbe`). 6 implementation commits in between.

Capture log + diff:

```bash
git log f9bca55..HEAD --reverse > /tmp/phase_f_log.txt
git diff f9bca55..HEAD > /tmp/phase_f_diff.txt
```

Or pipe directly:

```bash
{ git log f9bca55..HEAD --reverse; echo; echo "=== DIFF ==="; echo;
  git diff f9bca55..HEAD; } | codex exec --prompt-file - \
  docs/superpowers/plans/codex-prompts/2026-04-28-phase-f-review.md
```

(Adjust `codex` invocation to match your local CLI.)
