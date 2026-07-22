"""Real system clock adapter for the ``Clock`` port."""

from __future__ import annotations

from datetime import UTC, datetime

__all__ = ["SystemClock", "build_system_clock"]


class SystemClock:
    """Reads the actual wall-clock time, always timezone-aware in UTC."""

    def utc_now(self) -> datetime:
        return datetime.now(UTC)


def build_system_clock() -> SystemClock:
    """Build the production ``Clock`` implementation."""
    return SystemClock()
