"""Encrypted single-file backup contract.

SIRIUS-ARQ-0.1 S4 defines creation, validation, and restoration. All three
operations are implemented behind this port; presentation only uses application
use cases and never accesses the adapter directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


class BackupError(RuntimeError):
    """Raised when a backup operation fails.

    Messages are safe: they never include the backup password or decrypted
    content.
    """


class BackupValidationError(BackupError):
    """Raised when a backup cannot be validated safely."""


class BackupTooLargeError(BackupError):
    """Raised when a backup exceeds the 100 MB in-memory limit.

    SIRIUS-ARQ-0.1 S12.2 requires streaming encryption before increasing this
    limit. Sirius 0.1 therefore refuses oversized files.
    """


class BackupRestoreError(BackupError):
    """Raised when a validated backup cannot be restored safely."""


class BackupConfirmationRequiredError(BackupRestoreError):
    """Raised when a destructive restoration lacks explicit confirmation."""


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


@dataclass(frozen=True, slots=True)
class BackupValidationResult:
    """Metadata returned after a backup file passes every validation check."""

    path: Path
    manifest: BackupManifest
    size_bytes: int


@dataclass(frozen=True, slots=True)
class BackupRestoreResult:
    """The outcome of an atomic restoration and its pre-restore safety copy."""

    path: Path
    manifest: BackupManifest
    size_bytes: int
    safety_backup_path: Path | None


class BackupService(Protocol):
    """Contract implemented by the encrypted single-file backup adapter."""

    def create_backup(self, password: str) -> BackupResult:
        """Create a validated, encrypted single-file backup and return it."""
        ...

    def validate_backup(self, backup_path: Path, password: str) -> BackupValidationResult:
        """Validate password, format, hashes, version, schema, and SQLite integrity."""
        ...

    def restore_backup(
        self,
        backup_path: Path,
        password: str,
        *,
        confirmed: bool,
    ) -> BackupRestoreResult:
        """Restore a validated backup atomically after explicit confirmation."""
        ...
