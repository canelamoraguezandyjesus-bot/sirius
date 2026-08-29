"""Observable memory/decision panel (B4f: RF-019 a RF-026, PA-010 a PA-016).

Integrated as a tab of ``MainWindow`` — not a new window, not a separate
management application. Makes the recuerdos and decisiones already
implemented in B4a-B4e observable and operable: their origin, estado and
versión; correction and substitution through the already-existing use cases;
archival and deletion with explicit confirmation (including the source
message choice and the old-backup warning); and unresolved precedence
conflicts, shown for clarification but never resolved or picked silently
here (PA-014). Every write goes through an already-existing B4 use case —
this widget never touches ``MemoryRepository``, ``DecisionRepository``,
``UnitOfWork``, SQLAlchemy, or SQLite directly (AGENTS.md: dependency
direction presentación -> aplicación -> dominio).

Dialogs are shown only through injectable seams, exactly like
``MainWindow``/``ProjectContinuityWidget``: production defaults to real Qt
dialogs, tests inject recording/no-op doubles so ``scripts/check.ps1`` never
opens a real window on the desktop.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from sirius.application.approve_decision import (
    ApprovalNotConfirmedError,
    ApproveDecisionUseCase,
    InvalidDecisionStatusError,
)
from sirius.application.archive_decision import (
    ArchiveDecisionUseCase,
    DecisionNotArchivableError,
)
from sirius.application.archive_memory import ArchiveMemoryUseCase, MemoryNotArchivableError
from sirius.application.correct_memory import (
    CorrectMemoryUseCase,
    InvalidMemoryCorrectionDataError,
    MemoryNotCorrectableError,
)
from sirius.application.decision_origin import DecisionOrigin, GetDecisionOriginUseCase
from sirius.application.delete_memory import (
    OLD_BACKUP_WARNING,
    DeleteMemoryUseCase,
    DeletionNotConfirmedError,
    MemoryNotDeletableError,
    SourceMessageChoice,
)
from sirius.application.detect_precedence_conflicts import DetectPrecedenceConflictsUseCase
from sirius.application.knowledge_overview import GetKnowledgeOverviewUseCase, KnowledgeOverview
from sirius.application.memory_origin import GetMemoryOriginUseCase, MemoryOrigin
from sirius.application.project_continuity import (
    ProjectContinuityUseCase,
    ProjectNotConfiguredError,
)
from sirius.application.propose_decision import (
    InvalidDecisionProposalDataError,
    ProposeDecisionUseCase,
)
from sirius.application.save_manual_memory import (
    InvalidManualMemoryDataError,
    SaveManualMemoryUseCase,
)
from sirius.application.supersede_decision import (
    DecisionSupersessionNotConfirmedError,
    InvalidDecisionSupersessionError,
    SupersedeDecisionUseCase,
)
from sirius.domain.decision import Decision, is_same_subject_and_project
from sirius.domain.memory import Memory
from sirius.domain.precedence import PrecedenceOutcome
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)

_GENERIC_ERROR_TEXT = "No se pudo completar la operación. Inténtalo de nuevo."
_NO_SELECTION_TITLE = "Nada seleccionado"
_NO_PROJECT_WARNING = (
    "No hay un proyecto configurado todavía: no se puede proponer una decisión sin proyecto."
)


def _short(content: str | None, limit: int = 60) -> str:
    if content is None:
        return "(contenido eliminado)"
    text = content.strip().replace("\n", " ")
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _memory_label(memory: Memory) -> str:
    subject = f" [{memory.subject_key}]" if memory.subject_key is not None else ""
    return (
        f"#{memory.id} ({memory.status.value}) v{memory.current_revision.version}{subject} — "
        f"{_short(memory.current_revision.content)}"
    )


def _decision_label(decision: Decision) -> str:
    return (
        f"#{decision.id} ({decision.status.value}) v{decision.current_revision.version} — "
        f"{decision.subject}: {_short(decision.current_revision.content)}"
    )


class _DeleteMemoryDialog(QDialog):
    """Modal dialog for RF-025/PA-016/SP-06: an explicit, typed choice between
    preserving and redacting the memory's source message, with the approved
    warning about old backups always visible before confirming."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Eliminar recuerdo")

        warning_label = QLabel(OLD_BACKUP_WARNING)
        warning_label.setWordWrap(True)

        self.preserve_radio = QRadioButton("Conservar el mensaje fuente")
        self.redact_radio = QRadioButton("Redactar también el mensaje fuente")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)
        self.preserve_radio.toggled.connect(self._enable_ok_once_chosen)
        self.redact_radio.toggled.connect(self._enable_ok_once_chosen)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Esta acción eliminará el contenido de este recuerdo."))
        layout.addWidget(self.preserve_radio)
        layout.addWidget(self.redact_radio)
        layout.addWidget(warning_label)
        layout.addWidget(buttons)

    def _enable_ok_once_chosen(self, checked: bool) -> None:
        if checked:
            self._ok_button.setEnabled(True)

    def selected_choice(self) -> SourceMessageChoice:
        return (
            SourceMessageChoice.REDACT
            if self.redact_radio.isChecked()
            else SourceMessageChoice.PRESERVE
        )


class _ChooseSupersedingDecisionDialog(QDialog):
    """Modal dialog picking which decision supersedes an APPROVED one.

    Las candidatas pueden estar PROPOSED o ya APPROVED: el usuario puede haber
    aprobado la decisión nueva antes de ordenar la sustitución.
    """

    def __init__(self, candidates: Sequence[Decision], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sustituir decisión")
        self._candidates = list(candidates)

        self.combo = QComboBox()
        for decision in self._candidates:
            self.combo.addItem(_decision_label(decision))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Elige la decisión que sustituirá a la vigente:"))
        layout.addWidget(self.combo)
        layout.addWidget(buttons)

    def selected_decision(self) -> Decision:
        return self._candidates[self.combo.currentIndex()]


class KnowledgeWidget(QGroupBox):
    """Panel observable de recuerdos, decisiones y conflictos de precedencia."""

    def __init__(
        self,
        get_knowledge_overview_use_case: GetKnowledgeOverviewUseCase,
        save_manual_memory_use_case: SaveManualMemoryUseCase,
        get_memory_origin_use_case: GetMemoryOriginUseCase,
        correct_memory_use_case: CorrectMemoryUseCase,
        archive_memory_use_case: ArchiveMemoryUseCase,
        delete_memory_use_case: DeleteMemoryUseCase,
        propose_decision_use_case: ProposeDecisionUseCase,
        approve_decision_use_case: ApproveDecisionUseCase,
        get_decision_origin_use_case: GetDecisionOriginUseCase,
        supersede_decision_use_case: SupersedeDecisionUseCase,
        archive_decision_use_case: ArchiveDecisionUseCase,
        detect_precedence_conflicts_use_case: DetectPrecedenceConflictsUseCase,
        project_continuity_use_case: ProjectContinuityUseCase,
        *,
        show_warning: Callable[[str, str], None] | None = None,
        show_information: Callable[[str, str], None] | None = None,
        confirm_action: Callable[[str, str], bool] | None = None,
        prompt_line: Callable[[str, str], str | None] | None = None,
        prompt_multiline: Callable[[str, str], str | None] | None = None,
        confirm_delete_memory: Callable[[], SourceMessageChoice | None] | None = None,
        choose_superseding_decision: Callable[[Sequence[Decision]], Decision | None] | None = None,
    ) -> None:
        super().__init__("Memoria y decisiones")
        self._get_overview_use_case = get_knowledge_overview_use_case
        self._save_manual_memory_use_case = save_manual_memory_use_case
        self._get_memory_origin_use_case = get_memory_origin_use_case
        self._correct_memory_use_case = correct_memory_use_case
        self._archive_memory_use_case = archive_memory_use_case
        self._delete_memory_use_case = delete_memory_use_case
        self._propose_decision_use_case = propose_decision_use_case
        self._approve_decision_use_case = approve_decision_use_case
        self._get_decision_origin_use_case = get_decision_origin_use_case
        self._supersede_decision_use_case = supersede_decision_use_case
        self._archive_decision_use_case = archive_decision_use_case
        self._detect_precedence_conflicts_use_case = detect_precedence_conflicts_use_case
        self._project_continuity_use_case = project_continuity_use_case

        self._show_warning = show_warning or self._default_show_warning
        self._show_information = show_information or self._default_show_information
        self._confirm_action = confirm_action or self._default_confirm_action
        self._prompt_line = prompt_line or self._default_prompt_line
        self._prompt_multiline = prompt_multiline or self._default_prompt_multiline
        self._confirm_delete_memory = confirm_delete_memory or self._default_confirm_delete_memory
        self._choose_superseding_decision = (
            choose_superseding_decision or self._default_choose_superseding_decision
        )

        self._is_busy = False
        self._is_externally_busy = False
        self._overview: KnowledgeOverview | None = None
        self._last_touched_list: QListWidget | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_memories_section())
        layout.addWidget(self._build_decisions_section())
        layout.addWidget(self._build_conflicts_section())

        self.refresh()

    # --- Diálogos por defecto (sustituidos en pruebas) --------------------

    def _default_show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _default_show_information(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)

    def _default_confirm_action(self, title: str, text: str) -> bool:
        answer = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _default_prompt_line(self, title: str, label: str) -> str | None:
        text, ok = QInputDialog.getText(self, title, label)
        return text if ok else None

    def _default_prompt_multiline(self, title: str, label: str) -> str | None:
        text, ok = QInputDialog.getMultiLineText(self, title, label)
        return text if ok else None

    def _default_confirm_delete_memory(self) -> SourceMessageChoice | None:
        dialog = _DeleteMemoryDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.selected_choice()

    def _default_choose_superseding_decision(
        self, candidates: Sequence[Decision]
    ) -> Decision | None:
        if not candidates:
            return None
        dialog = _ChooseSupersedingDecisionDialog(candidates, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.selected_decision()

    # --- Recuerdos ---------------------------------------------------------

    def _build_memories_section(self) -> QWidget:
        self.memories_list = QListWidget()
        self.memories_list.setAccessibleName("Recuerdos")
        self.memories_list.currentItemChanged.connect(self._handle_memories_list_selection_changed)
        # currentItemChanged no se emite al pulsar una fila que ya es
        # currentItem() (CODEX-001); itemClicked sí, así que un clic real
        # sobre la misma fila también cede la prioridad a este panel.
        self.memories_list.itemClicked.connect(self._handle_memories_list_selection_changed)

        self.save_memory_button = QPushButton("Guardar recuerdo…")
        self.save_memory_button.clicked.connect(self._handle_save_memory_clicked)
        self.correct_memory_button = QPushButton("Corregir…")
        self.correct_memory_button.clicked.connect(self._handle_correct_memory_clicked)
        self.archive_memory_button = QPushButton("Archivar")
        self.archive_memory_button.clicked.connect(self._handle_archive_memory_clicked)
        self.delete_memory_button = QPushButton("Eliminar…")
        self.delete_memory_button.clicked.connect(self._handle_delete_memory_clicked)
        self.memory_origin_button = QPushButton("Ver origen")
        self.memory_origin_button.clicked.connect(self._handle_memory_origin_clicked)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self.save_memory_button)
        buttons_row.addWidget(self.correct_memory_button)
        buttons_row.addWidget(self.archive_memory_button)
        buttons_row.addWidget(self.delete_memory_button)
        buttons_row.addWidget(self.memory_origin_button)

        group = QGroupBox("Recuerdos")
        layout = QVBoxLayout(group)
        layout.addWidget(self.memories_list)
        layout.addLayout(buttons_row)
        return group

    def _selected_memory(self) -> Memory | None:
        item = self.memories_list.currentItem()
        if item is None:
            return None
        memory = item.data(Qt.ItemDataRole.UserRole)
        return memory if isinstance(memory, Memory) else None

    def _handle_memories_list_selection_changed(
        self,
        current: QListWidgetItem | None = None,
        previous: QListWidgetItem | None = None,
    ) -> None:
        self._last_touched_list = self.memories_list
        self._refresh_action_buttons_enabled()

    def _handle_save_memory_clicked(self) -> None:
        if self._is_busy or self._is_externally_busy:
            return
        content = self._prompt_multiline("Guardar recuerdo", "Contenido del recuerdo:")
        if content is None:
            return
        try:
            self._save_manual_memory_use_case.save(content)
        except InvalidManualMemoryDataError as exc:
            self._show_warning("No se pudo guardar el recuerdo", str(exc))
            return
        except Exception as exc:
            _logger.error("No se pudo guardar el recuerdo (%s)", type(exc).__name__)
            self._show_warning("No se pudo guardar el recuerdo", _GENERIC_ERROR_TEXT)
            return
        self.refresh()

    def _handle_correct_memory_clicked(self) -> None:
        if self._is_busy or self._is_externally_busy:
            return
        memory = self._selected_memory()
        if memory is None:
            self._show_warning(_NO_SELECTION_TITLE, "Selecciona primero un recuerdo.")
            return
        content = self._prompt_multiline("Corregir recuerdo", "Nuevo contenido:")
        if content is None:
            return
        try:
            self._correct_memory_use_case.correct(memory.id, content)
        except (InvalidMemoryCorrectionDataError, MemoryNotCorrectableError) as exc:
            self._show_warning("No se pudo corregir el recuerdo", str(exc))
            return
        except Exception as exc:
            _logger.error("No se pudo corregir el recuerdo (%s)", type(exc).__name__)
            self._show_warning("No se pudo corregir el recuerdo", _GENERIC_ERROR_TEXT)
            return
        self.refresh()

    def _memory_for_resolution(self) -> Memory | None:
        """Prefer the ``conflicts_list`` entity (§4.2) only while it is the
        list the user last touched: acting on a conflict never depends on a
        stale ``memories_list`` selection, but selecting a memory in the
        general panel afterward cedes priority back to it."""
        entity = self._active_conflict_entity()
        return entity if isinstance(entity, Memory) else self._selected_memory()

    def _handle_archive_memory_clicked(self) -> None:
        if self._is_busy or self._is_externally_busy:
            return
        memory = self._memory_for_resolution()
        if memory is None:
            self._show_warning(_NO_SELECTION_TITLE, "Selecciona primero un recuerdo.")
            return
        if not self._confirm_action(
            "Archivar recuerdo",
            "El recuerdo dejará de usarse en el contexto ordinario, sin eliminar su "
            "contenido.\n\n¿Deseas continuar?",
        ):
            return
        try:
            self._archive_memory_use_case.archive(memory.id)
        except MemoryNotArchivableError as exc:
            self._show_warning("No se pudo archivar el recuerdo", str(exc))
            return
        except Exception as exc:
            _logger.error("No se pudo archivar el recuerdo (%s)", type(exc).__name__)
            self._show_warning("No se pudo archivar el recuerdo", _GENERIC_ERROR_TEXT)
            return
        self.refresh()

    def _handle_delete_memory_clicked(self) -> None:
        if self._is_busy or self._is_externally_busy:
            return
        memory = self._selected_memory()
        if memory is None:
            self._show_warning(_NO_SELECTION_TITLE, "Selecciona primero un recuerdo.")
            return
        choice = self._confirm_delete_memory()
        if choice is None:
            return
        try:
            result = self._delete_memory_use_case.delete(
                memory.id, confirmed=True, source_message_choice=choice
            )
        except (DeletionNotConfirmedError, MemoryNotDeletableError) as exc:
            self._show_warning("No se pudo eliminar el recuerdo", str(exc))
            return
        except Exception as exc:
            _logger.error("No se pudo eliminar el recuerdo (%s)", type(exc).__name__)
            self._show_warning("No se pudo eliminar el recuerdo", _GENERIC_ERROR_TEXT)
            return
        self.refresh()
        self._show_information("Recuerdo eliminado", result.old_backup_warning)

    def _handle_memory_origin_clicked(self) -> None:
        memory = self._selected_memory()
        if memory is None:
            self._show_warning(_NO_SELECTION_TITLE, "Selecciona primero un recuerdo.")
            return
        try:
            origin: MemoryOrigin = self._get_memory_origin_use_case.get_origin(memory.id)
        except LookupError as exc:
            self._show_warning("No se pudo abrir el origen", str(exc))
            return
        self._show_information(
            "Origen del recuerdo",
            f"Evento: {origin.event_type}\n"
            f"Actor: {origin.actor}\n"
            f"Fecha: {origin.created_at.isoformat()}\n"
            f"Mensaje: {origin.message_content or '(sin mensaje asociado)'}",
        )

    # --- Decisiones ----------------------------------------------------------

    def _build_decisions_section(self) -> QWidget:
        self.decisions_list = QListWidget()
        self.decisions_list.setAccessibleName("Decisiones")
        self.decisions_list.currentItemChanged.connect(
            self._handle_decisions_list_selection_changed
        )
        # Ver comentario equivalente en _build_memories_section (CODEX-001).
        self.decisions_list.itemClicked.connect(self._handle_decisions_list_selection_changed)

        self.propose_decision_button = QPushButton("Proponer decisión…")
        self.propose_decision_button.clicked.connect(self._handle_propose_decision_clicked)
        self.approve_decision_button = QPushButton("Aprobar")
        self.approve_decision_button.clicked.connect(self._handle_approve_decision_clicked)
        self.supersede_decision_button = QPushButton("Sustituir…")
        self.supersede_decision_button.clicked.connect(self._handle_supersede_decision_clicked)
        self.archive_decision_button = QPushButton("Archivar")
        self.archive_decision_button.clicked.connect(self._handle_archive_decision_clicked)
        self.decision_origin_button = QPushButton("Ver origen")
        self.decision_origin_button.clicked.connect(self._handle_decision_origin_clicked)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self.propose_decision_button)
        buttons_row.addWidget(self.approve_decision_button)
        buttons_row.addWidget(self.supersede_decision_button)
        buttons_row.addWidget(self.archive_decision_button)
        buttons_row.addWidget(self.decision_origin_button)

        group = QGroupBox("Decisiones")
        layout = QVBoxLayout(group)
        layout.addWidget(self.decisions_list)
        layout.addLayout(buttons_row)
        return group

    def _selected_decision(self) -> Decision | None:
        item = self.decisions_list.currentItem()
        if item is None:
            return None
        decision = item.data(Qt.ItemDataRole.UserRole)
        return decision if isinstance(decision, Decision) else None

    def _handle_decisions_list_selection_changed(
        self,
        current: QListWidgetItem | None = None,
        previous: QListWidgetItem | None = None,
    ) -> None:
        self._last_touched_list = self.decisions_list
        self._refresh_action_buttons_enabled()

    def _active_project_id(self) -> int | None:
        try:
            return self._project_continuity_use_case.get_summary().project_id
        except ProjectNotConfiguredError:
            return None

    def _handle_propose_decision_clicked(self) -> None:
        if self._is_busy or self._is_externally_busy:
            return
        project_id = self._active_project_id()
        if project_id is None:
            self._show_warning("No se pudo proponer la decisión", _NO_PROJECT_WARNING)
            return
        subject = self._prompt_line("Proponer decisión", "Asunto:")
        if subject is None:
            return
        content = self._prompt_multiline("Proponer decisión", "Contenido:")
        if content is None:
            return
        try:
            self._propose_decision_use_case.propose(subject, project_id, content)
        except InvalidDecisionProposalDataError as exc:
            self._show_warning("No se pudo proponer la decisión", str(exc))
            return
        except Exception as exc:
            _logger.error("No se pudo proponer la decisión (%s)", type(exc).__name__)
            self._show_warning("No se pudo proponer la decisión", _GENERIC_ERROR_TEXT)
            return
        self.refresh()

    def _handle_approve_decision_clicked(self) -> None:
        if self._is_busy or self._is_externally_busy:
            return
        decision = self._selected_decision()
        if decision is None:
            self._show_warning(_NO_SELECTION_TITLE, "Selecciona primero una decisión.")
            return
        if not self._confirm_action(
            "Aprobar decisión",
            f"La decisión «{decision.subject}» pasará a estar vigente.\n\n¿Deseas continuar?",
        ):
            return
        try:
            self._approve_decision_use_case.approve(decision.id, confirmed=True)
        except (ApprovalNotConfirmedError, InvalidDecisionStatusError) as exc:
            self._show_warning("No se pudo aprobar la decisión", str(exc))
            return
        except Exception as exc:
            _logger.error("No se pudo aprobar la decisión (%s)", type(exc).__name__)
            self._show_warning("No se pudo aprobar la decisión", _GENERIC_ERROR_TEXT)
            return
        self.refresh()

    def _decision_for_resolution(self) -> Decision | None:
        """Prefer the ``conflicts_list`` entity (§4.2) only while it is the
        list the user last touched: acting on a conflict never depends on a
        stale ``decisions_list`` selection, but selecting a decision in the
        general panel afterward cedes priority back to it."""
        entity = self._active_conflict_entity()
        return entity if isinstance(entity, Decision) else self._selected_decision()

    def _handle_supersede_decision_clicked(self) -> None:
        if self._is_busy or self._is_externally_busy:
            return
        superseded = self._decision_for_resolution()
        if superseded is None:
            self._show_warning(
                _NO_SELECTION_TITLE, "Selecciona primero la decisión vigente a sustituir."
            )
            return
        if self._overview is None:
            return
        # Las candidatas incluyen las decisiones ya APROBADAS del mismo asunto,
        # no solo las propuestas: antes solo se ofrecían las propuestas, así que
        # si el usuario ya había aprobado la decisión nueva no aparecía ninguna
        # candidata y las dos se quedaban vigentes con el mismo peso.
        candidates = [
            decision
            for decision in (*self._overview.proposed_decisions, *self._overview.current_decisions)
            if decision.id != superseded.id and is_same_subject_and_project(decision, superseded)
        ]
        superseding = self._choose_superseding_decision(candidates)
        if superseding is None:
            if not candidates:
                self._show_warning(
                    "No se pudo sustituir la decisión",
                    "No hay ninguna otra decisión con el mismo asunto y proyecto.",
                )
            return
        if not self._confirm_action(
            "Sustituir decisión",
            f"«{superseding.subject}» sustituirá a la decisión vigente actual.\n\n"
            "¿Deseas continuar?",
        ):
            return
        try:
            self._supersede_decision_use_case.supersede(
                superseded.id, superseding.id, confirmed=True
            )
        except (
            DecisionSupersessionNotConfirmedError,
            InvalidDecisionSupersessionError,
        ) as exc:
            self._show_warning("No se pudo sustituir la decisión", str(exc))
            return
        except Exception as exc:
            _logger.error("No se pudo sustituir la decisión (%s)", type(exc).__name__)
            self._show_warning("No se pudo sustituir la decisión", _GENERIC_ERROR_TEXT)
            return
        self.refresh()

    def _handle_archive_decision_clicked(self) -> None:
        if self._is_busy or self._is_externally_busy:
            return
        decision = self._decision_for_resolution()
        if decision is None:
            self._show_warning(_NO_SELECTION_TITLE, "Selecciona primero una decisión.")
            return
        if not self._confirm_action(
            "Archivar decisión",
            "La decisión dejará de usarse en el contexto ordinario, sin eliminar su "
            "contenido.\n\n¿Deseas continuar?",
        ):
            return
        try:
            self._archive_decision_use_case.archive(decision.id)
        except DecisionNotArchivableError as exc:
            self._show_warning("No se pudo archivar la decisión", str(exc))
            return
        except Exception as exc:
            _logger.error("No se pudo archivar la decisión (%s)", type(exc).__name__)
            self._show_warning("No se pudo archivar la decisión", _GENERIC_ERROR_TEXT)
            return
        self.refresh()

    def _handle_decision_origin_clicked(self) -> None:
        decision = self._selected_decision()
        if decision is None:
            self._show_warning(_NO_SELECTION_TITLE, "Selecciona primero una decisión.")
            return
        try:
            origin: DecisionOrigin = self._get_decision_origin_use_case.get_origin(decision.id)
        except LookupError as exc:
            self._show_warning("No se pudo abrir el origen", str(exc))
            return
        self._show_information(
            "Origen de la decisión",
            f"Evento: {origin.event_type}\n"
            f"Actor: {origin.actor}\n"
            f"Fecha: {origin.event_created_at.isoformat()}\n"
            f"Mensaje: {origin.message_content or '(sin mensaje asociado)'}",
        )

    # --- Conflictos de precedencia -------------------------------------------

    def _build_conflicts_section(self) -> QWidget:
        self.detect_conflicts_button = QPushButton("Detectar conflictos de precedencia")
        self.detect_conflicts_button.clicked.connect(self._handle_detect_conflicts_clicked)

        self.conflicts_list = QListWidget()
        self.conflicts_list.setAccessibleName("Conflictos de precedencia")
        self.conflicts_list.currentItemChanged.connect(self._handle_conflict_selection_changed)
        # Ver comentario equivalente en _build_memories_section (CODEX-001).
        self.conflicts_list.itemClicked.connect(self._handle_conflict_selection_changed)

        self.conflicts_status_label = QLabel("")
        self.conflicts_status_label.setWordWrap(True)

        group = QGroupBox("Conflictos de precedencia")
        layout = QVBoxLayout(group)
        layout.addWidget(self.detect_conflicts_button)
        layout.addWidget(self.conflicts_list)
        layout.addWidget(self.conflicts_status_label)
        return group

    def _selected_conflict_entity(self) -> Memory | Decision | None:
        item = self.conflicts_list.currentItem()
        if item is None:
            return None
        entity = item.data(Qt.ItemDataRole.UserRole)
        return entity if isinstance(entity, Memory | Decision) else None

    def _handle_conflict_selection_changed(
        self,
        current: QListWidgetItem | None = None,
        previous: QListWidgetItem | None = None,
    ) -> None:
        self._last_touched_list = self.conflicts_list
        self._refresh_action_buttons_enabled()

    def _active_conflict_entity(self) -> Memory | Decision | None:
        """The conflict member the user is currently resolving: only while
        ``conflicts_list`` is the list most recently touched (§4.2). Selecting
        something in ``memories_list``/``decisions_list`` afterward cedes
        priority back to that general panel, exactly like
        ``_handle_correct_memory_clicked``/``_handle_approve_decision_clicked``
        already do outside this flow."""
        if self._last_touched_list is not self.conflicts_list:
            return None
        return self._selected_conflict_entity()

    def _refresh_action_buttons_enabled(self) -> None:
        if self._is_busy or self._is_externally_busy:
            return
        # Solo las acciones que de verdad resuelven el conflicto quedan
        # habilitadas desde aquí (§4.2): corregir conserva subject_key/
        # project_id (el conflicto reaparecería) y toda decisión en conflicto
        # ya está APPROVED (aprobarla de nuevo siempre falla); simétricamente,
        # archivar un recuerdo no resuelve un conflicto de decisiones ni
        # sustituir/archivar una decisión resuelve uno de recuerdos.
        entity = self._active_conflict_entity()
        self.correct_memory_button.setEnabled(not isinstance(entity, Memory))
        self.approve_decision_button.setEnabled(not isinstance(entity, Decision))
        self.archive_memory_button.setEnabled(not isinstance(entity, Decision))
        self.supersede_decision_button.setEnabled(not isinstance(entity, Memory))
        self.archive_decision_button.setEnabled(not isinstance(entity, Memory))

    def _handle_detect_conflicts_clicked(self) -> None:
        try:
            conflicts = self._detect_precedence_conflicts_use_case.detect()
        except Exception as exc:
            _logger.error("No se pudieron detectar conflictos (%s)", type(exc).__name__)
            self.conflicts_status_label.setText(_GENERIC_ERROR_TEXT)
            return

        self.conflicts_list.blockSignals(True)
        try:
            self.conflicts_list.clear()
            if conflicts:
                self.conflicts_status_label.setText(
                    "Sirius no elige entre estos elementos: requieren aclaración explícita."
                )
                for conflict in conflicts:
                    assert conflict.outcome is PrecedenceOutcome.CONFLICT
                    header = QListWidgetItem(
                        f"Asunto «{conflict.subject_key}» (proyecto {conflict.project_id})"
                    )
                    header.setFlags(header.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                    self.conflicts_list.addItem(header)
                    for memory in conflict.conflicting_memories:
                        item = QListWidgetItem(_memory_label(memory))
                        item.setData(Qt.ItemDataRole.UserRole, memory)
                        self.conflicts_list.addItem(item)
                    for decision in conflict.conflicting_decisions:
                        item = QListWidgetItem(_decision_label(decision))
                        item.setData(Qt.ItemDataRole.UserRole, decision)
                        self.conflicts_list.addItem(item)
        finally:
            self.conflicts_list.blockSignals(False)

        if not conflicts:
            self.conflicts_status_label.setText("No hay conflictos de precedencia pendientes.")
        # Detectar de nuevo nunca deja seleccionado un ítem del conflicto
        # (blockSignals evita que clear()/addItem() disparen
        # currentItemChanged), así que la prioridad de conflicts_list no
        # sobrevive artificialmente a una redetección.
        if self._last_touched_list is self.conflicts_list:
            self._last_touched_list = None
        self._refresh_action_buttons_enabled()

    # --- Actualización y coordinación de estado ocupado ----------------------

    def refresh(self) -> None:
        """Reload every list from ``GetKnowledgeOverviewUseCase`` (read-only)."""
        try:
            overview = self._get_overview_use_case.get_overview()
        except Exception as exc:
            _logger.error("No se pudo cargar la memoria y decisiones (%s)", type(exc).__name__)
            self._overview = None
            return

        self._overview = overview

        # Signals blocked while repopulating: clear()/addItem() must never be
        # mistaken for the user touching this list, or a refresh triggered by
        # an unrelated action (e.g. resolving a conflict) would silently
        # reassign _last_touched_list and its resolution priority (§4.2).
        self.memories_list.blockSignals(True)
        try:
            self.memories_list.clear()
            for memory in (*overview.current_memories, *overview.archived_memories):
                item = QListWidgetItem(_memory_label(memory))
                item.setData(Qt.ItemDataRole.UserRole, memory)
                self.memories_list.addItem(item)
        finally:
            self.memories_list.blockSignals(False)

        self.decisions_list.blockSignals(True)
        try:
            self.decisions_list.clear()
            for decision in (
                *overview.proposed_decisions,
                *overview.current_decisions,
                *overview.archived_decisions,
            ):
                item = QListWidgetItem(_decision_label(decision))
                item.setData(Qt.ItemDataRole.UserRole, decision)
                self.decisions_list.addItem(item)
        finally:
            self.decisions_list.blockSignals(False)

    def set_external_busy(self, is_busy: bool) -> None:
        """Coordinate with a ``MainWindow``-level operation this widget does
        not own (sending a message, or a backup/restore in flight): mirrors
        ``ProjectContinuityWidget.set_external_busy``.
        """
        self._is_externally_busy = is_busy
        self._set_controls_enabled(not is_busy and not self._is_busy)

    def _set_controls_enabled(self, enabled: bool) -> None:
        for button in (
            self.save_memory_button,
            self.delete_memory_button,
            self.memory_origin_button,
            self.propose_decision_button,
            self.decision_origin_button,
            self.detect_conflicts_button,
        ):
            button.setEnabled(enabled)
        # Los cinco botones de resolución no se fijan aquí a ciegas: mientras
        # ocupado quedan forzados a False (ninguna selección posterior en
        # conflicts_list debe reactivarlos, CODEX-003); al dejar de estarlo,
        # _refresh_action_buttons_enabled vuelve a aplicar la restricción por
        # tipo de miembro en conflicto (§4.2) en vez de reactivarlos todos.
        if enabled:
            self._refresh_action_buttons_enabled()
        else:
            for button in (
                self.correct_memory_button,
                self.approve_decision_button,
                self.archive_memory_button,
                self.supersede_decision_button,
                self.archive_decision_button,
            ):
                button.setEnabled(False)


__all__ = ["KnowledgeWidget"]
