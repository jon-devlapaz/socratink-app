# socratink — Codex Workflows

This document defines repeatable workflows for specific agentic tasks.

---

## 1. Hot-Fix Workflow
*For narrow, high-priority regressions.*

Use when a user-facing behavior is broken or misaligned with an intended rule, and the fix is localized.

### Required Brief
Before starting, capture these fields:
- **Surface**: Where the issue appears.
- **Broken behavior**: What currently happens.
- **Intended behavior**: What should happen instead.
- **Repro**: Smallest set of steps to reproduce.
- **Impact**: Why it matters now.
- **Constraints**: Rules that must still hold (e.g., graph truth).
- **Non-goals**: What this fix must NOT expand into.

### Roles in a Hot-Fix
- **elliot**: Frames the rule and scope boundary.
- **sherlock**: Triages the cause and identifies the smallest patch surface.
- **orchestrator**: Executes the minimal fix.
- **thurman**: Verifies the fix on both local and hosted (if possible).

### Trigger Template
`Hot-fix: <surface>. Broken: <current behavior>. Intended: <restored behavior>. Repro: <short steps>. Impact: <why now>. Constraints: <rules>. Non-goals: <what this is not>.`

### Close-Out Template
```text
Hot-fix close-out
Root cause:
Rule restored:
Files changed:
Verification performed:
Residual risk:
Status: fixed locally / fixed in hosted path / not yet hosted-verified
```

---

## 2. Decision Log Workflow
*For resolving specialist disagreements.*

When specialists disagree, the orchestrator must produce a short decision record:
- **Disputed Point**: What is the conflict?
- **Evidence**: What does each side say?
- **Chosen Path**: Which direction are we going?
- **Owner**: Who is responsible for the result?
- **Doc Updates**: What documentation or state files were updated?

---

## 3. Glenna Review Workflow
*For post-hoc quality review.*

Invoke `glenna` after a complex task or when the workflow felt inefficient. Glenna reviews should:
- Evaluate role adherence and handoff quality.
- Identify repo constraint violations.
- Append a durable entry to `docs/codex/agent-review-log.md`.
