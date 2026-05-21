#!/usr/bin/env bash
# Read-only local AI reviewer for Socratink workflow artifacts.

set -euo pipefail

DEEPSEEK_LOCAL_BIN="${DEEPSEEK_LOCAL_BIN:-/Users/jondev/bin/deepseek-local}"
MAX_BYTES="${LOCAL_AI_REVIEW_MAX_BYTES:-81920}"

fail() {
  echo "[local-ai-review] ERROR: $*" >&2
  exit 2
}

usage() {
  cat <<'EOF'
Usage:
  scripts/local-ai-review.sh check
  scripts/local-ai-review.sh staged
  scripts/local-ai-review.sh diff
  scripts/local-ai-review.sh wip
  scripts/local-ai-review.sh publish-preview
  scripts/local-ai-review.sh smoke-local
  scripts/local-ai-review.sh pytest -- <pytest command>

Read-only advisory wrapper around /Users/jondev/bin/deepseek-local.
It uses canned prompts, refuses likely secrets, caps payload size, and never
performs persistent repo actions.
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
    http://127.0.0.1:*|https://127.0.0.1:*|127.0.0.1:*|http://localhost:*|https://localhost:*|localhost:*)
      return 0
      ;;
    *)
      fail "refusing broad OLLAMA_HOST=${host}; use 127.0.0.1 or localhost for local AI review"
      ;;
  esac
}

require_helper() {
  [ -x "$DEEPSEEK_LOCAL_BIN" ] || fail "DeepSeek helper is not executable: $DEEPSEEK_LOCAL_BIN"
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
  printf '%s' "$payload" | "$DEEPSEEK_LOCAL_BIN"
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
  "$@" 2>&1
}

ensure_local_ollama_host
require_helper

case "$mode" in
  check)
    run_check
    ;;
  staged)
    review_payload \
      "staged" \
      "Review this staged diff for behavior-breaking bugs only. Ignore style, naming, formatting, and speculative concerns. Report only issues that would break runtime behavior, tests, data safety, or Socratink workflow safety. For each finding, name the evidence that would verify or refute it. Do not recommend persistent repo actions." \
      "$(collect_staged)"
    ;;
  diff)
    review_payload \
      "diff" \
      "Review this unstaged diff for likely regressions only. Ignore style, naming, formatting, and speculative concerns. Report only issues that would break runtime behavior, tests, data safety, or Socratink workflow safety. For each finding, name the evidence that would verify or refute it. Do not recommend persistent repo actions." \
      "$(collect_diff)"
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
    review_payload \
      "pytest" \
      "Summarize this pytest output. Identify the likely root cause and the smallest next debugging step. Do not invent code not shown here and do not recommend bypassing tests." \
      "$(collect_pytest "$@")"
    ;;
  *)
    usage >&2
    fail "unknown mode: $mode"
    ;;
esac
