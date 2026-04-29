# Docs Registry

Inventory of everything under `docs/`. Classification is durable; status reflects the docs pivot to the evidence-weighted map doctrine.

## Legend

- **canonical** — binding doctrine or contract. Update only through deliberate doc work.
- **implementation** — binding implementation-facing spec. Derived from canonical docs.
- **evidence** — binding release-gate or manual-validation contract (not doctrine).
- **release-gate** — specific ship/merge gate documents.
- **workflow** — repeatable agent or process workflow documents.
- **artifact** — design storyboard or exploratory artifact; informs canonical docs.
- **historical** — preserved for context; not the current source of truth on its topic.
- **deprecated** — superseded; retained only for backward links. Do not cite.

Binding docs MUST be followed. Non-binding docs inform decisions but are not contracts.

## Precedence (Binding)

On any claim about **graph truth, evidence, mastery, completion, diagnostic capability, or what the learner knows**, [docs/product/evidence-weighted-map.md](../product/evidence-weighted-map.md) overrides every other binding doc, including the canonical `spec.md`, `ux-framework.md`, and all implementation-tier specs.

Concretely: if any binding doc below uses legacy shorthand ("verified understanding", "cleared", "mastered", "proved it", "real learning", "possess"), evidence-weighted-map.md §13 (Legacy Shorthand Replacement Table) governs interpretation. Those phrases are UI or copy shorthand — not knowledge claims. Agents must translate them at read time and reject new occurrences at write time.

On all other topics (three-phase loop, four-state model implementation, routing, guardrails, reward/sensory, session caps, auth), the individual binding doc listed below is authoritative.

## Canonical Doctrine

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [/UBIQUITOUS_LANGUAGE.md](../../UBIQUITOUS_LANGUAGE.md) | canonical | yes | Project-wide DDD glossary: binding terms (Graph truth, Recorded evidence, Reconstruction evidence, the four learning-loop states) and explicit Aliases to avoid. Authoritative term list referenced by the Precedence block above. | — |
| [product/evidence-weighted-map.md](../product/evidence-weighted-map.md) | canonical | yes | Defines the evidence-weighted map doctrine, true game loop, starting-map-as-anchor, map-maturity language, and graph-claim rules. Overrides other docs on graph-truth claims. | — |
| [product/spec.md](../product/spec.md) | canonical | yes | Binding product contract: three-phase loop, four-state model, panel modes, traversal, guardrails, evaluation checklist. | — |
| [product/ux-framework.md](../product/ux-framework.md) | canonical | yes | Metacognitive UX philosophy, reward/sensory rules, attribution management, session guardrails, ethical engagement boundary. | — |
| [theta/state.md](../theta/state.md) | canonical | yes | Evidence posture and confidence ratings for product-science claims; phase grounding; product language rules. | — |

## Implementation-Facing Specs

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [product/progressive-disclosure.md](../product/progressive-disclosure.md) | implementation | yes | Four-state model implementation spec: state transitions, persisted fields, phase tracking, drill contract, routing, progression layers, session guardrails, target happy path. | — |
| [product/post-drill-ux-spec.md](../product/post-drill-ux-spec.md) | implementation | yes | Post-phase panel copy, result-state visuals, sensory treatment, transcript policy, tier/band trajectory display. | — |
| [drill/engineering.md](../drill/engineering.md) | implementation | yes | Hard engineering invariants for drill/graph state coherence; pre-change checklist. | — |
| [drill/evaluation.md](../drill/evaluation.md) | evidence | yes | Manual eval set, answer modes, obvious-break checklist, evidence capture for the thermostat loop. | — |
| [product/repair-reps.md](../product/repair-reps.md) | implementation | yes | Unified implementation spec for Repair Reps (focused layout, card-stack visuals, self-rating evidence schema). | — |
| [project/auth-rollout.md](auth-rollout.md) | implementation | yes | Auth rollout phases, release gates, test plan, deferred work. | — |

## Artifacts (Design Storyboards)

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [product/starting-map-flow-artifact.md](../product/starting-map-flow-artifact.md) | artifact | no | Storyboard for the starting-map concept-entry flow. Informs `evidence-weighted-map.md` §11 and future canonical/implementation work. Not itself an implementation contract. | Operational rules live in [evidence-weighted-map.md](../product/evidence-weighted-map.md). |

## Release Gates & Evidence

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [project/state.md](state.md) | release-gate | yes | Current release gate, stage, priorities, active risks, product constraints. `socratinker` consolidates this. | — |
| [project/mvp-happy-path.md](mvp-happy-path.md) | release-gate | yes | Narrow manual ship gate for the thermostat loop. | — |
| [project/operations.md](operations.md) | release-gate | yes | Merge standard, release checks, evidence policy, near-term priorities. | — |

## Workflow & Agent Infra

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [codex/onboarding.md](../codex/onboarding.md) | workflow | yes | Canonical bootstrap for new Socratink coding sessions. | — |
| [codex/workflows.md](../codex/workflows.md) | workflow | yes | Hot-fix, Build-Measure-Learn, decision-log, and Glenna review workflows. | — |
| [codex/drill-build-measure-learn.md](../codex/drill-build-measure-learn.md) | workflow | yes | Drill log → Socratink Brain evaluation → fix cycle. | — |
| [codex/socratink-brain-workflow-architecture.md](../codex/socratink-brain-workflow-architecture.md) | deprecated | no | Stub pointing to authoritative `.socratink-brain/CLAUDE.md`. | `.socratink-brain/CLAUDE.md` |
| [codex/decision-log.md](../codex/decision-log.md) | workflow | yes | Append-only architectural/product decision log. Empty template at time of writing. | — |
| [codex/agent-review-log.md](../codex/agent-review-log.md) | workflow | yes | Append-only Glenna review log. | — |
| [superpowers/plans/2026-04-28-pipette.md](../superpowers/plans/2026-04-28-pipette.md) | workflow | yes | Load-bearing operational plan and slash-command definitions for the Pipette subsystem. | — |
| [superpowers/specs/2026-04-28-pipette-design.md](../superpowers/specs/2026-04-28-pipette-design.md) | workflow | yes | Architecture and CLI interface spec for the Pipette orchestration subsystem. | — |

## Reference Fixtures

| Path | Status | Binding | Purpose |
| --- | --- | --- | --- |
| `docs/reference/example-extraction-output.json` | reference | no | Sample extraction output for prompts and testing. Not a contract. |
| `docs/reference/hermes-agent-concept-source.md` | reference | no | Compressed Socratink-ready source for creating a Hermes Agent documentation concept. Derived from public Nous Research Hermes Agent docs and kept under the current extraction input limit. |
| `docs/reference/hermes-agent-docs-manifest.md` | reference | no | Full manifest of upstream Hermes Agent documentation pages, source paths, raw URLs, sizes, and headings used to build the compressed Hermes concept source. |

## Historical / Deprecated Notes

- **`docs/codex/session-bootstrap.md`** — deprecated alias. All bootstrap reads should resolve to `docs/codex/onboarding.md`. Do not add new content here.
- No other docs are currently deprecated. Items flagged as stale during the evidence-weighted-map pivot are updated in place (see `evidence-weighted-map.md` for the binding doctrine and surgical edits to the canonical docs in this registry).

## Lean-Startup Consolidation Candidates (Post-MVP)

None of these are dead. They are load-bearing for the feature they describe. They are listed here because they will create drift risk as MVP stabilization progresses and should be consolidated once current release work is stable. Do not consolidate during an active release gate.

- **`docs/product/starting-map-flow-artifact.md`** — design storyboard. Once the threshold flow is built, operational rules should move to a canonical `starting-map.md`; the artifact should be marked historical at that point.

If a new doc is added during MVP work, register it here with `binding: yes` or `binding: no` and add it to this consolidation list if it duplicates or refines an existing binding doc.

## Registry Maintenance

- When a new doc is added under `docs/`, register it here with status, binding flag, and purpose.
- When a doc becomes superseded, flip status to `historical` or `deprecated` and fill the "Superseded By" column. Do not delete.
- When doctrine shifts, the canonical doc that now governs must be referenced from this registry so readers find the current source of truth.
