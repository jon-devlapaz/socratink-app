"""Tests for should_enrich_with_lc — the four-gate enrichment threshold."""
from __future__ import annotations

from learning_commons import (
    LCSearchResult,
    LCStandard,
    should_enrich_with_lc,
)


def _std(score: float, *, jurisdiction: str = "Multi-State",
         statement_code: str | None = "HS-LS1-4",
         description: str = "x" * 60,
         uuid: str = "u-1") -> LCStandard:
    return LCStandard(
        case_uuid=uuid,
        statement_code=statement_code,
        description=description,
        jurisdiction=jurisdiction,
        score=score,
    )


def test_none_input_returns_none():
    assert should_enrich_with_lc(None) is None


def test_empty_standards_returns_none():
    result = LCSearchResult(top_score=0.0, standards=[])
    assert should_enrich_with_lc(result) is None


def test_low_score_below_threshold_returns_none():
    # 0.65 is the documented "garbage match plateau" score — see spec Appendix A
    result = LCSearchResult(top_score=0.65, standards=[_std(0.65)])
    assert should_enrich_with_lc(result) is None


def test_at_threshold_passes():
    result = LCSearchResult(top_score=0.70, standards=[_std(0.70)])
    out = should_enrich_with_lc(result)
    assert out is not None and len(out) == 1


def test_non_k12_returns_none_when_jurisdiction_unknown():
    # Empty jurisdiction → not identifiably K-12
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, jurisdiction="")],
    )
    assert should_enrich_with_lc(result) is None


def test_non_k12_returns_none_when_no_statement_code_and_short_description():
    # No statement code AND description shorter than threshold → not K-12 enough
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, statement_code=None, description="short")],
    )
    assert should_enrich_with_lc(result) is None


def test_k12_with_statement_code_passes_even_with_short_description():
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, statement_code="6.NS.B.2", description="short")],
    )
    out = should_enrich_with_lc(result)
    assert out is not None and len(out) == 1


def test_k12_with_long_description_passes_even_without_statement_code():
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, statement_code=None, description="x" * 80)],
    )
    out = should_enrich_with_lc(result)
    assert out is not None and len(out) == 1


def test_returns_top_three_standards_when_more_present():
    standards = [_std(0.80), _std(0.78), _std(0.75), _std(0.72), _std(0.71)]
    result = LCSearchResult(top_score=0.80, standards=standards)
    out = should_enrich_with_lc(result)
    assert out is not None
    assert len(out) == 3
    assert out[0].score == 0.80
    assert out[1].score == 0.78
    assert out[2].score == 0.75


def test_us_state_jurisdiction_passes_k12_check():
    # K-12 detection accepts known US-state jurisdictions in addition to "Multi-State"
    result = LCSearchResult(
        top_score=0.75,
        standards=[_std(0.75, jurisdiction="California", statement_code="CCSS.MATH.6.NS.B.2")],
    )
    out = should_enrich_with_lc(result)
    assert out is not None
