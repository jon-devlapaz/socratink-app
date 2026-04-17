import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth.router import GUEST_COOKIE_NAME, auth_router, sanitize_return_to_path
from auth.service import AuthSessionState, AuthUser


class FakeAuthService:
    def __init__(self, *, enabled=True):
        self.enabled = enabled
        self.cookie_name = "wos_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "wos_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.last_return_to = None
        self.last_provider = None
        self.last_logout_cookie = None
        self.last_built_oauth_state = None
        self.oauth_state_valid = True
        self.current_state = AuthSessionState(auth_enabled=enabled, authenticated=False)
        self.callback_state = AuthSessionState(
            auth_enabled=enabled,
            authenticated=True,
            user=AuthUser(id="user_123", email="learner@example.com"),
            sealed_session="sealed-abc",
        )

    def get_login_url(
        self, *, base_url: str, return_to: str | None = None, provider: str = "authkit"
    ) -> str:
        self.last_return_to = return_to
        self.last_provider = provider
        if not self.enabled:
            raise RuntimeError("disabled")
        return "https://auth.example/login"

    def exchange_code(
        self, *, code: str, ip_address: str | None = None, user_agent: str | None = None
    ):
        return self.callback_state

    def load_session(self, sealed_session: str | None):
        return self.current_state

    def logout(self, sealed_session: str | None):
        self.last_logout_cookie = sealed_session

    def build_oauth_state(self, *, return_to: str):
        self.last_built_oauth_state = return_to
        return "nonce-123", "signed-state-token"

    def verify_oauth_state(self, *, state: str | None, signed_cookie: str | None):
        if not self.oauth_state_valid:
            return None
        if state == "nonce-123" and signed_cookie == "signed-state-token":
            return "/library"
        return None

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")


def build_client(service: FakeAuthService) -> TestClient:
    app = FastAPI()
    app.state.auth_service = service
    app.include_router(auth_router)
    return TestClient(app)


class AuthRouterTests(unittest.TestCase):
    def test_sanitize_return_to_blocks_open_redirects(self):
        self.assertEqual(sanitize_return_to_path(None), "/")
        self.assertEqual(sanitize_return_to_path("https://evil.test"), "/")
        self.assertEqual(sanitize_return_to_path("//evil.test"), "/")
        self.assertEqual(sanitize_return_to_path("/concepts/1"), "/concepts/1")

    def test_api_me_returns_anonymous_when_auth_disabled(self):
        service = FakeAuthService(enabled=False)
        service.current_state = AuthSessionState(
            auth_enabled=False, authenticated=False
        )
        client = build_client(service)

        response = client.get("/api/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "auth_enabled": False,
                "authenticated": False,
                "guest_mode": False,
                "user": None,
            },
        )

    def test_login_redirect_uses_sanitized_return_path(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)

        response = client.get(
            "/auth/google?return_to=https://evil.test", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://auth.example/login")
        self.assertEqual(service.last_return_to, "nonce-123")
        self.assertEqual(service.last_provider, "GoogleOAuth")
        self.assertEqual(service.last_built_oauth_state, "/")
        self.assertIn(
            "wos_oauth_state=signed-state-token", response.headers.get("set-cookie", "")
        )

    def test_login_page_renders_html(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)

        response = client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Socratink - The Socratic Canvas", response.text)
        self.assertIn("Continue with Google", response.text)
        self.assertIn("Continue as Guest", response.text)
        self.assertIn("Buy me a coffee", response.text)
        self.assertIn("https://buymeacoffee.com/socratink", response.text)
        self.assertIn("coffee-button", response.text)
        self.assertNotIn("Email Address", response.text)

    def test_login_page_renders_without_file_assets(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)

        response = client.get("/login?return_to=/library")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Continue with Google", response.text)
        self.assertIn("<style>", response.text)
        self.assertIn("The Socratic Canvas", response.text)

    def test_callback_sets_cookie_and_redirects_to_return_to(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set("wos_oauth_state", "signed-state-token")

        response = client.get(
            "/auth/callback?code=abc123&state=nonce-123",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")
        self.assertIn("wos_session=sealed-abc", response.headers.get("set-cookie", ""))

    def test_callback_error_redirects_back_to_login(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set("wos_oauth_state", "signed-state-token")

        response = client.get(
            "/auth/callback?error=access_denied&state=nonce-123",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "/login?return_to=%2Flibrary&auth_error=access_denied",
            response.headers["location"],
        )

    def test_callback_invalid_state_redirects_back_to_login(self):
        service = FakeAuthService(enabled=True)
        service.oauth_state_valid = False
        client = build_client(service)
        client.cookies.set("wos_oauth_state", "signed-state-token")

        response = client.get(
            "/auth/callback?code=abc123&state=bad-state",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "/login?return_to=%2F&auth_error=invalid_state",
            response.headers["location"],
        )

    def test_logout_clears_cookie(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set("wos_session", "sealed-abc")
        client.cookies.set(GUEST_COOKIE_NAME, "guest")

        response = client.post("/api/auth/logout")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ok"], True)
        self.assertEqual(service.last_logout_cookie, "sealed-abc")
        self.assertIn("Max-Age=0", response.headers.get("set-cookie", ""))
        self.assertIn(f"{GUEST_COOKIE_NAME}=", response.headers.get("set-cookie", ""))

    def test_api_me_returns_guest_mode_when_guest_cookie_present(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(GUEST_COOKIE_NAME, "guest")

        response = client.get("/api/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "auth_enabled": True,
                "authenticated": False,
                "guest_mode": True,
                "user": None,
            },
        )

    def test_login_redirects_guest_sessions_back_into_app(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(GUEST_COOKIE_NAME, "guest")

        response = client.get("/login?return_to=/library", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")

    def test_guest_entry_sets_cookie_and_redirects(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/library", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")
        self.assertIn(
            f"{GUEST_COOKIE_NAME}=guest", response.headers.get("set-cookie", "")
        )

    def test_magic_auth_send_is_disabled(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)

        response = client.post(
            "/api/auth/magic-auth/send",
            json={"email": "Learner@Example.com"},
        )

        self.assertEqual(response.status_code, 503)

    def test_magic_auth_verify_is_disabled(self):
        service = FakeAuthService(enabled=True)
        client = build_client(service)

        response = client.post(
            "/api/auth/magic-auth/verify",
            json={"email": "learner@example.com", "code": "123456", "return_to": "/"},
        )

        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
