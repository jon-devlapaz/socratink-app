from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from runtime_env import load_app_env


ENV_KEYS = {
    "AUTH_ENABLED",
    "SUPABASE_URL",
    "SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_JWT_SECRET",
    "SESSION_COOKIE_KEY",
    "APP_BASE_URL",
    "VERCEL",
    "VERCEL_ENV",
    "CI",
    "SOCRATINK_DISABLE_DOTENV_LOCAL",
}


class RuntimeEnvTests(unittest.TestCase):
    def setUp(self):
        self.original = {key: os.environ.get(key) for key in ENV_KEYS}
        for key in ENV_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        for key in ENV_KEYS:
            if self.original[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = self.original[key]

    def _root(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_dotenv_local_overrides_dotenv_without_overriding_process_env(self):
        root = self._root()
        (root / ".env").write_text(
            "\n".join(
                [
                    "AUTH_ENABLED=false",
                    "SUPABASE_URL=https://from-dotenv.supabase.co",
                    "SESSION_COOKIE_KEY=",
                    "APP_BASE_URL=http://localhost:8000",
                ]
            )
            + "\n"
        )
        (root / ".env.local").write_text(
            "\n".join(
                [
                    "AUTH_ENABLED=true",
                    "SUPABASE_URL=https://from-local.supabase.co",
                    "SUPABASE_PUBLISHABLE_KEY=pk_local",
                    "SUPABASE_JWT_SECRET=jwt_local",
                    "SESSION_COOKIE_KEY=session_local",
                ]
            )
            + "\n"
        )
        os.environ["SUPABASE_URL"] = "https://from-process.supabase.co"

        report = load_app_env(root)

        self.assertEqual(report.loaded_files, (".env", ".env.local"))
        self.assertEqual(os.environ["AUTH_ENABLED"], "true")
        self.assertEqual(
            os.environ["SUPABASE_URL"], "https://from-process.supabase.co"
        )
        self.assertEqual(os.environ["SESSION_COOKIE_KEY"], "session_local")

    def test_dotenv_local_is_skipped_on_vercel(self):
        root = self._root()
        (root / ".env").write_text("AUTH_ENABLED=false\n")
        (root / ".env.local").write_text("AUTH_ENABLED=true\n")
        os.environ["VERCEL"] = "1"

        report = load_app_env(root)

        self.assertEqual(report.loaded_files, (".env",))
        self.assertEqual(report.skipped_local_reason, "Vercel runtime env detected")
        self.assertEqual(os.environ["AUTH_ENABLED"], "false")


if __name__ == "__main__":
    unittest.main()
