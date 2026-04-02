# Agent Onboarding

This document explains how to use the repo's Codex agent setup in a way that matches the actual needs of LearnOps-tamagachi.

## What This Repo Is

LearnOps-tamagachi is an MVP-stage learning product with:

- a drill engine
- a knowledge graph UI
- hosted deployment on Vercel
- ingestion flows for pasted text, URLs, files, and limited YouTube support
- an emerging research track for evidence-backed learning claims

This is not a greenfield repo. The default goal is to stabilize and improve what already exists.

## Read Order

Start every new session with:

1. [AGENTS.md](../../AGENTS.md)
2. [docs/project/state.md](../project/state.md)
3. [docs/codex/session-bootstrap.md](session-bootstrap.md)
4. [docs/theta/state.md](../theta/state.md) when research or claims are involved

## Directory Map

- `.codex/config.toml`
  Repo-level Codex configuration and agent registration.
- `.codex/agents/*.toml`
  Per-agent role definitions.
- `.agents/skills/theta-research/`
  Research skill, references, and templates for evidence work.
- `.agents/skills/glenna-review/`
  Review skill and template for post-hoc agent performance evaluation.
- `docs/project/state.md`
  Current product and environment truth.
- `docs/codex/`
  Codex usage docs for this repo.

## Agent Roles

### `orchestrator`

Use for:

- most direct implementation work
- end-to-end task ownership when no specialist is clearly required
- execution that may need light coordination across agents

Default mode:

- execution-first
- delegates selectively rather than by default

### `theta`

Use for:

- questions about learning science
- evaluating product claims against literature
- deciding whether language is evidence-backed or speculative

Do not use for:

- implementation-first coding tasks
- deployment debugging

Default mode:

- read-only
- evidence-focused
- labels conclusions as confirmed, likely, or speculative

### `sherlock`

Use for:

- tracing regressions
- debugging local vs deployed mismatches
- root-cause analysis with logs, code paths, and reproductions

Do not use for:

- writing features before the cause is understood

Default mode:

- read-only
- investigation-first

### `elliot`

Use for:

- product framing
- implementation planning
- interaction flow definition
- scoping MVP behavior before coding starts

Do not use for:

- freeform code changes without a defined plan

Default mode:

- planning-first
- owns change framing and handoff shape

### `rob`

Use for:

- brainstorming features, names, and concepts
- talking through creative directions
- adding morale, momentum, and playful product energy
- shaping rough ideas before they need implementation structure
- founder-style conversation about what this product wants to become

Do not use for:

- editing files
- implementing features
- owning execution or deployment hardening

Default mode:

- read-only
- creative, conversational, and co-founder-like

Note:

- `rob` is no longer the default entrypoint agent for the repo
- prefer `orchestrator` for execution
- prefer `elliot` when you need tighter product framing instead of freeform ideation

### `thurman`

Use for:

- release-readiness review
- regression review
- fallback-path validation
- identifying what is safe for MVP vs post-launch debt

Default mode:

- read-only
- severity-first QA posture

### `glenna`

Use for:

- reviewing a completed agent interaction end to end
- identifying weak handoffs, role drift, or missing constraint checks
- logging improvement recommendations for future agent prompts or workflow changes
- producing follow-up tasks for the correct owner agent

Do not use for:

- live orchestration during an active task
- directly implementing the fixes she recommends
- replacing `thurman` for product QA or `sherlock` for root-cause debugging

Default mode:

- post-hoc review only
- recommendation-first
- append review notes to the agent review log only when explicitly asked

## Best Practices For This Repo

- Start from repo root when launching Codex.
- Do not assume local success means deployment success.
- Use narrow fixes when stabilizing hosted behavior.
- Check current code before proposing architecture changes.
- Keep `AGENTS.md` short; put deep references in skills and docs.
- Treat Vercel as a first-class constraint when external services are involved.
- Distinguish product intent from current implementation.
- In mixed-agent workflows, let `orchestrator` own final consolidation of `docs/project/state.md` unless a different editor is explicitly assigned.
- When specialist agents disagree, write down the disputed point, evidence, chosen path, owner, and resulting state/doc updates before moving on.
- Invoke `glenna` after a meaningful interaction when you want to improve the agent system itself.
- Keep Glenna recommendation-only. Route actual changes back to the owning agent.

## High-Value Workflows

### 1. Deployed bug investigation

Use when something works locally but fails on Vercel.

Recommended flow:

1. `sherlock` inspects the exact code path and deployment logs.
2. `elliot` defines the acceptable fallback behavior for MVP.
3. `orchestrator` implements the narrow fix or graceful degradation.
4. `thurman` reviews whether the deployed fallback is acceptable for user testing.

Example in this repo:

- YouTube transcript import worked locally but failed on Vercel because YouTube blocked serverless IPs.
- Correct action was not "keep debugging frontend."
- Correct action was:
  - confirm backend `RequestBlocked`
  - define manual transcript fallback
  - return clear hosted-safe error messaging

### 2. Drill flow behavior change

Use when changing node progression, routing, or graph-state transitions.

Recommended flow:

1. `elliot` defines intended product behavior.
2. `sherlock` checks current state transitions in backend and frontend.
3. `orchestrator` implements backend/frontend sync changes.
4. `thurman` reviews regression risk around progression and post-drill graph updates.

Relevant files:

- [ai_service.py](../../ai_service.py)
- [main.py](../../main.py)
- [public/js/app.js](../../public/js/app.js)
- [public/js/graph-view.js](../../public/js/graph-view.js)

### 3. Knowledge graph UX change

Use when adjusting focus mode, fog-of-war, locked node behavior, or drill context presentation.

Recommended flow:

1. `elliot` defines the intended visual and interaction rule.
2. `sherlock` verifies current class/state conflicts.
3. `orchestrator` edits the graph view implementation and styles.
4. `thurman` validates hover, drill, and locked-node regressions.

Example in this repo:

- hover focus was conflicting with drill focus
- locked nodes needed teaser labels instead of blank circles

### 4. Research-backed product wording

Use when making claims about memory, retrieval, consolidation, or neurocognitive mechanisms.

Recommended flow:

1. `theta` evaluates the claim and evidence strength.
2. `elliot` decides how product language should change.
3. `orchestrator` updates copy or related implementation if needed.

Relevant skill:

- [.agents/skills/theta-research/SKILL.md](../../.agents/skills/theta-research/SKILL.md)

### 5. Security hardening for ingestion

Use when touching `/api/extract`, `/api/extract-url`, `/api/extract-youtube`, or similar backend surfaces.

Recommended flow:

1. `sherlock` identifies trust boundaries and failure modes.
2. `elliot` defines acceptable MVP behavior.
3. `orchestrator` implements hardening.
4. `thurman` checks release risk.

Must think about:

- SSRF
- internal error leakage
- local vs hosted differences
- fallback messaging

### 6. Agent performance review

Use when an interaction is complete and you want a durable assessment of how well the agent system performed.

Recommended flow:

1. Finish the actual task first.
2. Invoke `glenna` with the completed interaction and any relevant repo files.
3. Have Glenna evaluate role adherence, epistemic quality, workflow quality, repo constraint compliance, handoff quality, and missed opportunities.
4. Have Glenna append the review to `docs/codex/agent-review-log.md`.
5. Hand the recommended improvements back to `theta`, `sherlock`, `elliot`, `rob`, or `thurman` as appropriate.

Use Glenna when:

- an agent produced a weak or ambiguous handoff
- deployment or security constraints were missed
- you want to improve prompts, roles, or workflow order
- you want a persistent review trail instead of ad hoc chat critique

## Example Prompts

### Use `sherlock`

```text
Investigate why URL import works locally but fails in production. Confirm whether the failure is frontend, backend, or deployment-related, and identify the narrowest fix.
```

### Use `elliot`

```text
Define the intended user experience for a failed hosted YouTube import. Keep it MVP-scoped and describe the fallback path we should implement.
```

### Use `rob`

```text
Pressure-test this product idea as a creative co-founder. When the idea is mature enough for planning or execution, return a copy-ready handoff prompt for `elliot` or `orchestrator` instead of taking implementation ownership yourself.
```

### Use `thurman`

```text
Review the current branch for MVP deployment risk. Prioritize user-facing regressions, hosted failures, and missing fallback behavior.
```

### Use `theta`

```text
Evaluate whether our current language about retrieval, misconception repair, and consolidation is evidence-backed. Label each conclusion as confirmed, likely, or speculative.
```

### Use `glenna`

```text
Review the completed interaction for agent quality. Evaluate role adherence, epistemic quality, workflow quality, repo constraint compliance, handoff quality, and missed opportunities. Append a review entry to docs/codex/agent-review-log.md and end with explicit follow-up prompts for the owning agents.
```

## Common Mistakes

- Asking `rob` to code before the behavior is defined.
- Asking `theta` to author implementation details.
- Treating Vercel-only failures as random transient bugs.
- Assuming external service success locally means the hosted path is fine.
- Dumping long research notes into `AGENTS.md`.
- Starting sessions deep in a nested folder and expecting the same repo behavior.
- Asking Glenna to fix the issue she identified instead of routing the change to the owner agent.
- Using Glenna during an active task instead of after the interaction is complete.

## FAQ

### Do the files in `.codex/agents/` do anything by themselves?

Not reliably for this repo. They are intended to be registered through [.codex/config.toml](../../.codex/config.toml).

### Why keep `AGENTS.md` short?

Because it should hold stable rules and repo conventions. Deep context belongs in skill references and docs so the system can load it progressively.

### Why are some agents read-only by default?

Because this repo has meaningful deployment, product, and research constraints. Investigation and review agents should not mutate code by default.

### Why not let every agent edit?

Because it blurs ownership and increases assumption-driven changes. Planning, investigation, execution, and QA are intentionally separated here.

### What is the default implementation path?

Use `elliot` for framing, `rob` for execution, and `thurman` for release review when the change is non-trivial.

### What is the default path for a bug that appears only in production?

Use `sherlock` first. Confirm the actual deployed cause before coding a fix.

### When should I use Glenna?

Use Glenna after a completed interaction when you want to improve the agent system itself. She is a manual review layer, not the primary agent for delivery work.

### What should Glenna log?

Each review should append:

- timestamp
- interaction summary
- agents involved
- context reviewed
- what went well
- findings
- recommended improvements
- recommended owner for each improvement
- confidence

Findings should use `high`, `medium`, or `low` severity.

### Can I rely on YouTube transcript import in hosted preview?

No. Hosted retrieval may be blocked by YouTube. The current MVP fallback is manual transcript paste.

### Where should research papers and notes live?

Keep structured notes in:

- [.agents/skills/theta-research/references/](../../.agents/skills/theta-research/references/)

Keep templates in:

- [.agents/skills/theta-research/assets/](../../.agents/skills/theta-research/assets/)

Use raw PDFs cautiously if they are large, private, or copyrighted.

### What should I verify after a change?

At minimum:

- syntax or compile checks for touched backend/frontend files
- the exact user-facing flow that was changed
- local vs deployed implications if external services are involved

## Suggested Next Step

Link this document from:

- [AGENTS.md](../../AGENTS.md)
- [docs/codex/session-bootstrap.md](session-bootstrap.md)

That makes it easier for new sessions and collaborators to discover it.
