"""Read-only historical projects view (M2, §5.4).

Deliberately distinct from ``ProjectContinuityWidget``
(``src/sirius/presentation/project_continuity_widget.py``), which keeps
showing the single ``ACTIVE`` project exclusively. This widget only ever
lists ``COMPLETED`` projects and their conserved revision history, through
``HistoricalProjectsUseCase`` (``src/sirius/application/historical_projects.py``)
— never ``ProjectRepository``, SQLAlchemy, or SQLite directly (AGENTS.md:
dependency direction presentación -> aplicación -> dominio).

Carries no edit, continuity, or reactivation control of any kind: both
methods on ``HistoricalProjectsUseCase`` are read-only, and this widget is
mounted by ``MainWindow`` in a tab of its own, separate from the one hosting
``ProjectContinuityWidget``, so consulting a closed project's history can
never share screen space with — let alone modify or contaminate — the live
project.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from sirius.application.historical_projects import HistoricalProjectsUseCase
from sirius.domain.project import Project, ProjectRevision

NO_COMPLETED_PROJECTS_TEXT = "No hay proyectos completados todavía."
NO_REVISIONS_TEXT = "Selecciona un proyecto completado para ver su historial."

__all__ = ["NO_COMPLETED_PROJECTS_TEXT", "NO_REVISIONS_TEXT", "HistoricalProjectsWidget"]


def _project_label(project: Project) -> str:
    closed = project.completed_at.isoformat() if project.completed_at is not None else "—"
    return f"{project.name} — cerrado el {closed}"


def _revision_label(revision: ProjectRevision) -> str:
    blockers = "; ".join(revision.blockers) if revision.blockers else "Sin bloqueos registrados."
    return (
        f"v{revision.version} — objetivo: {revision.objective} | "
        f"estado: {revision.state_summary} | bloqueos: {blockers} | "
        f"siguiente paso: {revision.next_step}"
    )


class HistoricalProjectsWidget(QGroupBox):
    """Lista de proyectos completados y, al seleccionar uno, su historial.

    Consultar aquí nunca modifica ni contamina el proyecto activo: ninguna
    de las dos llamadas a ``HistoricalProjectsUseCase`` escribe, y esta
    superficie no comparte ningún widget ni estado con la vista del proyecto
    vivo.
    """

    def __init__(self, historical_projects_use_case: HistoricalProjectsUseCase) -> None:
        super().__init__("Proyectos históricos")
        self._use_case = historical_projects_use_case

        self.projects_list = QListWidget()
        self.projects_list.setAccessibleName("Proyectos completados")
        self.projects_list.itemSelectionChanged.connect(self._handle_project_selected)

        self.revisions_list = QListWidget()
        self.revisions_list.setAccessibleName("Historial de revisiones")

        projects_column = QWidget()
        projects_layout = QVBoxLayout(projects_column)
        projects_layout.setContentsMargins(0, 0, 0, 0)
        projects_layout.addWidget(QLabel("Proyectos completados:"))
        projects_layout.addWidget(self.projects_list)

        revisions_column = QWidget()
        revisions_layout = QVBoxLayout(revisions_column)
        revisions_layout.setContentsMargins(0, 0, 0, 0)
        revisions_layout.addWidget(QLabel("Historial de revisiones:"))
        revisions_layout.addWidget(self.revisions_list)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(projects_column)
        splitter.addWidget(revisions_column)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self.refresh()
        self._handle_project_selected()

    def refresh(self) -> None:
        """Reload the list of completed projects (local, deterministic, no network).

        Never touches ``revisions_list``: a caller who refreshes while a
        project is selected keeps seeing its history until it selects again,
        exactly as ``projects_list.itemSelectionChanged`` re-populates it.
        """
        self.projects_list.clear()
        projects = self._use_case.list_completed()
        if not projects:
            self.projects_list.addItem(NO_COMPLETED_PROJECTS_TEXT)
            return
        for project in projects:
            item = QListWidgetItem(_project_label(project))
            item.setData(Qt.ItemDataRole.UserRole, project)
            self.projects_list.addItem(item)

    def _selected_project(self) -> Project | None:
        item = self.projects_list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, Project) else None

    def _handle_project_selected(self) -> None:
        self.revisions_list.clear()
        project = self._selected_project()
        if project is None:
            self.revisions_list.addItem(NO_REVISIONS_TEXT)
            return
        revisions = self._use_case.get_revision_history(project.id)
        if not revisions:
            self.revisions_list.addItem(NO_REVISIONS_TEXT)
            return
        for revision in revisions:
            self.revisions_list.addItem(QListWidgetItem(_revision_label(revision)))
