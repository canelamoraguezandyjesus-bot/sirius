"""Application use case for the open, human-readable structured export (B9a).

SIRIUS-ARQ-0.1 S12.1 / RF-031 / ATD-009 "exportación abierta". Distinct from
``CreateBackupUseCase`` (encrypted, password-protected): this export is meant
to be read without Sirius and must never contain the API key (RNF-013).

Gathers conversation, active project, current memories and current decisions
through the existing read-only repositories — never SQLite or SQLAlchemy
directly — and delegates writing to ``ExportService``. Presentation wiring
(the pre-export personal-data warning, the background thread, showing the
resulting path) is B9b and does not exist yet: no presentation code calls
this use case in this cut.
"""

from __future__ import annotations

from pathlib import Path

from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.export import ExportError, ExportService
from sirius.ports.memory_repository import MemoryRepository
from sirius.ports.project_repository import ProjectRepository

__all__ = ["ExportError", "ExportStructuredUseCase"]


class ExportStructuredUseCase:
    """Orchestrates a read-only S12.1 structured export."""

    def __init__(
        self,
        export_service: ExportService,
        conversation_repository: ConversationRepository,
        project_repository: ProjectRepository,
        memory_repository: MemoryRepository,
        decision_repository: DecisionRepository,
    ) -> None:
        self._export_service = export_service
        self._conversation_repository = conversation_repository
        self._project_repository = project_repository
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository

    def export_structured(self, destination_dir: Path) -> Path:
        conversation = self._conversation_repository.get_main_conversation()
        messages = (
            self._conversation_repository.list_messages(conversation.id)
            if conversation is not None
            else []
        )
        project = self._project_repository.get_active_project()
        memories = self._memory_repository.list_current_memories()
        decisions = self._decision_repository.list_current_decisions()

        return self._export_service.export_structured(
            destination_dir,
            messages=messages,
            project=project,
            memories=memories,
            decisions=decisions,
        )
