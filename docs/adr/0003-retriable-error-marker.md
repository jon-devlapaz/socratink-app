# ADR-0003 — Retry contract is encoded in the type system via `RetriableLLMError`

**Status:** Accepted (2026-05-01)
**Driver:** Gemini sanity-check feedback during PR #76, [commit `56bde46`](https://github.com/jon-devlapaz/socratink-app/commit/56bde46)
**Supersedes:** N/A. Implicit retry contract from earlier in PR #76.

## Context

The first cut of `LLMClient.generate_structured` retried via:

```python
except (LLMRateLimitError, LLMServiceError) as exc:
    ...retry...
```

This was correct at the moment of writing but **fragile under future change**. The fragility is concrete:

- The retry contract — "which errors should `LLMClient` retry?" — lived in the tuple inside the `except` clause. It was implicit, not type-encoded.
- A live smoke test surfaced this exact failure mode: a 4xx error (expired API key) was first classified as `LLMServiceError`, which placed it in the retry set. The fix introduced `LLMClientError` as a sibling — but a future contributor adding another error class (e.g., `LLMQuotaExhaustedError`, `LLMSafetyFilteredError`) has no compiler signal telling them which category is correct. They have to remember to update both the class hierarchy AND the `except` tuple.
- Independent post-implementation review (Gemini sanity check) flagged the same risk: "the retry contract is implicit in a tuple and prone to future developer error."

## Decision

The retry contract is a marker base class.

```python
class LLMError(Exception): ...

class RetriableLLMError(LLMError):
    """LLMClient retries any exception that subclasses this."""

class LLMRateLimitError(RetriableLLMError): ...   # retried
class LLMServiceError(RetriableLLMError): ...     # retried

class LLMMissingKeyError(LLMError): ...           # NOT retried
class LLMClientError(LLMError): ...               # NOT retried
class LLMValidationError(LLMError): ...           # NOT retried
```

`LLMClient.generate_structured` reads:

```python
except RetriableLLMError as exc:
    ...retry...
```

Adding a new error type is a one-decision act: subclass `RetriableLLMError` iff it should be retried. The class hierarchy *is* the contract — there is no separate tuple to forget to update. A test (`test_retriable_marker_governs_retry_set`) locks in the current membership so accidental drift is caught.

## Alternatives

- **Stable tuple in `LLMClient`** (the original shape). Rejected on the grounds above: prone to drift; new contributors need to know about a tuple they may not be looking at.
- **`is_retriable: bool` attribute on each `LLMError`**. Rejected: behavior carried by an instance attribute is harder to introspect than behavior carried by the class hierarchy. `issubclass` is cheap, explicit, and discoverable.
- **Decorator-based registration** (e.g., `@retriable` on the class). Rejected as over-engineered for a flat hierarchy. ABC inheritance is the standard Python idiom; we use it.

## Consequences

- **The retry policy is self-documenting.** A reader of `llm/errors.py` sees the contract by class structure alone. No cross-file lookup needed.
- **Adding a new error class is type-safe** with respect to retry behavior. The compiler/type-checker (mypy) and the regression test both surface mistakes before runtime.
- **The retry loop is unchanged in shape but stronger in guarantee.** `except RetriableLLMError` is a simpler and more specific catch than `except (A, B)` — no maintenance work as the hierarchy grows.
- **Future categorization is open.** If a permanent-but-different category ever needs the same treatment (e.g., a `FatalLLMError` ABC for non-retried errors that get a special log path), it slots into the existing pattern.
