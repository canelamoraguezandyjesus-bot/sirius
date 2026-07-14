"""Unit tests for the presentation-facing backup restoration use case."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius.application.restore_backup import RestoreBackupUseCase
from sirius.ports.backup import (
    BackupConfirmationRequiredError,
    BackupManifest,
    BackupRestoreResult,
    BackupResult,
    BackupValidationError,
    BackupValidationResult,
)


class _FakeBackupService:
    def __init__(
        self,
        result: BackupRestoreResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received: list[tuple[Path, str, bool]] = []

    def create_backup(self, password: str) -> BackupResult:
        raise NotImplementedError

    def validate_backup(self, backup_path: Path, password: str) -> BackupValidationResult:
        raise NotImplementedError

    def restore_backup(
        self, backup_path: Path, password: str, *, confirmed: bool
    ) -> BackupRestoreResult:
        self.received.append((backup_path, password, confirmed))
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _fake_result(path: Path, safety_backup_path: Path | None) -> BackupRestoreResult:
    manifest = BackupManifest(
        format="siriusbackup",
        app_version="0.1.0.dev0",
        schema_version="abc123",
        created_at=datetime.now(UTC),
        sha256="0" * 64,
    )
    return BackupRestoreResult(
        path=path,
        manifest=manifest,
        size_bytes=1024,
        safety_backup_path=safety_backup_path,
    )


def test_restore_backup_delegates_with_the_confirmation_flag(tmp_path: Path) -> None:
    backup_path = tmp_path / "copy.siriusbackup"
    safety_path = tmp_path / "safety.siriusbackup"
    expected = _fake_result(backup_path, safety_path)
    service = _FakeBackupService(result=expected)
    use_case = RestoreBackupUseCase(service)

    result = use_case.restore_backup(backup_path, "a password", confirmed=True)

    assert result is expected
    assert service.received == [(backup_path, "a password", True)]


def test_restore_backup_propagates_missing_confirmation(tmp_path: Path) -> None:
    error = BackupConfirmationRequiredError("confirmación requerida")
    service = _FakeBackupService(error=error)
    use_case = RestoreBackupUseCase(service)

    with pytest.raises(BackupConfirmationRequiredError):
        use_case.restore_backup(tmp_path / "copy.siriusbackup", "a password", confirmed=False)


def test_restore_backup_propagates_safe_validation_errors(tmp_path: Path) -> None:
    error = BackupValidationError("copia inválida")
    service = _FakeBackupService(error=error)
    use_case = RestoreBackupUseCase(service)

    with pytest.raises(BackupValidationError, match="copia inválida"):
        use_case.restore_backup(tmp_path / "copy.siriusbackup", "a password", confirmed=True)
