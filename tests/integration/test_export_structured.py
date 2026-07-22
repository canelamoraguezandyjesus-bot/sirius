"""End-to-end integration test for the B9a structured export (RF-031, ATD-009,
SIRIUS-ARQ-0.1 S12.1).

Wires the real SQLite adapters (no fakes), a real Alembic-migrated database,
and ``FilesystemExportService`` with a deterministic ``FakeClock`` exactly as
``composition_root`` does, proving the whole read-only vertical slice: the
export contains real conversation, project, memory and decision data, uses
only vigente (current/approved) items, names its directory from the injected
clock, is valid UTF-8 JSON/JSONL, and never mutates the source database.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius.adapters.clock.fake import FakeClock
from sirius.adapters.export.filesystem_export_service import FilesystemExportService
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.export_structured import ExportStructuredUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.conversation import MessageRole, MessageStatus

_FIXED_NOW = datetime(2026, 3, 1, 9, 5, tzinfo=UTC)


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "sirius.db"
    upgrade_to_head(path)
    return path


def _build_use_case(database_path: Path, now: datetime = _FIXED_NOW) -> ExportStructuredUseCase:
    return ExportStructuredUseCase(
        FilesystemExportService(FakeClock(now)),
        build_sqlite_conversation_repository(database_path),
        build_sqlite_project_repository(database_path),
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    )


@pytest.mark.integration
def test_export_structured_creates_the_deterministic_directory_name(
    database_path: Path, tmp_path: Path
) -> None:
    use_case = _build_use_case(database_path)

    result = use_case.export_structured(tmp_path / "exports")

    assert result == tmp_path / "exports" / "sirius-export-20260301-0905"
    assert result.is_dir()


@pytest.mark.integration
def test_export_structured_writes_exactly_the_six_approved_files(
    database_path: Path, tmp_path: Path
) -> None:
    use_case = _build_use_case(database_path)

    result = use_case.export_structured(tmp_path / "exports")

    assert {p.name for p in result.iterdir()} == {
        "manifest.json",
        "conversation.jsonl",
        "project.json",
        "memories.jsonl",
        "decisions.jsonl",
        "README.txt",
    }


@pytest.mark.integration
def test_export_structured_with_no_project_configured_reports_absence_without_failing(
    database_path: Path, tmp_path: Path
) -> None:
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()  # neutral, unconfigured placeholder only

    use_case = _build_use_case(database_path)
    result = use_case.export_structured(tmp_path / "exports")

    assert json.loads((result / "project.json").read_text(encoding="utf-8")) is None


@pytest.mark.integration
def test_export_structured_contains_real_conversation_project_memory_and_decision_data(
    database_path: Path, tmp_path: Path
) -> None:
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(
        conversation.id, MessageRole.USER, "hola Sirius", operation_id="op-1"
    )
    conversation_repository.append_message(
        conversation.id,
        MessageRole.SIRIUS,
        "hola, ¿en qué trabajamos hoy?",
        operation_id="op-1",
        identity_version=1,
    )
    conversation_repository.append_message(
        conversation.id,
        MessageRole.SIRIUS,
        "respuesta parcial",
        operation_id="op-2",
        identity_version=1,
        status=MessageStatus.CANCELLED,
    )

    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Sirius 0.1",
        "Cerrar V8",
        state_summary="En marcha",
        blockers=("Falta validación manual",),
        next_step="Escribir la exportación",
    )

    unit_of_work = build_sqlite_unit_of_work(database_path)
    SaveManualMemoryUseCase(unit_of_work).save(
        "El usuario prefiere respuestas breves.", project_id=project.id
    )
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Formato de exportación", project.id, "Usar JSON/JSONL abierto"
    )
    ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)
    # A second, still-PROPOSED decision must never appear in the export: only
    # vigente (APPROVED) decisions belong in decisions.jsonl.
    ProposeDecisionUseCase(unit_of_work).propose("Segundo asunto", project.id, "Todavía en debate")

    use_case = _build_use_case(database_path)
    result = use_case.export_structured(tmp_path / "exports")

    conversation_lines = (result / "conversation.jsonl").read_text(encoding="utf-8").splitlines()
    messages = [json.loads(line) for line in conversation_lines]
    assert len(messages) == 3
    assert [m["role"] for m in messages] == ["user", "sirius", "sirius"]
    assert messages[0]["content"] == "hola Sirius"
    assert messages[0]["operation_id"] == "op-1"
    assert messages[2]["status"] == "cancelled"
    assert messages[2]["content"] == "respuesta parcial"

    project_data = json.loads((result / "project.json").read_text(encoding="utf-8"))
    assert project_data["name"] == "Sirius 0.1"
    assert project_data["current_revision"]["objective"] == "Cerrar V8"
    assert project_data["current_revision"]["blockers"] == ["Falta validación manual"]

    memory_lines = (result / "memories.jsonl").read_text(encoding="utf-8").splitlines()
    memories = [json.loads(line) for line in memory_lines]
    assert len(memories) == 1
    assert memories[0]["current_revision"]["content"] == "El usuario prefiere respuestas breves."
    assert memories[0]["status"] == "current"

    decision_lines = (result / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    decisions = [json.loads(line) for line in decision_lines]
    assert len(decisions) == 1
    assert decisions[0]["subject"] == "Formato de exportación"
    assert decisions[0]["status"] == "approved"
    assert decisions[0]["current_revision"]["content"] == "Usar JSON/JSONL abierto"


@pytest.mark.integration
def test_export_structured_never_mutates_the_source_database(
    database_path: Path, tmp_path: Path
) -> None:
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "hola")

    before = database_path.read_bytes()
    use_case = _build_use_case(database_path)
    use_case.export_structured(tmp_path / "exports")
    after = database_path.read_bytes()

    assert before == after
