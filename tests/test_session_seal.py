"""S5 — Fernet sealing of {access_token, refresh_token, expires_at}."""

import unittest

from cryptography.fernet import Fernet

from auth.session_seal import seal_session_tokens, unseal_session_tokens, validate_session_cookie_key


KEY = Fernet.generate_key().decode()


SAMPLE = {
    "access_token": "eyJabc.def.ghi",
    "refresh_token": "rt_abcdef0123456789",
    "expires_at": 1745260000,
}


class SealUnsealTests(unittest.TestCase):
    def test_round_trip(self):
        sealed = seal_session_tokens(SAMPLE, key=KEY)
        self.assertIsInstance(sealed, str)
        decoded = unseal_session_tokens(sealed, key=KEY)
        self.assertEqual(decoded, SAMPLE)

    def test_wrong_key_rejected(self):
        sealed = seal_session_tokens(SAMPLE, key=KEY)
        other_key = Fernet.generate_key().decode()
        with self.assertRaises(ValueError):
            unseal_session_tokens(sealed, key=other_key)

    def test_tampered_blob_rejected(self):
        sealed = seal_session_tokens(SAMPLE, key=KEY)
        tampered = sealed[:-4] + "XXXX"
        with self.assertRaises(ValueError):
            unseal_session_tokens(tampered, key=KEY)

    def test_garbage_blob_rejected(self):
        with self.assertRaises(ValueError):
            unseal_session_tokens("not-a-fernet-token", key=KEY)

    def test_unseal_raises_value_error_with_message(self):
        """ValueError message must say 'Invalid sealed session blob', not a cryptography internals string."""
        with self.assertRaises(ValueError) as ctx:
            unseal_session_tokens("garbage", key=KEY)
        self.assertIn("Invalid sealed session blob", str(ctx.exception))

    def test_unseal_value_error_wraps_original_cause(self):
        """The ValueError should chain the original exception as __cause__."""
        try:
            unseal_session_tokens("garbage", key=KEY)
        except ValueError as err:
            self.assertIsNotNone(err.__cause__)
        else:
            self.fail("Expected ValueError was not raised")

    def test_wrong_key_error_wraps_original_cause(self):
        """Wrong-key path also wraps the original exception."""
        sealed = seal_session_tokens(SAMPLE, key=KEY)
        other_key = Fernet.generate_key().decode()
        try:
            unseal_session_tokens(sealed, key=other_key)
        except ValueError as err:
            self.assertIsNotNone(err.__cause__)
        else:
            self.fail("Expected ValueError was not raised")

    def test_round_trip_preserves_numeric_expires_at(self):
        """Numeric expires_at survives JSON round-trip without type coercion."""
        sealed = seal_session_tokens(SAMPLE, key=KEY)
        result = unseal_session_tokens(sealed, key=KEY)
        self.assertEqual(result["expires_at"], 1745260000)
        self.assertIsInstance(result["expires_at"], int)

    def test_round_trip_with_extra_fields(self):
        """Extra fields in the token dict are preserved through seal/unseal."""
        tokens = {**SAMPLE, "provider_token": "pt_extra"}
        sealed = seal_session_tokens(tokens, key=KEY)
        result = unseal_session_tokens(sealed, key=KEY)
        self.assertEqual(result["provider_token"], "pt_extra")


class ValidateSessionCookieKeyTests(unittest.TestCase):
    """Tests for the new validate_session_cookie_key() function."""

    def test_valid_fernet_key_passes(self):
        """A proper Fernet-generated key should not raise."""
        valid_key = Fernet.generate_key().decode()
        # Should not raise
        validate_session_cookie_key(valid_key)

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_session_cookie_key("")

    def test_non_base64_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_session_cookie_key("not-a-valid-key!!!")

    def test_short_base64_raises_value_error(self):
        """A base64 string that's too short for a Fernet key should fail."""
        import base64
        short = base64.urlsafe_b64encode(b"tooshort").decode()
        with self.assertRaises(ValueError):
            validate_session_cookie_key(short)

    def test_invalid_key_raises_value_error_with_message(self):
        """The ValueError message should say 'Invalid Fernet key'."""
        with self.assertRaises(ValueError) as ctx:
            validate_session_cookie_key("invalid-fernet-key")
        self.assertIn("Invalid Fernet key", str(ctx.exception))

    def test_invalid_key_wraps_original_cause(self):
        """ValueError should chain the original cryptography exception as __cause__."""
        try:
            validate_session_cookie_key("bad")
        except ValueError as err:
            self.assertIsNotNone(err.__cause__)
        else:
            self.fail("Expected ValueError was not raised")

    def test_wrong_length_base64_raises_value_error(self):
        """Base64 that decodes to wrong byte length fails Fernet validation."""
        import base64
        # Fernet requires exactly 32 bytes. 20 bytes is wrong.
        wrong_length = base64.urlsafe_b64encode(b"A" * 20).decode()
        with self.assertRaises(ValueError):
            validate_session_cookie_key(wrong_length)

    def test_valid_key_returns_none(self):
        """validate_session_cookie_key returns None (not the Fernet object) on success."""
        valid_key = Fernet.generate_key().decode()
        result = validate_session_cookie_key(valid_key)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
