"""S9 + S10 + S11 — router endpoints under SupabaseAuthService.

Replaces / augments tests/test_auth_router.py once WorkOS is removed.
Uses a fake service matching the SupabaseAuthService interface.
"""

import unittest
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth.router import GUEST_COOKIE_NAME, auth_router
from auth.service import AuthSessionState, AuthUser


class FakeSupabaseAuthService:
    def __init__(self, *, enabled=True):
        self.enabled = enabled
        self.cookie_name = "sb_session"
        self.cookie_samesite = "lax"
        self.cookie_max_age = 120
        self.oauth_state_cookie_name = "sb_oauth_state"
        self.oauth_state_ttl_seconds = 600
        self.app_base_url = "http://localhost:8000"
        self.callback_path = "/auth/callback"

        # Interaction recording
        self.last_built_state = None
        self.last_exchange_args = None
        self.last_logout_cookie = None
        self.oauth_state_valid = True

        self.current_state = AuthSessionState(auth_enabled=enabled, authenticated=False)
        self.callback_state = AuthSessionState(
            auth_enabled=enabled,
            authenticated=True,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
            sealed_session="sealed-session-blob",
        )

    # --- supabase-shaped service interface ---

    def build_oauth_state(self, *, return_to: str):
        self.last_built_state = return_to
        return (
            "nonce-pkce",
            "v_pkce_verifier_value",
            "ch_pkce_challenge_value",
            "signed-state-cookie",
        )

    def get_login_url(self, *, state_nonce: str, code_challenge: str) -> str:
        if not self.enabled:
            raise RuntimeError("disabled")
        return (
            "https://abc123.supabase.co/auth/v1/authorize"
            f"?provider=google&state={state_nonce}&code_challenge={code_challenge}"
            "&code_challenge_method=S256"
            "&redirect_to=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcallback"
        )

    def verify_oauth_state(self, *, state: str | None, signed_cookie: str | None):
        if not self.oauth_state_valid:
            return None
        if state == "nonce-pkce" and signed_cookie == "signed-state-cookie":
            return ("/library", "v_pkce_verifier_value")
        return None

    def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str):
        self.last_exchange_args = {
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        }
        return self.callback_state

    def load_session(self, sealed_session: str | None):
        return self.current_state

    def logout(self, sealed_session: str | None):
        self.last_logout_cookie = sealed_session

    def resolve_cookie_secure(self, base_url: str) -> bool:
        return base_url.startswith("https://")

    def callback_redirect_uri(self) -> str:
        return f"{self.app_base_url.rstrip('/')}{self.callback_path}"


def build_client(service: FakeSupabaseAuthService) -> TestClient:
    app = FastAPI()
    app.state.auth_service = service
    app.include_router(auth_router)
    return TestClient(app)


class GoogleAuthStartTests(unittest.TestCase):
    def test_redirects_to_supabase_authorize_with_pkce(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)

        response = client.get(
            "/auth/google?return_to=/library", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        location = response.headers["location"]
        parsed = urlparse(location)
        self.assertEqual(parsed.netloc, "abc123.supabase.co")
        self.assertEqual(parsed.path, "/auth/v1/authorize")
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        self.assertEqual(qs["provider"], "google")
        self.assertEqual(qs["code_challenge_method"], "S256")
        self.assertIn("code_challenge", qs)
        self.assertEqual(qs["state"], "nonce-pkce")

    def test_state_cookie_set_with_signed_payload(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)

        response = client.get("/auth/google", follow_redirects=False)

        self.assertIn(
            f"{service.oauth_state_cookie_name}=signed-state-cookie",
            response.headers.get("set-cookie", ""),
        )

    def test_open_redirect_return_to_sanitized(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)

        client.get(
            "/auth/google?return_to=https://evil.test", follow_redirects=False
        )

        self.assertEqual(service.last_built_state, "/")


class CallbackTests(unittest.TestCase):
    def test_success_sets_session_cookie_and_redirects(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get(
            "/auth/callback?code=abc123&state=nonce-pkce", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")
        self.assertIn(
            "sb_session=sealed-session-blob", response.headers.get("set-cookie", "")
        )
        self.assertEqual(
            service.last_exchange_args,
            {
                "code": "abc123",
                "code_verifier": "v_pkce_verifier_value",
                "redirect_uri": "http://localhost:8000/auth/callback",
            },
        )

    def test_invalid_state_redirects_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.oauth_state_valid = False
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get(
            "/auth/callback?code=abc&state=bad", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=invalid_state", response.headers["location"])

    def test_missing_code_redirects_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get(
            "/auth/callback?state=nonce-pkce", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=missing_code", response.headers["location"])

    def test_provider_error_propagates(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get(
            "/auth/callback?error=access_denied&state=nonce-pkce",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=access_denied", response.headers["location"])

    def test_exchange_failure_redirects_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)

        def boom(**_kwargs):
            raise RuntimeError("supabase down")

        service.exchange_code = boom  # type: ignore[assignment]
        client = build_client(service)
        client.cookies.set(service.oauth_state_cookie_name, "signed-state-cookie")

        response = client.get(
            "/auth/callback?code=abc&state=nonce-pkce", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])


class ApiMeAndLogoutTests(unittest.TestCase):
    def test_api_me_returns_user_when_authenticated(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
        )
        client = build_client(service)

        response = client.get("/api/me")
        body = response.json()
        self.assertTrue(body["authenticated"])
        self.assertEqual(body["user"]["email"], "learner@example.com")

    def test_api_me_writes_back_refreshed_cookie(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.current_state = AuthSessionState(
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="user_uuid_123", email="learner@example.com"),
            sealed_session="sealed-refreshed-blob",
        )
        client = build_client(service)

        response = client.get("/api/me")
        self.assertIn(
            "sb_session=sealed-refreshed-blob",
            response.headers.get("set-cookie", ""),
        )

    def test_logout_clears_session_and_guest_cookies(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)
        client.cookies.set(service.cookie_name, "sealed-session-blob")
        client.cookies.set(GUEST_COOKIE_NAME, "guest")

        response = client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(service.last_logout_cookie, "sealed-session-blob")
        cookies = response.headers.get("set-cookie", "")
        self.assertIn("sb_session=", cookies)
        self.assertIn(f"{GUEST_COOKIE_NAME}=", cookies)
        self.assertIn("Max-Age=0", cookies)

    def test_magic_auth_endpoints_remain_disabled(self):
        service = FakeSupabaseAuthService(enabled=True)
        client = build_client(service)

        send = client.post(
            "/api/auth/magic-auth/send", json={"email": "x@y.z"}
        )
        verify = client.post(
            "/api/auth/magic-auth/verify",
            json={"email": "x@y.z", "code": "123456", "return_to": "/"},
        )
        self.assertEqual(send.status_code, 503)
        self.assertEqual(verify.status_code, 503)


class AnonymousGuestTests(unittest.TestCase):
    def test_guest_calls_sign_in_anonymously_and_sets_session_cookie(self):
        service = FakeSupabaseAuthService(enabled=True)
        called = {}

        def fake_anon():
            called["yes"] = True
            return AuthSessionState(
                auth_enabled=True,
                authenticated=True,
                user=AuthUser(id="anon_uuid_456"),
                guest_mode=True,
                sealed_session="sealed-anon-blob",
            )

        service.sign_in_anonymously = fake_anon  # type: ignore[assignment]
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/library", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/library")
        self.assertTrue(called.get("yes"))
        self.assertIn(
            "sb_session=sealed-anon-blob", response.headers.get("set-cookie", "")
        )

    def test_guest_open_redirect_sanitized(self):
        service = FakeSupabaseAuthService(enabled=True)
        service.sign_in_anonymously = lambda: AuthSessionState(  # type: ignore[assignment]
            auth_enabled=True,
            authenticated=True,
            user=AuthUser(id="anon_uuid_456"),
            guest_mode=True,
            sealed_session="sealed-anon-blob",
        )
        client = build_client(service)

        response = client.get(
            "/auth/guest?return_to=https://evil.test", follow_redirects=False
        )

        self.assertEqual(response.headers["location"], "/")

    def test_guest_failure_redirects_to_login_with_error(self):
        service = FakeSupabaseAuthService(enabled=True)

        def boom():
            raise RuntimeError("supabase down")

        service.sign_in_anonymously = boom  # type: ignore[assignment]
        client = build_client(service)

        response = client.get("/auth/guest?return_to=/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("auth_error=authentication_failed", response.headers["location"])


if __name__ == "__main__":
    unittest.main()
