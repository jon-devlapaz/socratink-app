#!/usr/bin/env python3
"""Generate health metrics for a Socratink Brain knowledge base."""

from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

CURATED_DIRS = ["doctrine", "mechanisms", "records", "sources", "syntheses"]


@dataclass
class WikiStats:
    total_pages: int = 0
    page_counts: dict = field(default_factory=dict)
    unresolved_issues: int = 0
    stale_decisions: int = 0
    stale_pages_by_type: dict = field(default_factory=dict)
    contradiction_flags: int = 0
    open_question_flags: int = 0
    hypothesis_flags: int = 0
    provenance_covered_pages: int = 0
    provenance_total_pages: int = 0
    raw_source_files: int = 0
    referenced_raw_artifacts: int = 0
    external_artifact_refs: int = 0
    chat_surfaces_expected: int = 0
    chat_surfaces_instrumented: int = 0
    test_surfaces_expected: int = 0
    test_surfaces_instrumented: int = 0
    missing_instrumentation: list[str] = field(default_factory=list)
    evaluated_sessions: int = 0
    evaluated_runs: int = 0

    def report(self) -> str:
        provenance_rate = (self.provenance_covered_pages / self.provenance_total_pages * 100.0) if self.provenance_total_pages else 0.0
        raw_reference_rate = (self.referenced_raw_artifacts / self.raw_source_files * 100.0) if self.raw_source_files else 0.0
        lines = [
            "=== Socratink Brain Stats ===",
            "",
            f"Total curated pages: {self.total_pages}",
            "Page counts:",
        ]
        for page_type, count in sorted(self.page_counts.items()):
            lines.append(f"  {page_type}: {count}")
        lines.extend(
            [
                "",
                f"Unresolved issues: {self.unresolved_issues}",
                f"Stale decisions: {self.stale_decisions}",
                f"Stale curated pages: {sum(self.stale_pages_by_type.values())} ({format_counts(self.stale_pages_by_type)})",
                f"Contradiction flags: {self.contradiction_flags}",
                f"Open-question flags: {self.open_question_flags}",
                f"Hypothesis flags: {self.hypothesis_flags}",
                "",
                f"Provenance coverage: {self.provenance_covered_pages}/{self.provenance_total_pages} pages ({provenance_rate:.1f}%)",
                f"Raw artifact reference rate: {self.referenced_raw_artifacts}/{self.raw_source_files} files ({raw_reference_rate:.1f}%)",
                f"External artifact refs: {self.external_artifact_refs}",
                "",
                f"Chat surface coverage: {self.chat_surfaces_instrumented}/{self.chat_surfaces_expected}",
                f"Test surface coverage: {self.test_surfaces_instrumented}/{self.test_surfaces_expected}",
                f"Missing instrumentation: {len(self.missing_instrumentation)} ({', '.join(self.missing_instrumentation) if self.missing_instrumentation else 'none'})",
                f"Evaluated sessions: {self.evaluated_sessions}",
                f"Evaluated runs: {self.evaluated_runs}",
            ]
        )
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
        return [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
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


def curated_pages(wiki_dir: Path) -> list[Path]:
    pages: list[Path] = []
    for subdir in CURATED_DIRS:
        directory = wiki_dir / subdir
        if directory.exists():
            pages.extend(sorted(directory.glob("*.md")))
    return pages


def count_raw_files(raw_dir: Path) -> int:
    if not raw_dir.exists():
        return 0
    ignored_names = {"README.md", "CLAUDE.md", ".gitkeep"}
    return sum(1 for path in raw_dir.rglob("*") if path.is_file() and not path.name.startswith(".") and path.name not in ignored_names)


def to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def format_counts(counts: dict) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))


def gather_stats(kb_root: Path) -> WikiStats:
    stats = WikiStats()
    wiki_dir = kb_root / "wiki"
    stats.raw_source_files = count_raw_files(kb_root / "raw")
    page_counts = Counter()
    stale_pages_by_type = Counter()
    referenced_raw = set()
    external_refs = set()
    today = date.today()

    for page in curated_pages(wiki_dir):
        content = page.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(content)
        page_type = frontmatter.get("type")
        if not page_type:
            continue

        page_counts[page_type] += 1
        stats.total_pages += 1
        stats.provenance_total_pages += 1

        sources = frontmatter.get("sources", [])
        raw_artifacts = frontmatter.get("raw_artifacts", [])
        if isinstance(sources, list) and sources:
            stats.provenance_covered_pages += 1
        elif page_type == "source" and isinstance(raw_artifacts, list) and raw_artifacts:
            stats.provenance_covered_pages += 1

        flags = frontmatter.get("flags", [])
        if isinstance(flags, list):
            stats.contradiction_flags += sum(1 for flag in flags if flag == "contradiction")
            stats.open_question_flags += sum(1 for flag in flags if flag == "open-question")
            stats.hypothesis_flags += sum(1 for flag in flags if flag == "hypothesis")

        workflow_status = frontmatter.get("workflow_status")
        review_after = frontmatter.get("review_after")
        if review_after:
            try:
                stale = date.fromisoformat(review_after) < today
            except ValueError:
                stale = False
            if stale:
                stale_pages_by_type[page_type] += 1

        if page_type == "issue" and workflow_status == "open":
            stats.unresolved_issues += 1
        if page_type == "decision" and workflow_status == "open":
            if review_after and stale:
                stats.stale_decisions += 1

        if page_type == "source":
            if isinstance(raw_artifacts, list):
                for artifact in raw_artifacts:
                    if isinstance(artifact, str) and artifact.startswith("raw/"):
                        referenced_raw.add(artifact)
                    elif isinstance(artifact, str):
                        external_refs.add(artifact)
            stats.evaluated_sessions += to_int(frontmatter.get("evaluated_sessions"))
            stats.evaluated_runs += to_int(frontmatter.get("evaluated_runs"))

    stats.page_counts = dict(page_counts)
    stats.stale_pages_by_type = dict(stale_pages_by_type)
    stats.referenced_raw_artifacts = len(referenced_raw)
    stats.external_artifact_refs = len(external_refs)

    log_coverage_path = wiki_dir / "log-coverage.md"
    if log_coverage_path.exists():
        coverage = extract_frontmatter(log_coverage_path.read_text(encoding="utf-8"))
        expected_chat = coverage.get("expected_chat_surfaces", [])
        instrumented_chat = coverage.get("instrumented_chat_surfaces", [])
        expected_test = coverage.get("expected_test_surfaces", [])
        instrumented_test = coverage.get("instrumented_test_surfaces", [])
        if isinstance(expected_chat, list):
            stats.chat_surfaces_expected = len(expected_chat)
        if isinstance(instrumented_chat, list):
            stats.chat_surfaces_instrumented = len(instrumented_chat)
        if isinstance(expected_test, list):
            stats.test_surfaces_expected = len(expected_test)
        if isinstance(instrumented_test, list):
            stats.test_surfaces_instrumented = len(instrumented_test)
        missing_instrumentation = coverage.get("missing_instrumentation", [])
        if isinstance(missing_instrumentation, list):
            stats.missing_instrumentation = missing_instrumentation

    return stats


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: wiki_stats.py <kb-root-directory>")
        raise SystemExit(1)

    kb_root = Path(sys.argv[1]).resolve()
    if not kb_root.is_dir():
        print(f"Error: {kb_root} is not a directory")
        raise SystemExit(1)

    stats = gather_stats(kb_root)
    print(stats.report())


if __name__ == "__main__":
    main()
