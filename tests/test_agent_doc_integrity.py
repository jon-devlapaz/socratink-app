from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER_PATH = REPO_ROOT / "scripts" / "check_agent_docs.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_agent_docs", CHECKER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_agent_docs_match_live_repo_routes() -> None:
    checker = _load_checker()

    assert checker.validate(REPO_ROOT) == []


def test_agent_doc_checker_reports_stale_references(tmp_path: Path) -> None:
    checker = _load_checker()
    doc = tmp_path / "AGENTS.md"
    doc.write_text("Use `scripts/gone.sh` and Context7.\n")

    assert set(checker.validate_document(doc, tmp_path)) == {
        "AGENTS.md:1: missing path `scripts/gone.sh`",
        "AGENTS.md:1: retired reference `Context7`",
        "AGENTS.md: missing required route `$socratink-agent-flow`",
        "AGENTS.md: missing required route `agents/QUALITY.md`",
    }


def test_agent_doc_checker_validates_reference_style_links(tmp_path: Path) -> None:
    checker = _load_checker()
    doc = tmp_path / "notes.md"
    doc.write_text(
        "Read [quality][quality] and [missing][unknown].\n"
        "[quality]: agents/missing.md \"Agent quality\"\n"
    )

    assert checker.validate_document(doc, tmp_path) == [
        "notes.md:1: undefined link reference `unknown`",
        "notes.md:2: missing link `agents/missing.md`",
    ]
