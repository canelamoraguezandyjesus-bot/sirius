"""Presentation-facing use case for creating an encrypted single-file backup.

Keeps the dependency direction from AGENTS.md intact: ``presentation`` may
only know use cases of ``application`` (mirrors ``ApiKeySettingsUseCase``
and ``SendMessageUseCase``), never the ``BackupService`` port or its SQLite
adapter directly.
"""

from __future__ import annotations

from sirius.ports.backup import BackupError, BackupResult, BackupService, BackupTooLargeError

__all__ = ["BackupError", "BackupTooLargeError", "CreateBackupUseCase"]


class CreateBackupUseCase:
    """Creates a validated, encrypted single-file backup of Sirius's data."""

    def __init__(self, backup_service: BackupService) -> None:
        self._backup_service = backup_service

    def create_backup(self, password: str) -> BackupResult:
        return self._backup_service.create_backup(password)
