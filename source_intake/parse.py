"""Pure-function HTML/text parsing for source_intake.

This module imports nothing from urllib, socket, ipaddress, or any I/O
layer. All functions are pure (input → output, or input → raise ParseEmpty).

Security note: BS4 with stdlib html.parser does not parse XML and is not
vulnerable to billion-laughs / XXE. We deliberately do not depend on lxml
for this reason.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedPage:
    """Pure-function output of html or plain-text parsing.

    Title is always populated (host fallback applied here, not in the facade).
    """
    title: str    # max 200 chars, never empty
    text: str     # max 500_000 chars; raises ParseEmpty if < min_text_length


# Functions implemented in subsequent tasks: decode, extract_html, extract_plain
