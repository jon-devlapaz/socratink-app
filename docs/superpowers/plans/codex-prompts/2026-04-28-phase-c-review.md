# CODEX REVIEW — pipette Phase C (Milestone 2)

You are an independent reviewer. The pipette implementation plan
(`docs/superpowers/plans/2026-04-28-pipette.md`) was hardened over 28 rounds of
prior gemini sanity-checks plus a ChatGPT audit; assume it is correct.

Your job: review Phase C (Tasks C1 through C7 — orchestrator core, the Python
modules the slash command shells into) against the plan. The git range is
below, with full diff appended.

## What Phase C was supposed to deliver

- **C1** `tools/pipette/folder.py` + `__init__.py` + `__main__.py` + `tests/pipette/conftest.py` + `tests/pipette/test_folder.py`. 5 tests covering kebab-slug, folder-name with full HHMMSS, rename-to-aborted, rename-to-crashed.
- **C2** `tools/pipette/trace.py` + `tests/pipette/test_trace.py`. 4 tests. JSONL with `O_APPEND`-positioned single-`os.write` records (PIPE_BUF claim was retracted).
- **C3** `tools/pipette/lockfile.py` + `tests/pipette/test_lockfile.py`. Atomic `O_EXCL` acquire, no PID liveness (v1 deviation per plan §3), `state: running` always refused with stale-hint, `state: paused` survives process death, `update_state` uses per-pid temp + `os.replace`, `abort` topic-verifies and trace-logs. Filesystem detection refuses NFS/FUSE. 11 tests.
- **C4** `tools/pipette/cli.py` (16 subcommands; lazy imports per branch) + thin orchestrator stub + `tests/pipette/test_cli.py` (7 tests: 4 surface + 3 build-coverage-map).
- **C5** Replace orchestrator stub with full impl: `start`, `resume_run`, `abort_run`, `recover_run`, `lock_status`, `pause_run`, `finish_run`, `archive_for_loop_back`. 7 tests.
- **C6** `tools/pipette/research_gate.py` — `derive_slug` (8 content words after stop-words), `write_brief`, `write_findings`, `_bump_caps` enforcing strict `>` per-file:2 / per-step:3 caps via `lockfile.update_state`. 6 tests.
- **C7** Full `tools/pipette/subagent_stop.py` (replaces B3 stub). Hook reads lockfile via `git rev-parse --git-common-dir` (works inside disposable worktrees), reads `<folder>/current_task.json`, then runs in order: working-tree-clean check → progress check (commits since pre_dispatch_sha) → TDD-precedence chronological walk (only `feat:`/`fix:` regexes) → LLM review via gemini subprocess (no --approval-mode flag, fence-stripping, `.replace()` not `.format()`, `{task_id}` interpolation, fail-closed on gemini failure). Top-level `main()` wraps in try/except so any crash emits structured deny + exits 0. 11 tests.

Also: a real race-condition fix landed mid-Phase-C as commit `0e9aa82` —
`acquire()` now handles a concurrently-just-created-but-not-yet-written
lockfile by treating None/non-dict from `yaml.safe_load` as "concurrent
in flight" and falling through to `O_EXCL` (which loses the race and raises
`LockHeld` cleanly). Surfaced by 2/5 flapping on
`test_concurrent_acquisition_only_one_wins` after C5 landed; 10/10 after fix.

Total: **52 tests pass** across `tests/pipette/`.

## What to flag

Real defects only:

- File contents diverging from the plan's verbatim spec
- Wrong commit messages (each task has a specific message in the plan)
- Missing or wrong-named subcommands in cli.py (the slash command will
  reference these by name in Phase F; mismatches break silently)
- Tests that mock instead of actually exercise behavior
- Off-by-one or threshold errors in cap counters (per-file:2 strict, per-step:3 strict)
- TDD precedence regex letting through commits that should deny, or denying
  commits that should pass (e.g., `chore:` commits should NOT trigger TDD)
- LLM prompt template formatting bugs (`.format()` vs `.replace()` matters)
- Race conditions or TOCTOU windows beyond what the plan acknowledges
- Hook's `_main_repo_root` doing something other than `git rev-parse
  --git-common-dir`
- `_lock_path()` not honoring `PIPETTE_LOCK_PATH` env var (tests rely on this)
- Gemini called WITH `--approval-mode plan` (should be plain `[GEMINI_BIN]`)

What NOT to flag:

- Style preferences
- Locked decisions (drop agentproof, no PID liveness, belt-and-suspenders
  graphify, 600s SubagentStop timeout, fail-closed-on-gemini-failure, etc.)
- Future-phase concerns (Phase S/F not yet implemented)
- The plan's mid-stream patches (commits `dc4ad01`, `d4e6cae`, `0e9aa82`) —
  those landed real fixes
- Anything addressed in the 28 prior gemini rounds + ChatGPT audit

## Documented deviations from plan-verbatim (real plan defects fixed mid-implementation)

These changes deviate from the plan's literal text but are correct fixes to
plan defects discovered during implementation. **Do NOT flag these.**

1. **C3 — `test_concurrent_acquisition_only_one_wins` subprocess `-c` string.**
   The plan's test joined statements with `;` including before a `try:` block,
   which is a Python SyntaxError in `-c` mode. Implementer joined with `\n` so
   the try/except parses correctly. Test semantics are identical (two procs
   race, exactly one exits 0 and one exits 2).

2. **C4 — doctor subparser added `description=` arg.** The plan's `_build_parser()`
   only set `help=` on the doctor subparser. The test
   `test_doctor_subcommand_exists` asserts `"preflight" in r.stdout.lower()`
   when running `doctor --help` — but argparse's `--help` shows the
   `description=` field, not `help=`. Implementer added `description=` so the
   "preflight" string appears in `doctor --help` output as the test requires.

3. **C5 — `test_start_refuses_when_running` capsys double-call.** The plan's
   test had `assert "already running" in capsys.readouterr().err.lower()` AND
   a separate `capsys.readouterr()` call earlier; the second drains the
   buffer so the first returns empty. Implementer captured to a local
   variable and asserted "running" in stderr (the broader match preserves
   the original test author's intent without the double-drain bug).

4. **C5 — orchestrator stub expanded from 4 functions to 8 in C4.** The plan's
   stub at C4 had only `start, resume_run, abort_run, lock_status`, but the
   CLI lazy-imports more (`recover_run, pause_run, finish_run,
   archive_for_loop_back`). Implementer added the stubs so all CLI
   subcommands resolve. C5 then replaced wholesale with the full
   implementation. (Same total functions; just declared earlier.)

5. **Lockfile race fix (commit `0e9aa82`).** Was already mentioned above —
   the `acquire()` function now handles a concurrently-just-created-but-not-
   yet-written lockfile by treating None/non-dict from `yaml.safe_load` as
   "concurrent in flight" and falling through to `O_EXCL` (which loses the
   race and raises `LockHeld`). Surfaced by 2/5 flapping on
   `test_concurrent_acquisition_only_one_wins`; 10/10 after fix.

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

Phase C starts immediately after the Phase B last fix (`d4e6cae`) and
ends at C7 (`c9a82a5`). 9 implementation commits + 1 race-fix commit.

Capture log + diff:

```bash
git log d4e6cae..HEAD --reverse > /tmp/phase_c_log.txt
git diff d4e6cae..HEAD > /tmp/phase_c_diff.txt
```

Or pipe directly:

```bash
{ git log d4e6cae..HEAD --reverse; echo; echo "=== DIFF ==="; echo;
  git diff d4e6cae..HEAD; } | codex exec --prompt-file - \
  docs/superpowers/plans/codex-prompts/2026-04-28-phase-c-review.md
```

(Adjust `codex` invocation to match your local CLI.)
