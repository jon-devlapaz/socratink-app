# Riverflow

Single-repo Git visualizer. Main branch flows left → right; other branches fork as side streams; PRs surface as confluence arcs. CI status surfaces as a small dot on each tip-ish commit. There's also a chat panel powered by Gemini that already knows what you're looking at.

Tinted in the socratink palette — deep indigo page, lavender accent, cream text — so it feels like part of the family without claiming to be a customer surface.

## Run it

```bash
./tools/riverflow/riverflow
```

The launcher auto-detects `OWNER/REPO` from the repo's `origin` remote, auto-detects the main branch, reads tokens from `~/.config/riverflow/`, runs `npm install` once if needed, boots Vite on http://localhost:5180, and opens your browser at the **right edge** (the "now" view) of the river.

First run prompts for a GitHub token. Gemini is optional.

## Tokens

Both live under `~/.config/riverflow/`, both `chmod 600` automatically.

| File              | Purpose          | How to get one                                                  |
| ----------------- | ---------------- | --------------------------------------------------------------- |
| `token`           | GitHub PAT       | https://github.com/settings/tokens — classic, `repo` scope      |
| `gemini-token`    | Gemini API key   | https://aistudio.google.com/apikey                              |

To rotate either: `rm ~/.config/riverflow/<file>` and re-run the launcher.

If `gemini-token` is missing, the chat panel still appears but shows a "no key configured" state. Everything else works.

## Actions

- **Branch** — right-click a commit → name → confirm
- **Open PR** — click a branch label → fill title/body → confirm
- **Merge PR** — click an open (amber, dashed) PR arc → confirm

All merges use a merge commit. No squash, rebase, force-push, or delete.

## Navigation

- **Drag** anywhere on the canvas to pan
- **⌘-scroll** (or Ctrl-scroll on Linux/Win) to zoom, anchored to the cursor
- **+ / − / 1:1** in the topbar are equivalents
- **Click a commit** opens it on github.com
- **`?` in the topbar** opens the gestures cheat sheet

## CI status

Small green / red / amber dot at the upper-right of each commit. Aggregated from `/commits/{sha}/check-runs`:

- green — all check runs `success`
- red — at least one `failure` / `timed_out` / `cancelled`
- amber — at least one still in progress
- no dot — either no CI configured for that commit, or it's not in the refresh window

To stay under GitHub's rate limit, riverflow only refreshes CI for the **last 3 main commits + each branch tip** every poll. Older commits keep whatever CI state was cached on first observation. If a green dot looks stale on an older commit, that's why.

## Chat (optional)

The "chat" toggle in the topbar opens a right-side dock backed by `gemini-2.5-flash`. Every turn ships a fresh snapshot of the current graph as the system prompt — branches with ahead/behind/CI, open and recently-merged PRs, the last 12 main commits — so you can ask "summarize what just landed" or "any branches stale?" without copy-pasting context.

- Thinking is disabled (`thinkingBudget: 0`) for snappy responses on lookup-style questions
- History is capped at the last 20 turns to keep request size sane
- Conversation is **not persisted** — closing the dock clears it on next open

**Privacy**: every turn sends repo metadata (commit messages, branch names, PR titles, author names) to Google. Fine for repos you own. Don't point this at client work without considering whether that's OK.

## Config

| Env var          | Purpose                              |
| ---------------- | ------------------------------------ |
| `GITHUB_TOKEN`   | One-shot override of saved PAT       |
| `GEMINI_API_KEY` | One-shot override of saved chat key  |
| `RIVERFLOW_PORT` | Override port (default `5180`)       |

## Notes

- Polls GitHub every 30s; "refresh" forces an immediate refetch
- 50-commit cap per branch
- Closed-unmerged PRs are hidden by design
- `.env` is regenerated on every launch — don't edit it by hand
- Tokens live client-side in the dev server's `.env`. **Local tool only — do not deploy.**
