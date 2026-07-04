"""App shell navigation and icon contract tests."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_app_shell_uses_organic_icon_contract() -> None:
    index_html = (REPO_ROOT / "public" / "index.html").read_text()
    components_css = (REPO_ROOT / "public" / "css" / "components.css").read_text()

    assert index_html.count('class="sidebar-nav-icon"') == 5
    assert "edit_note</span> Start learning" not in index_html
    assert "view_quilt</span> Desk" not in index_html
    assert "auto_stories</span> Library" not in index_html
    assert "Learning loop" not in index_html
    assert 'id="nav-loop"' not in index_html
    assert "Source-less loop" not in index_html
    assert "rate_review</span> Send Feedback" not in index_html
    assert "Material+Symbols" not in index_html
    assert ".sidebar-nav-icon" in components_css
    assert 'content: "cloud_sync"' not in components_css
