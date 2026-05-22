#!/usr/bin/env bash
# share-lab.sh — expose one static public/_lab prototype through a temporary URL.
#
# Usage:
#   scripts/share-lab.sh minimal-gestalt-overview
#   scripts/share-lab.sh concept-overview-variants.html
#   scripts/share-lab.sh _lab/minimal-gestalt-overview.html --port 8010
#   scripts/share-lab.sh --list
#
# This serves only the repo's public/ directory via a loopback static server,
# then opens an ngrok tunnel to that static server. It does not expose the
# FastAPI dev app or local auth/session endpoints.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC_DIR="$ROOT/public"
LAB_DIR="$PUBLIC_DIR/_lab"
PORT=8010
TARGET=""

usage() {
  sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
}

list_surfaces() {
  if [[ ! -d "$LAB_DIR" ]]; then
    echo "share-lab.sh: no public/_lab directory found." >&2
    exit 2
  fi
  find "$LAB_DIR" -maxdepth 1 -type f -name '*.html' -print \
    | sed "s#^$LAB_DIR/##; s#\\.html\$##" \
    | sort
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --list)
      list_surfaces
      exit 0
      ;;
    --port)
      if [[ $# -lt 2 || ! "$2" =~ ^[0-9]+$ ]]; then
        echo "share-lab.sh: --port requires a numeric port." >&2
        exit 2
      fi
      PORT="$2"
      shift 2
      ;;
    -*)
      echo "share-lab.sh: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "$TARGET" ]]; then
        echo "share-lab.sh: expected one target, got extra argument: $1" >&2
        exit 2
      fi
      TARGET="$1"
      shift
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "share-lab.sh: target is required." >&2
  echo "  try: scripts/share-lab.sh --list" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "share-lab.sh: python3 not found in PATH." >&2
  exit 127
fi
if ! command -v ngrok >/dev/null 2>&1; then
  echo "share-lab.sh: ngrok not found in PATH." >&2
  echo "  install ngrok, then authenticate it before using this script." >&2
  exit 127
fi

normalize_target() {
  local raw="$1"
  while true; do
    case "$raw" in
      ./public/*) raw="${raw#./public/}" ;;
      public/*) raw="${raw#public/}" ;;
      /_lab/*) raw="${raw#/_lab/}" ;;
      _lab/*) raw="${raw#_lab/}" ;;
      /*) raw="${raw#/}" ;;
      *) break ;;
    esac
  done
  raw="${raw%.html}"
  if [[ -z "$raw" || "$raw" == */ || "$raw" == *'//'* ]]; then
    echo "share-lab.sh: invalid _lab target: $1" >&2
    exit 2
  fi
  local segment
  local -a segments
  IFS='/' read -r -a segments <<< "$raw"
  for segment in "${segments[@]}"; do
    if [[ -z "$segment" || "$segment" == "." || "$segment" == ".." ]]; then
      echo "share-lab.sh: invalid _lab target: $1" >&2
      exit 2
    fi
  done
  printf '/_lab/%s.html' "$raw"
}

TARGET_PATH="$(normalize_target "$TARGET")"
LOCAL_FILE="$PUBLIC_DIR${TARGET_PATH}"

if [[ ! -f "$LOCAL_FILE" ]]; then
  echo "share-lab.sh: no prototype found at public${TARGET_PATH}" >&2
  echo "available _lab surfaces:" >&2
  list_surfaces | sed 's/^/  - /' >&2
  exit 2
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "share-lab.sh: port $PORT is already in use." >&2
  echo "  pass another port: scripts/share-lab.sh $TARGET --port 8011" >&2
  exit 3
fi
STATIC_PID=""
NGROK_PID=""
cleanup() {
  if [[ -n "$NGROK_PID" ]] && kill -0 "$NGROK_PID" >/dev/null 2>&1; then
    kill "$NGROK_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$STATIC_PID" ]] && kill -0 "$STATIC_PID" >/dev/null 2>&1; then
    kill "$STATIC_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$PUBLIC_DIR" >/tmp/socratink-share-lab-http.log 2>&1 &
STATIC_PID="$!"

for _ in {1..30}; do
  if curl -fsS "http://127.0.0.1:$PORT$TARGET_PATH" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

if ! curl -fsS "http://127.0.0.1:$PORT$TARGET_PATH" >/dev/null 2>&1; then
  echo "share-lab.sh: static server did not start on 127.0.0.1:$PORT." >&2
  echo "  log: /tmp/socratink-share-lab-http.log" >&2
  exit 4
fi

NGROK_LOG="/tmp/socratink-share-lab-ngrok.log"
: > "$NGROK_LOG"
ngrok http "$PORT" --log=stdout >"$NGROK_LOG" 2>&1 &
NGROK_PID="$!"

PUBLIC_URL=""
for _ in {1..80}; do
  if ! kill -0 "$NGROK_PID" >/dev/null 2>&1; then
    break
  fi
  PUBLIC_URL="$(sed -n 's/.*url=\(https:\/\/[^ ]*\).*/\1/p' "$NGROK_LOG" | tail -1)"
  if [[ -n "$PUBLIC_URL" ]]; then
    break
  fi
  sleep 0.25
done

if [[ -z "$PUBLIC_URL" ]]; then
  echo "share-lab.sh: ngrok did not publish a URL." >&2
  echo "  log: /tmp/socratink-share-lab-ngrok.log" >&2
  exit 5
fi

PHONE_URL="${PUBLIC_URL}${TARGET_PATH}"

cat <<EOF
share-lab.sh
local:  http://127.0.0.1:${PORT}${TARGET_PATH}
phone:  ${PHONE_URL}

Serving only: ${PUBLIC_DIR}
Tunnel stays open while this command runs. Press Ctrl-C to stop.
EOF

# Keep the script alive and surface tunnel logs if ngrok exits.
wait "$NGROK_PID"
