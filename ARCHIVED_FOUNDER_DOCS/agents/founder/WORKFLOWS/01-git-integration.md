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
- no-mistakes run id, PR URL, gate head, `origin/dev` head, and eventual merge SHA for production-bound runs
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
- use `python3 scripts/agent-push.py --bypass-no-mistakes` or `SOCRATINK_BYPASS_NO_MISTAKES=1 python3 scripts/agent-push.py` only when intentionally skipping the no-mistakes gate for `origin/dev`; the bypass still uses the normal preview/ack authorization flow
- for final production-bound `dev` publication, treat the route as one continuous release ledger: push through no-mistakes, babysit the gate to completion, verify the PR checks, merge to `main`, run deploy verification for the merge SHA, then clean local branch/worktree state

## Helper Commands

```text
scripts/git-wip-explain.sh              # full local/session orientation
scripts/git-wip-explain.sh --short      # compact terminal-start summary
scripts/git-wip-explain.sh --json       # stable machine-readable orientation
python3 scripts/agent-push.py --target no-mistakes/dev
python3 scripts/agent-push.py --target no-mistakes/dev --json
python3 scripts/agent-push.py --bypass-no-mistakes
no-mistakes attach
scripts/no-mistakes-finish-dev.sh       # after no-mistakes finishes
scripts/git-worktree-cleanup.sh         # list stale worktrees
scripts/git-worktree-cleanup.sh --json  # stable machine-readable worktree list
scripts/git-worktree-cleanup.sh --remove-clean --apply
scripts/no-mistakes-lint.sh             # reproduce configured no-mistakes lint command
scripts/no-mistakes-test.sh             # reproduce configured no-mistakes test command
scripts/git-founder-help.sh             # founder-facing command map
scripts/git-founder-help.sh doctor      # read-only helper readiness check
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
- wrapper refreshes `no-mistakes/dev` before publishing there and blocks early if the destination is not an ancestor of local `HEAD`
- publishing `dev` is blocked when local `dev` is behind `origin/dev`
- a rejected `no-mistakes/dev` push with `fetch first` means the gate ref moved or was rewritten; inspect `git cherry -v no-mistakes/dev HEAD`, preserve local `dev`, then replay only unique local commits on top of the refreshed gate ref
- a branch that is both behind and ahead of its upstream is diverged; inspect with `git fetch && git status --short --branch && git diff @{u}...HEAD`, not `scripts/agent-push.py`
- after no-mistakes finishes, use `scripts/no-mistakes-finish-dev.sh` to refuse active runs, dirty trees, or unique local commits before folding local `dev` onto `origin/dev`
- when a dirty tree blocks finishing, use `scripts/git-wip-explain.sh` to classify staged, unstaged, and untracked work before deciding what to commit or move
- when stale worktrees create session confusion, use `scripts/git-worktree-cleanup.sh` to list candidates and remove only clean registered worktrees with `--remove <path> --apply`
- use the `--json` forms only for agents/scripts that need stable fields; founder-facing terminal usage should stay prose-first unless structured output is explicitly useful
- use `scripts/git-founder-help.sh doctor` when shell shortcuts, hook installation, helper executability, or `no-mistakes` availability is suspect
- `.no-mistakes.yaml` runs the Codex no-mistakes agent, delegates gate `lint` and `test` to repo-owned wrappers, and ignores `public/_lab/**`
- `scripts/no-mistakes-lint.sh` bootstraps Python, sources test-safe auth/env defaults, runs `scripts/doctor.sh`, and runs `git diff --check` from the merge-base of `COMPARE_BRANCH` or `origin/dev`
- `scripts/no-mistakes-test.sh` bootstraps Python, sources the same test-safe auth/env defaults, installs Node/Chromium coverage prerequisites, defaults `COMPARE_BRANCH` to `origin/dev` when available, and runs `scripts/check-coverage.sh`; when neither `SOCRATINK_BASE_URL` nor `APP_BASE_URL` was provided by the caller, it chooses a free loopback port and points both vars at that temporary local app
- no-mistakes bypass is limited to `origin/dev`; explicit non-`origin/dev` bypass targets fail before publication
- for long no-mistakes runs, keep a compact release ledger: no-mistakes run id, gate head, PR URL, `origin/dev` head, merge SHA, production verifier result, and final local branch/worktree status
- while no-mistakes is running, treat review/test/document/lint findings as gate rounds; use `no-mistakes attach` and the TUI fix/approve loop before pushing a replacement commit, unless the current run is intentionally being superseded
- no-mistakes success is not production success; PR checks, merge state, main preflight, and `scripts/verify-deploy.sh <merge-sha>` remain separate verification milestones
- after production verification succeeds, reconcile local `dev` onto `origin/dev`, confirm default push still routes through `no-mistakes`, and remove only clean temporary worktrees or branches with no unique commits
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
