"""GUI tests for the B3a first-project screen (RF-014/015/016, D-02).

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
from sirius.domain.project import Project
from sirius.presentation.initial_project_window import GREETING_TEXT, InitialProjectWindow


class _FakeProjectRepository:
    def __init__(self, initial: Project | None = None, *, raise_on_update: bool = False) -> None:
        now = datetime.now(UTC)
        self._project = initial or Project(
            id=1,
            name="",
            objective="",
            current_state="",
            blockers="",
            next_step="",
            created_at=now,
            updated_at=now,
        )
        self._raise_on_update = raise_on_update
        self.update_calls: list[tuple[str, str]] = []

    def get_or_create_active_project(self) -> Project:
        return self._project

    def get_active_project(self) -> Project | None:
        return self._project

    def update_project(
        self,
        project_id: int,
        *,
        name: str | None = None,
        objective: str | None = None,
        current_state: str | None = None,
        blockers: str | None = None,
        next_step: str | None = None,
    ) -> Project:
        if self._raise_on_update:
            raise RuntimeError("fallo simulado de infraestructura con detalles internos sensibles")
        assert name is not None
        assert objective is not None
        self.update_calls.append((name, objective))
        self._project = Project(
            id=self._project.id,
            name=name,
            objective=objective,
            current_state=current_state or self._project.current_state,
            blockers=blockers if blockers is not None else self._project.blockers,
            next_step=next_step or self._project.next_step,
            created_at=self._project.created_at,
            updated_at=datetime.now(UTC),
        )
        return self._project


def _configured_project(project_id: int = 1) -> Project:
    now = datetime.now(UTC)
    return Project(
        id=project_id,
        name="Original",
        objective="Objetivo original",
        current_state="s",
        blockers="",
        next_step="n",
        created_at=now,
        updated_at=now,
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

    assert repository.update_calls == []
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

    assert repository.update_calls == []


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
    assert project.objective == "Aprender Sirius"


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
    assert repository.update_calls == []


@pytest.mark.gui
def test_a_repository_failure_never_shows_internal_details_and_leaves_no_partial_project(
    qtbot: QtBot,
) -> None:
    repository = _FakeProjectRepository(raise_on_update=True)
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

    assert len(repository.update_calls) == 1
