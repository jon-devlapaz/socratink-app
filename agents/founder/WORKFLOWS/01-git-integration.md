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

## Required Confirmation

- no silent publication
- use `scripts/agent-push.py`
- follow the wrapper's ack/override flow
- urgency is never authorization

## Verification

- wrapper recommendation is shown
- wrapper refreshes `origin/dev` before evaluating a `dev` publication
- publishing `dev` is blocked when local `dev` is behind `origin/dev`
- after no-mistakes finishes, use `scripts/no-mistakes-finish-dev.sh` to refuse active runs, dirty trees, or unique local commits before folding local `dev` onto `origin/dev`
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
