"""Unit tests for the composition root's backup/recovery wiring.

Only checks that the right types come out and that the disposal callable is
safe to use; the backup/recovery *behavior* itself is covered by the adapter
and use-case tests, and end-to-end by ``tests/gui/test_backup_recovery_ui.py``.
"""

from __future__ import annotations

from pathlib import Path

from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.create_backup import CreateBackupUseCase
from sirius.application.restore_backup import RestoreBackupUseCase
from sirius.application.validate_backup import ValidateBackupUseCase
from sirius.composition_root import build_conversation_dependencies


def test_build_conversation_dependencies_wires_the_three_backup_use_cases(
    tmp_path: Path,
) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(dependencies.create_backup_use_case, CreateBackupUseCase)
    assert isinstance(dependencies.validate_backup_use_case, ValidateBackupUseCase)
    assert isinstance(dependencies.restore_backup_use_case, RestoreBackupUseCase)


def test_build_conversation_dependencies_provides_a_callable_to_close_connections(
    tmp_path: Path,
) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert callable(dependencies.close_database_connections)
    dependencies.close_database_connections()  # must not raise


def test_close_database_connections_is_safe_to_call_more_than_once(tmp_path: Path) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    dependencies.close_database_connections()
    dependencies.close_database_connections()  # Engine.dispose() is idempotent
