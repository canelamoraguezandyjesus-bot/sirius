"""Deterministic clock for tests: never touches the real wall-clock time."""

from __future__ import annotations

from datetime import datetime

__all__ = ["FakeClock"]


class FakeClock:
    """Returns a fixed, injected instant every time ``utc_now`` is called."""

    def __init__(self, fixed_now: datetime) -> None:
        self._fixed_now = fixed_now

    def utc_now(self) -> datetime:
        return self._fixed_now
