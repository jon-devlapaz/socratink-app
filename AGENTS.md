# AGENTS.md

This file is the lightweight local operating guide for this repository.

## Core instruction source
- `AGENTS.md` is the primary entry file for agent-facing context and lint checks.
- If this file is missing, use `README.md` and `.github/workflows/`.

## Scope
- Keep changes scoped to the explicit request.
- Prefer small, reversible edits over broad refactors.
- Record blockers and follow-ups in the task summary.

## Read this before edits
- Current architecture/truth lives in `README.md`, `docs/project/doc-map.md`, and `docs/product/north-star.md`.
- Agent workflow and verification doctrine lives in `docs/project/doc-map.md`.
- Runtime and deployment notes are in `.github/workflows/` and related scripts.
- Product doctrine lives in `docs/product/north-star.md` (canonical), with `PRODUCT.md`, `DESIGN.md`, and `UBIQUITOUS_LANGUAGE.md` as derived contracts.
## Safe change sequence
- Confirm branch and dirty state before touching files.
- For normal code work, start from the clean home checkout with `agent-work start <slug>` and do edits only in the printed sibling worktree.
- Prefer docs/config edits before runtime commands for repo-level hygiene tasks.
- Run the documented local checks before opening a PR.

## Code-work entry point
- For Socratink app feature-slice work, `$socratink-agent-flow` is mandatory by
  default. If a task asks to implement, review, publish, merge, clean up, prove
  golden, or orient a feature slice, load and follow that skill first; do not
  start direct implementation from this pane unless the user explicitly says
  `no agent flow`.
- Default to one task, one agent, one worktree, one branch.
- Home checkout stays on clean `main` for orientation, publish, and cleanup.
- Agent prompt line: `Work only in <worktree-path>. Before editing, run agent-work guard .`
- For Herdr delegation, a short ask like `Use agent-work for nav icons` is enough; clarify only if scope is ambiguous, then run `agent-work launch "<task>"` from the home checkout.
- Before publishing feature work, rename or recreate the review branch as `feat/<slug>`. Cleanup commits on `main` publish to `origin/main`.
- After merge, delete the merged `feat/<slug>` branch residue and remove the clean worktree with the repo cleanup helper.

## Git-golden state
Call the repo `git-golden` only when all of these are true:
- `main` is checked out and matches `origin/main`.
- The working tree is clean.
- There are no stashes.
- There are no extra linked worktrees; the primary checkout still appears in `git worktree list`.
- There are no local feature or agent branches left over.
- There are no remote feature or agent branches left over.
- There are no open PRs for finished work.

Proof commands:

```bash
git status --short --branch
git worktree list --porcelain
git branch --format='%(refname:short)'
git branch -r --format='%(refname:short)'
git stash list
gh pr list --state open
```

## Commands
- Setup: `bash scripts/bootstrap-python.sh`
- Local checks: `bash scripts/doctor.sh`
- Logic tests: `.venv/bin/pytest -q`

## Practical constraints
- Avoid editing generated artifacts.
- Keep dependency/security edits deliberate and version-aware.
- Ask before introducing new cross-platform behavior outside this repo workflow.

## Communication defaults
- Keep responses concise and action-oriented.
- Cite exact files and commands in changes and handoffs.

## Learned User Preferences
- During UI polish, show the live browser preview so the user can see what is being made.
- Desk due/ready UX should stay board-centric (Linear-style Ready filter, due marks, selection strip), not a header inventory list of due nodes.
- Give blunt honesty on whether desk UI captures metacognitive learning; do not praise-pad weak UX.
- For Socratink implementation slices, follow `/socratink-agent-flow` unless the user explicitly opts out.
- Prefer landing UI as small sequential product-story slices with feedback between wires over large UI overhauls.
- Spaced-return / due copy should use learner reconstruction language (e.g. Ready to revisit, Reconstruct again), not app-maintenance phrasing like Due for maintenance.

## Learned Workspace Facts
- Due/Ready desk state must come from real training evidence (`spaced_attempt` / spaced re-drill eligibility), never decorative mastery or fake progress chrome.
- Iso board due marks: avoid CSS/SVG transform footguns on `.tile-group` when styling due tiles.
- When editing CSS under `public/`, bump `?v=` cache-bust pins through the parent import chain (`layout.css` → `styles.css` → `index.css` → `index.html`).
- Treat localStorage and file-backed sessions as non-durable until proven; label readiness claims as local, hosted, or production.
