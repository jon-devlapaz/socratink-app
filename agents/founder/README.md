# Founder Agent Canon

This folder is the founder-facing part of the shared agent canon. It is where the repo keeps durable workflow rules that should outlive any one tool, model, or local machine setup.

It is not meant to replace the detailed workflow card or the root agent instructions. Treat this file as the map: it tells you what exists, where to look, and what is enforced today.

## What Each File Does

- `WORKFLOWS/01-git-integration.md` is the source for the founder git workflow. It explains when publication should go to `origin/dev`, `origin/feat/*`, or `no-mistakes/dev`, and when a push needs stronger confirmation.
- `WORKFLOWS/02-git-homeostasis.md` is the source for restoring branch homeostasis. It explains how to survey branch state, classify stale branches, salvage valuable work, and converge back to the intended `main + dev` shape without silent data loss.
- `WORKFLOWS/03-prototyping.md` is the source for founder prototype workflow. It explains when to use a logic/state harness versus a UI/copy variant sweep, how to keep prototypes throwaway, and where to capture the verdict when the question is answered.
- `WORKFLOWS/04-deploy-verification.md` is the source for deploy verification. It explains how to wait for the intended production deployment, run the smoke against the live site, and report deploy status separately from smoke status.
- `CODE-REVIEW-GRAPH-FAQ.md` is the founder-facing FAQ for CRG. It explains, in plain language, when the graph is worth using and how to think about it as structural code memory.
- `../LEARNINGS.md` is the non-binding ledger for recurring founder/agent workflow observations. Read it when founder workflow friction, publication safety, verification discipline, artifact placement, or workflow promotion is part of the task.
- `trusted-remotes.json` is the tracked allowlist for remotes that the push wrapper may trust. It prevents agents from treating a remote name like `origin` as safe without checking the URL.
- `README.md` is this overview. It summarizes the folder for humans; it should not redefine policy.

## Canonical, Runtime, And Tool-Specific

- Canonical: files under `agents/`, especially workflow cards and tracked config. These are the shared rules.
- Runtime: `.agents/runtime/`, which is ignored by git. This holds push authorizations, decision logs, and optional local trusted-remote extensions.
- Entrypoints: `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`. They should point into the shared canon instead of becoming separate rulebooks.
- Tool-specific runtime or wrappers: `.claude/`, `.codex/`, `.gemini/`, and similar local surfaces.

## Enforced Vs. Guidance

V1 deterministically enforces push publication only:

- `scripts/agent-push.py` classifies the publication, prints the recommended route, binds the chosen route to an ack token, and writes runtime evidence.
- `scripts/git-hooks/pre-push` blocks raw pushes unless they match an authorization created by the wrapper.
- `.agents/runtime/push-decisions.jsonl` records the publication decision after an acknowledged push attempt.

Other actions are still guidance, not hard enforcement: commit shaping, branch deletion, PR opening, and review sequencing still depend on the workflow card and human judgment.

## Workflow Learning Loop

Founder workflow learnings compound through `agents/LEARNINGS.md`:

- `observed` entries capture reusable friction from real work without creating policy.
- recurring or high-risk entries become `candidate` and name the canonical file that should absorb the rule.
- `promoted` entries link to the reviewed canon change that now owns the rule.

Use this loop for workflow quality problems, not product architecture.

- Read the ledger when the task involves founder workflow friction, publication safety, verification discipline, artifact placement, or workflow promotion.
- Append only reusable evidence from real work.
- Promote the rule into the workflow card or other canonical file once the recurrence threshold is met.

If the learning belongs in a founder workflow card, promote it there rather than expanding this README.

## What Still Lives Outside This Folder

- Root entrypoints: `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`.
- Bootstrap and agent quality docs: `agents/ONBOARDING.md` and `agents/QUALITY.md`.
- Executable enforcement: `scripts/agent-push.py`, `scripts/git-hooks/pre-push`, and `scripts/doctor.sh`.
- Founder-facing git command map and local readiness checks: `scripts/git-founder-help.sh`.
- Runtime state: `.agents/runtime/`.

## What V1 Solves

V1 gives the founder a shared canon, a concrete git workflow card, trusted remote config, and deterministic protection around push publication. The important shift is that publication is now a recorded decision: agents can recommend one route, the founder can choose another, and the wrapper logs the difference.

## What V1 Does Not Solve Yet

V1 does not automate every git decision, replace remote branch protection, or make local hooks sufficient for all safety cases. It also does not fully model PR lifecycle, force-push policy, branch cleanup, or cross-tool prompt migration. Those remain future workflow work unless the detailed workflow card says otherwise.
