"""Unit tests for ``CreateBackupUseCase``: the only backup-related API
``presentation`` is allowed to touch, per AGENTS.md's inward dependency rule.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius.application.create_backup import CreateBackupUseCase
from sirius.ports.backup import BackupError, BackupManifest, BackupResult


class _FakeBackupService:
    def __init__(self, result: BackupResult | None = None, error: BackupError | None = None):
        self._result = result
        self._error = error
        self.received_passwords: list[str] = []

    def create_backup(self, password: str) -> BackupResult:
        self.received_passwords.append(password)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _fake_result(path: Path) -> BackupResult:
    manifest = BackupManifest(
        format="siriusbackup",
        app_version="0.1.0.dev0",
        schema_version="abc123",
        created_at=datetime.now(UTC),
        sha256="0" * 64,
    )
    return BackupResult(path=path, manifest=manifest, size_bytes=1024)


def test_create_backup_delegates_to_the_backup_service(tmp_path: Path) -> None:
    expected = _fake_result(tmp_path / "sirius-backup.siriusbackup")
    service = _FakeBackupService(result=expected)
    use_case = CreateBackupUseCase(service)

    result = use_case.create_backup("a password")

    assert result is expected
    assert service.received_passwords == ["a password"]


def test_create_backup_propagates_backup_errors() -> None:
    service = _FakeBackupService(error=BackupError("boom"))
    use_case = CreateBackupUseCase(service)

    with pytest.raises(BackupError):
        use_case.create_backup("a password")
