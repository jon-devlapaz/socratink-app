# Docs Registry
This is the intentionally small map of docs that still earn a place in this repo.
If a file is not listed here or reachable from one listed here, treat it as
non-canonical working material.

For an agent-crawler index see [`/llms.txt`](../../llms.txt).

## Entry Points
- [`docs/project/doc-map.md`](doc-map.md) - docs-vault front door and memory boundary
- [`docs/product/north-star.md`](../product/north-star.md) - canonical product doctrine
- [`/AGENTS.md`](../../AGENTS.md) - agent ops canon, commands, and conventions
- [`/PRODUCT.md`](../../PRODUCT.md) - implementation contract derived from the north star
- [`/DESIGN.md`](../../DESIGN.md) - product/design hub, primitives, voice, and boundaries
- [`/UBIQUITOUS_LANGUAGE.md`](../../UBIQUITOUS_LANGUAGE.md) - canonical terms and aliases to avoid
- [`docs/.obsidian/app.json`](../.obsidian/app.json) - Obsidian vault link config

## Precedence
- With the pruned docs cleanup, there is currently no in-tree `docs/` replacement for
  the former product/spec or evidence docs. Use the canonical repo-level docs above
  as the current authority, and add a dedicated in-tree docs file before reintroducing
  those references.
- On all other topics, use the file listed as the top-level canonical source for that
  topic in this registry.

## Canonical Docs

| Topic | Doc |
| --- | --- |
| Product north star / doctrine | [`docs/product/north-star.md`](../product/north-star.md) |

## Maintenance
- Open `docs/` as an Obsidian vault only as a navigation layer. Git and this registry
  remain authoritative.
- Do not add working plans, QA prompts, research notes, implementation handoffs,
  generated artifacts, or deprecated redirects under `docs/`.
- If a temporary note matters long-term, promote only its durable rule into the relevant
  canonical doc above. Otherwise rely on git history.
- When doctrine shifts, update the authoritative doc first; this registry follows.
- This map was intentionally pruned to match currently checked-in files in this branch.
