#!/usr/bin/env bash
# Founder-facing map and readiness checks for the Socratink git helpers.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  scripts/git-founder-help.sh
  scripts/git-founder-help.sh --json
  scripts/git-founder-help.sh doctor [--json]

Default mode prints the founder-facing git helper map. Doctor mode is read-only
and checks whether the repo-owned helper scripts and local shell shortcuts are
available.
EOF
}

print_help() {
  cat <<'EOF'
Socratink git helper map

Daily orientation
  scripts/agent-lane-status.sh
    Use when: you need the fastest answer to "where are we, who owns this lane,
    what is blocking, and what is the next professional move?"
    Safe: read-only. It does not fetch, checkout, push, close panes, or clean.

  gwip
    Use when: you feel unsure what changed, what is staged, whether you are
    ahead/behind, or which worktrees exist.
    Safe: read-only. It does not stage, commit, reset, fetch, or push.

  gwip --short
    Use when: you only need the dashboard line and the next recommended command.
    This is what new project terminals run automatically.

  gwip --json
    Use when: an agent or script needs stable machine-readable state.

Publishing
  gpub
    Use when: the working tree is clean and you want to publish committed local
    work to the authorized origin target.
    Safe: first run is a preview only. It prints an ack command. It refuses
    dirty working trees so uncommitted files cannot be accidentally skipped.

  gpub --json
    Use when: an agent needs the publication preview as structured data.

  gpub --ack <token>
    Use when: you have read the gpub preview and intentionally want to publish.

Worktree cleanup
  gwt
    Use when: you want to see old agent/worktree sessions and whether they are
    clean-removable, dirty-blocked, current, or main.
    Safe: list-only by default.

  gwt --json
    Use when: an agent or script needs stable machine-readable worktree status.

  gwt --remove <path> --apply
    Use when: gwt marked a worktree clean-removable and you want it gone.
    It refuses the current worktree, main worktree, dirty worktrees, and unknown paths.

  gwt --remove-clean --apply
    Use when: you want to delete every clean-removable worktree in one sweep.
    It still refuses the current worktree, main worktree, dirty worktrees, and unknown paths.

Help and readiness
  ghelp
    Use when: you want this command map.

  ghelp doctor
    Use when: you want to check helper executables, hook wiring, and local shell shortcut wiring.

Legacy muscle memory
  snm
    Use when: your fingers remember the old shortcut.
    It now calls gpub safely. It no longer raw-pushes or auto-resets.

Rules of thumb
  Dirty tree?        gwip
  Clean + ahead?     gpub
  Too many sessions? gwt
  Delete clean sessions? gwt --remove-clean --apply
EOF
}

print_help_json() {
  python3 - <<'PY'
import json

commands = [
    {
        "name": "agent-lane-status",
        "script": "scripts/agent-lane-status.sh",
        "safe": "read-only",
        "uses": ["lane-status", "pr-state", "worktree-inventory", "next-move"],
        "json": "scripts/agent-lane-status.sh --json",
    },
    {
        "name": "gwip",
        "script": "scripts/git-wip-explain.sh",
        "safe": "read-only",
        "uses": ["orientation", "dirty-state", "next-command"],
        "json": "gwip --json",
    },
    {
        "name": "gpub",
        "script": "scripts/agent-push.py",
        "safe": "preview-first publish",
        "uses": ["publication-preview", "acknowledged-publish"],
        "json": "gpub --json",
    },
    {
        "name": "gwt",
        "script": "scripts/git-worktree-cleanup.sh",
        "safe": "list-only by default",
        "uses": ["worktree-inventory", "guarded-cleanup"],
        "json": "gwt --json",
    },
    {
        "name": "ghelp",
        "script": "scripts/git-founder-help.sh",
        "safe": "read-only",
        "uses": ["command-map", "doctor"],
        "json": "ghelp --json",
    },
    {
        "name": "snm",
        "script": "shell wrapper to gpub",
        "safe": "legacy preview-first alias",
        "uses": ["legacy-muscle-memory"],
        "json": None,
    },
]
print(json.dumps({"schema_version": 1, "workflow": "socratink-founder-git", "commands": commands}, sort_keys=True))
PY
}

add_check_json() {
  local name="$1" ok="$2" detail="$3"
  CHECKS_JSON="${CHECKS_JSON}${CHECKS_JSON:+$'\n'}${name}	${ok}	${detail}"
}

run_doctor() {
  local json_mode="$1"
  local ok_all="1"
  CHECKS_JSON=""

  check_file git-wip-explain "$repo_root/scripts/git-wip-explain.sh" executable
  check_file git-worktree-cleanup "$repo_root/scripts/git-worktree-cleanup.sh" executable
  check_file agent-push "$repo_root/scripts/agent-push.py" file
  check_file pre-push-hook "$repo_root/scripts/git-hooks/pre-push" executable

  local hook_path
  hook_path="$(git -C "$repo_root" config --local --default '' core.hooksPath)"
  if [ "$hook_path" = "scripts/git-hooks" ]; then
    add_check_json hook-path true "core.hooksPath=scripts/git-hooks"
  else
    ok_all="0"
    add_check_json hook-path false "core.hooksPath=${hook_path:-unset}"
  fi

  local zshrc="${HOME:-}/.zshrc"
  if [ -f "$zshrc" ] && grep -q "gwip()" "$zshrc" && grep -q "gpub()" "$zshrc" && grep -q "gwt()" "$zshrc"; then
    add_check_json shell-shortcuts true "gwip/gpub/gwt found in ~/.zshrc"
  else
    ok_all="0"
    add_check_json shell-shortcuts false "expected gwip/gpub/gwt shortcuts not found in ~/.zshrc"
  fi

  if [ "$json_mode" = "1" ]; then
    CHECKS_JSON="$CHECKS_JSON" python3 - <<'PY'
import json
import os

checks = []
for line in os.environ["CHECKS_JSON"].splitlines():
    name, ok, detail = line.split("\t", 2)
    checks.append({"name": name, "ok": ok == "true", "detail": detail})
payload = {"schema_version": 1, "workflow": "socratink-founder-git", "checks": checks}
print(json.dumps(payload, sort_keys=True))
PY
  else
    echo "Socratink git helper doctor"
    while IFS=$'\t' read -r name ok detail; do
      [ -n "$name" ] || continue
      if [ "$ok" = "true" ]; then
        printf '  [OK] %s: %s\n' "$name" "$detail"
      else
        printf '  [WARN] %s: %s\n' "$name" "$detail"
      fi
    done <<< "$CHECKS_JSON"
  fi

  [ "$ok_all" = "1" ]
}

check_file() {
  local name="$1" path="$2" kind="$3"
  if [ "$kind" = "executable" ] && [ -x "$path" ]; then
    add_check_json "$name" true "${path#"$repo_root"/}"
    return
  fi
  if [ "$kind" = "file" ] && [ -f "$path" ]; then
    add_check_json "$name" true "${path#"$repo_root"/}"
    return
  fi
  add_check_json "$name" false "missing ${kind}: ${path#"$repo_root"/}"
}

mode="help"
json_mode="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    doctor)
      mode="doctor"
      shift
      ;;
    --json)
      json_mode="1"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

case "$mode:$json_mode" in
  help:0) print_help ;;
  help:1) print_help_json ;;
  doctor:*) run_doctor "$json_mode" ;;
esac
