"""B9 Python smoke for source-optional /api/extract.

Spec ref: docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md
Plan ref: docs/superpowers/plans/2026-05-03-conversational-concept-creation-backend.md (Task 19)

Runs the three smoke scenarios from Plan A's Task 19 against the real
FastAPI handler with the real LLM client (real Gemini calls!), bypassing
auth via a fake AuthService that mirrors what the route tests use.

Three scenarios:
  1. Source-less substantive sketch    → expect 200, real ProvisionalMap
  2. Source-less thin sketch ("idk")    → expect 422 thin_sketch_no_source
  3. Legacy text-only payload           → expect 200, real ProvisionalMap

Run from repo root with the venv active:
  $ . .venv/bin/activate
  $ python scripts/b9-python-smoke.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Make the repo root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from auth.service import AuthSessionState  # noqa: E402


class _FakeAuthService:
    """Mirrors tests/test_extract_route_source_optional.py:_FakeAuthService."""

    def __init__(self):
        self.enabled = True
        self.cookie_name = "wos_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "wos_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.current_state = AuthSessionState(
            auth_enabled=True, authenticated=True, guest_mode=True
        )

    def load_session(self, sealed_session):
        return self.current_state

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


def _build_client() -> TestClient:
    main.app.state.auth_service = _FakeAuthService()
    client = TestClient(main.app)
    client.cookies.set("wos_session", "sealed-anon-blob")
    return client


def _summarize_map(payload: dict) -> dict:
    pm = payload.get("provisional_map") or payload.get("knowledge_map") or {}
    metadata = pm.get("metadata", {})
    return {
        "source_title": metadata.get("source_title"),
        "architecture_type": metadata.get("architecture_type"),
        "low_density": metadata.get("low_density"),
        "core_thesis": (metadata.get("core_thesis") or "")[:140],
        "governing_assumptions": metadata.get("governing_assumptions", [])[:3],
        "backbone_count": len(pm.get("backbone", [])),
        "cluster_count": len(pm.get("clusters", [])),
        "subnode_count_total": sum(len(c.get("subnodes", [])) for c in pm.get("clusters", [])),
    }


def _scenario(label: str, request_body: dict, expected_status: int):
    print(f"\n=== {label} ===")
    print(f"request: {json.dumps(request_body)[:200]}")
    started = time.monotonic()
    response = client.post("/api/extract", json=request_body)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    print(f"status:  HTTP {response.status_code}  ({elapsed_ms} ms)  expected: {expected_status}")
    body = response.json()
    if response.status_code == 422:
        detail = body.get("detail", body)
        error = detail.get("error") if isinstance(detail, dict) else None
        message = detail.get("message") if isinstance(detail, dict) else None
        print(f"error:   {error!r}")
        print(f"message: {message!r}")
    elif response.status_code == 200:
        summary = _summarize_map(body)
        for k, v in summary.items():
            print(f"  {k}: {v}")
    else:
        print(f"unexpected body: {json.dumps(body)[:400]}")
    ok = response.status_code == expected_status
    print(f"verdict: {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    client = _build_client()

    results = []

    results.append(_scenario(
        "1. Source-less substantive sketch (real Gemini call)",
        {
            "name": "Photosynthesis",
            "starting_sketch": (
                "Plants take in light and somehow make sugar from water and "
                "carbon dioxide. Not sure where the oxygen comes out."
            ),
            "source": None,
        },
        expected_status=200,
    ))

    results.append(_scenario(
        "2. Source-less thin sketch (no Gemini call)",
        {
            "name": "Photosynthesis",
            "starting_sketch": "idk",
            "source": None,
        },
        expected_status=422,
    ))

    results.append(_scenario(
        "3. Legacy text-only payload (real Gemini call, existing extract path)",
        {
            "text": (
                "Photosynthesis is the process by which plants convert light "
                "energy from the sun into chemical energy stored in glucose. "
                "It occurs in the chloroplasts of plant cells, primarily in "
                "the leaves. The overall reaction takes carbon dioxide and "
                "water as inputs and produces glucose and oxygen as outputs."
            ),
        },
        expected_status=200,
    ))

    print("\n=== Summary ===")
    print(f"{sum(results)}/{len(results)} scenarios passed")
    sys.exit(0 if all(results) else 1)
