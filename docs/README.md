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

Use the founder vault for cross-project operating memory: people, open loops, personal priorities, recurring agent preferences, and observations that are not repo doctrine.

Do not copy canonical Socratink doctrine into the founder vault. Link to the repo docs instead.

## Update Rule

Every meaningful change should answer one question:

> Which canonical memory surface changed?

Valid answers:

- no doc impact
- update [project/state.md](project/state.md)
- update the relevant product or design spec
- add or supersede an ADR
- update [project/doc-map.md](project/doc-map.md)
- archive or redirect a stale doc

Archive history should remain link-valid, but it is not authoritative unless an active doc says so.
