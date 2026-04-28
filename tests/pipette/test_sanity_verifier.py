# tests/pipette/test_sanity_verifier.py
from tools.pipette.sanity.schema import Finding, ReviewerOutput
from tools.pipette.sanity.verifier import filter_by_confidence, build_verifier_prompt

def _f(reviewer: str, conf: float) -> Finding:
    return Finding(reviewer=reviewer, severity="critical", confidence=conf, claim="x", evidence=["a"])  # type: ignore[arg-type]

def test_filter_drops_below_0_8():
    out = filter_by_confidence([_f("contracts", 0.5), _f("contracts", 0.79), _f("contracts", 0.8), _f("contracts", 0.95)])
    assert [f.confidence for f in out] == [0.8, 0.95]

def test_filter_returns_empty_when_all_below_threshold():
    assert filter_by_confidence([_f("contracts", 0.1), _f("contracts", 0.5)]) == []

def test_filter_passes_through_at_exact_threshold():
    assert len(filter_by_confidence([_f("contracts", 0.8)])) == 1

def test_build_verifier_prompt_includes_all_reviewer_outputs():
    outputs = [
        ReviewerOutput(reviewer="contracts", findings=[_f("contracts", 0.7)]),
        ReviewerOutput(reviewer="impact", findings=[_f("impact", 0.8)]),
        ReviewerOutput(reviewer="glossary", findings=[]),
        ReviewerOutput(reviewer="coverage", findings=[_f("coverage", 0.6)]),
    ]
    prompt = build_verifier_prompt(outputs)
    for r in ["contracts", "impact", "glossary", "coverage"]:
        assert f'"reviewer":"{r}"' in prompt or f'"reviewer": "{r}"' in prompt

def test_build_verifier_prompt_loads_reviewer_md_template():
    """The prompt must include the verifier.md template's instructions."""
    prompt = build_verifier_prompt([])
    assert "re-check each finding" in prompt
    assert "code-review-graph" in prompt
