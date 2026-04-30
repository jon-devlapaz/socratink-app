"""Guards against shipping a syntactically broken frontend bundle.

`public/js/app.js` is loaded with `<script type="module">`. A parse error there
takes the whole UI down silently — the deploy is READY but the browser fails to
load the module. This regressed once via merge-conflict residue (orphan tags
and a stray backtick after a closed template literal); the test below would
have caught it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_JS = REPO_ROOT / "public" / "js"


def _module_js_files() -> list[Path]:
    return sorted(p for p in PUBLIC_JS.glob("*.js") if p.is_file())


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
@pytest.mark.parametrize("js_path", _module_js_files(), ids=lambda p: p.name)
def test_module_js_parses(tmp_path: Path, js_path: Path) -> None:
    # Copy under a .mjs extension so `node --check` parses it in module mode,
    # matching how `<script type="module">` evaluates the file in-browser.
    target = tmp_path / f"{js_path.stem}.mjs"
    target.write_bytes(js_path.read_bytes())

    result = subprocess.run(
        ["node", "--check", str(target)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{js_path.relative_to(REPO_ROOT)} failed module parse:\n{result.stderr}"
    )
