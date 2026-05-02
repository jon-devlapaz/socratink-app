from llm.errors import (
    LLMClientError,
    LLMError,
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
    RetriableLLMError,
)


def test_all_subclasses_inherit_from_llm_error():
    for cls in (
        LLMClientError,
        LLMMissingKeyError,
        LLMRateLimitError,
        LLMServiceError,
        LLMValidationError,
        RetriableLLMError,
    ):
        assert issubclass(cls, LLMError)
        assert issubclass(cls, Exception)


def test_subclasses_are_distinct():
    classes = {
        LLMClientError,
        LLMMissingKeyError,
        LLMRateLimitError,
        LLMServiceError,
        LLMValidationError,
    }
    assert len(classes) == 5
    assert not issubclass(LLMValidationError, LLMServiceError)
    assert not issubclass(LLMRateLimitError, LLMServiceError)
    # Critical: LLMClientError must NOT subclass LLMServiceError, otherwise
    # LLMClient's retry loop would erroneously retry permanent 4xx failures.
    assert not issubclass(LLMClientError, LLMServiceError)
    assert not issubclass(LLMClientError, LLMRateLimitError)


def test_retriable_marker_governs_retry_set():
    """RetriableLLMError is the single source of truth for "LLMClient retries this."
    Lock in the membership so a future error class added without thinking
    about retries can't accidentally land in (or out of) the retry set.
    """
    # Retried — must subclass RetriableLLMError
    assert issubclass(LLMRateLimitError, RetriableLLMError)
    assert issubclass(LLMServiceError, RetriableLLMError)

    # Permanent — must NOT subclass RetriableLLMError
    assert not issubclass(LLMMissingKeyError, RetriableLLMError)
    assert not issubclass(LLMClientError, RetriableLLMError)
    assert not issubclass(LLMValidationError, RetriableLLMError)


def test_validation_error_carries_message_and_optional_raw_text():
    err = LLMValidationError("bad shape", raw_text='{"oops":')
    assert "bad shape" in str(err)
    assert err.raw_text == '{"oops":'


def test_validation_error_raw_text_defaults_none():
    err = LLMValidationError("bad shape")
    assert err.raw_text is None
