# Architecture Decision Records

This directory holds the binding architectural decisions for socratink-app. Each ADR records: a decision that was made, the context that forced it, the alternatives we considered, and the consequences we have to live with.

## When to write a new ADR

Write one when:

- A decision shapes how new code in some area MUST be written, and that "must" can't be inferred from reading the code itself.
- A decision is non-obvious enough that a contributor (or a future agent) might re-litigate it without context.
- A decision rules out an alternative for a load-bearing reason that would otherwise be invisible.

Don't write one for:

- Vocabulary — that lives in [UBIQUITOUS_LANGUAGE.md](../../UBIQUITOUS_LANGUAGE.md).
- Style preferences without an architectural blast radius.
- Working notes — those go in `docs/superpowers/specs/`.

## Format

Each ADR is a markdown file numbered sequentially: `NNNN-short-slug.md`. Format:

- **Status**: Accepted / Superseded by ADR-XXXX / Proposed
- **Context**: What forced the decision. Cite code locations, prior incidents, or product constraints.
- **Decision**: What we are doing. Use the present tense — "we use X" not "we will use X."
- **Alternatives**: Other options we considered, and why they lost.
- **Consequences**: What this decision now costs or constrains. Both positive and negative.

Keep them short. Link to the spec / plan / commits that drove the decision rather than re-explaining context.

## Index

- [ADR-0001 — `ProvisionalMap` as a typed cognitive artifact contract](0001-provisional-map-typed-contract.md)
- [ADR-0002 — LLM provider lives behind a seam; application asks for cognitive artifacts](0002-llm-seam.md)
- [ADR-0003 — Retry contract is encoded in the type system via `RetriableLLMError`](0003-retriable-error-marker.md)
