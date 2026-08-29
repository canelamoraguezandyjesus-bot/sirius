"""GUI tests for the B3a/B3c first-project screen (RF-014/015/016, D-02).

No test ever touches the real Windows Credential Manager, SQLite, or the LLM
provider: every window here wraps a real ``InitialProjectUseCase`` around an
in-memory fake ``ProjectRepository`` — the same pattern used across this repo
(e.g. ``ValidateAndSaveApiKeyUseCase`` wrapping a recording ``CredentialValidator``
double) — so no test needs a duck-typed stand-in for the use case itself.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from sirius.application.initial_project import InitialProjectUseCase
from sirius.domain.identity import INITIAL_IDENTITY_NAME
from sirius.domain.project import Project, ProjectRevision, ProjectStatus
from sirius.presentation.initial_project_window import GREETING_TEXT, InitialProjectWindow


class _FakeProjectRepository:
    def __init__(self, initial: Project | None = None, *, raise_on_create: bool = False) -> None:
        now = datetime.now(UTC)
        self._project = initial or Project(
            id=1,
            name="",
            status=ProjectStatus.ACTIVE,
            current_revision=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        self._raise_on_create = raise_on_create
        self.create_calls: list[tuple[str, str]] = []

    def get_active_project(self) -> Project | None:
        return self._project

    def ensure_bootstrap_project(self) -> None:
        raise AssertionError("must never be called by InitialProjectWindow")

    def get_project(self, project_id: int) -> Project | None:
        raise AssertionError("must never be called by InitialProjectWindow")

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        raise AssertionError("must never be called by InitialProjectWindow")

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
        raise AssertionError("must never be called by InitialProjectWindow")

    def complete_active_project(self, project_id: int) -> Project:
        raise AssertionError("must never be called by InitialProjectWindow")

    def list_completed_projects(self) -> tuple[Project, ...]:
        raise AssertionError("must never be called by InitialProjectWindow")

    def create_project(
        self,
        name: str,
        objective: str,
        *,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
    ) -> Project:
        if self._raise_on_create:
            raise RuntimeError("fallo simulado de infraestructura con detalles internos sensibles")
        self.create_calls.append((name, objective))
        now = datetime.now(UTC)
        base_id = self._project.id if self._project is not None else 1
        base_created_at = self._project.created_at if self._project is not None else now
        revision = ProjectRevision(
            id=1,
            project_id=base_id,
            version=1,
            objective=objective,
            state_summary=state_summary,
            blockers=blockers,
            next_step=next_step,
            source_event_id=None,
            created_at=now,
        )
        self._project = Project(
            id=base_id,
            name=name,
            status=ProjectStatus.ACTIVE,
            current_revision=revision,
            created_at=base_created_at,
            updated_at=now,
            completed_at=None,
        )
        return self._project


def _configured_project(project_id: int = 1) -> Project:
    now = datetime.now(UTC)
    revision = ProjectRevision(
        id=1,
        project_id=project_id,
        version=1,
        objective="Objetivo original",
        state_summary="s",
        blockers=(),
        next_step="n",
        source_event_id=None,
        created_at=now,
    )
    return Project(
        id=project_id,
        name="Original",
        status=ProjectStatus.ACTIVE,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _noop_show_warning(title: str, text: str) -> None:
    del title, text


def _build_window(
    repository: _FakeProjectRepository | None = None,
    *,
    show_warning: Callable[[str, str], None] | None = None,
) -> tuple[InitialProjectWindow, _FakeProjectRepository, InitialProjectUseCase]:
    resolved_repository = repository or _FakeProjectRepository()
    use_case = InitialProjectUseCase(resolved_repository)
    window = InitialProjectWindow(use_case, show_warning=show_warning or _noop_show_warning)
    return window, resolved_repository, use_case


@pytest.mark.gui
def test_shows_the_deterministic_greeting_with_the_canonical_identity_name(
    qtbot: QtBot,
) -> None:
    window, _repository, _use_case = _build_window()
    qtbot.addWidget(window)

    assert INITIAL_IDENTITY_NAME in GREETING_TEXT
    assert "proveedor" not in GREETING_TEXT.lower()  # never an LLM-generated promise


@pytest.mark.gui
def test_name_and_objective_fields_are_present_and_accessible(qtbot: QtBot) -> None:
    window, _repository, _use_case = _build_window()
    qtbot.addWidget(window)

    assert window.name_input.isEnabled() is True
    assert window.objective_input.isEnabled() is True
    assert window.create_button.isEnabled() is True


@pytest.mark.gui
def test_initial_keyboard_focus_is_on_the_name_field(qtbot: QtBot) -> None:
    window, _repository, _use_case = _build_window()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitActive(window)
    QApplication.processEvents()

    assert window.name_input.hasFocus() is True


@pytest.mark.gui
def test_missing_fields_show_an_actionable_warning_without_calling_the_repository(
    qtbot: QtBot,
) -> None:
    warnings: list[tuple[str, str]] = []
    window, repository, _use_case = _build_window(
        show_warning=lambda title, text: warnings.append((title, text))
    )
    qtbot.addWidget(window)

    window._handle_create_clicked()

    assert repository.create_calls == []
    assert len(warnings) == 1


@pytest.mark.gui
def test_whitespace_only_objective_is_rejected_before_calling_the_repository(
    qtbot: QtBot,
) -> None:
    window, repository, _use_case = _build_window()
    qtbot.addWidget(window)
    window.name_input.setText("Mi Proyecto")
    window.objective_input.setText("   ")

    window._handle_create_clicked()

    assert repository.create_calls == []


@pytest.mark.gui
def test_valid_submission_creates_the_project_and_emits_created(qtbot: QtBot) -> None:
    window, _repository, use_case = _build_window()
    qtbot.addWidget(window)
    created_calls: list[None] = []
    window.created.connect(lambda: created_calls.append(None))

    window.name_input.setText("  Mi Proyecto  ")
    window.objective_input.setText("  Aprender Sirius  ")
    window._handle_create_clicked()

    assert len(created_calls) == 1
    assert use_case.is_configured() is True
    project = use_case.get_active_project()
    assert project is not None
    assert project.name == "Mi Proyecto"
    assert project.current_revision is not None
    assert project.current_revision.objective == "Aprender Sirius"


@pytest.mark.gui
def test_submitting_via_return_pressed_also_creates_the_project(qtbot: QtBot) -> None:
    window, _repository, use_case = _build_window()
    qtbot.addWidget(window)

    window.name_input.setText("Mi Proyecto")
    window.objective_input.setText("Aprender Sirius")
    window.objective_input.returnPressed.emit()

    assert use_case.is_configured() is True


@pytest.mark.gui
def test_already_configured_error_is_shown_inline_and_data_is_kept(qtbot: QtBot) -> None:
    """A second attempt (e.g. a stale window still open) is rejected by the
    real use case's own RF-015 guard, shown inline, without losing input."""
    repository = _FakeProjectRepository(_configured_project())
    window, _repository, _use_case = _build_window(repository)
    qtbot.addWidget(window)
    window.name_input.setText("Segundo Proyecto")
    window.objective_input.setText("Otro objetivo")

    window._handle_create_clicked()

    assert window.status_label.text() != ""
    assert window.name_input.text() == "Segundo Proyecto"
    assert window.objective_input.text() == "Otro objetivo"
    assert window.name_input.isEnabled() is True
    assert window.create_button.isEnabled() is True
    assert repository.create_calls == []


@pytest.mark.gui
def test_a_repository_failure_never_shows_internal_details_and_leaves_no_partial_project(
    qtbot: QtBot,
) -> None:
    repository = _FakeProjectRepository(raise_on_create=True)
    window, _repository, use_case = _build_window(repository)
    qtbot.addWidget(window)
    window.name_input.setText("Mi Proyecto")
    window.objective_input.setText("Aprender Sirius")

    window._handle_create_clicked()

    assert "fallo simulado" not in window.status_label.text()
    assert "RuntimeError" not in window.status_label.text()
    assert window.status_label.text() != ""
    assert window.name_input.isEnabled() is True
    assert window.objective_input.isEnabled() is True
    assert window.create_button.isEnabled() is True
    assert use_case.is_configured() is False


@pytest.mark.gui
def test_double_submit_is_prevented_while_busy(qtbot: QtBot) -> None:
    window, repository, _use_case = _build_window()
    qtbot.addWidget(window)
    window.name_input.setText("Mi Proyecto")
    window.objective_input.setText("Aprender Sirius")

    window._handle_create_clicked()
    window._handle_create_clicked()  # a second, redundant call right after success

    assert len(repository.create_calls) == 1
