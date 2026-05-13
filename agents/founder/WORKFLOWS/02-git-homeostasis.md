# Git Homeostasis

## Trigger

Any request to clean up branch state, archive stale branches, reset `dev`, converge to `main + dev`, or restore repo homeostasis after branch drift.

## Goal

Converge the repo to the intended branch shape without silent data loss: exactly `main` and `dev`, both clean, both at the intended tip, with any high-signal local work either salvaged, archived, or explicitly discarded.

## Inputs To Inspect

- working tree state
- local branches and tracking state
- remote refs and prune status
- open PRs tied to non-`main` / non-`dev` branches
- ancestry of each non-`main` / non-`dev` branch relative to `main`
- unique commits on each candidate branch
- actual file-level content of suspicious commits
- remote list, including local-file remotes that may preserve history

## Risk Classification

- `safe`: read-only survey and classification
- `confirm`: branch rename, absorbed-branch delete, salvage onto `dev`, fast-forward `dev` to `main`, publish `dev` after verified salvage
- `hard-confirm`: deleting a branch with unique work, deleting remote refs, hard reset, force-push, or any action that can discard history or alter shared remote history destructively

## Recommended Route

Use a fixed three-phase route:

1. `SURVEY`
   Read repo state before proposing any action.
2. `CLASSIFY`
   For each branch outside `{main, dev}`, classify it as:
   - `absorbed`: tip already reachable from `main`
   - `salvage`: unique commits with real value
   - `junk`: unique commits with no retained value after inspection
3. `EXECUTE`
   Apply the deterministic sequence:
   - bring `dev` to `main`
   - salvage valuable work onto `dev`
   - publish `dev` through `agents/founder/WORKFLOWS/01-git-integration.md` using `scripts/agent-push.py`
   - archive or rename remaining branches
   - delete absorbed or explicitly-discarded branches
   - prune orphan remote refs
   - fast-forward re-converge if upstream automation advanced `main`

## Required Confirmation

- no destructive git action without an explicit pause
- surface branch fate when classification is ambiguous
- preserve unique work before deleting it
- never treat "looks unimportant" as authorization to destroy history

## Verification

- `SURVEY`
  - working tree is clean before any execution path
  - branch and remote inventory is current after fetch/prune
- `CLASSIFY`
  - ancestry claims verified, not inferred from names or commit messages
  - unique commits inspected by content when salvage value is uncertain
- `EXECUTE`
  - `dev` matches `main` before salvage starts
  - salvage result matches the intended manifest exactly
  - any publication step follows `01-git-integration.md` instead of raw `git push`
  - each rename/delete leaves the expected branch list
  - remote state matches local after publication/prune
  - final invariant is exactly `main` + `dev` at the intended tips

## Stop Rules

- stop if the working tree is dirty
- stop if the repo uses a different intended branch model than `main + dev`
- stop if a branch has unique commits whose value is still ambiguous
- stop before any destructive action if no preservation path exists
- stop if the publication path would require force-push without explicit founder approval

## Artifact Destination

- shared workflow truth: this file
- migration status: `agents/MIGRATION.md`
- raw sediment or repeated branch-friction observations: `agents/LEARNINGS.md`
