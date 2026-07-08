import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import main
from auth.service import AuthConfigurationError, AuthSessionState, AuthUser


class FakeAuthService:
    def __init__(self, state: AuthSessionState):
        self.cookie_name = "sb_session"
        self.enabled = state.auth_enabled
        self.state = state

    def load_session(self, sealed_session: str | None):
        return self.state


class FakeLearnerStateTable:
    def __init__(self, rows=None, execute_error: Exception | None = None):
        self.rows = list(rows or [])
        self.execute_error = execute_error
        self.last_upsert = None
        self.filters = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def upsert(self, payload, **kwargs):
        self.last_upsert = {"payload": payload, "kwargs": kwargs}
        self.rows = [payload]
        return self

    def execute(self):
        if self.execute_error:
            raise self.execute_error
        result = MagicMock()
        result.data = list(self.rows)
        return result


class FakeSupabaseClient:
    def __init__(self, table: FakeLearnerStateTable):
        self.learner_state_table = table
        self.access_token = None

    def table(self, name: str):
        if name != "learner_state":
            raise AssertionError(f"unexpected table: {name}")
        return self.learner_state_table


def _identified_state(user_id: str, *, access_token: str | None = "user-access-jwt") -> AuthSessionState:
    return AuthSessionState(
        auth_enabled=True,
        authenticated=True,
        user=AuthUser(id=user_id),
        access_token=access_token,
    )


class LearnerStateApiTests(unittest.TestCase):
    def setUp(self):
        self.original_service = main.app.state.auth_service

    def tearDown(self):
        main.app.state.auth_service = self.original_service

    def _client(self, state: AuthSessionState) -> TestClient:
        main.app.state.auth_service = FakeAuthService(state)
        client = TestClient(main.app)
        client.cookies.set("sb_session", "sealed-session")
        return client

    def test_guest_cannot_read_learner_state(self):
        state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            guest_mode=True,
            user=AuthUser(id="00000000-0000-0000-0000-000000000111"),
        )
        client = self._client(state)
        response = client.get("/api/learner-state")
        self.assertEqual(response.status_code, 401)

    def test_get_returns_404_when_empty(self):
        state = _identified_state("00000000-0000-0000-0000-000000000222")
        client = self._client(state)
        table = FakeLearnerStateTable(rows=[])
        captured = {}

        def fake_build(url, key, *, access_token=None):
            captured["access_token"] = access_token
            return FakeSupabaseClient(table)

        with (
            patch.dict(
                main.os.environ,
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_PUBLISHABLE_KEY": "pk_test",
                },
            ),
            patch("main.build_supabase_client", side_effect=fake_build),
        ):
            response = client.get("/api/learner-state")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(captured["access_token"], "user-access-jwt")

    def test_put_and_get_round_trip(self):
        user_id = "00000000-0000-0000-0000-000000000333"
        state = _identified_state(user_id)
        client = self._client(state)
        table = FakeLearnerStateTable(rows=[])
        payload = {
            "schema_version": 1,
            "concepts": [{"id": "c1", "name": "Thermostat"}],
            "training": {
                "c1": {
                    "concept_id": "c1",
                    "schema_version": 1,
                    "node_records": {},
                }
            },
            "updated_at": "2026-07-08T12:00:00.000Z",
        }
        captured = {}

        def fake_build(url, key, *, access_token=None):
            captured["access_token"] = access_token
            return FakeSupabaseClient(table)

        with (
            patch.dict(
                main.os.environ,
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_PUBLISHABLE_KEY": "pk_test",
                },
            ),
            patch("main.build_supabase_client", side_effect=fake_build),
        ):
            put_response = client.put("/api/learner-state", json=payload)
            get_response = client.get("/api/learner-state")

        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(put_response.json(), {"status": "ok"})
        self.assertEqual(table.last_upsert["payload"]["user_id"], user_id)
        self.assertEqual(captured["access_token"], "user-access-jwt")
        self.assertEqual(get_response.status_code, 200)
        body = get_response.json()
        self.assertEqual(body["concepts"], payload["concepts"])
        self.assertEqual(body["training"], payload["training"])

    def test_missing_access_token_returns_401(self):
        state = _identified_state(
            "00000000-0000-0000-0000-000000000555",
            access_token=None,
        )
        client = self._client(state)
        response = client.put(
            "/api/learner-state",
            json={"schema_version": 1, "concepts": [], "training": {}},
        )
        self.assertEqual(response.status_code, 401)

    def test_missing_supabase_env_returns_503(self):
        state = _identified_state("00000000-0000-0000-0000-000000000444")
        client = self._client(state)

        with patch(
            "main.build_supabase_client",
            side_effect=AuthConfigurationError("SUPABASE_URL is required."),
        ):
            response = client.put(
                "/api/learner-state",
                json={"schema_version": 1, "concepts": [], "training": {}},
            )

        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
