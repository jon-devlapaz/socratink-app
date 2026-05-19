# socratink — Drill Docs Rebuild Note

The previous drill docs were retired because the app changed and the old drill doctrine was no longer trustworthy enough to remain active canon.

Do not use archived drill docs as the source of truth for new implementation decisions.

## Current Binding Truth

Use these surfaces in order:

- [../superpowers/specs/2026-05-15-drill-data-model-design.md](../superpowers/specs/2026-05-15-drill-data-model-design.md) — current binding drill data-model canon: training evidence store, derived states, and rendering contract
- [contract.md](contract.md) — compatibility redirect and short runtime summary
- [../product/evidence-weighted-map.md](../product/evidence-weighted-map.md) — binding doctrine for what the graph may and may not claim
- [../product/spec.md](../product/spec.md) — binding product contract for the three-phase loop, routing, progression layers, panel modes, and guardrails
- [../product/post-drill-ux-spec.md](../product/post-drill-ux-spec.md) — current learner-facing post-phase UX contract
- [../project/state.md](../project/state.md) — current release posture and active risks
- [../project/mvp-happy-path.md](../project/mvp-happy-path.md) — current manual release gate

For runtime evidence, prefer:

- `.qa-runs/browser-ground-truth/` — browser-ground-truth drift evidence
- `logs/drill-runs.jsonl` — current run evidence

## Archived Historical Context

These files are preserved only for historical context:

- [../archive/drill/engineering.md](../archive/drill/engineering.md)
- [../archive/drill/evaluation.md](../archive/drill/evaluation.md)

If a future rebuild wants to recover a useful invariant or eval pattern from them, promote it deliberately into new canon rather than reactivating the archived files.
