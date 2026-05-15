import json

import pytest

from models.repair_reps import (
    RepairRep,
    RepairRepsEvaluation,
    parse_repair_reps_response,
    validate_repair_reps_result,
)


class FakeResponse:
    def __init__(self, parsed=None, text: str | None = None):
        self.parsed = parsed
        self.text = text


def valid_reps() -> list[RepairRep]:
    return [
        RepairRep(
            id="rep-1",
            kind="missing_bridge",
            prompt="What bridge connects the comparison to the heater action?",
            target_bridge="The below-setpoint comparison creates a gap, so heat turns on.",
            feedback_cue="Check whether you named both the gap and the action.",
        ),
        RepairRep(
            id="rep-2",
            kind="next_step",
            prompt="What happens if the room is still below the setpoint?",
            target_bridge="Heating remains active until the measured temperature reaches the setpoint.",
            feedback_cue="Check whether your answer stayed tied to the setpoint.",
        ),
        RepairRep(
            id="rep-3",
            kind="cause_effect",
            prompt="Why does the comparison determine heater state?",
            target_bridge="The comparison identifies whether heat is needed.",
            feedback_cue="Look for the cause-effect link from comparison to heater state.",
        ),
    ]


def valid_evaluation() -> RepairRepsEvaluation:
    return RepairRepsEvaluation(reps=valid_reps())


def test_parse_repair_reps_response_accepts_parsed_evaluation() -> None:
    evaluation = valid_evaluation()

    assert parse_repair_reps_response(FakeResponse(parsed=evaluation)) is evaluation


def test_parse_repair_reps_response_accepts_strict_dict_payload() -> None:
    payload = valid_evaluation().model_dump()

    parsed = parse_repair_reps_response(FakeResponse(parsed=payload))

    assert isinstance(parsed, RepairRepsEvaluation)
    assert parsed.reps[0].id == "rep-1"


def test_parse_repair_reps_response_accepts_raw_json_text() -> None:
    payload = valid_evaluation().model_dump()

    parsed = parse_repair_reps_response(FakeResponse(text=json.dumps(payload)))

    assert isinstance(parsed, RepairRepsEvaluation)
    assert parsed.reps[1].kind == "next_step"


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(parsed=None),
        FakeResponse(parsed={"reps": []}),
        FakeResponse(text="{not json"),
        FakeResponse(
            parsed={
                **valid_evaluation().model_dump(),
                "routing": "NEXT",
            }
        ),
        FakeResponse(
            text=json.dumps(
                {
                    "reps": [
                        {
                            **valid_evaluation().model_dump()["reps"][0],
                            "score_eligible": True,
                        },
                        *valid_evaluation().model_dump()["reps"][1:],
                    ]
                }
            )
        ),
    ],
)
def test_parse_repair_reps_response_rejects_invalid_or_extra_fields(
    response: FakeResponse,
) -> None:
    with pytest.raises(ValueError, match="invalid structured repair reps response"):
        parse_repair_reps_response(response)


def test_repair_reps_schema_stays_gemini_compatible_without_extra_forbid() -> None:
    schema = RepairRepsEvaluation.model_json_schema()

    assert "additionalProperties" not in json.dumps(schema)
    assert "additional_properties" not in json.dumps(schema)


def test_validate_repair_reps_result_accepts_exact_three_complete_reps() -> None:
    validate_repair_reps_result(valid_evaluation(), expected_count=3)


@pytest.mark.parametrize(
    ("reps", "message"),
    [
        (valid_reps()[:2], "exactly 3 reps"),
        ([valid_reps()[0], valid_reps()[0], valid_reps()[2]], "duplicated"),
        (
            [
                valid_reps()[0].model_copy(update={"id": " "}),
                valid_reps()[1],
                valid_reps()[2],
            ],
            "missing an id",
        ),
        (
            [
                valid_reps()[0].model_copy(update={"prompt": " "}),
                valid_reps()[1],
                valid_reps()[2],
            ],
            "missing a prompt",
        ),
        (
            [
                valid_reps()[0].model_copy(update={"target_bridge": " "}),
                valid_reps()[1],
                valid_reps()[2],
            ],
            "missing a target bridge",
        ),
        (
            [
                valid_reps()[0].model_copy(update={"feedback_cue": " "}),
                valid_reps()[1],
                valid_reps()[2],
            ],
            "missing a feedback cue",
        ),
    ],
)
def test_validate_repair_reps_result_rejects_malformed_reps(
    reps: list[RepairRep], message: str
) -> None:
    evaluation = RepairRepsEvaluation.model_construct(reps=reps)

    with pytest.raises(ValueError, match=message):
        validate_repair_reps_result(evaluation, expected_count=3)
