# tests/pipette/test_gemini_picker.py
import subprocess
from unittest.mock import patch
import pytest
from tools.pipette.gemini_picker import (
    invoke_gemini, GeminiYamlInvalidAfterRetries, GeminiProcessFailure,
)
from tools.pipette.sanity.schema import Verdict

VALID_VERDICT_YAML = """
verdict: PASS
notes: |
  Looks good.
"""

VALID_NEEDS_RESEARCH_YAML = """
verdict: NEEDS_RESEARCH
research_brief:
  question: Does Pinecone support hybrid?
  why_needed: design depends on it
"""

INVALID_VERDICT_YAML = "this is not yaml: [unclosed"

INVALID_SCHEMA_YAML = """
verdict: PASS
jump_back_to: 1
"""

def _completed(stdout: str, returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(args=["gemini"], returncode=returncode, stdout=stdout, stderr=stderr)

def test_valid_yaml_returns_verdict():
    with patch("subprocess.run", return_value=_completed(VALID_VERDICT_YAML)) as m:
        v = invoke_gemini(prompt="Anything")
    assert v.verdict == "PASS"
    assert m.call_count == 1

def test_needs_research_verdict_round_trips_structured_brief():
    with patch("subprocess.run", return_value=_completed(VALID_NEEDS_RESEARCH_YAML)):
        v = invoke_gemini(prompt="Anything")
    assert v.verdict == "NEEDS_RESEARCH"
    assert v.research_brief is not None
    assert v.research_brief.question == "Does Pinecone support hybrid?"
    assert v.research_brief.why_needed == "design depends on it"

def test_invalid_yaml_retries_up_to_3_times():
    side = [_completed(INVALID_VERDICT_YAML)] * 3 + [_completed(VALID_VERDICT_YAML)]
    with patch("subprocess.run", side_effect=side) as m:
        v = invoke_gemini(prompt="Anything")
    assert v.verdict == "PASS"
    assert m.call_count == 4  # 3 bad + 1 good after retries

def test_4_invalid_attempts_raises():
    with patch("subprocess.run", return_value=_completed(INVALID_VERDICT_YAML)):
        with pytest.raises(GeminiYamlInvalidAfterRetries):
            invoke_gemini(prompt="Anything")

def test_schema_violation_treated_as_yaml_invalid_for_retry():
    side = [_completed(INVALID_SCHEMA_YAML), _completed(VALID_VERDICT_YAML)]
    with patch("subprocess.run", side_effect=side):
        v = invoke_gemini(prompt="Anything")
    assert v.verdict == "PASS"

def test_process_failure_raises_immediately():
    with patch("subprocess.run", return_value=_completed("", returncode=1, stderr="auth expired")):
        with pytest.raises(GeminiProcessFailure) as ei:
            invoke_gemini(prompt="Anything")
    assert "auth expired" in str(ei.value)

def test_process_failure_does_not_count_against_yaml_retries():
    """A process failure is not a YAML retry — it pauses the pipeline.
       This test asserts that a single process failure is *not* retried
       N more times before raising."""
    with patch("subprocess.run", return_value=_completed("", returncode=1, stderr="boom")) as m:
        with pytest.raises(GeminiProcessFailure):
            invoke_gemini(prompt="Anything")
    assert m.call_count == 1

def test_retry_prompt_includes_prior_bad_output():
    captured: list[str] = []
    def fake_run(args, **kw):
        captured.append(kw.get("input", "") or "")
        if len(captured) <= 1:
            return _completed(INVALID_VERDICT_YAML)
        return _completed(VALID_VERDICT_YAML)
    with patch("subprocess.run", side_effect=fake_run):
        invoke_gemini(prompt="P")
    assert "this output was not valid YAML" in captured[1].lower() or "this output was not valid yaml" in captured[1].lower()
    assert INVALID_VERDICT_YAML.strip() in captured[1]
