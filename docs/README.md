# Socratink Docs Vault

This folder can be opened as an Obsidian vault, but Git remains the source of truth.

Start here:

- [project/doc-map.md](project/doc-map.md) — canonical doc registry and precedence rules
- [project/state.md](project/state.md) — current release posture and active risks
- [product/evidence-weighted-map.md](product/evidence-weighted-map.md) — binding graph-truth doctrine
- [product/spec.md](product/spec.md) — binding product contract
- [adr/README.md](adr/README.md) — architecture decision log

## Memory Boundary

Use this repo vault for Socratink truth: product doctrine, architecture decisions, implementation contracts, release state, and agent instructions that must travel with the code.

Use the in-repo agent surfaces for shared workflow truth: [agents/README.md](../agents/README.md) for the boundary contract, [agents/LEARNINGS.md](../agents/LEARNINGS.md) for the learning ledger, and [agents/founder/WORKFLOWS/](../agents/founder/WORKFLOWS/) for founder workflow cards.

Use the founder vault for cross-project operating memory: people, open loops, personal priorities, recurring agent preferences, and observations that are not repo doctrine.

Do not copy canonical doctrine into the founder vault — link to the repository docs ([agents/README.md](../agents/README.md), [agents/LEARNINGS.md](../agents/LEARNINGS.md), [agents/founder/WORKFLOWS/](../agents/founder/WORKFLOWS/)).

## Update Rule

Every meaningful change should answer one question:

> Which canonical memory surface changed?

Valid answers:

- no doc impact
- update exactly one canonical document: [project/state.md](project/state.md), an ADR, the relevant product/design spec, or [project/doc-map.md](project/doc-map.md)
- delete stale working material after migrating any durable rule into canon

Git history is the archive for deleted working notes, research prompts, dated QA
plans, and implementation handoffs.
