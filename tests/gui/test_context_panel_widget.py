"""GUI tests for the B5 context panel (SIRIUS-B5-001).

Every use case here is the real one, wired by ``build_conversation_dependencies``
against a temporary SQLite database (the same pattern ``test_knowledge_widget.py``
and ``test_main_window.py`` use) — no hand-rolled fake repositories. The panel
is read-only, so there are no write seams to inject; only ``show_warning`` and
``show_information`` are recorded, matching ``tests/gui/conftest.py``'s
guarantee that no test ever opens a real Qt dialog.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.presentation.context_panel_widget import (
    NO_DECISIONS_TEXT,
    NO_MEMORIES_TEXT,
    NO_PROJECT_TEXT,
    ContextPanelWidget,
)


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_dependencies(
    tmp_path: Path, *, configure_project: bool = True
) -> ConversationDependencies:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    if configure_project:
        project_repository.create_project(
            "Proyecto de prueba",
            "Objetivo de prueba",
            state_summary="en curso",
            blockers=(),
            next_step="terminar B5",
        )
    return build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )


class _Recorder:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, str]] = []
        self.informations: list[tuple[str, str]] = []

    def show_warning(self, title: str, text: str) -> None:
        self.warnings.append((title, text))

    def show_information(self, title: str, text: str) -> None:
        self.informations.append((title, text))


def _build_widget(
    dependencies: ConversationDependencies, recorder: _Recorder
) -> ContextPanelWidget:
    return ContextPanelWidget(
        dependencies.project_continuity_use_case,
        dependencies.get_knowledge_overview_use_case,
        dependencies.get_memory_origin_use_case,
        dependencies.get_decision_origin_use_case,
        show_warning=recorder.show_warning,
        show_information=recorder.show_information,
    )


@pytest.mark.gui
def test_project_anchor_shows_name_and_next_step(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    text = widget.project_anchor_label.text()
    assert "Proyecto de prueba" in text
    assert "terminar B5" in text


@pytest.mark.gui
def test_project_anchor_without_project_is_safe(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path, configure_project=False)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert widget.project_anchor_label.text() == NO_PROJECT_TEXT


@pytest.mark.gui
def test_empty_knowledge_shows_placeholders(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert widget.decisions_list.count() == 1
    assert widget.decisions_list.item(0).text() == NO_DECISIONS_TEXT
    assert widget.memories_list.count() == 1
    assert widget.memories_list.item(0).text() == NO_MEMORIES_TEXT


@pytest.mark.gui
def test_current_memory_is_listed(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia vigente")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    labels = [widget.memories_list.item(i).text() for i in range(widget.memories_list.count())]
    assert any("preferencia vigente" in label for label in labels)


@pytest.mark.gui
def test_only_approved_decisions_are_listed(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    # Una propuesta (PROPOSED) no debe aparecer como contexto vigente.
    dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    approved = dependencies.propose_decision_use_case.propose(
        "Formato de copias", project_id, "Usar Argon2id + Fernet"
    )
    dependencies.approve_decision_use_case.approve(approved.id, confirmed=True)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    labels = [widget.decisions_list.item(i).text() for i in range(widget.decisions_list.count())]
    assert any("Formato de copias" in label for label in labels)
    assert not any("Motor de persistencia" in label for label in labels)


@pytest.mark.gui
def test_decision_origin_without_selection_warns(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)

    widget.decision_origin_button.click()

    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_memory_origin_opens_information(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia con origen")
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.memory_origin_button.click()

    assert len(recorder.informations) == 1
    assert recorder.informations[0][0] == "Origen del recuerdo"


@pytest.mark.gui
def test_placeholder_rows_carry_no_selectable_item(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)
    # La fila "Sin recuerdos vigentes." no lleva un Memory adjunto: pedir su
    # origen debe avisar, no romper.
    widget.memories_list.setCurrentRow(0)
    widget.memory_origin_button.click()

    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_refresh_picks_up_a_new_memory(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)
    assert widget.memories_list.item(0).text() == NO_MEMORIES_TEXT

    dependencies.save_manual_memory_use_case.save("recuerdo tardío")
    widget.refresh_button.click()

    labels = [widget.memories_list.item(i).text() for i in range(widget.memories_list.count())]
    assert any("recuerdo tardío" in label for label in labels)


@pytest.mark.gui
def test_external_busy_disables_controls(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.set_external_busy(True)
    assert not widget.refresh_button.isEnabled()
    assert not widget.decision_origin_button.isEnabled()
    assert not widget.memory_origin_button.isEnabled()

    widget.set_external_busy(False)
    assert widget.refresh_button.isEnabled()
    assert widget.decision_origin_button.isEnabled()
    assert widget.memory_origin_button.isEnabled()
