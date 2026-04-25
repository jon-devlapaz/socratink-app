"""S7 + S16 — exchange_code calls Supabase, seals tokens, maps user."""

import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.fernet import Fernet

from auth.service import (
    AuthConfigurationError,
    SupabaseAuthService,
)
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


def _fake_response(
    *,
    full_name: str | None = "Jon Doe",
    given_name: str | None = None,
    session: bool = True,
    access_token: str | None = "access.jwt.value",
    refresh_token: str | None = "refresh-rt-value",
):
    user_metadata = {}
    if full_name is not None:
        user_metadata["full_name"] = full_name
    if given_name is not None:
        user_metadata["given_name"] = given_name
    user = SimpleNamespace(
        id="user_uuid_123",
        email="learner@example.com",
        user_metadata=user_metadata,
    )
    session_obj = None
    if session:
        session_obj = SimpleNamespace(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=int(time.time()) + 3600,
        )
    return SimpleNamespace(user=user, session=session_obj)


class ExchangeCodeTests(unittest.TestCase):
    def test_returns_authenticated_state_with_sealed_session(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            client = factory.return_value
            client.auth.exchange_code_for_session.return_value = _fake_response()
            state = svc.exchange_code(
                code="abc",
                code_verifier="ver_xyz",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        self.assertTrue(state.authenticated)
        self.assertIsNotNone(state.sealed_session)

    def test_missing_session_returns_unauthenticated_without_user(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            client = factory.return_value
            client.auth.exchange_code_for_session.return_value = _fake_response(
                session=False
            )
            state = svc.exchange_code(
                code="abc",
                code_verifier="ver_xyz",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        self.assertFalse(state.authenticated)
        self.assertIsNone(state.sealed_session)
        self.assertIsNone(state.user)
        self.assertFalse(state.guest_mode)

    def test_missing_token_returns_unauthenticated_without_user(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            client = factory.return_value
            client.auth.exchange_code_for_session.return_value = _fake_response(
                access_token=None
            )
            state = svc.exchange_code(
                code="abc",
                code_verifier="ver_xyz",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        self.assertFalse(state.authenticated)
        self.assertIsNone(state.sealed_session)
        self.assertIsNone(state.user)
        self.assertFalse(state.guest_mode)

    def test_sdk_called_with_dict_argument_shape(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            client = factory.return_value
            client.auth.exchange_code_for_session.return_value = _fake_response()
            svc.exchange_code(
                code="abc",
                code_verifier="ver_xyz",
                redirect_uri="http://localhost:8000/auth/callback",
            )
            client.auth.exchange_code_for_session.assert_called_once_with(
                {
                    "auth_code": "abc",
                    "code_verifier": "ver_xyz",
                    "redirect_to": "http://localhost:8000/auth/callback",
                }
            )

    def test_sealed_session_round_trips_to_supabase_tokens(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.exchange_code_for_session.return_value = (
                _fake_response()
            )
            state = svc.exchange_code(
                code="abc",
                code_verifier="ver_xyz",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        decoded = unseal_session_tokens(state.sealed_session, key=SESSION_KEY)
        self.assertEqual(decoded["access_token"], "access.jwt.value")
        self.assertEqual(decoded["refresh_token"], "refresh-rt-value")
        self.assertIn("expires_at", decoded)

    def test_sdk_failure_raises_or_propagates(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.exchange_code_for_session.side_effect = (
                RuntimeError("boom")
            )
            with self.assertRaises(Exception):
                svc.exchange_code(
                    code="abc",
                    code_verifier="ver_xyz",
                    redirect_uri="http://localhost:8000/auth/callback",
                )

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
            svc.exchange_code(
                code="abc",
                code_verifier="v",
                redirect_uri="http://x/callback",
            )


class UserMetadataMappingTests(unittest.TestCase):
    """S16 — map Supabase user_metadata to AuthUser names."""

    def test_full_name_split_into_first_last(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.exchange_code_for_session.return_value = (
                _fake_response(full_name="Jon Doe")
            )
            state = svc.exchange_code(
                code="abc",
                code_verifier="v",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        self.assertEqual(state.user.first_name, "Jon")
        self.assertEqual(state.user.last_name, "Doe")

    def test_given_name_used_when_full_name_absent(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.exchange_code_for_session.return_value = (
                _fake_response(full_name=None, given_name="Jon")
            )
            state = svc.exchange_code(
                code="abc",
                code_verifier="v",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        self.assertEqual(state.user.first_name, "Jon")

    def test_email_only_when_no_metadata(self):
        svc = _build_service()
        with patch.object(svc, "_make_supabase_client") as factory:
            factory.return_value.auth.exchange_code_for_session.return_value = (
                _fake_response(full_name=None, given_name=None)
            )
            state = svc.exchange_code(
                code="abc",
                code_verifier="v",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        self.assertIsNone(state.user.first_name)
        self.assertEqual(state.user.email, "learner@example.com")


if __name__ == "__main__":
    unittest.main()
