"""S4 — Supabase access-token JWT verification. Pure given key + issuer."""

import time
import unittest

import jwt

from auth.jwt_verify import (
    InvalidAccessToken,
    TokenExpired,
    verify_access_token,
)


SECRET = "supabase-jwt-secret-test-fixture"
ISSUER = "https://abc123.supabase.co/auth/v1"


def _make_token(**overrides) -> str:
    now = int(time.time())
    claims = {
        "aud": "authenticated",
        "iss": ISSUER,
        "sub": "user_uuid_123",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
        "email": "learner@example.com",
        "user_metadata": {"full_name": "Jon Doe"},
    }
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS256")


class VerifyAccessTokenTests(unittest.TestCase):
    def test_valid_token_returns_claims(self):
        token = _make_token()
        claims = verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)
        self.assertEqual(claims["sub"], "user_uuid_123")
        self.assertEqual(claims["email"], "learner@example.com")

    def test_wrong_audience_rejected(self):
        token = _make_token(aud="wrong")
        with self.assertRaises(InvalidAccessToken):
            verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)

    def test_wrong_issuer_rejected(self):
        token = _make_token(iss="https://evil.supabase.co/auth/v1")
        with self.assertRaises(InvalidAccessToken):
            verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)

    def test_missing_sub_rejected(self):
        token = _make_token()
        # Re-encode without sub
        decoded = jwt.decode(
            token, SECRET, algorithms=["HS256"], audience="authenticated"
        )
        decoded.pop("sub")
        token = jwt.encode(decoded, SECRET, algorithm="HS256")
        with self.assertRaises(InvalidAccessToken):
            verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)

    def test_role_not_authenticated_rejected(self):
        token = _make_token(role="anon")
        with self.assertRaises(InvalidAccessToken):
            verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)

    def test_expired_raises_token_expired(self):
        token = _make_token(exp=int(time.time()) - 60)
        with self.assertRaises(TokenExpired):
            verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)

    def test_wrong_signature_rejected(self):
        token = _make_token()
        with self.assertRaises(InvalidAccessToken):
            verify_access_token(token, jwt_secret="other-secret", issuer=ISSUER)

    def test_garbage_token_rejected(self):
        with self.assertRaises(InvalidAccessToken):
            verify_access_token("not.a.jwt", jwt_secret=SECRET, issuer=ISSUER)


class IsAnonymousClaimTests(unittest.TestCase):
    def test_is_anonymous_true_surfaced_in_claims(self):
        token = _make_token(is_anonymous=True)
        claims = verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)
        self.assertTrue(claims.get("is_anonymous"))

    def test_is_anonymous_false_when_absent(self):
        token = _make_token()
        claims = verify_access_token(token, jwt_secret=SECRET, issuer=ISSUER)
        # Treat absence as False; explicit False also acceptable.
        self.assertFalse(claims.get("is_anonymous", False))


if __name__ == "__main__":
    unittest.main()
