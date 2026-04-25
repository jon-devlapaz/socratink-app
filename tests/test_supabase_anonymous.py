"""S18 — sign_in_anonymously: Supabase anonymous user → sealed session."""

import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.fernet import Fernet

from auth.service import AuthConfigurationError, SupabaseAuthService
from auth.session_seal import unseal_session_tokens


SESSION_KEY = Fernet.generate_key().decode()
JWT_SECRET = "jwt-secret"


def _build_service() -> SupabaseAuthService:
    return SupabaseAuthService(
        enabled=True,
        supabase_url="https://abc123.supabase.co",
        publishable_key="pk_test",
        jwt_secret=JWT_SECRET,
        session_cookie_key=SESSION_KEY,
        app_base_url="http://localhost:8000",
    )


def _fake_anon_response():
    user = SimpleNamespace(
        id="anon_uuid_456",
        email=None,
        user_metadata={},
    )
    session = SimpleNamespace(
        access_token="anon.access.jwt",
        refresh_token="anon-refresh-rt",
        expires_at=int(time.time()) + 3600,
    )
    return SimpleNamespace(user=user, session=session)


class SignInAnonymouslyTests(unittest.TestCase):
    def test_returns_authenticated_state_with_sealed_session(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.sign_in_anonymously.return_value = (
                _fake_anon_response()
            )
            state = svc.sign_in_anonymously()
        self.assertTrue(state.authenticated)
        self.assertIsNotNone(state.sealed_session)
        self.assertEqual(state.user.id, "anon_uuid_456")
        self.assertIsNone(state.user.email)

    def test_sdk_called_with_no_arguments(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.sign_in_anonymously.return_value = (
                _fake_anon_response()
            )
            svc.sign_in_anonymously()
            factory.return_value.auth.sign_in_anonymously.assert_called_once_with()

    def test_sealed_session_round_trips_to_anon_tokens(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.sign_in_anonymously.return_value = (
                _fake_anon_response()
            )
            state = svc.sign_in_anonymously()
        decoded = unseal_session_tokens(state.sealed_session, key=SESSION_KEY)
        self.assertEqual(decoded["access_token"], "anon.access.jwt")
        self.assertEqual(decoded["refresh_token"], "anon-refresh-rt")

    def test_sdk_failure_propagates(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.sign_in_anonymously.side_effect = RuntimeError(
                "supabase down"
            )
            with self.assertRaises(Exception):
                svc.sign_in_anonymously()

    def test_disabled_service_raises_configuration_error(self):
        svc = SupabaseAuthService(
            enabled=False,
            supabase_url=None,
            publishable_key=None,
            jwt_secret=None,
            session_cookie_key=None,
            app_base_url=None,
        )
        with self.assertRaises(AuthConfigurationError):
            svc.sign_in_anonymously()


if __name__ == "__main__":
    unittest.main()
