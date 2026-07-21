"""Panel de contexto completo (B5, SIRIUS-B5-001).

Superficie de contexto *de solo lectura* insertada por ``MainWindow`` en la
pestaña "Conversación", debajo del bloque de continuidad del proyecto
(``ProjectContinuityWidget``) y encima del historial. Su función es que el
contexto vigente del proyecto activo sea consultable sin salir de la
conversación ni reconstruirlo a mano: un ancla del proyecto activo (nombre y
siguiente paso) junto con las decisiones y los recuerdos vigentes, cada uno
con su origen abrible.

No es una pestaña ni una ventana nueva, no es una aplicación de gestión y
nunca modifica memoria, decisiones ni proyecto: toda edición sigue viviendo en
sus superficies existentes (``ProjectContinuityWidget`` para el proyecto y la
pestaña "Memoria y decisiones" para recuerdos y decisiones). Este panel solo
lee y muestra.

Todo lo que muestra se obtiene de forma local y determinista de los casos de
uso ya existentes (``ProjectContinuityUseCase``, ``GetKnowledgeOverviewUseCase``,
``GetMemoryOriginUseCase``, ``GetDecisionOriginUseCase``): nunca lo genera el
proveedor, nunca se persiste como mensaje y nunca provoca una llamada de red.
Como el resto de la presentación, no toca ``MemoryRepository``,
``DecisionRepository``, ``ProjectRepository``, SQLAlchemy ni SQLite directamente
(AGENTS.md: dirección de dependencias presentación -> aplicación -> dominio).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from sirius.application.decision_origin import DecisionOrigin, GetDecisionOriginUseCase
from sirius.application.knowledge_overview import GetKnowledgeOverviewUseCase
from sirius.application.memory_origin import GetMemoryOriginUseCase, MemoryOrigin
from sirius.application.project_continuity import (
    ProjectContinuityError,
    ProjectContinuityUseCase,
    ProjectNotConfiguredError,
)
from sirius.domain.decision import Decision
from sirius.domain.memory import Memory
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)

NO_PROJECT_TEXT = "Todavía no hay un proyecto configurado."
NO_DECISIONS_TEXT = "Sin decisiones vigentes."
NO_MEMORIES_TEXT = "Sin recuerdos vigentes."
_NO_SELECTION_TITLE = "Nada seleccionado"
_CONTEXT_UNAVAILABLE_TEXT = "No se pudo cargar el contexto vigente. Inténtalo de nuevo."

__all__ = ["NO_DECISIONS_TEXT", "NO_MEMORIES_TEXT", "NO_PROJECT_TEXT", "ContextPanelWidget"]


def _short(content: str | None, limit: int = 80) -> str:
    if content is None:
        return "(contenido eliminado)"
    text = content.strip().replace("\n", " ")
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _memory_label(memory: Memory) -> str:
    subject = f" [{memory.subject_key}]" if memory.subject_key is not None else ""
    return f"#{memory.id}{subject} — {_short(memory.current_revision.content)}"


def _decision_label(decision: Decision) -> str:
    return f"#{decision.id} — {decision.subject}: {_short(decision.current_revision.content)}"


class ContextPanelWidget(QGroupBox):
    """Panel de solo lectura con el contexto vigente del proyecto activo.

    Reúne, en la pestaña "Conversación", el ancla del proyecto activo con las
    decisiones y los recuerdos vigentes y su origen. Nunca escribe: es la
    contrapartida consultable de las superficies de edición ya existentes.

    ``set_external_busy()`` refleja el mismo patrón que
    ``ProjectContinuityWidget``/``KnowledgeWidget``: cuando ``MainWindow`` está
    ocupada con una operación que este panel no controla (enviar/transmitir un
    mensaje, o una copia/restauración en curso), sus controles se deshabilitan;
    al terminar, se restauran. No hay estado de escritura propio que proteger,
    porque el panel no escribe nada.
    """

    def __init__(
        self,
        project_continuity_use_case: ProjectContinuityUseCase,
        get_knowledge_overview_use_case: GetKnowledgeOverviewUseCase,
        get_memory_origin_use_case: GetMemoryOriginUseCase,
        get_decision_origin_use_case: GetDecisionOriginUseCase,
        *,
        show_warning: Callable[[str, str], None] | None = None,
        show_information: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__("Contexto vigente")
        self._project_continuity_use_case = project_continuity_use_case
        self._get_knowledge_overview_use_case = get_knowledge_overview_use_case
        self._get_memory_origin_use_case = get_memory_origin_use_case
        self._get_decision_origin_use_case = get_decision_origin_use_case
        self._show_warning = show_warning or self._default_show_warning
        self._show_information = show_information or self._default_show_information

        self.project_anchor_label = QLabel("")
        self.project_anchor_label.setWordWrap(True)

        self.decisions_list = QListWidget()
        self.decisions_list.setAccessibleName("Decisiones vigentes")
        self.decision_origin_button = QPushButton("Ver origen de la decisión")
        self.decision_origin_button.clicked.connect(self._handle_decision_origin_clicked)

        self.memories_list = QListWidget()
        self.memories_list.setAccessibleName("Recuerdos vigentes")
        self.memory_origin_button = QPushButton("Ver origen del recuerdo")
        self.memory_origin_button.clicked.connect(self._handle_memory_origin_clicked)

        self.refresh_button = QPushButton("Actualizar contexto")
        self.refresh_button.clicked.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.addWidget(self.project_anchor_label)

        layout.addWidget(QLabel("Decisiones vigentes:"))
        layout.addWidget(self.decisions_list)
        decision_row = QHBoxLayout()
        decision_row.addWidget(self.decision_origin_button)
        layout.addLayout(decision_row)

        layout.addWidget(QLabel("Recuerdos vigentes:"))
        layout.addWidget(self.memories_list)
        memory_row = QHBoxLayout()
        memory_row.addWidget(self.memory_origin_button)
        layout.addLayout(memory_row)

        layout.addWidget(self.refresh_button)

        self.refresh()

    def _default_show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _default_show_information(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)

    def refresh(self) -> None:
        """Recargar el contexto vigente (local, determinista, sin red).

        Seguro ante un proyecto ausente o no configurado y ante un fallo de
        lectura: nunca lanza, cae a un estado vacío legible en su lugar.
        """
        self._render_project_anchor()
        self._render_knowledge()

    def _render_project_anchor(self) -> None:
        try:
            summary = self._project_continuity_use_case.get_summary()
        except ProjectNotConfiguredError:
            self.project_anchor_label.setText(NO_PROJECT_TEXT)
            return
        except ProjectContinuityError as exc:
            _logger.error("No se pudo cargar el proyecto del contexto (%s)", type(exc).__name__)
            self.project_anchor_label.setText(NO_PROJECT_TEXT)
            return
        self.project_anchor_label.setText(
            f"Proyecto: {summary.name} — Ahora toca: {summary.next_step}"
        )

    def _render_knowledge(self) -> None:
        self.decisions_list.clear()
        self.memories_list.clear()
        try:
            overview = self._get_knowledge_overview_use_case.get_overview()
        except Exception as exc:
            _logger.error("No se pudo cargar el contexto vigente (%s)", type(exc).__name__)
            self.decisions_list.addItem(_CONTEXT_UNAVAILABLE_TEXT)
            self.memories_list.addItem(_CONTEXT_UNAVAILABLE_TEXT)
            return

        if overview.current_decisions:
            for decision in overview.current_decisions:
                item = QListWidgetItem(_decision_label(decision))
                item.setData(Qt.ItemDataRole.UserRole, decision)
                self.decisions_list.addItem(item)
        else:
            self.decisions_list.addItem(NO_DECISIONS_TEXT)

        if overview.current_memories:
            for memory in overview.current_memories:
                item = QListWidgetItem(_memory_label(memory))
                item.setData(Qt.ItemDataRole.UserRole, memory)
                self.memories_list.addItem(item)
        else:
            self.memories_list.addItem(NO_MEMORIES_TEXT)

    def _selected_decision(self) -> Decision | None:
        item = self.decisions_list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, Decision) else None

    def _selected_memory(self) -> Memory | None:
        item = self.memories_list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, Memory) else None

    def _handle_decision_origin_clicked(self) -> None:
        decision = self._selected_decision()
        if decision is None:
            self._show_warning(_NO_SELECTION_TITLE, "Selecciona primero una decisión vigente.")
            return
        try:
            origin: DecisionOrigin = self._get_decision_origin_use_case.get_origin(decision.id)
        except LookupError as exc:
            self._show_warning("No se pudo abrir el origen", str(exc))
            return
        self._show_information(
            "Origen de la decisión",
            f"Asunto: {origin.subject}\n"
            f"Estado: {origin.status.value}\n"
            f"Versión: {origin.version}\n"
            f"Evento: {origin.event_type}\n"
            f"Actor: {origin.actor}\n"
            f"Fecha: {origin.event_created_at.isoformat()}\n"
            f"Mensaje: {origin.message_content or '(sin mensaje asociado)'}",
        )

    def _handle_memory_origin_clicked(self) -> None:
        memory = self._selected_memory()
        if memory is None:
            self._show_warning(_NO_SELECTION_TITLE, "Selecciona primero un recuerdo vigente.")
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

    def set_external_busy(self, is_busy: bool) -> None:
        """Coordinar con una operación de ``MainWindow`` que este panel no
        controla (enviar/transmitir un mensaje, o una copia/restauración en
        curso): refleja ``ProjectContinuityWidget.set_external_busy``.

        El panel es de solo lectura, así que no tiene escritura propia que
        proteger; simplemente deshabilita sus controles mientras la operación
        externa está en curso y los restaura al terminar.
        """
        enabled = not is_busy
        self.decision_origin_button.setEnabled(enabled)
        self.memory_origin_button.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)
