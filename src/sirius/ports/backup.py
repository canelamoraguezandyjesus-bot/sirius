"""Encrypted single-file backup contract.

Method name mirrors SIRIUS-ARQ-0.1 S4: ``create_backup``. ``validate_backup``
and ``restore_backup`` belong to a later increment of V7 and are
deliberately absent until that work is approved and implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


class BackupError(RuntimeError):
    """Raised when creating a backup fails.

    The message is always safe: it never includes the backup password or
    any decrypted content.
    """


class BackupTooLargeError(BackupError):
    """Raised when the encrypted backup file would exceed the 100 MB limit.

    SIRIUS-ARQ-0.1 S12.2: "Si el archivo supera 100 MB ... la arquitectura
    debe migrar a cifrado por flujo antes de ampliar el volumen." Sirius 0.1
    does not implement streaming encryption, so it refuses instead.
    """


@dataclass(frozen=True, slots=True)
class BackupManifest:
    """Metadata describing one backup package (SIRIUS-ARQ-0.1 S12.2)."""

    format: str
    app_version: str
    schema_version: str
    created_at: datetime
    sha256: str


@dataclass(frozen=True, slots=True)
class BackupResult:
    """The outcome of a successfully created and self-validated backup."""

    path: Path
    manifest: BackupManifest
    size_bytes: int


class BackupService(Protocol):
    """Contract implemented by the encrypted single-file backup adapter."""

    def create_backup(self, password: str) -> BackupResult:
        """Create a validated, encrypted single-file backup and return it.

        Never includes the OpenAI API key. Raises ``BackupError`` (or the
        more specific ``BackupTooLargeError``) instead of writing a partial
        or unvalidated file.
        """
        ...
