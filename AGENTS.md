# Agents

This repository supports a small multi-agent workflow for product, research, and implementation work.

## Layout

- `.codex/config.toml`
  Shared Codex configuration for this repo.
- `.codex/agents/*.toml`
  Per-agent definitions and default instructions.
- `.agents/skills/*`
  Local reusable skills with references and templates.
- `docs/project/state.md`
  Current product and execution state for the whole project.
- `docs/theta/state.md`
  Current state for the Theta research track.
- `docs/codex/session-bootstrap.md`
  Bootstrap context for new Codex sessions.

## Current Agent Roles

- `orchestrator`
  Default repo agent for direct execution and selective routing to specialists only when needed.
- `theta`
  Research agent focused on neurocognitive science and evidence quality.
- `sherlock`
  Investigation agent for debugging, tracing regressions, and root-cause analysis.
- `elliot`
  Product and systems agent for shaping requirements into concrete implementation plans.
- `rob`
  Read-only co-founder voice for creative exploration, product instinct, and concept shaping.
- `thurman`
  QA and release-readiness agent for validating workflows, risk, and deployment behavior.
- `glenna`
  Post-hoc review agent for evaluating agent interaction quality, handoffs, and improvement opportunities.

## Working Conventions

- Keep agent instructions specific and role-bound.
- Put longform evidence and paper notes under `.agents/skills/theta-research/references/`.
- Put reusable agent review workflow guidance under `.agents/skills/glenna-review/`.
- Keep project state documents short and current rather than exhaustive.
- Treat `docs/codex/session-bootstrap.md` as the minimum context a fresh coding session should read first.
- In mixed-agent workflows, `orchestrator` owns final consolidation of `docs/project/state.md`.
  Specialists may propose or draft state updates, but the final merged project-state update should be written once by the workflow owner unless a different editor is explicitly assigned.
- Resolve specialist disagreement with an explicit decision record.
  Record the disputed point, the evidence on each side, the decider, the chosen path, and any resulting state or doc updates.

## Assumptions To Avoid

- Role files alone are not enough.
  Agent files under `.codex/agents/` must also be registered in `.codex/config.toml` via `[agents.<name>]` and `config_file`.
- Project trust matters.
  If the repo is not trusted by the runtime, project-scoped Codex config may not load.
- Do not put the research corpus in `AGENTS.md`.
  Keep this file short and stable. Put workflows in skills and source notes under `.agents/skills/.../references/`.
- Do not assume local behavior matches hosted behavior.
  This project ships on Vercel, and third-party services can behave differently in serverless environments.
- Do not assume YouTube ingestion is reliable in production.
  Hosted YouTube transcript retrieval can fail with `RequestBlocked`; fallback is manual transcript paste.
- Launch location matters.
  Start from repo root when possible so discovery of `AGENTS.md`, `.codex/`, and `.agents/skills/` is predictable.
- Do not assume every agent should edit files.
  In this project, role agents are analysis-first by default. Editing authority should be explicit per task.
- Do not assume `rob` is the default executor.
  The repo default agent is `orchestrator`, which owns direct execution unless a specialist is explicitly better suited.
- Do not route implementation work to `rob`.
  `rob` is a read-only creative co-founder voice, not an execution agent.
- Do not treat Glenna as a live supervisor.
  Glenna is a manual, post-hoc reviewer. She evaluates completed interactions and logs recommendations, but does not auto-route or auto-implement fixes.

## Project-Specific Constraints

- Product stage is MVP stabilization, not greenfield exploration.
- Backend changes must be evaluated for both local and deployed behavior.
- Security-sensitive endpoints must be reviewed for SSRF and error leakage.
- Research and product language must distinguish evidence, hypothesis, and speculation.
- Favor progressive disclosure in skills and docs instead of large always-loaded context dumps.
- Agent quality improvement should be durable.
  Glenna reviews should append to `docs/codex/agent-review-log.md` so recommendations remain inspectable after the session.
