"""Tests for admin.router — Admin Gate enforcement, route round-trips, conflict detection.

Auth model: builds a minimal FastAPI app with the admin_router only and a
fake auth service shaped like SupabaseAuthService. The gate's behavior
across (anon, guest, authenticated-no-user, authenticated-no-email,
non-admin-email, admin-email, auth-disabled, auth-service-exception) is
exercised here, not at the production-app level.

TINK_TODO_PATH is monkeypatched to a per-test temp file so we never
touch /Users/jondev/dev/socratink/todo.md.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from admin import admin_router
from admin import router as admin_module
from auth.service import AuthSessionState, AuthUser


class _FakeAuthService:
    def __init__(self, state: AuthSessionState | Exception | None = None):
        self._state = state
        self.enabled = True
        self.cookie_name = "sb_session"

    def load_session(self, sealed):
        if isinstance(self._state, Exception):
            raise self._state
        return self._state if self._state else AuthSessionState(
            auth_enabled=True, authenticated=False
        )


def _build_app(state: AuthSessionState | Exception | None = None) -> FastAPI:
    app = FastAPI()
    app.state.auth_service = _FakeAuthService(state)
    app.include_router(admin_router)
    return app


def _admin_state() -> AuthSessionState:
    return AuthSessionState(
        auth_enabled=True,
        authenticated=True,
        user=AuthUser(id="admin", email="jonathan10620@gmail.com"),
    )


SAMPLE_TODO = (
    "## Session 2026-04-28 Closeout — testing\n"
    "\n"
    "### Now\n"
    "\n"
    "- [ ] alpha task\n"
    "- [ ] beta task\n"
    "\n"
    "### Backlog\n"
    "\n"
    "- [ ] gamma task\n"
)


class AdminGateTests(unittest.TestCase):
    """All eight failure paths must return 404. No leaks of admin-surface existence."""

    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name) / "todo.md"
        self.tmp_path.write_text(SAMPLE_TODO, encoding="utf-8")
        self._orig_path = admin_module.TINK_TODO_PATH
        admin_module.TINK_TODO_PATH = self.tmp_path

    def tearDown(self):
        admin_module.TINK_TODO_PATH = self._orig_path
        self._tmpdir.cleanup()

    def _client(self, state):
        return TestClient(_build_app(state))

    def test_anon_returns_404(self):
        # No session at all → load_session returns the not-authenticated state.
        client = self._client(AuthSessionState(auth_enabled=True, authenticated=False))
        r = client.get("/admin/todo")
        self.assertEqual(r.status_code, 404)

    def test_guest_returns_404(self):
        client = self._client(AuthSessionState(
            auth_enabled=True, authenticated=False, guest_mode=True,
        ))
        r = client.get("/admin/todo")
        self.assertEqual(r.status_code, 404)

    def test_authenticated_no_user_returns_404(self):
        client = self._client(AuthSessionState(
            auth_enabled=True, authenticated=True, user=None,
        ))
        r = client.get("/admin/todo")
        self.assertEqual(r.status_code, 404)

    def test_authenticated_no_email_returns_404(self):
        client = self._client(AuthSessionState(
            auth_enabled=True, authenticated=True, user=AuthUser(id="x", email=None),
        ))
        r = client.get("/admin/todo")
        self.assertEqual(r.status_code, 404)

    def test_non_admin_email_returns_404(self):
        client = self._client(AuthSessionState(
            auth_enabled=True, authenticated=True,
            user=AuthUser(id="x", email="other@example.com"),
        ))
        r = client.get("/admin/todo")
        self.assertEqual(r.status_code, 404)

    def test_auth_disabled_returns_404(self):
        # auth_enabled=False, authenticated=False (the dataclass default).
        client = self._client(AuthSessionState(auth_enabled=False, authenticated=False))
        r = client.get("/admin/todo")
        self.assertEqual(r.status_code, 404)

    def test_auth_service_exception_returns_404(self):
        client = self._client(RuntimeError("supabase down"))
        r = client.get("/admin/todo")
        self.assertEqual(r.status_code, 404)

    def test_admin_email_returns_200_with_html(self):
        client = self._client(_admin_state())
        r = client.get("/admin/todo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("tink todo", r.text)
        self.assertIn("text/html", r.headers["content-type"])


class AdminDataTests(unittest.TestCase):

    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name) / "todo.md"
        self.tmp_path.write_text(SAMPLE_TODO, encoding="utf-8")
        self._orig_path = admin_module.TINK_TODO_PATH
        admin_module.TINK_TODO_PATH = self.tmp_path
        self.client = TestClient(_build_app(_admin_state()))

    def tearDown(self):
        admin_module.TINK_TODO_PATH = self._orig_path
        self._tmpdir.cleanup()

    def test_data_endpoint_returns_parsed_payload(self):
        r = self.client.get("/api/admin/todo")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("sessions", data)
        self.assertIn("mtime", data)
        sessions = [s for s in data["sessions"] if s["line_index"] >= 0]
        self.assertEqual(len(sessions), 1)
        bucket_names = [b["name"] for b in sessions[0]["buckets"]]
        self.assertEqual(bucket_names, ["Now", "Backlog"])

    def test_mtime_endpoint_returns_just_mtime(self):
        r = self.client.get("/api/admin/todo/mtime")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("mtime", data)
        self.assertEqual(set(data.keys()), {"mtime"})

    def test_toggle_round_trip(self):
        data = self.client.get("/api/admin/todo").json()
        first_session = next(s for s in data["sessions"] if s["line_index"] >= 0)
        now_bucket = first_session["buckets"][0]
        alpha = now_bucket["items"][0]
        self.assertTrue(alpha["is_open"])
        r = self.client.patch("/api/admin/todo/toggle", json={
            "line_index": alpha["line_index"],
            "expected_mtime": data["mtime"],
        })
        self.assertEqual(r.status_code, 200)
        new_data = r.json()
        new_alpha = next(
            i for s in new_data["sessions"] for b in s["buckets"]
            for i in b["items"] if "alpha" in i["body"]
        )
        self.assertFalse(new_alpha["is_open"])
        self.assertIn("admin-toggle", new_alpha["body"])
        # File on disk reflects the change
        on_disk = self.tmp_path.read_text(encoding="utf-8")
        self.assertIn("- [x] alpha task *(resolved", on_disk)

    def test_toggle_409_on_mtime_mismatch(self):
        data = self.client.get("/api/admin/todo").json()
        alpha = data["sessions"][1]["buckets"][0]["items"][0]
        r = self.client.patch("/api/admin/todo/toggle", json={
            "line_index": alpha["line_index"],
            "expected_mtime": data["mtime"] - 9999,
        })
        self.assertEqual(r.status_code, 409)

    def test_toggle_422_on_non_item_line(self):
        data = self.client.get("/api/admin/todo").json()
        # Line 0 is the h2 heading, not an item
        r = self.client.patch("/api/admin/todo/toggle", json={
            "line_index": 0,
            "expected_mtime": data["mtime"],
        })
        self.assertEqual(r.status_code, 422)

    def test_move_within_session_succeeds(self):
        data = self.client.get("/api/admin/todo").json()
        s = next(s for s in data["sessions"] if s["line_index"] >= 0)
        gamma_line = s["buckets"][1]["items"][0]["line_index"]
        now_bucket_line = s["buckets"][0]["line_index"]
        r = self.client.patch("/api/admin/todo/move", json={
            "line_index": gamma_line,
            "target_bucket_line": now_bucket_line,
            "after_item_line": None,
            "expected_mtime": data["mtime"],
        })
        self.assertEqual(r.status_code, 200)
        new_data = r.json()
        s_new = next(s for s in new_data["sessions"] if s["line_index"] >= 0)
        now_items = [i["body"] for i in s_new["buckets"][0]["items"]]
        self.assertEqual(now_items[0], "gamma task")

    def test_edit_round_trip(self):
        data = self.client.get("/api/admin/todo").json()
        s = next(s for s in data["sessions"] if s["line_index"] >= 0)
        alpha = s["buckets"][0]["items"][0]
        r = self.client.patch("/api/admin/todo/edit", json={
            "line_index": alpha["line_index"],
            "new_body": "alpha task (edited)",
            "expected_mtime": data["mtime"],
        })
        self.assertEqual(r.status_code, 200)
        new_data = r.json()
        edited = next(
            i for sess in new_data["sessions"] for b in sess["buckets"]
            for i in b["items"] if i["line_index"] == alpha["line_index"]
        )
        self.assertEqual(edited["body"], "alpha task (edited)")
        self.assertIn("- [ ] alpha task (edited)", self.tmp_path.read_text())

    def test_edit_409_on_mtime_mismatch(self):
        data = self.client.get("/api/admin/todo").json()
        alpha = data["sessions"][1]["buckets"][0]["items"][0]
        r = self.client.patch("/api/admin/todo/edit", json={
            "line_index": alpha["line_index"],
            "new_body": "anything",
            "expected_mtime": data["mtime"] - 9999,
        })
        self.assertEqual(r.status_code, 409)

    def test_edit_422_on_newline_in_body(self):
        data = self.client.get("/api/admin/todo").json()
        alpha = data["sessions"][1]["buckets"][0]["items"][0]
        r = self.client.patch("/api/admin/todo/edit", json={
            "line_index": alpha["line_index"],
            "new_body": "first line\nsecond line",
            "expected_mtime": data["mtime"],
        })
        self.assertEqual(r.status_code, 422)

    def test_edit_422_on_empty_body(self):
        data = self.client.get("/api/admin/todo").json()
        alpha = data["sessions"][1]["buckets"][0]["items"][0]
        r = self.client.patch("/api/admin/todo/edit", json={
            "line_index": alpha["line_index"],
            "new_body": "   ",
            "expected_mtime": data["mtime"],
        })
        self.assertEqual(r.status_code, 422)

    def test_edit_422_on_non_item_line(self):
        data = self.client.get("/api/admin/todo").json()
        r = self.client.patch("/api/admin/todo/edit", json={
            "line_index": 0,
            "new_body": "anything",
            "expected_mtime": data["mtime"],
        })
        self.assertEqual(r.status_code, 422)

    def test_move_409_on_mtime_mismatch(self):
        data = self.client.get("/api/admin/todo").json()
        s = next(s for s in data["sessions"] if s["line_index"] >= 0)
        gamma_line = s["buckets"][1]["items"][0]["line_index"]
        now_bucket_line = s["buckets"][0]["line_index"]
        r = self.client.patch("/api/admin/todo/move", json={
            "line_index": gamma_line,
            "target_bucket_line": now_bucket_line,
            "after_item_line": None,
            "expected_mtime": data["mtime"] - 9999,
        })
        self.assertEqual(r.status_code, 409)


class AdminFeedbackTests(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(_build_app(_admin_state()))

    @patch("admin.router.build_supabase_client")
    def test_feedback_list_hides_exception_details(self, mock_build):
        mock_client = Mock()
        mock_client.table().select().eq().order().execute.side_effect = Exception("Sensitive DB error: missing column xyz")
        mock_build.return_value = mock_client
        
        r = self.client.get("/api/admin/feedback")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["detail"], "Failed to fetch feedback")
        self.assertNotIn("Sensitive DB error", r.text)

    @patch("admin.router.build_supabase_client")
    def test_feedback_import_hides_exception_details(self, mock_build):
        mock_client = Mock()
        mock_client.table().select().eq().execute.side_effect = Exception("Sensitive DB error on import")
        mock_build.return_value = mock_client

        r = self.client.post("/api/admin/feedback/123/import")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["detail"], "Failed to import feedback")

    @patch("admin.router.build_supabase_client")
    def test_feedback_import_returns_404(self, mock_build):
        mock_client = Mock()
        mock_res = Mock()
        mock_res.data = []
        mock_client.table().select().eq().execute.return_value = mock_res
        mock_build.return_value = mock_client

        r = self.client.post("/api/admin/feedback/123/import")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["detail"], "Feedback not found")

    @patch("admin.router.build_supabase_client")
    def test_feedback_dismiss_hides_exception_details(self, mock_build):
        mock_client = Mock()
        mock_client.table().update().eq().execute.side_effect = Exception("Sensitive DB error on dismiss")
        mock_build.return_value = mock_client

        r = self.client.delete("/api/admin/feedback/123")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["detail"], "Failed to dismiss feedback")


class AdminRegistrationTests(unittest.TestCase):

    def test_dev_environment_default(self):
        # No APP_BASE_URL set → permissive
        import os
        original = os.environ.pop("APP_BASE_URL", None)
        try:
            self.assertTrue(admin_module._is_dev_environment())
        finally:
            if original is not None:
                os.environ["APP_BASE_URL"] = original

    def test_localhost_url_is_dev(self):
        import os
        os.environ["APP_BASE_URL"] = "http://localhost:8000"
        try:
            self.assertTrue(admin_module._is_dev_environment())
        finally:
            os.environ.pop("APP_BASE_URL")

    def test_127001_url_is_dev(self):
        import os
        os.environ["APP_BASE_URL"] = "http://127.0.0.1:8000"
        try:
            self.assertTrue(admin_module._is_dev_environment())
        finally:
            os.environ.pop("APP_BASE_URL")

    def test_prod_url_is_not_dev(self):
        import os
        os.environ["APP_BASE_URL"] = "https://app.socratink.ai"
        try:
            self.assertFalse(admin_module._is_dev_environment())
        finally:
            os.environ.pop("APP_BASE_URL")


class AdminHealthCheckTests(unittest.TestCase):
    """The /admin/health endpoint is an unauthenticated liveness probe.

    It is intentionally NOT gated by `_require_admin` — it just confirms
    the router is mounted. Authentication on a health check would defeat
    the purpose (infra needs to probe before any session exists).
    """

    def test_health_check_returns_200_for_anonymous(self):
        client = TestClient(_build_app())
        r = client.get("/admin/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_health_check_returns_200_for_admin(self):
        client = TestClient(_build_app(_admin_state()))
        r = client.get("/admin/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})
