"""Pure whitespace normalization (SIRIUS-SMOKE-001, disposable automation smoke
test — not wired into any real flow).
"""

from __future__ import annotations

import re

__all__ = ["normalize_whitespace"]

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    """Collapse any run of whitespace (spaces, tabs, newlines) into a single
    space and trim leading/trailing whitespace. A blank or whitespace-only
    string returns ``""``."""
    return _WHITESPACE_RUN.sub(" ", text).strip()
