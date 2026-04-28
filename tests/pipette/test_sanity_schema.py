import pytest
from tools.pipette.sanity.schema import Finding, Verdict


def test_finding_round_trip():
    f = Finding(reviewer="contracts", severity="critical", confidence=0.9, claim="X", evidence=["a.py:10"])
    assert f.model_dump()["confidence"] == 0.9


def test_verdict_pass_must_not_set_jump_back_to():
    with pytest.raises(ValueError):
        Verdict(verdict="PASS", jump_back_to=1)


def test_verdict_fail_requires_jump_back_to():
    with pytest.raises(ValueError):
        Verdict(verdict="FAIL")
    Verdict(verdict="FAIL", jump_back_to=1)  # ok


def test_verdict_jump_back_to_3_or_4_invalid():
    with pytest.raises(ValueError):
        Verdict(verdict="FAIL", jump_back_to=3)
    with pytest.raises(ValueError):
        Verdict(verdict="FAIL", jump_back_to=4)


def test_verdict_needs_research_requires_brief():
    with pytest.raises(ValueError):
        Verdict(verdict="NEEDS_RESEARCH")
    Verdict(verdict="NEEDS_RESEARCH", research_brief={"question": "Q?", "why_needed": "X"})  # ok


def test_verdict_research_brief_requires_both_fields():
    from tools.pipette.sanity.schema import ResearchBrief
    with pytest.raises(Exception):  # pydantic ValidationError on missing field
        ResearchBrief(question="Q?")
    with pytest.raises(Exception):
        ResearchBrief(why_needed="X")
