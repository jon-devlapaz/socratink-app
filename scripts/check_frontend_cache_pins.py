#!/usr/bin/env python3
"""Check cache-bust pins for versioned frontend references."""
from __future__ import annotations

import posixpath
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
APP_JS = "public/js/app.js"
LAUNCH_PAD_JS = "public/js/launch-pad.js"
CSS_INDEX = "public/css/index.css"
INDEX_HTML = "public/index.html"
STYLES_CSS = "public/styles.css"
VERSIONED_PARENT_PATHS = (
    APP_JS,
    LAUNCH_PAD_JS,
    CSS_INDEX,
    INDEX_HTML,
    STYLES_CSS,
)
_VERSIONED_REFERENCE_RE = re.compile(
    r"(?P<quote>['\"])(?P<asset>[^'\"]+?)\?v=(?P<pin>[0-9]+)(?:[&#][^'\"]*)?(?P=quote)"
)


def _resolve_public_path(parent_path: str, asset: str) -> str | None:
    if re.match(r"^[a-z][a-z0-9+.-]*:", asset, re.IGNORECASE):
        return None
    if asset.startswith("//"):
        return None
    if asset.startswith("/"):
        normalized = posixpath.normpath(asset.lstrip("/"))
        return f"public/{normalized}" if normalized != "." else None
    parent_dir = posixpath.dirname(parent_path)
    normalized = posixpath.normpath(posixpath.join(parent_dir, asset))
    return normalized if normalized.startswith("public/") else None


def _versioned_references(files: dict[str, str]) -> dict[tuple[str, str], tuple[str, str]]:
    references: dict[tuple[str, str], tuple[str, str]] = {}
    for parent_path in VERSIONED_PARENT_PATHS:
        for match in _VERSIONED_REFERENCE_RE.finditer(files.get(parent_path, "")):
            asset = match.group("asset")
            child_path = _resolve_public_path(parent_path, asset)
            if child_path is None:
                continue
            references[(child_path, parent_path)] = (
                posixpath.basename(asset),
                match.group("pin"),
            )
    return references


def _reference_verb(parent_path: str) -> str:
    return "imports" if parent_path.endswith((".css", ".js")) else "loads"


def validate_changed_cache_pins(
    *,
    changed_paths: set[str],
    old_files: dict[str, str],
    new_files: dict[str, str],
) -> list[str]:
    """Return cache-bust failures for changed versioned frontend assets."""
    failures: list[str] = []
    old_references = _versioned_references(old_files)
    new_references = _versioned_references(new_files)
    for (child_path, parent_path), (asset_name, new_pin) in sorted(new_references.items()):
        if child_path not in changed_paths:
            continue
        old_reference = old_references.get((child_path, parent_path))
        if old_reference is None:
            continue
        _old_asset_name, old_pin = old_reference
        if old_pin == new_pin:
            failures.append(
                f"{child_path} changed but {parent_path} still "
                f"{_reference_verb(parent_path)} {asset_name}?v={new_pin}"
            )
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
        path: _read_old(path, compare_ref) for path in VERSIONED_PARENT_PATHS
    }
    new_files = {
        path: _read_new(path) for path in VERSIONED_PARENT_PATHS
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
