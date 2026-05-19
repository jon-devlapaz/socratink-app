# Git Integration

## Trigger

Any request to commit, publish a branch, open a PR, or "push/ship" code.

## Goal

Route publication safely while keeping the founder in the loop for meaningful persistent-state changes.

## Inputs To Inspect

- current branch
- working tree state
- destination remote/refspec
- touched files
- unpublished publication diff against the relevant remote/base
- trusted remote patterns in `agents/founder/trusted-remotes.json`
- whether the path is `dev`, `feat/*`, `main`, or `no-mistakes`

## Risk Classification

- `safe`: read-only local git inspection
- `confirm`: commit, branch delete, PR open, push `origin/dev`, push `origin/feat/*`, push `no-mistakes/dev`
- `hard-confirm`: push `origin/main`, force-push, push/merge to publish-protected targets, prod-coupled publication

V1 note: only push publication is deterministically enforced in code. Commit shaping, branch deletion, and PR opening remain workflow-card policy.

## Recommended Route

- use `origin/dev` for ordinary narrow `dev` publication
- use `origin/feat/*` for feature-branch publication intended for PR flow
- use `no-mistakes/dev` for larger, higher-blast-radius, or higher-risk publication

## Helper Commands

```text
scripts/git-wip-explain.sh              # full local/session orientation
scripts/git-wip-explain.sh --short      # compact terminal-start summary
python3 scripts/agent-push.py --target no-mistakes/dev
no-mistakes attach
scripts/no-mistakes-finish-dev.sh       # after no-mistakes finishes
scripts/git-worktree-cleanup.sh         # list stale worktrees
scripts/git-worktree-cleanup.sh --remove-clean --apply
```

## Required Confirmation

- no silent publication
- use `scripts/agent-push.py`
- follow the wrapper's ack/override flow
- treat the printed `--ack` token as an opaque receipt for the previewed branch, HEAD, dirty state, route, remote URL/refspec, diff fingerprint, risk class, nonce, and timestamp; copy the full generated command without inspecting or editing the token
- urgency is never authorization

## Verification

- wrapper recommendation is shown
- wrapper refreshes `origin/dev` before evaluating a `dev` publication
- publishing `dev` is blocked when local `dev` is behind `origin/dev`
- a branch that is both behind and ahead of its upstream is diverged; inspect with `git fetch && git status --short --branch && git diff @{u}...HEAD`, not `scripts/agent-push.py`
- after no-mistakes finishes, use `scripts/no-mistakes-finish-dev.sh` to refuse active runs, dirty trees, or unique local commits before folding local `dev` onto `origin/dev`
- when a dirty tree blocks finishing, use `scripts/git-wip-explain.sh` to classify staged, unstaged, and untracked work before deciding what to commit or move
- when stale worktrees create session confusion, use `scripts/git-worktree-cleanup.sh` to list candidates and remove only clean registered worktrees with `--remove <path> --apply`
- push intent is revalidated on ack
- raw `git push` is blocked without authorization artifact

## Stop Rules

- do not publish if hook path is uninstalled
- do not chain two persistent-state actions in one step
- do not treat prose guidance as enforcement

## Artifact Destination

- runtime evidence: `.agents/runtime/push-decisions.jsonl`
- trusted remote config: `agents/founder/trusted-remotes.json`
- shared workflow truth: this file
