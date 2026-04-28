# tools/pipette/sanity/verifier.py
"""Two-stage verifier:
  1. build_verifier_prompt — emits the prompt that drives a verifier subagent
     (dispatched from the slash command, like the other 4 reviewers).
  2. filter_by_confidence — final mechanical 0.8 threshold on the verifier's
     re-scored output.
"""
from __future__ import annotations
from pathlib import Path
from tools.pipette.sanity.schema import Finding, ReviewerOutput

CONFIDENCE_THRESHOLD = 0.8

_VERIFIER_PROMPT_PATH = Path(__file__).parent / "reviewers" / "verifier.md"


def filter_by_confidence(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.confidence >= CONFIDENCE_THRESHOLD]


def build_verifier_prompt(outputs: list[ReviewerOutput]) -> str:
    """Concatenate the verifier.md template with the 4 reviewer outputs as JSON."""
    template = _VERIFIER_PROMPT_PATH.read_text()
    blocks = []
    for o in outputs:
        blocks.append(f"### Reviewer: {o.reviewer}\n```json\n{o.model_dump_json()}\n```")
    return template + "\n\n---\n\n## Reviewer outputs\n\n" + "\n\n".join(blocks)
