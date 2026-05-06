#!/usr/bin/env bash
set -euo pipefail

pids=$(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk '$9 ~ /:800[0-9]$/ {print $2}' | sort -u)

if [[ -z "${pids}" ]]; then
  echo "No listeners on localhost:800*"
  exit 0
fi

echo "Killing PIDs on 800*: ${pids}"
kill ${pids} 2>/dev/null || true
sleep 1

still=$(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk '$9 ~ /:800[0-9]$/ {print $2}' | sort -u)
if [[ -n "${still}" ]]; then
  echo "Force killing: ${still}"
  kill -9 ${still} 2>/dev/null || true
fi

echo "Done."
