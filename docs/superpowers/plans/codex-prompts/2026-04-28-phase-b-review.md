# CODEX REVIEW — pipette Phase B (Milestone 1)

You are an independent reviewer. The pipette implementation plan
(`docs/superpowers/plans/2026-04-28-pipette.md`) was hardened over 28 rounds of
prior gemini sanity-checks plus a ChatGPT audit; assume it is correct.

Your job: review the IMPLEMENTATION of Phase B (Tasks B1, B2, B3, B4) for real
defects against the plan. The git range is below, with full diff appended.

## What Phase B was supposed to deliver

- **B1**: Create `tools/pipette/requirements.txt` (pydantic≥2, pyyaml≥6 only).
  Rewrite the §6 Agentproof paragraph in
  `docs/superpowers/specs/2026-04-28-pipette-design.md` to describe a local
  hand-rolled validator instead. (Agentproof PyPI package was the wrong package
  — it's an AI test-assertion library, not a workflow-graph validator.)
  Single commit.

- **B2**: Create `tools/pipette/install_post_commit.sh` — idempotent installer
  with sentinel `# pipette-graphify v1`; refuses to clobber existing user
  hooks. Run it once. Smoke-commit (empty) to prove the hook doesn't break
  commits. Commit the installer (NOT `.git/hooks/post-commit`, which is
  local-only). Two commits expected: smoke + installer.

- **B3**: Create `tools/pipette/subagent_stop.py` — stub returning
  `{"permissionDecision": "allow", "reason": "stub — full impl in C7"}`.
  Create `tests/pipette/test_subagent_stop_wiring.py` exercising the stub via
  `python -m tools.pipette.subagent_stop`. Add SubagentStop block (timeout
  600s) to `.claude/settings.example.json` (committed) AND to local
  `.claude/settings.json` (gitignored, not committed). Block schema:
  ```json
  {"matcher": "", "hooks": [{"type": "command",
    "command": "python -m tools.pipette.subagent_stop", "timeout": 600}]}
  ```
  Multiple commits expected (the original plan's `git add .claude/settings.json`
  was a defect because that file is gitignored in this repo; the plan was
  patched mid-stream — see commit `dc4ad01`).

- **B4**: Create `docs/pipeline/_meta/{CONSTITUTION.md,UBIQUITOUS_LANGUAGE.md,
  lessons.md,.gitignore}` with verbatim content from the plan. Single commit.

## What to flag

Real defects only:

- File contents that diverge from the plan's verbatim spec (e.g.,
  `requirements.txt` includes a third dependency, CONSTITUTION.md missing a
  paragraph, etc.)
- Wrong commit messages (`feat(pipette): ...` format, exact wording per the
  plan)
- Wrong files committed (e.g., a gitignored file force-added with `git add -f`,
  or an unrelated file caught up in the commit)
- Missing sentinel/idempotency guards in the post-commit installer
- Test that doesn't actually test what it claims (e.g., `test_stub_returns_allow`
  doesn't actually invoke the stub)
- File mode wrong (installer must be `+x`)
- Cross-task dependencies broken (e.g., the test won't run because some package
  init file is missing)
- The post-commit hook content not matching the plan
- The plan's mid-stream patch (commit `dc4ad01`) being incomplete or wrong —
  is the new B3 instruction internally consistent?

## What NOT to flag

- Style preferences (formatting, naming, blank-line counts) unless they break
  something
- Decisions the plan explicitly made (drop agentproof, no PID liveness in v1,
  belt-and-suspenders graphify, 600s SubagentStop timeout, etc.) — those are
  locked
- Future-phase concerns (e.g., "C1 hasn't created `__init__.py` yet" — that's
  expected; the test passes via Python 3 namespace packages)
- Anything that was already addressed in 28 prior gemini rounds

## Required output

Emit ONE YAML object and nothing else. No prose, no code fences:

```yaml
verdict: PASS | NEEDS_CHANGES
confidence: 0.0–1.0
findings:
  - severity: critical | high | medium | low
    location: <commit SHA + file path>
    claim: <one sentence>
    evidence: <quoted line from diff or plan>
    suggested_fix: <concrete; not "consider">
notes: <one paragraph, only if cross-cutting>
```

`PASS` with empty findings is allowed. `NEEDS_CHANGES` requires ≥1
critical or high finding.

## Git range

Phase B starts at the plan-commit `f4411f5` (just the plan, no implementation)
and ends at `692fe0e` (B4 _meta scaffolding). 7 commits in between.

To capture the log+diff yourself locally:

```bash
git log f4411f5..HEAD --reverse > /tmp/phase_b_log.txt
git diff f4411f5..HEAD > /tmp/phase_b_diff.txt
```

Or pipe directly:

```bash
{ git log f4411f5..HEAD --reverse; echo; echo "=== DIFF ==="; echo;
  git diff f4411f5..HEAD; } | codex exec --model o3-mini --prompt-file - \
  docs/superpowers/plans/codex-prompts/2026-04-28-phase-b-review.md
```

(Adjust `codex` invocation to match your local CLI.)
