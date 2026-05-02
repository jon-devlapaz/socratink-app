"""Architectural invariant: the Gemini SDK lives ONLY behind the seam.

If this test fails, application code re-coupled to a provider. The fix is
NOT to add the file to ``_ALLOWED``; it is to route the call through
``llm.LLMClient`` instead.

See ADR-0003 for the rationale.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Paths that may import the Gemini SDK directly. Keep this set MINIMAL.
_ALLOWED = {"llm/gemini_adapter.py"}

# Substrings that indicate a Gemini-SDK import.
_FORBIDDEN_IMPORT_NEEDLES = (
    "from google import genai",
    "from google.genai",
    "import google.genai",
    "from google.generativeai",
    "import google.generativeai",
)

# Directories to skip entirely.
_SKIP_DIR_PARTS = {
    ".venv",
    "venv",
    ".git",
    "node_modules",
    "__pycache__",
    "tmp",
    ".pytest_cache",
    "test-results",
    "logs",
    ".worktrees",
}


def _iter_repo_python_files():
    for py_path in REPO_ROOT.rglob("*.py"):
        if any(part in _SKIP_DIR_PARTS for part in py_path.parts):
            continue
        yield py_path


def test_gemini_sdk_only_imported_in_adapter():
    """No file outside llm/gemini_adapter.py may import the Gemini SDK.

    Exception (temporary): ai_service.py still uses the legacy Gemini SDK
    for drill_chat and generate_repair_reps. Those paths migrate in a
    follow-up sweep. Once migrated, remove ai_service.py from the exception
    list and tighten the assertion.
    """
    violations: list[str] = []
    for py_path in _iter_repo_python_files():
        rel = py_path.relative_to(REPO_ROOT).as_posix()
        if rel in _ALLOWED:
            continue
        if rel == "ai_service.py":
            # Temporary exception until drill_chat + generate_repair_reps migrate.
            continue
        try:
            text = py_path.read_text(encoding="utf-8")
        except Exception:
            continue
        for needle in _FORBIDDEN_IMPORT_NEEDLES:
            if needle in text:
                violations.append(f"{rel}: contains {needle!r}")
    assert not violations, (
        "LLM seam violation — provider import outside the adapter:\n  "
        + "\n  ".join(violations)
    )


def test_extract_knowledge_map_uses_llm_seam():
    """ai_service.py must use llm.LLMClient at least for the extract path.

    Closed by Task 9. drill_chat and generate_repair_reps still use the
    legacy SDK, so the file still imports google.genai overall — but
    extract_knowledge_map now goes through the seam. When those paths
    migrate, the broader isolation test above will tighten too.
    """
    ai_service = (REPO_ROOT / "ai_service.py").read_text(encoding="utf-8")
    assert (
        "from llm import" in ai_service
    ), "ai_service.py must import from llm for the extract path"
    assert (
        "ProvisionalMap" in ai_service
    ), "ai_service.py must reference ProvisionalMap as the extract return type"
