# ADR-0002 — LLM provider lives behind a seam; application asks for cognitive artifacts

**Status:** Accepted (2026-05-01)
**Driver:** [foundation design spec, §5.2 + §5.3](../superpowers/specs/2026-05-01-foundation-design.md), PR #76

## Context

Before this PR, `ai_service.py` was a 1035-line module that fused four concerns: Gemini SDK calls, retry policy, error normalization, and several distinct prompted Gemini stages (extraction, drill, repair reps). Tests reached for `ai_service._get_client` and `ai_service._call_gemini_with_retry` (private names) — a strong signal that the seam between application code and provider code did not exist where it needed to.

The product itself does not care which LLM produced a Provisional map. The *application* says, "give me a `ProvisionalMap`"; the *infrastructure* — Gemini today, possibly Anthropic or OpenAI later — handles "how do we get one?" The two concerns lived in the same file.

## Decision

The LLM provider lives behind an `llm/` package. Application code imports only `LLMClient`, `StructuredLLMRequest`, `StructuredLLMResult`, `TokenUsage`, the normalized error hierarchy, and `build_llm_client`. Provider-specific code (currently `google-genai`) is confined to `llm/gemini_adapter.py`.

The application asks for a validated cognitive artifact:

```python
result = client.generate_structured(StructuredLLMRequest(
    system_prompt=...,
    user_prompt=...,
    response_schema=ProvisionalMap,   # ← the contract
    task_name="provisional_map_generation",
    prompt_version=EXTRACT_PROMPT_VERSION,
))
provisional_map = result.parsed   # ← already a Pydantic instance
```

The application **never** sees a Gemini `response`, a `dict`, a JSON string, or a provider-specific exception class.

### Responsibility split

| Concern | Lives in |
|---|---|
| SDK call (request/response) | `llm/gemini_adapter.py` |
| Pydantic → JSON Schema translation | `llm/gemini_adapter.py` |
| Provider exception → normalized error | `llm/gemini_adapter.py` |
| Retry policy + exponential backoff | `llm/client.py` |
| Structured telemetry log per call | `llm/client.py` |
| Token-usage extraction (normalized shape) | `llm/gemini_adapter.py` (raw) → `llm/client.py` (consumed) |

`LLMAdapter` is a `runtime_checkable` Protocol with a single primitive: `call_once(request) -> StructuredLLMResult` or raises a normalized error. `LLMClient` is the concrete wrapper that owns retry + telemetry. Adding a second provider is one new file (e.g., `llm/anthropic_adapter.py`) plus updating `llm/factory.py`.

### The architectural invariant

`tests/test_llm_seam_isolation.py` walks every `.py` file outside `.worktrees/`/`.venv/`/etc. and asserts that none of them import `google.genai` or `google.generativeai` except `llm/gemini_adapter.py`. `ai_service.py` is currently exempted because `drill_chat` and `generate_repair_reps` still use the legacy SDK; that exemption is documented and removed in the next migration sweep. **The foundation thesis holds iff this test passes.**

A second test asserts `ai_service.py` references `from llm import` and `ProvisionalMap` for the extract path — a positive regression gate that the migration didn't quietly revert.

### User-facing error policy

Across the entire `LLMError` hierarchy, the route returns **stable copy** to the learner. Provider-internal strings (`"Gemini service error (HTTP 503): ..."`, model names, error codes) flow into operator logs but never into the response body. The learner is never told which AI provider we use. See [PR #76 commit `706bd5b`](https://github.com/jon-devlapaz/socratink-app/commit/706bd5b) for the parametrized leak test that locks this in.

## Alternatives

- **Wrap each Gemini call site in a small helper.** Rejected: doesn't solve the seam problem (provider details still in application files), doesn't centralize retry/telemetry, and tests would still patch private names.
- **Build the seam but add multiple adapters now.** Rejected as cargo-culting. The seam is the architectural commitment; adding a second adapter is later focused work driven by an actual product or cost reason. The Gemini adapter exists today because we use Gemini today.
- **Retry policy in the adapter (per-provider).** Rejected: duplicates the loop in every adapter and makes "what is retried?" a per-provider question. The current shape — adapter classifies errors into normalized categories, client owns retry — is the cleanest split (see also [ADR-0003](0003-retriable-error-marker.md)).

## Consequences

- **The product-quality test from the design spec — *"no socratink application code should import Gemini directly"* — is now an automated assertion**, not a hope. It enforces itself on every commit.
- **Switching providers is a one-file addition.** Once a second adapter exists (e.g., Anthropic), `LLM_PROVIDER=anthropic` flips the entire stack — including the `/api/extract` route — without touching application code.
- **One legacy exception remains** for `ai_service.py` until `drill_chat` and `generate_repair_reps` migrate. That exception is annotated in the test and removed in the next sweep. Until then, contributors writing new logic in `ai_service.py` should prefer the seam path over the legacy one (the test won't catch this — judgment matters).
- **Tests no longer patch private names.** The migration test for `extract_knowledge_map` injects a fake `LLMClient` instead of monkeypatching `_get_client` and `_call_gemini_with_retry`. Future LLM-touching tests follow the same pattern.
