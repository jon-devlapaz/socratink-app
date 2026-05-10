#!/usr/bin/env bash
# persona.sh — pipe a customer-persona prompt to Gemini and stream the answer.
#
# Usage:
#   scripts/persona.sh <prompt-file>     # read from a file
#   cat prompt.txt | scripts/persona.sh  # read from stdin
#   scripts/persona.sh --template        # print the template path and exit
#
# Filters Gemini CLI's noisy "Discarding invalid hook definition" startup
# blocks, and tees the result to a timestamped log under .playwright-mcp/
# so you don't lose the response if the terminal scrolls.
#
# Methodology lives in docs/codex/customer-persona-prompt-template.md —
# this script is the runner, not the template.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$ROOT/docs/codex/customer-persona-prompt-template.md"
LOG_DIR="$ROOT/.playwright-mcp"

if [[ "${1:-}" == "--template" ]]; then
  echo "$TEMPLATE"
  exit 0
fi
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
fi

if ! command -v gemini >/dev/null 2>&1; then
  echo "persona.sh: gemini CLI not found in PATH." >&2
  echo "  install via your package manager or:" >&2
  echo "    npm install -g @google/gemini-cli" >&2
  echo "  then run:  gemini auth login" >&2
  exit 127
fi

# Resolve input source.
if [[ $# -ge 1 ]]; then
  if [[ ! -r "$1" ]]; then
    echo "persona.sh: cannot read prompt file: $1" >&2
    exit 2
  fi
  INPUT_SRC="$1"
else
  if [[ -t 0 ]]; then
    echo "persona.sh: no prompt file given and stdin is a TTY." >&2
    echo "  usage:  scripts/persona.sh <prompt-file>" >&2
    echo "          cat prompt.txt | scripts/persona.sh" >&2
    echo "  template lives at: $TEMPLATE" >&2
    exit 2
  fi
  INPUT_SRC="-"
fi

# Read prompt up-front so we can both log it and pipe it.
if [[ "$INPUT_SRC" == "-" ]]; then
  PROMPT_TEXT="$(cat)"
else
  PROMPT_TEXT="$(cat "$INPUT_SRC")"
fi

# Cheap shape check — warn (not fail) if the prompt looks empty or doesn't
# carry a persona block. The persona template's distinguishing marker is
# "You are " on its own line; we don't enforce it, just nudge.
if [[ -z "${PROMPT_TEXT// /}" ]]; then
  echo "persona.sh: prompt is empty." >&2
  exit 2
fi
if ! grep -q "^You are " <<<"$PROMPT_TEXT"; then
  echo "persona.sh: heads up — prompt doesn't start with a 'You are ...'" >&2
  echo "  persona block. Gemini will still answer but the persona may drift." >&2
  echo "  template:  $TEMPLATE" >&2
  echo "" >&2
fi

mkdir -p "$LOG_DIR"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_PATH="$LOG_DIR/persona-$TS.txt"

# Run gemini, filter the noise, tee to both stdout and the log.
{
  echo "# persona.sh run $TS"
  echo "# input: ${INPUT_SRC/-/<stdin>}"
  echo "# ---"
  printf '%s\n' "$PROMPT_TEXT" | gemini --approval-mode plan 2>&1 | awk '
    /^Discarding invalid hook/ { skip = 1; next }
    skip && /^}/               { skip = 0; next }
    skip                       { next }
    /^Ripgrep is not available/ { next }
    { print }
  '
} | tee "$LOG_PATH"

echo "" >&2
echo "persona.sh: response logged to ${LOG_PATH#$ROOT/}" >&2
