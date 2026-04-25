"""S2 — OAuth state cookie carries PKCE code_verifier alongside nonce."""

import time
import unittest

from auth.oauth_state import OAuthState, sign_state, verify_state


SECRET = "test-secret-do-not-use-in-prod"


def _payload(**overrides):
    base = OAuthState(
        nonce="n_" + "a" * 32,
        return_to="/library",
        code_verifier="v_" + "b" * 50,
        issued_at=int(time.time()),
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


class SignVerifyRoundTripTests(unittest.TestCase):
    def test_round_trip_preserves_all_fields(self):
        original = _payload()
        token = sign_state(original, SECRET)
        decoded = verify_state(token, secret=SECRET, max_age_seconds=600)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.nonce, original.nonce)
        self.assertEqual(decoded.return_to, original.return_to)
        self.assertEqual(decoded.code_verifier, original.code_verifier)
        self.assertEqual(decoded.issued_at, original.issued_at)

    def test_tampered_payload_returns_none(self):
        token = sign_state(_payload(), SECRET)
        # Token is base64url-encoded; flipping a middle character corrupts the
        # underlying JSON payload (or its signature) — verify must reject either.
        tampered = token[: len(token) // 2] + (
            "A" if token[len(token) // 2] != "A" else "B"
        ) + token[len(token) // 2 + 1 :]
        self.assertIsNone(
            verify_state(tampered, secret=SECRET, max_age_seconds=600)
        )

    def test_wrong_secret_returns_none(self):
        token = sign_state(_payload(), SECRET)
        self.assertIsNone(
            verify_state(token, secret="other-secret", max_age_seconds=600)
        )

    def test_expired_returns_none(self):
        old = _payload(issued_at=int(time.time()) - 3600)
        token = sign_state(old, SECRET)
        self.assertIsNone(verify_state(token, secret=SECRET, max_age_seconds=600))

    def test_garbage_returns_none(self):
        self.assertIsNone(verify_state("not-json", secret=SECRET, max_age_seconds=600))
        self.assertIsNone(verify_state("", secret=SECRET, max_age_seconds=600))


if __name__ == "__main__":
    unittest.main()
