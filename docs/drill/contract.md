# socratink — Drill Contract

This document is a compatibility redirect. The current binding drill data-model
contract is:

- [../superpowers/specs/2026-05-15-drill-data-model-design.md](../superpowers/specs/2026-05-15-drill-data-model-design.md)

Use that spec before changing drill evidence persistence, node-state derivation,
study reveal behavior, repair records, concept-page drill UI, or Library evidence
rendering. It supersedes this file on every point of disagreement.

## Current Runtime Contract

- Training evidence is stored separately from the provisional graph in
  browser-local records keyed as `socratink:training:v1:<conceptId>`.
- Node state is derived from training records at render time:
  `null | primed | needs repair | solidified`.
- `null` means no learner reconstruction evidence is on record for the node.
- `primed` means learner reconstruction evidence exists and study/repair/review
  routing is derived from that evidence.
- `needs repair` means the current evidence has named gaps that require repair.
- `solidified` requires spaced strong reconstruction evidence; study or reading
  alone cannot produce it.
- Library renders learner-authored reconstruction text only. It must not fall
  back to AI-generated graph summaries as proof of reconstruction.

For graph-truth doctrine, read [../product/evidence-weighted-map.md](../product/evidence-weighted-map.md).
For the broader product contract, read [../product/spec.md](../product/spec.md).
For learner-facing post-phase UX, read [../product/post-drill-ux-spec.md](../product/post-drill-ux-spec.md).
