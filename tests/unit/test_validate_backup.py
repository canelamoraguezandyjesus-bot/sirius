"""Unit tests for the presentation-facing backup validation use case."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius.application.validate_backup import ValidateBackupUseCase
from sirius.ports.backup import (
    BackupManifest,
    BackupResult,
    BackupValidationError,
    BackupValidationResult,
)


class _FakeBackupService:
    def __init__(
        self,
        result: BackupValidationResult | None = None,
        error: BackupValidationError | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received: list[tuple[Path, str]] = []

    def create_backup(self, password: str) -> BackupResult:
        raise NotImplementedError

    def validate_backup(
        self, backup_path: Path, password: str
    ) -> BackupValidationResult:
        self.received.append((backup_path, password))
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _fake_result(path: Path) -> BackupValidationResult:
    manifest = BackupManifest(
        format="siriusbackup",
        app_version="0.1.0.dev0",
        schema_version="abc123",
        created_at=datetime.now(UTC),
        sha256="0" * 64,
    )
    return BackupValidationResult(path=path, manifest=manifest, size_bytes=1024)


def test_validate_backup_delegates_without_modifying_the_path(tmp_path: Path) -> None:
    path = tmp_path / "copy.siriusbackup"
    expected = _fake_result(path)
    service = _FakeBackupService(result=expected)
    use_case = ValidateBackupUseCase(service)

    result = use_case.validate_backup(path, "a password")

    assert result is expected
    assert service.received == [(path, "a password")]


def test_validate_backup_propagates_safe_validation_errors(tmp_path: Path) -> None:
    error = BackupValidationError("copia inválida")
    service = _FakeBackupService(error=error)
    use_case = ValidateBackupUseCase(service)

    with pytest.raises(BackupValidationError, match="copia inválida"):
        use_case.validate_backup(tmp_path / "copy.siriusbackup", "a password")
