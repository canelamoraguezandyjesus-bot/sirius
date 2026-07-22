"""Unit tests for FilesystemExportService (SIRIUS-ARQ-0.1 S12.1).

Uses domain entities built directly in memory (no SQLite) and a
``FakeClock`` so the export directory name is fully deterministic. SQLite
integration is covered separately by
``tests/integration/test_export_structured.py``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius import __version__ as APP_VERSION
from sirius.adapters.clock.fake import FakeClock
from sirius.adapters.export.filesystem_export_service import FilesystemExportService
from sirius.adapters.persistence.migrations import get_supported_schema_version
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.domain.project import Project, ProjectRevision, ProjectStatus
from sirius.ports.export import ExportError

_FIXED_NOW = datetime(2026, 3, 1, 14, 37, 12, tzinfo=UTC)
_EXPECTED_FILES = (
    "manifest.json",
    "conversation.jsonl",
    "project.json",
    "memories.jsonl",
    "decisions.jsonl",
    "README.txt",
)


def _service(now: datetime = _FIXED_NOW) -> FilesystemExportService:
    return FilesystemExportService(FakeClock(now))


def _message(sequence: int, *, status: MessageStatus = MessageStatus.COMPLETED) -> Message:
    return Message(
        id=sequence,
        conversation_id=1,
        sequence=sequence,
        role=MessageRole.USER if sequence % 2 else MessageRole.SIRIUS,
        content=f"mensaje {sequence}",
        created_at=_FIXED_NOW,
        operation_id=f"op-{sequence}",
        identity_version=1 if sequence % 2 == 0 else None,
        status=status,
    )


def _project() -> Project:
    revision = ProjectRevision(
        id=1,
        project_id=1,
        version=2,
        objective="objetivo real",
        state_summary="en marcha",
        blockers=("bloqueo 1", "bloqueo 2"),
        next_step="siguiente paso",
        source_event_id=None,
        created_at=_FIXED_NOW,
    )
    return Project(
        id=1,
        name="Mi proyecto",
        status=ProjectStatus.ACTIVE,
        current_revision=revision,
        created_at=_FIXED_NOW,
        updated_at=_FIXED_NOW,
        completed_at=None,
    )


def _unconfigured_project() -> Project:
    return Project(
        id=1,
        name="",
        status=ProjectStatus.ACTIVE,
        current_revision=None,
        created_at=_FIXED_NOW,
        updated_at=_FIXED_NOW,
        completed_at=None,
    )


def _memory(memory_id: int) -> Memory:
    revision = MemoryRevision(
        id=memory_id,
        memory_id=memory_id,
        version=1,
        content="prefiere respuestas breves",
        origin="Guardado manual",
        source_event_id=None,
        created_at=_FIXED_NOW,
    )
    return Memory(
        id=memory_id,
        status=MemoryStatus.CURRENT,
        current_revision=revision,
        created_at=_FIXED_NOW,
        updated_at=_FIXED_NOW,
        subject_key="tono",
        project_id=1,
    )


def _decision(decision_id: int) -> Decision:
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content="usar tono formal",
        source_event_id=None,
        created_at=_FIXED_NOW,
    )
    return Decision(
        id=decision_id,
        subject="tono",
        project_id=1,
        status=DecisionStatus.APPROVED,
        current_revision=revision,
        created_at=_FIXED_NOW,
        updated_at=_FIXED_NOW,
    )


def test_export_structured_creates_a_directory_named_from_the_injected_clock(
    tmp_path: Path,
) -> None:
    result = _service().export_structured(
        tmp_path, messages=[], project=None, memories=[], decisions=[]
    )

    assert result == tmp_path / "sirius-export-20260301-1437"
    assert result.is_dir()


def test_export_structured_writes_exactly_the_six_approved_files(tmp_path: Path) -> None:
    result = _service().export_structured(
        tmp_path, messages=[], project=None, memories=[], decisions=[]
    )

    assert {p.name for p in result.iterdir()} == set(_EXPECTED_FILES)


def test_manifest_has_format_app_version_schema_date_and_file_list(tmp_path: Path) -> None:
    result = _service().export_structured(
        tmp_path, messages=[], project=None, memories=[], decisions=[]
    )

    manifest = json.loads((result / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format"] == "sirius-export"
    assert manifest["app_version"] == APP_VERSION
    assert manifest["schema_version"] == get_supported_schema_version()
    assert manifest["created_at"] == _FIXED_NOW.isoformat()
    assert manifest["files"] == list(_EXPECTED_FILES)


def test_conversation_jsonl_has_one_line_per_message_in_order_with_required_fields(
    tmp_path: Path,
) -> None:
    messages = [_message(1), _message(2, status=MessageStatus.CANCELLED)]

    result = _service().export_structured(
        tmp_path, messages=messages, project=None, memories=[], decisions=[]
    )

    lines = (result / "conversation.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first == {
        "role": "user",
        "content": "mensaje 1",
        "status": "completed",
        "created_at": _FIXED_NOW.isoformat(),
        "operation_id": "op-1",
        "identity_version": None,
    }
    second = json.loads(lines[1])
    assert second["status"] == "cancelled"
    assert second["role"] == "sirius"
    assert second["identity_version"] == 1


def test_project_json_is_null_when_no_project_is_configured(tmp_path: Path) -> None:
    cases = {"no-project": None, "unconfigured-placeholder": _unconfigured_project()}
    for case_name, project in cases.items():
        result = _service().export_structured(
            tmp_path / case_name,
            messages=[],
            project=project,
            memories=[],
            decisions=[],
        )
        assert json.loads((result / "project.json").read_text(encoding="utf-8")) is None


def test_project_json_reflects_the_active_project_and_its_current_revision(tmp_path: Path) -> None:
    result = _service().export_structured(
        tmp_path, messages=[], project=_project(), memories=[], decisions=[]
    )

    data = json.loads((result / "project.json").read_text(encoding="utf-8"))
    assert data["name"] == "Mi proyecto"
    assert data["status"] == "active"
    assert data["current_revision"]["objective"] == "objetivo real"
    assert data["current_revision"]["blockers"] == ["bloqueo 1", "bloqueo 2"]
    assert data["current_revision"]["version"] == 2


def test_memories_jsonl_has_one_line_per_current_memory(tmp_path: Path) -> None:
    result = _service().export_structured(
        tmp_path, messages=[], project=None, memories=[_memory(1), _memory(2)], decisions=[]
    )

    lines = (result / "memories.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["current_revision"]["content"] == "prefiere respuestas breves"
    assert first["subject_key"] == "tono"


def test_decisions_jsonl_has_one_line_per_current_decision(tmp_path: Path) -> None:
    result = _service().export_structured(
        tmp_path, messages=[], project=None, memories=[], decisions=[_decision(1)]
    )

    lines = (result / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    decision = json.loads(lines[0])
    assert decision["subject"] == "tono"
    assert decision["status"] == "approved"
    assert decision["current_revision"]["content"] == "usar tono formal"


def test_readme_explains_the_content_and_the_api_key_warning(tmp_path: Path) -> None:
    result = _service().export_structured(
        tmp_path, messages=[], project=None, memories=[], decisions=[]
    )

    readme_text = (result / "README.txt").read_text(encoding="utf-8")
    assert "clave de API" in readme_text
    assert "información personal" in readme_text


def test_export_structured_refuses_to_overwrite_an_existing_export(tmp_path: Path) -> None:
    service = _service()
    service.export_structured(tmp_path, messages=[], project=None, memories=[], decisions=[])

    with pytest.raises(ExportError):
        service.export_structured(tmp_path, messages=[], project=None, memories=[], decisions=[])


def test_export_structured_leaves_no_partial_directory_on_a_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sirius.adapters.export.filesystem_export_service as module

    def _boom(_value: dict[str, object]) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "_json_dumps", _boom)

    with pytest.raises(RuntimeError):
        _service().export_structured(tmp_path, messages=[], project=None, memories=[], decisions=[])

    assert list(tmp_path.iterdir()) == []
