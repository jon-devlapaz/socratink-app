# Founder Agent Orchestration Design

**Date:** 2026-05-12
**Status:** Drafted (brainstorm phase complete; pending founder review before plan + implementation)
**Author:** Brainstormed with Codex using Superpowers workflows; sanity-checked with Gemini and GPT-5.5; decisions made by Jon

---

## 1. Why this exists

This repo already contains high-value agent guidance, but it is fragmented across tool-specific roots and local runtime directories (`AGENTS.md`, `.claude/`, `.codex/`, Gemini-local state, repo docs, scripts, hooks). That fragmentation creates three recurring failures:

- **drift**: Claude-, Codex-, and Gemini-facing instructions can diverge
- **context waste**: agents spend turns rediscovering workflow truth that should be canonical
- **unsafe autonomy**: high-cost git actions rely too much on prose guidance and not enough on deterministic brakes

The goal is not to build a generic autonomous agent. The goal is to create a founder-facing orchestration layer for working agentically in this codebase, where agents can route correctly, stop when they should, and preserve human control over meaningful state changes.

## 2. Core thesis

> **This repo should have one canonical home for shared agent workflow truth, while deterministic enforcement for dangerous actions lives in code, not in prose.**

Three architectural invariants follow:

1. **Shared workflow truth is model-agnostic.** Canonical orchestration doctrine lives in a neutral `agents/` directory, not in `.claude/`, `.codex/`, or a Gemini-specific path.
2. **Root adapter files are thin.** `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` exist as entrypoints into the canon. They should not become parallel doctrine surfaces.
3. **Workflow prose is not the security boundary.** High-cost git actions must be enforced by a deterministic wrapper + git hook, not by asking an LLM to remember to pause.

## 3. Goals

- Create a canonical, model-agnostic home for shared founder workflow truth.
- Keep root adapter files short, explicit, and discoverable.
- Preserve high-signal tool-specific content while migrating only stable, cross-model doctrine into the canon.
- Encode the first deterministic workflow for the repo's highest-cost recurring founder friction: git integration.
- Shift git push safety from advisory prose to deterministic enforcement.
- Produce context-efficient workflow cards that are easier for agents to consume than long narrative docs.

## 4. Non-goals (v1)

- Building a generic workflow engine or DSL.
- Migrating every agent-facing file in one pass.
- Replacing existing runtime scripts (`scripts/doctor.sh`, deploy checks, hooks, etc.) with `agents/` content.
- Encoding feature development, UI prototyping, review, or deploy-confidence workflows before the git workflow proves the shape.
- Using `agents/` as a storage home for caches, auth state, or tool-local runtime artifacts.
- Treating local hooks as sufficient protection for protected branches; remote branch protection remains required.

## 5. Authority model

### 5.1 Canonical order

1. **`agents/`** — canonical shared workflow truth
2. **Root adapter files** — `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`
3. **Tool-specific directories** — `.claude/`, `.codex/`, `.gemini/` as runtime/config/wrapper surfaces

### 5.2 What belongs in `agents/`

`agents/` owns:

- workflow cards
- templates
- migration ledgers
- founder orchestration doctrine
- prompt batteries
- decision rubrics that any model should follow

`agents/` does **not** own:

- runtime executables that already belong under `scripts/`
- auth/session state
- local caches
- tool-specific hooks/settings syntax

Workflow cards should route to existing repo-owned scripts, docs, hooks, and checks instead of reimplementing them.

### 5.3 Adapter contract

`AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` should be thin adapters, but not empty pointers. Each must include:

- the canonical path where shared workflow truth lives
- the must-not-miss bootstrap rules
- the rule that tool-specific directories are not canonical doctrine
- explicit instructions to load the relevant canon before acting

They should remain short enough to avoid context bloat, but strong enough that a tool which auto-loads only the root file still sees the core constraints.

## 6. Initial file layout

```text
AGENTS.md
CLAUDE.md
GEMINI.md
agents/
  README.md
  MIGRATION.md
  _templates/
    workflow-card.md
  founder/
    WORKFLOWS/
      01-git-integration.md
scripts/
  agent-push.py
  git-hooks/
    pre-push
.agents/
  runtime/
    push-decisions.jsonl
```

## 7. Migration policy

Migration is selective, not wholesale.

Content should move from `.claude/` or similar locations into `agents/` only when it is:

- stable
- high-signal
- cross-model relevant
- worth repeatedly loading or discovering

High-value legacy content should not be deleted just because a new canon exists. It should be preserved until its signal has been captured or intentionally deprecated.

### 7.1 `agents/MIGRATION.md` statuses

Each candidate artifact should be tracked as one of:

- `promoted`
- `adapter-only`
- `tool-specific`
- `preserved-pending-review`
- `deprecated`

This ledger exists so future agents can distinguish settled canon from leftover sediment.

## 8. Workflow-card standard

Workflow cards are written agents-first: short, explicit, low-ambiguity, and easy to scan under context pressure.

Every workflow card should follow one fixed schema:

1. `Trigger`
2. `Goal`
3. `Inputs To Inspect`
4. `Risk Classification`
5. `Recommended Route`
6. `Required Confirmation`
7. `Verification`
8. `Stop Rules`
9. `Artifact Destination`

The template for this schema lives at `agents/_templates/workflow-card.md`.

## 9. First workflow: `git-integration`

### 9.1 Why this workflow comes first

Git commit/push/PR actions are:

- the highest-cost recurring founder friction
- the most likely place for unsafe “helpful autonomy”
- the easiest high-leverage workflow to make deterministic first

This workflow should route agent behavior for:

- commit shaping
- push route selection
- PR opening
- confirmation boundaries for persistent state changes

### 9.2 Action tiers

- **`safe`**
  - read-only local git inspection
- **`confirm`**
  - commit
  - branch delete
  - open PR
  - push `origin/dev`
  - push `no-mistakes/dev`
- **`hard-confirm`**
  - push `origin/main`
  - force-push
  - merge to a protected branch
  - prod-affecting deploy path

### 9.3 Route policy

`no-mistakes` is **not** the universal default. It is a costly review brake.

Default route recommendations:

- **Recommend `origin/dev`** for ordinary, narrow, straightforward `dev` changes where CodeRabbit on `origin` is sufficient.
- **Recommend `no-mistakes/dev`** for larger, higher-blast-radius, higher-risk, or messier changes that benefit from the additional brake.

Rules:

- urgency/frustration is never authorization
- agents must not chain two persistent-state actions in one step
- route selection is recommended by the enforcer, not inferred from chat memory

## 10. Deterministic push enforcement

### 10.1 Principle

The workflow card documents the policy. It does **not** enforce the policy.

The enforcement seam is:

- `scripts/agent-push.py`
- `scripts/git-hooks/pre-push`
- `.agents/runtime/push-decisions.jsonl`

### 10.2 `agent-push.py` contract

`scripts/agent-push.py` is the only allowed push path for agents.

Responsibilities:

1. inspect repo state and intended target
2. compute risk triggers deterministically
3. recommend `origin/dev` or `no-mistakes/dev`
4. print the recommendation, triggered rules, and required ack token
5. exit non-zero on the first run
6. accept a second run with `--ack ...`
7. recompute intent and invalidate the ack if anything material changed
8. record the decision
9. execute exactly one push path

The script should be implemented in Python, not Bash, because the risk logic and intent-binding rules will become unmaintainable in shell quickly.

### 10.3 `pre-push` hook contract

The `pre-push` hook exists to block raw `git push` attempts.

It should reject the push unless the wrapper created a valid one-shot authorization artifact that matches:

- exact remote
- exact refspec / destination
- remote URL allowlist
- current HEAD SHA
- current branch
- computed risk class
- fresh timestamp / nonce

This should be treated as tamper-evident friction, not cryptographic security. The real goal is to prevent accidental or shortcut agent pushes, not to defend against a malicious local user.

### 10.4 Hook installation

The enforcement is not real unless the hook is installed.

Bootstrap/doctor must verify:

- `core.hooksPath` points to the repo-owned hooks path, or
- the relevant hook is installed at the git layer

Fresh clones, worktrees, and alternate local checkouts must not silently skip this.

### 10.5 Remote identity

The wrapper must not trust local aliases like `origin` or `no-mistakes` by name alone.

It should allowlist expected remotes by URL and reject arbitrary refspecs by default.

### 10.6 Intent binding

The second-run ack is only valid if the push intent is unchanged.

At minimum, the wrapper must recompute and invalidate when any of these change:

- HEAD SHA
- dirty state
- diff hash
- remote URL
- destination branch/refspec
- route recommendation

## 11. Objective risk triggers

The risk model should use explicit deterministic triggers, not freeform “this feels risky.”

### 11.1 Hard-confirm triggers

Any of the following should force `hard-confirm`:

- destination is `main`
- operation is force-push
- operation targets a protected branch
- action is coupled to a prod-affecting deploy path

### 11.2 Confirm triggers

Any of the following should force at least `confirm`:

- commit
- branch delete
- PR open
- any push to `origin/dev`
- any push to `no-mistakes/dev`

### 11.3 `no-mistakes` recommendation triggers

The initial `no-mistakes` recommendation should fire when one or more of the following are true:

- change touches multiple subsystems
- change touches load-bearing runtime files or directories
- change touches shared instruction or workflow canon
- change is large by file count or diff size threshold
- change involved non-obvious reconciliation, conflict handling, or unclear branch state

Initial path-sensitive triggers for recommendation:

- `main.py`
- `ai_service.py`
- `auth/`
- `vercel.json`
- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `agents/`

The exact file-count / LOC thresholds should be finalized in the implementation plan, not improvised during coding.

## 12. Runtime decision logging

Operational evidence should live under a neutral runtime path:

```text
.agents/runtime/push-decisions.jsonl
```

Each entry should include:

- timestamp
- branch
- target remote/refspec
- remote URL
- HEAD SHA
- recommended route
- chosen route
- override status
- triggered rules
- ack mode

This log is for handoffs and auditing, not for doctrine.

## 13. Branch protection and real safety

Local hooks reduce accidental agent behavior. They do not replace remote policy.

Real `main`/force-push safety must continue to rely on remote protections such as GitHub branch protection.

This design assumes:

- local enforcement prevents casual bypass by agents
- remote enforcement protects against local mistakes that still get through

## 14. Founder interaction model

The founder remains in the loop for meaningful workflow decisions.

Implications:

- the wrapper recommends; it does not silently decide
- overrides are allowed, but require typed acknowledgment
- a brake is intended to slow decisions down, not imprison the founder

The system should prefer the cheapest adequate brake for the specific change, not the heaviest possible gate by default.

## 15. Out of scope for v1

- generalized workflow registries
- workflow execution engines
- dashboards for runtime audit logs
- non-git workflow enforcement
- migration of all tool-specific legacy content
- direct implementation of additional workflows before the git path proves the model

## 16. Definition of done for this design slice

This design slice is done when all of the following exist and agree with each other:

- `agents/README.md` defining the canon boundary
- `agents/MIGRATION.md` defining migration states
- `agents/_templates/workflow-card.md`
- `agents/founder/WORKFLOWS/01-git-integration.md`
- root adapter files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) updated to point into the canon
- `scripts/agent-push.py`
- `scripts/git-hooks/pre-push`
- hook-install verification in bootstrap/doctor
- runtime log path `.agents/runtime/push-decisions.jsonl`

And the enforcement contract is true in practice:

- raw `git push` is blocked without wrapper authorization
- the wrapper recomputes intent before executing a push
- agent push recommendations are deterministic
- founder override is possible only through explicit typed acknowledgment

## 17. Open questions for implementation planning

- exact file-count and diff-size thresholds for `no-mistakes` recommendation
- exact allowlist format for trusted remotes
- exact nonce/authorization artifact format shared between wrapper and hook
- whether adapter files should import canon directly or inline a minimal bootstrap plus path references
- whether doctor should fail hard or warn on missing hook installation in non-agent contexts
