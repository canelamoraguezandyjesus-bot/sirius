"""Pre-bootstrap data-location contracts (B2b, D-10).

Resolving where Sirius keeps its data must happen before SQLite, logging, or
composition can start (AGENTS.md dependency direction still applies: these
contracts avoid any dependency on ``SiriusPaths``, the persistence adapters,
platformdirs, or JSON — only ``sirius.infrastructure.bootstrap_location_store``
and ``sirius.infrastructure.data_path_validator`` know those details).

Messages on every error here are safe to show directly to the user: they
never include tracebacks or OS-internal detail beyond a short, translated
explanation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class DataLocationError(RuntimeError):
    """Base error for pre-bootstrap data-location operations."""


class LocationFileCorruptedError(DataLocationError):
    """Raised when the external pointer file exists but cannot be trusted.

    Never triggers a silent fallback to the default database: the caller
    must show a recovery screen and only overwrite the file after a new,
    explicit, validated choice (``LocationStore.save``).
    """


class DataPathInvalidError(DataLocationError):
    """Raised when a candidate data path fails a physical validation check
    (not absolute, invalid Windows characters, blocked by a file, cannot be
    created, or cannot be proven writable)."""


class DataPathHasExistingInstallationError(DataPathInvalidError):
    """Raised when a non-default candidate path already contains a Sirius
    installation. B2b never adopts, migrates, or overwrites existing data
    outside the default path — this always stops the flow."""


@dataclass(frozen=True, slots=True)
class DataPathCheck:
    """Facts about a validated (and possibly just-created) candidate directory.

    Purely descriptive: this layer never decides whether an existing
    installation is acceptable. That policy belongs to the application use
    case, which knows whether the candidate is the default path (where an
    existing installation is expected and welcome) or a custom one (where
    B2b forbids adopting existing data).
    """

    path: Path
    has_existing_installation: bool
    is_onedrive: bool


class LocationStore(Protocol):
    """Persists and loads the chosen data directory, external to that directory.

    Lives in a location that is fixed and independent of the data directory
    it points to, so it can be read before the data directory itself is
    known.
    """

    def load(self) -> Path | None:
        """Return the previously saved data directory, or None if never saved.

        Raises ``LocationFileCorruptedError`` if the pointer file exists but
        cannot be parsed or trusted.
        """
        ...

    def save(self, data_dir: Path) -> None:
        """Persist the chosen data directory atomically, replacing any prior value."""
        ...


class DataPathValidator(Protocol):
    """Validates and, if requested, creates a candidate data directory.

    Never treats ``os.access()`` as sufficient proof of write access: every
    check that claims write access actually creates and deletes a small,
    content-free temporary file.
    """

    def peek(self, candidate: Path) -> DataPathCheck:
        """Read-only inspection: never creates, writes, or raises for a
        missing path. Used only to decide whether the default path already
        holds a usable installation, without touching the filesystem."""
        ...

    def validate(self, candidate: Path, *, allow_create: bool) -> DataPathCheck:
        """Fully validate ``candidate`` (and create it if ``allow_create`` and
        it does not exist yet), proving real write access.

        Raises ``DataPathInvalidError`` for any physical problem. Never
        leaves a partially created directory behind on failure.
        """
        ...
