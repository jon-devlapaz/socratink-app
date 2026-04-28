# tests/pipette/test_reviewer_prompts.py
from pathlib import Path
PROMPTS = Path("tools/pipette/sanity/reviewers")

def test_each_reviewer_prompt_specifies_json_output_contract():
    for p in PROMPTS.glob("*.md"):
        text = p.read_text()
        assert "Output contract" in text
        assert '"reviewer"' in text and '"findings"' in text
        assert "No prose outside the JSON" in text
