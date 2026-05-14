# Docs Registry

Canonical entry points first; deep specs and ephemera below. For an agent-crawler index see [`/llms.txt`](../../llms.txt).

## Entry points

- [`/DESIGN.md`](../../DESIGN.md) — canonical product/design hub (intent, decisions, primitives, voice, boundaries)
- [`/AGENTS.md`](../../AGENTS.md) — agent ops canon (commands, conventions, git workflow)
- [`/UBIQUITOUS_LANGUAGE.md`](../../UBIQUITOUS_LANGUAGE.md) — canonical domain terms and aliases-to-avoid
- [`/PRODUCT.md`](../../PRODUCT.md) — strategic product brief (users, purpose, brand posture, non-goals)

## Precedence

On any claim about **graph truth, evidence, mastery, completion, diagnostic capability, or what the learner knows**, [`product/evidence-weighted-map.md`](../product/evidence-weighted-map.md) overrides every other binding doc — including `DESIGN.md`, `spec.md`, and all implementation-tier specs. Legacy shorthand ("verified understanding", "cleared", "mastered") falls under its §13 Legacy Shorthand Replacement Table.

On all other topics, the doc listed below for that topic is authoritative.

## Canonical deep-dives

| Topic | Doc |
| --- | --- |
| Full UX manifesto (prose source for DESIGN.md §§3–6) | [`docs/design/socratink-ux.md`](../design/socratink-ux.md) |
| Design system component rules | [`docs/design/socratink-design-system.md`](../design/socratink-design-system.md) |
| Product spec (three-phase loop, panel modes, guardrails) | [`docs/product/spec.md`](../product/spec.md) |
| Evidence-weighted map doctrine | [`docs/product/evidence-weighted-map.md`](../product/evidence-weighted-map.md) |
| ADR index (append-only architectural decisions) | [`docs/adr/README.md`](../adr/README.md) |
| Theta-state (evidence posture for product-science claims) | [`docs/project/theta-state.md`](theta-state.md) |

## Implementation-facing specs

| Topic | Doc |
| --- | --- |
| Four-state model implementation | [`docs/product/progressive-disclosure.md`](../product/progressive-disclosure.md) |
| Post-drill panel UX | [`docs/product/post-drill-ux-spec.md`](../product/post-drill-ux-spec.md) |
| Drill contract | [`docs/drill/contract.md`](../drill/contract.md) |
| Repair Reps | [`docs/product/repair-reps.md`](../product/repair-reps.md) |
| Auth rollout | [`docs/project/auth-rollout.md`](auth-rollout.md) |

## Release gates

- [`docs/project/state.md`](state.md) — current release gate
- [`docs/project/mvp-happy-path.md`](mvp-happy-path.md) — narrow MVP ship gate
- [`docs/project/operations.md`](operations.md) — merge standard and release checks
- [`docs/qa/2026-05-11-mvp-browser-test.md`](../qa/2026-05-11-mvp-browser-test.md) — current pre-merge browser QA
- [`docs/qa/antigravity-mobile-qa-prompt.md`](../qa/antigravity-mobile-qa-prompt.md) — mobile regression audit

## Agent infra

See [`agents/README.md`](../../agents/README.md) for the canonical workflow hub. Founder workflows in `agents/founder/WORKFLOWS/`.

## Archive

Ephemeral handoffs and dated QA plans live under [`docs/archive/`](../archive/). Older handoffs from 2026-05-01..07 moved during the 2026-05 design-md refactor.

## Maintenance

- When a new doc is added under `docs/`, list it here under the right section.
- When a doc becomes superseded, `git mv` it under `docs/archive/<date-context>/`. Don't delete.
- When doctrine shifts, update DESIGN.md §4 first; the registry follows.
