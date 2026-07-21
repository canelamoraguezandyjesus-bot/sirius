"""Pure whitespace normalization helper."""

from __future__ import annotations

import re

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    """Collapse consecutive whitespace into a single space and trim the ends."""
    return _WHITESPACE_RUN.sub(" ", text).strip()
