# Agent Learnings Ledger

This is the non-binding learning ledger for founder and agent workflow usage.

It captures high-signal observations from real work so repeated workflow friction becomes easier to notice. It is not policy, not a prompt pack, and not a second canon. Future agents may use it as evidence, but binding workflow truth still lives in `AGENTS.md`, `agents/README.md`, workflow cards, `agents/ONBOARDING.md`, `agents/QUALITY.md`, and other registered canonical files.

## Read Rule

Read this file only when the task touches agent/founder workflow design, bootstrap instructions, publication safety, artifact placement, verification discipline, workflow-card creation, migration into `agents/`, or when the current task repeats known workflow friction.

For context efficiency, read this contract and the Pattern Index first. Open detailed entries only for matching pattern keys or statuses.

## Write Rule

Append or update an entry only after real usage exposes reusable workflow evidence. Good learning evidence includes:

- workflow friction that slowed or confused a task
- task-alignment misses between the founder request and agent behavior
- verification misses or unclear proof standards
- publication, branch, or artifact-placement safety issues
- repeated uncertainty about which canon surface owns a rule
- founder-agent coordination patterns worth formalizing

Do not log ordinary task details, product doctrine, one-off preferences, speculative ideas, or anything that belongs directly in a workflow card today.

## Status Vocabulary

- `observed`: seen in real usage, not yet recurring enough to change canon
- `candidate`: recurring or high-risk enough that promotion should be considered
- `promoted`: incorporated into a canonical workflow, adapter, or binding doc
- `rejected`: reviewed and intentionally not promoted
- `superseded`: replaced by a newer learning or canonical rule

## Promotion Rule

Promote by human-reviewable doc edit, never by automatic canon mutation.

Mark an entry `candidate` and recommend a promotion target when either condition is true:

- the same pattern appears in 3 real tasks
- the same pattern appears in 2 real tasks and affects publication safety, verification integrity, bootstrap correctness, or canon/source-of-truth boundaries

Promotion targets must be explicit: a workflow card under `agents/founder/WORKFLOWS/`, `agents/README.md`, `agents/founder/README.md`, `agents/ONBOARDING.md`, `agents/QUALITY.md`, or another registered canonical file.

After promotion, update the ledger entry to `promoted`, link the destination, and keep the evidence count. If the decision is not to promote, mark it `rejected` with the reason.

## Pattern Index

Keep this table short. It exists so future agents can spot recurrence without loading every entry.

| Pattern key | Status | Count | Last seen | Recommended promotion target | Entry |
| --- | --- | ---: | --- | --- | --- |
| `subagent-delegation-too-soft` | `observed` | 1 | 2026-05-13 | `none yet` | [LYYYY-2026-05-13-subagent-delegation-too-soft](#lyyyy-2026-05-13-subagent-delegation-too-soft) |
| `explore-compress-merge` | `promoted` | 1 | 2026-05-15 | `agents/founder/WORKFLOWS/05-explore-compress.md` | [L0002-2026-05-15-explore-compress-merge](#l0002-2026-05-15-explore-compress-merge) |
| `verification-gates-not-self-contained` | `promoted` | 2 | 2026-05-18 | `agents/QUALITY.md` | [L0003-2026-05-17-verification-gates-not-self-contained](#l0003-2026-05-17-verification-gates-not-self-contained) |
| `no-mistakes-uncommitted-config-stale` | `observed` | 1 | 2026-05-22 | `none yet` | [LYYYY-2026-05-22-no-mistakes-uncommitted-config-stale](#lyyyy-2026-05-22-no-mistakes-uncommitted-config-stale) |
| `no-mistakes-release-ledger` | `promoted` | 1 | 2026-05-25 | `agents/founder/WORKFLOWS/01-git-integration.md`, `agents/founder/WORKFLOWS/04-deploy-verification.md` | [L0004-2026-05-25-no-mistakes-release-ledger](#l0004-2026-05-25-no-mistakes-release-ledger) |


## Entries

Use [agents/_templates/learning-entry.md](./_templates/learning-entry.md) for new entries.

# LYYYY-2026-05-13-subagent-delegation-too-soft

- Status: `observed`
- Pattern key: `subagent-delegation-too-soft`
- First seen: `2026-05-13`
- Last seen: `2026-05-13`
- Evidence count: `1`
- Affected workflow surface: `coordination`
- Recommended promotion target: `none yet`
- Related canonical files: `agents/README.md`, `agents/QUALITY.md`

## Observation

Small, judgment-heavy repo-doc cleanups can stall when delegated to a subagent with too much latitude and no hard edit contract. The failure mode is not bad reasoning; it is an inspect-only loop where the subagent identifies the right issue but never crosses into editing.

## Evidence

- `2026-05-13`: a `GPT-5.5` high-reasoning worker was asked to perform a lean CRG docs cleanup. It returned `NO_CHANGES` after correctly concluding that the old CRG support docs overstated visualization auto-sync and needed simplification. The cleanup then had to be executed locally with a narrower edit contract.

## Promotion Notes

Still non-binding because this is one observed failure mode, not yet a repeated pattern. If it recurs, promote a rule into the canonical workflow docs: keep small canon-boundary cleanups local by default, or give subagents an explicit patch contract with exact files and exact claims to change.

# L0002-2026-05-15-explore-compress-merge

- Status: `promoted`
- Pattern key: `explore-compress-merge`
- First seen: `2026-05-15`
- Last seen: `2026-05-15`
- Evidence count: `1`
- Affected workflow surface: `founder session design`
- Recommended promotion target: `agents/founder/WORKFLOWS/05-explore-compress.md` (already written)
- Related canonical files: `agents/founder/WORKFLOWS/03-prototyping.md`

## Observation

When a grilling or design session hits a question that can only be answered by prototyping, diverging into free exploration and then using a rewind+summarize to compress the result back into the primary thread preserves context quality on both ends: the exploration is unconstrained, and the primary session isn't drowned in churn.

The key mechanism is treating the conversation's rewind+summarize as a compression primitive — not a rollback. The artifact is retained; only the iteration noise is dropped.

## Evidence

- `2026-05-15`: founder ran `/grill-with-docs` on a UI design question, hit an unanswerable fork, diverged into `/prototype`, iterated freely, then used `/rewind` + "summarize" to compress learnings back into the grilling session. Described as "smooth" with explicit intent to repeat.

## Promotion Notes

Promoted immediately into `agents/founder/WORKFLOWS/05-explore-compress.md` on first sighting because the pattern was deliberate, low-risk, and the founder explicitly wanted it captured as a reusable workflow card. Revisit the card if a second sighting shows the workflow needs tighter stop rules.

# L0003-2026-05-17-verification-gates-not-self-contained

- Status: `promoted`
- Pattern key: `verification-gates-not-self-contained`
- First seen: `2026-05-17`
- Last seen: `2026-05-18`
- Evidence count: `2`
- Affected workflow surface: `verification discipline`
- Recommended promotion target: `agents/QUALITY.md`
- Related canonical files: `scripts/qa-smoke.sh`, `scripts/check-coverage.sh`, `agents/QUALITY.md`

## Observation

A command documented as a local verification gate must carry its own local-only setup defaults. If a passing gate depends on environment set by another wrapper, agents can report false confidence or waste time debugging auth symptoms that are really harness setup drift.

## Evidence

- `2026-05-17`: `./scripts/check-coverage.sh` passed because it set `SOCRATINK_E2E_LOCAL_GUEST=1`, but `bash scripts/qa-smoke.sh local` initially failed four guest-bootstrap tests by redirecting to `/login?auth_error=authentication_failed`. The fix was to make `qa-smoke.sh` enable the local E2E guest path for loopback targets only.
- `2026-05-18`: promoting `scripts/check-coverage.sh` into GitHub Actions exposed another hidden harness assumption: the browser coverage path needed a loopback app plus a CI-safe `/auth/e2e/guest` bootstrap contract. The CI workflow now provisions Python, Node coverage tooling, Chromium, the local app, and an explicit compare branch before running the gate.

## Promotion Notes

Promoted into `agents/QUALITY.md` after the second sighting affected verification integrity. Keep subagent edit-contract guidance unpromoted until it recurs; that pattern remains a delegation prompt habit, not binding quality doctrine.

# LYYYY-2026-05-22-no-mistakes-uncommitted-config-stale

- Status: `observed`
- Pattern key: `no-mistakes-uncommitted-config-stale`
- First seen: `2026-05-22`
- Last seen: `2026-05-22`
- Evidence count: `1`
- Affected workflow surface: `agentic configuration`
- Recommended promotion target: `none yet`
- Related canonical files: `AGENTS.md`

## Observation

The `no-mistakes` daemon executes its validation and review pipeline within an isolated, clean Git worktree checked out from the pushed commit ref. Because of this, changes to repository-level configuration files (such as `.no-mistakes.yaml`) must be committed to Git to take effect. If changes remain only in the working directory (uncommitted), the daemon will fall back to the stale committed version of the configuration, causing unexpected behaviors or using the wrong agent.

## Evidence

- `2026-05-22`: Changing `.no-mistakes.yaml` to `agent: acp:pool` in the working directory did not stop the daemon from running the review step using the old `codex` agent, because the daemon was running in an isolated worktree based on the older commit that still had `agent: codex`. Committing the change and pushing allowed the daemon to correctly parse the new config.

## Promotion Notes

Keep as observed until it recurs or affects safety. If promoted, document this behavior clearly in `AGENTS.md` under the common development commands section to remind developers to commit `.no-mistakes.yaml` changes before expecting the daemon to reflect them.

# L0004-2026-05-25-no-mistakes-release-ledger

- Status: `promoted`
- Pattern key: `no-mistakes-release-ledger`
- First seen: `2026-05-25`
- Last seen: `2026-05-25`
- Evidence count: `1`
- Affected workflow surface: `publication`
- Recommended promotion target: `agents/founder/WORKFLOWS/01-git-integration.md`, `agents/founder/WORKFLOWS/04-deploy-verification.md`
- Related canonical files: `scripts/agent-push.py`, `scripts/no-mistakes-finish-dev.sh`, `scripts/verify-deploy.sh`

## Observation

A final production-bound no-mistakes run creates several truth surfaces at once: local pre-gate commits, daemon-published `origin/dev` commits, the no-mistakes run id, PR checks, Vercel preview, merge commit, main preflight, production deployment, and local cleanup state. If the agent does not maintain a compact release ledger, the run stays correct but accumulates avoidable entropy: repeated log polling, unclear SHA names, and delayed cleanup of temporary worktrees.

The clean pattern is to track exactly one ledger through the run: no-mistakes run id, gate head, PR URL, `origin/dev` head, merge SHA, production verifier result, and final local branch/worktree status. Treat gate success, PR merge, and production smoke as separate milestones. Cleanup belongs after production verification, not after local or preview success.

## Evidence

- `2026-05-25`: PR #257 required a no-mistakes rerun after Vercel rejected an exact `.python-version` patch pin and the frontend cache-pin gate caught a stale parent JS import. The daemon then added a mobile drawer smoke hardening commit after evidence review. The final release succeeded only after tracking no-mistakes run `01KSG9ME2W11C7W5Z0S49595QG`, PR #257, `origin/dev` head `af851b1`, merge commit `1b5f6b6`, main preflight success, and `scripts/verify-deploy.sh 1b5f6b603d9555b4d527cbd364299c5ecc907da2` production smoke success (`33 passed, 2 skipped`).
- `2026-05-25`: GitHub Pages failed separately because Jekyll tried to render `agents/superpowers/**` Liquid-looking markdown. That signal was real and inspected, but it was not the Vercel production app path. Future release summaries should label such red signals explicitly instead of allowing them to blur the deploy verdict.

## Promotion Notes

Promoted immediately on founder request after a production-bound release because the pattern affects publication safety and verification integrity. The ledger requirement belongs in `agents/founder/WORKFLOWS/01-git-integration.md`; the deploy-signal separation belongs in `agents/founder/WORKFLOWS/04-deploy-verification.md`.
