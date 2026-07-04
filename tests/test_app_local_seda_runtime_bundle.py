"""App-local SEDA runtime source-control boundary tests."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TUI_DIR = REPO_ROOT / "scripts" / "socratink_tui"
LOOP_SERVER_WRAPPER = REPO_ROOT / "socratink-loop-server"
LOOP_SERVER = REPO_ROOT / "loop-server.mjs"
APP_LOCAL_RUNTIME_PATHS = (
    REPO_ROOT / "lib" / "README.md",
    REPO_ROOT / "lib" / "seda",
    REPO_ROOT / "lib" / "loop-server",
    REPO_ROOT / "bridge.py",
    REPO_ROOT / "bridge_lib",
    REPO_ROOT / "vendor" / "python" / "ai_service.py",
    REPO_ROOT / "learning_cases" / "cases.jsonl",
    REPO_ROOT / "pedagogical_agents" / "contracts.json",
    REPO_ROOT / "public" / "loop" / "README.md",
)


def test_loop_runtime_wrappers_make_runtime_boundary_explicit() -> None:
    loop_wrapper = LOOP_SERVER_WRAPPER.read_text()
    tui_readme = (TUI_DIR / "README.md").read_text()

    assert LOOP_SERVER.exists()
    assert "loop-server-control" not in loop_wrapper
    assert "source " not in loop_wrapper
    assert 'export PORT="${PORT:-8787}"' in loop_wrapper
    assert "exec node --no-warnings loop-server.mjs" in loop_wrapper

    assert "legacy founder terminal lab" in tui_readme
    assert "not the learner product runtime" in tui_readme
    assert "lib/seda/" in tui_readme
    assert "lib/loop-server/" in tui_readme


def test_app_local_seda_runtime_bundle_has_source_control_anchors() -> None:
    missing = [
        str(path.relative_to(REPO_ROOT))
        for path in APP_LOCAL_RUNTIME_PATHS
        if not path.exists()
    ]
    assert missing == []

    root_readme = (REPO_ROOT / "README.md").read_text()
    lib_readme = (REPO_ROOT / "lib" / "README.md").read_text()
    loop_readme = (REPO_ROOT / "public" / "loop" / "README.md").read_text()

    assert "app-local SEDA loop runtime" in root_readme
    assert "sibling `socratink-tui-agent` checkout" in root_readme
    assert "Node runtime that powers app-local SEDA sessions" in lib_readme
    assert "does not depend on a\nsibling checkout" in lib_readme
    assert "debug and backcompat surface" in loop_readme
    assert "not through a visible `#nav-loop` route" in loop_readme
