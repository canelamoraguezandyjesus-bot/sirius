"""Whitespace normalization for plain text (SIRIUS-SMOKE-001).

Disposable automation smoke test: a single pure, deterministic function with
no dependents and no side effects, added solely to exercise the
implementation -> CI -> review pipeline end to end.
"""

from __future__ import annotations

import re

__all__ = ["normalize_whitespace"]

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace into a single space and trim the ends.

    An empty string or a string made up entirely of whitespace returns "".
    """
    return _WHITESPACE_RUN.sub(" ", text).strip()
