# Handoff: Code Review Graph Hook Hardening

**Context:** The `code-review-graph` (CRG) is currently integrated via `.claude/settings.example.json` (Claude Code hooks), which updates the graph when the agent edits files. However, it relies on manual rebuilds when humans pull code, switch branches, or rebase. 

**Objective:** Implement native Git hooks and enhance the Claude hooks so the Code Review Graph and its HTML visualization stay 100% synchronized automatically, regardless of whether a human or an agent makes the change.

Please implement the following robust hook architecture:

## 1. Native Git Hooks (in `scripts/git-hooks/`)
The graph needs to respond to Git operations so it stays fresh when developers pull from `main`, rebase, or commit.

Create or update the following hooks in `scripts/git-hooks/`:
*   **`post-merge`**: Run `code-review-graph update &` (in the background so it doesn't block the `git pull`).
*   **`post-rewrite`**: (Fires after rebase). Run `code-review-graph build &` (full rebuild is safer after a rebase).
*   **`post-commit`**: Run `code-review-graph update &`.
*   **`post-checkout`**: Update the existing `post-checkout` script to append `code-review-graph build &` when a branch changes (`flag=1`), ensuring a fresh graph when jumping between feature branches.

*Crucial Constraint for Git Hooks:* Wrap the CRG commands in a check to ensure `code-review-graph` is actually installed (e.g., `if command -v code-review-graph >/dev/null 2>&1; then ...`). Swallow output or direct to `/dev/null` so it doesn't spam the terminal.

## 2. Hook Registration
Ensure developers actually use these hooks.
*   Update `scripts/bootstrap-python.sh` (or the relevant setup script) to include:
    `git config core.hooksPath scripts/git-hooks`
    This ensures all developers share the same Git hook behaviors without manual symlinking.

## 3. Enhanced Claude Settings (`.claude/settings.example.json`)
The current `.claude/settings.example.json` covers `Edit|Write|Bash`. 
*   **Missing Tools:** Add `Replace` and `ApplyPatch` to the `PostToolUse` matcher so the graph updates when the agent uses those specific file-editing tools.
*   **Visualizer Auto-Sync:** Add a background execution of `python3 scripts/build_code_graph_viz.py` to the `EnterWorktree` hook (and possibly the `SessionStart` hook) so the `docs/code-graph.html` constellation visualization is regenerated automatically alongside the graph rebuild.

## 4. Verification
After implementing, verify that:
1. Making a commit updates the graph.
2. Checking out a new branch triggers a graph build.
3. The visualizer HTML updates seamlessly.
4. If `code-review-graph` is uninstalled or not in the PATH, the git hooks fail gracefully without breaking standard Git operations.

---
**Execution:** Please execute this plan directly. Prioritize the Git hooks as they provide the widest safety net for team synchronization.