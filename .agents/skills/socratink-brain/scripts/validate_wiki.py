#!/usr/bin/env python3
"""Validate structural integrity of a Socratink Brain knowledge base.

Checks deterministic structure only:
- required directories/files
- required frontmatter fields
- valid enum values
- required sections by page type
- reachable/indexed curated pages
- review_after presence where required
- log coverage manifest completeness
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_DIRS = [
    "raw",
    "wiki",
    "wiki/doctrine",
    "wiki/mechanisms",
    "wiki/records",
    "wiki/sources",
    "wiki/syntheses",
]

REQUIRED_FILES = [
    "CLAUDE.md",
    "ACTIVE.md",
    "wiki/index.md",
    "wiki/log.md",
    "wiki/log-coverage.md",
]

CURATED_DIRS = ["doctrine", "mechanisms", "records", "sources", "syntheses"]
PAGE_TYPES = {
    "doctrine",
    "mechanism",
    "decision",
    "issue",
    "experiment",
    "finding",
    "source",
    "synthesis",
}
BASIS_VALUES = {"sourced", "inferred"}
CONFIDENCE_VALUES = {"high", "medium", "low", "speculative"}
FLAG_VALUES = {"hypothesis", "open-question", "contradiction"}
LOG_SURFACE_VALUES = {"drill", "replay", "none"}
WORKFLOW_BY_TYPE = {
    "doctrine": {"active", "deprecated", "obsolete"},
    "mechanism": {"active", "deprecated", "obsolete"},
    "source": {"active", "deprecated", "obsolete"},
    "decision": {"open", "resolved", "obsolete"},
    "issue": {"open", "resolved", "obsolete"},
    "experiment": {"open", "resolved", "obsolete"},
    "finding": {"open", "resolved", "obsolete"},
    "synthesis": {"open", "resolved", "obsolete"},
}
SOURCE_KIND_VALUES = {
    "product-doc",
    "research-note",
    "drill-chat-log",
    "drill-run-log",
    "drill-turn-log",
    "product-chat-log",
    "test-replay-log",
    "bug-report",
    "screenshot",
    "experiment-note",
}
REQUIRED_SECTIONS = {
    "doctrine": ["## Principle", "## Evidence", "## Product Implication"],
    "mechanism": ["## Mechanism", "## Evidence", "## Product Implication"],
    "decision": [
        "## Decision",
        "## Evidence",
        "## Inference",
        "## Product Implication",
    ],
    "issue": ["## What Broke", "## Evidence", "## Product Implication"],
    "experiment": [
        "## Change",
        "## Evidence",
        "## Inference",
        "## Product Implication",
    ],
    "finding": ["## Finding", "## Evidence", "## Product Implication"],
    "source": ["## Summary", "## Raw Artifacts", "## Connections"],
    "synthesis": [
        "## Pattern",
        "## Evidence",
        "## Inference",
        "## Product Implication",
    ],
}
LOG_COVERAGE_FIELDS = {
    "title",
    "type",
    "updated",
    "expected_chat_surfaces",
    "instrumented_chat_surfaces",
    "expected_test_surfaces",
    "instrumented_test_surfaces",
    "current_log_files",
    "missing_instrumentation",
}
LOG_COVERAGE_SECTIONS = [
    "## Current Log Adapters",
    "## Missing Instrumentation",
    "## Notes",
]


@dataclass
class Result:
    success: bool = True
    issues: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def add_issue(self, severity: str, message: str) -> None:
        self.issues.append({"severity": severity, "message": message})
        if severity in {"error", "warning"}:
            self.success = False

    def report(self) -> str:
        if not self.issues:
            return f"Wiki is healthy. Stats: {self.stats}"
        lines = [f"Found {len(self.issues)} issue(s):"]
        icons = {"error": "E", "warning": "W", "info": "I"}
        for issue in self.issues:
            lines.append(f"  [{icons.get(issue['severity'], '?')}] {issue['message']}")
        if self.stats:
            lines.append(f"\nStats: {self.stats}")
        return "\n".join(lines)


def extract_frontmatter_block(content: str) -> str:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", content, re.DOTALL)
    return match.group(1) if match else ""


def parse_scalar(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [
            item.strip().strip('"').strip("'")
            for item in inner.split(",")
            if item.strip()
        ]
    return value.strip('"').strip("'")


def extract_frontmatter(content: str) -> dict:
    block = extract_frontmatter_block(content)
    data = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = parse_scalar(value)
    return data


def extract_links(content: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", content)


def curated_pages(wiki_dir: Path) -> list[Path]:
    pages: list[Path] = []
    for subdir in CURATED_DIRS:
        directory = wiki_dir / subdir
        if directory.exists():
            pages.extend(sorted(directory.glob("*.md")))
    return pages


def normalize_page_rel(wiki_dir: Path, page: Path) -> str:
    return str(page.relative_to(wiki_dir))


def resolve_link(page: Path, wiki_dir: Path, link: str) -> str:
    resolved = (page.parent / link).resolve()
    try:
        return str(resolved.relative_to(wiki_dir.resolve()))
    except ValueError:
        return os.path.normpath(os.path.relpath(resolved, wiki_dir))


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def resolve_source_entry(page: Path, kb_root: Path, source: str) -> Path:
    if source.startswith("raw/"):
        return kb_root / source
    if source.startswith("docs/"):
        return kb_root.parent / source
    return page.parent / source


def validate_required_structure(kb_root: Path, result: Result) -> bool:
    for rel in REQUIRED_DIRS:
        if not (kb_root / rel).exists():
            result.add_issue("error", f"Missing required directory: {rel}")
    for rel in REQUIRED_FILES:
        if not (kb_root / rel).exists():
            result.add_issue("error", f"Missing required file: {rel}")
    return result.success


def validate_page_frontmatter(
    relpath: str, frontmatter: dict, content: str, result: Result
) -> None:
    page_type = frontmatter.get("type")
    if page_type not in PAGE_TYPES:
        result.add_issue("warning", f"{relpath} has invalid type '{page_type}'")
        return

    required_fields = {
        "title",
        "type",
        "updated",
        "related",
        "basis",
        "workflow_status",
        "flags",
    }
    if page_type != "source":
        required_fields.add("sources")
    for field_name in sorted(required_fields - set(frontmatter.keys())):
        result.add_issue("warning", f"{relpath} missing required field '{field_name}'")

    if frontmatter.get("basis") not in BASIS_VALUES:
        result.add_issue(
            "warning", f"{relpath} has invalid basis '{frontmatter.get('basis')}'"
        )

    if page_type != "source":
        if "confidence" not in frontmatter:
            result.add_issue(
                "warning", f"{relpath} missing required field 'confidence'"
            )
        elif frontmatter.get("confidence") not in CONFIDENCE_VALUES:
            result.add_issue(
                "warning",
                f"{relpath} has invalid confidence '{frontmatter.get('confidence')}'",
            )

    flags = frontmatter.get("flags", [])
    if not isinstance(flags, list):
        result.add_issue("warning", f"{relpath} flags must be a list")
    else:
        for flag in sorted(flag for flag in flags if flag not in FLAG_VALUES):
            result.add_issue("warning", f"{relpath} has invalid flag '{flag}'")

    workflow_status = frontmatter.get("workflow_status")
    if workflow_status not in WORKFLOW_BY_TYPE[page_type]:
        result.add_issue(
            "warning",
            f"{relpath} has invalid workflow_status '{workflow_status}' for type '{page_type}'",
        )

    if page_type == "decision" and not frontmatter.get("review_after"):
        result.add_issue(
            "warning", f"{relpath} is a decision record without review_after"
        )

    if page_type == "source":
        if frontmatter.get("source_kind") not in SOURCE_KIND_VALUES:
            result.add_issue(
                "warning",
                f"{relpath} has invalid source_kind '{frontmatter.get('source_kind')}'",
            )
        for field_name in (
            "raw_artifacts",
            "log_surface",
            "evaluated_sessions",
            "evaluated_runs",
        ):
            if field_name not in frontmatter:
                result.add_issue(
                    "warning", f"{relpath} source page missing {field_name}"
                )
        if frontmatter.get("log_surface") not in LOG_SURFACE_VALUES:
            result.add_issue(
                "warning",
                f"{relpath} has invalid log_surface '{frontmatter.get('log_surface')}'",
            )

    for section in REQUIRED_SECTIONS[page_type]:
        if section not in content:
            result.add_issue(
                "warning", f"{relpath} missing required section '{section}'"
            )


def validate_source_paths(
    page: Path, kb_root: Path, wiki_dir: Path, frontmatter: dict, result: Result
) -> None:
    relpath = normalize_page_rel(wiki_dir, page)
    page_type = frontmatter.get("type")

    sources = frontmatter.get("sources", [])
    related = frontmatter.get("related", [])
    if isinstance(sources, list) and isinstance(related, list):
        overlap = sorted(set(sources).intersection(related))
        for entry in overlap:
            result.add_issue(
                "warning", f"{relpath} has duplicate sources/related entry '{entry}'"
            )

    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, str) or not source:
                continue
            resolved = resolve_source_entry(page, kb_root, source)
            if page_type != "source":
                if is_under(resolved, wiki_dir / "sources"):
                    pass
                elif is_under(resolved, kb_root.parent / "docs"):
                    pass
                else:
                    result.add_issue(
                        "warning",
                        f"{relpath} sources entry must point to a source page or repo doc: {source}",
                    )
            if not resolved.exists():
                result.add_issue(
                    "warning", f"{relpath} sources entry does not resolve: {source}"
                )

    if frontmatter.get("type") == "source":
        raw_artifacts = frontmatter.get("raw_artifacts", [])
        if isinstance(raw_artifacts, list):
            for artifact in raw_artifacts:
                if (
                    isinstance(artifact, str)
                    and artifact.startswith("raw/")
                    and not (kb_root / artifact).is_file()
                ):
                    result.add_issue(
                        "warning",
                        f"{relpath} raw_artifacts entry does not resolve to a file: {artifact}",
                    )


def validate_log_coverage(
    kb_root: Path, log_coverage_path: Path, result: Result
) -> None:
    content = log_coverage_path.read_text(encoding="utf-8")
    frontmatter = extract_frontmatter(content)

    for field_name in sorted(LOG_COVERAGE_FIELDS - set(frontmatter.keys())):
        result.add_issue(
            "warning", f"wiki/log-coverage.md missing required field '{field_name}'"
        )

    if frontmatter.get("type") != "log-coverage":
        result.add_issue(
            "warning", "wiki/log-coverage.md must have type 'log-coverage'"
        )

    list_fields = (
        "expected_chat_surfaces",
        "instrumented_chat_surfaces",
        "expected_test_surfaces",
        "instrumented_test_surfaces",
        "current_log_files",
        "missing_instrumentation",
    )
    for field_name in list_fields:
        value = frontmatter.get(field_name)
        if value is not None and not isinstance(value, list):
            result.add_issue(
                "warning", f"wiki/log-coverage.md field '{field_name}' must be a list"
            )

    current_log_files = frontmatter.get("current_log_files", [])
    if isinstance(current_log_files, list):
        for log_file in current_log_files:
            if (
                isinstance(log_file, str)
                and log_file
                and not (kb_root.parent / log_file).is_file()
            ):
                result.add_issue(
                    "info",
                    f"wiki/log-coverage.md current_log_files entry not present in this checkout: {log_file}",
                )

    for section in LOG_COVERAGE_SECTIONS:
        if section not in content:
            result.add_issue(
                "warning", f"wiki/log-coverage.md missing required section '{section}'"
            )


def validate_active_queue(
    kb_root: Path, wiki_dir: Path, pages: list[Path], result: Result
) -> None:
    active_path = kb_root / "ACTIVE.md"
    if not active_path.exists():
        return

    content = active_path.read_text(encoding="utf-8")
    curated_page_rels = {normalize_page_rel(wiki_dir, page) for page in pages}
    match = re.search(
        r"^Current promoted items:\s*\n(?P<body>.*?)(?:\n## |\Z)",
        content,
        re.DOTALL | re.MULTILINE,
    )
    if not match:
        result.add_issue(
            "warning", "ACTIVE.md missing 'Current promoted items:' section"
        )
        return

    bullets = [
        line.strip()
        for line in match.group("body").splitlines()
        if line.strip().startswith("- ")
    ]
    if len(bullets) > 5:
        result.add_issue(
            "warning", f"ACTIVE.md has {len(bullets)} promoted items; maximum is 5"
        )

    for bullet in bullets:
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", bullet)
        if not links:
            result.add_issue(
                "warning", f"ACTIVE.md item missing curated wiki link: {bullet}"
            )
            continue
        for link in links:
            if not link.startswith("wiki/"):
                result.add_issue(
                    "warning", f"ACTIVE.md item link must start with wiki/: {link}"
                )
                continue
            wiki_link = os.path.normpath(link.removeprefix("wiki/"))
            if not (kb_root / link).is_file():
                result.add_issue(
                    "warning", f"ACTIVE.md item link does not resolve: {link}"
                )
            elif wiki_link not in curated_page_rels:
                result.add_issue(
                    "warning",
                    f"ACTIVE.md item link must point to a curated wiki page: {link}",
                )
        if "docs/project/state.md#current-release-goal" not in bullet:
            result.add_issue(
                "warning", f"ACTIVE.md item missing release-goal citation: {bullet}"
            )


def validate_reachability(wiki_dir: Path, pages: list[Path], result: Result) -> None:
    page_map = {normalize_page_rel(wiki_dir, page): page for page in pages}
    adjacency: dict[str, set[str]] = defaultdict(set)

    index_links = extract_links((wiki_dir / "index.md").read_text(encoding="utf-8"))
    root_targets: set[str] = set()
    for link in index_links:
        normalized = os.path.normpath(link)
        if normalized in page_map:
            root_targets.add(normalized)
        elif not (wiki_dir / normalized).exists() and normalized != "log-coverage.md":
            result.add_issue(
                "warning", f"wiki/index.md references missing page '{normalized}'"
            )

    for page in pages:
        relpath = normalize_page_rel(wiki_dir, page)
        content = page.read_text(encoding="utf-8")
        for link in extract_links(content):
            target = resolve_link(page, wiki_dir, link)
            if target in page_map:
                adjacency[relpath].add(target)
            elif not (page.parent / link).exists():
                result.add_issue("warning", f"Broken link in {relpath}: {link}")

    reachable = set(root_targets)
    queue = deque(root_targets)
    while queue:
        current = queue.popleft()
        for nxt in adjacency.get(current, set()):
            if nxt not in reachable:
                reachable.add(nxt)
                queue.append(nxt)

    for relpath in page_map:
        if relpath not in reachable:
            result.add_issue(
                "warning", f"Curated page not reachable from wiki/index.md: {relpath}"
            )

    result.stats["indexed_roots"] = len(root_targets)
    result.stats["reachable_pages"] = len(reachable)


def validate(kb_root: Path) -> Result:
    result = Result()
    if not validate_required_structure(kb_root, result):
        return result

    wiki_dir = kb_root / "wiki"
    pages = curated_pages(wiki_dir)
    result.stats["total_curated_pages"] = len(pages)
    page_counts: dict[str, int] = defaultdict(int)

    for page in pages:
        relpath = normalize_page_rel(wiki_dir, page)
        content = page.read_text(encoding="utf-8")
        if not content.startswith("---"):
            result.add_issue("warning", f"{relpath} missing frontmatter")
            continue
        frontmatter = extract_frontmatter(content)
        page_counts[frontmatter.get("type", "unknown")] += 1
        validate_page_frontmatter(relpath, frontmatter, content, result)
        validate_source_paths(page, kb_root, wiki_dir, frontmatter, result)

    validate_log_coverage(kb_root, wiki_dir / "log-coverage.md", result)
    validate_active_queue(kb_root, wiki_dir, pages, result)
    validate_reachability(wiki_dir, pages, result)
    result.stats["page_counts"] = dict(page_counts)
    return result


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: validate_wiki.py <kb-root-directory>")
        raise SystemExit(1)

    kb_root = Path(sys.argv[1]).resolve()
    if not kb_root.is_dir():
        print(f"Error: {kb_root} is not a directory")
        raise SystemExit(1)

    result = validate(kb_root)
    print(result.report())
    raise SystemExit(0 if result.success else 10)


if __name__ == "__main__":
    main()
