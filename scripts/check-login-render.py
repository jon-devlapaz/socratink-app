#!/usr/bin/env python3
"""Check that /login renders from its public template with live assets."""

from __future__ import annotations

import os
import json
import sys
from pathlib import Path

os.environ["SOCRATINK_DEV_AUTOGUEST"] = "0"
os.environ["SOCRATINK_LOCAL_AUTH_BYPASS"] = "0"
os.environ["SOCRATINK_DISABLE_DOTENV_LOCAL"] = "1"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from auth.router import (
    _inline_login_assets,
    _LOGIN_CSS_MARKER,
    _LOGIN_JS_MARKER,
)
from main import app


LOGIN_ASSETS = ROOT / "auth" / "login_assets"
LOGIN_HTML = LOGIN_ASSETS / "login.html"
LOGIN_CSS = LOGIN_ASSETS / "login.css"
LOGIN_JS = LOGIN_ASSETS / "login.js"


def main() -> None:
    template = LOGIN_HTML.read_text(encoding="utf-8")
    css = LOGIN_CSS.read_text(encoding="utf-8")
    js = LOGIN_JS.read_text(encoding="utf-8")
    router = (ROOT / "auth" / "router.py").read_text(encoding="utf-8")
    vercel = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    with TestClient(app) as client:
        response = client.get(
            "/login?return_to=%2Flibrary",
            follow_redirects=False,
        )
        redirect = client.get(
            "/login.html?return_to=%2Flibrary",
            follow_redirects=False,
        )

    assert response.status_code == 200
    rendered = response.text
    assert 'data-login-template="public"' in template
    assert 'data-login-template="public"' in rendered
    assert "Close the source. Explain it. See what survives." in rendered
    assert "Socratink helps you find what you can explain" not in rendered
    assert "Reconstruction practice" not in rendered
    assert "No account needed to begin." not in rendered
    assert "sō·krə·tink" not in rendered
    assert '<h1 id="login-heading">' in rendered
    assert 'class="brand-mark"' not in rendered
    assert "Start with a Google account" in rendered
    assert "save and sync" not in rendered.lower()
    assert "localStorage.getItem('socratink.motion')" in rendered
    assert css in rendered
    assert js in rendered
    assert template.count(_LOGIN_CSS_MARKER) == 1
    assert template.count(_LOGIN_JS_MARKER) == 1
    assert _LOGIN_CSS_MARKER not in rendered
    assert _LOGIN_JS_MARKER not in rendered
    for element_id in (
        "auth-status-banner",
        "guest-continue-link",
        "google-login-link",
        "google-label",
    ):
        assert rendered.count(f'id="{element_id}"') == 1
    assert rendered.index('id="guest-continue-link"') < rendered.index(
        'id="google-login-link"'
    )
    assert "buymeacoffee.com" not in rendered
    assert "discord.gg" not in rendered
    assert "auth_error" in rendered
    assert "return_to" in rendered
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "/login?return_to=%2Flibrary"
    assert "_EMBEDDED_LOGIN_CSS" not in router
    assert "_EMBEDDED_LOGIN_JS" not in router
    assert "auth/login_assets/**" in vercel["functions"]["api/index.py"]["includeFiles"]

    invalid_templates = (
        _LOGIN_JS_MARKER,
        _LOGIN_CSS_MARKER + _LOGIN_CSS_MARKER + _LOGIN_JS_MARKER,
        _LOGIN_CSS_MARKER + _LOGIN_JS_MARKER + _LOGIN_JS_MARKER,
    )
    for invalid_template in invalid_templates:
        try:
            _inline_login_assets(invalid_template, "css", "js")
        except RuntimeError as error:
            assert "exactly one" in str(error)
        else:
            raise AssertionError("Invalid login template markers must fail.")

    print("login render contract: PASS")


if __name__ == "__main__":
    main()
