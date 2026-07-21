"""Pure text-normalization helpers with no dependency on the rest of Sirius."""

from __future__ import annotations

import re

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    """Collapse consecutive whitespace into single spaces and trim the ends."""
    return _WHITESPACE_RUN.sub(" ", text).strip()
