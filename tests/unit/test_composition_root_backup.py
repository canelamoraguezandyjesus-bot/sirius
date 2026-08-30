"""Unit tests for the composition root's backup/recovery wiring.

Only checks that the right types come out and that the disposal callable is
safe to use; the backup/recovery *behavior* itself is covered by the adapter
and use-case tests, and end-to-end by ``tests/gui/test_backup_recovery_ui.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.persistence import staged_engine_port as staged_engine_port_module
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


def test_close_database_connections_also_disposes_the_staged_engine_port_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAUDE-REVISOR-001: build_conversation_dependencies wires a private
    Engine for staged_engine_port (RankRelevantKnowledgeUseCase) that isn't
    part of ``repositories``. On Windows an undisposed pool here would block
    RestoreBackupUseCase's atomic file replace exactly like an undisposed
    repository pool would, so it must be disposed too.
    """
    built_ports = []
    original_build_staged_engine_port = staged_engine_port_module.build_staged_engine_port

    def capturing_build_staged_engine_port(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        port = original_build_staged_engine_port(*args, **kwargs)  # type: ignore[arg-type]
        built_ports.append(port)
        return port

    monkeypatch.setattr(
        "sirius.composition_root.build_staged_engine_port", capturing_build_staged_engine_port
    )

    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert len(built_ports) == 1
    engine = built_ports[0]._engine
    assert engine is not None
    pool_before_close = engine.pool

    dependencies.close_database_connections()

    # SQLAlchemy's Engine.dispose() replaces the pool with a fresh, empty one,
    # discarding every connection the old pool held open. A different pool
    # identity is the observable proof this engine's pool was disposed.
    assert engine.pool is not pool_before_close
