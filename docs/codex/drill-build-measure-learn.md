# Drill Build-Measure-Learn Workflow

Use this workflow when a drill change, hosted drill run, fixture run, or newly pulled drill transcript needs to become a proposed product or code fix.

The loop is:

1. Build: run the drill path.
2. Measure: capture drill transcript telemetry.
3. Learn: evaluate the logs with Socratink Brain.
4. Fix: propose the smallest release-relevant change.
5. Repeat: rerun the drill and compare against the prior evidence.

## 1. Build

Run one focused drill path. Keep the run narrow enough that the logs can answer one question.

Good run questions:

- Did cold attempt stay unscored and generative?
- Did study unlock only after generative commitment?
- Did spacing/interleaving block premature re-drill?
- Did re-drill resolve to `drilled` or `solidified` truthfully?
- Did the graph patch the same active node that the backend evaluated?
- Did hosted behavior match local behavior?

Prefer hosted production evidence when the change could diverge on Vercel. Use fixture or local evidence only as a narrower signal, and label it as such in Socratink Brain.

## 2. Measure

For hosted drill evidence, ensure Vercel has:

- `SOCRATINK_TELEMETRY_STDOUT=true`
- `SOCRATINK_CAPTURE_DRILL_TRANSCRIPTS=true` when transcript content is needed

Then export the recent Socratink Brain-marked drill events:

```bash
scripts/eval-pull 1h
```

For a wider window:

```bash
scripts/eval-pull 24h
```

The exported raw artifacts should land in:

```text
.socratink-brain/raw/drill-chat-logs/
```

Do not edit the raw JSONL files. They are immutable evidence.

## 3. Learn

Run a Socratink Brain `evaluate-logs` pass against the new raw artifact. The output should update compiled product memory, not just summarize the log.

Use this handoff prompt:

```text
Using socratink-brain, evaluate the newest raw drill chat logs in `.socratink-brain/raw/drill-chat-logs/`.

Build-Measure-Learn scope:
- Build: identify which drill path the log represents.
- Measure: summarize what the transcript proves and what it does not prove.
- Learn: create or update the Socratink Brain source page, log coverage, and any finding or issue that changes release truth.
- Proposed fix: if the log reveals a release-relevant break, write the smallest hot-fix brief with surface, broken behavior, intended behavior, repro, impact, constraints, and non-goals.

Respect:
- Generation Before Recognition.
- The graph must tell the truth.
- Attempted is not mastered.
- Fixture/local evidence is not hosted validation.
- Missing instrumentation is a health gap, not a silent omission.
```

Socratink Brain pass should usually touch:

- `.socratink-brain/wiki/sources/`
- `.socratink-brain/wiki/log-coverage.md`
- `.socratink-brain/wiki/index.md`
- `.socratink-brain/wiki/log.md`

It should create a page under `.socratink-brain/wiki/records/` only when the log changes product truth, release risk, instrumentation truth, or active MVP priorities.

## 4. Fix

If the Socratink Brain finding is release-relevant, convert it into a hot-fix brief before editing code:

```text
Hot-fix: <surface>.
Broken: <current behavior from logs>.
Intended: <rule restored>.
Repro: <smallest hosted/local path>.
Impact: <which current release-goal behavior this affects>.
Constraints: Generation Before Recognition; graph truth; no mastery without spaced re-drill; hosted behavior matters.
Non-goals: <what this fix must not expand into>.
Evidence: <Socratink Brain source/finding page plus raw log path>.
```

Then patch the smallest code or copy surface that restores the rule.

## 5. Repeat

After the fix:

1. Run the narrow local or fixture check that should catch the regression.
2. Run the hosted drill path if the bug could diverge on Vercel.
3. Export logs again with `scripts/eval-pull`.
4. Run Socratink Brain `evaluate-logs` again.
5. Mark the finding as resolved only when the new evidence directly covers the broken behavior.

Do not close the loop from local tests alone when the failure mode involved Vercel runtime logs, hosted environment variables, or serverless behavior.

## Automation Boundary

Automated now:

- Vercel log export into raw Socratink Brain artifacts: `scripts/eval-pull`.
- Raw-log extraction from Vercel JSON runtime logs: `scripts/export_socratink_brain_vercel_logs.py`.
- Deterministic Socratink Brain structure validation: `.agents/skills/socratink-brain/scripts/validate_wiki.py`.

Agent-mediated by design:

- Determining what the logs prove.
- Deciding whether a finding is release-relevant.
- Proposing the smallest safe fix.
- Updating `ACTIVE.md`.

That boundary preserves the Build-Measure-Learn loop without letting automation promote weak or ambiguous evidence into product truth.
