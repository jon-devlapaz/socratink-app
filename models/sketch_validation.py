"""Shared substantiveness heuristic for the learner's starting sketch.

This is the *only* place the substantiveness rule is defined for the backend.
Frontend (Plan B) ports this exact behavior to JS and verifies parity against
``tests/fixtures/sketch_validation_parity.json``.

A sketch is "substantive" when it carries enough learner-generated signal to
seed source-less provisional-map generation. The heuristic is deliberately
simple — token count + a small "don't know" pattern list — because:

  - It must run identically in two languages.
  - The cost of a false-negative (blocking a learner whose sketch is actually
    fine) is recoverable: the strategy-framed footer copy invites them to add
    more or attach source.
  - The cost of a false-positive (passing through a thin sketch that triggers
    hallucinated source-less generation) is foundational principle violation
    per spec §2 principle #7.

When in doubt, this returns False. Source attachment is always a valid
alternative for the learner.
"""
from __future__ import annotations

import re

# Minimum non-stopword token count to be considered substantive.
MIN_SUBSTANTIVE_TOKENS = 5

# Patterns the learner uses when they have nothing to say. Matched as
# normalized substring of the *whole* normalized sketch (stripped, lowercased,
# punctuation collapsed). Keep the list short and obvious; longer/cleverer
# detection is a different problem.
_DONT_KNOW_PATTERNS = (
    "idk",
    "i dont know",
    "i don't know",
    "no idea",
    "no clue",
    "dunno",
    "not sure",
)

# A small English stopword set — kept tiny on purpose so we don't ship an
# external dictionary and so JS parity stays trivial.
_STOPWORDS = frozenset(
    """
    a an the and or but if of for in on at to from by with as is are was were
    be been being do does did has have had this that these those it its
    """.split()
)

_PUNCT_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")
_REPEATED_CHAR_RE = re.compile(r"^(.)\1{4,}$")  # aaaaa, ?????, ......


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace, drop punctuation."""
    text = text.strip().lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _is_dont_know(normalized: str) -> bool:
    """The whole sketch is essentially a 'don't know' pattern."""
    if not normalized:
        return True
    if _REPEATED_CHAR_RE.match(normalized):
        return True
    for pattern in _DONT_KNOW_PATTERNS:
        if normalized == pattern:
            return True
        if normalized.startswith(pattern + " "):
            extra = normalized[len(pattern) + 1:].split()
            if len(extra) <= 3:
                return True
    return False


def _count_substantive_tokens(normalized: str) -> int:
    """Token count after dropping stopwords and very short tokens."""
    tokens = [t for t in normalized.split() if t and len(t) >= 2]
    return sum(1 for t in tokens if t not in _STOPWORDS)


def is_substantive_sketch(text: str) -> bool:
    """Return True if the sketch carries enough learner signal to seed
    source-less provisional-map generation.

    See the module docstring for the principle this enforces and why the
    heuristic is deliberately simple.
    """
    if text is None:
        return False
    normalized = _normalize(text)
    if not normalized:
        return False
    if _is_dont_know(normalized):
        return False
    if _count_substantive_tokens(normalized) < MIN_SUBSTANTIVE_TOKENS:
        return False
    return True
