---
name: git-order
description: Use when a repo has chaotic branch state — multiple stale archives, divergent dev/main, orphan remote refs, lingering test/* branches, uncertain salvage value — and the user wants to converge to exactly main + dev at the same clean tip. Triggers include "clean up branches", "archive stale branches", "fresh dev off main", "reset dev", "delete all branches except main and dev", or any branch list with 3+ active local branches when only main + dev should remain.
status: draft
tested-by: 2026-05-01 worked-example (live, observed end-to-end). Subagent baseline pending.
design-source: docs/diagrams/git-order.excalidraw
---

# git-order

## Singular goal

> From any branch state ⇒ exactly `main` and `dev`, both clean, both at the same tip, with high-signal local work salvaged onto `dev`.

Two-branch invariant. Anything else is intermediate state and must end up either merged, archived, or deleted.

## When NOT to use

- Mid-feature work where intermediate branches are load-bearing (let them live)
- A repo that uses a different branch model (release/*, feature/*, gitflow) — this skill assumes the user's `main = prod, dev = fresh from main` convention
- When the user wants to keep an archive branch for reference — surface the option, don't auto-delete

## The three phases

```
SURVEY  ▸  CLASSIFY  ▸  EXECUTE
```

Run them in order. Don't execute before classify; don't classify before survey.

## Phase 1 — SURVEY (read-only)

Run these and read the output before proposing anything:

```bash
git status --short                                           # working tree must be clean
git branch -vv                                               # local branches + tracking
git branch -r                                                # remote refs
git fetch --all --prune                                      # before reasoning about ahead/behind
gh pr list --state open --head <branch>                      # for each non-main local branch
git remote -v                                                # which remotes exist; flag local-file remotes
```

For each non-main, non-dev local branch B, also capture:

```bash
git merge-base --is-ancestor "$(git rev-parse B)" main && echo "absorbed" || echo "divergent"
git log --oneline main..B                                    # unique commits
git show --stat <suspicious-sha>                             # when commit message looks misleading
```

**STOP if working tree is dirty.** Do not proceed.

## Phase 2 — CLASSIFY (decision tree)

For each branch B ≠ {main, dev}:

| Question | Answer | Bucket |
|---|---|---|
| `tip(B)` reachable from main? | yes | **ABSORBED** → safe to delete with `git branch -d` |
| `tip(B)` reachable from main? | no | go to next question |
| Do `main..B` commits have value? (read content, not just count) | yes | **SALVAGE** → carry onto fresh dev |
| Do `main..B` commits have value? | no (junk / aborted / superseded) | **JUNK** → delete with `-D` after preserving a backup ref |

**Reading content matters.** A commit message can lie. Always inspect actual file lists for commits not on main before classifying as JUNK.

Ambiguous? **Pause** and surface to the user. Do not auto-decide.

## Phase 3 — EXECUTE (deterministic sequence)

Each step has a verification. Don't skip verification.

```
1. dev := main           git checkout dev && git merge --ff-only main
                         (or fresh-branch if dev unsalvageable)
                         verify: git log --oneline main..dev shows nothing

2. SALVAGE onto dev      for each SALVAGE-classified branch:
                           git checkout dev-branch -- <files>   (file-copy)
                           OR git cherry-pick <sha>             (commit-copy)
                         commit each salvage as its own atomic commit
                         verify: git diff --stat main..dev matches the salvage manifest exactly

3. push origin dev       git push origin dev          (FF only — never --force)
                         verify: remote ref advances to local tip

4. archive-rename        for each remaining branch:
                           git branch -m <name> dev-archive-YYYY-MM-DD[-tag]
                         add -tag suffix if base name collides
                         verify: git for-each-ref shows the new name

5. local delete          git branch -d <archive>      (absorbed; should succeed)
                         git branch -D <archive>      (junk; force ok IF backup ref exists)
                         verify: git branch -vv shows only main + dev

6. orphan remote prune   git push origin --delete <ref>     (for each origin orphan)
                         verify: git branch -r shows only origin/main + origin/dev

7. ff-converge           git checkout dev && git merge --ff-only main
                         (catches the merge commit if origin auto-PR'd dev → main)
                         git push origin dev
                         verify: tip(main) == tip(dev), both local and origin
```

## Three invariants (callouts)

- **⏸ PAUSE before destructive op.** Branch delete (`-D`), force-push, hard-reset, history rewrite, remote ref delete. Surface 2–3 numbered options and wait. *Never* "small."
- **✓ VERIFY each step.** After every salvage commit, every push, every delete: run the verify command. A diffstat that doesn't match the salvage manifest means stop and re-check classification.
- **⊕ PRESERVE before delete.** A branch with unique commits classified as JUNK must have its tip reachable from at least one remote ref (e.g., a no-mistakes file remote) OR the user must explicitly accept loss. Otherwise `git branch -D` is a quiet history loss.

## Quick reference — the 5-line ending

When done, this should be the entire branch listing:

```
local:   * dev   <SHA> [origin/dev]
           main  <SHA> [origin/main]
origin:    main, dev only
```

`tip(main) == tip(dev)`, working tree clean, `git diff main..dev` empty.

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Trust commit message over content | Branch labeled "Add starting-map support" actually contains aborted-pipeline JSON dumps | Always `git show --name-only <sha>` before classifying |
| Cherry-pick onto stale base | Conflicts on README/config that main rewrote | Do `dev := main` first; cherry-pick onto current dev, not the source branch's base |
| Delete remote orphan first | Reflog still has tip locally; remote ref preserves nothing | Verify content reachable from main BEFORE remote `--delete` |
| Force-push to "fix" dev divergence | Overwrites teammates' work, fragments history | Check `merge-base --is-ancestor` first; if FF possible, regular push works |
| Auto-merge surprise | After pushing dev, repo plumbing PRs dev→main; local dev is now behind main | Step 7 (ff-converge) catches this; don't skip |

## Red flags — STOP and re-classify

- "I'll just delete it, the commits looked unimportant" → read the diff first
- "I can force-push dev, it's mine" → check ancestry; FF push works in 95% of cases
- "The merge-base is recent, so it can't be that far behind" → main can move 100+ commits in a week; count
- "The commit message describes the change" → it can be misleading; verify by file list
- Branch name conflict on rename → add a `-tag` suffix; never overwrite an existing archive name

## Reference

The decision tree and sequence are visualized at `docs/diagrams/git-order.excalidraw`. Open in https://excalidraw.com (drag the file in). The diagram is the canonical "why" for this skill.

## Draft notice

This skill is **draft**. Tested via a single observed live execution (2026-05-01: 5-branch chaos → main+dev at 56878c8). Subagent pressure-test pending — until then, treat this as a recipe, not a contract.
