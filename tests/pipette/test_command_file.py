# tests/pipette/test_command_file.py
import re
from pathlib import Path

def test_pipette_command_has_frontmatter():
    text = Path(".claude/commands/pipette.md").read_text()
    assert text.startswith("---\n")
    fm_end = text.find("\n---\n", 4)
    assert fm_end > 0
    fm = text[4:fm_end]
    assert re.search(r"^name:\s*pipette\s*$", fm, re.MULTILINE)

def test_pipette_command_references_each_step():
    text = Path(".claude/commands/pipette.md").read_text()
    # B-revision (2026-04-28): Step 1.5 collapsed into Step 1 — no longer in marker list.
    for step_marker in ["Step -1", "Step 0", "Step 1", "Step 2", "Step 3", "Step 4", "Step 5", "Step 6", "Step 7"]:
        assert step_marker in text, f"missing {step_marker} section"
