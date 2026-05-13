# Agent Learnings Ledger

This is the non-binding learning ledger for founder and agent workflow usage.

It captures high-signal observations from real work so repeated workflow friction becomes easier to notice. It is not policy, not a prompt pack, and not a second canon. Future agents may use it as evidence, but binding workflow truth still lives in `agents/README.md`, workflow cards, `agents/MIGRATION.md`, `agents/ONBOARDING.md`, `agents/QUALITY.md`, and other registered canonical files.

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
- `promoted`: incorporated into a canonical workflow, adapter, migration ledger, or binding doc
- `rejected`: reviewed and intentionally not promoted
- `superseded`: replaced by a newer learning or canonical rule

## Promotion Rule

Promote by human-reviewable doc edit, never by automatic canon mutation.

Mark an entry `candidate` and recommend a promotion target when either condition is true:

- the same pattern appears in 3 real tasks
- the same pattern appears in 2 real tasks and affects publication safety, verification integrity, bootstrap correctness, or canon/source-of-truth boundaries

Promotion targets must be explicit: a workflow card under `agents/founder/WORKFLOWS/`, `agents/README.md`, `agents/founder/README.md`, `agents/MIGRATION.md`, `agents/ONBOARDING.md`, `agents/QUALITY.md`, or another registered canonical file.

After promotion, update the ledger entry to `promoted`, link the destination, and keep the evidence count. If the decision is not to promote, mark it `rejected` with the reason.

## Pattern Index

Keep this table short. It exists so future agents can spot recurrence without loading every entry.

| Pattern key | Status | Count | Last seen | Recommended promotion target | Entry |
| --- | --- | ---: | --- | --- | --- |
| `subagent-delegation-too-soft` | `observed` | 1 | 2026-05-13 | `none yet` | [LYYYY-2026-05-13-subagent-delegation-too-soft](#lyyyy-2026-05-13-subagent-delegation-too-soft) |

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

- `2026-05-13`: a `GPT-5.5` high-reasoning worker was asked to perform a lean CRG docs cleanup. It returned `NO_CHANGES` after correctly concluding that the docs overstated visualization auto-sync and that `docs/project/code-review-graph-sop.md` and `docs/project/crg-hooks-handoff.md` should be simplified. The cleanup then had to be executed locally with a narrower edit contract.

## Promotion Notes

Still non-binding because this is one observed failure mode, not yet a repeated pattern. If it recurs, promote a rule into the canonical workflow docs: keep small canon-boundary cleanups local by default, or give subagents an explicit patch contract with exact files and exact claims to change.
