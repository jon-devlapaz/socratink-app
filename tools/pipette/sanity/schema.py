from typing import Literal
from pydantic import BaseModel, Field


class Finding(BaseModel):
    reviewer: Literal["contracts", "impact", "glossary", "coverage", "verifier"]
    severity: Literal["critical", "high", "medium", "low", "polish"]
    confidence: float = Field(ge=0.0, le=1.0)
    claim: str            # one-sentence statement of what's wrong
    evidence: list[str]   # file paths or symbol names from 00-graph-context.md
    suggested_fix: str | None = None


class ReviewerOutput(BaseModel):
    reviewer: Literal["contracts", "impact", "glossary", "coverage", "verifier"]
    findings: list[Finding]
    notes: str = ""


class ResearchBrief(BaseModel):
    question: str
    why_needed: str


_ALLOWED_JUMP = (1, 1.5, 2)


class Verdict(BaseModel):
    verdict: Literal["PASS", "FAIL", "NEEDS_RESEARCH"]
    # typing.Literal rejects floats; use `float | None` and validate value set in the validator.
    jump_back_to: float | None = None
    research_brief: ResearchBrief | None = None
    notes: str = ""

    def model_post_init(self, _ctx) -> None:
        if self.jump_back_to is not None and self.jump_back_to not in _ALLOWED_JUMP:
            raise ValueError(f"jump_back_to must be one of {_ALLOWED_JUMP}, got {self.jump_back_to!r}")
        if self.verdict == "FAIL" and self.jump_back_to is None:
            raise ValueError("FAIL requires jump_back_to in {1, 1.5, 2}")
        if self.verdict in ("PASS", "NEEDS_RESEARCH") and self.jump_back_to is not None:
            raise ValueError(f"{self.verdict} must not set jump_back_to")
        if self.verdict == "NEEDS_RESEARCH" and self.research_brief is None:
            raise ValueError("NEEDS_RESEARCH requires research_brief object with {question, why_needed}")
