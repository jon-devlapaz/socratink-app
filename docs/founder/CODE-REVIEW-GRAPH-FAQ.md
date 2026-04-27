# Code Review Graph — Founder FAQ

A founder-facing guide to using the code-review-graph (CRG) on socratink-app.
Plain-language. For the agent-facing technical runbook (hooks, tool reference,
troubleshooting), see [`docs/code-review-graph-sop.md`](../code-review-graph-sop.md).

---

## What is it, in one sentence?

A persistent map of every function, class, call, and test in this codebase that
Claude Code reads instead of scanning files — so it (and you) can answer
"where does X live / what depends on Y / is this risky" in seconds, without
burning tokens or guessing.

## What kind of memory is it (and isn't it)?

It's **structural code memory** — facts about the code as it exists right now.
It is *not* a substitute for any of these:

| Memory type | Where it lives | What I keep there |
|---|---|---|
| Why we did it that way | commits, decision docs, auto-memory feedback notes | rationale, constraints, past corrections |
| Past sessions / conversations | `episodic-memory` | what we discussed before |
| Tasks & follow-ups | `tink-todo` / `todo.md` | next actions |
| **Code structure** | **CRG** | **what's connected to what, what's covered, what flows where** |

When I confuse these I waste time. CRG only knows what it can parse from code —
treat it that way.

---

## The three habits worth building

If I do nothing else, these three change how a session feels:

### 1. Start every session by asking for context, not by searching

When I open a session and don't know where I left off, before reading anything I
ask Claude to call `get_minimal_context_tool`. ~100 tokens, returns the top
risks, the major communities, the critical flows, and a suggested next step.

> Try this prompt: *"Give me a minimal-context catch-up on this repo."*

### 2. Search before I build

Anytime I'm about to write a helper, a util, a parser, a wrapper — search the
graph first. The graph knows every function in this repo by name and keyword.
Most "let me write X" moments have an answer already in the codebase that I
forgot existed.

> Try this prompt: *"Search the graph for anything related to <thing> before I
> write a new helper."*

### 3. Check blast radius before I touch anything load-bearing

Before editing a function that gets called in many places (drill chat,
hero actions, auth, the graph board), ask for its impact radius. The graph
returns every caller, dependent, and test. I see the cost of the change before
I make it.

> Try this prompt: *"What's the blast radius of changing `<symbol>`? Include
> tests."*

---

## When do I use it?

### Every session
- "Where am I, what's risky?" → minimal-context catch-up.
- "What changed since last commit?" → risk-scored diff (`detect_changes_tool`).
- "Is this thing tested?" → tests-for query.

### Before a PR or merge
- The `/review` skill already wires this in. Run it before merging anything
  non-trivial. It produces a blast-radius table + coverage gaps + recommendation.

### When something feels off
- "Why is this slow / weird / brittle?" → trace callers and callees of the
  suspect symbol; check recent changes; look at the affected flow.

### Monthly hygiene (if I remember)
- "Anything ballooning?" → `find_large_functions_tool`.
- "Any dead code?" → `refactor_tool` in dead-code mode (always cross-check
  with `rg` before deleting — see Floor Caveat below).
- "Any new high-coupling between communities?" → architecture overview.

### When I'm coming back to a feature after weeks
- "What's the canonical flow through `runHeroAction` / `selectTile` / etc.?" →
  flow tool. Faster than re-reading the code.

---

## Common questions

### Q: I keep writing little helpers I'm pretty sure I've written before. How does this stop that?

Ask Claude to `semantic_search_nodes_tool` with a keyword from the helper's
purpose ("rate limiter", "token sanitiser", "drill timer"). If it exists, you
get the file and line. If it doesn't, you write it knowing for sure.

This is the single highest-value memory pattern. The 10-second search beats
the 10-minute duplicate every time.

### Q: I'm about to refactor something. How do I know what I'll break?

Two graph calls:

1. `get_impact_radius_tool` on the symbol → all callers + dependents.
2. `query_graph_tool(pattern="tests_for", target="<symbol>")` → existing
   coverage.

If coverage is thin or impact is wide, write a test first or split the change.

### Q: How do I get a "table of contents" for this codebase?

Two options:

1. **Communities** — `list_communities_tool` returns the major modules detected
   automatically (here: `js-node`, `tests-session`, `auth-auth`,
   `socratink-app-drill`, `scripts-summary`, `socratink-app-request`). Then drill
   in with `get_community_tool`.
2. **Flows** — `list_flows_tool` returns the main user-journey call chains
   sorted by criticality (here, top flows are `selectTile`, `runHeroAction`,
   `toggleTheme`, `importLibraryConcept`).

When you've been away from the code for a while, communities + flows is faster
than any README.

### Q: Can I see this visually?

Yes. The constellation viz:

```bash
python3 scripts/build_code_graph_viz.py
open docs/code-graph.html
```

Communities are colored, node size = degree, edges = call/import relationships.
Hover, click to lock, drag, zoom. Regenerate any time the graph rebuilds.
The HTML is gitignored — it's a generated artifact.

### Q: I want fresh architecture docs without writing any. Can the graph give me that?

```bash
code-review-graph wiki
```

Generates one markdown page per detected community into
`.code-review-graph/wiki/`. Treat as discardable / regen-able. Don't hand-edit.

### Q: I have a vague feeling something's wrong. Where do I start?

1. `detect_changes_tool` — anything risky in recent edits?
2. `get_architecture_overview_tool` — coupling warnings?
3. `find_large_functions_tool` — anything ballooning?

If all three come back clean, the problem is probably not structural — it's
behavioural, and the graph won't see it. Time to read code or run tests.

### Q: How do I know if it's lying to me?

The most common failure mode: **CALLS counts under-report.** If the graph says
"this is the only call site of X," that may not be true. Always confirm with
`rg "<symbol>"` before acting on uniqueness claims. This is the **floor
caveat** — the graph's count is a floor, not a ceiling.

Beyond that, if results feel stale, run `code-review-graph status` to see when
the graph last updated. If it's outdated, run `code-review-graph build` to
force a full rebuild.

### Q: My agent isn't using the graph even though it should be.

Check three things:

1. `cat .mcp.json` — is the `code-review-graph` server registered?
2. `cat .claude/settings.json` — are the hooks present? (Compare to
   `.claude/settings.example.json` for the team baseline.)
3. Open a fresh session and ask: *"Run `code-review-graph status`."*
   If it errors, the server isn't running. Restart Claude Code.

### Q: I work in worktrees a lot. Does the graph travel with them?

Each worktree gets its own `.code-review-graph/graph.db`. The
`EnterWorktree → build` hook builds a fresh graph automatically when you spin
up a new one. First build takes ~10s for this repo size. After that,
incremental updates are sub-second.

### Q: It feels like overkill for a 50-file repo. Should I bother?

Honestly — for the smallest tasks, no. For tiny edits, just edit. The graph
earns its keep when:
- I'm about to make a change with non-obvious blast radius
- I'm orienting after time away
- I'm reviewing a PR I didn't write
- I'm pretty sure I've solved this problem before but can't remember where

If those scenarios are rare for you on a given day, skip it. It's not religion.

---

## Copy-paste prompts

Things I can drop into a Claude Code prompt verbatim:

```
Catch me up: minimal context, top risks, suggested next step.

What's the blast radius of changing <symbol>? Include tests and flows.

Search the graph for anything related to <topic> before I write a new helper.

Detect changes since HEAD. Risk-score them. Flag untested high-risk changes.

Walk me through the flow named <flow_name>. Step by step.

What community does <symbol> live in? Show me the others in the same community.

Find functions over 100 lines. Suggest decomposition candidates.

Generate the wiki and tell me which community page is most out of sync with my mental model.
```

---

## What CRG can't help with (and where to go instead)

| If I want to remember… | Use |
|---|---|
| Why I made a decision | git log + commit message; or auto-memory feedback |
| What we discussed last week | `episodic-memory` |
| Pending follow-ups | `tink-todo` / `todo.md` |
| Product or design rationale | `docs/product/`, `docs/design/`, `docs/drill/`, etc. |
| Customer / market context | not in this repo at all |
| Anything visual or experiential | screenshots, recordings — graph won't see them |

Don't try to make CRG hold these. It can't, and the attempt corrupts what it's
actually good at.

---

## Maintenance — the three commands I might actually run myself

```bash
code-review-graph status         # is the graph fresh? when did it last update?
code-review-graph build          # force a full rebuild (use when something feels off)
code-review-graph clean && code-review-graph build  # nuclear reset (rare)
```

For everything else (DB locks, stale flows, missing nodes), see the
[technical SOP](../code-review-graph-sop.md#troubleshooting).

---

## TL;DR

- **CRG is structural code memory.** Use it for facts about the code, not for
  decisions or context.
- **Three habits:** start with minimal context, search before building, check
  blast radius before changing.
- **The floor caveat:** graph counts are a floor — `rg` before claiming
  "only call site."
- **The constellation viz** (`docs/code-graph.html`) is a recall aid — use it
  when re-orienting after time away.
- **Don't push it past its boundary.** Decisions, conversations, follow-ups,
  product context — those have their own systems.
