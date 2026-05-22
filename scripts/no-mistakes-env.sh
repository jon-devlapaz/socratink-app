#!/usr/bin/env bash

_no_mistakes_generate_session_key() {
  local python_bin="${PYTHON_BIN:-python}"
  if ! command -v "$python_bin" >/dev/null 2>&1; then
    python_bin="python3"
  fi
  "$python_bin" -c 'import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
}

export AUTH_ENABLED="${AUTH_ENABLED:-true}"
export SUPABASE_URL="${SUPABASE_URL:-https://example.supabase.co}"
export SUPABASE_PUBLISHABLE_KEY="${SUPABASE_PUBLISHABLE_KEY:-dummy-publishable-key}"
export SUPABASE_JWT_SECRET="${SUPABASE_JWT_SECRET:-dummy-jwt-secret}"
export APP_BASE_URL="${APP_BASE_URL:-http://localhost:8000}"
export SOCRATINK_BASE_URL="${SOCRATINK_BASE_URL:-http://localhost:8000}"
export SOCRATINK_DEV_AUTOGUEST="${SOCRATINK_DEV_AUTOGUEST:-0}"
export SOCRATINK_E2E_LOCAL_GUEST="${SOCRATINK_E2E_LOCAL_GUEST:-1}"
export GEMINI_API_KEY="${GEMINI_API_KEY:-dummy-for-tests}"
export GITHUB_ACTIONS="${GITHUB_ACTIONS:-true}"

if [ -z "${SESSION_COOKIE_KEY:-}" ]; then
  export SESSION_COOKIE_KEY="$(_no_mistakes_generate_session_key)"
else
  export SESSION_COOKIE_KEY
fi
