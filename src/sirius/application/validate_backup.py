"""Presentation-facing use case for validating an encrypted backup file."""

from __future__ import annotations

from pathlib import Path

from sirius.ports.backup import (
    BackupService,
    BackupTooLargeError,
    BackupValidationError,
    BackupValidationResult,
)

__all__ = [
    "BackupTooLargeError",
    "BackupValidationError",
    "ValidateBackupUseCase",
]


class ValidateBackupUseCase:
    """Validate a backup without changing the current Sirius database."""

    def __init__(self, backup_service: BackupService) -> None:
        self._backup_service = backup_service

    def validate_backup(
        self, backup_path: Path, password: str
    ) -> BackupValidationResult:
        return self._backup_service.validate_backup(backup_path, password)
