import unittest

from fastapi.testclient import TestClient

import main
from auth import GUEST_COOKIE_NAME
from auth.service import AuthSessionState


class FakeAuthService:
    def __init__(self, *, enabled=True):
        self.enabled = enabled
        self.cookie_name = "wos_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "wos_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.current_state = AuthSessionState(auth_enabled=enabled, authenticated=False)

    def load_session(self, sealed_session: str | None):
        return self.current_state

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


class AuthGateTests(unittest.TestCase):
    def setUp(self):
        self.original_service = main.app.state.auth_service

    def tearDown(self):
        main.app.state.auth_service = self.original_service

    def build_client(self, service: FakeAuthService) -> TestClient:
        main.app.state.auth_service = service
        return TestClient(main.app)

    def test_root_redirects_to_login_without_entry_choice(self):
        client = self.build_client(FakeAuthService(enabled=True))

        response = client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/login?return_to=%2F")

    def test_html_entrypoints_redirect_to_login_without_entry_choice(self):
        client = self.build_client(FakeAuthService(enabled=True))

        response = client.get("/ai-runs-dashboard.html", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["location"], "/login?return_to=%2Fai-runs-dashboard.html"
        )

    def test_core_api_requires_guest_or_auth_entry(self):
        client = self.build_client(FakeAuthService(enabled=True))

        response = client.post("/api/extract", json={"text": "   "})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Choose Google sign-in or continue as guest before using the app.",
        )

    def test_guest_cookie_unlocks_app_entrypoints(self):
        client = self.build_client(FakeAuthService(enabled=True))
        client.cookies.set(GUEST_COOKIE_NAME, "guest")

        response = client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Socratink", response.text)

    def test_guest_cookie_unlocks_core_api(self):
        client = self.build_client(FakeAuthService(enabled=True))
        client.cookies.set(GUEST_COOKIE_NAME, "guest")

        response = client.post("/api/extract", json={"text": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "No text provided.")


if __name__ == "__main__":
    unittest.main()
