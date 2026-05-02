# ADR-0001 — `ProvisionalMap` as a typed cognitive artifact contract

**Status:** Accepted (2026-05-01)
**Driver:** [foundation design spec, §5.1](../superpowers/specs/2026-05-01-foundation-design.md), PR #76

## Context

The MVP path produces a **Provisional map** (per [UBIQUITOUS_LANGUAGE.md](../../UBIQUITOUS_LANGUAGE.md): "a map shaped by starting-map input but still carrying no graph-truth mutation"). Every downstream stage — Cold attempt, Targeted study, Repair Reps, Spaced re-drill — consumes the map as a graph of mechanisms, identifiers, and relationships. If the map's structural integrity is broken, the brittleness propagates invisibly and surfaces as bad UX much later (a Cold attempt on a node that doesn't exist; a Repair Rep referencing a missing cluster).

Before this PR, `extract_knowledge_map` returned a `dict` and validated only that `metadata`/`backbone`/`clusters` were the right top-level types. There were no checks that subnodes lived in their declared cluster, that backbone references resolved, that learning-prerequisite edges formed a DAG, or that identifiers matched the grammar the prompt asked for. Pre-PR there were also zero unit tests for the function.

## Decision

The MVP map is a typed Pydantic model — `models.ProvisionalMap` — and that model is the contract between extraction and every downstream consumer. Its shape mirrors `app_prompts/extract-system-v1.txt` exactly. Application code holds `ProvisionalMap` instances; the wire shape (`dict`) is produced only at the route boundary via `.model_dump()`.

The model enforces structural integrity at parse time:

- Identifier grammar (`b<N>`, `c<N>`, `c<N>_s<M>`, `core-thesis`) via `models.identifiers.parse_id`.
- Reference closure: every backbone `dependent_clusters` references an existing cluster; every cluster is covered by ≥ 1 backbone (BACKBONE COVERAGE RULE); every cluster has ≥ 1 subnode (MINIMUM DRILLABILITY RULE); every subnode lives in its declared cluster; relationship endpoints exist; framework `source_clusters` resolve.
- Acyclicity: learning prerequisites form a DAG (no self-loops, no reciprocals, DFS cycle check).

The route maps any `ValueError` raised by these validators to HTTP 422 — the structural shape is wrong, retrying won't help.

`extra="forbid"` is intentionally **not** set. Pydantic emits `additionalProperties: false` in the JSON Schema when `extra="forbid"` is configured, and Gemini's `response_schema` parameter rejects schemas containing it. Field-level correctness is governed by the prompt + the closure validators above. See `_parse_repair_reps_response` in `ai_service.py` for the same precedent.

## Alternatives

- **Keep the `dict` shape and add a separate validator function.** Considered and rejected: validation would be a separate step downstream code could forget to invoke. Pydantic at the boundary is enforcement-by-construction.
- **Strict `extra="forbid"` with a parallel "loose" schema for Gemini export.** Considered and rejected for v1 — adds a dual-class dance (the same one `_parse_repair_reps_response` already does for repair-reps). Worth revisiting if Gemini starts producing extra fields that we want loud rejection on.
- **Quality-floor knobs** (≥ N nodes, ≥ M clusters per backbone) on the model. Considered and rejected: that is the prompt's job. If the prompt produces thin maps, fix the prompt; the schema is for *structural* integrity, not content quality.

## Consequences

- **Catches breakage at extraction time, not three steps later.** A malformed map fails at parse, surfacing as a 422 with a specific validator message instead of a Cold attempt UX bug.
- **Downstream code that previously walked dicts must update.** `scripts/run_tasting_fixture.py` was updated to call `.model_dump()` after extraction; future internal callers must either consume `ProvisionalMap` directly (preferred) or do the same.
- **Wire shape preserved.** Route handlers call `.model_dump()` so frontend consumers see the same JSON they always did.
- **Schema is bound to one prompt version.** When `app_prompts/extract-system-v1.txt` changes shape, `ProvisionalMap` must change alongside it. Prompts and schemas version together; this ADR doesn't formalize the registry yet (deferred — see spec §5.4).
