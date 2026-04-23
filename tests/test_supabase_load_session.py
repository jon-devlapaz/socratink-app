"""S8 — load_session: verify access JWT, refresh on expiry, re-seal."""

import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.fernet import Fernet

from auth.service import SupabaseAuthService
from auth.session_seal import seal_session_tokens, unseal_session_tokens


SESSION_KEY = Fernet.generate_key().decode()
JWT_SECRET = "jwt-secret"
ISSUER = "https://abc123.supabase.co/auth/v1"


def _make_service() -> SupabaseAuthService:
    return SupabaseAuthService(
        enabled=True,
        supabase_url="https://abc123.supabase.co",
        publishable_key="pk_test",
        jwt_secret=JWT_SECRET,
        session_cookie_key=SESSION_KEY,
        app_base_url="http://localhost:8000",
    )


def _make_access_token(*, exp_offset: int = 3600) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "aud": "authenticated",
            "iss": ISSUER,
            "sub": "user_uuid_123",
            "role": "authenticated",
            "iat": now,
            "exp": now + exp_offset,
            "email": "learner@example.com",
            "user_metadata": {"full_name": "Jon Doe"},
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def _seal(*, exp_offset: int = 3600) -> str:
    return seal_session_tokens(
        {
            "access_token": _make_access_token(exp_offset=exp_offset),
            "refresh_token": "rt_value",
            "expires_at": int(time.time()) + exp_offset,
        },
        key=SESSION_KEY,
    )


class LoadSessionTests(unittest.TestCase):
    def test_valid_session_returns_authenticated(self):
        svc = _make_service()
        state = svc.load_session(_seal())
        self.assertTrue(state.authenticated)
        self.assertEqual(state.user.id, "user_uuid_123")
        self.assertEqual(state.user.email, "learner@example.com")

    def test_no_cookie_returns_unauthenticated(self):
        svc = _make_service()
        state = svc.load_session(None)
        self.assertFalse(state.authenticated)
        self.assertEqual(state.error_reason, "no_session_cookie_provided")

    def test_tampered_cookie_clears(self):
        svc = _make_service()
        state = svc.load_session("not-a-fernet-token")
        self.assertFalse(state.authenticated)
        self.assertTrue(state.should_clear_cookie)

    def test_expired_access_refreshes_and_re_seals(self):
        svc = _make_service()
        sealed_in = _seal(exp_offset=-60)
        new_access = _make_access_token(exp_offset=3600)
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.refresh_session.return_value = SimpleNamespace(
                user=SimpleNamespace(
                    id="user_uuid_123",
                    email="learner@example.com",
                    user_metadata={"full_name": "Jon Doe"},
                ),
                session=SimpleNamespace(
                    access_token=new_access,
                    refresh_token="rt_rotated",
                    expires_at=int(time.time()) + 3600,
                ),
            )
            state = svc.load_session(sealed_in)
        self.assertTrue(state.authenticated)
        self.assertIsNotNone(state.sealed_session)
        self.assertNotEqual(state.sealed_session, sealed_in)
        decoded = unseal_session_tokens(state.sealed_session, key=SESSION_KEY)
        self.assertEqual(decoded["access_token"], new_access)
        self.assertEqual(decoded["refresh_token"], "rt_rotated")

    def test_refresh_failure_clears_session(self):
        svc = _make_service()
        sealed_in = _seal(exp_offset=-60)
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.refresh_session.side_effect = RuntimeError(
                "refresh denied"
            )
            state = svc.load_session(sealed_in)
        self.assertFalse(state.authenticated)
        self.assertTrue(state.should_clear_cookie)

    def test_disabled_service_returns_disabled_state(self):
        svc = SupabaseAuthService(
            enabled=False,
            supabase_url=None,
            publishable_key=None,
            jwt_secret=None,
            session_cookie_key=None,
            app_base_url=None,
        )
        state = svc.load_session("anything")
        self.assertFalse(state.auth_enabled)
        self.assertFalse(state.authenticated)


if __name__ == "__main__":
    unittest.main()
