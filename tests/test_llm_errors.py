from llm.errors import (
    LLMError,
    LLMMissingKeyError,
    LLMRateLimitError,
    LLMServiceError,
    LLMValidationError,
)


def test_all_subclasses_inherit_from_llm_error():
    for cls in (
        LLMMissingKeyError,
        LLMRateLimitError,
        LLMServiceError,
        LLMValidationError,
    ):
        assert issubclass(cls, LLMError)
        assert issubclass(cls, Exception)


def test_subclasses_are_distinct():
    classes = {
        LLMMissingKeyError,
        LLMRateLimitError,
        LLMServiceError,
        LLMValidationError,
    }
    assert len(classes) == 4
    assert not issubclass(LLMValidationError, LLMServiceError)
    assert not issubclass(LLMRateLimitError, LLMServiceError)


def test_validation_error_carries_message_and_optional_raw_text():
    err = LLMValidationError("bad shape", raw_text='{"oops":')
    assert "bad shape" in str(err)
    assert err.raw_text == '{"oops":'


def test_validation_error_raw_text_defaults_none():
    err = LLMValidationError("bad shape")
    assert err.raw_text is None
