#!/usr/bin/env bash
# Reinstall git hooks for this repo.
# Run after fresh clone or if .git/hooks is wiped.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
hooks_dir="$repo_root/.git/hooks"
mkdir -p "$hooks_dir"

cat > "$hooks_dir/pre-commit" <<'HOOK'
#!/bin/sh
# Block commits containing git conflict markers (stash-pop / merge / rebase residue).
# Reinstall via scripts/install-hooks.sh if .git is recreated.

files=$(git diff --cached --name-only --diff-filter=AM)
if [ -n "$files" ]; then
    hits=""
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        nums=$(git diff --cached --numstat -- "$f" 2>/dev/null | awk '{print $1, $2}')
        case "$nums" in
            "- "*|*" -") continue ;;
        esac
        match=$(git show ":$f" 2>/dev/null | grep -nE '^(<{7}|>{7}|={7})( |$)' || true)
        if [ -n "$match" ]; then
            hits="$hits
--- $f ---
$match"
        fi
    done <<EOF
$files
EOF

    if [ -n "$hits" ]; then
        echo "Commit blocked: git conflict markers found in staged content."
        printf '%s\n' "$hits"
        echo ""
        echo "Resolve markers before committing."
        echo "To bypass (NOT recommended), use: git commit --no-verify"
        exit 1
    fi
fi

if command -v code-review-graph >/dev/null 2>&1; then
    code-review-graph detect-changes --brief || true
fi
HOOK

chmod +x "$hooks_dir/pre-commit"
echo "Installed: $hooks_dir/pre-commit"
