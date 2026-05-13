---
name: git-order
description: Use when a repo has chaotic branch state and the goal is to restore branch homeostasis safely back to the intended `main + dev` shape.
status: draft
tested-by: 2026-05-01 worked-example (live, observed end-to-end). Subagent baseline pending.
design-source: docs/diagrams/git-order.excalidraw
---

# git-order

Canonical shared workflow truth for this process lives in `agents/founder/WORKFLOWS/02-git-homeostasis.md`.

Use this Claude skill as a thin packaging wrapper:

1. Read `agents/founder/WORKFLOWS/02-git-homeostasis.md`.
2. Follow its survey -> classify -> execute flow.
3. If execution requires publication, route that step through `agents/founder/WORKFLOWS/01-git-integration.md` and `scripts/agent-push.py`.

The Excalidraw at `docs/diagrams/git-order.excalidraw` is supporting visual material, not the canonical doctrine surface.
