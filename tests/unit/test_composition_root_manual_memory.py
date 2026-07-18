"""Unit tests for the composition root's B4a wiring.

Confirms ``save_manual_memory_use_case`` and ``get_memory_origin_use_case``
are built and share the same underlying repositories as the rest of the
application — no SQLite adapter is exposed to a caller, only the two use
cases (AGENTS.md: "No accedas a SQLite... desde la interfaz").
"""

from __future__ import annotations

from pathlib import Path

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.memory_origin import GetMemoryOriginUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.conversation import MessageRole


def test_build_conversation_dependencies_wires_manual_memory_use_cases(tmp_path: Path) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(dependencies.save_manual_memory_use_case, SaveManualMemoryUseCase)
    assert isinstance(dependencies.get_memory_origin_use_case, GetMemoryOriginUseCase)


def test_saved_memory_origin_is_queryable_through_the_wired_use_cases(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    dependencies = build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )

    result = dependencies.send_message_use_case.send_message("guarda que prefiero brevedad")
    memory = dependencies.save_manual_memory_use_case.save(
        "El usuario prefiere respuestas breves", message_id=result.user_message.id
    )

    origin = dependencies.get_memory_origin_use_case.get_origin(memory.id)

    assert origin.message_id == result.user_message.id
    assert origin.message_content == "guarda que prefiero brevedad"
    assert result.user_message.role == MessageRole.USER
