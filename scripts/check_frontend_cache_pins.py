#!/usr/bin/env python3
"""Check JS cache-bust pins for frontend modules with parent imports."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONCEPT_PAGE_VIEW = "public/js/concept-page-view.js"
APP_JS = "public/js/app.js"
INDEX_HTML = "public/index.html"


def _first_pin(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _unchanged_pin_failure(
    *,
    changed_path: str,
    parent_path: str,
    asset_name: str,
    pattern: str,
    old_files: dict[str, str],
    new_files: dict[str, str],
) -> str | None:
    old_pin = _first_pin(pattern, old_files.get(parent_path, ""))
    new_pin = _first_pin(pattern, new_files.get(parent_path, ""))
    if new_pin is None:
        return f"{changed_path} changed but {parent_path} does not reference {asset_name}?v="
    if old_pin == new_pin:
        return (
            f"{changed_path} changed but {parent_path} still "
            f"{'imports' if parent_path.endswith('.js') else 'loads'} {asset_name}?v={new_pin}"
        )
    return None


def validate_changed_cache_pins(
    *,
    changed_paths: set[str],
    old_files: dict[str, str],
    new_files: dict[str, str],
) -> list[str]:
    """Return cache-bust failures for changed frontend modules."""
    failures: list[str] = []
    if CONCEPT_PAGE_VIEW in changed_paths:
        failure = _unchanged_pin_failure(
            changed_path=CONCEPT_PAGE_VIEW,
            parent_path=APP_JS,
            asset_name="concept-page-view.js",
            pattern=r"concept-page-view\.js\?v=([0-9]+)",
            old_files=old_files,
            new_files=new_files,
        )
        if failure:
            failures.append(failure)
    if APP_JS in changed_paths:
        failure = _unchanged_pin_failure(
            changed_path=APP_JS,
            parent_path=INDEX_HTML,
            asset_name="app.js",
            pattern=r"app\.js\?v=([0-9]+)",
            old_files=old_files,
            new_files=new_files,
        )
        if failure:
            failures.append(failure)
    return failures


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True)


def _read_old(path: str, compare_ref: str) -> str:
    try:
        return _git("show", f"{compare_ref}:{path}")
    except subprocess.CalledProcessError:
        return ""


def _read_new(path: str) -> str:
    file_path = REPO_ROOT / path
    return file_path.read_text() if file_path.exists() else ""


def main(argv: list[str]) -> int:
    compare_ref = argv[1] if len(argv) > 1 else "HEAD"
    changed = {
        line.strip()
        for line in _git("diff", "--name-only", compare_ref, "--").splitlines()
        if line.strip()
    }
    old_files = {
        APP_JS: _read_old(APP_JS, compare_ref),
        INDEX_HTML: _read_old(INDEX_HTML, compare_ref),
    }
    new_files = {
        APP_JS: _read_new(APP_JS),
        INDEX_HTML: _read_new(INDEX_HTML),
    }
    failures = validate_changed_cache_pins(
        changed_paths=changed,
        old_files=old_files,
        new_files=new_files,
    )
    if failures:
        print("Frontend cache-bust pin check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
