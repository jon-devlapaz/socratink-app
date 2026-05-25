# Docs Registry

This is the intentionally small map of docs that still earn a place in the repo.
If a file is not listed here or reachable from one listed here, treat it as
non-canonical working material.

For an agent-crawler index see [`/llms.txt`](../../llms.txt).

## Entry Points

- [`docs/README.md`](../README.md) - docs-vault front door and memory boundary
- [`/PRODUCT.md`](../../PRODUCT.md) - strategic product brief
- [`/DESIGN.md`](../../DESIGN.md) - product/design hub, primitives, voice, and boundaries
- [`/AGENTS.md`](../../AGENTS.md) - agent ops canon, commands, conventions, git workflow
- [`/UBIQUITOUS_LANGUAGE.md`](../../UBIQUITOUS_LANGUAGE.md) - canonical terms and aliases to avoid
- [`docs/project/state.md`](state.md) - current release posture and active risks

## Precedence

On any claim about **graph truth, evidence, mastery, completion, diagnostic
capability, or what the learner knows**,
[`product/evidence-weighted-map.md`](../product/evidence-weighted-map.md)
overrides every other binding doc, including `DESIGN.md`, `spec.md`, and
implementation-tier specs. Legacy knowledge/completion shorthand falls under
its §14 Legacy Shorthand Replacement Table.

On all other topics, the doc listed below for that topic is authoritative.

## Canonical Docs

| Topic | Doc |
| --- | --- |
| Product contract: loop, routing, progression layers, inline modes, guardrails | [`docs/product/spec.md`](../product/spec.md) |
| Evidence-weighted graph doctrine | [`docs/product/evidence-weighted-map.md`](../product/evidence-weighted-map.md) |
| Post-drill result-surface UX | [`docs/product/post-drill-ux-spec.md`](../product/post-drill-ux-spec.md) |
| Founder mental model | [`docs/product/test-driven-learning.md`](../product/test-driven-learning.md) |
| Full UX manifesto and voice rationale | [`docs/design/socratink-ux.md`](../design/socratink-ux.md) |
| Drill data model, training evidence, derivation math, rendering fields | [`docs/superpowers/specs/2026-05-15-drill-data-model-design.md`](../superpowers/specs/2026-05-15-drill-data-model-design.md) |
| Architectural decisions | [`docs/adr/README.md`](../adr/README.md) |

## Maintenance

- Open `docs/` as an Obsidian vault only as a navigation layer. Git and this
  registry remain authoritative.
- Do not add working plans, QA prompts, research notes, implementation handoffs,
  generated artifacts, or deprecated redirects under `docs/`.
- If a temporary note matters long-term, promote only its durable rule into the
  relevant canonical doc above. Otherwise rely on git history.
- When doctrine shifts, update the authoritative doc first; this registry follows.
