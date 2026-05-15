import pytest

from models.drill_attempts import (
    has_substantive_attempt,
    infer_help_request_reason,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("", None),
        ("   ", None),
        ("I don't know", "explicit_unknown"),
        ("idk, no idea", "explicit_unknown"),
        ("Could you explain this?", "explicit_explain_request"),
        ("Please break that down for me", "explicit_explain_request"),
        ("I'm confused and lost here", "affective_confusion"),
        ("The pump opens because pressure changes.", None),
    ],
)
def test_infer_help_request_reason_classifies_help_markers(
    message: str, expected: str | None
) -> None:
    assert infer_help_request_reason(message) == expected


@pytest.mark.parametrize(
    "message",
    [
        "The channel opens because voltage changes across the membrane.",
        "If pressure rises, the valve closes and flow moves through the bypass.",
        "I think the heater turns on because the measured temperature is below target?",
        "Signals traveled through receptors during repeated stimulation.",
    ],
)
def test_has_substantive_attempt_accepts_generative_commitment(
    message: str,
) -> None:
    assert has_substantive_attempt(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "",
        "plants grow",
        "Can you explain this?",
        "I don't know can you please explain this",
        "Maybe it is kind of just this",
    ],
)
def test_has_substantive_attempt_rejects_help_or_low_signal_messages(
    message: str,
) -> None:
    assert has_substantive_attempt(message) is False
