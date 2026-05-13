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

On any claim about **graph truth, evidence, mastery, completion, diagnostic capability, or what the learner knows**, [docs/product/evidence-weighted-map.md](../product/evidence-weighted-map.md) overrides every other binding doc, including the canonical `spec.md`, `/DESIGN.md`, and all implementation-tier specs.

Concretely: if any binding doc below uses legacy shorthand ("verified understanding", "cleared", "mastered", "proved it", "real learning", "possess"), evidence-weighted-map.md §13 (Legacy Shorthand Replacement Table) governs interpretation. Those phrases are UI or copy shorthand — not knowledge claims. Agents must translate them at read time and reject new occurrences at write time.

On all other topics (three-phase loop, four-state model implementation, routing, guardrails, reward/sensory, session caps, auth), the individual binding doc listed below is authoritative.

## Canonical Doctrine

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [/DESIGN.md](../../DESIGN.md) | canonical | yes | The canonical UX doctrine: unifying metaphor, metacognitive happy path, state claims, session guardrails, AI contracts, and ethical engagement. | — |
| [/UBIQUITOUS_LANGUAGE.md](../../UBIQUITOUS_LANGUAGE.md) | canonical | yes | Project-wide DDD glossary: binding terms (Graph truth, Recorded evidence, Reconstruction evidence, the four learning-loop states) and explicit Aliases to avoid. Authoritative term list referenced by the Precedence block above. | — |
| [/CONTEXT.md](../../CONTEXT.md) | canonical | yes | Domain glossary for terms whose meaning shapes a specific surface (e.g. Library). Canonical for the surface-level terms it defines; complements `/UBIQUITOUS_LANGUAGE.md` (which governs cross-cutting graph/loop vocabulary). If code or copy disagrees with this file, the code or copy is wrong. | — |
| [product/evidence-weighted-map.md](../product/evidence-weighted-map.md) | canonical | yes | Defines the evidence-weighted map doctrine, true game loop, starting-map-as-anchor, map-maturity language, and graph-claim rules. Overrides other docs on graph-truth claims. | — |
| [product/spec.md](../product/spec.md) | canonical | yes | Binding product contract: three-phase loop, four-state model, panel modes, traversal, guardrails, evaluation checklist. | — |
| [archive/product/ux-framework.md](../archive/product/ux-framework.md) | historical | no | Former metacognitive UX philosophy doc. Archived after consolidation into `/DESIGN.md`; keep only for historical reference. | [/DESIGN.md](../../DESIGN.md) |
| [/PRODUCT.md](../../PRODUCT.md) | deprecated | no | Brand personality, anti-references, product purpose, design principles. | [/DESIGN.md](../../DESIGN.md) |
| [project/theta-state.md](theta-state.md) | canonical | yes | Evidence posture and confidence ratings for product-science claims; phase grounding; product language rules. | — |

## Implementation-Facing Specs

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [product/progressive-disclosure.md](../product/progressive-disclosure.md) | implementation | yes | Four-state model implementation spec: state transitions, persisted fields, phase tracking, drill contract, routing, progression layers, session guardrails, target happy path. | — |
| [product/post-drill-ux-spec.md](../product/post-drill-ux-spec.md) | implementation | yes | Post-phase panel copy, result-state visuals, sensory treatment, transcript policy, tier/band trajectory display. | — |
| [drill/engineering.md](../drill/engineering.md) | implementation | yes | Hard engineering invariants for drill/graph state coherence; pre-change checklist. | — |
| [drill/evaluation.md](../drill/evaluation.md) | evidence | yes | Manual eval set, answer modes, obvious-break checklist, evidence capture for the thermostat loop. | — |
| [product/repair-reps.md](../product/repair-reps.md) | implementation | yes | Unified implementation spec for Repair Reps (focused layout, card-stack visuals, self-rating evidence schema). | — |
| [project/auth-rollout.md](auth-rollout.md) | implementation | yes | Auth rollout phases, release gates, test plan, deferred work. | — |
| [design/handoffs/2026-05-02-extraction-evals-and-rubric.md](../design/handoffs/2026-05-02-extraction-evals-and-rubric.md) | implementation | yes | Evaluation rubric and rubrics for extraction quality. | — |
| [design/handoffs/2026-05-04-conversational-concept-creation-frontend.md](../design/handoffs/2026-05-04-conversational-concept-creation-frontend.md) | historical | no | Conversational concept creation frontend implementation (Threshold composer / Starting sketch flow). Deprecated 2026-05-07; the surface it described has been replaced by the Door + Launch Pad flow. | [design/handoffs/2026-05-07-progressive-route-materialization-agent-brief.md](../design/handoffs/2026-05-07-progressive-route-materialization-agent-brief.md) |
| [design/handoffs/2026-05-05-desk-iso-board-handoff.md](../design/handoffs/2026-05-05-desk-iso-board-handoff.md) | implementation | yes | Desk isometric board implementation handoff. | — |
| [design/handoffs/2026-05-07-progressive-route-materialization-agent-brief.md](../design/handoffs/2026-05-07-progressive-route-materialization-agent-brief.md) | implementation | yes | Agent brief for C-prime concept entry: progressive disclosure for learners, progressive route materialization, source/no-source contracts, and implementation guardrails. | — |

## Artifacts (Design Storyboards)

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [product/starting-map-flow-artifact.md](../product/starting-map-flow-artifact.md) | artifact | no | Storyboard for the starting-map concept-entry flow. Informs `evidence-weighted-map.md` §11 and future canonical/implementation work. Not itself an implementation contract. | Operational rules live in [evidence-weighted-map.md](../product/evidence-weighted-map.md). |
| [design/handoffs/2026-05-01-new-concept-modal-redesign.md](../design/handoffs/2026-05-01-new-concept-modal-redesign.md) | artifact | no | Design storyboard for the new concept modal. | — |
| [product/landing-page-brief.md](../product/landing-page-brief.md) | artifact | no | Strategic brief for the Socratink landing page. | — |

## Release Gates & Evidence

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [project/state.md](state.md) | release-gate | yes | Current release gate, stage, priorities, active risks, product constraints. `socratinker` consolidates this. | — |
| [project/mvp-happy-path.md](mvp-happy-path.md) | release-gate | yes | Narrow manual ship gate for the thermostat loop. | — |
| [project/operations.md](operations.md) | release-gate | yes | Merge standard, release checks, evidence policy, near-term priorities. | — |
| [qa/antigravity-mobile-qa-prompt.md](../qa/antigravity-mobile-qa-prompt.md) | release-gate | yes | Mobile layout regression audit prompt and checklist. | — |
| [qa/2026-05-07-c-prime-antigravity-qa-plan.md](../qa/2026-05-07-c-prime-antigravity-qa-plan.md) | release-gate | yes | Browser QA plan for C-prime concept entry (Door + Launch Pad). Antigravity-runnable test cases and breakfix report. | — |
| [qa/2026-05-07-c-prime-shipgate-verifications.md](../qa/2026-05-07-c-prime-shipgate-verifications.md) | release-gate | yes | C-prime ship-gate verifications: server-side bypass guard and persistence-then-clear ordering under failure injection. | — |
| [qa/2026-05-11-mvp-browser-test.md](../qa/2026-05-11-mvp-browser-test.md) | release-gate | yes | Pre-merge browser QA prompt for the Gemini-3-Pro MVP gate: end-to-end Socratic-loop walkthrough with evidence-capture rules. | — |

## Workflow & Agent Infra

| Doc | Status | Binding | Purpose | Superseded By |
| --- | --- | --- | --- | --- |
| [/agents/README.md](../../agents/README.md) | workflow | yes | Canonical boundary for shared model-agnostic agent workflow truth. | — |
| [/agents/LEARNINGS.md](../../agents/LEARNINGS.md) | workflow | no | Non-binding ledger for recurring founder/agent workflow observations; entries become binding only after promotion into canonical docs. | — |
| [/agents/MIGRATION.md](../../agents/MIGRATION.md) | workflow | yes | Migration ledger for promoting tool-specific agent surfaces into the shared canon. | — |
| [/agents/_templates/learning-entry.md](../../agents/_templates/learning-entry.md) | workflow | yes | Fixed schema for entries in the non-binding workflow learning ledger. | — |
| [/agents/_templates/workflow-card.md](../../agents/_templates/workflow-card.md) | workflow | yes | Fixed schema for future workflow cards. | — |
| [/agents/founder/README.md](../../agents/founder/README.md) | workflow | no | Founder-facing orientation map for `agents/founder/`; summarizes canonical surfaces without redefining policy. | — |
| [/agents/founder/WORKFLOWS/01-git-integration.md](../../agents/founder/WORKFLOWS/01-git-integration.md) | workflow | yes | Founder git publication workflow: push routing, confirmation boundaries, and v1 enforcement scope. | — |
| [/agents/founder/WORKFLOWS/02-git-homeostasis.md](../../agents/founder/WORKFLOWS/02-git-homeostasis.md) | workflow | yes | Founder branch-homeostasis workflow: survey, classify, salvage, archive, and converge back to the intended `main + dev` shape. | — |
| [/agents/founder/WORKFLOWS/03-prototyping.md](../../agents/founder/WORKFLOWS/03-prototyping.md) | workflow | yes | Founder prototyping workflow: choose logic/state vs UI/copy prototype shape, keep it throwaway, and capture only the answer durably. | — |
| [/agents/founder/WORKFLOWS/04-deploy-verification.md](../../agents/founder/WORKFLOWS/04-deploy-verification.md) | workflow | yes | Founder deploy-verification workflow: wait for the intended production deployment, run smoke only after success, and report deploy status distinctly from smoke status. | — |
| [/agents/founder/trusted-remotes.json](../../agents/founder/trusted-remotes.json) | workflow | yes | Trusted remote URL pattern config for the founder git publication workflow. | — |
| [/agents/ONBOARDING.md](../../agents/ONBOARDING.md) | workflow | yes | Canonical bootstrap for new Socratink coding sessions. | — |
| [/agents/QUALITY.md](../../agents/QUALITY.md) | workflow | yes | Deterministic agent behavior, source-of-truth rules, and product-truth guardrails. | — |
| [/agents/WORKFLOWS/README.md](../../agents/WORKFLOWS/README.md) | workflow | yes | Shared hot-fix, Build-Measure-Learn, decision-log, and Glenna review workflows. | — |
| [/agents/WORKFLOWS/drill-build-measure-learn.md](../../agents/WORKFLOWS/drill-build-measure-learn.md) | workflow | yes | Drill log → Socratink Brain evaluation → fix cycle. | — |
| [/agents/_logs/decision-log.md](../../agents/_logs/decision-log.md) | workflow | yes | Append-only architectural and product decision log. | — |
| [/agents/_logs/agent-review-log.md](../../agents/_logs/agent-review-log.md) | workflow | yes | Append-only Glenna review log. | — |
| [/agents/_templates/customer-persona-prompt.md](../../agents/_templates/customer-persona-prompt.md) | workflow | yes | Reusable customer-persona prompt template used by `scripts/persona.sh` and persona-driven copy or UX evaluations. | — |
| [archive/project/2026-05-09-settings-toggle-handoff.md](../archive/project/2026-05-09-settings-toggle-handoff.md) | historical | no | Point-in-time Codex handoff for a settings toggle fix. Preserved only as historical context. | — |
| [project/code-review-graph-sop.md](code-review-graph-sop.md) | workflow | yes | Standard operating procedure for using the Code-Review Graph. | — |
| [archive/project/crg-hooks-handoff.md](../archive/project/crg-hooks-handoff.md) | historical | no | Historical implementation handoff for CRG hook hardening. The live truth is the current hooks plus `project/code-review-graph-sop.md`. | [project/code-review-graph-sop.md](code-review-graph-sop.md) |
| [/agents/founder/CODE-REVIEW-GRAPH-FAQ.md](../../agents/founder/CODE-REVIEW-GRAPH-FAQ.md) | workflow | no | Founder-facing CRG FAQ. Plain-language guidance that complements the technical SOP without redefining policy. | — |

## Reference Fixtures

| Path | Status | Binding | Purpose |
| --- | --- | --- | --- |
| `docs/reference/example-extraction-output.json` | reference | no | Sample extraction output for prompts and testing. Not a contract. |
| [archive/reference/extraction-catalog.md](../archive/reference/extraction-catalog.md) | historical | no | Historical extraction-phase inventory. Convenience only; not part of active bootstrap or binding contracts. |
| [archive/project/crg-architecture-snapshot-2026-05-04.md](../archive/project/crg-architecture-snapshot-2026-05-04.md) | historical | no | Stale point-in-time CRG architecture snapshot. Preserved only as historical context, not active orientation. |

## Historical / Deprecated Notes

- **`docs/product/ux-framework.md`** — archived. Consolidated into `/DESIGN.md` as the canonical UX doctrine.
- **`docs/archive/naming-refactor/`** — historical project phase documentation.
- No other docs are currently deprecated. Items flagged as stale during the evidence-weighted-map pivot are updated in place (see `evidence-weighted-map.md` for the binding doctrine and surgical edits to the canonical docs in this registry).

## Lean-Startup Consolidation Candidates (Post-MVP)

None of these are dead. They are load-bearing for the feature they describe. They are listed here because they will create drift risk as MVP stabilization progresses and should be consolidated once current release work is stable. Do not consolidate during an active release gate.

- **`docs/product/starting-map-flow-artifact.md`** — design storyboard. Once the threshold flow is built, operational rules should move to a canonical `starting-map.md`; the artifact should be marked historical at that point.

If a new doc is added during MVP work, register it here with `binding: yes` or `binding: no` and add it to this consolidation list if it duplicates or refines an existing binding doc.

## Registry Maintenance

- When a new doc is added under `docs/`, register it here with status, binding flag, and purpose.
- When a doc becomes superseded, flip status to `historical` or `deprecated` and fill the "Superseded By" column. Do not delete.
- When doctrine shifts, the canonical doc that now governs must be referenced from this registry so readers find the current source of truth.
