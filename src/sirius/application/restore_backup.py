"""Presentation-facing use case for restoring an encrypted single-file backup.

Keeps the dependency direction from AGENTS.md intact: ``presentation`` may
only know use cases of ``application`` (mirrors ``CreateBackupUseCase`` and
``ValidateBackupUseCase``), never the ``BackupService`` port or its SQLite
adapter directly.
"""

from __future__ import annotations

from pathlib import Path

from sirius.ports.backup import (
    BackupConfirmationRequiredError,
    BackupRestoreError,
    BackupRestoreResult,
    BackupService,
    BackupTooLargeError,
    BackupValidationError,
)

__all__ = [
    "BackupConfirmationRequiredError",
    "BackupRestoreError",
    "BackupTooLargeError",
    "BackupValidationError",
    "RestoreBackupUseCase",
]


class RestoreBackupUseCase:
    """Restores a validated backup atomically after explicit confirmation."""

    def __init__(self, backup_service: BackupService) -> None:
        self._backup_service = backup_service

    def restore_backup(
        self, backup_path: Path, password: str, *, confirmed: bool
    ) -> BackupRestoreResult:
        return self._backup_service.restore_backup(backup_path, password, confirmed=confirmed)
