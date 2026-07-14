"""Encrypted single-file backup contract.

SIRIUS-ARQ-0.1 S4 defines three operations: create, validate, and restore.
This increment implements creation and validation; restoration remains a later
V7 block.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


class BackupError(RuntimeError):
    """Raised when a backup operation fails.

    The message is always safe: it never includes the backup password or any
    decrypted content.
    """


class BackupValidationError(BackupError):
    """Raised when a backup cannot be validated safely."""


class BackupTooLargeError(BackupError):
    """Raised when a backup exceeds the 100 MB in-memory limit.

    SIRIUS-ARQ-0.1 S12.2 requires streaming encryption before increasing this
    limit. Sirius 0.1 therefore refuses oversized files.
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


@dataclass(frozen=True, slots=True)
class BackupValidationResult:
    """Metadata returned after a backup file passes every validation check."""

    path: Path
    manifest: BackupManifest
    size_bytes: int


class BackupService(Protocol):
    """Contract implemented by the encrypted single-file backup adapter."""

    def create_backup(self, password: str) -> BackupResult:
        """Create a validated, encrypted single-file backup and return it."""
        ...

    def validate_backup(self, backup_path: Path, password: str) -> BackupValidationResult:
        """Validate password, format, hashes, version, schema, and SQLite integrity."""
        ...
