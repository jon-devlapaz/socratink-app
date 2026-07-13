# Agent Learnings Ledger

This file contains unresolved, non-binding evidence about founder and agent
workflow. Binding workflow lives in `AGENTS.md`, `agents/README.md`, and
`agents/QUALITY.md`.

Read it only for workflow design, bootstrap, publication safety, artifact
placement, verification discipline, or recurring workflow friction. Add an
entry only after real usage exposes a reusable pattern. Promote through a
reviewed edit to an active canonical file; once resolved, remove the entry and
rely on git history.

## Active patterns

| Pattern key | Status | Count | Last seen | Recommended target | Entry |
| --- | --- | ---: | --- | --- | --- |
| `subagent-delegation-too-soft` | `observed` | 1 | 2026-05-13 | `none yet` | [L0001](#l0001-subagent-delegation-too-soft) |

## L0001: Subagent delegation too soft

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

## Next decision

Still non-binding because this is one observed failure mode, not yet a repeated pattern. If it recurs, promote a rule into the canonical workflow docs: keep small canon-boundary cleanups local by default, or give subagents an explicit patch contract with exact files and exact claims to change.
