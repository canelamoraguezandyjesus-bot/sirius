"""Unit tests for ExportStructuredUseCase's read-only orchestration (B9a).

Exercises only the wiring between the four repositories and the
``ExportService`` port with static/recording test doubles; the real
filesystem writing behavior is covered by
``tests/unit/test_filesystem_export_service.py`` and
``tests/integration/test_export_structured.py``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from sirius.application.export_structured import ExportStructuredUseCase
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.criticality import Criticality
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.domain.project import Project, ProjectRevision, ProjectStatus

_NOW = datetime(2026, 3, 1, tzinfo=UTC)


def _message(message_id: int) -> Message:
    return Message(
        id=message_id,
        conversation_id=1,
        sequence=message_id,
        role=MessageRole.USER,
        content="hola",
        created_at=_NOW,
        status=MessageStatus.COMPLETED,
    )


def _project() -> Project:
    revision = ProjectRevision(
        id=1,
        project_id=1,
        version=1,
        objective="objetivo",
        state_summary="estado",
        blockers=(),
        next_step="siguiente",
        source_event_id=None,
        created_at=_NOW,
    )
    return Project(
        id=1,
        name="Proyecto",
        status=ProjectStatus.ACTIVE,
        current_revision=revision,
        created_at=_NOW,
        updated_at=_NOW,
        completed_at=None,
    )


def _memory(memory_id: int) -> Memory:
    revision = MemoryRevision(
        id=memory_id,
        memory_id=memory_id,
        version=1,
        content="recuerdo",
        origin="Guardado manual",
        source_event_id=None,
        created_at=_NOW,
    )
    return Memory(
        id=memory_id,
        status=MemoryStatus.CURRENT,
        current_revision=revision,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _decision(decision_id: int) -> Decision:
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content="decisión",
        source_event_id=None,
        created_at=_NOW,
    )
    return Decision(
        id=decision_id,
        subject="asunto",
        project_id=1,
        status=DecisionStatus.APPROVED,
        current_revision=revision,
        created_at=_NOW,
        updated_at=_NOW,
    )


class _StaticConversationRepository:
    def __init__(self, conversation: Conversation | None, messages: list[Message]) -> None:
        self._conversation = conversation
        self._messages = messages
        self.list_messages_calls: list[int] = []

    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("export_structured() must never create a conversation")

    def get_main_conversation(self) -> Conversation | None:
        return self._conversation

    def append_message(self, *args: object, **kwargs: object) -> Message:
        raise AssertionError("export_structured() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        self.list_messages_calls.append(conversation_id)
        return self._messages

    def get_message(self, message_id: int) -> Message | None:
        raise AssertionError("export_structured() must never look up a single message")

    def redact_message(self, message_id: int) -> Message:
        raise AssertionError("export_structured() must never redact a message")


class _StaticProjectRepository:
    def __init__(self, project: Project | None) -> None:
        self._project = project

    def get_active_project(self) -> Project | None:
        return self._project

    def get_project(self, project_id: int) -> Project | None:
        raise AssertionError("export_structured() must never look up a project by id")

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        raise AssertionError("export_structured() must never list project revisions")

    def ensure_bootstrap_project(self) -> None:
        raise AssertionError("export_structured() must never seed a project")

    def create_project(self, *args: object, **kwargs: object) -> Project:
        raise AssertionError("export_structured() must never create a project")

    def append_revision(self, *args: object, **kwargs: object) -> Project:
        raise AssertionError("export_structured() must never append a revision")

    def complete_active_project(self, project_id: int) -> Project:
        raise AssertionError("export_structured() must never complete a project")

    def list_completed_projects(self) -> tuple[Project, ...]:
        raise AssertionError("export_structured() must never list completed projects")


class _StaticMemoryRepository:
    def __init__(self, memories: list[Memory]) -> None:
        self._memories = memories

    def create_memory(self, *args: object, **kwargs: object) -> Memory:
        raise AssertionError("export_structured() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("export_structured() must never look up a single memory")

    def list_current_memories(self) -> list[Memory]:
        return self._memories

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError("export_structured() must never list memories by category")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("export_structured() must never list archived memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("export_structured() must never read memory history")

    def correct_memory(self, *args: object, **kwargs: object) -> Memory:
        raise AssertionError("export_structured() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("export_structured() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("export_structured() must never delete a memory")

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("export() must never set a category")

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError("export() must never set a category")

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError("export() must never list uncategorized memories")

    def set_user_criticality(self, memory_id: int, criticality: Criticality | None) -> Memory:
        raise AssertionError("export() must never list uncategorized memories")

    def list_current_memories_by_criticality(self, levels: Sequence[Criticality]) -> list[Memory]:
        raise AssertionError("export() must never list uncategorized memories")


class _StaticDecisionRepository:
    def __init__(self, decisions: list[Decision]) -> None:
        self._decisions = decisions

    def create_proposal(self, *args: object, **kwargs: object) -> Decision:
        raise AssertionError("export_structured() must never propose a decision")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("export_structured() must never look up a single decision")

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("export_structured() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("export_structured() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        return self._decisions

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        raise AssertionError("export_structured() must never list decisions by category")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("export_structured() must never list proposed decisions")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("export_structured() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("export_structured() must never list archived decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("export_structured() must never look up a superseding decision")

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("export() must never set a category")

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError("export() must never set a category")

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError("export() must never list uncategorized decisions")

    def set_user_criticality(self, decision_id: int, criticality: Criticality | None) -> Decision:
        raise AssertionError("export() must never list uncategorized decisions")

    def list_current_decisions_by_criticality(
        self, levels: Sequence[Criticality]
    ) -> list[Decision]:
        raise AssertionError("export() must never list uncategorized decisions")


class _RecordingExportService:
    def __init__(self, result: Path) -> None:
        self._result = result
        self.calls: list[dict[str, object]] = []

    def export_structured(
        self,
        destination_dir: Path,
        *,
        messages: Sequence[Message],
        project: Project | None,
        memories: Sequence[Memory],
        decisions: Sequence[Decision],
    ) -> Path:
        self.calls.append(
            {
                "destination_dir": destination_dir,
                "messages": list(messages),
                "project": project,
                "memories": list(memories),
                "decisions": list(decisions),
            }
        )
        return self._result


def test_export_structured_gathers_data_and_delegates_to_the_service(tmp_path: Path) -> None:
    conversation = Conversation(id=1, created_at=_NOW)
    messages = [_message(1), _message(2)]
    project = _project()
    memories = [_memory(1)]
    decisions = [_decision(1)]
    expected_result = tmp_path / "sirius-export-20260301-0000"
    export_service = _RecordingExportService(expected_result)

    use_case = ExportStructuredUseCase(
        export_service,
        _StaticConversationRepository(conversation, messages),
        _StaticProjectRepository(project),
        _StaticMemoryRepository(memories),
        _StaticDecisionRepository(decisions),
    )

    result = use_case.export_structured(tmp_path)

    assert result == expected_result
    assert len(export_service.calls) == 1
    call = export_service.calls[0]
    assert call["destination_dir"] == tmp_path
    assert call["messages"] == messages
    assert call["project"] == project
    assert call["memories"] == memories
    assert call["decisions"] == decisions


def test_export_structured_never_lists_messages_without_a_conversation(tmp_path: Path) -> None:
    conversation_repository = _StaticConversationRepository(None, [])
    export_service = _RecordingExportService(tmp_path / "sirius-export-20260301-0000")

    use_case = ExportStructuredUseCase(
        export_service,
        conversation_repository,
        _StaticProjectRepository(None),
        _StaticMemoryRepository([]),
        _StaticDecisionRepository([]),
    )

    use_case.export_structured(tmp_path)

    assert conversation_repository.list_messages_calls == []
    assert export_service.calls[0]["messages"] == []
    assert export_service.calls[0]["project"] is None
