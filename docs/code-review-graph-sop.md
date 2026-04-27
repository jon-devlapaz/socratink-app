# code-review-graph SOP

How to use the knowledge graph in this repo. For agents, the rules also live in
`CLAUDE.md` and `.claude/skills/`. This is the human-readable companion.

## What the graph is

[`code-review-graph`](https://github.com/tirth8205/code-review-graph) (MIT) parses this repo with
Tree-sitter and stores a structural graph in `.code-review-graph/graph.db` (SQLite, WAL mode).
Nodes: files, classes, functions, tests. Edges: CALLS, IMPORTS_FROM, INHERITS,
CONTAINS, TESTED_BY, REFERENCES. The agent queries it via MCP instead of scanning
files — far fewer tokens, with structural context (callers, dependents, coverage).

Current shape: ~870 nodes, ~7,100 edges across 50 files (Python + JavaScript).

## How it stays fresh

Hooks in `.claude/settings.json` keep the graph in sync automatically. You should
not need to run anything by hand.

> `.claude/settings.json` is gitignored (per-developer). The team baseline is
> committed at [`.claude/settings.example.json`](../.claude/settings.example.json) —
> copy it on first checkout and add any personal hooks (linters, formatters, etc.)
> on top.

| Event | Hook | What runs |
|---|---|---|
| SessionStart | every new session | `code-review-graph status` (header + last-update) |
| PostToolUse: `Edit\|Write\|Bash` | after every file mutation | `code-review-graph update --skip-flows` (incremental) |
| PostToolUse: `EnterWorktree` | when a fresh worktree is created | `code-review-graph build` (full, synchronous, 60s timeout) |

`EnterWorktree → build` runs synchronously to avoid racing with the incremental
`update` that PostToolUse fires on the first edit in a worktree.

## The token-efficiency contract

Three rules. Apply them every time you (or the agent) reach for the graph.

1. **Start with `get_minimal_context_tool(task="…")`.** ~100 tokens of risk +
   communities + flows + suggested next tools. Replaces the usual 3-4 separate
   `list_*` calls.
2. **Default to `detail_level="minimal"`.** Escalate to `"standard"` only when
   minimal is genuinely insufficient.
3. **Prefer targeted `query_graph(target=…)`** over broad `list_*` when the
   target is known.

**Floor caveat:** the graph under-reports CALLS counts in some cases. For "only
call site" claims, hand-grep with `rg "<symbol>"` before asserting.

## Skills (slash-invokable workflows)

Project skills under `.claude/skills/` codify the standard graph workflows.
Invoke by name or by saying what you want.

| Skill | Trigger | What it does |
|---|---|---|
| `review-changes` | "review my changes" | risk-scored review of working-tree diff |
| `explore-codebase` | open-ended "where is X" / "how does Y work" | minimal-context → architecture → narrowed search |
| `debug-issue` | "debug this bug" | semantic search → trace callers/callees → flows |
| `refactor-safely` | "rename X" / "find dead code" | preview via `refactor_tool` then apply |
| `review` | "/review" | the project's broader review (correctness, MVP-blocker classification, TODO follow-ups). Uses graph data when available |

## Decision tree — graph or grep?

Before using `Grep` / `Glob` / `Read`, ask: does the graph already cover this?

```
"Where is symbol X?"           → semantic_search_nodes_tool(query="X", detail_level="minimal")
"What calls X?"                → query_graph_tool(pattern="callers_of",   target="X")
"What does X call?"            → query_graph_tool(pattern="callees_of",   target="X")
"What imports module X?"       → query_graph_tool(pattern="importers_of", target="X")
"What tests X?"                → query_graph_tool(pattern="tests_for",    target="X")
"What's in file X?"            → query_graph_tool(pattern="file_summary", target="X")
"Blast radius of changing X?"  → get_impact_radius_tool(target="X")
"Which flows touch X?"         → get_affected_flows_tool
"What changed and is it safe?" → detect_changes_tool
"Big-picture architecture?"    → get_architecture_overview_tool
"Source snippets for review?"  → get_review_context_tool   (NOT Read whole files)
"Functions over N lines?"      → find_large_functions_tool
```

Fall back to `Grep`/`Glob`/`Read` only when the graph genuinely doesn't cover what
you need. The floor caveat is the canonical exception.

## Visualization

Constellation viz of the graph:

```
python3 scripts/build_code_graph_viz.py
open docs/code-graph.html
```

The script reads `.code-review-graph/graph.db` directly and emits a single
self-contained HTML (D3 force layout, communities color-coded). Re-run any time
the graph rebuilds.

## Troubleshooting

### `database is locked`

SQLite WAL handles concurrent reads, but two writers will collide. The most
common cause: a long-running `build` while a hook fires `update`. Wait a few
seconds and retry. If it persists, check for orphaned `code-review-graph`
processes:

```bash
ps aux | grep code-review-graph | grep -v grep
```

Kill stragglers (`kill <pid>`) and retry.

### Stale graph / missing nodes

If the graph looks out of date or a node you expect is missing, force a full
rebuild:

```bash
code-review-graph status              # confirm last_updated
code-review-graph build               # full re-parse (also runs on EnterWorktree)
```

### Nuclear reset

If the DB is corrupted or in an inconsistent state:

```bash
code-review-graph clean               # delete .code-review-graph/graph.db
code-review-graph build               # rebuild from scratch
```

This is safe — the DB is a derived artifact, regenerated from source. It's
gitignored.

### Fresh worktree

`EnterWorktree → build` should fire automatically. If it didn't (timeout, hook
not picked up):

```bash
cd <worktree-path>
code-review-graph build
```

## Tool reference (24 MCP tools)

Grouped by use case. Token cost rises roughly top-to-bottom in each group.

**First call (always):**
- `get_minimal_context_tool` — ~100 tokens, risk + flows + next-tool suggestions
- `list_graph_stats_tool` — node/edge/file counts

**Review / impact:**
- `detect_changes_tool` — risk-scored diff vs HEAD
- `get_review_context_tool` — token-efficient source snippets
- `get_impact_radius_tool` — blast radius of a change
- `get_affected_flows_tool` — flows touched by changes

**Exploration:**
- `semantic_search_nodes_tool` — find by name/keyword (uses vectors if embedded)
- `query_graph_tool` — patterns: callers_of, callees_of, imports_of, importers_of, children_of, tests_for, inheritors_of, file_summary
- `get_architecture_overview_tool` — community-based architecture map
- `list_communities_tool` / `get_community_tool`
- `list_flows_tool` / `get_flow_tool`
- `find_large_functions_tool` — hygiene scan

**Refactor:**
- `refactor_tool` (modes: suggest, dead_code, rename) — preview only
- `apply_refactor_tool` — apply a previewed rename

**Wiki / docs:**
- `generate_wiki_tool` / `get_wiki_page_tool` — auto-generated community docs in `.code-review-graph/wiki/`

**Build:**
- `build_or_update_graph_tool` / `run_postprocess_tool`

**Optional / opt-in:**
- `embed_graph_tool` — compute vector embeddings (requires `pip install code-review-graph[embeddings]`). Once embedded, `semantic_search_nodes_tool` automatically uses vector similarity.

## What we deliberately don't use

- **Multi-repo registry** (`list_repos_tool`, `cross_repo_search_tool`) — socratink-app is a single repo. Skip unless we register a sibling like `.socratink-brain` for cross-graph queries.
- **Embeddings** — keyword + FTS5 search is enough at 50 files. Revisit if semantic search starts missing things.

## Upstream

Repo: <https://github.com/tirth8205/code-review-graph>
Docs: <https://code-review-graph.com>
License: MIT.
