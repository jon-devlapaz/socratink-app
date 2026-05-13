from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_agents_canon_scaffold_exists() -> None:
    required = [
        REPO_ROOT / "agents" / "README.md",
        REPO_ROOT / "agents" / "MIGRATION.md",
        REPO_ROOT / "agents" / "_templates" / "workflow-card.md",
    ]
    missing = [str(path.relative_to(REPO_ROOT)) for path in required if not path.exists()]
    assert not missing, f"missing agent canon scaffold: {missing}"


def test_git_integration_workflow_exists_and_mentions_v1_scope() -> None:
    path = REPO_ROOT / "agents" / "founder" / "WORKFLOWS" / "01-git-integration.md"
    assert path.exists(), "missing git-integration workflow card"
    text = path.read_text(encoding="utf-8")
    assert "origin/dev" in text
    assert "origin/feat/*" in text
    assert "no-mistakes/dev" in text
    assert "push publication" in text


def test_root_adapters_point_to_agents_canon() -> None:
    for rel in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "agents/" in text, f"{rel} must point to canonical agents/ path"


def test_bootstrap_docs_acknowledge_agents_canon() -> None:
    onboarding = (REPO_ROOT / "docs" / "codex" / "onboarding.md").read_text(encoding="utf-8")
    quality = (REPO_ROOT / "docs" / "codex" / "agent-quality.md").read_text(encoding="utf-8")
    assert "agents/" in onboarding
    assert "agents/" in quality
