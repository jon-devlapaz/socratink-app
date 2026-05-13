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
