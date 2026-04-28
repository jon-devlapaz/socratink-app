from pathlib import Path
import pytest
import yaml
from tools.pipette.research_gate import (
    derive_slug, write_brief, ResearchCapExceeded,
)
from tools.pipette.lockfile import acquire

def _setup(tmp_path: Path) -> Path:
    root = tmp_path / "pipeline"
    (root / "_meta").mkdir(parents=True)
    folder = root / "2026-04-28-143211-x"
    folder.mkdir()
    acquire(root / "_meta" / ".lock", topic="x", folder=folder)
    return folder

def test_slug_deterministic_from_question():
    s1 = derive_slug("Does Pinecone support hybrid search w/ metadata filters as of Q2 2026?")
    s2 = derive_slug("Does Pinecone support hybrid search w/ metadata filters as of Q2 2026?!?")
    assert s1 == s2

def test_slug_drops_stop_words_and_kebabs():
    s = derive_slug("Is the new GraphQL endpoint stable in Q2 2026?")
    assert "the" not in s.split("-")
    assert "is" not in s.split("-")
    assert s == "new-graphql-endpoint-stable-q2-2026"  # 8 content words max

def test_per_file_cap_aborts_on_third_raise(tmp_path: Path):
    folder = _setup(tmp_path)
    write_brief(folder=folder, step=3, question="Does Pinecone support hybrid?", why="x")
    write_brief(folder=folder, step=3, question="Does Pinecone support hybrid?", why="x")
    with pytest.raises(ResearchCapExceeded):
        write_brief(folder=folder, step=3, question="Does Pinecone support hybrid?", why="x")

def test_per_step_cap_aborts_on_fourth_raise(tmp_path: Path):
    folder = _setup(tmp_path)
    write_brief(folder=folder, step=3, question="Q1", why="x")
    write_brief(folder=folder, step=3, question="Q2", why="x")
    write_brief(folder=folder, step=3, question="Q3", why="x")
    with pytest.raises(ResearchCapExceeded):
        write_brief(folder=folder, step=3, question="Q4", why="x")

def test_brief_yaml_has_required_fields(tmp_path: Path):
    folder = _setup(tmp_path)
    p = write_brief(folder=folder, step=1, question="Foo bar baz", why="needed at step 1")
    rec = yaml.safe_load(Path(p).read_text())
    for k in ("raised_by_step", "raised_at", "research_question", "why_needed", "blocking", "required_findings", "suggested_tools"):
        assert k in rec

def test_caps_are_persisted_in_lockfile(tmp_path: Path):
    folder = _setup(tmp_path)
    write_brief(folder=folder, step=3, question="Foo", why="x")
    lock = yaml.safe_load((tmp_path / "pipeline" / "_meta" / ".lock").read_text())
    assert lock["research_caps"]["per_step"]["3"] == 1
    assert lock["research_caps"]["per_file"]["3-foo.md"] == 1
