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

**Cross-feature scan:** Before producing the artifact, scan `docs/pipeline/*/00-graph-context.md` for runs whose impact-radius overlaps the current topic. Prepend a digest of their `01-grill.md` and `04-plan.md` (one paragraph each) so prior decisions are surfaced.

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

1. **Contracts reviewer** — reads grill + glossary + plan against real symbols from `00-graph-context.md`. Flags: invented APIs, missing dependencies, type mismatches.
2. **Impact reviewer** — re-runs `get_affected_flows` against the proposal. Flags: missed callers, untested affected paths.
3. **Glossary-consistency reviewer** — checks every domain term in grill + diagram against `UBIQUITOUS_LANGUAGE.md`. Flags: synonyms, undefined terms.
4. **Test-coverage reviewer** — checks coverage map against the proposal. Flags: changes to untested code, missing test plan.

Each reviewer emits findings with a confidence score (0–1). A **verifier agent** re-checks each finding against actual code (mirroring Anthropic's verification-of-findings pattern). Only findings ≥ 0.8 confidence survive.

**Gemini as picker.** Surviving findings are passed to `gemini --approval-mode plan` along with grill + glossary + diagram + graph context. Gemini emits the canonical YAML verdict:

```yaml
verdict: PASS | FAIL
jump_back_to: 1 | 1.5 | 2     # only if FAIL; valid targets are completed prior steps
notes: |
  <what's wrong, what to revise>
```

`jump_back_to: 3` is invalid (the gate cannot loop to itself); `jump_back_to: 4` is invalid (the plan does not yet exist at the time of the gate).

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

**Best-of-N for high-risk tasks (optional).** When a subagent task has `risk_score >= HIGH` (from Step 0) or coverage of the affected modules is below threshold, pipette dispatches the same task to **K=3** subagents in parallel via `superpowers:dispatching-parallel-agents` + `superpowers:using-git-worktrees`. A selector subagent compares outputs against the plan's acceptance criteria and Step 0's `minimal_review_set`, picks the best, archives the rest to `_attempts/best-of-n-<task>/`.

**TDD enforcement.** When `coverage < threshold` for the affected modules (per Step 0), the plan must include a test commit before each implementation commit. The SubagentStop hook fails the task if `git log` shows the test commit didn't precede the impl commit.

**Per-subagent gate (automatic):** SubagentStop hook gates each subagent return.

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
│   └── weekly-YYYY-MM-DD.md       # scheduled weekly aggregate eval
└── YYYY-MM-DD-<topic>/
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
    └── _attempts/                 # archived loop-back artifacts and best-of-N losers
        ├── 3-2026-04-28T14-32-00/
        └── best-of-n-<task>/
```

The whole `docs/pipeline/` tree is committed to git. It is documentation.

If the user kills a pipeline mid-run, the folder is renamed to `<topic>-aborted/`.

## 5. Cross-cutting concerns

### 5.1 Typed gates

Each user gate (soft) and automated gate (hard) is a typed hook event with explicit exit codes:

- `approve` — proceed to next step
- `revise` — return to current step with notes
- `abort` — kill pipeline, rename folder to `*-aborted/`

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

## 6. Pre-ship preflight

Before Pipette v1 ships, run **Agentproof** (arxiv 2603.20356) against the pipeline graph as a one-time structural check. Agentproof reports that 27% of benchmark agentic workflows have structural defects (dead-end nodes, unreachable exits) and 55% violate human-gate policies. The check is cheap and catches structural bugs before they show up at runtime.

## 7. Naming conventions

- **Slash command:** `/pipette <topic>`
- **Per-feature folder name:** `YYYY-MM-DD-<kebab-case-topic>/` (matches existing `docs/superpowers/specs/` convention)
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
