"""Injectable clock contract (SIRIUS-ARQ-0.1 S4: "utc_now(); permite pruebas deterministas").

Any component whose output embeds the current date/time — the export
directory name (S12.1), for instance — takes a ``Clock`` instead of calling
``datetime.now()`` directly, so tests can supply a fixed instant.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Contract implemented by the real system clock and deterministic test doubles."""

    def utc_now(self) -> datetime:
        """Return the current instant, timezone-aware in UTC."""
        ...
