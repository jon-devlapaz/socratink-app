"""Fixtures for the socratink-app browser smoke suite.

Design notes
------------
- Each test gets a fresh BrowserContext (default pytest-playwright behavior)
  with localStorage cleared, so theme-preloader and onboarding state are
  always seen from a blank slate.
- Console errors and failed requests are captured per-test on the BrowserContext
  itself and exposed as fixtures, so each assertion can reason about its own
  navigation independently.
- The `same_origin` predicate is computed from `base_url` once per session and
  used to filter cross-origin noise (fonts, analytics, browser extensions).
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

import pytest
from playwright.sync_api import BrowserContext, ConsoleMessage, Page, Request


DEFAULT_BASE_URL = "http://localhost:8000"

# Allow-list of console-error message substrings the suite should ignore.
# Keep this tiny and add only with proven justification (link to a commit/PR).
CONSOLE_ERROR_ALLOW_LIST: tuple[re.Pattern[str], ...] = ()

# URLs we expect to legitimately 404 in some environments (e.g. favicon when
# the brand asset isn't present). Keep specific.
#
# /_vercel/speed-insights/script.js is injected by Vercel in production but is
# absent on local uvicorn — both the request failure and the resulting console
# "Failed to load resource" error are expected outside Vercel.
EXPECTED_404_PATHS: tuple[str, ...] = ("/_vercel/speed-insights/script.js",)


@pytest.fixture(scope="session")
def base_url() -> str:
    """Target URL. Override with SOCRATINK_BASE_URL for prod/preview runs."""
    return os.environ.get("SOCRATINK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


@pytest.fixture(scope="session")
def same_origin(base_url: str):
    """Return a predicate `is_same_origin(url) -> bool` for the current target."""
    target = urlparse(base_url)

    def _is_same_origin(url: str) -> bool:
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        return parsed.scheme == target.scheme and parsed.netloc == target.netloc

    return _is_same_origin


@pytest.fixture
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Extend pytest-playwright defaults with sensible smoke-test settings."""
    return {
        **browser_context_args,
        "ignore_https_errors": False,
        "viewport": {"width": 1280, "height": 800},
    }


@pytest.fixture
def captured(context: BrowserContext, same_origin) -> Iterator[dict[str, list]]:
    """Wire console-error and request-failed listeners onto the context.

    Returns a dict with two lists: `console_errors` and `failed_requests`.
    Both are filtered to same-origin only to avoid third-party / extension noise.
    """
    console_errors: list[ConsoleMessage] = []
    failed_requests: list[Request] = []

    def _on_console(msg: ConsoleMessage) -> None:
        if msg.type != "error":
            return
        text = msg.text
        for allowed in CONSOLE_ERROR_ALLOW_LIST:
            if allowed.search(text):
                return
        # Filter to same-origin: best-effort using the message location URL.
        location = msg.location or {}
        loc_url = location.get("url", "") if isinstance(location, dict) else ""
        if loc_url and not same_origin(loc_url):
            return
        if loc_url and urlparse(loc_url).path in EXPECTED_404_PATHS:
            return
        console_errors.append(msg)

    def _on_request_failed(request: Request) -> None:
        if not same_origin(request.url):
            return
        path = urlparse(request.url).path
        if path in EXPECTED_404_PATHS:
            return
        failed_requests.append(request)

    context.on("console", _on_console)
    context.on("requestfailed", _on_request_failed)

    yield {
        "console_errors": console_errors,
        "failed_requests": failed_requests,
    }


@pytest.fixture
def clean_page(page: Page, base_url: str, captured) -> Iterator[Page]:
    """Page with localStorage/sessionStorage cleared and listeners wired.

    Use this for any test that depends on first-visit-from-blank-slate
    behavior (theme preloader, onboarding, default routing).
    """
    # Visit the origin first so storage clearing has a same-origin context.
    page.goto(base_url)
    page.evaluate(
        """
        try { localStorage.clear(); } catch (e) {}
        try { sessionStorage.clear(); } catch (e) {}
        """
    )
    yield page
