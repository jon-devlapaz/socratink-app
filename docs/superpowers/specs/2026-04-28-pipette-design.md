# Pipette — Heavy-Planning Pipeline Skill

**Status:** Design approved 2026-04-28. Ready for implementation plan.
**Trigger:** User-invoked slash command `/pipette <topic>`.
**Install:** Project-only at `socratink-app/.claude/commands/pipette.md`.

---

## 1. Purpose

Pipette is a single slash command that runs a fixed multi-step pipeline before any code is touched. It enforces heavy planning, independent verification, reality grounding via the code-review-graph MCP, and a no-mistakes-gated push. Each run produces a per-feature folder of numbered artifacts that future runs can learn from.

The command is opt-in. Default flows (a normal "let's build X" request) still go through standard brainstorming. Pipette is invoked only when the user judges a task worth the ceremony.

## 2. Non-goals

- **Not a replacement** for `superpowers:brainstorming`. Pipette is heavier and explicit-only; brainstorming remains the default for ad-hoc creative work.
- **Not a cloud / async system.** Execution stays synchronous and local. Cloud handoff (Devin, Codex Cloud, Cursor cloud agents) is deliberately omitted; the pipeline's value is the human-in-loop gates that synchronous execution makes cheap.
- **Not multi-repo.** v1 lives in socratink-app and may hard-code project-specific paths (no-mistakes target, `tests/e2e/` smoke runner, code-review-graph MCP location).
- **Not a coding agent.** Pipette orchestrates other skills and MCPs; it does not directly write production code.

## 3. Pipeline shape

```
−1  Read project constants (CONSTITUTION.md, UBIQUITOUS_LANGUAGE.md)
 0  Graph reconnaissance (code-review-graph MCP)
 1  Grill (mattpocock grill-me, graph-augmented)
 1.5 Glossary delta (mattpocock ubiquitous-language)
 2  Diagram (Mermaid by default, Excalidraw opt-in)
 3  Multi-agent sanity check (4 reviewers → verifier → gemini picker)
 4  Plan (superpowers:writing-plans)
 5  Execute (superpowers:subagent-driven-development + SubagentStop hook + optional best-of-N)
 6  Ship (git push no-mistakes → /review in disposable worktree → PR)
 7  Eval (objective signals + 1-line self-report)
```

### Step −1: Read project constants

Two static files at `docs/pipeline/_meta/`:

- **`CONSTITUTION.md`** — Architectural constraints that govern every feature ("all DB writes go through repository X", "no cross-bounded-context imports", "all background jobs use queue Y"). Hand-curated. Updated rarely.
- **`UBIQUITOUS_LANGUAGE.md`** — DDD glossary, project-wide. Updated by Step 1.5 of every pipette run.

Both are prepended to Step 0's input. They define the rules of the game before reality grounding begins.

### Step 0: Graph reconnaissance

Run the code-review-graph MCP in this order against the topic:

```
1. semantic_search_nodes(<topic keywords>)         → relevant nodes
2. get_architecture_overview()                      → high-level structure
3. get_impact_radius(nodes from step 1)             → blast radius + risk_score
4. get_affected_flows(nodes from step 1)            → execution paths likely touched
5. query_graph for tests covering those nodes       → coverage map
6. minimal_review_set(nodes from step 1)            → smallest review surface
```

**Cross-feature scan:** Before producing the artifact, scan `docs/pipeline/*/00-graph-context.md` for runs whose impact-radius overlaps the current topic. Prepend a digest of their `01-grill.md` and `04-plan.md` (one paragraph each) so prior decisions are surfaced. **Cap at the top 3 most-recent overlapping runs** to bound context growth.

**Watch mode:** Pipette assumes the code-review-graph MCP runs in incremental mode via a post-commit `/graphify` hook (separate from this spec). Step 0 reads a fresh graph rather than rebuilding per run. If the graph is stale, Step 0 logs a warning and proceeds.

**Artifact:** `00-graph-context.md` containing modules, callers/callees, blast radius, risk_score, minimal_review_set, coverage map, prior-feature digest.

### Step 1: Grill

Invoke `grill-me` with `00-graph-context.md` prepended. Grill-me's existing rule applies — when a question can be answered by exploring the codebase, explore instead of asking. The graph context makes that exploration cheap.

**User gate (soft):** approve the grill-me design summary before advancing.

**Artifact:** `01-grill.md` — design summary covering the decisions reached.

### Step 1.5: Glossary delta

Invoke `ubiquitous-language` against the conversation so far. The skill writes to `UBIQUITOUS_LANGUAGE.md`; pipette intercepts the write to land at `docs/pipeline/_meta/UBIQUITOUS_LANGUAGE.md` (project-level, not feature-level).

The per-feature folder receives `01b-glossary-delta.md` showing only the additions and changes from this run.

**User gate (soft):** approve the delta before advancing.

**Artifacts:** `01b-glossary-delta.md` (per-feature), `_meta/UBIQUITOUS_LANGUAGE.md` (updated in place).

### Step 2: Diagram

**Default:** Auto-generate a Mermaid diagram seeded from `00-graph-context.md`'s impact graph + glossary terms via `workflow-diagramming`. Save as `02-diagram.mmd`.

**Opt-in escalation:** If the topic is architectural / spatial, the user types `excalidraw` to escalate. Pipette opens the same scene in Excalidraw via the official MCP for whiteboarding. Save as `02-diagram.excalidraw`.

The diagram **must** use canonical glossary terms. This is a soft check at user gate; Step 3's consistency reviewer enforces it.

**User gate (soft):** approve the diagram before advancing.

### Step 3: Multi-agent sanity check (hard gate)

Replaces the original single-Gemini call with a fan-out:

1. **Contracts reviewer** — reads grill + glossary + diagram against real symbols from `00-graph-context.md`. Flags: invented APIs, missing dependencies, type mismatches. (The plan does not yet exist at this gate; Step 4 happens after.)
2. **Impact reviewer** — re-runs `get_affected_flows` against the proposal. Flags: missed callers, untested affected paths.
3. **Glossary-consistency reviewer** — checks every domain term in grill + diagram against `UBIQUITOUS_LANGUAGE.md`. Flags: synonyms, undefined terms.
4. **Test-coverage reviewer** — checks coverage map against the proposal. Flags: changes to untested code, missing test plan.

**Reviewers run in parallel**, not sequentially. The latency budget for the gate is `max(reviewer_latency) + verifier_latency + picker_latency`, not the sum. Implementation must dispatch via `superpowers:dispatching-parallel-agents` (or equivalent) to honor this. Sequential dispatch is a defect, not a tradeoff.

Each reviewer emits findings with a confidence score (0–1). A **verifier agent** re-checks each finding against actual code (mirroring Anthropic's verification-of-findings pattern). Only findings ≥ 0.8 confidence survive.

**Gemini as picker.** Surviving findings are passed to `gemini --approval-mode plan` along with grill + glossary + diagram + graph context. Gemini emits the canonical YAML verdict:

```yaml
verdict: PASS | FAIL | NEEDS_RESEARCH
jump_back_to: 1 | 1.5 | 2 | null     # null when PASS or NEEDS_RESEARCH
research_brief: <inline brief, only when NEEDS_RESEARCH; see §5.5>
notes: |
  <what's wrong, what to revise>
```

`jump_back_to: 3` is invalid (the gate cannot loop to itself); `jump_back_to: 4` is invalid (the plan does not yet exist at the time of the gate). `NEEDS_RESEARCH` does **not** loop back — it pauses the pipeline for outside input then re-runs Step 3 with the research findings in scope (see §5.5).

**YAML retry.** Pipette parses Gemini's verdict against the schema. On parse failure or schema violation, retry up to 3 times with the prior bad output appended as "this output was not valid YAML for the required schema; emit only the YAML and nothing else". After 3 failed attempts, raise to user as a hard error — do not silently proceed.

**Process-level failure.** If the `gemini` CLI itself returns a non-zero exit code (auth expired, network failure, rate-limit exhausted), this is **not** a YAML retry — it is a process failure. Pipeline pauses immediately, prints the exact stderr from gemini, and instructs the user to resolve the underlying issue (re-auth, retry, etc.) and resume with `/pipette resume <topic>`. Never loop on process-level errors.

**Hard gate:** FAIL forces loop-back to gemini-picked step.

**Override:** User types `override` → one-line "why" prompt → memory entry `feedback_gemini_override_<topic>.md` written → pipeline proceeds to Step 4.

**Manual jump-back override:** User can override gemini's `jump_back_to` with `--jump-to N`.

**Artifact:** `03-gemini-verdict.md` containing all reviewers' raw findings, verifier filter results, and Gemini's final YAML verdict.

### Step 4: Plan

Invoke `superpowers:writing-plans` with the full artifact stack. The plan must reference real symbols from `00-graph-context.md`. After the plan is drafted, re-run `get_impact_radius` on the *proposed* changes to validate the plan covers all affected files. If coverage is incomplete, the plan revises before user gate.

**User gate (soft):** approve plan before advancing.

**Artifact:** `04-plan.md`.

### Step 5: Execute

Invoke `superpowers:subagent-driven-development`. Each independent plan task is dispatched to a subagent in the same session.

**SubagentStop hook (deterministic).** A `SubagentStop` agent-handler hook runs after each subagent returns:
- Reads the subagent's diff
- Runs spec-compliance + code-quality review against `04-plan.md`, using the same severity scale as the project `/review` skill (Critical / High / Medium / Low / Polish)
- Returns `permissionDecision: deny` on any Critical finding; otherwise `allow`
- `deny` blocks progression; pipeline pauses for user resolution

**Hook crash semantics.** If the SubagentStop hook itself crashes or returns a non-zero exit code instead of a structured `permissionDecision`, pipette treats this as `deny` and pauses for user resolution. The hook's output and exit code are written to `trace.jsonl` for diagnosis. Never silently pass on hook failure — fail-closed is the only safe default for a deterministic gate.

**Best-of-N for high-risk tasks (optional).** When a subagent task has `risk_score >= HIGH` (from Step 0) or coverage of the affected modules is below threshold, pipette dispatches the same task to **K=3** subagents in parallel via `superpowers:dispatching-parallel-agents` + `superpowers:using-git-worktrees`. A selector subagent compares outputs against the plan's acceptance criteria and Step 0's `minimal_review_set`, picks the best, archives the rest to `_attempts/best-of-n-<task>/`.

**TDD enforcement.** When `coverage < threshold` for the affected modules (per Step 0), the plan must include a test commit before each implementation commit. The SubagentStop hook fails the task if `git log` shows the test commit didn't precede the impl commit.

**Per-subagent gate (automatic):** SubagentStop hook gates each subagent return.

**Crash recovery.** Step 5's single-task path runs in a disposable git worktree (the same machinery best-of-N uses). On crash or `abort` gate, the worktree is removed; partial commits never leak into the user's working tree. Recovery on resume re-dispatches the failed task into a fresh worktree.

**Artifact:** `05-execution-log.md` (record of subagent dispatches, diffs, hook decisions, best-of-N selections) + commits.

### Step 6: Ship

Run `git push no-mistakes`. The no-mistakes git proxy intercepts the push, runs `/review` in a disposable worktree, and only forwards to origin + opens a PR on PASS.

**Hard gate (automatic):** no-mistakes' /review.

**Artifact:** `06-pr-link.md` with the PR URL and the /review verdict summary.

### Step 7: Eval

After Step 6 succeeds, pipette runs an automatic eval pass.

**Objective signals (auto-collected):**
- `/review` passed first try? (boolean)
- Plan needed mid-execution rework? (boolean)
- Subagent retry count
- Gemini FAIL count and gemini-picked jump-back distribution
- PR merged within 24h? (filled in by deferred check)
- Regression detected within 14d? (filled in by scheduled agent)

**Self-reported signal (immediate):**
- One-line prompt: "Did each step earn its time? Rate 1–5: graph / grill / glossary / diagram / sanity-check / plan / execute / ship."

**Lessons feedback loop.** Pipette appends one-line lessons to `docs/pipeline/_meta/lessons.md`. Recent lessons are prepended to Step 0's input on subsequent runs.

**Weekly aggregate.** A scheduled agent (via `anthropic-skills:schedule`, weekly) reads `docs/pipeline/*/07-eval.md`, aggregates trends, identifies the weakest step, and writes `docs/pipeline/_meta/weekly-<YYYY-MM-DD>.md`.

**Deferred to v2:** independent gemini-as-grader of artifacts. Risks circularity (gemini grading what gemini already gated) and adds API cost. Re-evaluate after 5–10 runs.

**Artifact:** `07-eval.md`, `_meta/lessons.md` (appended), weekly aggregate (separate cadence).

## 4. Artifact folder structure

```
docs/pipeline/
├── _meta/
│   ├── CONSTITUTION.md            # hand-curated architectural constraints
│   ├── UBIQUITOUS_LANGUAGE.md     # project DDD glossary, updated by 1.5
│   ├── lessons.md                 # appended by Step 7 of every run
│   ├── weekly-YYYY-MM-DD.md       # scheduled weekly aggregate eval
│   └── .lock                      # mutex for concurrent runs (§5.6)
└── YYYY-MM-DD-HHMMSS-<topic>/
    ├── 00-graph-context.md
    ├── 01-grill.md
    ├── 01b-glossary-delta.md
    ├── 02-diagram.{mmd|excalidraw}
    ├── 03-gemini-verdict.md
    ├── 04-plan.md
    ├── 05-execution-log.md
    ├── 06-pr-link.md
    ├── 07-eval.md
    ├── trace.jsonl                # cross-cutting telemetry
    ├── _research/                 # research-gate briefs and pasted findings (§5.5)
    │   └── <step>-<slug>.md
    └── _attempts/                 # archived loop-back artifacts and best-of-N losers
        ├── 3-2026-04-28T14-32-00/
        └── best-of-n-<task>/
```

The whole `docs/pipeline/` tree is committed to git. It is documentation.

If the user kills a pipeline mid-run, the folder is renamed to `YYYY-MM-DD-HHMMSS-<topic>-aborted/` (full timestamp preserved per §5.6).

## 5. Cross-cutting concerns

### 5.1 Typed gates

Each user gate (soft) and automated gate (hard) is a typed hook event with explicit exit codes:

- `approve` — proceed to next step
- `revise` — return to current step with notes
- `abort` — kill pipeline, rename folder to `YYYY-MM-DD-HHMMSS-<topic>-aborted/` (per §5.6)

Hook events emit to `trace.jsonl`.

### 5.2 Telemetry

`trace.jsonl` records one event per line:

```json
{"ts": "2026-04-28T14:32:00Z", "step": 3, "event": "gate", "decision": "FAIL", "jump_back_to": 1, "tokens": 12340, "latency_ms": 8200}
```

Records: tool calls, gate decisions, latencies, token counts, gemini verdicts, hook denials. Cheap. Powers Step 7 evals and future A/B analysis.

### 5.3 Loop-back semantics

On Step 3 FAIL → jump to step N → all artifacts from step N onward are archived to `_attempts/N-<timestamp>/` before being rewritten. This preserves full audit trail of failed design attempts within a single pipeline run.

### 5.4 Override accounting

Every `override` of a Gemini FAIL writes a memory entry:

```
feedback_gemini_override_<topic>.md
---
date: YYYY-MM-DD
topic: <topic>
gemini_jump_back_to: <step>
gemini_notes_summary: <one line>
override_reason: <user one-line>
---
```

Pattern matches existing `feedback_propose_then_gemini_then_execute.md` memory.

### 5.5 Research Gate (cross-cutting hard stop)

Any step can raise `NEEDS_RESEARCH` when a load-bearing claim depends on external/world knowledge that the agent cannot confidently produce from the codebase or training data. Most often raised by Step 3's verifier; Step 1 grill-me may also raise it.

**When to raise (criteria, all must hold):**
- The claim is about *current external state* — a third-party API surface, a library's behavior in Q1–Q2 2026, an ecosystem norm — not something derivable from the codebase or basic language semantics.
- The agent's confidence on the claim is < 0.7.
- The claim is *load-bearing* — answering it wrong materially changes the design or plan.

**When NOT to raise:**
- The codebase or `00-graph-context.md` already answers the question (that is Step 0's job).
- The answer is in training data and stable (e.g. how Python's `dict` works).
- The agent is being timid rather than genuinely uncertain.

**Mechanism:**

1. The raising step writes a structured research brief to `docs/pipeline/<topic>/_research/<step>-<slug>.md`:
   ```yaml
   raised_by_step: 3
   raised_at: 2026-04-28T14:32:00Z
   research_question: "Does Pinecone support hybrid search w/ metadata filters as of Q2 2026?"
   why_needed: "Step 1 design assumes hybrid search w/ filter; verifier cannot confirm SDK supports it."
   suggested_tools: ["Claude Research", "ChatGPT Deep Research", "Perplexity", "Gemini Deep Research"]
   required_findings:
     - confirmation w/ source URL and date
     - example call pattern
     - known gotchas / breaking changes
   blocking: true
   ```
2. Pipeline pauses. Prints to chat: `"⏸  Pipeline paused at step <N>. Run deep research on docs/pipeline/<topic>/_research/<file>.md, then resume with /pipette resume <topic>"`.
3. User runs an external deep-research tool, pastes the result back via `/pipette resume <topic>`.
4. Pipeline appends the result to the same `_research/<file>.md` (under a `## Findings` section), then re-runs the step that raised the gate with the findings prepended to its input.

**Step 3 schema integration.** Step 3's verdict gains `NEEDS_RESEARCH` as a third value (alongside `PASS` and `FAIL`); see §3 Step 3 for the full schema. Unlike `FAIL`, `NEEDS_RESEARCH` does not loop back — it pauses, ingests the research, and re-runs Step 3.

**Anti-loop.** Two compounded caps prevent a single step from looping indefinitely:

- **Per-file cap (2).** A single `_research/<file>.md` can be re-raised at most twice. On the third raise of the same file, pipeline aborts with a hard error.
- **Per-step cap (3).** Across an entire pipeline run, a single step (e.g., Step 3) can raise `NEEDS_RESEARCH` at most **3 times total**, regardless of whether the questions are the same or different. On the fourth raise from the same step, pipeline aborts with a hard error — even if each individual question has its own file. This defends against the failure mode where an LLM rephrases the same logical question across raises and bypasses the per-file counter via slug variation.

Both caps are tracked in `trace.jsonl` and surfaced in `07-eval.md`.

**Counter granularity.** The per-file counter is keyed on `_research/<file>.md`. Slugs derive deterministically from the `research_question` text (kebab-cased first 8 words after stop-word removal) so semantically-identical questions resolve to the same file. The per-step counter is keyed on the raising step number, independent of slug content — this is the load-bearing defense against slug-juggling. The deterministic-slug heuristic is a best-effort optimization; the per-step cap is the guarantee.

**Resume guard.** `/pipette resume <topic>` requires an active paused pipeline for that topic. If no `_meta/.lock` (see §5.6) names the topic as paused, the command prints `"no paused pipeline for <topic>"` and exits with code 1. Resume never silently starts a fresh run.

**Eval signal.** Step 7 records: count of `NEEDS_RESEARCH` raises per run, and on resume whether the next verdict was `PASS` (research helped) or `FAIL` (research surfaced a deeper problem). Helps tune the criteria over time.

### 5.6 Concurrency

Pipette runs are mutually exclusive within a repository. Concurrent runs would race on `_meta/UBIQUITOUS_LANGUAGE.md`, `_meta/lessons.md`, the git index during Step 5, and the cross-feature scan at Step 0.

#### Lockfile schema

`docs/pipeline/_meta/.lock` is a YAML file. The orchestrator process is short-lived: a slash command invocation runs to completion, pause, or crash, and exits. The lockfile **persists across orchestrator process lifetimes** — that is the entire point of `state: paused`.

```yaml
topic: <topic>
folder: docs/pipeline/YYYY-MM-DD-HHMMSS-<topic>
pid: <process id of the orchestrator that last wrote this lockfile>
pid_started_at: <ISO 8601 timestamp of when that PID's process started, captured at lock-acquire time>
lock_written_at: <ISO 8601 timestamp of last lockfile write>
state: running | paused
paused_at_step: <step number, only when state=paused>
pause_reason: <NEEDS_RESEARCH | gemini_cli_failure | hook_crash | user_initiated, only when state=paused>
```

#### Lockfile state machine

Three valid states the lockfile can be in when `/pipette <topic>` is invoked:

| Lockfile state | PID liveness check | Action |
|---|---|---|
| `state: running` | Live AND `pid_started_at` matches process actual start time | "pipeline already running for `<existing-topic>` (pid `<N>`); abort or finish that run first" — exit 1 |
| `state: running` | Live BUT `pid_started_at` does NOT match process start time | PID was reused by an unrelated process. Treat lockfile as **stale crash**; same handling as next row. |
| `state: running` | PID dead | Crash. Rename `<folder>/` to `<folder>-crashed/` (preserving the full HHMMSS), append crash record to `trace.jsonl`, remove lockfile, then proceed with the new run. |
| `state: paused` | (PID liveness not checked — paused means orchestrator has exited cleanly) | "a paused pipeline exists for `<existing-topic>` — resume it with `/pipette resume <existing-topic>` or discard it with `/pipette abort <existing-topic>`" — exit 1. The paused folder is preserved as-is. |
| (no lockfile) | n/a | No active or paused pipeline. Acquire lockfile with `state: running`, proceed. |

**PID liveness with reuse defense.** Liveness is `kill -0 <pid>` (or platform equivalent). If alive, also read the process's actual start time (e.g., `ps -o lstart= -p <pid>` on macOS/Linux) and compare to `pid_started_at`. Mismatch → unrelated process reused the PID → treat as stale crash. This closes the OS-PID-reuse hole.

#### Pause / resume / abort lifecycle

| Action | Lockfile transition | Notes |
|---|---|---|
| Step transitions to next step | `state: running`, update `lock_written_at` | Heartbeat-style write, every step boundary |
| Pause (NEEDS_RESEARCH, gemini_cli_failure, hook_crash, user-initiated) | `state: paused`, set `paused_at_step` and `pause_reason`, update `lock_written_at`, **then** orchestrator exits cleanly | The `state: paused` write must complete and fsync before exit. If the orchestrator dies before this write, the next invocation will (correctly) treat it as a crash. |
| `/pipette resume <topic>` | Read lockfile. Require `state: paused`. Transition `state: paused → running`, update `pid`, `pid_started_at`, `lock_written_at`, write atomically, then continue from `paused_at_step`. | If `state` is anything other than `paused` (e.g., the lockfile is missing or `state: running`), exit 1 with `"no paused pipeline for <topic>"`. Resume never operates on a `running` lockfile and never starts a fresh run. |
| Step 7 completion | Remove lockfile | Clean finish |
| `/pipette abort <topic>` | If `state: paused`: rename folder to `<folder>-aborted/` (preserving HHMMSS), append abort record to `trace.jsonl`, remove lockfile. If `state: running` with live matching PID: refuse (`"pipeline is actively running; kill pid <N> first"`). If `state: running` with dead PID or PID-reuse: perform crash recovery (rename to `*-crashed/`) AND remove lockfile in one operation. | Abort is the user's escape hatch and must work in every state. |

#### Folder naming for terminal states

Folders preserve the full timestamp on rename to prevent collisions when the same topic fails repeatedly:

- Aborted: `YYYY-MM-DD-HHMMSS-<topic>-aborted/`
- Crashed: `YYYY-MM-DD-HHMMSS-<topic>-crashed/`

#### Atomicity

Lockfile manipulation distinguishes **initial acquisition** (must be exclusive) from **state updates** (the lock is already held).

**Initial acquisition.** Use atomic create-or-fail to prevent two concurrent `/pipette` invocations from racing on the empty-lockfile case:

- Open `_meta/.lock` with `O_CREAT | O_EXCL | O_WRONLY` (or equivalent — `mkdir` of a sentinel directory works as a portable fallback). Exactly one caller wins; the other receives `EEXIST` and falls into the "lockfile exists" branch of the state machine table above.
- Write the initial YAML, fsync, close. The lock is held atomically from `O_EXCL` success — the rename pattern is **not** used for acquisition.

**State updates while holding the lock.** Use per-process temp files to avoid two unrelated callers (e.g., a resume in one terminal racing the orchestrator's own heartbeat write — should never happen under mutual exclusion, but defense-in-depth is cheap):

- Write to `_meta/.lock.<pid>.<rand>.tmp` (PID + random suffix), fsync, then `rename()` over `_meta/.lock`. POSIX `rename()` is atomic on the same filesystem.
- Never write to a static `.lock.tmp` filename — that re-introduces the TOCTOU race the `O_EXCL` step was designed to prevent.

**Filesystem caveat.** Pipette assumes a POSIX local filesystem (APFS, ext4, btrfs). On NFS, FUSE, or filesystems without reliable `O_EXCL` semantics, lockfile mutual exclusion is not guaranteed; pipette must detect this at `pipette doctor` and refuse to run. Detection: attempt `O_EXCL` create on a sentinel file in `_meta/.lock-test`, then verify a second `O_EXCL` create on the same path fails synchronously.

#### Why a lockfile, not a queue

Queueing concurrent runs would let users start a second pipette mid-grill on a related topic — exactly when the first run's eventual `01-grill.md` would have been useful input. Mutual exclusion is the right default; if a second topic needs work, the user finishes or aborts the first run first.

## 6. Pre-ship preflight

Pipette has hard prerequisites that must be installed and verified *before* the slash command can ship. The plan must include a `pipette doctor` step that fails with a clear error if any of these are missing:

| Prerequisite | Why | How verified |
|---|---|---|
| `no-mistakes` git proxy installed and configured for `socratink-app` | Step 6 push gate | `git remote get-url no-mistakes` returns success |
| `code-review-graph` MCP wired in `.mcp.json` and reachable | Step 0 + Step 4 | `get_minimal_context_tool` returns a non-error response |
| Post-commit `/graphify` hook installed (keeps the graph fresh) | Step 0 reads a fresh graph rather than rebuilding per run | `.git/hooks/post-commit` references graphify |
| `gemini` CLI installed and authenticated | Step 3 picker | `gemini --version` returns 0 |
| mattpocock `grill-me` skill present in `~/.claude/skills/` | Step 1 | Skill discovery lists it |
| mattpocock `ubiquitous-language` skill present | Step 1.5 | Skill discovery lists it |
| `superpowers` plugin installed | Steps 4–5 | Plugin list includes it |
| `SubagentStop` agent-handler hook installed in `.claude/settings.json` | Step 5 deterministic gate | Settings reads back the hook |
| Excalidraw MCP installed (only if user opts in at Step 2) | Step 2 escalation path | Conditional check |
| Agentproof installed and runnable | Pre-ship structural check (below) | `agentproof --version` returns 0 |

If a prerequisite is missing, `pipette doctor` prints the exact install command and aborts. Pipette never silently degrades — a missing prerequisite is a hard error, not a fallback.

After all prerequisites pass, run pipette's local pipeline-graph structural validator (`python -m tools.pipette.validate_pipeline_graph tools/pipette/pipeline_graph.json`) as a one-time check. The validator flags: any non-exit node with no outgoing edges, any node unreachable from `start`, any gate node missing an outgoing edge for one of its declared decision labels, and any cycle other than the explicit Step-3 jump-back loops. (The spec previously referenced "Agentproof" / "arxiv 2603.20356"; that reference was based on a misunderstanding of the PyPI `agentproof` package, which is a test-assertion library, not a workflow-graph validator.)

## 7. Naming conventions

- **Slash command:** `/pipette <topic>`
- **Per-feature folder name:** `YYYY-MM-DD-HHMMSS-<kebab-case-topic>/` (HHMMSS prevents same-day same-topic collisions; matches §4 artifact tree)
- **Memory entries from override:** `feedback_gemini_override_<kebab-topic>.md`

## 8. Future work (deferred)

| Item | Why deferred | Earliest revisit |
|---|---|---|
| Gemini-as-grader at Step 7 | Risk of circularity; need data first | After 5–10 runs |
| Cloud / async execution flag at Step 5 | Synchronous discipline is the asset | When session limits become a real bottleneck |
| User-global install (`~/.claude/commands/`) | v1 is socratink-flavored | When second repo wants the pipeline |
| Truth Gate (sync verifier from the orchestrator diagram) at Step 5 | Premature; need no-mistakes-class infra at per-task level | After best-of-N has run >20 times |
| Multi-repo support | Hard-codes assumed | Same as user-global |

## 9. Open implementation questions for writing-plans

These are not design decisions but implementation details to nail down in the plan:

- Exact format of the 4 reviewers' findings (JSON schema)
- Hook handler script language (bash? Python? TypeScript?)
- How `--jump-to N` is parsed from chat input
- What `risk_score` threshold counts as HIGH for best-of-N triggering
- What numeric `coverage` threshold triggers TDD enforcement and best-of-N
- Where the post-commit `/graphify` hook lives (assumed installed; spec separate)
- Whether `trace.jsonl` is committed or `.gitignore`'d (recommend committed for the same reason as the rest of the folder)

## 10. Decisions log (for traceability)

| # | Decision | Locked |
|---|---|---|
| Q1 | Trigger | Explicit slash command, project-only |
| Q2 | Gating | User soft + Gemini hard with override |
| Q3 | Artifacts | Per-feature folder with numbered files |
| Q4 | Diagram | Asked at runtime → revised post-research to Mermaid-default |
| Q5 | Execute | Subagent-driven, augmented with SubagentStop hook + best-of-N |
| Q6 | FAIL loop-back | Gemini-picked with `--jump-to` override |
| Q7 | Install | Project-only |
| — | Glossary | At Step 1.5, project-level + per-feature delta |
| — | Reality grounding | code-review-graph MCP at Step 0, threaded into 1/2/3/4 |
| — | Eval | Objective + self-report at Step 7; gemini grader deferred |
| — | Name | `pipette` |

## 11. Publish path (v2)

Pipette is intended for public release on GitHub once v1 has been used 5–10 times in this repo and the rough edges have been ground off. This section captures what v2 needs so the work isn't lost; **none of it is in v1's scope**.

### What v2 must add

| Item | Purpose |
|---|---|
| `README.md` | What pipette is, why it exists, install steps, dependency list, one-screen example |
| `LICENSE` (MIT) | Matches mattpocock's `skills` repo and most of the agentic-dev ecosystem |
| `pipette.config.{json\|yaml}` | Abstracts project-specific values: push target (`no-mistakes` or another remote), smoke-runner path, severity-scale source, code-review-graph MCP location, gemini binary path. Defaults match v1's hard-codes so socratink keeps working. |
| `examples/` | One full redacted `docs/pipeline/<topic>/` from a real run, showing every artifact a user gets |
| Dependency-check script | `pipette doctor` — verifies no-mistakes, code-review-graph MCP, gemini CLI, mattpocock's grill-me and ubiquitous-language skills, and superpowers plugin are all installed and reachable |
| Compatibility note | Pipette assumes Claude Code as the host. Cross-host (Codex / Gemini CLI / Cursor) is out of scope; document the assumption explicitly. |

### What stays out of v2

- **Multi-repo orchestration.** Each repo runs its own pipette.
- **Cloud / async execution.** Same reason as in v1 (§2 non-goals).
- **Vendored copies of dependencies.** Pipette installs alongside its dependencies, never bundles them.

### Migration discipline

When promoting v1 → v2, the only code-touching change inside socratink-app should be: replace hard-coded paths with reads from `pipette.config.*`. No behavior change. The migration is a pure refactor; the config file's defaults preserve exact v1 behavior.
