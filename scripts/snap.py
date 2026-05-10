#!/usr/bin/env -S .venv/bin/python
"""snap.py — sweep `?v=` variants of a prototype page and screenshot each.

Used by the `_lab/` variant-prototype workflow (see prototype skill at
.claude/skills/prototype/SKILL.md). Compresses the
hand-loop of "navigate → screenshot → repeat" into one command.

Usage:
    scripts/snap.py <surface> [-v A,B,C,D] [-w 1024] [-H 1300]
                              [--theme dark|light|auto] [--full|--no-full]
                              [--open] [--list]

`<surface>` is either:
  - a name under /_lab (e.g. `library-empty-variants` or `library-empty-variants.html`)
  - a path with `_lab/` prefix
  - a full URL (http://... — used as-is, only the ?v= is added)

Output goes to `.playwright-mcp/snap-<surface>-<v>.png`. Pre-existing files
are overwritten so re-runs always land on the same paths.

Exits early with a clear message when:
  - the dev server isn't reachable on the base URL
  - the surface doesn't resolve to an existing file (lists candidates)
  - a passed variant token isn't found in the page's data-variant attrs
"""

from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
LAB_DIR = ROOT / "public" / "_lab"
OUT_DIR = ROOT / ".playwright-mcp"
DEFAULT_BASE = "http://127.0.0.1:8000"


def is_full_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def with_variant_param(url: str, value: str) -> str:
    parts = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if k != "v"]
    query.append(("v", value))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def list_lab_surfaces() -> list[str]:
    if not LAB_DIR.is_dir():
        return []
    return sorted(p.stem for p in LAB_DIR.glob("*.html"))


def resolve_surface(surface: str, base: str) -> tuple[str, str, Path | None]:
    """Return (url, slug, local_path).

    `local_path` is the on-disk HTML file when the surface is local; None
    when the surface was a full URL.
    """
    if is_full_url(surface):
        path = urllib.parse.urlsplit(surface).path
        slug = path.rsplit("/", 1)[-1].removesuffix(".html") or "page"
        return surface, slug, None

    name = surface.removeprefix("_lab/").removesuffix(".html")
    local = LAB_DIR / f"{name}.html"
    if not local.is_file():
        avail = list_lab_surfaces()
        msg = [f"snap.py: no _lab surface named {name!r}"]
        if avail:
            msg.append("available surfaces:")
            for s in avail:
                msg.append(f"  - {s}")
        else:
            msg.append(f"no .html files found under {LAB_DIR.relative_to(ROOT)}/")
        print("\n".join(msg), file=sys.stderr)
        sys.exit(2)
    return f"{base}/_lab/{name}.html", name, local


def variants_in_html(local: Path | None) -> set[str]:
    """Pull the data-variant tokens out of the HTML, if it's a local file."""
    if local is None:
        return set()
    try:
        text = local.read_text(encoding="utf-8")
    except OSError:
        return set()
    return set(re.findall(r'data-variant="([^"]+)"', text))


def check_dev_server(base: str) -> None:
    """Bail with a friendly hint if the dev server isn't accepting TCP.

    Use a raw TCP connect (not HTTP) so 3xx/4xx responses don't get treated
    as 'server down' — auto-guest redirects through /login on first hit.
    """
    parts = urllib.parse.urlsplit(base)
    host = parts.hostname or "127.0.0.1"
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=3):
            pass
    except OSError as exc:
        print(
            f"snap.py: cannot reach dev server at {host}:{port} ({exc})\n"
            "  start it first:  bash scripts/dev.sh\n"
            "  or pass --base http://host:port",
            file=sys.stderr,
        )
        sys.exit(3)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("surface", nargs="?", help="prototype name, path, or full URL")
    p.add_argument("-v", "--variants", default="A,B,C,D",
                   help="comma-separated variant tokens (default: A,B,C,D)")
    p.add_argument("-w", "--width", type=int, default=1024)
    p.add_argument("-H", "--height", type=int, default=1300)
    p.add_argument("--theme", choices=("dark", "light", "auto"), default="dark",
                   help="force data-theme on html+body before each shot (default: dark)")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help=f"dev server base (default: {DEFAULT_BASE})")
    p.add_argument("--open", dest="open_after", action="store_true",
                   help="open the resulting PNGs in Preview (macOS) when done")
    p.add_argument("--list", dest="list_only", action="store_true",
                   help="list available _lab surfaces and exit")
    full = p.add_mutually_exclusive_group()
    full.add_argument("--full", dest="full_page", action="store_true", default=True,
                      help="capture full scrollable page (default)")
    full.add_argument("--no-full", dest="full_page", action="store_false",
                      help="capture only the visible viewport")
    args = p.parse_args()

    if args.list_only:
        for s in list_lab_surfaces():
            print(s)
        return 0
    if not args.surface:
        p.error("surface is required (try --list to see what's available)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not is_full_url(args.surface):
        check_dev_server(args.base)

    url, slug, local_path = resolve_surface(args.surface, args.base)
    requested = [v.strip() for v in args.variants.split(",") if v.strip()]
    if not requested:
        print("snap.py: no variants given", file=sys.stderr)
        return 2

    known = variants_in_html(local_path)
    if known:
        unknown = [v for v in requested if v not in known]
        if unknown:
            print(
                f"snap.py: variant(s) {unknown} not found in "
                f"{local_path.relative_to(ROOT)} (page has: {sorted(known)})",
                file=sys.stderr,
            )
            return 4

    theme_js = (
        ""
        if args.theme == "auto"
        else f"""
        document.documentElement.setAttribute('data-theme', {args.theme!r});
        document.body && document.body.setAttribute('data-theme', {args.theme!r});
        """
    )

    print(f"snap → {slug}  theme={args.theme}  variants={','.join(requested)}")

    written: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": args.width, "height": args.height})
        page = context.new_page()

        # Auto-guest: first hit on / mints a guest session on local dev.
        page.goto(args.base, wait_until="domcontentloaded")

        for v in requested:
            target = with_variant_param(url, v)
            page.goto(target, wait_until="networkidle")
            if theme_js:
                page.evaluate(theme_js)
            out = OUT_DIR / f"snap-{slug}-{v}.png"
            page.screenshot(path=str(out), full_page=args.full_page)
            written.append(out)
            print(f"  {v} → {out.relative_to(ROOT)}")

        browser.close()

    print(f"\nsnapped {len(written)} variants of {slug}")

    if args.open_after and written:
        if sys.platform == "darwin":
            subprocess.run(["open", *map(str, written)], check=False)
        else:
            print(f"--open is macOS only; PNGs are at {OUT_DIR.relative_to(ROOT)}/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
