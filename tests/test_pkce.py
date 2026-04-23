"""S1 — PKCE primitives. Pure functions, no IO."""

import base64
import hashlib
import re
import unittest

from auth.pkce import challenge_from_verifier, generate_verifier


class GenerateVerifierTests(unittest.TestCase):
    def test_length_in_pkce_spec_range(self):
        v = generate_verifier()
        self.assertGreaterEqual(len(v), 43)
        self.assertLessEqual(len(v), 128)

    def test_url_safe_charset_only(self):
        v = generate_verifier()
        self.assertRegex(v, r"^[A-Za-z0-9\-._~]+$")

    def test_uniqueness(self):
        seen = {generate_verifier() for _ in range(50)}
        self.assertEqual(len(seen), 50)


class ChallengeFromVerifierTests(unittest.TestCase):
    def test_matches_rfc7636_s256(self):
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        self.assertEqual(challenge_from_verifier(verifier), expected)

    def test_no_padding(self):
        c = challenge_from_verifier(generate_verifier())
        self.assertNotIn("=", c)

    def test_different_verifiers_different_challenges(self):
        a = generate_verifier()
        b = generate_verifier()
        self.assertNotEqual(challenge_from_verifier(a), challenge_from_verifier(b))

    def test_url_safe_chars(self):
        c = challenge_from_verifier(generate_verifier())
        self.assertRegex(c, r"^[A-Za-z0-9_\-]+$")


if __name__ == "__main__":
    unittest.main()
