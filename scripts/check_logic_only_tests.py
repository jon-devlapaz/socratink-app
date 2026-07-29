#!/usr/bin/env python3
"""Reject automated tests that couple to browser-rendered interface details."""

from __future__ import annotations

import argparse
import ast
import re
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_TEST_PATH_PARTS = {
    "browser",
    "e2e",
    "snapshots",
    "ui",
    "visual",
}
FORBIDDEN_TEST_NAME_TOKENS = {
    "accessibility",
    "dom",
    "layout",
    "markup",
    "selector",
    "snapshot",
    "ui",
    "visual",
}
FORBIDDEN_IMPORT_ROOTS = {
    "playwright",
    "pytest_playwright",
    "pyppeteer",
    "selenium",
}
FORBIDDEN_ATTRIBUTES = {
    "bounding_box",
    "get_by_label",
    "get_by_placeholder",
    "get_by_role",
    "get_by_test_id",
    "get_by_text",
    "locator",
    "query_selector",
    "query_selector_all",
    "screenshot",
    "wait_for_selector",
}
LITERAL_RULES = (
    (
        "DOM test seam",
        re.compile(
            r"\b(?:globalThis\.)?document\."
            r"(?:createElement|getElementById|querySelector|querySelectorAll)\b"
        ),
    ),
    (
        "rendered HTML contract",
        re.compile(r"\brender[A-Za-z0-9_]*Html\b"),
    ),
    (
        "frontend asset contract",
        re.compile(
            r"(?:public/(?:index\.html|css/)|login\.(?:html|css))",
            re.IGNORECASE,
        ),
    ),
    (
        "markup attribute contract",
        re.compile(
            r"(?:aria-(?:checked|current|label|live)|"
            r"data-(?:testid|theme)|(?:class|id)=[\"'])",
            re.IGNORECASE,
        ),
    ),
    (
        "HTML element contract",
        re.compile(
            r"<(?:button|dialog|form|input|nav|section|textarea)\b",
            re.IGNORECASE,
        ),
    ),
)
RUNNER_RULES = (
    "chromium",
    "cypress",
    "monocart-coverage-reports",
    "playwright",
    "pytest-playwright",
    "selenium",
    "tests/e2e",
)
RUNNER_FILES = (
    "package.json",
    "package-lock.json",
    "pytest.ini",
    "requirements-dev.txt",
    "scripts/check-coverage.sh",
    "scripts/doctor.sh",
    "scripts/test-cov.sh",
)
TEST_SOURCE_SUFFIXES = {
    ".cjs",
    ".js",
    ".jsx",
    ".mjs",
    ".py",
    ".ts",
    ".tsx",
}
NON_PYTHON_BROWSER_API_RE = re.compile(
    r"\b(?:boundingBox|getByLabel|getByRole|getByTestId|getByText|"
    r"locator|querySelector|querySelectorAll|screenshot|waitForSelector)\s*\("
)


def _test_files(root: Path) -> list[Path]:
    tests_root = root / "tests"
    if not tests_root.is_dir():
        return []
    return sorted(
        path
        for path in tests_root.rglob("*")
        if path.is_file()
        and path.suffix in TEST_SOURCE_SUFFIXES
        and (
            path.name.startswith("test_")
            or "_test." in path.name
            or ".test." in path.name
            or ".spec." in path.name
        )
    )


def _runner_files(root: Path) -> list[Path]:
    paths = [root / relative for relative in RUNNER_FILES]
    workflow_root = root / ".github" / "workflows"
    if workflow_root.is_dir():
        paths.extend(workflow_root.glob("*.yml"))
        paths.extend(workflow_root.glob("*.yaml"))
    return sorted(path for path in paths if path.is_file())


def _import_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _string_literals(tree: ast.AST) -> str:
    return "\n".join(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )


def _name_tokens(names: list[str]) -> set[str]:
    return {
        token
        for name in names
        for token in re.split(r"[^a-z0-9]+", name.casefold())
        if token
    }


def validate_test_file(path: Path, root: Path) -> list[str]:
    relative = path.relative_to(root).as_posix()
    failures: list[str] = []

    relative_path = path.relative_to(root)
    forbidden_parts = FORBIDDEN_TEST_PATH_PARTS.intersection(relative_path.parts)
    if forbidden_parts:
        failures.append(
            f"{relative}: forbidden test path `{sorted(forbidden_parts)[0]}`"
        )

    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [*failures, f"{relative}: cannot inspect test: {exc}"]

    forbidden_names = FORBIDDEN_TEST_NAME_TOKENS.intersection(
        _name_tokens([path.name])
    )
    if forbidden_names:
        failures.append(
            f"{relative}: UI-coupled test name `{sorted(forbidden_names)[0]}`"
        )

    if path.suffix != ".py":
        if NON_PYTHON_BROWSER_API_RE.search(source):
            failures.append(f"{relative}: browser assertion API")
        for root_name in FORBIDDEN_IMPORT_ROOTS:
            if re.search(
                rf"(?:from\s+|require\([\"']){re.escape(root_name)}(?:[/.\"'])",
                source,
            ):
                failures.append(
                    f"{relative}: browser automation import `{root_name}`"
                )
        for label, pattern in LITERAL_RULES:
            if pattern.search(source):
                failures.append(f"{relative}: {label}")
        return failures

    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError as exc:
        return [*failures, f"{relative}: cannot inspect test: {exc}"]

    test_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        and node.name.startswith("test")
    ]
    forbidden_names = FORBIDDEN_TEST_NAME_TOKENS.intersection(
        _name_tokens(test_names)
    )
    if forbidden_names:
        failures.append(
            f"{relative}: UI-coupled test name `{sorted(forbidden_names)[0]}`"
        )

    forbidden_imports = FORBIDDEN_IMPORT_ROOTS.intersection(_import_roots(tree))
    if forbidden_imports:
        failures.append(
            f"{relative}: browser automation import `{sorted(forbidden_imports)[0]}`"
        )

    attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    forbidden_attributes = FORBIDDEN_ATTRIBUTES.intersection(attributes)
    if forbidden_attributes:
        failures.append(
            f"{relative}: browser assertion API `{sorted(forbidden_attributes)[0]}`"
        )

    literals = _string_literals(tree)
    for label, pattern in LITERAL_RULES:
        if "source_intake" in relative_path.parts and label in {
            "HTML element contract",
            "markup attribute contract",
        }:
            continue
        if pattern.search(literals):
            failures.append(f"{relative}: {label}")

    return failures


def validate(root: Path = REPO_ROOT) -> list[str]:
    failures: list[str] = []
    for path in _test_files(root):
        failures.extend(validate_test_file(path, root))

    for path in _runner_files(root):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8").casefold()
        for token in RUNNER_RULES:
            if token in text:
                failures.append(
                    f"{relative}: forbidden UI-test runner token `{token}`"
                )

    return sorted(set(failures))


def self_test() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        bad_test = root / "tests" / "e2e" / "test_smoke.py"
        bad_test.parent.mkdir(parents=True)
        bad_test.write_text(
            "from playwright.sync_api import Page\n"
            "def test_ui(page: Page):\n"
            "    snippet = 'globalThis.document.getElementById(\"door\")'\n"
            "    assert snippet\n",
            encoding="utf-8",
        )
        (root / "package.json").write_text(
            '{"devDependencies":{"playwright":"1.0.0"}}',
            encoding="utf-8",
        )
        js_test = root / "tests" / "door.spec.js"
        js_test.write_text(
            "test('door', () => document.querySelector('#door'));\n",
            encoding="utf-8",
        )
        failures = validate(root)

    expected = (
        "forbidden test path",
        "UI-coupled test name",
        "browser automation import",
        "DOM test seam",
        "browser assertion API",
        "forbidden UI-test runner token",
    )
    missing = [label for label in expected if not any(label in item for item in failures)]
    if missing:
        print(f"[logic-only-tests] SELF-TEST FAIL: missing {', '.join(missing)}")
        return 1
    print("[logic-only-tests] SELF-TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=REPO_ROOT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    failures = validate(args.root.resolve())
    if failures:
        print("[logic-only-tests] FAIL: UI-coupled automated tests found")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"[logic-only-tests] OK: {len(_test_files(args.root.resolve()))} test files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
