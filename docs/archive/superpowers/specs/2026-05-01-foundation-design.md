# Foundation design — cognitive artifacts, LLM seam, prompt registry

**Date:** 2026-05-01
**Status:** Approved (brainstorm phase complete; ready for plan + implementation)
**Author:** Brainstormed with Claude, sanity-checked with Gemini, decisions made by jon-devlapaz

---

## 1. Why this exists

The founder is concerned about building features on a "castle on sand." Diagnostic recon on `ai_service.py` (1035 LOC, four concerns fused into one module) confirmed real friction:

- Tests patch `_get_client` and `_call_gemini_with_retry` (private names) — strongest signal of a missing seam
- `extract_knowledge_map` has zero unit tests, uses raw `json.loads` instead of Gemini's `response_schema`, and writes to `logs/extract-invalid-json.log` on failure
- Gemini error → HTTP-status mapping is duplicated three times in `main.py`
- Prompts loaded inconsistently (drill/repair-reps at module import; extract per-call)
- `_resolve_node_mechanism` lives in `main.py` despite `ai_service.py` requiring its output

The product docs sharpen the goal:

- **PRODUCT.md** — calm, Socratic personality; anti-references include "generic AI tutor branding that claims to know the learner's mind."
- **DESIGN.md** MVP cut — *"Pasted text + global learner-map inputs only. Internal routing signals (never learner-visible)."* URL ingestion deferred until manual fallback ships.
- **UBIQUITOUS_LANGUAGE.md** distinguishes **Provisional map** (shaped by starting-map input) from **Draft map** (extracted from source, no learner evidence).

The MVP path produces a **Provisional map**, not a Draft map. The current `extract_knowledge_map` is mis-named for the MVP. This spec corrects that drift while building the seams that prevent re-tangling.

## 2. Core thesis

> **The application asks for a validated cognitive artifact. It never asks for "Gemini output."**

Three architectural invariants flow from this:

1. **Cognitive artifacts are typed.** A `ProvisionalMap` is a Pydantic model with structural validation (identifier grammar, reference closure). The boundary between extraction and downstream stages is the validated artifact, not a `dict`.
2. **The LLM provider lives behind a seam.** Application code imports only `LLMClient`. Provider-specific SDKs (Gemini today, possibly Anthropic later) live exclusively inside adapter modules. An architectural test enforces this invariant.
3. **Prompts are first-class versioned artifacts.** Each game-loop stage resolves to one active prompt version via a filesystem registry; the active version is config, not code.

## 3. Goals

- Make the cognitive artifact (`ProvisionalMap`) a typed structural contract.
- Hide the LLM provider behind a domain-shaped seam owned by the application.
- Make prompt swapping a configuration change, not a code change.
- Add the missing test coverage on the load-bearing extraction path.
- Establish ADR + static-analysis discipline so this foundation cannot quietly erode.

## 4. Non-goals (deliberately deferred)

- Writing a second LLM adapter (Anthropic, OpenAI). The seam exists; adding adapters is later, focused work.
- Moving `_resolve_node_mechanism` out of `main.py`. Separate foundation move.
- Per-`intake_mode` prompt forking. One prompt per stage; branch with conditional logic inside the prompt only when divergence is real.
- A bespoke offline eval CLI. Pytest with golden fixtures covers the same need.
- A TOML registry manifest. Filesystem layout + env-var pin is enough.
- URL ingestion UI exposure. Per DESIGN.md MVP cut.
- Image / audio / video intake.
- Quality-floor knobs (≥N nodes per map). The prompt governs that; validators catch structural breakage only.

## 5. Architecture

### 5.1 The cognitive artifact contract

`ProvisionalMap` is a Pydantic model. The shape is the same shape `extract_knowledge_map` returns today, but typed and validated.

The model carries:

- **Identifier grammar** — `BackboneId`, `ClusterId`, `SubnodeId` typed wrappers. Parser rejects malformed IDs (`b1`, `c1_s2`, `core-thesis` are valid; arbitrary strings are not).
- **Reference closure validators** — implements every closure rule documented in `app_prompts/extract-system-v1.txt` (output rules section): backbone-cluster coverage, dependent-cluster existence, every cluster has at least one subnode, learning-prerequisite DAG (no self-loops, reciprocals, or cycles), framework-cluster references resolve.
- **No quality-floor knobs.** The prompt is responsible for content quality. The model is responsible for structural integrity.

The exact field set of `ProvisionalMap` is bound to the JSON schema declared in `app_prompts/extract-system-v1.txt`. When the prompt's output schema changes, the Pydantic model changes alongside it (likely as a new prompt version + matching model migration).

Future: `DraftMap` (raw extraction from source, no learner shaping) becomes a sibling model when URL ingestion ships.

### 5.2 The LLM seam — `llm/` package

```
llm/
├── __init__.py        # public re-exports: LLMClient, StructuredLLMRequest, StructuredLLMResult, TokenUsage, errors
├── types.py           # request, result, usage dataclasses
├── errors.py          # normalized exception hierarchy
├── adapter.py         # LLMAdapter Protocol — primitive: call_once(req) -> result | raise normalized error
├── client.py          # LLMClient (concrete) — wraps an adapter; owns retry policy, telemetry, logging
└── gemini_adapter.py  # GeminiAdapter(LLMAdapter)
```

#### Request / result types

```python
@dataclass(frozen=True)
class StructuredLLMRequest:
    system_prompt: str
    user_prompt: str
    response_schema: type[BaseModel]
    temperature: float = 0.0
    max_retries: int = 2
    task_name: str | None = None        # e.g., "provisional_map_generation"
    prompt_version: str | None = None   # e.g., "v3"

@dataclass(frozen=True)
class StructuredLLMResult:
    parsed: BaseModel
    raw_text: str
    usage: TokenUsage
    model: str
    provider: str
    latency_ms: float
    raw_provider_metadata: dict[str, Any] | None = None

@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
```

#### Normalized error hierarchy

```python
class LLMError(Exception): ...
class LLMMissingKeyError(LLMError): ...
class LLMRateLimitError(LLMError): ...
class LLMServiceError(LLMError): ...
class LLMValidationError(LLMError): ...
```

`LLMValidationError` is raised when the provider returns content but the result fails schema validation. Distinct from `LLMServiceError` (transport / upstream failure) so the route layer can map it differently (likely 502 vs 503, or surface a more specific learner-facing message).

#### Responsibility split

| Concern | Lives in | Why |
|---|---|---|
| SDK call (Gemini API request/response) | `GeminiAdapter` | Provider-specific |
| Schema-export translation (Pydantic → `response_schema` JSON) | `GeminiAdapter` | Provider-specific |
| Exception classification (Gemini exception → normalized error) | `GeminiAdapter` | Provider-specific |
| Pydantic validation of returned content | `GeminiAdapter` (raises `LLMValidationError` on failure) | Adapter is the boundary |
| Retry policy (loop, backoff) | `LLMClient` | Provider-agnostic |
| Telemetry / structured logging | `LLMClient` | Normalized fields fire once per call |
| Token usage accounting | `LLMClient` (extracted from result) | Provider-agnostic shape |

The adapter exposes one primitive: `call_once(StructuredLLMRequest) -> StructuredLLMResult` or raises a normalized exception. `LLMClient.generate_structured(req)` wraps that in a retry loop and a logging block. App code only imports `LLMClient`.

### 5.3 Architectural invariant — the isolation test

`tests/test_llm_seam_isolation.py` walks every `.py` file in the repo and asserts that no file outside `llm/gemini_adapter.py` imports `google.generativeai` or `google.genai`. This test is the enforcement of the foundation thesis: the foundation IS modular if and only if this test passes. ADR-0003 cites this test as the load-bearing artifact.

### 5.4 Prompt registry

Filesystem layout:

```
app_prompts/
├── provisional_map_generation/
│   ├── v1.txt
│   └── v2.txt
├── cold_attempt/
│   └── v1.txt
├── spaced_re_drill/        # may be a symlink or alias to cold_attempt initially
│   └── v1.txt
└── repair_reps/
    └── v1.txt
```

Resolver: `prompts.py` exposes `get(stage: str) -> Prompt`. Active version per stage resolves via env var `PROMPT_VERSION_<STAGE_UPPER>` (e.g., `PROMPT_VERSION_PROVISIONAL_MAP_GENERATION=v2`); default is the highest-numbered file.

```python
@dataclass(frozen=True)
class Prompt:
    name: str           # stage name
    version: str        # e.g., "v2"
    text: str           # system_prompt body
    schema_class: type[BaseModel] | None = None  # bound schema for this stage
```

The `schema_class` field couples a stage to its expected cognitive artifact (e.g., `provisional_map_generation` → `ProvisionalMap`). Callers pass the resolved `Prompt` into `StructuredLLMRequest.response_schema`.

### 5.5 Model selection

Two levels of granularity:

- **Global default** — `LLM_PROVIDER=gemini`, `LLM_MODEL=gemini-1.5-flash` (env vars)
- **Per-stage override** — `LLM_PROVIDER_<STAGE>`, `LLM_MODEL_<STAGE>`

No per-prompt-version model affinity yet. Add only if a prompt is empirically shown to depend on a specific model.

### 5.6 Regression tests — golden fixtures

```
tests/
├── fixtures/
│   └── provisional_maps/
│       ├── short_concept_only.json     # input: just a concept name
│       ├── pasted_passage.json         # input: a paragraph
│       └── small_text_file.json        # input: TXT file content
└── test_provisional_map_extraction.py
```

Each fixture stores the input + a recorded LLM response + the expected structural shape (node counts by type, identifier grammar, closure properties). The default test path is **offline**: replay the recorded response through the parser and assert structural shape. CI runs this every time. A separate manual-invocation path re-records by calling the LLM live; a developer runs it intentionally when a prompt version changes shape.

This split keeps CI deterministic and free, while still letting golden fixtures be refreshed against real LLM output when intentional.

### 5.7 Stage 0 (input)

UI does not change. The single-field Concept Threshold ("What do you want to understand?") with optional file attach is product-correct per DESIGN.md.

`ImportedSource` gains an internal-only field:

```python
intake_mode: Literal["concept_only", "passage", "file_text", "file_pdf"]
```

Detected post-submit. Never surfaced to the learner. Used by the prompt registry for telemetry tagging and (later, if needed) per-mode prompt branching.

The `min_text_length` divergence (1 char for `from_text`, 200 for `from_url`) is replaced by per-`intake_mode` floors:

- `concept_only` — allows short input by design (1+ chars)
- `passage` — 80-char floor (conservative; below 80 is almost certainly a concept name miscategorized)
- `file_text` / `file_pdf` — 200-char extracted-text floor matching URL-path policy

### 5.8 Static analysis baseline

`pyproject.toml` gains minimal ruff and mypy configurations:

- **Ruff** — basic ruleset (E, F, I, B). Run on changed files in pre-commit; full repo in CI as warnings only at first.
- **Mypy** — `--ignore-missing-imports`, `--check-untyped-defs`. Apply to `llm/`, `prompts.py`, and the `ProvisionalMap` model from day 1. Other modules opt-in over time.

The point is to lock the floor on new code without forcing a repo-wide retrofit.

## 6. ADRs to write (alongside this foundation work)

- **ADR-0001 — `ProvisionalMap` as a typed cognitive artifact contract.** Records: why Pydantic, why structural-only validation, why this is enforced via Gemini's `response_schema` (and equivalently in future adapters).
- **ADR-0002 — Prompt registry shape (filesystem-only, no manifest).** Records: why a manifest was deliberately *not* introduced; how the env-var override works; how to add a new stage.
- **ADR-0003 — LLM seam: the application asks for cognitive artifacts, not provider output.** Records: the invariant, the file layout, the responsibility split, and the architectural isolation test as the enforcement mechanism.

Vocabulary changes (e.g., adding "Stage" or "Game loop" if needed) live in `UBIQUITOUS_LANGUAGE.md`, not in ADRs.

## 7. Implementation order

| # | Step | Commit-able as |
|---|---|---|
| 1 | `llm/types.py`: `StructuredLLMRequest`, `StructuredLLMResult`, `TokenUsage` | own PR |
| 2 | `llm/errors.py` + `llm/adapter.py` (Protocol) + `llm/client.py` (retry + telemetry) | same PR or follow-up |
| 3 | `llm/gemini_adapter.py` — replaces `_get_client` and `_call_gemini_with_retry`; classifies Gemini exceptions into normalized errors; raises `LLMValidationError` on schema failure | same PR |
| 4 | `tests/test_llm_seam_isolation.py` — architectural invariant | same PR |
| 5 | Define `ProvisionalMap` Pydantic model + identifier grammar + closure validator | own PR |
| 6 | Migrate `extract_knowledge_map` to call `LLMClient.generate_structured(req)` returning `ProvisionalMap`; remove `_clean_response` fence-stripping path | own PR |
| 7 | Migrate `drill_chat` and `generate_repair_reps` to use the same client; collapse `main.py`'s three duplicate error-mapping blocks into one | own PR |
| 8 | `prompts.py` + filesystem registry + `PROMPT_VERSION_<STAGE>` env override; migrate the three existing prompts under the new layout | own PR |
| 9 | Pytest golden fixtures for `ProvisionalMap` extraction (start with one fixture; expand as confidence grows) | own PR |
| 10 | Ruff + mypy non-disruptive baseline in `pyproject.toml` | own PR |
| 11 | `intake_mode` field on `ImportedSource`; per-mode `min_text_length` policy; replaces the 1-vs-200 divergence | own PR |
| 12 | ADR-0001, ADR-0002, ADR-0003 written and committed | own PR (or alongside steps that introduce each decision) |

The currently-approved scope for the first execution sweep is steps **1-6** (the LLM seam + first migration through `extract_knowledge_map`). Steps 7-12 follow as separate moves.

## 8. Final state

| Layer | Shape |
|---|---|
| Cognitive artifact contract | `ProvisionalMap` Pydantic model + closure validator |
| LLM seam | `llm/` package: types, errors, Protocol adapter, concrete client, GeminiAdapter |
| Architectural invariant | `tests/test_llm_seam_isolation.py` enforces "no provider import outside the adapter" |
| Prompt registry | Filesystem layout + `prompts.py` resolver + env-var version pin |
| Regression tests | Golden fixtures under `tests/fixtures/provisional_maps/` exercised via pytest |
| Static analysis | Ruff + mypy non-disruptive baseline |
| Stage 0 | UI unchanged; `ImportedSource` gains internal `intake_mode`; per-mode `min_text_length` |
| ADRs | ADR-0001 (artifact contract), ADR-0002 (registry shape), ADR-0003 (LLM seam) |

## 9. Verification

The foundation is achieved when all of the following hold:

- `tests/test_llm_seam_isolation.py` passes
- `extract_knowledge_map` returns a validated `ProvisionalMap` instance, not a `dict`
- Switching `LLM_PROVIDER` would require only writing a new adapter — no application-code changes
- A new prompt version ships by adding a file under `app_prompts/{stage}/v{N+1}.txt` and setting one env var
- Tests for extraction shape live in `tests/`, not in the application module's private internals
- Adding a new game-loop stage that needs a prompt is one new directory + one prompt file + one entry point in calling code
- ADR-0001, 0002, 0003 are present in `docs/adr/`

## 10. Out-of-scope explicit list (this is not a "we'll get to it" — these are deliberate cuts)

- Anthropic or OpenAI adapter (write when needed; the seam is ready)
- Quality-floor knobs (≥N nodes etc.); fix prompts if they drift in quality
- Per-`intake_mode` prompt forking (split files only when divergence is real)
- A bespoke eval CLI separate from pytest
- TOML or YAML registry manifest
- URL ingestion UI exposure (deferred per DESIGN.md MVP cut)
- Moving `_resolve_node_mechanism` out of `main.py`
- Image / audio / video intake
- Streaming LLM responses
- Per-prompt-version model affinity in the registry
