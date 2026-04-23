"""S5 — Fernet sealing of {access_token, refresh_token, expires_at}."""

import unittest

from cryptography.fernet import Fernet, InvalidToken

from auth.session_seal import seal_session_tokens, unseal_session_tokens


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
        with self.assertRaises(InvalidToken):
            unseal_session_tokens(sealed, key=other_key)

    def test_tampered_blob_rejected(self):
        sealed = seal_session_tokens(SAMPLE, key=KEY)
        tampered = sealed[:-4] + "XXXX"
        with self.assertRaises(InvalidToken):
            unseal_session_tokens(tampered, key=KEY)

    def test_garbage_blob_rejected(self):
        with self.assertRaises(InvalidToken):
            unseal_session_tokens("not-a-fernet-token", key=KEY)


if __name__ == "__main__":
    unittest.main()
