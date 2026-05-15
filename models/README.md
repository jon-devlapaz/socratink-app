# models/

Provisional-map data model. The shape every part of the pipeline (extract,
draft, drill, repair-reps) reads and writes. Pydantic-backed; the `parsed`
field of every `StructuredLLMResult` from the extract stage is an instance
of `ProvisionalMap`.

## Public surface

Import from `models` directly.

| Export | What it is |
| :--- | :--- |
| `ProvisionalMap` | The top-level container. `metadata`, `backbone`, `clusters`, `relationships`, `learning_prereqs`, `frameworks`, `domain_mechanics`. |
| `BackboneItem` | A backbone principle (causal spine of the domain). |
| `Cluster` | A cluster of related subnodes around a backbone item. |
| `Subnode` | A leaf concept. |
| `Relationships` | Edges between nodes. |
| `LearningPrereq` | A directed prerequisite edge. |
| `Framework` | A reusable analytical lens. |
| `DomainMechanic` | A domain-specific causal mechanism. |
| `Metadata` | Map-level provenance (source, model, run id). |
| `BackboneId`, `ClusterId`, `SubnodeId` | Strongly-typed identifier wrappers (NewType-style). |
| `IdKind`, `parse_id(s)` | Identifier kind tag + parser that returns the right ID class given a raw string. |
| `CORE_THESIS` | The reserved identifier for the map's core thesis node. Used by drill routing. |
| `is_substantive_sketch(text)` | Pure-function gate: does this sketch carry enough learner signal to seed source-less map generation? |
| `HelpRequestReason`, `infer_help_request_reason(text)` / `has_substantive_attempt(text)` | Cold-attempt intent classifiers (help request vs genuine generative commitment) plus the Literal tag they return. |
| `RepairRep`, `RepairRepsEvaluation`, `RepairRepsResult` | Repair Reps response contracts; graph-neutral typed micro-practice, not graph-truth mutation. |
| `parse_repair_reps_response(response)` | Strict parser for provider responses; rejects extra routing/scoring fields before returning the loose Gemini-compatible schema. |
| `validate_repair_reps_result(evaluation, expected_count=...)` | Post-parse validation for exact count, non-empty ids/prompts/bridges/cues, and duplicate ids. |

## Files

| File | Role |
| :--- | :--- |
| `provisional_map.py` | Pydantic models for the full map structure. |
| `identifiers.py` | ID types, `IdKind`, `parse_id`, `CORE_THESIS`. |
| `drill_attempts.py` | Pure cold-attempt intent classifiers used before drill scoring/routing normalization. |
| `sketch_validation.py` | `is_substantive_sketch` heuristic (stopwords, min substantive tokens). |
| `knowledge_map_context.py` | Wire-shape validators and target-local context pruning used by drill and Repair Reps routes. |
| `repair_reps.py` | Repair Reps response models, strict parsing, and result validation. |

## Footguns

- **`CORE_THESIS` is a reserved identifier**, not a backbone item like the
  others. Drill routing and the graph view both special-case it. If you
  rename it you will break the drill state machine.
- **Identifier types are not interchangeable.** `BackboneId`, `ClusterId`,
  and `SubnodeId` look like strings but the type system separates them.
  Use `parse_id()` when you have a raw string of unknown kind; do not
  cast directly.
- **`is_substantive_sketch` is deliberately simple.** It exists to reject
  empty/"i don't know" responses, not to grade content quality. Don't
  make it smarter — the principle ("preserve learner effort, reject only
  evidence of no effort") is documented in the module docstring and
  reinforced in feedback memory `feedback_screen_foundation_principles.md`.
- **Pydantic v2 semantics.** All models are Pydantic v2 (`BaseModel`,
  `ConfigDict`). v1 patterns (`@validator`, `Config` class) do not work.
- **There is a current defensive `if text is None` check in
  `sketch_validation.py:115`** against a `str`-typed parameter. This
  violates AGENTS.md anti-defensiveness and is captured as a follow-up.
  Removing it is what enables flipping `warn_unreachable = True` in
  `mypy.ini`.

## Related

- Schema producer: `app_prompts/extract-system-v1.txt` declares the shape.
- Validation: `ai_service.py` parses LLM output into `ProvisionalMap`.
- Drill consumer: drill agent reads the map and routes by node kind.
