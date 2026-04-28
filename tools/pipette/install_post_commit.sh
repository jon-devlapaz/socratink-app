#!/usr/bin/env bash
# Idempotent + non-destructive installer for the /graphify post-commit hook.
# Refuses to clobber existing user hooks; surfaces a clear error instead.
set -euo pipefail
HOOK=".git/hooks/post-commit"
SENTINEL="# pipette-graphify v1"

if [[ -f "$HOOK" ]]; then
  if grep -q "$SENTINEL" "$HOOK"; then
    echo "post-commit /graphify hook already present"
    exit 0
  fi
  echo "ERROR: $HOOK exists and does not contain the pipette-graphify sentinel." >&2
  echo "Refusing to overwrite. Inspect the existing hook and either:" >&2
  echo "  1. Append these lines manually:" >&2
  echo "       $SENTINEL" >&2
  echo "       exec code-review-graph update >/dev/null 2>&1 || true" >&2
  echo "  2. Remove $HOOK and re-run this installer." >&2
  exit 1
fi

cat > "$HOOK" <<EOF
#!/usr/bin/env bash
$SENTINEL
# /graphify — keep the code-review-graph fresh on every committed snapshot.
# Belt-and-suspenders with .claude/settings.json PostToolUse update.
exec code-review-graph update >/dev/null 2>&1 || true
EOF
chmod +x "$HOOK"
echo "installed $HOOK"
