# Founder Agent Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the first agent-first canonical workflow layer for the repo by creating the shared `agents/` canon, migrating the bootstrap/docs authority surfaces to point at it, and implementing deterministic push publication enforcement with a Python wrapper and blocking `pre-push` hook.

**Architecture:** The shared workflow truth moves into `agents/`, while `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` become thin entrypoints. Git publication safety is enforced by `scripts/agent-push.py` plus `scripts/git-hooks/pre-push`, with `.agents/runtime/` as ignored runtime evidence. V1 intentionally enforces only push publication; commit shaping, branch deletion, and PR opening remain workflow-card policy.

**Tech Stack:** Markdown docs, Python 3.13 CLI script, repo-versioned git hooks, pytest, existing `scripts/bootstrap-python.sh` / `scripts/doctor.sh`.

---

## File Structure

**Create:**
- `GEMINI.md` — Gemini entrypoint adapter into canonical workflow truth
- `agents/README.md` — boundary doc for what belongs in `agents/`
- `agents/MIGRATION.md` — migration ledger and statuses
- `agents/_templates/workflow-card.md` — fixed schema for future workflow cards
- `agents/founder/WORKFLOWS/01-git-integration.md` — first canonical workflow card
- `scripts/agent-push.py` — deterministic push publication wrapper
- `scripts/git-hooks/pre-push` — blocking hook that only allows authorized pushes
- `tests/test_agent_push.py` — wrapper policy + CLI tests
- `tests/test_pre_push_hook.py` — hook authorization tests
- `tests/test_agent_hook_installation.py` — bootstrap/doctor hook-path verification tests

**Modify:**
- `AGENTS.md` — add canonical `agents/` entrypoint guidance without deleting existing repo truth
- `CLAUDE.md` — preserve adapter role, point to canonical `agents/`
- `docs/codex/onboarding.md` — point bootstrap into canonical `agents/`
- `docs/codex/agent-quality.md` — update source-of-truth order and migration wording
- `docs/project/doc-map.md` — register `agents/` canon and updated authority model
- `docs/project/code-review-graph-sop.md` — clarify that CRG hooks remain best-effort, while `pre-push` is intentionally blocking
- `docs/project/crg-hooks-handoff.md` — remove contradiction with blocking `pre-push`
- `scripts/bootstrap-python.sh` — verify `core.hooksPath`, ensure `pre-push` executable
- `scripts/doctor.sh` — fail if hook path is not installed/configured correctly

**Untouched:**
- product runtime behavior (`main.py`, `ai_service.py`, frontend code)
- remote branch protection configuration (assumed external)
- non-git workflow enforcement

---

## Accepted implementation decisions

- The tracked canonical home is `agents/`, not `.claude/` or `.codex/`.
- `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` are thin adapters with must-not-miss bootstrap rules.
- `scripts/agent-push.py` is the supported path for normal push publication.
- The blocking enforcement seam is local only: wrapper + `pre-push` + runtime authorization artifact.
- Human break-glass bypass is explicit `git push --no-verify <remote> <refspec>`. It is documented but not supported for agents.
- The wrapper creates `.agents/runtime/` and its JSONL log on demand.
- V1 deterministically enforces only push publication. Other git actions remain workflow-card policy.
- The trusted remote strategy is tracked regex/pattern based, not Jon-machine absolute paths.

---

## Acceptance Criteria

1. `agents/` exists and is the documented shared canon for founder workflow truth.
2. `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `docs/codex/onboarding.md`, and `docs/codex/agent-quality.md` no longer present competing canon.
3. `agents/founder/WORKFLOWS/01-git-integration.md` documents `origin/dev`, `origin/feat/*`, and `no-mistakes/dev` publication policy clearly.
4. `scripts/agent-push.py` can:
   - recommend `origin/dev`, `origin/feat/*`, or `no-mistakes/dev`
   - emit a required ack token on first run
   - reject a second run if push intent changed
   - write `.agents/runtime/push-decisions.jsonl`
5. `scripts/git-hooks/pre-push` rejects raw pushes unless a matching one-shot authorization artifact exists.
6. `scripts/bootstrap-python.sh` and `scripts/doctor.sh` verify the hook path and do not silently allow an unprotected repo state.
7. Tests cover wrapper recommendation logic, ack invalidation, hook authorization, and hook installation checks.

---

## Task 1: Create the canonical `agents/` scaffold

**Files:**
- Create: `agents/README.md`
- Create: `agents/MIGRATION.md`
- Create: `agents/_templates/workflow-card.md`

- [ ] **Step 1: Write the failing doc-structure test**

Create `tests/test_agent_hook_installation.py` with:

```python
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_agents_canon_scaffold_exists() -> None:
    required = [
        REPO_ROOT / "agents" / "README.md",
        REPO_ROOT / "agents" / "MIGRATION.md",
        REPO_ROOT / "agents" / "_templates" / "workflow-card.md",
    ]
    missing = [str(path.relative_to(REPO_ROOT)) for path in required if not path.exists()]
    assert not missing, f"missing agent canon scaffold: {missing}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_agent_hook_installation.py::test_agents_canon_scaffold_exists -v
```

Expected: FAIL with missing `agents/...` paths.

- [ ] **Step 3: Create `agents/README.md`**

Create `agents/README.md`:

```md
# agents/

Canonical shared workflow truth for repo agents.

## What belongs here

- workflow cards
- templates
- migration ledgers
- founder orchestration doctrine
- prompt batteries
- shared decision rubrics

## What does not belong here

- runtime executables already owned by `scripts/`
- auth/session state
- caches
- tool-specific hooks/settings syntax

## Authority rule

`agents/` is the shared canon. `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` are entrypoint adapters into this canon. Tool-specific directories like `.claude/`, `.codex/`, and `.gemini/` are runtime/config/wrapper surfaces, not canonical doctrine.

## Migration rule

Migrate selectively. Promote only stable, high-signal, cross-model content. Preserve high-value tool-local content until its signal is captured or intentionally deprecated.
```

- [ ] **Step 4: Create `agents/MIGRATION.md`**

Create `agents/MIGRATION.md`:

```md
# Agent Canon Migration Ledger

Use this ledger to track migration from tool-specific surfaces into `agents/`.

## Status vocabulary

- `promoted`
- `adapter-only`
- `tool-specific`
- `preserved-pending-review`
- `deprecated`

## Initial entries

| Surface | Status | Notes |
| --- | --- | --- |
| `AGENTS.md` | `adapter-only` | repo root entrypoint; retains must-not-miss bootstrap rules |
| `CLAUDE.md` | `adapter-only` | Claude compatibility pointer into canon |
| `GEMINI.md` | `adapter-only` | Gemini compatibility pointer into canon |
| `docs/codex/onboarding.md` | `preserved-pending-review` | currently binding bootstrap surface; must point into canon |
| `docs/codex/agent-quality.md` | `preserved-pending-review` | currently binding quality/source-of-truth surface; must reflect canon |
| `.claude/` | `tool-specific` | runtime skills/settings surface |
| `.codex/` | `tool-specific` | runtime/config/memory surface |
| `.gemini/` | `tool-specific` | runtime/config/auth surface |
```

- [ ] **Step 5: Create the workflow-card template**

Create `agents/_templates/workflow-card.md`:

```md
# [Workflow Name]

## Trigger

## Goal

## Inputs To Inspect

## Risk Classification

## Recommended Route

## Required Confirmation

## Verification

## Stop Rules

## Artifact Destination
```

- [ ] **Step 6: Run the scaffold test again**

Run:

```bash
pytest tests/test_agent_hook_installation.py::test_agents_canon_scaffold_exists -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add agents/README.md agents/MIGRATION.md agents/_templates/workflow-card.md tests/test_agent_hook_installation.py
git commit -m "feat(agents): add canonical scaffold and workflow template"
```

---

## Task 2: Write the first canonical workflow card

**Files:**
- Create: `agents/founder/WORKFLOWS/01-git-integration.md`
- Test: `tests/test_agent_hook_installation.py`

- [ ] **Step 1: Extend the failing test for the workflow card**

Append to `tests/test_agent_hook_installation.py`:

```python
def test_git_integration_workflow_exists_and_mentions_v1_scope() -> None:
    path = REPO_ROOT / "agents" / "founder" / "WORKFLOWS" / "01-git-integration.md"
    assert path.exists(), "missing git-integration workflow card"
    text = path.read_text(encoding="utf-8")
    assert "origin/dev" in text
    assert "origin/feat/*" in text
    assert "no-mistakes/dev" in text
    assert "push publication" in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_agent_hook_installation.py::test_git_integration_workflow_exists_and_mentions_v1_scope -v
```

Expected: FAIL because the workflow card does not exist yet.

- [ ] **Step 3: Write `agents/founder/WORKFLOWS/01-git-integration.md`**

Create `agents/founder/WORKFLOWS/01-git-integration.md`:

```md
# Git Integration

## Trigger

Any request to commit, publish a branch, open a PR, or “push/ship” code.

## Goal

Route publication safely while keeping the founder in the loop for meaningful persistent-state changes.

## Inputs To Inspect

- current branch
- working tree state
- destination remote/refspec
- touched files
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
- follow the wrapper’s ack/override flow
- urgency is never authorization

## Verification

- wrapper recommendation is shown
- push intent is revalidated on ack
- raw `git push` is blocked without authorization artifact

## Stop Rules

- do not publish if hook path is uninstalled
- do not chain two persistent-state actions in one step
- do not treat prose guidance as enforcement

## Artifact Destination

- runtime evidence: `.agents/runtime/push-decisions.jsonl`
- shared workflow truth: this file
```

- [ ] **Step 4: Run the workflow-card test again**

Run:

```bash
pytest tests/test_agent_hook_installation.py::test_git_integration_workflow_exists_and_mentions_v1_scope -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/founder/WORKFLOWS/01-git-integration.md tests/test_agent_hook_installation.py
git commit -m "feat(agents): add git integration workflow card"
```

---

## Task 3: Convert bootstrap and registry surfaces into adapters

**Files:**
- Create: `GEMINI.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `docs/codex/onboarding.md`
- Modify: `docs/codex/agent-quality.md`
- Modify: `docs/project/doc-map.md`
- Modify: `docs/project/code-review-graph-sop.md`
- Modify: `docs/project/crg-hooks-handoff.md`
- Test: `tests/test_agent_hook_installation.py`

- [ ] **Step 1: Add a failing adapter/registry test**

Append to `tests/test_agent_hook_installation.py`:

```python
def test_root_adapters_point_to_agents_canon() -> None:
    for rel in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "agents/" in text, f"{rel} must point to canonical agents/ path"


def test_bootstrap_docs_acknowledge_agents_canon() -> None:
    onboarding = (REPO_ROOT / "docs" / "codex" / "onboarding.md").read_text(encoding="utf-8")
    quality = (REPO_ROOT / "docs" / "codex" / "agent-quality.md").read_text(encoding="utf-8")
    assert "agents/" in onboarding
    assert "agents/" in quality
```

- [ ] **Step 2: Run the adapter test to verify it fails**

Run:

```bash
pytest tests/test_agent_hook_installation.py::test_root_adapters_point_to_agents_canon tests/test_agent_hook_installation.py::test_bootstrap_docs_acknowledge_agents_canon -v
```

Expected: FAIL because `GEMINI.md` is missing and the Codex docs do not yet point into `agents/`.

- [ ] **Step 3: Create `GEMINI.md`**

Create `GEMINI.md`:

```md
# GEMINI.md

Canonical agent workflow truth for this repo lives in `agents/` and is entered via `AGENTS.md`.

Gemini sessions should:
1. read `AGENTS.md`
2. load the relevant canon under `agents/`
3. treat `.claude/`, `.codex/`, and `.gemini/` as runtime/config surfaces, not canonical doctrine
```

- [ ] **Step 4: Update `AGENTS.md` and `CLAUDE.md` minimally**

Add near the top of `AGENTS.md`:

```md
## Shared Agent Canon

The canonical shared workflow truth for repo agents now lives in `agents/`.

- Use `agents/README.md` for the boundary contract
- Use `agents/founder/WORKFLOWS/` for founder workflow cards
- Treat tool-specific directories (`.claude/`, `.codex/`, `.gemini/`) as runtime/config surfaces unless a migration ledger entry says otherwise
```

Replace `CLAUDE.md` with:

```md
# CLAUDE.md

Canonical shared workflow truth for this repo lives in `AGENTS.md` and `agents/`.

Claude sessions should read `AGENTS.md` first, then load the relevant canon in `agents/`. This file exists as a compatibility adapter and should not become a competing doctrine surface.
```

- [ ] **Step 5: Update the current Codex/bootstrap docs and registry**

Make these targeted edits:

```md
# docs/codex/onboarding.md
- add `agents/README.md` and `agents/founder/WORKFLOWS/` to the read order / bootstrap rules
- clarify that `docs/codex/onboarding.md` now bootstraps into the canonical `agents/` layer

# docs/codex/agent-quality.md
- replace “Agent bootstrap: docs/codex/onboarding.md” with wording that onboarding routes into `agents/`
- replace “Do not create parallel source-of-truth files...” with wording that the migration intentionally promotes `agents/` while reducing old surfaces to adapters/redirects

# docs/project/doc-map.md
- register `agents/README.md`, `agents/MIGRATION.md`, `agents/_templates/workflow-card.md`, `agents/founder/WORKFLOWS/01-git-integration.md`
- update the workflow/authority notes to reflect the new canon

# docs/project/code-review-graph-sop.md
- keep CRG hooks best-effort
- explicitly carve out the new blocking `pre-push` as workflow enforcement, not CRG behavior

# docs/project/crg-hooks-handoff.md
- update verification language so CRG-specific hooks remain graceful, while repo `pre-push` can be intentionally blocking
```

- [ ] **Step 6: Run the adapter/registry tests again**

Run:

```bash
pytest tests/test_agent_hook_installation.py::test_root_adapters_point_to_agents_canon tests/test_agent_hook_installation.py::test_bootstrap_docs_acknowledge_agents_canon -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add AGENTS.md CLAUDE.md GEMINI.md docs/codex/onboarding.md docs/codex/agent-quality.md docs/project/doc-map.md docs/project/code-review-graph-sop.md docs/project/crg-hooks-handoff.md tests/test_agent_hook_installation.py
git commit -m "feat(agents): route bootstrap and registry docs into canon"
```

---

## Task 4: Implement `scripts/agent-push.py` and wrapper tests

**Files:**
- Create: `scripts/agent-push.py`
- Create: `tests/test_agent_push.py`

- [ ] **Step 1: Write the failing recommendation and ack tests**

Create `tests/test_agent_push.py`:

```python
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "agent-push.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("agent_push", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dev_branch_recommends_origin_dev_for_narrow_change(tmp_path):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["public/js/app.js"],
        remote_urls={"origin": "https://github.com/jon-devlapaz/socratink-app.git"},
    )
    recommendation = mod.recommend_route(state, explicit_target=None)
    assert recommendation.route == "origin/dev"


def test_feature_branch_recommends_origin_feature_branch(tmp_path):
    mod = _load_module()
    state = mod.PushState(
        branch="feat/demo-flow",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["public/js/app.js"],
        remote_urls={"origin": "https://github.com/jon-devlapaz/socratink-app.git"},
    )
    recommendation = mod.recommend_route(state, explicit_target=None)
    assert recommendation.route == "origin/feat/demo-flow"


def test_high_risk_paths_recommend_no_mistakes(tmp_path):
    mod = _load_module()
    state = mod.PushState(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        changed_paths=["main.py", "docs/codex/onboarding.md"],
        remote_urls={
            "origin": "https://github.com/jon-devlapaz/socratink-app.git",
            "no-mistakes": "/Users/example/.no-mistakes/repos/deadbeef.git",
        },
    )
    recommendation = mod.recommend_route(state, explicit_target=None)
    assert recommendation.route == "no-mistakes/dev"


def test_ack_payload_invalidates_when_head_changes(tmp_path):
    mod = _load_module()
    payload = mod.AuthorizationPayload(
        branch="dev",
        head_sha="abc1234",
        dirty=False,
        route="origin/dev",
        remote_url="https://github.com/jon-devlapaz/socratink-app.git",
        refspec="dev",
        diff_fingerprint="fingerprint-1",
        risk_class="confirm",
        nonce="nonce-1",
        issued_at_epoch=1,
    )
    current = payload.model_copy(update={"head_sha": "fffffff"})
    assert not mod.intent_matches(payload, current)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_agent_push.py -v
```

Expected: FAIL because `scripts/agent-push.py` does not exist.

- [ ] **Step 3: Write the minimal wrapper implementation**

Create `scripts/agent-push.py`:

```python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = REPO_ROOT / ".agents" / "runtime"
AUTH_PATH = RUNTIME_DIR / "push-auth.json"
LOG_PATH = RUNTIME_DIR / "push-decisions.jsonl"

PUBLIC_REMOTE_PATTERNS = [r"^https://github\\.com/jon-devlapaz/socratink-app\\.git$"]
NO_MISTAKES_PATTERNS = [r"(^|/|\\\\)\\.no-mistakes([/\\\\])repos([/\\\\])[0-9a-f]+\\.git$"]

HIGH_RISK_PREFIXES = (
    "main.py",
    "api/index.py",
    "ai_service.py",
    "auth/",
    "vercel.json",
    ".github/workflows/",
    "requirements.txt",
    "requirements-dev.txt",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "agents/",
    "docs/codex/onboarding.md",
    "docs/codex/agent-quality.md",
    "scripts/bootstrap-python.sh",
    "scripts/doctor.sh",
    "scripts/check-coverage.sh",
    "scripts/git-hooks/",
)


@dataclass(frozen=True)
class PushState:
    branch: str
    head_sha: str
    dirty: bool
    changed_paths: list[str]
    remote_urls: dict[str, str]


@dataclass(frozen=True)
class RouteRecommendation:
    route: str
    risk_class: str
    triggers: list[str]


class AuthorizationPayload(BaseModel):
    branch: str
    head_sha: str
    dirty: bool
    route: str
    remote_url: str
    refspec: str
    diff_fingerprint: str
    risk_class: str
    nonce: str
    issued_at_epoch: int


def recommend_route(state: PushState, explicit_target: str | None) -> RouteRecommendation:
    if state.branch.startswith("feat/"):
        return RouteRecommendation(route=f"origin/{state.branch}", risk_class="confirm", triggers=["feature_branch"])
    high_risk = [path for path in state.changed_paths if path.startswith(HIGH_RISK_PREFIXES)]
    if high_risk:
        return RouteRecommendation(route="no-mistakes/dev", risk_class="confirm", triggers=high_risk)
    return RouteRecommendation(route="origin/dev", risk_class="confirm", triggers=["default_dev_publication"])


def intent_matches(original: AuthorizationPayload, current: AuthorizationPayload) -> bool:
    return original.model_dump() == current.model_dump()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target")
    parser.add_argument("--ack")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Fill in the real CLI behavior**

Expand `main()` to:

```python
- gather branch / HEAD / dirty state via `git`
- gather changed paths via `git diff --name-only --cached` fallback to `git diff --name-only HEAD`
- gather remote URLs via `git remote -v`
- compute route recommendation
- map route to remote + refspec
- create `RUNTIME_DIR` on demand
- first run: print recommendation + required rerun command, write nothing irreversible, return 1
- second run: validate ack payload, write `AUTH_PATH`, append decision log, run `git push <remote> <refspec>`, then delete `AUTH_PATH`
```

- [ ] **Step 5: Run wrapper tests again**

Run:

```bash
pytest tests/test_agent_push.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/agent-push.py tests/test_agent_push.py
git commit -m "feat(git): add deterministic agent push wrapper"
```

---

## Task 5: Implement the blocking `pre-push` hook and hook tests

**Files:**
- Create: `scripts/git-hooks/pre-push`
- Create: `tests/test_pre_push_hook.py`

- [ ] **Step 1: Write the failing hook tests**

Create `tests/test_pre_push_hook.py`:

```python
import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "scripts" / "git-hooks" / "pre-push"


def test_pre_push_rejects_without_authorization(tmp_path):
    result = subprocess.run(
        ["/bin/zsh", str(HOOK), "origin", "https://github.com/jon-devlapaz/socratink-app.git"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "agent-push.py" in result.stderr


def test_pre_push_accepts_matching_authorization(tmp_path):
    runtime = tmp_path / ".agents" / "runtime"
    runtime.mkdir(parents=True)
    auth = runtime / "push-auth.json"
    auth.write_text(json.dumps({
        "branch": "dev",
        "head_sha": "abc1234",
        "dirty": False,
        "route": "origin/dev",
        "remote_url": "https://github.com/jon-devlapaz/socratink-app.git",
        "refspec": "dev",
        "diff_fingerprint": "fp",
        "risk_class": "confirm",
        "nonce": "n",
        "issued_at_epoch": 1,
    }), encoding="utf-8")
    env = os.environ | {"SOCRATINK_PUSH_AUTH_PATH": str(auth), "SOCRATINK_PUSH_SKIP_GIT_HEAD": "1"}
    result = subprocess.run(
        ["/bin/zsh", str(HOOK), "origin", "https://github.com/jon-devlapaz/socratink-app.git"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0
```

- [ ] **Step 2: Run the hook tests to verify they fail**

Run:

```bash
pytest tests/test_pre_push_hook.py -v
```

Expected: FAIL because the hook does not exist yet.

- [ ] **Step 3: Write the minimal hook**

Create `scripts/git-hooks/pre-push`:

```bash
#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
auth_path="${SOCRATINK_PUSH_AUTH_PATH:-$repo_root/.agents/runtime/push-auth.json}"
remote_name="${1:-}"
remote_url="${2:-}"

if [ ! -f "$auth_path" ]; then
  echo "[pre-push] ERROR: push not authorized. Use scripts/agent-push.py." >&2
  exit 1
fi

python3 - "$auth_path" "$remote_name" "$remote_url" <<'PY'
import json
import sys
from pathlib import Path

auth_path = Path(sys.argv[1])
remote_name = sys.argv[2]
remote_url = sys.argv[3]
payload = json.loads(auth_path.read_text(encoding="utf-8"))

expected_route = payload["route"]
expected_url = payload["remote_url"]

if expected_route.startswith("origin/") and remote_name != "origin":
    raise SystemExit(1)
if expected_route.startswith("no-mistakes/") and remote_name != "no-mistakes":
    raise SystemExit(1)
if remote_url != expected_url:
    raise SystemExit(1)
PY

rm -f "$auth_path"
exit 0
```

- [ ] **Step 4: Make the hook executable and rerun tests**

Run:

```bash
chmod +x scripts/git-hooks/pre-push
pytest tests/test_pre_push_hook.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/git-hooks/pre-push tests/test_pre_push_hook.py
git commit -m "feat(git): add blocking pre-push authorization hook"
```

---

## Task 6: Wire bootstrap/doctor and finish doc consistency

**Files:**
- Modify: `scripts/bootstrap-python.sh`
- Modify: `scripts/doctor.sh`
- Modify: `docs/project/code-review-graph-sop.md`
- Modify: `docs/project/crg-hooks-handoff.md`
- Modify: `docs/project/doc-map.md`
- Modify: `docs/codex/onboarding.md`
- Modify: `docs/codex/agent-quality.md`
- Test: `tests/test_agent_hook_installation.py`

- [ ] **Step 1: Add the failing hook-installation checks**

Append to `tests/test_agent_hook_installation.py`:

```python
import subprocess


def test_bootstrap_script_wires_repo_hook_path() -> None:
    text = (REPO_ROOT / "scripts" / "bootstrap-python.sh").read_text(encoding="utf-8")
    assert "core.hooksPath" in text
    assert "scripts/git-hooks" in text


def test_doctor_checks_hook_installation() -> None:
    text = (REPO_ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
    assert "core.hooksPath" in text or "git config --local --default '' core.hooksPath" in text
    assert "scripts/git-hooks" in text
```

- [ ] **Step 2: Run the tests to verify at least the doctor check fails**

Run:

```bash
pytest tests/test_agent_hook_installation.py::test_bootstrap_script_wires_repo_hook_path tests/test_agent_hook_installation.py::test_doctor_checks_hook_installation -v
```

Expected: bootstrap test PASS, doctor test FAIL because `doctor.sh` does not check hook installation yet.

- [ ] **Step 3: Update `scripts/doctor.sh`**

Add after required-file checks:

```bash
echo "[doctor] git hook path..."
hook_path="$(git config --local --default '' core.hooksPath)"
if [ "$hook_path" != "scripts/git-hooks" ]; then
  echo "[doctor] FAIL: core.hooksPath is '$hook_path' (expected scripts/git-hooks)" >&2
  exit 1
fi

if [ ! -x "scripts/git-hooks/pre-push" ]; then
  echo "[doctor] FAIL: scripts/git-hooks/pre-push missing or not executable" >&2
  exit 1
fi
```

- [ ] **Step 4: Update docs for consistency**

Make these exact doc edits:

```md
# docs/project/code-review-graph-sop.md
- keep CRG post-* hooks documented as best-effort
- add one explicit sentence: repo `pre-push` is workflow enforcement and may block publication intentionally

# docs/project/crg-hooks-handoff.md
- change the verification bullet so “fail gracefully without breaking standard Git operations” applies to CRG hook commands, not to the repo-wide `pre-push` publication gate

# docs/project/doc-map.md
- ensure the new `agents/` files are registered and these hook docs remain accurate

# docs/codex/onboarding.md / docs/codex/agent-quality.md
- verify the `agents/` canon wording from Task 3 still matches final implementation
```

- [ ] **Step 5: Run the hook-installation tests again**

Run:

```bash
pytest tests/test_agent_hook_installation.py -v
```

Expected: PASS.

- [ ] **Step 6: Run the minimum repo verification**

Run:

```bash
bash scripts/doctor.sh
pytest tests/test_agent_push.py tests/test_pre_push_hook.py tests/test_agent_hook_installation.py -v
```

Expected:
- `doctor.sh` exits 0
- pytest exits 0

- [ ] **Step 7: Commit**

```bash
git add scripts/bootstrap-python.sh scripts/doctor.sh docs/project/code-review-graph-sop.md docs/project/crg-hooks-handoff.md docs/project/doc-map.md docs/codex/onboarding.md docs/codex/agent-quality.md tests/test_agent_hook_installation.py
git commit -m "feat(git): wire hook installation and align bootstrap docs"
```

---

## Task 7: End-to-end manual publication proof

**Files:**
- Modify: none expected (verification only unless a bug is found)

- [ ] **Step 1: Dry-run the wrapper on `dev`**

Run:

```bash
python3 scripts/agent-push.py --target origin/dev
```

Expected: exits non-zero after printing recommendation and rerun command with ack token.

- [ ] **Step 2: Verify raw push is blocked**

Run:

```bash
git push origin dev
```

Expected: FAIL from `pre-push` with a message that instructs the caller to use `scripts/agent-push.py`.

- [ ] **Step 3: Re-run the wrapper with the printed ack token**

Run:

```bash
python3 scripts/agent-push.py --target origin/dev --ack "<token printed by prior run>"
```

Expected: authorization artifact created, push succeeds once, runtime log appended, auth artifact removed.

- [ ] **Step 4: Verify runtime evidence**

Run:

```bash
tail -n 1 .agents/runtime/push-decisions.jsonl
```

Expected: last line includes `recommended_route`, `chosen_route`, and `override`.

- [ ] **Step 5: Commit final integration polish if needed**

Only if verification required code/doc changes:

```bash
git add <changed-files>
git commit -m "fix(git): polish agent push publication flow"
```

---

## Self-review checklist

- Spec coverage:
  - canonical `agents/` scaffold: Tasks 1-3
  - first workflow card: Task 2
  - adapter migration and bootstrap docs: Tasks 3 and 6
  - deterministic push enforcement: Tasks 4-5
  - runtime evidence and verification: Tasks 4, 5, and 7
- Placeholder scan:
  - no `TODO`/`TBD` markers remain in plan steps
  - all open questions from the spec were resolved into concrete v1 choices
- Type consistency:
  - wrapper file is consistently `scripts/agent-push.py`
  - runtime log path is consistently `.agents/runtime/push-decisions.jsonl`
  - enforcement scope is consistently “push publication only” for v1
