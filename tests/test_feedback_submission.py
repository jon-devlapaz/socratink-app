import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from auth.service import AuthSessionState, AuthUser


class FakeAuthService:
    def __init__(self, state: AuthSessionState):
        self.cookie_name = "sb_session"
        self.enabled = state.auth_enabled
        self.state = state

    def load_session(self, sealed_session: str | None):
        return self.state


class FakeFeedbackTable:
    def __init__(self, execute_error: Exception | None = None):
        self.execute_error = execute_error
        self.inserted = None
        self.insert_kwargs = None

    def insert(self, payload, **kwargs):
        self.inserted = payload
        self.insert_kwargs = kwargs
        return self

    def execute(self):
        if self.execute_error:
            raise self.execute_error
        return object()


class FakeSupabaseClient:
    def __init__(self, table: FakeFeedbackTable):
        self.feedback_table = table

    def table(self, name: str):
        if name != "feedback":
            raise AssertionError(f"unexpected table: {name}")
        return self.feedback_table


class FeedbackSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.original_service = main.app.state.auth_service

    def tearDown(self):
        main.app.state.auth_service = self.original_service

    def _client(self, state: AuthSessionState) -> TestClient:
        main.app.state.auth_service = FakeAuthService(state)
        client = TestClient(main.app)
        client.cookies.set("sb_session", "sealed-session")
        return client

    def test_submit_feedback_inserts_message_and_user_id(self):
        state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="00000000-0000-0000-0000-000000000123"),
        )
        client = self._client(state)
        feedback_table = FakeFeedbackTable()

        with (
            patch.dict(
                main.os.environ,
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_PUBLISHABLE_KEY": "pk_test",
                },
            ),
            patch(
                "main.build_supabase_client",
                return_value=FakeSupabaseClient(feedback_table),
            ),
        ):
            response = client.post(
                "/api/feedback",
                json={"message": "This feedback message is long enough."},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(
            feedback_table.inserted,
            {
                "message": "This feedback message is long enough.",
                "user_id": "00000000-0000-0000-0000-000000000123",
                "status": "pending",
            },
        )
        self.assertEqual(feedback_table.insert_kwargs, {"returning": "minimal"})

    def test_permission_denied_feedback_storage_error_returns_503(self):
        state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            guest_mode=True,
            user=AuthUser(id="00000000-0000-0000-0000-000000000456"),
        )
        client = self._client(state)
        feedback_table = FakeFeedbackTable(
            Exception(
                "{'message': 'permission denied for table users', "
                "'code': '42501', 'hint': None, 'details': None}"
            )
        )

        with (
            patch.dict(
                main.os.environ,
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_PUBLISHABLE_KEY": "pk_test",
                },
            ),
            patch(
                "main.build_supabase_client",
                return_value=FakeSupabaseClient(feedback_table),
            ),
        ):
            response = client.post(
                "/api/feedback",
                json={"message": "This feedback message is long enough."},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Feedback storage is currently unavailable. Please try again later.",
        )


if __name__ == "__main__":
    unittest.main()
