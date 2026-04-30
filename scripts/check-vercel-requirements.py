#!/usr/bin/env python3
"""Validate the Python dependency surface Vercel parses during builds."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_INPUT = REPO_ROOT / "requirements.in"
VERCEL_REQUIREMENTS = REPO_ROOT / "requirements.txt"


def _meaningful_lines(path: Path) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append((line_number, stripped))
    return lines


def _check_vercel_parser_surface(lines: list[tuple[int, str]]) -> list[str]:
    errors: list[str] = []
    for line_number, line in lines:
        if line.startswith("-"):
            errors.append(
                f"{VERCEL_REQUIREMENTS.name}:{line_number}: remove pip option/include `{line}`; "
                "Vercel requires direct package specifiers here"
            )
        if line.endswith("\\"):
            errors.append(
                f"{VERCEL_REQUIREMENTS.name}:{line_number}: remove line continuation; "
                "Vercel's requirements parser expects one package per line"
            )
        if "--hash=" in line or line.startswith("--hash"):
            errors.append(
                f"{VERCEL_REQUIREMENTS.name}:{line_number}: remove hash option; "
                "use requirements.lock for reproducible local installs"
            )
    return errors


def main() -> int:
    input_lines = _meaningful_lines(RUNTIME_INPUT)
    vercel_lines = _meaningful_lines(VERCEL_REQUIREMENTS)

    errors = _check_vercel_parser_surface(vercel_lines)

    input_requirements = [line for _, line in input_lines]
    vercel_requirements = [line for _, line in vercel_lines]
    if vercel_requirements != input_requirements:
        errors.append(
            f"{VERCEL_REQUIREMENTS.name} must mirror {RUNTIME_INPUT.name} exactly, "
            "excluding comments and blank lines"
        )

    if errors:
        print("[check-vercel-requirements] FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print(
            "Fix: keep requirements.txt as a simple direct list copied from requirements.in; "
            "keep pins and hashes in requirements.lock.",
            file=sys.stderr,
        )
        return 1

    print("[check-vercel-requirements] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
