# CODEX REVIEW — pipette Phase S (Milestone 3)

You are an independent reviewer. The pipette implementation plan
(`docs/superpowers/plans/2026-04-28-pipette.md`) was hardened over 28 rounds
of prior gemini sanity-checks plus a ChatGPT audit. Phase B and Phase C
already shipped (codex prompts at `2026-04-28-phase-{b,c}-review.md`).

Your job: review Phase S (Tasks S1–S6 — sanity gate logic, gemini picker,
doctor, pipeline-graph validator) for real defects against the plan.

## What Phase S was supposed to deliver

- **S1** `tools/pipette/sanity/__init__.py` (empty) + `sanity/schema.py` +
  `tests/pipette/test_sanity_schema.py`. Pydantic `Finding`,
  `ReviewerOutput`, `ResearchBrief`, `Verdict`. `Verdict.jump_back_to` is
  `float | None` (Literal rejects floats); enforced via
  `model_post_init`. NEEDS_RESEARCH requires a `ResearchBrief` object
  with both `question` and `why_needed`. 6 tests.

- **S2** Four reviewer prompts: `tools/pipette/sanity/reviewers/{contracts,
  impact,glossary,coverage}.md`. Each declares an "Output contract"
  emitting one JSON object matching `ReviewerOutput`. Reviewer focus
  differs per file (contracts=invented APIs, impact=missed callers,
  glossary=undefined terms, coverage=untested code). One test that
  globs the dir and asserts each file has the contract markers.

- **S3** `tools/pipette/sanity/verifier.py` + `sanity/reviewers/verifier.md`
  + `tests/pipette/test_sanity_verifier.py`. `build_verifier_prompt`
  concatenates verifier.md template + 4 reviewer outputs as JSON;
  `filter_by_confidence` applies the strict `>=0.8` threshold. 5 tests.
  Note: the test `test_reviewer_prompts.py` from S2 still passes; its
  glob `*.md` now scans 5 files (incl. verifier.md) and all have the
  contract markers.

- **S4** `tools/pipette/gemini_picker.py` + tests. `invoke_gemini` calls
  `subprocess.run([GEMINI_BIN, "--approval-mode", "plan"], ...)` (DOES use
  the flag — distinct from the SubagentStop hook which doesn't),
  3-retry YAML schema validation with prior bad output appended to retry
  prompt, fence-stripping, schema violations treated as YAML retries.
  `subprocess.run` exceptions wrapped as `GeminiProcessFailure`.
  `invoke_and_print` (CLI entry) calls `lockfile.pause` on process
  failure to transition to paused state. 8 tests.

- **S5** `tools/pipette/doctor.py` + tests. 10 preflight checks
  (no-mistakes, code-review-graph CLI + MCP wired in
  `.claude/settings.local.json`, post-commit /graphify hook, gemini CLI,
  grill-me skill, ubiquitous-language skill, superpowers plugin,
  SubagentStop hook wired, pipeline-graph validator importable, fs O_EXCL).
  Plus `_run_local_graph_validator` running after all 10 pass. 4 tests
  on the harness (Check, run_checks, _aggregate_rc).

- **S6** `tools/pipette/pipeline_graph.json` (the spec's pipeline as nodes
  + edges) + `tools/pipette/validate_pipeline_graph.py` (hand-rolled
  structural validator replacing agentproof) + tests. Validator
  checks: every non-exit node has ≥1 outgoing edge; every node
  reachable from `start`; every gate node has outgoing edges for each
  declared `decision` label; cycle detection runs AFTER filtering out
  whitelisted `ALLOWED_LOOP_BACK_EDGES` (Step-3 jump-backs etc.).
  5 tests. The validator passes against the JSON it's shipped with.

**Plan defect surfaced and fixed mid-Phase-S:** the plan's
`pipeline_graph.json` declared `exit_crashed` as a node but no edge led
to it, breaking the validator's reachability check. The implementer
removed `exit_crashed` (a vestigial node from an earlier draft) — minimal
correct fix; documented in the S6 commit message.

Total after Phase S: **81 tests pass**, `python -m tools.pipette doctor`
exits 0 with all 10 checks ✅ + structural validation passing.

## What to flag

Real defects only:

- File contents diverging from the plan's verbatim spec (other than the
  documented `exit_crashed` removal in pipeline_graph.json)
- Wrong commit messages (each task has a specific message)
- Pydantic schema invariants that don't actually fire when violated
  (test it by constructing invalid Verdicts manually if needed)
- Reviewer prompt missing the "Output contract" / "No prose outside the
  JSON" sentinel (they're load-bearing for runtime parsing in Phase F)
- Verifier filter using wrong threshold or wrong comparison (must be
  `>= 0.8`, not `> 0.8`)
- Gemini picker using the WRONG flag (S4's picker DOES use
  `--approval-mode plan`; the SubagentStop hook does NOT — these are
  two separate gemini invocations)
- Gemini picker not catching `subprocess.TimeoutExpired` /
  `FileNotFoundError`
- Gemini picker not pausing the lockfile on process failure
- Doctor checks looking at wrong files / paths
- Pipeline-graph validator missing one of the 4 checks (outgoing edges,
  reachability, gate labels, cycles)
- Pipeline-graph validator's cycle detection not filtering allowed
  loop-backs first (would flag every legitimate jump-back as a defect)
- Edge labels in pipeline_graph.json containing descriptive text instead
  of just the decision label (e.g. `"FAIL/jump_back_to=1"` instead of
  `"FAIL"` with `notes: "jump_back_to=1"`)

What NOT to flag:

- Style preferences
- Locked decisions (drop agentproof, no PID liveness in lockfile,
  belt-and-suspenders graphify, etc.)
- Future-phase concerns (Phase F — slash command markdown — and
  Phase A — dogfood — not yet implemented)
- The `exit_crashed` removal (real plan defect; fix is correct)

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

Phase S starts immediately after Phase C's last commit (`27648f5` was the
codex-prompt for Phase C; the last code commit was `c9a82a5` —
SubagentStop full handler). Phase S ends at S6's commit (`b5490ed` —
pipeline_graph + validator). 6 implementation commits in between.

Capture log + diff:

```bash
git log 27648f5..HEAD --reverse > /tmp/phase_s_log.txt
git diff 27648f5..HEAD > /tmp/phase_s_diff.txt
```

Or pipe directly:

```bash
{ git log 27648f5..HEAD --reverse; echo; echo "=== DIFF ==="; echo;
  git diff 27648f5..HEAD; } | codex exec --prompt-file - \
  docs/superpowers/plans/codex-prompts/2026-04-28-phase-s-review.md
```

(Adjust `codex` invocation to match your local CLI.)
