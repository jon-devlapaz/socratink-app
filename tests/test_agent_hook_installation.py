from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_agents_canon_scaffold_exists() -> None:
    required = [
        REPO_ROOT / "agents" / "README.md",
        REPO_ROOT / "agents" / "LEARNINGS.md",
        REPO_ROOT / "agents" / "QUALITY.md",
    ]
    missing = [str(path.relative_to(REPO_ROOT)) for path in required if not path.exists()]
    assert not missing, f"missing agent canon scaffold: {missing}"


def test_archived_founder_docs_exist_outside_active_canon() -> None:
    path = REPO_ROOT / "ARCHIVED_FOUNDER_DOCS" / "agents" / "founder" / "WORKFLOWS" / "01-git-integration.md"
    assert path.exists(), "missing archived git-integration workflow card"


def test_root_adapters_point_to_agents_canon() -> None:
    for rel in ("AGENTS.md", "CLAUDE.md"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "agents/" in text or "docs/project/doc-map.md" in text


def test_quality_doc_acknowledges_active_canon() -> None:
    quality = (REPO_ROOT / "agents" / "QUALITY.md").read_text(encoding="utf-8")
    assert "AGENTS.md" in quality
    assert "docs/project/doc-map.md" in quality


def test_bootstrap_script_wires_repo_hook_path() -> None:
    text = (REPO_ROOT / "scripts" / "bootstrap-python.sh").read_text(encoding="utf-8")
    assert "core.hooksPath" in text
    assert "scripts/git-hooks" in text


def test_doctor_checks_hook_installation() -> None:
    text = (REPO_ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
    assert "core.hooksPath" in text or "git config --local --default '' core.hooksPath" in text
    assert "scripts/git-hooks" in text
