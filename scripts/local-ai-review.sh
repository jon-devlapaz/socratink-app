#!/usr/bin/env bash
# No-push/no-file-edit local AI reviewer for Socratink workflow artifacts.

set -euo pipefail

DEEPSEEK_LOCAL_BIN="${DEEPSEEK_LOCAL_BIN:-/Users/jondev/bin/deepseek-local}"
MAX_BYTES="${LOCAL_AI_REVIEW_MAX_BYTES:-81920}"

fail() {
  echo "[local-ai-review] ERROR: $*" >&2
  exit 2
}

fail_open() {
  echo "[local-ai-review] WARNING: $*" >&2
  echo "[local-ai-review] Skipping review (fail-open)." >&2
  exit 0
}

has_code_changes() {
  local files
  if [ "${mode:-}" = "staged" ]; then
    files="$(git -C "$repo_root" diff --cached --name-only --no-ext-diff 2>/dev/null || true)"
  elif [ "${mode:-}" = "diff" ]; then
    files="$(git -C "$repo_root" diff --name-only --no-ext-diff 2>/dev/null || true)"
  elif [ "${mode:-}" = "publish-diff" ]; then
    local base="${1:-origin/dev}"
    files="$(git -C "$repo_root" diff --name-only "${base}...HEAD" --no-ext-diff 2>/dev/null || true)"
  else
    return 0
  fi

  [ -n "$files" ] || return 1

  local code_file_found=false
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      *.md|*.json|*.yml|*.yaml|*.txt|*.png|*.jpg|*.jpeg|*.gif|*.svg|.gitignore|LICENSE|*.ini|pyproject.toml|pyrefly.toml|mypy.ini|vercel.json|*/.gemini/*)
        # Skip non-code files
        ;;
      *)
        code_file_found=true
        break
        ;;
    esac
  done <<< "$files"

  if [ "$code_file_found" = "true" ]; then
    return 0
  else
    return 1
  fi
}

usage() {
  cat <<'EOF'
Usage:
  scripts/local-ai-review.sh check
  scripts/local-ai-review.sh staged
  scripts/local-ai-review.sh diff
  scripts/local-ai-review.sh publish-diff <base-ref>
  scripts/local-ai-review.sh wip
  scripts/local-ai-review.sh publish-preview
  scripts/local-ai-review.sh smoke-local
  scripts/local-ai-review.sh pytest -- <pytest command>

Advisory wrapper around /Users/jondev/bin/deepseek-local.
It uses canned prompts, refuses likely secrets, caps payload size, and never
edits files or pushes. publish-preview runs agent-push.py in preview mode,
which may fetch/refresh local remote-tracking refs before producing redacted
output.
EOF
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

mode="${1:-}"
[ -n "$mode" ] || {
  usage >&2
  exit 2
}
shift || true

case "$mode" in
  --help|-h|help)
    usage
    exit 0
    ;;
esac

ensure_local_ollama_host() {
  local host="${OLLAMA_HOST:-}"
  [ -n "$host" ] || return 0
  case "$host" in
    http://127.0.0.1:*|https://127.0.0.1:*|http://localhost:*|https://localhost:*)
      return 0
      ;;
    127.0.0.1:*|localhost:*)
      export OLLAMA_HOST="http://${host}"
      return 0
      ;;
    *)
      if [ "${mode:-}" = "check" ]; then
        fail "refusing broad OLLAMA_HOST=${host}; use 127.0.0.1 or localhost for local AI review"
      else
        fail_open "refusing broad OLLAMA_HOST=${host}; use 127.0.0.1 or localhost for local AI review"
      fi
      ;;
  esac
}

require_helper() {
  if [ ! -x "$DEEPSEEK_LOCAL_BIN" ]; then
    if [ "${mode:-}" = "check" ]; then
      fail "DeepSeek helper is not executable: $DEEPSEEK_LOCAL_BIN"
    else
      fail_open "DeepSeek helper is not executable: $DEEPSEEK_LOCAL_BIN"
    fi
  fi
}

payload_size() {
  wc -c | tr -d '[:space:]'
}

refuse_secret_payload() {
  local payload="$1"
  if printf '%s' "$payload" | grep -Eiq '(^|[^A-Z0-9_])(OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY|SUPABASE_SERVICE_ROLE|[A-Z0-9_]*(KEY|TOKEN|SECRET))='; then
    fail "refusing to send possible secret to local model"
  fi
  if printf '%s' "$payload" | grep -Eq -- '-----BEGIN [A-Z ]*PRIVATE KEY-----'; then
    fail "refusing to send possible private key to local model"
  fi
  if printf '%s' "$payload" | grep -Eq '(^|[[:space:]])\.env(\.local)?($|[[:space:]:])'; then
    fail "refusing to send .env-like content to local model"
  fi
}

review_payload() {
  local mode_label="$1"
  local prompt="$2"
  local context="$3"
  local payload bytes

  payload="$(printf '%s\n\n--- CONTEXT ---\n%s\n' "$prompt" "$context")"
  refuse_secret_payload "$payload"
  bytes="$(printf '%s' "$payload" | payload_size)"
  if [ "$bytes" -gt "$MAX_BYTES" ]; then
    fail "payload is ${bytes} bytes, over limit ${MAX_BYTES}; narrow the diff or set LOCAL_AI_REVIEW_MAX_BYTES"
  fi

  echo "[local-ai-review] mode: $mode_label"
  echo "[local-ai-review] bytes: $bytes"
  echo "[local-ai-review] helper: $DEEPSEEK_LOCAL_BIN"
  echo "[local-ai-review] ADVISORY ONLY: verify findings against repo files, tests, and deterministic helpers."
  if ! printf '%s' "$payload" | "$DEEPSEEK_LOCAL_BIN"; then
    fail_open "local review helper failed (check if Ollama is running and the model is installed)"
  fi
}

run_check() {
  ensure_local_ollama_host
  require_helper
  "$DEEPSEEK_LOCAL_BIN" --check
}

collect_staged() {
  git -C "$repo_root" diff --cached --no-ext-diff
}

collect_diff() {
  git -C "$repo_root" diff --no-ext-diff
}

collect_wip() {
  local helper="$repo_root/scripts/git-wip-explain.sh"
  [ -x "$helper" ] || fail "missing executable wip helper: $helper"
  "$helper"
}

collect_publish_preview() {
  local helper="$repo_root/scripts/agent-push.py"
  [ -f "$helper" ] || fail "missing publish helper: $helper"
  python3 "$helper" --target no-mistakes/dev 2>&1 \
    | sed -E 's/(--ack )[[:graph:]]+/\1[ACK_TOKEN_REDACTED]/g'
}

collect_smoke_local() {
  local helper="$repo_root/scripts/qa-smoke.sh"
  [ -x "$helper" ] || fail "missing executable smoke helper: $helper"
  "$helper" local 2>&1
}

collect_pytest() {
  [ "${1:-}" = "--" ] || fail "pytest mode requires: scripts/local-ai-review.sh pytest -- <pytest command>"
  shift
  [ "$#" -gt 0 ] || fail "pytest mode requires a command after --"
  local runner_name
  runner_name="$(basename "$1")"
  case "$runner_name" in
    pytest|pytest3)
      ;;
    *)
      fail "pytest mode requires a pytest runner after --, got: $1"
      ;;
  esac
  "$@" 2>&1 || true
}

ensure_local_ollama_host
require_helper

case "$mode" in
  check)
    run_check
    ;;
  staged)
    if ! has_code_changes; then
      echo "[local-ai-review] No code changes to review. Skipping."
      exit 0
    fi
    review_payload \
      "staged" \
      "Review this staged diff for behavior-breaking bugs only. Ignore style, naming, formatting, and speculative concerns. Report only issues that would break runtime behavior, tests, data safety, or Socratink workflow safety. For each finding, name the evidence that would verify or refute it. Do not recommend persistent repo actions." \
      "$(collect_staged)"
    ;;
  diff)
    if ! has_code_changes; then
      echo "[local-ai-review] No code changes to review. Skipping."
      exit 0
    fi
    review_payload \
      "diff" \
      "Review this unstaged diff for likely regressions only. Ignore style, naming, formatting, and speculative concerns. Report only issues that would break runtime behavior, tests, data safety, or Socratink workflow safety. For each finding, name the evidence that would verify or refute it. Do not recommend persistent repo actions." \
      "$(collect_diff)"
    ;;
  publish-diff)
    base="${1:-}"
    if [ -z "$base" ]; then
      base="origin/dev"
    fi
    if ! has_code_changes "$base"; then
      echo "[local-ai-review] No code changes to review. Skipping."
      exit 0
    fi
    review_payload \
      "publish-diff" \
      "Review this diff of commits about to be published for behavior-breaking bugs only. Ignore style, naming, formatting, and speculative concerns. Report only issues that would break runtime behavior, tests, data safety, or Socratink workflow safety. For each finding, name the evidence that would verify or refute it. Do not recommend persistent repo actions." \
      "$(git -C "$repo_root" diff "$base...HEAD" --no-ext-diff)"
    ;;
  wip)
    review_payload \
      "wip" \
      "Explain the safest next git action from this Socratink helper output. Treat the helper as the source of truth. Do not recommend persistent repo actions unless the helper output clearly supports them. Prefer one narrow next command and name any blockers." \
      "$(collect_wip)"
    ;;
  publish-preview)
    review_payload \
      "publish-preview" \
      "Review this Socratink publish preview for reasons a human should stop before approving. Do not create, edit, decode, or recommend bypassing any ack token. Do not recommend raw publication commands. Findings only." \
      "$(collect_publish_preview)"
    ;;
  smoke-local)
    review_payload \
      "smoke-local" \
      "Summarize this local smoke-test output. Separate setup failures from app regressions. Name the smallest deterministic verification step. Do not recommend bypassing tests." \
      "$(collect_smoke_local)"
    ;;
  pytest)
    pytest_context="$(collect_pytest "$@")"
    review_payload \
      "pytest" \
      "Summarize this pytest output. Identify the likely root cause and the smallest next debugging step. Do not invent code not shown here and do not recommend bypassing tests." \
      "$pytest_context"
    ;;
  *)
    usage >&2
    fail "unknown mode: $mode"
    ;;
esac
