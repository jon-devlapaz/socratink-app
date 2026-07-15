#!/usr/bin/env python3
"""Fail when canonical agent docs route to stale local references."""
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_DOCS = (
    "AGENTS.md",
    "CLAUDE.md",
    "agents/README.md",
    "agents/QUALITY.md",
    "docs/project/doc-map.md",
    "docs/project/state.md",
)
REQUIRED_REFERENCES = {
    "AGENTS.md": ("agents/QUALITY.md", "$socratink-agent-flow"),
    "CLAUDE.md": ("AGENTS.md", "docs/project/doc-map.md"),
}
RETIRED_TERMS = (
    ".socratink-brain",
    "Context7",
    "agents/founder/WORKFLOWS",
    "scripts/install-hooks.sh",
)
MARKDOWN_LINK_RE = re.compile(r"\[[^]]*]\(([^)]+)\)")
REFERENCE_DEFINITION_RE = re.compile(r"(?m)^\s{0,3}\[([^]]+)]\s*:\s*(\S+)")
REFERENCE_USE_RE = re.compile(r"\[([^]]+)]\[([^]]*)]")
INLINE_CODE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
LOCAL_PATH_RE = re.compile(
    r"(?<![\w.-])(?:"
    r"(?:agents|docs|scripts|tests|public|\.github)/[A-Za-z0-9_./-]+"
    r"|(?:AGENTS|CLAUDE|README|PRODUCT|DESIGN|UBIQUITOUS_LANGUAGE)\.md"
    r"|requirements(?:-dev)?\.txt|vercel\.json|package(?:-lock)?\.json"
    r"|pyrefly\.toml|mypy\.ini"
    r")"
)


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _local_link_target(doc_path: Path, target: str, root: Path) -> Path | None:
    target = target.strip().split(maxsplit=1)[0].strip("<>")
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    return root / target.lstrip("/") if target.startswith("/") else doc_path.parent / target


def validate_document(doc_path: Path, root: Path) -> list[str]:
    text = doc_path.read_text()
    relative_doc = doc_path.relative_to(root).as_posix()
    failures: list[str] = []

    for term in RETIRED_TERMS:
        for match in re.finditer(re.escape(term), text):
            failures.append(
                f"{relative_doc}:{_line_number(text, match.start())}: retired reference `{term}`"
            )

    for match in MARKDOWN_LINK_RE.finditer(text):
        target = _local_link_target(doc_path, match.group(1), root)
        if target is not None and not target.exists():
            failures.append(
                f"{relative_doc}:{_line_number(text, match.start())}: missing link `{match.group(1)}`"
            )

    definitions = {
        match.group(1).casefold(): match for match in REFERENCE_DEFINITION_RE.finditer(text)
    }
    for match in definitions.values():
        target = _local_link_target(doc_path, match.group(2), root)
        if target is not None and not target.exists():
            failures.append(
                f"{relative_doc}:{_line_number(text, match.start())}: missing link `{match.group(2)}`"
            )
    for match in REFERENCE_USE_RE.finditer(text):
        label = (match.group(2) or match.group(1)).casefold()
        if label not in definitions:
            failures.append(
                f"{relative_doc}:{_line_number(text, match.start())}: undefined link reference `{label}`"
            )

    for code_match in INLINE_CODE_RE.finditer(text):
        for path_match in LOCAL_PATH_RE.finditer(code_match.group(1)):
            reference = path_match.group(0).rstrip("./")
            if reference and not (root / reference).exists():
                failures.append(
                    f"{relative_doc}:{_line_number(text, code_match.start())}: missing path `{reference}`"
                )

    for required in REQUIRED_REFERENCES.get(relative_doc, ()):
        if required not in text:
            failures.append(f"{relative_doc}: missing required route `{required}`")

    return sorted(set(failures))


def validate(root: Path = REPO_ROOT) -> list[str]:
    failures: list[str] = []
    for relative_doc in CANONICAL_DOCS:
        doc_path = root / relative_doc
        if not doc_path.is_file():
            failures.append(f"{relative_doc}: canonical doc is missing")
            continue
        failures.extend(validate_document(doc_path, root))
    return sorted(failures)


def main() -> int:
    failures = validate()
    if failures:
        print("[agent-docs] FAIL: stale agent documentation:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("[agent-docs] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
