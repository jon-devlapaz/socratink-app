# Agent Onboarding

This file is a short entrypoint for Codex sessions.

Canonical workflow, agent roles, and repo constraints live in [AGENTS.md](../../AGENTS.md). Do not duplicate or override them here.

## What This Repo Is

LearnOps-tamagachi is an MVP-stage hosted learning product with:

- a drill engine
- a knowledge graph UI
- Vercel serverless deployment constraints
- ingestion and extraction flows
- an active research track for evidence-backed product language

This is not a greenfield repo. Default to stabilization over expansion.

## Read Order

Start every new session with:

1. [AGENTS.md](../../AGENTS.md)
2. [docs/project/state.md](../project/state.md)
3. [docs/codex/session-bootstrap.md](session-bootstrap.md)
4. [docs/theta/state.md](../theta/state.md) when research or claims are involved

## Working Rules

- Treat [AGENTS.md](../../AGENTS.md) as the source of truth for role boundaries and routing.
- Use [docs/codex/hotfix-workflow.md](hotfix-workflow.md) for narrow regressions.
- Use [docs/drill/graph-invariants.md](../drill/graph-invariants.md) before changing drill or graph behavior.
- Assume hosted behavior can diverge from local behavior.
- Keep `AGENTS.md` short and keep deep context in skills or focused docs.
- In mixed-agent workflows, let `orchestrator` own final consolidation of `docs/project/state.md` unless a different editor is explicitly assigned.
- When specialists disagree, write down the disputed point, evidence, chosen path, owner, and resulting state/doc updates before moving on.

## Default Usage

- `orchestrator` owns direct execution unless a specialist is clearly better suited.
- `theta` is for evidence quality, claims, and learning-science review.
- `sherlock` is for debugging, root-cause analysis, and repo bloat or structural investigation.
- `elliot` is for product framing and implementation planning.
- `thurman` is for QA and release-risk review.
- `rob` is read-only creative support, not the default executor.
- `glenna` is a post-hoc review layer, not a live supervisor.

## Common Mistakes

- Treating local success as deployment validation.
- Letting graph presentation become the source of truth.
- Using AI to replace the learner's generation step.
- Expanding docs with overlapping canonical guidance instead of updating the owning doc.
- Asking read-only specialists to implement changes before the behavior is settled.
