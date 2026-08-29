"""GUI tests for the M2 read-only historical projects view (§5.4/§8-M2).

Mirrors ``test_project_continuity_widget.py``: every widget here wraps a real
``HistoricalProjectsUseCase`` (and, where the active project is involved,
``ProjectContinuityUseCase``) around an in-memory fake ``ProjectRepository`` —
no SQLite involved. The fake raises on every repository method the widget
under test must never call, so an unwanted write or an unwanted read of the
active project surfaces as a test failure, not a silent pass.
"""

from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from sirius.application.historical_projects import HistoricalProjectsUseCase
from sirius.application.project_continuity import ProjectContinuityUseCase
from sirius.application.project_lifecycle import ProjectLifecycleUseCase
from sirius.domain.project import Project, ProjectRevision, ProjectStatus
from sirius.presentation.historical_projects_widget import (
    NO_COMPLETED_PROJECTS_TEXT,
    NO_REVISIONS_TEXT,
    HistoricalProjectsWidget,
)
from sirius.presentation.project_continuity_widget import ProjectContinuityWidget


class _FakeProjectRepository:
    """Backs both widgets under test with a single ACTIVE project plus a
    fixed set of COMPLETED projects, each with its own revision history.

    Every method a read-only historical view must never call raises
    ``AssertionError`` — same pattern as
    ``test_project_continuity_widget.py``'s fake.
    """

    def __init__(
        self,
        active_project: Project | None,
        completed_projects: tuple[Project, ...] = (),
        revisions_by_project_id: dict[int, tuple[ProjectRevision, ...]] | None = None,
    ) -> None:
        self._active_project = active_project
        self._completed_projects = completed_projects
        self._revisions_by_project_id = revisions_by_project_id or {}

    def get_active_project(self) -> Project | None:
        return self._active_project

    def ensure_bootstrap_project(self) -> None:
        raise AssertionError("must never be called from these widgets")

    def get_project(self, project_id: int) -> Project | None:
        raise AssertionError("must never be called from these widgets")

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        if project_id not in self._revisions_by_project_id:
            msg = f"Unknown project id: {project_id}"
            raise ValueError(msg)
        return self._revisions_by_project_id[project_id]

    def create_project(
        self,
        name: str,
        objective: str,
        *,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
    ) -> Project:
        raise AssertionError("must never be called from these widgets")

    def append_revision(
        self,
        project_id: int,
        *,
        objective: str,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
        source_event_id: int | None = None,
    ) -> Project:
        raise AssertionError("must never be called from these widgets")

    def complete_active_project(self, project_id: int) -> Project:
        raise AssertionError("must never be called from these widgets")

    def list_completed_projects(self) -> tuple[Project, ...]:
        return self._completed_projects


def _project(
    project_id: int,
    *,
    name: str,
    status: ProjectStatus,
    objective: str = "Objetivo",
    completed_at: datetime | None = None,
) -> Project:
    now = datetime.now(UTC)
    revision = ProjectRevision(
        id=project_id * 10,
        project_id=project_id,
        version=1,
        objective=objective,
        state_summary="en curso",
        blockers=(),
        next_step="siguiente paso",
        source_event_id=None,
        created_at=now,
    )
    return Project(
        id=project_id,
        name=name,
        status=status,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        completed_at=completed_at,
    )


def _revision(
    project_id: int,
    *,
    version: int,
    objective: str,
    state_summary: str,
    blockers: tuple[str, ...],
    next_step: str,
) -> ProjectRevision:
    return ProjectRevision(
        id=project_id * 100 + version,
        project_id=project_id,
        version=version,
        objective=objective,
        state_summary=state_summary,
        blockers=blockers,
        next_step=next_step,
        source_event_id=None,
        created_at=datetime.now(UTC),
    )


def _build_widget(repository: _FakeProjectRepository) -> HistoricalProjectsWidget:
    return HistoricalProjectsWidget(HistoricalProjectsUseCase(repository))


def test_lists_no_completed_projects_when_none_exist(qtbot: QtBot) -> None:
    widget = _build_widget(_FakeProjectRepository(active_project=None))
    qtbot.addWidget(widget)

    assert widget.projects_list.count() == 1
    assert widget.projects_list.item(0).text() == NO_COMPLETED_PROJECTS_TEXT


def test_lists_completed_project_by_name_and_closing_date(qtbot: QtBot) -> None:
    closed_at = datetime(2026, 3, 1, tzinfo=UTC)
    completed = _project(
        2, name="Proyecto cerrado", status=ProjectStatus.COMPLETED, completed_at=closed_at
    )
    repository = _FakeProjectRepository(active_project=None, completed_projects=(completed,))
    widget = _build_widget(repository)
    qtbot.addWidget(widget)

    assert widget.projects_list.count() == 1
    item = widget.projects_list.item(0)
    assert "Proyecto cerrado" in item.text()
    assert closed_at.isoformat() in item.text()
    assert item.data(Qt.ItemDataRole.UserRole) == completed


def test_selecting_a_completed_project_shows_its_revision_history(qtbot: QtBot) -> None:
    completed = _project(3, name="Proyecto cerrado", status=ProjectStatus.COMPLETED)
    revisions = (
        _revision(
            3,
            version=1,
            objective="Objetivo inicial",
            state_summary="arrancando",
            blockers=(),
            next_step="primer paso",
        ),
        _revision(
            3,
            version=2,
            objective="Objetivo final",
            state_summary="cerrado",
            blockers=("bloqueo x",),
            next_step="ninguno",
        ),
    )
    repository = _FakeProjectRepository(
        active_project=None,
        completed_projects=(completed,),
        revisions_by_project_id={3: revisions},
    )
    widget = _build_widget(repository)
    qtbot.addWidget(widget)

    assert widget.revisions_list.count() == 1
    assert widget.revisions_list.item(0).text() == NO_REVISIONS_TEXT

    widget.projects_list.setCurrentRow(0)

    assert widget.revisions_list.count() == 2
    first_text = widget.revisions_list.item(0).text()
    second_text = widget.revisions_list.item(1).text()
    assert "v1" in first_text
    assert "Objetivo inicial" in first_text
    assert "arrancando" in first_text
    assert "primer paso" in first_text
    assert "v2" in second_text
    assert "Objetivo final" in second_text
    assert "bloqueo x" in second_text


def test_widget_offers_no_edit_continuity_or_reactivation_control(qtbot: QtBot) -> None:
    completed = _project(4, name="Proyecto cerrado", status=ProjectStatus.COMPLETED)
    repository = _FakeProjectRepository(active_project=None, completed_projects=(completed,))
    widget = _build_widget(repository)
    qtbot.addWidget(widget)

    assert widget.findChildren(QPushButton) == []


def test_consulting_history_never_changes_the_active_project_view(qtbot: QtBot) -> None:
    """§8-M2's literal acceptance criterion: with an active configured
    project and at least one completed project, selecting the completed
    project in the historical view must never change what
    ``ProjectContinuityWidget`` shows for the active one.
    """
    active = _project(1, name="Proyecto activo", status=ProjectStatus.ACTIVE)
    completed = _project(2, name="Proyecto cerrado", status=ProjectStatus.COMPLETED)
    revisions = (
        _revision(
            2,
            version=1,
            objective="Objetivo cerrado",
            state_summary="cerrado",
            blockers=(),
            next_step="ninguno",
        ),
    )
    repository = _FakeProjectRepository(
        active_project=active,
        completed_projects=(completed,),
        revisions_by_project_id={2: revisions},
    )

    continuity_widget = ProjectContinuityWidget(
        ProjectContinuityUseCase(repository),
        ProjectLifecycleUseCase(repository),
    )
    qtbot.addWidget(continuity_widget)
    historical_widget = _build_widget(repository)
    qtbot.addWidget(historical_widget)

    before = (
        continuity_widget.name_label.text(),
        continuity_widget.objective_label.text(),
        continuity_widget.current_state_label.text(),
        continuity_widget.blockers_label.text(),
        continuity_widget.next_step_label.text(),
    )

    historical_widget.projects_list.setCurrentRow(0)
    assert historical_widget.revisions_list.count() == 1

    after = (
        continuity_widget.name_label.text(),
        continuity_widget.objective_label.text(),
        continuity_widget.current_state_label.text(),
        continuity_widget.blockers_label.text(),
        continuity_widget.next_step_label.text(),
    )
    assert before == after
    assert continuity_widget.name_label.text() == "Proyecto activo"
