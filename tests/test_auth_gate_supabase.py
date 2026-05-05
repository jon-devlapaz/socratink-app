"""S12 — middleware gate writes back refreshed session cookie.

Refresh-token rotation requires that rotated tokens be written back on protected
requests; otherwise the next request 401s.
"""

import os
import unittest

from fastapi.testclient import TestClient

import main
from auth.service import AuthSessionState, AuthUser


class FakeSupabaseAuthService:
    def __init__(self, *, enabled=True):
        self.enabled = enabled
        self.cookie_name = "sb_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "sb_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.current_state = AuthSessionState(auth_enabled=enabled, authenticated=False)

    def load_session(self, sealed_session: str | None):
        return self.current_state

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


class AuthGateRefreshWritebackTests(unittest.TestCase):
    def setUp(self):
        self.original_service = main.app.state.auth_service

    def tearDown(self):
        main.app.state.auth_service = self.original_service

    def build_client(self, service):
        main.app.state.auth_service = service
        return TestClient(main.app)

    def _authenticated_with_refresh(self) -> AuthSessionState:
        return AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
            sealed_session="sealed-refreshed-blob",
        )

    def test_protected_html_writes_back_refreshed_session(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = self._authenticated_with_refresh()
        client = self.build_client(service)
        client.cookies.set(service.cookie_name, "sealed-old-blob")

        response = client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "sb_session=sealed-refreshed-blob",
            response.headers.get("set-cookie", ""),
        )

    def test_protected_api_writes_back_refreshed_session(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = self._authenticated_with_refresh()
        client = self.build_client(service)
        client.cookies.set(service.cookie_name, "sealed-old-blob")

        response = client.post("/api/extract", json={"text": "   "})

        # 400 (bad input) is fine; we only care that the gate let it through
        # AND that the response included the refreshed cookie.
        self.assertNotEqual(response.status_code, 401)
        self.assertIn(
            "sb_session=sealed-refreshed-blob",
            response.headers.get("set-cookie", ""),
        )

    def test_unauthenticated_still_redirects(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = self.build_client(service)

        response = client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/login?return_to=%2F")

    def test_anonymous_session_unlocks_gate(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            guest_mode=True,
            user=AuthUser(id="anon_uuid_456"),
        )
        client = self.build_client(service)
        client.cookies.set(service.cookie_name, "sealed-anon-blob")

        response = client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 200)


class DevAutoguestGuardTests(unittest.TestCase):
    """The dev-autoguest escape hatch must stay inert in any production-shaped
    runtime env, regardless of whether the opt-in env var is set.
    """

    def setUp(self):
        self.original_service = main.app.state.auth_service
        self._env_keys = ("SOCRATINK_DEV_AUTOGUEST", "VERCEL", "VERCEL_ENV", "CI")
        self._env_snapshot = {k: os.environ.get(k) for k in self._env_keys}

    def tearDown(self):
        main.app.state.auth_service = self.original_service
        for key, value in self._env_snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _set_env(self, **values):
        for key in self._env_keys:
            os.environ.pop(key, None)
        for key, value in values.items():
            if value is not None:
                os.environ[key] = value

    def _client(self):
        service = FakeSupabaseAuthService(enabled=True)
        main.app.state.auth_service = service
        return TestClient(main.app)

    def test_default_local_redirects_to_login(self):
        self._set_env()  # all unset
        client = self._client()
        response = client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/login?return_to=%2F")

    def test_dev_autoguest_redirects_to_guest_route(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        client = self._client()
        response = client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/auth/guest?return_to=%2F")

    def test_vercel_env_disables_dev_autoguest(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1", VERCEL="1")
        client = self._client()
        response = client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/login?return_to=%2F")

    def test_vercel_env_marker_disables_dev_autoguest(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1", VERCEL_ENV="production")
        client = self._client()
        response = client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/login?return_to=%2F")

    def test_ci_env_disables_dev_autoguest(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1", CI="true")
        client = self._client()
        response = client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/login?return_to=%2F")

    def test_api_me_exposes_dev_mode_when_enabled(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1")
        client = self._client()
        response = client.get("/api/me")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json().get("dev_mode"), True)

    def test_api_me_dev_mode_false_in_default_local(self):
        self._set_env()  # all unset
        client = self._client()
        response = client.get("/api/me")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json().get("dev_mode"), False)

    def test_api_me_dev_mode_false_in_vercel(self):
        self._set_env(SOCRATINK_DEV_AUTOGUEST="1", VERCEL="1")
        client = self._client()
        response = client.get("/api/me")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json().get("dev_mode"), False)


if __name__ == "__main__":
    unittest.main()
