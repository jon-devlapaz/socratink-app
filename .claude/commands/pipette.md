---
name: pipette
description: |
  Heavy-planning pipeline. User-invokable. Runs a multi-step pipeline (graph reconnaissance →
  grill-with-docs (glossary updated inline) → diagram → multi-agent sanity gate → plan →
  subagent execute → no-mistakes-gated push → eval) with deterministic gates,
  lockfile-based mutual exclusion, and per-feature artifact folders under
  docs/pipeline/. Use when the topic warrants the ceremony — not for default
  brainstorming. Read the spec at
  docs/superpowers/specs/2026-04-28-pipette-design.md before invoking on novel topics.
user-invocable: true
---

# /pipette

Argument routing:

- `/pipette doctor` → run `python -m tools.pipette doctor`. Print results. Stop.
- `/pipette abort <topic>` → run `python -m tools.pipette abort "<topic>"`. Stop.
- `/pipette resume <topic>` → see "Resume flow" below. Do NOT just shell out and stop.
- otherwise → topic = "$ARGS". Proceed to Step −1.

## Global rule: raising NEEDS_RESEARCH from any step

Per spec §5.5, ANY step (most commonly Steps 1 and 3) can raise `NEEDS_RESEARCH` when the agent or a subagent determines that a load-bearing claim depends on external/world knowledge it cannot confidently produce. (B-revision 2026-04-28: Step 1.5 was collapsed into Step 1 via the `grill-with-docs` skill, so research raises from 1.5 are no longer possible.)

If at any step you or a subagent need external research to proceed:

1. Write the brief: `python -m tools.pipette research-brief --folder=FOLDER --step=<current_step> --question-and-why "<one-sentence question>" "<one-sentence why_needed>"`
2. Pause the lockfile: `python -m tools.pipette pause --step=<current_step> --reason=NEEDS_RESEARCH`
3. Print to the user: `"⏸  Pipeline paused at step <N>. Run deep research on <FOLDER>/_research/<file>.md, then resume with /pipette resume <topic> [/path/to/findings.md]"`
4. Exit. Do NOT continue the step.

The anti-loop caps (per-file: 2, per-step: 3) are enforced inside the `research-brief` CLI; if a cap is hit, the CLI aborts the pipeline automatically.

## Resume flow (re-entry after a paused pipeline)

Per spec §5.5 and §5.6: resume must (a) accept pasted research findings when paused for `NEEDS_RESEARCH`, (b) flip the lockfile state to running, and (c) re-dispatch execution to the paused step. The dispatch handles ALL pause reasons — NEEDS_RESEARCH (Steps 1 or 3) and non-research pauses (Step 3 gemini_cli_failure, Step 5 hook_crash, any-step user_initiated).

Procedure (the dispatcher branches on `pause_reason` FIRST, then on `paused_at_step`):

1. Read `docs/pipeline/_meta/.lock`. If `state` is not `paused` or topic doesn't match: print the orchestrator's error (`pipette: no paused pipeline for <topic>`) and stop.
2. Capture `paused_at_step`, `pause_reason`, and `folder` from the lockfile.
3. **If `pause_reason == "NEEDS_RESEARCH"`** (raised by Step 1 or 3 only; B-revision dropped Step 1.5):
   - Locate the most recent research brief in `<folder>/_research/` (sorted by mtime). Read its `research_question` from the YAML front block.
   - Ask the user to paste their research findings (or accept from a file: `/pipette resume <topic> /path/to/findings.md`).
   - Append findings via `python -m tools.pipette research-findings --folder=<folder> --step=<paused_at_step> --question=<research_question> --findings-file=<file>`.
   - Validate `paused_at_step ∈ {1, 3}` (spec §5.5; B-revision 2026-04-28). If invalid, hard error: `"NEEDS_RESEARCH from step <N> is invalid; restricted to 1 or 3"` and stop.
4. **If `pause_reason ∈ {gemini_cli_failure, hook_crash, user_initiated}`:**
   - No findings to ingest. Just acknowledge that the user has resolved the underlying issue (gemini auth refreshed, hook bug fixed, etc.).
5. **Flip the lockfile state to running:** `python -m tools.pipette resume "<topic>"`. Returns 0 on success; nonzero exits stop here.
6. **Append resume event to trace:** `python -m tools.pipette trace-append --folder=<folder> --step=<paused_at_step> --event=resumed`.
7. **Re-dispatch to the paused step.** Re-enter the appropriate Step section of this command, with NEEDS_RESEARCH findings (if any) prepended to that step's input:
   - `paused_at_step == 1` → "Step 1: Grill (with docs)"
   - `paused_at_step == 3` → "Step 3: Multi-agent sanity check"
   - `paused_at_step == 5` → "Step 5: Execute" (re-dispatches the failed task; subagents start fresh in the worktree, picking up from the most recent committed state)
   - any other value (0, 1.5, 2, 4) → hard error: `"resume from step <N> not yet implemented"` and stop. v1 doesn't pause at these steps; if you see this, the lockfile is corrupted. (1.5 specifically: B-revision 2026-04-28 collapsed it into Step 1.)

## Step -1: Read project constants

Bash: `python -m tools.pipette start "$ARGS"` — captures FOLDER from stdout (line `pipette: started <topic-slug> → <folder>`).

Read `docs/pipeline/_meta/CONSTITUTION.md` and `docs/pipeline/_meta/CONTEXT.md` (the project's ubiquitous-language glossary) and `docs/pipeline/_meta/lessons.md` (last 20 lines). Hold these in context for every subsequent step.

## Step 0: Graph reconnaissance

Call MCP tools in this order against the topic:
1. `mcp__code-review-graph__semantic_search_nodes` with topic keywords
2. `mcp__code-review-graph__get_architecture_overview`
3. `mcp__code-review-graph__get_impact_radius` on results from (1)
4. `mcp__code-review-graph__get_affected_flows` on results from (1)
5. `mcp__code-review-graph__query_graph` for tests covering nodes from (1)
6. `mcp__code-review-graph__get_minimal_context_tool` (or `get_review_context` with `detail_level=minimal`) on results from (1) — surface the smallest review surface that captures the topic; this becomes the `minimal_review_set` referenced by best-of-N selection in Step 5.

Cross-feature scan: glob `docs/pipeline/*/00-graph-context.md`. For each whose impact radius overlaps the current topic (heuristic: any shared node in the affected-files list), prepend a one-paragraph digest of its `01-grill.md` and `04-plan.md`. Cap at 3 most-recent overlapping runs.

**Coverage map (load-bearing for Step 5):** Step 0 produces `FOLDER/coverage_map.json` — the data source the SubagentStop hook reads (via `current_task.json["coverage"]`) for TDD-enforcement and best-of-N triggering. v1 uses a graph-derived approximation (real `pytest --cov` integration is v2):

The orchestrator does NOT loop per-affected-node manually — that would burn context on a deterministic transformation. Instead:

1. Make a SINGLE batched MCP query: `mcp__code-review-graph__query_graph` with a query like *"all CALLS or CONTAINS edges from any node whose source file matches `tests/**` into any node from `<affected_files_list>`"*. Dump the raw response to `FOLDER/_graph_test_coverage_dump.json`.
2. Run `python -m tools.pipette build-coverage-map --dump-file=FOLDER/_graph_test_coverage_dump.json --affected-files <file1> <file2> ... --output=FOLDER/coverage_map.json`.

The Python helper (`build-coverage-map` CLI subcommand on `cli.py`) computes the heuristic deterministically:

- For each affected source file F: if at least one test node in the dump has an edge into a node in F, set `coverage[F] = 0.85` (TDD enforcement skipped, no best-of-N from coverage).
- Else: set `coverage[F] = 0.30` (TDD enforcement triggers; best-of-N also triggers since 0.30 < 0.40).

Write the resulting map to `FOLDER/coverage_map.json` as `{"_method": "graph_approx_v1", "files": {"<source-file>": <float>}}`. Step 5 reads this when computing `current_task.json["coverage"]` per task: `coverage = min(coverage_map["files"][m] for m in affected_modules)` (worst-case across modules so the strictest gate fires).

This is an approximation, not real line coverage. It catches the obvious case (no tests at all → strict TDD gate) and skips it where tests demonstrably touch the source. The `_method` field lets v2 detect-and-replace this approximation with real `pytest --cov` data.

Watch mode: if `mcp__code-review-graph__status` reports `last_updated` more than 1 hour stale, log a warning to FOLDER/trace.jsonl (`python -m tools.pipette trace-append --folder=FOLDER --step=0 --event=stale_graph_warn`) and continue.

Write `FOLDER/00-graph-context.md` containing: modules, callers/callees, blast radius, risk_score, minimal_review_set, coverage map, prior-feature digest. Append `step=0 event=finished` to trace.

## Step 1: Grill (with docs)

**B-revision (2026-04-28):** This step uses `grill-with-docs` (replaces `grill-me`). The skill challenges the plan against the project's existing glossary at `_meta/CONTEXT.md`, sharpens fuzzy language, and updates `CONTEXT.md` inline as decisions crystallise. Step 1.5 (separate `ubiquitous-language` skill invocation) was therefore collapsed into Step 1.

**Resume-with-research:** before invoking grill, glob `FOLDER/_research/1-*.md`. If any exist with a `## Findings` section, prepend them to the grill's input as context (formatted as "PRIOR RESEARCH FINDINGS RELEVANT TO THIS DESIGN: ..."). This is how Step 1 picks up findings from a NEEDS_RESEARCH pause-resume cycle (spec §5.5).

Invoke `Skill: grill-with-docs` with:
- The topic + any research findings from above
- The contents of `00-graph-context.md`
- The contents of `docs/pipeline/_meta/CONTEXT.md` (so the grill can challenge against the existing glossary and update it in place)

The grill follows its own rules: it explores the codebase instead of asking when answerable from code, challenges fuzzy language against canonical terms, updates `CONTEXT.md` inline as decisions are made, and offers ADRs sparingly when a decision is hard-to-reverse + surprising + a real tradeoff. **CONTEXT.md updates land directly in `docs/pipeline/_meta/CONTEXT.md`** — that's the canonical glossary; do not write a separate per-feature glossary delta.

When the grill produces a design summary, write it to `FOLDER/01-grill.md`. Any ADRs the skill generated land at `docs/adr/` (created lazily) per the skill's own convention.

### Step 1.6: Verify-cited-symbols (F6, pipette-only discipline)

**B-revision (2026-04-30):** before the soft user gate below fires, the orchestrator (you) must enforce two pipette-specific disciplines on the grill summary the grill skill itself does not enforce. These exist because the 2026-04-28 admin-tink-todo run shipped `01-grill.md` with `state.email` referenced when `AuthSessionState.email` did not exist (only `state.user.email`); see `docs/pipeline/_meta/implementation-followups.md` F6.

For the **single most-cited symbol** in the grill's design summary (the field, method, or function the design hinges on most):

1. Use the `Read` tool on the file that defines that symbol.
2. Confirm the field/method shape exists exactly as cited (e.g., if the snippet says `state.email`, confirm `state.email` resolves on the actual class — not via `state.user.email` indirection or any other shape).
3. Log the round-trip as a structured trace event:

   ```
   python -m tools.pipette trace-append --folder=FOLDER --step=1 \
     --event=grill_symbol_verified --data=symbol=<the.symbol.you.checked>
   ```

4. **If the cited symbol does not match its actual shape, return to the grill with the corrected shape as feedback.** Do not advance to the user gate (Step 1.8) until the round-trip is logged AND the grill summary references real symbols.

This is prompt-level discipline. The trace event provides observability so a future audit can confirm whether the orchestrator skipped this step.

### Step 1.7: Deployment-topology check (F7, pipette-only discipline)

If the grill marks any route as a **Dev-only Route** per `docs/pipeline/_meta/CONTEXT.md`, you must (in this order):

1. Use the `Read` tool on `vercel.json` (or the project's actual deployment config — confirm the filename via `ls *.json` at the repo root rather than assuming).
2. Identify every layer that could intercept the request between client and the FastAPI handler. For socratink-app this is typically: `Vercel CDN → FastAPI middleware → handler`.
3. Append a topology block to `01-grill.md`:

   ```
   ## Deployment topology
   - Path: <e.g. /admin/tink-todo>
   - Layers: <e.g. Vercel CDN (serves public/* directly) → FastAPI middleware → handler>
   - Gating placement: <where is the gate? in middleware? in handler? in vercel.json rewrites?>
   - Risk: <e.g. if HTML lives in public/, the CDN bypasses the FastAPI gate>
   ```

4. Either: (a) the route's HTML shell is served by a FastAPI handler (`HTMLResponse`), not from `public/`; OR (b) the cited `vercel.json` rewrites must be inspected and confirmed to forward the path to the function.

The Read of `vercel.json` is **mandatory** — do not write the topology block from pre-training knowledge. Mirrors §1.6's "Read the cited symbol before claiming its shape" discipline, applied to deployment layers.

### Step 1.8: Emit pipette-meta block (Chunk G F15 dependency)

Before writing the soft user gate, append a single HTML comment to `01-grill.md` with the metrics F15's heuristic auto-pass at Step 3 entry will read:

```
<!-- pipette-meta total_changed_lines=N max_risk_score=F -->
```

- `N` = total lines the design proposes to change across all affected files (your best estimate from the grill summary; integer).
- `F` = the max risk_score across affected files from `00-graph-context.md` (decimal between 0.0 and 1.0).

The order of the keys (`total_changed_lines` then `max_risk_score`) matters — the F15 regex is order-sensitive. Both keys are required; if you can't compute one, default `total_changed_lines=999 max_risk_score=1.0` to force F15 to fall through (conservative; never auto-pass on missing metrics).

### Step 1.9: User gate (soft)

Ask "Approve grill summary? (approve / revise / abort)". On `revise`, return to grill with feedback. On `abort`, run `python -m tools.pipette abort "$ARGS"` and exit. Append `step=1 event=gate decision=<choice>` to trace.

## Step 2: Diagram

Default: invoke `Skill: workflow-diagramming` to produce a Mermaid diagram seeded from the impact graph + glossary terms. Save as `FOLDER/02-diagram.mmd`.

If the user types `excalidraw`, invoke `Skill: whiteboarding` instead and save as `FOLDER/02-diagram.excalidraw`.

The diagram MUST use canonical glossary terms.

**User gate (soft):** approve / revise / abort.

## Step 3: Multi-agent sanity check (HARD GATE)

**Resume-with-research:** before dispatching reviewers, glob `FOLDER/_research/3-*.md`. If any exist with `## Findings`, prepend them to EACH reviewer's input (under "PRIOR RESEARCH FINDINGS:") AND include them in the gemini-picker prompt's "RESEARCH FINDINGS" section. This is how Step 3 ingests the result of a prior `NEEDS_RESEARCH` pause-resume cycle (spec §5.5).

Dispatch the 4 reviewers in **parallel** via `Skill: superpowers:dispatching-parallel-agents`:

For each reviewer in [contracts, impact, glossary, coverage]:
- Subagent prompt: contents of `tools/pipette/sanity/reviewers/<reviewer>.md` + the artifact stack: `00-graph-context.md`, `01-grill.md`, `02-diagram.{mmd|excalidraw}`, AND `docs/pipeline/_meta/CONTEXT.md` (the project glossary, updated inline by `grill-with-docs` during Step 1; load-bearing for the glossary-consistency reviewer per spec §3 Step 3, also useful for the other 3 reviewers as terminology context). (B-revision 2026-04-28: per-feature glossary delta `01b-glossary-delta.md` no longer exists; the glossary lives only in `_meta/CONTEXT.md`.)
- Subagent writes its output JSON to `FOLDER/_reviewer-<name>.json` (instructed in the dispatch prompt). The orchestrator validates each file by parsing as `ReviewerOutput` (with markdown fence stripping):
  ```bash
  python -c "import json, re, sys; from tools.pipette.sanity.schema import ReviewerOutput; raw = open('FOLDER/_reviewer-<name>.json').read(); raw = re.sub(r'^\s*\`\`\`(?:json)?\s*\n?', '', raw); raw = re.sub(r'\n?\`\`\`\s*$', '', raw); ReviewerOutput.model_validate(json.loads(raw))"
  ```
  Validation failure on any reviewer file → re-dispatch that reviewer once, then hard error if still invalid.

Verifier subagent (1 dispatch): build the verifier prompt by invoking `python -m tools.pipette build-verifier-prompt --reviewer-files FOLDER/_reviewer-contracts.json FOLDER/_reviewer-impact.json FOLDER/_reviewer-glossary.json FOLDER/_reviewer-coverage.json > FOLDER/_verifier-prompt.txt`. Dispatch as a single subagent (the verifier MCP-grounds against `code-review-graph` per its prompt). The subagent writes its output JSON to `FOLDER/_verifier-output.json`. The orchestrator pipes that file through `python -m tools.pipette verifier-filter < FOLDER/_verifier-output.json` to apply the 0.8 confidence filter. The filter's stdout is the FINAL set of surviving findings — reviewer-original findings never reach gemini directly.

Build the gemini prompt with the canonical schema embedded. Write to `FOLDER/_step3-prompt.txt`:

```
You are the picker for /pipette Step 3. Read the artifact stack and surviving findings. Decide:
  - PASS — surviving findings do not warrant blocking; advance to Step 4 (plan).
  - FAIL — at least one Critical or High finding requires loop-back; specify jump_back_to ∈ {1, 2}. (B-revision 2026-04-28: Step 1.5 collapsed into Step 1; jump_back_to=1.5 is no longer valid.)
  - NEEDS_RESEARCH — a load-bearing claim requires external/world knowledge the agent cannot confidently resolve.

Output ONE YAML object and nothing else. No prose, no code fences:

verdict: PASS | FAIL | NEEDS_RESEARCH
jump_back_to: 1 | 2           # required only when verdict is FAIL; null otherwise
research_brief:               # required only when verdict is NEEDS_RESEARCH
  question: <one sentence>
  why_needed: <one sentence>
notes: |
  <free-form reasoning, what's wrong if FAIL or what to look up if NEEDS_RESEARCH>

Constraints:
  - jump_back_to=3 is invalid (the gate cannot loop to itself).
  - jump_back_to=4 is invalid (Step 4 happens AFTER this gate).
  - PASS and NEEDS_RESEARCH must NOT set jump_back_to.
  - NEEDS_RESEARCH must set research_brief.

---

ARTIFACT STACK:
<concatenate 00-graph-context.md, 01-grill.md, 02-diagram.{mmd|excalidraw}, _meta/CONTEXT.md>

---

SURVIVING FINDINGS (post-verifier, ≥0.8 confidence):
<filtered findings JSON from `python -m tools.pipette verifier-filter`>
```

Invoke `python -m tools.pipette gemini --prompt-file=FOLDER/_step3-prompt.txt --folder=FOLDER`. Read its stdout (Verdict YAML) and exit code.

**Write `03-gemini-verdict.md` UNCONDITIONALLY on any exit-0 verdict** (PASS, FAIL, or NEEDS_RESEARCH) BEFORE branching. The file contains the full reviewers' raw findings, the verifier-filtered survivors, and the verdict YAML. This is required by spec §5.3 — on FAIL, the archive to `_attempts/N-<ts>/` MUST include `03-gemini-verdict.md` so the audit trail captures why the design was rejected.

Then branch on verdict type:
- exit 0 + verdict PASS → advance to Step 4.
- exit 0 + verdict FAIL → **PAUSE FOR USER CHOICE first**. Print gemini's `notes` to the user, then ask:
    > Gemini FAIL on this design. Gemini suggests jump back to step <N>. Choose:
    >   1. `loop` — accept gemini's jump-back to step <N>
    >   2. `--jump-to <step>` — override gemini's destination (must be 1 or 2; validated via `python -m tools.pipette parse-jump`)
    >   3. `override` — bypass the gate, write a feedback memory (per spec §5.4 schema), advance to Step 4
    >   4. `abort` — discard this run via `python -m tools.pipette abort "$ARGS"`
    
  Do NOT loop back automatically; that would deny the user the override and manual-jump options the spec mandates. Once the user chooses:
    - `loop` → archive (`python -m tools.pipette archive-for-loop-back --folder=FOLDER --jump-back-to=<gemini's value>`), loop back.
    - `--jump-to N` → validate via parse-jump, archive with `--jump-back-to=<validated N>`, loop back.
    - `override` → run the override-memory write flow described under "User override" below, advance to Step 4.
    - `abort` → call `python -m tools.pipette abort "$ARGS"` and exit.
- exit 0 + verdict NEEDS_RESEARCH → extract the structured `research_brief.{question, why_needed}` from the verdict YAML (`python -c "import yaml,sys; d=yaml.safe_load(sys.stdin)['research_brief']; print(d['question']); print(d['why_needed'])"` reads question on line 1 and why on line 2; the slash command captures both). Write to a temp YAML file `FOLDER/_step3-brief.yaml` containing `{question: ..., why_needed: ...}`. Then call `python -m tools.pipette research-brief --folder=FOLDER --step=3 --brief-file=FOLDER/_step3-brief.yaml`. Pause: `python -m tools.pipette pause --step=3 --reason=NEEDS_RESEARCH`. Print resume instructions and exit.
- exit 1 (process failure) → pause already recorded by gemini-picker; print stderr to user; exit.
- exit 2 (YAML invalid 4x) → hard error to user.

User override: if user types `override`, prompt for one-line reason, then save the override as a project-scoped feedback memory using Claude's auto-memory system. The exact write path is whatever the harness exposes for the current project (e.g., the directory shown in this session's `MEMORY.md` system reminder). Do NOT hardcode an absolute path; let the harness resolve it. Pipette's contract is the file *contents*, not its location.

File contents must follow spec §5.4 exactly:

```markdown
---
name: feedback_gemini_override_<kebab-topic>
description: User overrode gemini FAIL on <kebab-topic>; reason captured here for future reference.
type: feedback
date: YYYY-MM-DD
topic: <kebab-topic>
gemini_jump_back_to: <step>
gemini_notes_summary: <one line summary of gemini's notes>
override_reason: <user-supplied one-line>
---

(body — copy gemini's full notes here for context)
```

Then append a one-line entry to the project's `MEMORY.md` index in the canonical format (`- [Title](file.md) — one-line hook`). Advance to Step 4.

User manual jump-back: if user types `--jump-to N`, capture the literal string and validate via `python -m tools.pipette parse-jump "<user input>"`. Exit 0 prints `1` or `2` on stdout; exit 2 prints rejection. The slash command MUST use the validated value, never re-parse via natural language. If validation rejects, surface the error to the user and re-prompt. Then archive accordingly and loop back.

## Step 4: Plan

Invoke `Skill: superpowers:writing-plans` with the full artifact stack. The plan must reference real symbols from `00-graph-context.md`. After the plan is drafted, re-run `mcp__code-review-graph__get_impact_radius` on the proposed changes; if files are missing from the plan, prompt the writing-plans subagent to revise.

**User gate (soft):** approve / revise / abort. On approve, write `FOLDER/04-plan.md`.

## Step 5: Execute

Invoke `Skill: superpowers:subagent-driven-development` with `04-plan.md`. Each task → fresh subagent.

For each task:
- Compute `risk_score` from Step 0's `00-graph-context.md` for the affected modules.
- Compute `coverage` from Step 0's coverage map.
- **Capture `pre_dispatch_sha` and write `FOLDER/current_task.json` BEFORE dispatching the subagent.** This is the contract with the SubagentStop hook (Task **C7** reads this file from the lockfile-pointed folder; the Claude Code event payload does NOT carry coverage or boundary info). Schema:
  ```json
  {
    "task_id": "<plan task id, e.g. C3>",
    "coverage": <float, 0.0–1.0>,
    "affected_modules": ["src/foo.py", "tests/foo_test.py"],
    "pre_dispatch_sha": "<output of `git rev-parse HEAD` captured immediately before dispatch>"
  }
  ```
  No `worktree_dir`: the hook uses `os.getcwd()` instead (which IS the worktree under best-of-N's `superpowers:using-git-worktrees` — see Task **C7** which explicitly resolves to cwd, not to any caller-supplied path). The `pre_dispatch_sha` scopes both the TDD precedence walk and the LLM-review diff to ONLY the subagent's novel commits, not unrelated history on the branch.
- If `risk_score >= 0.7` OR `coverage < 0.4`: best-of-N. Use `Skill: superpowers:dispatching-parallel-agents` + `Skill: superpowers:using-git-worktrees`. K=3. **Before dispatching the selector subagent, REMOVE `FOLDER/current_task.json`** — the selector reads/compares but produces no commits, so the SubagentStop hook's progress check would otherwise deny it. With `current_task.json` absent, the hook returns its "orchestrator hasn't dispatched" allow path. After the selector returns and the orchestrator captures the winner, write a fresh `current_task.json` for the NEXT plan task. The selector subagent compares K parallel outputs against plan acceptance criteria + minimal_review_set; archives losers to `FOLDER/_attempts/best-of-n-<task>/`. The selector designates a winner; orchestrator captures the winner's branch name.
- Else: single subagent in disposable worktree. **Invoke `Skill: superpowers:using-git-worktrees`** to create the worktree, dispatch the subagent into it, capture the resulting branch name, and clean up the worktree on completion or abort. (Same skill as best-of-N uses.) Without this, the subagent would write to the orchestrator's working tree and partial commits on failure would contaminate it.
- **Merge subagent branch back to orchestrator's branch.** After the SubagentStop hook approves and the subagent commits in its worktree, the orchestrator runs `git merge --no-ff <subagent-branch>` (or `git rebase` if the project policy prefers linear history). For best-of-N, only the winner's branch is merged; loser branches are kept in worktrees under `_attempts/best-of-n-<task>/`. WITHOUT this merge, Step 6's `git push` would push an empty branch — see review round 10. Capture merge conflicts: surface to user, do NOT auto-resolve.
- TDD enforcement: if `coverage < 0.6`, the plan must show test commits preceding impl commits. The SubagentStop hook (auto, wired in B3, full handler in C7) checks `git log` in the worktree for a recent `test:` commit and denies on violation.
- The SubagentStop hook fires automatically when the subagent stops. On `permissionDecision: deny`, pause and surface the reason to the user; on `allow`, advance.
- **Do NOT remove `FOLDER/current_task.json` between best-of-N parallel hook returns.** With K=3 parallel subagents, deleting after the first hook return would cause the remaining 2 subagents' hooks to find no `current_task.json` and silently fall through to the `allow` ("orchestrator hasn't dispatched") branch. Instead: overwrite `current_task.json` before EACH new task dispatch (Step 5 iterates per plan task). Stale data is impossible because the next dispatch's overwrite is the synchronization point. Only after Step 5 finishes for ALL tasks (or pipeline aborts/pauses) should the file be removed.

- **If the hook returns `deny` because of a transient gemini failure** (reason starts with `"fail-closed: gemini unavailable"`), the orchestrator surfaces this to the user with the offer to: (a) resolve gemini auth/network and `/pipette resume <topic>` (which re-dispatches the Step 5 task fresh), or (b) `override` (write a `feedback_pipette_hook_override_<topic>.md` memory entry + advance). This is the user override path the spec contemplates for hard gates.

Append events at every dispatch to `FOLDER/05-execution-log.md`.

## Step 6: Ship

Bash: `git push no-mistakes <current-branch>`. The no-mistakes proxy runs `/review` in a disposable worktree and either forwards + opens a PR or blocks.

On block: print the /review output verbatim to the user, then run `python -m tools.pipette abort "$ARGS"` and exit. Per the pipeline graph (Task **S6** `pipeline_graph.json`) gate_review FAIL transitions to exit_aborted, NOT to pause. The user must address the /review findings (typically by amending the relevant subagent commits) and re-run `/pipette <topic>` from scratch — the prior run's artifacts are preserved under `<folder>-aborted/`.

On open: write `FOLDER/06-pr-link.md` with the PR URL and the verdict summary.

## Step 7: Eval

Read `FOLDER/trace.jsonl`. Compute objective signals:
- `/review` passed first try? (boolean — was there a Step 6 retry event?)
- Plan needed mid-execution rework? (any `step=4 event=revised` after Step 4 first wrote?)
- Subagent retry count
- Gemini FAIL count and jump-back distribution
- NEEDS_RESEARCH raise count

Ask user: "Did each step earn its time? Rate 1–5: graph / grill / diagram / sanity-check / plan / execute / ship." (B-revision 2026-04-28: glossary rating dropped — grill now includes glossary updates inline.)

Write `FOLDER/07-eval.md` with the YAML frontmatter format the F2 weekly aggregator parses:

```markdown
---
topic: <kebab-topic>
folder: <FOLDER>
finished_at: <ISO 8601>
objective:
  review_first_try: true | false
  plan_revised: true | false
  subagent_retry_count: <int>
  gemini_fail_count: <int>
  gemini_jump_back_distribution: {1: <count>, 2: <count>}
  needs_research_count: <int>
self_report:                 # 1–5 ratings, exactly the keys below
  graph: <int>
  grill: <int>
  diagram: <int>
  sanity_check: <int>
  plan: <int>
  execute: <int>
  ship: <int>
---

<free-form notes paragraph from the user, optional>
```

Append a one-line lesson to `docs/pipeline/_meta/lessons.md` (format: `- YYYY-MM-DD <topic>: <one-line takeaway>`).

Bash: `python -m tools.pipette finish --folder=FOLDER` (removes lockfile, prints "✅ pipeline complete: <topic>"). Stage and offer to commit `FOLDER/` and `_meta/` updates.
