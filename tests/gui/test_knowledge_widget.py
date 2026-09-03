"""GUI tests for the B4f observable memory/decision panel (RF-019 a RF-026,
PA-010 a PA-016).

Every use case here is the real one, wired by ``build_conversation_dependencies``
against a temporary SQLite database (the same pattern ``test_main_window.py``
uses) — no fake ``UnitOfWork``/repository stand-ins are hand-rolled. Every
dialog seam (``prompt_line``/``prompt_multiline``/``confirm_action``/
``confirm_delete_memory``/``choose_superseding_decision``) is injected with a
deterministic double, matching ``tests/gui/conftest.py``'s guarantee that no
test ever opens a real Qt dialog.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtTest import QTest
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.delete_memory import OLD_BACKUP_WARNING, SourceMessageChoice
from sirius.application.set_criticality import CriticalityTargetKind
from sirius.application.tag_category import CategoryTargetKind, TagCategoryUseCase
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.domain.criticality import Criticality
from sirius.domain.decision import Decision
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.presentation.knowledge_widget import KnowledgeWidget, _DeleteMemoryDialog


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
            next_step="siguiente paso",
        )
    return build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )


class _Recorder:
    """Records every warning/information dialog shown, for assertions."""

    def __init__(self) -> None:
        self.warnings: list[tuple[str, str]] = []
        self.informations: list[tuple[str, str]] = []

    def show_warning(self, title: str, text: str) -> None:
        self.warnings.append((title, text))

    def show_information(self, title: str, text: str) -> None:
        self.informations.append((title, text))


def _build_widget(
    dependencies: ConversationDependencies,
    recorder: _Recorder,
    *,
    confirm_action: bool = True,
    prompt_line_value: str | None = None,
    prompt_multiline_value: str | None = None,
    confirm_delete_memory_value: SourceMessageChoice | None = None,
    choose_superseding_decision: Callable[[Sequence[Decision]], Decision | None] | None = None,
    correct_memory_use_case: Any = None,
    tag_category_use_case: Any = None,
    set_category_use_case: Any = None,
    category_vocabulary: frozenset[str] | None = None,
    propose_criticality_use_case: Any = None,
    set_criticality_use_case: Any = None,
    thread_pool: QThreadPool | None = None,
) -> KnowledgeWidget:
    def _choose_superseding(candidates: Sequence[Decision]) -> Decision | None:
        if choose_superseding_decision is None:
            return None
        return choose_superseding_decision(candidates)

    return KnowledgeWidget(
        dependencies.get_knowledge_overview_use_case,
        dependencies.save_manual_memory_use_case,
        dependencies.get_memory_origin_use_case,
        correct_memory_use_case or dependencies.correct_memory_use_case,
        dependencies.archive_memory_use_case,
        dependencies.delete_memory_use_case,
        dependencies.propose_decision_use_case,
        dependencies.approve_decision_use_case,
        dependencies.get_decision_origin_use_case,
        dependencies.supersede_decision_use_case,
        dependencies.archive_decision_use_case,
        dependencies.detect_precedence_conflicts_use_case,
        dependencies.project_continuity_use_case,
        dependencies.confirm_memory_suggestion_use_case,
        dependencies.reject_memory_suggestion_use_case,
        tag_category_use_case=tag_category_use_case,
        set_category_use_case=set_category_use_case,
        category_vocabulary=category_vocabulary,
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=set_criticality_use_case,
        thread_pool=thread_pool,
        show_warning=recorder.show_warning,
        show_information=recorder.show_information,
        confirm_action=lambda title, text: confirm_action,
        prompt_line=lambda title, label: prompt_line_value,
        prompt_multiline=lambda title, label: prompt_multiline_value,
        confirm_delete_memory=lambda: confirm_delete_memory_value,
        choose_superseding_decision=_choose_superseding,
    )


@pytest.mark.gui
def test_refresh_lists_current_and_archived_memories(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia guardada")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert widget.memories_list.count() == 1
    assert "preferencia guardada" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_save_memory_button_creates_a_new_memory(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(
        dependencies, _Recorder(), prompt_multiline_value="recuerda esto por favor"
    )
    qtbot.addWidget(widget)

    widget.save_memory_button.click()

    assert widget.memories_list.count() == 1
    assert "recuerda esto por favor" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_save_memory_cancelled_prompt_creates_nothing(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder(), prompt_multiline_value=None)
    qtbot.addWidget(widget)

    widget.save_memory_button.click()

    assert widget.memories_list.count() == 0


@pytest.mark.gui
def test_correct_memory_creates_a_new_revision(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("contenido original")
    widget = _build_widget(dependencies, _Recorder(), prompt_multiline_value="contenido corregido")
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.correct_memory_button.click()

    assert widget.memories_list.count() == 1
    assert "contenido corregido" in widget.memories_list.item(0).text()
    assert "v2" in widget.memories_list.item(0).text()


class _DoubleCorrectMemoryUseCase:
    """A double of ``CorrectMemoryUseCase`` that returns a canned ``Memory``,
    for the retagging-orchestration tests below (§8-M8's acceptance
    criterion for ``_handle_correct_memory_clicked``)."""

    def __init__(self, result: Memory) -> None:
        self._result = result
        self.calls: list[tuple[int, str]] = []

    def correct(self, memory_id: int, content: str, *, message_id: int | None = None) -> Memory:
        self.calls.append((memory_id, content))
        return self._result


class _RecordingTagCategoryUseCase:
    """A double of ``TagCategoryUseCase`` that records every call, for
    asserting whether ``CategoryTaggingWorker`` actually ran. Reports nothing
    uncategorized by default so the retroactive pass at construction
    (CODEX-002/CLAUDE-M8-001) never enqueues extra, unrelated calls in tests
    that only care about a single triggered action; pass the two sequences to
    exercise that retroactive pass itself."""

    def __init__(
        self,
        uncategorized_memories: Sequence[Memory] = (),
        uncategorized_decisions: Sequence[Decision] = (),
    ) -> None:
        self.calls: list[tuple[CategoryTargetKind, int]] = []
        self._uncategorized_memories = list(uncategorized_memories)
        self._uncategorized_decisions = list(uncategorized_decisions)

    def tag(self, kind: CategoryTargetKind, item_id: int) -> bool:
        self.calls.append((kind, item_id))
        return True

    def list_uncategorized_memories(self) -> list[Memory]:
        return self._uncategorized_memories

    def list_uncategorized_decisions(self) -> list[Decision]:
        return self._uncategorized_decisions


def _corrected_memory(*, category: str | None, category_locked: bool) -> Memory:
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=2,
        memory_id=1,
        version=2,
        content="contenido corregido",
        origin="Corrección manual del usuario",
        source_event_id=None,
        created_at=now,
    )
    return Memory(
        id=1,
        status=MemoryStatus.CURRENT,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        category=category,
        category_locked=category_locked,
    )


@pytest.mark.gui
def test_correcting_a_memory_enqueues_retagging_when_category_is_unset(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """§8-M8: confirma que la interfaz encola un ``CategoryTaggingWorker``
    nuevo sobre el elemento corregido cuando el resultado devuelto trae
    ``category is None``."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("contenido original")
    corrected = _corrected_memory(category=None, category_locked=False)
    correct_memory_use_case = _DoubleCorrectMemoryUseCase(corrected)
    tag_category_use_case = _RecordingTagCategoryUseCase()
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_multiline_value="contenido corregido",
        correct_memory_use_case=correct_memory_use_case,
        tag_category_use_case=tag_category_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.correct_memory_button.click()

    assert correct_memory_use_case.calls == [(1, "contenido corregido")]
    assert thread_pool.waitForDone(5000)
    assert tag_category_use_case.calls == [(CategoryTargetKind.MEMORY, corrected.id)]


@pytest.mark.gui
def test_correcting_a_memory_does_not_enqueue_retagging_when_category_is_locked(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """§8-M8: no encola nada cuando el resultado devuelto conserva
    ``category_locked = True`` — corregir el contenido nunca reabre una
    categoría que el usuario ya cerró."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("contenido original")
    corrected = _corrected_memory(category=None, category_locked=True)
    correct_memory_use_case = _DoubleCorrectMemoryUseCase(corrected)
    tag_category_use_case = _RecordingTagCategoryUseCase()
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_multiline_value="contenido corregido",
        correct_memory_use_case=correct_memory_use_case,
        tag_category_use_case=tag_category_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.correct_memory_button.click()

    assert correct_memory_use_case.calls == [(1, "contenido corregido")]
    assert thread_pool.waitForDone(5000)
    assert tag_category_use_case.calls == []


@pytest.mark.gui
def test_correct_memory_without_selection_warns(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)

    widget.correct_memory_button.click()

    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_archive_memory_moves_it_out_of_current(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia archivable")
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.archive_memory_button.click()

    assert "(archived)" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_archive_memory_cancelled_confirmation_leaves_it_current(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia")
    widget = _build_widget(dependencies, _Recorder(), confirm_action=False)
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.archive_memory_button.click()

    assert "(current)" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_delete_memory_preserving_source_message_shows_old_backup_warning(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("secreto a borrar")
    recorder = _Recorder()
    widget = _build_widget(
        dependencies,
        recorder,
        confirm_delete_memory_value=SourceMessageChoice.PRESERVE,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.delete_memory_button.click()

    # A deleted memory leaves both list_current_memories() and
    # list_archived_memories() (MemoryStatus.DELETED is excluded from both),
    # so the overview this panel renders from no longer includes it.
    assert widget.memories_list.count() == 0
    assert recorder.informations[-1][1] == OLD_BACKUP_WARNING


@pytest.mark.gui
def test_delete_memory_redacting_source_message_shows_old_backup_warning(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("secreto a redactar")
    recorder = _Recorder()
    widget = _build_widget(
        dependencies,
        recorder,
        confirm_delete_memory_value=SourceMessageChoice.REDACT,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.delete_memory_button.click()

    assert widget.memories_list.count() == 0
    assert recorder.informations[-1][1] == OLD_BACKUP_WARNING


@pytest.mark.gui
def test_delete_memory_dialog_ok_button_disabled_until_explicit_choice(qtbot: QtBot) -> None:
    dialog = _DeleteMemoryDialog()
    qtbot.addWidget(dialog)
    ok_button = dialog._ok_button

    assert ok_button.isEnabled() is False
    assert dialog.preserve_radio.isChecked() is False
    assert dialog.redact_radio.isChecked() is False

    dialog.redact_radio.setChecked(True)

    assert ok_button.isEnabled() is True


@pytest.mark.gui
def test_delete_memory_cancelled_dialog_leaves_memory_untouched(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("contenido intacto")
    widget = _build_widget(dependencies, _Recorder(), confirm_delete_memory_value=None)
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.delete_memory_button.click()

    assert "contenido intacto" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_view_memory_origin_shows_the_recorded_event(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia con origen")
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.memory_origin_button.click()

    assert len(recorder.informations) == 1
    assert "memory.manual_save" in recorder.informations[0][1]


@pytest.mark.gui
def test_propose_decision_without_active_project_warns(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path, configure_project=False)
    recorder = _Recorder()
    widget = _build_widget(
        dependencies,
        recorder,
        prompt_line_value="Motor de persistencia",
        prompt_multiline_value="Usar SQLite",
    )
    qtbot.addWidget(widget)

    widget.propose_decision_button.click()

    assert widget.decisions_list.count() == 0
    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_propose_decision_creates_a_proposed_decision(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="Motor de persistencia",
        prompt_multiline_value="Usar SQLite local",
    )
    qtbot.addWidget(widget)

    widget.propose_decision_button.click()

    assert widget.decisions_list.count() == 1
    assert "(proposed)" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_approve_decision_moves_it_to_approved(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.approve_decision_button.click()

    assert "(approved)" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_supersede_decision_with_no_candidates_warns(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    approved = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    dependencies.approve_decision_use_case.approve(approved.id, confirmed=True)
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder, choose_superseding_decision=None)
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.supersede_decision_button.click()

    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_supersede_decision_replaces_the_approved_one(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    original = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    dependencies.approve_decision_use_case.approve(original.id, confirmed=True)
    substitute = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL"
    )

    def _pick_last(candidates: Sequence[Decision]) -> Decision:
        assert [c.id for c in candidates] == [substitute.id]
        return candidates[0]

    widget = _build_widget(
        dependencies,
        _Recorder(),
        confirm_action=True,
        choose_superseding_decision=_pick_last,
    )
    qtbot.addWidget(widget)
    original_row = next(
        row
        for row in range(widget.decisions_list.count())
        if f"#{original.id} " in widget.decisions_list.item(row).text()
    )
    widget.decisions_list.setCurrentRow(original_row)

    widget.supersede_decision_button.click()

    # A superseded decision leaves list_current_decisions() (only APPROVED)
    # without ever becoming PROPOSED or ARCHIVED, so the overview this panel
    # renders from no longer includes it; its link stays reachable, when
    # needed, through DecisionRepository.get_superseding_decision.
    texts = [widget.decisions_list.item(row).text() for row in range(widget.decisions_list.count())]
    assert not any(f"#{original.id} " in text for text in texts)
    assert any(f"#{substitute.id} " in text and "(approved)" in text for text in texts)


@pytest.mark.gui
def test_supersede_decision_offers_an_already_approved_decision_as_candidate(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """El caso manual que falló, ejercido por el panel real de la interfaz.

    Antes el selector se poblaba solo con decisiones PROPUESTAS, así que si el
    usuario ya había aprobado la decisión nueva no aparecía ninguna candidata,
    salía un aviso y las dos se quedaban vigentes con el mismo peso.
    """
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    original = dependencies.propose_decision_use_case.propose(
        "Día de la reunión", project_id, "La reunión es los martes"
    )
    dependencies.approve_decision_use_case.approve(original.id, confirmed=True)
    substitute = dependencies.propose_decision_use_case.propose(
        "Día de la reunión", project_id, "La reunión es los jueves"
    )
    dependencies.approve_decision_use_case.approve(substitute.id, confirmed=True)

    offered: list[list[int]] = []

    def _pick_substitute(candidates: Sequence[Decision]) -> Decision:
        offered.append([candidate.id for candidate in candidates])
        return next(candidate for candidate in candidates if candidate.id == substitute.id)

    recorder = _Recorder()
    widget = _build_widget(
        dependencies,
        recorder,
        confirm_action=True,
        choose_superseding_decision=_pick_substitute,
    )
    qtbot.addWidget(widget)
    original_row = next(
        row
        for row in range(widget.decisions_list.count())
        if f"#{original.id} " in widget.decisions_list.item(row).text()
    )
    widget.decisions_list.setCurrentRow(original_row)

    widget.supersede_decision_button.click()

    # La decisión ya aprobada se ofreció como candidata, y la seleccionada
    # nunca se ofrece a sí misma.
    assert offered == [[substitute.id]]
    assert recorder.warnings == []

    # El panel observable ya solo muestra la nueva como vigente.
    texts = [widget.decisions_list.item(row).text() for row in range(widget.decisions_list.count())]
    assert not any(f"#{original.id} " in text for text in texts)
    assert any(f"#{substitute.id} " in text and "(approved)" in text for text in texts)

    # Y el estado persistido es el correcto, con su vínculo.
    stored = dependencies.get_knowledge_overview_use_case.get_overview()
    assert [decision.id for decision in stored.current_decisions] == [substitute.id]


@pytest.mark.gui
def test_archive_decision_moves_it_out_of_current(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    approved = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    dependencies.approve_decision_use_case.approve(approved.id, confirmed=True)
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.archive_decision_button.click()

    assert "(archived)" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_view_decision_origin_shows_the_recorded_event(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.decision_origin_button.click()

    assert len(recorder.informations) == 1
    assert "decision.proposed" in recorder.informations[0][1]


@pytest.mark.gui
def test_detect_conflicts_reports_none_when_precedence_is_unambiguous(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.detect_conflicts_button.click()

    assert widget.conflicts_list.count() == 0
    assert "No hay conflictos" in widget.conflicts_status_label.text()


@pytest.mark.gui
def test_detect_conflicts_lists_unresolved_conflicts_without_choosing_a_winner(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project_id
    )
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.detect_conflicts_button.click()

    # Una cabecera no seleccionable por conflicto, más un ítem seleccionable
    # por cada miembro individual (§4.2) — nunca una única línea combinada.
    assert widget.conflicts_list.count() == 3
    header = widget.conflicts_list.item(0)
    assert "Motor de persistencia" in header.text()
    assert not (header.flags() & Qt.ItemFlag.ItemIsSelectable)
    member_texts = [widget.conflicts_list.item(row).text() for row in (1, 2)]
    assert any("usar SQLite local" in text for text in member_texts)
    assert any("usar un servidor remoto" in text for text in member_texts)
    assert "requieren aclaración" in widget.conflicts_status_label.text()


@pytest.mark.gui
def test_archive_memory_from_conflicts_list_resolves_the_conflict(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Criterio 1 de §8-M3: archivar una memoria en conflicto desde
    ``conflicts_list`` hace que una detección posterior deje de reportarlo,
    sin que ``sirius.domain.precedence`` cambie una sola línea."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project_id
    )
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.detect_conflicts_button.click()
    assert widget.conflicts_list.count() == 3

    widget.conflicts_list.setCurrentRow(1)
    widget.archive_memory_button.click()

    widget.detect_conflicts_button.click()

    assert widget.conflicts_list.count() == 0
    assert "No hay conflictos" in widget.conflicts_status_label.text()


@pytest.mark.gui
def test_conflicts_list_selection_disables_actions_that_do_not_resolve_the_conflict(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Criterio 2 de §8-M3: con un miembro Memory de un conflicto activo
    seleccionado, ``correct_memory_button`` queda deshabilitado (la
    corrección conserva ``subject_key``/``project_id`` y el conflicto
    reaparecería) mientras ``archive_memory_button`` sigue habilitado; con un
    miembro Decision seleccionado, ``approve_decision_button`` queda
    deshabilitado (toda decisión en conflicto ya está APPROVED) mientras
    ``supersede_decision_button``/``archive_decision_button`` siguen
    habilitados."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    first = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite"
    )
    dependencies.approve_decision_use_case.approve(first.id, confirmed=True)
    second = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL"
    )
    dependencies.approve_decision_use_case.approve(second.id, confirmed=True)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)
    widget.detect_conflicts_button.click()

    # Memory/Decision ids are independent sequences that can coincide (both
    # start at 1), so rows are told apart by the type of the associated
    # entity, never by matching "#<id>" against the rendered text.
    memory_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if isinstance(widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole), Memory)
    )
    widget.conflicts_list.setCurrentRow(memory_row)

    assert widget.correct_memory_button.isEnabled() is False
    assert widget.archive_memory_button.isEnabled() is True
    # CLAUDE-REV-001: approve_decision_button no resuelve un conflicto de
    # recuerdos tampoco, así que debe quedar deshabilitado igual que
    # correct_memory_button, no solo cuando el miembro activo es una Decision.
    assert widget.approve_decision_button.isEnabled() is False

    def _is_first_decision_row(row: int) -> bool:
        entity = widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole)
        return isinstance(entity, Decision) and entity.id == first.id

    decision_row = next(
        row for row in range(widget.conflicts_list.count()) if _is_first_decision_row(row)
    )
    widget.conflicts_list.setCurrentRow(decision_row)

    assert widget.approve_decision_button.isEnabled() is False
    assert widget.supersede_decision_button.isEnabled() is True
    assert widget.archive_decision_button.isEnabled() is True
    # CLAUDE-REV-001: correct_memory_button no resuelve un conflicto de
    # decisiones tampoco, así que debe quedar deshabilitado igual que
    # approve_decision_button, no solo cuando el miembro activo es una Memory.
    assert widget.correct_memory_button.isEnabled() is False


@pytest.mark.gui
def test_archive_decision_from_conflicts_list_ignores_the_general_panel_selection(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Criterio 3 de §8-M3: con una Decision distinta seleccionada a la vez en
    ``decisions_list`` (el panel general), archivar con la selección de
    ``conflicts_list`` activa modifica la decisión del conflicto — su id
    coincide con el de ``_selected_conflict_entity``, no con el de
    ``_selected_decision()`` sobre ``decisions_list`` — y una detección
    posterior ya no reporta ese conflicto."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    conflicting_first = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite"
    )
    dependencies.approve_decision_use_case.approve(conflicting_first.id, confirmed=True)
    conflicting_second = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL"
    )
    dependencies.approve_decision_use_case.approve(conflicting_second.id, confirmed=True)
    unrelated = dependencies.propose_decision_use_case.propose(
        "Día de la reunión", project_id, "La reunión es los martes"
    )
    dependencies.approve_decision_use_case.approve(unrelated.id, confirmed=True)

    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.detect_conflicts_button.click()

    unrelated_row = next(
        row
        for row in range(widget.decisions_list.count())
        if f"#{unrelated.id} " in widget.decisions_list.item(row).text()
    )
    widget.decisions_list.setCurrentRow(unrelated_row)
    selected_in_general_panel = widget._selected_decision()
    assert selected_in_general_panel is not None
    assert selected_in_general_panel.id == unrelated.id

    conflict_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if f"#{conflicting_first.id} " in widget.conflicts_list.item(row).text()
    )
    widget.conflicts_list.setCurrentRow(conflict_row)

    widget.archive_decision_button.click()

    texts = [widget.decisions_list.item(row).text() for row in range(widget.decisions_list.count())]
    assert not any(f"#{conflicting_first.id} " in text and "(approved)" in text for text in texts)
    assert any(f"#{unrelated.id} " in text and "(approved)" in text for text in texts)

    widget.detect_conflicts_button.click()
    assert widget.conflicts_list.count() == 0


@pytest.mark.gui
def test_selecting_memory_in_general_panel_after_conflict_cedes_priority_back_to_it(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CLAUDE-M3-001: ``conflicts_list`` solo tiene prioridad mientras sigue
    siendo la lista tocada más recientemente (§4.2) — seleccionar después una
    memoria distinta en ``memories_list`` reactiva ``correct_memory_button``
    y hace que ``archive_memory_button`` actúe sobre esa memoria, no sobre el
    miembro del conflicto visto antes."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project_id
    )
    unrelated = dependencies.save_manual_memory_use_case.save(
        "el equipo se reúne los martes", subject_key="Calendario", project_id=project_id
    )
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.detect_conflicts_button.click()

    memory_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if isinstance(widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole), Memory)
    )
    widget.conflicts_list.setCurrentRow(memory_row)
    assert widget.correct_memory_button.isEnabled() is False
    conflicting_memory_ids = {
        widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole).id
        for row in range(widget.conflicts_list.count())
        if isinstance(widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole), Memory)
    }

    unrelated_row = next(
        row
        for row in range(widget.memories_list.count())
        if f"#{unrelated.id} " in widget.memories_list.item(row).text()
    )
    widget.memories_list.setCurrentRow(unrelated_row)
    assert widget.correct_memory_button.isEnabled() is True

    widget.archive_memory_button.click()

    texts = [widget.memories_list.item(row).text() for row in range(widget.memories_list.count())]
    assert any(f"#{unrelated.id} " in text and "(archived)" in text for text in texts)
    assert not any(
        f"#{memory_id} " in text and "(archived)" in text
        for memory_id in conflicting_memory_ids
        for text in texts
    )


@pytest.mark.gui
def test_selecting_decision_in_general_panel_after_conflict_cedes_priority_back_to_it(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-001: seleccionar primero un miembro en ``conflicts_list`` y
    después una decisión distinta en ``decisions_list`` (el panel general)
    hace que ``archive_decision_button`` actúe sobre la decisión seleccionada
    al final en ``decisions_list``, no sobre el miembro del conflicto visto
    antes — el orden inverso al ya cubierto por
    ``test_archive_decision_from_conflicts_list_ignores_the_general_panel_selection``."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    conflicting_first = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite"
    )
    dependencies.approve_decision_use_case.approve(conflicting_first.id, confirmed=True)
    conflicting_second = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL"
    )
    dependencies.approve_decision_use_case.approve(conflicting_second.id, confirmed=True)
    unrelated = dependencies.propose_decision_use_case.propose(
        "Día de la reunión", project_id, "La reunión es los martes"
    )
    dependencies.approve_decision_use_case.approve(unrelated.id, confirmed=True)

    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.detect_conflicts_button.click()

    conflict_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if f"#{conflicting_first.id} " in widget.conflicts_list.item(row).text()
    )
    widget.conflicts_list.setCurrentRow(conflict_row)
    assert widget.approve_decision_button.isEnabled() is False

    unrelated_row = next(
        row
        for row in range(widget.decisions_list.count())
        if f"#{unrelated.id} " in widget.decisions_list.item(row).text()
    )
    widget.decisions_list.setCurrentRow(unrelated_row)
    selected_in_general_panel = widget._selected_decision()
    assert selected_in_general_panel is not None
    assert selected_in_general_panel.id == unrelated.id

    widget.archive_decision_button.click()

    texts = [widget.decisions_list.item(row).text() for row in range(widget.decisions_list.count())]
    assert any(f"#{unrelated.id} " in text and "(archived)" in text for text in texts)
    assert not any(f"#{conflicting_first.id} " in text and "(archived)" in text for text in texts)
    assert any(f"#{conflicting_first.id} " in text and "(approved)" in text for text in texts)


@pytest.mark.gui
def test_clicking_the_already_current_memory_row_cedes_priority_back_to_it(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-001: ``currentItemChanged`` no se emite al pulsar una fila que ya
    es ``currentItem()``. Secuencia: se selecciona una memoria del panel
    general, después un miembro de ``conflicts_list`` (que toma la
    prioridad), y por último se vuelve a pulsar —con un clic real, no
    ``setCurrentRow``— la misma fila ya seleccionada en ``memories_list``.
    Ese clic real debe ceder la prioridad de vuelta al panel general, igual
    que lo haría seleccionar una fila distinta."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project_id
    )
    already_selected = dependencies.save_manual_memory_use_case.save(
        "el equipo se reúne los martes", subject_key="Calendario", project_id=project_id
    )
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(lambda: widget.memories_list.viewport().width() > 0)

    already_selected_row = next(
        row
        for row in range(widget.memories_list.count())
        if f"#{already_selected.id} " in widget.memories_list.item(row).text()
    )
    widget.memories_list.setCurrentRow(already_selected_row)
    assert widget._last_touched_list is widget.memories_list

    widget.detect_conflicts_button.click()
    memory_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if isinstance(widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole), Memory)
    )
    widget.conflicts_list.setCurrentRow(memory_row)
    assert widget._last_touched_list is widget.conflicts_list

    # memories_list.currentItem() sigue siendo already_selected: setCurrentRow
    # nunca se llamó a nada distinto en esta lista, así que un clic real sobre
    # esa misma fila no dispara currentItemChanged — solo itemClicked.
    already_selected_item = widget.memories_list.item(already_selected_row)
    assert widget.memories_list.currentItem() is already_selected_item
    QTest.mouseClick(
        widget.memories_list.viewport(),
        Qt.MouseButton.LeftButton,
        pos=widget.memories_list.visualItemRect(already_selected_item).center(),
    )
    assert widget._last_touched_list is widget.memories_list

    widget.archive_memory_button.click()

    texts = [widget.memories_list.item(row).text() for row in range(widget.memories_list.count())]
    assert any(f"#{already_selected.id} " in text and "(archived)" in text for text in texts)
    assert not any("Motor de persistencia" in text and "(archived)" in text for text in texts)


@pytest.mark.gui
def test_clicking_the_already_current_decision_row_cedes_priority_back_to_it(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-001, caso simétrico de decisiones: ``currentItemChanged`` no se
    emite al pulsar una fila ya seleccionada en ``decisions_list``, así que un
    clic real sobre ella debe ceder la prioridad de vuelta al panel general
    igual que en ``test_clicking_the_already_current_memory_row_cedes_priority_back_to_it``."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    conflicting_first = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite"
    )
    dependencies.approve_decision_use_case.approve(conflicting_first.id, confirmed=True)
    conflicting_second = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL"
    )
    dependencies.approve_decision_use_case.approve(conflicting_second.id, confirmed=True)
    already_selected = dependencies.propose_decision_use_case.propose(
        "Día de la reunión", project_id, "La reunión es los martes"
    )
    dependencies.approve_decision_use_case.approve(already_selected.id, confirmed=True)

    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(lambda: widget.decisions_list.viewport().width() > 0)

    already_selected_row = next(
        row
        for row in range(widget.decisions_list.count())
        if f"#{already_selected.id} " in widget.decisions_list.item(row).text()
    )
    widget.decisions_list.setCurrentRow(already_selected_row)
    assert widget._last_touched_list is widget.decisions_list

    widget.detect_conflicts_button.click()
    conflict_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if f"#{conflicting_first.id} " in widget.conflicts_list.item(row).text()
    )
    widget.conflicts_list.setCurrentRow(conflict_row)
    assert widget._last_touched_list is widget.conflicts_list

    already_selected_item = widget.decisions_list.item(already_selected_row)
    assert widget.decisions_list.currentItem() is already_selected_item
    QTest.mouseClick(
        widget.decisions_list.viewport(),
        Qt.MouseButton.LeftButton,
        pos=widget.decisions_list.visualItemRect(already_selected_item).center(),
    )
    assert widget._last_touched_list is widget.decisions_list

    widget.archive_decision_button.click()

    texts = [widget.decisions_list.item(row).text() for row in range(widget.decisions_list.count())]
    assert any(f"#{already_selected.id} " in text and "(archived)" in text for text in texts)
    assert not any(f"#{conflicting_first.id} " in text and "(archived)" in text for text in texts)
    assert any(f"#{conflicting_first.id} " in text and "(approved)" in text for text in texts)


@pytest.mark.gui
def test_clicking_the_conflict_header_does_not_touch_conflicts_list(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-001 (ronda 4): la cabecera de un conflicto («Asunto «...»
    (proyecto ...)») no lleva ``ItemIsSelectable`` pero sí emite
    ``itemClicked`` al pulsarla. Secuencia: se selecciona un miembro A en
    ``conflicts_list`` (que toma la prioridad), después una memoria B
    distinta en ``memories_list`` (que cede la prioridad de vuelta al panel
    general), y por último se pulsa la cabecera del conflicto. Ese clic sobre
    la cabecera no produce ninguna entidad y no debe devolver la prioridad a
    ``conflicts_list``: archivar debe seguir actuando sobre B, no sobre A."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project_id
    )
    unrelated = dependencies.save_manual_memory_use_case.save(
        "el equipo se reúne los martes", subject_key="Calendario", project_id=project_id
    )
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(lambda: widget.conflicts_list.viewport().width() > 0)

    widget.detect_conflicts_button.click()
    memory_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if isinstance(widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole), Memory)
    )
    widget.conflicts_list.setCurrentRow(memory_row)
    assert widget._last_touched_list is widget.conflicts_list

    unrelated_row = next(
        row
        for row in range(widget.memories_list.count())
        if f"#{unrelated.id} " in widget.memories_list.item(row).text()
    )
    widget.memories_list.setCurrentRow(unrelated_row)
    assert widget._last_touched_list is widget.memories_list

    header_item = widget.conflicts_list.item(0)
    assert not (header_item.flags() & Qt.ItemFlag.ItemIsSelectable)
    QTest.mouseClick(
        widget.conflicts_list.viewport(),
        Qt.MouseButton.LeftButton,
        pos=widget.conflicts_list.visualItemRect(header_item).center(),
    )
    assert widget._last_touched_list is widget.memories_list

    widget.archive_memory_button.click()

    texts = [widget.memories_list.item(row).text() for row in range(widget.memories_list.count())]
    assert any(f"#{unrelated.id} " in text and "(archived)" in text for text in texts)
    assert not any("Motor de persistencia" in text and "(archived)" in text for text in texts)


@pytest.mark.gui
def test_clicking_the_conflict_header_while_unfocused_does_not_touch_conflicts_list(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-001 (ronda 5): el clic real sobre la cabecera de un conflicto
    cuando ``conflicts_list`` NO tiene el foco (a diferencia del test
    anterior, que solo usaba ``setCurrentRow`` y por eso no reproducía el
    fallo) entrega primero un ``QEvent.FocusIn`` al widget. El
    ``eventFilter`` reaccionaba a *cualquier* ``FocusIn`` leyendo
    ``currentItem()`` — todavía el miembro A, porque la cabecera no es
    seleccionable — y reactivaba ``conflicts_list`` antes de que
    ``itemClicked`` pudiera ignorar la cabecera. Secuencia: se selecciona un
    miembro A en ``conflicts_list``, se selecciona una memoria B en
    ``memories_list`` y se le da el foco explícitamente (para forzar el
    ``QEvent.FocusIn`` por ratón que el clic siguiente genera en
    ``conflicts_list``), y por
    último se pulsa con el ratón la cabecera del conflicto (sin haber tocado
    ``conflicts_list`` de nuevo). Archivar debe seguir actuando sobre B."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project_id
    )
    unrelated = dependencies.save_manual_memory_use_case.save(
        "el equipo se reúne los martes", subject_key="Calendario", project_id=project_id
    )
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(lambda: widget.conflicts_list.viewport().width() > 0)

    widget.detect_conflicts_button.click()
    memory_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if isinstance(widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole), Memory)
    )
    widget.conflicts_list.setCurrentRow(memory_row)
    assert widget._last_touched_list is widget.conflicts_list

    unrelated_row = next(
        row
        for row in range(widget.memories_list.count())
        if f"#{unrelated.id} " in widget.memories_list.item(row).text()
    )
    widget.memories_list.setCurrentRow(unrelated_row)
    assert widget._last_touched_list is widget.memories_list

    # A diferencia de test_clicking_the_conflict_header_does_not_touch_conflicts_list,
    # aquí se fuerza explícitamente el foco a memories_list para que el clic
    # posterior sobre conflicts_list dispare un QEvent.FocusIn real (por
    # ratón) antes del itemClicked de la cabecera.
    widget.memories_list.setFocus(Qt.FocusReason.MouseFocusReason)
    qtbot.waitUntil(lambda: widget.memories_list.hasFocus())

    header_item = widget.conflicts_list.item(0)
    assert not (header_item.flags() & Qt.ItemFlag.ItemIsSelectable)
    QTest.mouseClick(
        widget.conflicts_list.viewport(),
        Qt.MouseButton.LeftButton,
        pos=widget.conflicts_list.visualItemRect(header_item).center(),
    )
    assert widget._last_touched_list is widget.memories_list

    widget.archive_memory_button.click()

    texts = [widget.memories_list.item(row).text() for row in range(widget.memories_list.count())]
    assert any(f"#{unrelated.id} " in text and "(archived)" in text for text in texts)
    assert not any("Motor de persistencia" in text and "(archived)" in text for text in texts)


@pytest.mark.gui
def test_returning_keyboard_focus_to_the_current_row_touches_the_memories_list(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-002 (ronda 4): Tab/Shift+Tab pueden devolver el foco a una fila
    que ya es ``currentItem()`` sin emitir ``currentItemChanged`` ni
    ``itemClicked``. Secuencia: se selecciona una memoria del panel general,
    después un miembro de ``conflicts_list`` (que toma la prioridad), y por
    último el foco de teclado vuelve a ``memories_list`` sin cambiar su
    selección. Ese regreso de foco debe ceder la prioridad de vuelta al panel
    general igual que un clic o una nueva selección."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project_id
    )
    already_selected = dependencies.save_manual_memory_use_case.save(
        "el equipo se reúne los martes", subject_key="Calendario", project_id=project_id
    )
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(lambda: widget.memories_list.viewport().width() > 0)

    already_selected_row = next(
        row
        for row in range(widget.memories_list.count())
        if f"#{already_selected.id} " in widget.memories_list.item(row).text()
    )
    widget.memories_list.setCurrentRow(already_selected_row)
    assert widget._last_touched_list is widget.memories_list

    widget.detect_conflicts_button.click()
    memory_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if isinstance(widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole), Memory)
    )
    widget.conflicts_list.setCurrentRow(memory_row)
    assert widget._last_touched_list is widget.conflicts_list

    # memories_list.currentItem() sigue siendo already_selected_row: no se
    # simula un clic ni una selección nueva, solo el foco de teclado
    # regresando a la lista (setFocus es lo que dispara QEvent.FocusIn).
    already_selected_item = widget.memories_list.item(already_selected_row)
    assert widget.memories_list.currentItem() is already_selected_item
    widget.memories_list.setFocus(Qt.FocusReason.TabFocusReason)
    qtbot.waitUntil(lambda: widget.memories_list.hasFocus())
    assert widget._last_touched_list is widget.memories_list

    widget.archive_memory_button.click()

    texts = [widget.memories_list.item(row).text() for row in range(widget.memories_list.count())]
    assert any(f"#{already_selected.id} " in text and "(archived)" in text for text in texts)
    assert not any("Motor de persistencia" in text and "(archived)" in text for text in texts)


@pytest.mark.gui
def test_returning_keyboard_focus_to_the_current_row_touches_the_decisions_list(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-002 (ronda 4), caso simétrico de decisiones: el mismo regreso de
    foco por teclado a una fila ya seleccionada en ``decisions_list`` debe
    ceder la prioridad de vuelta al panel general."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    conflicting_first = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite"
    )
    dependencies.approve_decision_use_case.approve(conflicting_first.id, confirmed=True)
    conflicting_second = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL"
    )
    dependencies.approve_decision_use_case.approve(conflicting_second.id, confirmed=True)
    already_selected = dependencies.propose_decision_use_case.propose(
        "Día de la reunión", project_id, "La reunión es los martes"
    )
    dependencies.approve_decision_use_case.approve(already_selected.id, confirmed=True)

    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(lambda: widget.decisions_list.viewport().width() > 0)

    already_selected_row = next(
        row
        for row in range(widget.decisions_list.count())
        if f"#{already_selected.id} " in widget.decisions_list.item(row).text()
    )
    widget.decisions_list.setCurrentRow(already_selected_row)
    assert widget._last_touched_list is widget.decisions_list

    widget.detect_conflicts_button.click()
    conflict_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if f"#{conflicting_first.id} " in widget.conflicts_list.item(row).text()
    )
    widget.conflicts_list.setCurrentRow(conflict_row)
    assert widget._last_touched_list is widget.conflicts_list

    already_selected_item = widget.decisions_list.item(already_selected_row)
    assert widget.decisions_list.currentItem() is already_selected_item
    widget.decisions_list.setFocus(Qt.FocusReason.TabFocusReason)
    qtbot.waitUntil(lambda: widget.decisions_list.hasFocus())
    assert widget._last_touched_list is widget.decisions_list

    widget.archive_decision_button.click()

    texts = [widget.decisions_list.item(row).text() for row in range(widget.decisions_list.count())]
    assert any(f"#{already_selected.id} " in text and "(archived)" in text for text in texts)
    assert not any(f"#{conflicting_first.id} " in text and "(archived)" in text for text in texts)
    assert any(f"#{conflicting_first.id} " in text and "(approved)" in text for text in texts)


@pytest.mark.gui
def test_conflicts_list_selection_disables_actions_of_the_incompatible_entity_type(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-002: seleccionar un miembro ``Memory`` de un conflicto
    deshabilita también las acciones de decisión (``supersede_decision_button``,
    ``archive_decision_button``), que no resuelven un conflicto de recuerdos;
    seleccionar un miembro ``Decision`` deshabilita ``archive_memory_button``,
    que no resuelve uno de decisiones — sin esto, pulsar una de esas acciones
    podía archivar o sustituir una entidad ajena al conflicto tomada de la
    selección obsoleta del panel general."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    first = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite"
    )
    dependencies.approve_decision_use_case.approve(first.id, confirmed=True)
    second = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL"
    )
    dependencies.approve_decision_use_case.approve(second.id, confirmed=True)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)
    widget.detect_conflicts_button.click()

    memory_row = next(
        row
        for row in range(widget.conflicts_list.count())
        if isinstance(widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole), Memory)
    )
    widget.conflicts_list.setCurrentRow(memory_row)
    assert widget.archive_memory_button.isEnabled() is True
    assert widget.supersede_decision_button.isEnabled() is False
    assert widget.archive_decision_button.isEnabled() is False

    def _is_first_decision_row(row: int) -> bool:
        entity = widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole)
        return isinstance(entity, Decision) and entity.id == first.id

    decision_row = next(
        row for row in range(widget.conflicts_list.count()) if _is_first_decision_row(row)
    )
    widget.conflicts_list.setCurrentRow(decision_row)
    assert widget.supersede_decision_button.isEnabled() is True
    assert widget.archive_decision_button.isEnabled() is True
    assert widget.archive_memory_button.isEnabled() is False


@pytest.mark.gui
def test_set_external_busy_composes_with_conflict_type_restrictions(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-003: mientras hay una operación externa en curso,
    ``set_external_busy(True)`` deshabilita también los cinco botones de
    resolución de conflictos, y cambiar de selección en ``conflicts_list``
    durante ese intervalo no debe reactivarlos; al terminar, se reaplica la
    restricción por tipo de miembro en conflicto en vez de un reactivado
    ciego de los cinco."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project_id
    )
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)
    widget.detect_conflicts_button.click()

    memory_rows = [
        row
        for row in range(widget.conflicts_list.count())
        if isinstance(widget.conflicts_list.item(row).data(Qt.ItemDataRole.UserRole), Memory)
    ]
    widget.conflicts_list.setCurrentRow(memory_rows[0])
    assert widget.archive_memory_button.isEnabled() is True

    widget.set_external_busy(True)
    assert widget.correct_memory_button.isEnabled() is False
    assert widget.approve_decision_button.isEnabled() is False
    assert widget.archive_memory_button.isEnabled() is False
    assert widget.supersede_decision_button.isEnabled() is False
    assert widget.archive_decision_button.isEnabled() is False

    widget.conflicts_list.setCurrentRow(memory_rows[1])
    assert widget.archive_memory_button.isEnabled() is False
    assert widget.correct_memory_button.isEnabled() is False

    widget.set_external_busy(False)
    assert widget.correct_memory_button.isEnabled() is False
    assert widget.archive_memory_button.isEnabled() is True


@pytest.mark.gui
def test_set_external_busy_disables_every_action_button(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.set_external_busy(True)

    assert not widget.save_memory_button.isEnabled()
    assert not widget.propose_decision_button.isEnabled()
    assert not widget.detect_conflicts_button.isEnabled()

    widget.set_external_busy(False)

    assert widget.save_memory_button.isEnabled()
    assert widget.propose_decision_button.isEnabled()
    assert widget.detect_conflicts_button.isEnabled()


# --- Sugerencias pendientes (M6, SIRIUS-ARQ-0.2 §3.6) ---------------------------


@pytest.mark.gui
def test_refresh_lists_pending_suggestions_only(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    pending = dependencies.propose_memory_suggestion_use_case.propose("sugerencia pendiente")
    confirmed = dependencies.propose_memory_suggestion_use_case.propose("sugerencia a confirmar")
    dependencies.confirm_memory_suggestion_use_case.confirm(confirmed.id)
    rejected = dependencies.propose_memory_suggestion_use_case.propose("sugerencia a rechazar")
    dependencies.reject_memory_suggestion_use_case.reject(rejected.id)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert widget.suggestions_list.count() == 1
    assert "sugerencia pendiente" in widget.suggestions_list.item(0).text()
    assert f"#{pending.id}" in widget.suggestions_list.item(0).text()


@pytest.mark.gui
def test_confirm_suggestion_creates_a_memory_and_removes_it_from_pending(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.propose_memory_suggestion_use_case.propose("recordar esto")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)
    widget.suggestions_list.setCurrentRow(0)

    widget.confirm_suggestion_button.click()

    assert widget.suggestions_list.count() == 0
    assert widget.memories_list.count() == 1
    assert "recordar esto" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_reject_suggestion_removes_it_from_pending_without_creating_a_memory(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.propose_memory_suggestion_use_case.propose("no guardar esto")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)
    widget.suggestions_list.setCurrentRow(0)

    widget.reject_suggestion_button.click()

    assert widget.suggestions_list.count() == 0
    assert widget.memories_list.count() == 0


@pytest.mark.gui
def test_confirm_suggestion_without_a_selection_warns_and_creates_nothing(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.propose_memory_suggestion_use_case.propose("sugerencia pendiente")
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)

    widget.confirm_suggestion_button.click()

    assert recorder.warnings
    assert widget.suggestions_list.count() == 1
    assert widget.memories_list.count() == 0


@pytest.mark.gui
def test_reject_suggestion_without_a_selection_warns_and_changes_nothing(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.propose_memory_suggestion_use_case.propose("sugerencia pendiente")
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)

    widget.reject_suggestion_button.click()

    assert recorder.warnings
    assert widget.suggestions_list.count() == 1


@pytest.mark.gui
def test_set_external_busy_disables_suggestion_buttons_too(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.propose_memory_suggestion_use_case.propose("sugerencia pendiente")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.set_external_busy(True)

    assert not widget.confirm_suggestion_button.isEnabled()
    assert not widget.reject_suggestion_button.isEnabled()

    widget.set_external_busy(False)

    assert widget.confirm_suggestion_button.isEnabled()
    assert widget.reject_suggestion_button.isEnabled()


# --- Etiquetado automático tras cada guardado/confirmación/propuesta -------
#
# CODEX-003: en producción solo se encolaba un CategoryTaggingWorker tras
# corregir un recuerdo; guardar uno nuevo, confirmar una sugerencia o
# proponer una decisión no encolaban nada, así que esos tres caminos nunca
# recibían categoría automática.


@pytest.mark.gui
def test_saving_a_memory_enqueues_automatic_tagging(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    tag_category_use_case = _RecordingTagCategoryUseCase()
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_multiline_value="recuerda esto por favor",
        tag_category_use_case=tag_category_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.save_memory_button.click()

    assert thread_pool.waitForDone(5000)
    assert len(tag_category_use_case.calls) == 1
    kind, item_id = tag_category_use_case.calls[0]
    assert kind is CategoryTargetKind.MEMORY
    assert item_id == widget.memories_list.item(0).data(Qt.ItemDataRole.UserRole).id


@pytest.mark.gui
def test_confirming_a_suggestion_enqueues_automatic_tagging(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.propose_memory_suggestion_use_case.propose("sugerencia a confirmar")
    tag_category_use_case = _RecordingTagCategoryUseCase()
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        tag_category_use_case=tag_category_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)
    widget.suggestions_list.setCurrentRow(0)

    widget.confirm_suggestion_button.click()

    assert thread_pool.waitForDone(5000)
    assert len(tag_category_use_case.calls) == 1
    assert tag_category_use_case.calls[0][0] is CategoryTargetKind.MEMORY


@pytest.mark.gui
def test_proposing_a_decision_enqueues_automatic_tagging(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    tag_category_use_case = _RecordingTagCategoryUseCase()
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="Motor de persistencia",
        prompt_multiline_value="Usar SQLite local",
        tag_category_use_case=tag_category_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.propose_decision_button.click()

    assert thread_pool.waitForDone(5000)
    assert len(tag_category_use_case.calls) == 1
    assert tag_category_use_case.calls[0][0] is CategoryTargetKind.DECISION


class _FixedCategoryClassifier:
    """A ``CategoryClassifierPort`` double with one canned answer, mirroring
    ``tests/integration/test_category_tagging.py``'s ``_FakeClassifier``:
    never real Ollama."""

    def __init__(self, category: str | None) -> None:
        self._category = category

    def classify(self, content: str) -> str | None:
        return self._category


@pytest.mark.gui
def test_tagging_worker_finished_signal_refreshes_the_panel(qtbot: QtBot, tmp_path: Path) -> None:
    """CODEX-004: la señal ``finished`` del worker es lo único que hace
    aparecer una clasificación automática en el panel — sin conectarla, la
    categoría no aparecería hasta que otra acción disparase un refresco."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    database_path = tmp_path / "sirius.db"
    tag_category_use_case = TagCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
        _FixedCategoryClassifier("trabajo"),
    )
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_multiline_value="recuerda esto por favor",
        tag_category_use_case=tag_category_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.save_memory_button.click()
    assert thread_pool.waitForDone(5000)

    qtbot.waitUntil(lambda: "trabajo" in widget.memories_list.item(0).text(), timeout=5000)


# --- Referencia fuerte a los workers en vuelo (CODEX-001) -------------------
#
# QThreadPool.start() no conserva la referencia Python a un QRunnable (el
# mismo problema ya documentado para _active_send_worker en main_window.py):
# un CategoryTaggingWorker cuyo run() termine muy rápido puede recolectarse
# antes de que su señal finished, encolada entre hilos, llegue a procesarse,
# y _handle_tagging_worker_finished() nunca se ejecuta.


class _BlockingTagCategoryUseCase:
    """Bloquea ``tag()`` hasta que el test llame a ``release()``, para poder
    observar el worker mientras sigue en vuelo — mismo patrón que
    ``tests/gui/test_backup_recovery_ui.py``."""

    def __init__(self) -> None:
        self._continue_event = threading.Event()
        self.calls: list[tuple[CategoryTargetKind, int]] = []

    def tag(self, kind: CategoryTargetKind, item_id: int) -> bool:
        self.calls.append((kind, item_id))
        self._continue_event.wait(timeout=5)
        return False

    def list_uncategorized_memories(self) -> list[Memory]:
        return []

    def list_uncategorized_decisions(self) -> list[Decision]:
        return []

    def release(self) -> None:
        self._continue_event.set()


@pytest.mark.gui
def test_tagging_worker_reference_is_retained_while_in_flight_and_released_on_completion(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Mirrors tests/gui/test_conversation_ui.py's
    test_send_worker_reference_is_retained_while_blocked_and_released_on_completion
    for CategoryTaggingWorker: without a strong Python-level reference to
    every in-flight worker, a fast-finishing one can be garbage-collected
    before its queued cross-thread signal is delivered, and
    category_tagging_idle would never fire."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    tag_category_use_case = _BlockingTagCategoryUseCase()
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_multiline_value="recuerda esto por favor",
        tag_category_use_case=tag_category_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    assert widget._active_tagging_workers == []

    widget.save_memory_button.click()
    qtbot.waitUntil(lambda: tag_category_use_case.calls != [], timeout=5000)

    # The worker is genuinely blocked mid-run: the reference must still be held.
    assert len(widget._active_tagging_workers) == 1
    assert widget.has_pending_category_tagging

    idle_signals: list[None] = []
    widget.category_tagging_idle.connect(lambda: idle_signals.append(None))

    tag_category_use_case.release()

    qtbot.waitUntil(lambda: len(idle_signals) == 1, timeout=5000)
    assert widget._active_tagging_workers == []
    assert not widget.has_pending_category_tagging


# --- Pase retroactivo de arranque -------------------------------------------
#
# CLAUDE-M8-001/CODEX-002: list_uncategorized() estaba implementado en ambos
# repositorios pero no lo invocaba ningún llamador, así que un recuerdo o
# decisión guardado antes de esta migración se quedaba sin categoría para
# siempre.


@pytest.mark.gui
def test_opening_the_panel_retags_memories_and_decisions_left_uncategorized(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("recuerdo antiguo sin categoría")
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    decision = dependencies.propose_decision_use_case.propose(
        "Asunto antiguo", project_id, "contenido antiguo"
    )
    tag_category_use_case = _RecordingTagCategoryUseCase(
        uncategorized_memories=[memory], uncategorized_decisions=[decision]
    )
    thread_pool = QThreadPool()

    widget = _build_widget(
        dependencies,
        _Recorder(),
        tag_category_use_case=tag_category_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    assert thread_pool.waitForDone(5000)
    assert (CategoryTargetKind.MEMORY, memory.id) in tag_category_use_case.calls
    assert (CategoryTargetKind.DECISION, decision.id) in tag_category_use_case.calls


@pytest.mark.gui
def test_opening_the_panel_does_not_retag_anything_without_dependencies(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Sin ``tag_category_use_case``/``thread_pool`` inyectados (el valor por
    defecto de casi todas las pruebas de este fichero), el pase retroactivo
    no debe fallar ni intentar nada."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("recuerdo sin categoría")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert widget.memories_list.count() == 1


# --- Categoría observable y editable (CODEX-001) ----------------------------
#
# SetCategoryUseCase ya se construía en la raíz de composición, pero ningún
# consumidor de producción lo usaba, y el panel no mostraba category en
# absoluto: el usuario no podía ver ni corregir una clasificación.


@pytest.mark.gui
def test_memory_label_shows_its_category(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("preferencia categorizada")
    dependencies.set_category_use_case.set(CategoryTargetKind.MEMORY, memory.id, "trabajo")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert "trabajo" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_decision_label_shows_its_category(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    decision = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    dependencies.set_category_use_case.set(CategoryTargetKind.DECISION, decision.id, "proyecto")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert "proyecto" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_edit_memory_category_button_sets_and_locks_a_manual_category(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia a categorizar")
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="personal",
        set_category_use_case=dependencies.set_category_use_case,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.edit_memory_category_button.click()

    assert "personal" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_edit_memory_category_rejects_a_value_outside_the_closed_vocabulary(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-002: D7 exige un vocabulario cerrado (mismo que usa el
    clasificador automático) para que las categorías sigan siendo
    comparables; un valor ajeno como "inventada" nunca debe llegar a
    ``SetCategoryUseCase.set()``."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia a categorizar")
    recorder = _Recorder()
    widget = _build_widget(
        dependencies,
        recorder,
        prompt_line_value="inventada",
        set_category_use_case=dependencies.set_category_use_case,
        category_vocabulary=dependencies.category_vocabulary,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.edit_memory_category_button.click()

    assert " · " not in widget.memories_list.item(0).text()
    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_edit_memory_category_accepts_a_value_from_the_closed_vocabulary(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia a categorizar")
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="personal",
        set_category_use_case=dependencies.set_category_use_case,
        category_vocabulary=dependencies.category_vocabulary,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.edit_memory_category_button.click()

    assert "personal" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_edit_decision_category_button_sets_and_locks_a_manual_category(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="proyecto",
        set_category_use_case=dependencies.set_category_use_case,
    )
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.edit_decision_category_button.click()

    assert "proyecto" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_edit_memory_category_without_selection_warns(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    recorder = _Recorder()
    widget = _build_widget(
        dependencies, recorder, set_category_use_case=dependencies.set_category_use_case
    )
    qtbot.addWidget(widget)

    widget.edit_memory_category_button.click()

    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_edit_memory_category_cancelled_prompt_changes_nothing(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia intacta")
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value=None,
        set_category_use_case=dependencies.set_category_use_case,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.edit_memory_category_button.click()

    assert " · " not in widget.memories_list.item(0).text()


# --- Criticidad: propuesta y edición manual (M21b, ADR-131) -----------------
#
# «Sirius propone, el usuario decide» (M18b/ADR-126, ADR-130): la única
# escritura de ``criticality`` sigue siendo ``SetCriticalityUseCase.set()``,
# disparada exclusivamente por una acción explícita del usuario. Los dobles
# de abajo son deliberadamente los mismos dos, calcados de
# ``_RecordingTagCategoryUseCase``/``_BlockingTagCategoryUseCase``, ya que la
# propuesta comparte exactamente el mismo patrón de worker que la categoría.


class _RecordingProposeCriticalityUseCase:
    """Doble de ``ProposeCriticalityUseCase`` que registra cada llamada, para
    afirmar cuántos ``CriticalityProposalWorker`` arrancó realmente el
    panel — nunca más de uno por selección (ADR-131: nunca un barrido)."""

    def __init__(self, result: Criticality | None = None) -> None:
        self.calls: list[tuple[CriticalityTargetKind, int]] = []
        self._result = result

    def propose(self, kind: CriticalityTargetKind, item_id: int) -> Criticality | None:
        self.calls.append((kind, item_id))
        return self._result


class _BlockingProposeCriticalityUseCase:
    """Bloquea ``propose()`` hasta que el test llame a ``release()`` — mismo
    patrón que ``_BlockingTagCategoryUseCase`` —, para poder cambiar la
    selección mientras un worker sigue en vuelo y comprobar que la propuesta
    tardía se descarta sin mostrarse (ADR-131)."""

    def __init__(self, result: Criticality | None = Criticality.CRITICO) -> None:
        self._continue_event = threading.Event()
        self.calls: list[tuple[CriticalityTargetKind, int]] = []
        self._result = result

    def propose(self, kind: CriticalityTargetKind, item_id: int) -> Criticality | None:
        self.calls.append((kind, item_id))
        self._continue_event.wait(timeout=5)
        return self._result

    def release(self) -> None:
        self._continue_event.set()


class _SequencedBlockingProposeCriticalityUseCase:
    """Como ``_BlockingProposeCriticalityUseCase``, pero cada llamada tiene
    su propio resultado y su propio cerrojo: ``release(n)`` libera solo la
    llamada n-ésima. Permite forzar el orden de llegada (por ejemplo, que
    el resultado obsoleto de v1 llegue DESPUÉS del de v2) y distinguir en
    pantalla cuál de los dos gobernó (CLAUDE-REV-R3-001)."""

    def __init__(self, results: Sequence[Criticality | None]) -> None:
        self._results = list(results)
        self._events = [threading.Event() for _ in self._results]
        self.calls: list[tuple[CriticalityTargetKind, int]] = []
        self._lock = threading.Lock()

    def propose(self, kind: CriticalityTargetKind, item_id: int) -> Criticality | None:
        with self._lock:
            index = len(self.calls)
            self.calls.append((kind, item_id))
        self._events[index].wait(timeout=5)
        return self._results[index]

    def release(self, index: int) -> None:
        self._events[index].set()


class _RecordingSetCriticalityUseCase:
    """Doble de ``SetCriticalityUseCase`` que registra cada llamada, para
    afirmar que ``Rechazar`` nunca la invoca."""

    def __init__(self) -> None:
        self.calls: list[tuple[CriticalityTargetKind, int, Criticality | None]] = []

    def set(
        self, kind: CriticalityTargetKind, item_id: int, criticality: Criticality | None
    ) -> None:
        self.calls.append((kind, item_id, criticality))


@pytest.mark.gui
def test_memory_label_shows_its_criticality(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("nunca compartir la clave privada")
    dependencies.set_criticality_use_case.set(
        CriticalityTargetKind.MEMORY, memory.id, Criticality.CRITICO
    )
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert "[CRITICO]" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_decision_label_shows_its_criticality(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    decision = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    dependencies.set_criticality_use_case.set(
        CriticalityTargetKind.DECISION, decision.id, Criticality.IMPORTANTE
    )
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert "[IMPORTANTE]" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_edit_memory_criticality_button_sets_critico(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("no perder este dato")
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="CRITICO",
        set_criticality_use_case=dependencies.set_criticality_use_case,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.edit_memory_criticality_button.click()

    assert "[CRITICO]" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_edit_memory_criticality_button_sets_importante(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("recordar esto también")
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="IMPORTANTE",
        set_criticality_use_case=dependencies.set_criticality_use_case,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.edit_memory_criticality_button.click()

    assert "[IMPORTANTE]" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_edit_memory_criticality_button_ordinario_clears_the_mark(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """ORDINARIO no es un tercer nivel del enum ``Criticality`` (M18b): se
    traduce a ``None``, que quita la marca por completo."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("marcado y luego desmarcado")
    dependencies.set_criticality_use_case.set(
        CriticalityTargetKind.MEMORY, memory.id, Criticality.CRITICO
    )
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="ORDINARIO",
        set_criticality_use_case=dependencies.set_criticality_use_case,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.edit_memory_criticality_button.click()

    assert "[CRITICO]" not in widget.memories_list.item(0).text()
    assert "[IMPORTANTE]" not in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_edit_decision_criticality_button_sets_a_manual_criticality(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="CRITICO",
        set_criticality_use_case=dependencies.set_criticality_use_case,
    )
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.edit_decision_criticality_button.click()

    assert "[CRITICO]" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_edit_memory_criticality_rejects_a_value_outside_the_closed_vocabulary(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("recuerdo cualquiera")
    recorder = _Recorder()
    widget = _build_widget(
        dependencies,
        recorder,
        prompt_line_value="URGENTISIMO",
        set_criticality_use_case=dependencies.set_criticality_use_case,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.edit_memory_criticality_button.click()

    assert "[" not in widget.memories_list.item(0).text()
    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_edit_memory_criticality_without_selection_warns(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    recorder = _Recorder()
    widget = _build_widget(
        dependencies, recorder, set_criticality_use_case=dependencies.set_criticality_use_case
    )
    qtbot.addWidget(widget)

    widget.edit_memory_criticality_button.click()

    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_selecting_an_unmarked_memory_starts_exactly_one_proposal_worker(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("sin criticidad todavía")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.memories_list.setCurrentRow(0)

    assert thread_pool.waitForDone(5000)
    assert propose_criticality_use_case.calls == [(CriticalityTargetKind.MEMORY, memory.id)]


@pytest.mark.gui
def test_selecting_an_already_marked_memory_does_not_start_a_worker(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("ya con criticidad")
    dependencies.set_criticality_use_case.set(
        CriticalityTargetKind.MEMORY, memory.id, Criticality.IMPORTANTE
    )
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.memories_list.setCurrentRow(0)

    assert thread_pool.waitForDone(200) is True or thread_pool.activeThreadCount() == 0
    assert propose_criticality_use_case.calls == []


@pytest.mark.gui
def test_selecting_an_unmarked_memory_without_dependencies_proposes_nothing(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Sin ``propose_criticality_use_case``/``thread_pool`` inyectados no se
    propone nada, igual que ``_start_tagging_worker`` para categoría."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("sin criticidad, sin dependencias")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.memories_list.setCurrentRow(0)

    assert widget.memory_criticality_proposal_label.text() == ""


@pytest.mark.gui
def test_criticality_proposal_appears_for_the_current_selection(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("posible fuga de credenciales")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.memories_list.setCurrentRow(0)

    qtbot.waitUntil(
        lambda: widget.memory_criticality_proposal_label.text() == "Sirius propone: CRITICO",
        timeout=5000,
    )
    assert widget.confirm_memory_criticality_button.isEnabled()
    assert widget.reject_memory_criticality_button.isEnabled()


@pytest.mark.gui
def test_confirm_criticality_proposal_writes_the_exact_proposal_and_refreshes(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("posible fuga de credenciales")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(
        lambda: widget.memory_criticality_proposal_label.text() == "Sirius propone: CRITICO",
        timeout=5000,
    )

    widget.confirm_memory_criticality_button.click()

    assert "[CRITICO]" in widget.memories_list.item(0).text()
    assert widget.memory_criticality_proposal_label.text() == ""
    assert not widget.confirm_memory_criticality_button.isEnabled()


@pytest.mark.gui
def test_reject_criticality_proposal_does_not_write(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("posible fuga de credenciales")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    set_criticality_use_case = _RecordingSetCriticalityUseCase()
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(
        lambda: widget.memory_criticality_proposal_label.text() == "Sirius propone: CRITICO",
        timeout=5000,
    )

    widget.reject_memory_criticality_button.click()

    assert set_criticality_use_case.calls == []
    assert widget.memory_criticality_proposal_label.text() == ""
    assert not widget.confirm_memory_criticality_button.isEnabled()


@pytest.mark.gui
def test_reselecting_a_queried_memory_does_not_start_a_second_worker(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Un elemento consultado una vez no se vuelve a consultar en la misma
    sesión (ADR-131): la caché por ``(kind, id)`` evita un segundo worker."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("consultada una vez")
    other = dependencies.save_manual_memory_use_case.save("otro recuerdo distinto")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    # ``QThreadPool.waitForDone`` solo espera a que el hilo del worker
    # termine — la señal ``finished``, entre hilos, sigue en cola hasta que
    # el bucle de eventos de la GUI la procese; ``qtbot.waitUntil`` lo pumpea
    # hasta que la caché refleja el resultado (no basta con ``waitForDone``).
    widget.memories_list.setCurrentRow(0)
    assert thread_pool.waitForDone(5000)
    qtbot.waitUntil(
        lambda: (CriticalityTargetKind.MEMORY, memory.id) in widget._criticality_proposal_cache,
        timeout=5000,
    )
    assert propose_criticality_use_case.calls.count((CriticalityTargetKind.MEMORY, memory.id)) == 1

    widget.memories_list.setCurrentRow(1)
    assert thread_pool.waitForDone(5000)
    qtbot.waitUntil(
        lambda: (CriticalityTargetKind.MEMORY, other.id) in widget._criticality_proposal_cache,
        timeout=5000,
    )

    widget.memories_list.setCurrentRow(0)
    assert thread_pool.waitForDone(2000)
    qtbot.wait(200)

    assert propose_criticality_use_case.calls.count((CriticalityTargetKind.MEMORY, memory.id)) == 1


@pytest.mark.gui
def test_late_criticality_proposal_after_selection_changed_is_not_shown(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Si la selección cambió antes de que la propuesta llegara, se descarta
    sin mostrarse (ADR-131) — comparando ``kind``/``id`` con la selección
    vigente. ``other`` se marca de antemano para que seleccionarlo no
    arranque un segundo worker que compita por la misma señal ``finished``."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("primera selección")
    other = dependencies.save_manual_memory_use_case.save("segunda selección")
    dependencies.set_criticality_use_case.set(
        CriticalityTargetKind.MEMORY, other.id, Criticality.IMPORTANTE
    )
    propose_criticality_use_case = _BlockingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(lambda: propose_criticality_use_case.calls != [], timeout=5000)
    # La selección cambia antes de que la propuesta llegue.
    widget.memories_list.setCurrentRow(1)

    propose_criticality_use_case.release()
    assert thread_pool.waitForDone(5000)
    # Igual que arriba: da tiempo a que la señal ``finished``, encolada entre
    # hilos, llegue a procesarse antes de comprobar que no se mostró nada.
    qtbot.wait(200)

    assert propose_criticality_use_case.calls == [(CriticalityTargetKind.MEMORY, memory.id)]
    assert widget.memory_criticality_proposal_label.text() == ""
    assert not widget.confirm_memory_criticality_button.isEnabled()


# --- Coordinación con una restauración de copia de seguridad (CODEX-001) ---
#
# Mismo mecanismo que ``has_pending_category_tagging``/``category_tagging_idle``
# (ver la sección "Etiquetado automático de categoría" arriba), aplicado ahora
# a ``CriticalityProposalWorker``: un worker en vuelo también sigue usando los
# repositorios, y una restauración debe esperar a que no quede ninguno.


@pytest.mark.gui
def test_criticality_worker_reference_is_retained_while_in_flight_and_released_on_completion(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Mirrors test_tagging_worker_reference_is_retained_while_in_flight_and_released_on_completion
    for CriticalityProposalWorker: sin la referencia fuerte en
    ``_active_criticality_workers``, un worker que termine muy rápido podría
    recolectarse antes de que su señal ``finished`` se procese, y
    ``criticality_proposal_idle`` nunca llegaría a emitirse."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("sin criticidad todavía")
    propose_criticality_use_case = _BlockingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    assert widget._active_criticality_workers == []
    assert not widget.has_pending_criticality_proposal

    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(lambda: propose_criticality_use_case.calls != [], timeout=5000)

    assert len(widget._active_criticality_workers) == 1
    assert widget.has_pending_criticality_proposal

    idle_signals: list[None] = []
    widget.criticality_proposal_idle.connect(lambda: idle_signals.append(None))

    propose_criticality_use_case.release()

    qtbot.waitUntil(lambda: len(idle_signals) == 1, timeout=5000)
    assert widget._active_criticality_workers == []
    assert not widget.has_pending_criticality_proposal


@pytest.mark.gui
def test_selecting_an_item_does_not_start_a_criticality_worker_while_externally_busy(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-001: mientras una operación externa (por ejemplo, una
    restauración de copia de seguridad ya confirmada) mantiene el panel
    ocupado, seleccionar un elemento sin criticidad no debe arrancar un
    ``CriticalityProposalWorker`` nuevo — arrancaría después de que la
    restauración ya hubiera comprobado que no quedaba ninguno pendiente."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("sin criticidad todavía")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.set_external_busy(True)
    widget.memories_list.setCurrentRow(0)

    assert thread_pool.waitForDone(200) is True or thread_pool.activeThreadCount() == 0
    assert propose_criticality_use_case.calls == []
    assert not widget.has_pending_criticality_proposal


# --- Invalidación de la propuesta al corregir un recuerdo (CODEX-002) ------
#
# ``CorrectMemoryUseCase.correct`` crea una nueva revisión bajo el mismo id
# (RF-022): cualquier caché, rechazo o resultado en vuelo de una propuesta
# calculada sobre el contenido anterior deja de ser válido.


@pytest.mark.gui
def test_correcting_a_memory_invalidates_its_cached_criticality_proposal(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("contenido original")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_multiline_value="contenido corregido",
        correct_memory_use_case=dependencies.correct_memory_use_case,
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(
        lambda: (CriticalityTargetKind.MEMORY, memory.id) in widget._criticality_proposal_cache,
        timeout=5000,
    )
    assert propose_criticality_use_case.calls.count((CriticalityTargetKind.MEMORY, memory.id)) == 1

    widget.correct_memory_button.click()
    assert (CriticalityTargetKind.MEMORY, memory.id) not in widget._criticality_proposal_cache

    # refresh() reconstruye la lista y pierde la selección (ver comentario en
    # KnowledgeWidget.refresh): hay que reseleccionar el mismo recuerdo.
    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(
        lambda: (
            propose_criticality_use_case.calls.count((CriticalityTargetKind.MEMORY, memory.id)) == 2
        ),
        timeout=5000,
    )


@pytest.mark.gui
def test_correcting_a_memory_forgets_a_previous_rejection_of_its_criticality_proposal(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Un rechazo de esta sesión (ADR-131) es del contenido rechazado, no del
    id: tras corregir, la propuesta calculada sobre el contenido nuevo debe
    poder volver a mostrarse."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("contenido original")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_multiline_value="contenido corregido",
        correct_memory_use_case=dependencies.correct_memory_use_case,
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)

    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(
        lambda: widget.memory_criticality_proposal_label.text() == "Sirius propone: CRITICO",
        timeout=5000,
    )
    widget.reject_memory_criticality_button.click()
    assert (CriticalityTargetKind.MEMORY, memory.id) in widget._rejected_criticality_proposals

    widget.correct_memory_button.click()
    assert (CriticalityTargetKind.MEMORY, memory.id) not in widget._rejected_criticality_proposals

    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(
        lambda: widget.memory_criticality_proposal_label.text() == "Sirius propone: CRITICO",
        timeout=5000,
    )


# --- Botones de confirmar/rechazar criticidad durante un estado ocupado ----
# (CLAUDE-REV-002/CODEX-003)


@pytest.mark.gui
def test_set_external_busy_disables_criticality_buttons_even_without_a_shown_proposal(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Sin ninguna propuesta visible, los cuatro botones ya estaban
    deshabilitados; un estado ocupado no debe dejarlos habilitados al volver
    (CLAUDE-REV-002: antes ni siquiera se forzaban a False)."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.set_external_busy(True)
    assert not widget.confirm_memory_criticality_button.isEnabled()
    assert not widget.reject_memory_criticality_button.isEnabled()
    assert not widget.confirm_decision_criticality_button.isEnabled()
    assert not widget.reject_decision_criticality_button.isEnabled()

    widget.set_external_busy(False)
    assert not widget.confirm_memory_criticality_button.isEnabled()
    assert not widget.reject_memory_criticality_button.isEnabled()
    assert not widget.confirm_decision_criticality_button.isEnabled()
    assert not widget.reject_decision_criticality_button.isEnabled()


@pytest.mark.gui
def test_set_external_busy_disables_and_restores_a_shown_criticality_proposal(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("posible fuga de credenciales")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(
        lambda: widget.memory_criticality_proposal_label.text() == "Sirius propone: CRITICO",
        timeout=5000,
    )

    widget.set_external_busy(True)
    assert not widget.confirm_memory_criticality_button.isEnabled()
    assert not widget.reject_memory_criticality_button.isEnabled()

    widget.set_external_busy(False)
    assert widget.confirm_memory_criticality_button.isEnabled()
    assert widget.reject_memory_criticality_button.isEnabled()


@pytest.mark.gui
def test_criticality_worker_finishing_while_externally_busy_keeps_buttons_disabled(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-003: un worker que arrancó antes del estado ocupado puede
    terminar mientras dura — ``_show_criticality_proposal`` no debe habilitar
    los botones en ese caso; deben seguir deshabilitados hasta que el estado
    ocupado termine."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("posible fuga de credenciales")
    propose_criticality_use_case = _BlockingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(lambda: propose_criticality_use_case.calls != [], timeout=5000)

    widget.set_external_busy(True)
    propose_criticality_use_case.release()
    qtbot.waitUntil(
        lambda: widget.memory_criticality_proposal_label.text() == "Sirius propone: CRITICO",
        timeout=5000,
    )

    assert not widget.confirm_memory_criticality_button.isEnabled()
    assert not widget.reject_memory_criticality_button.isEnabled()

    widget.set_external_busy(False)
    assert widget.confirm_memory_criticality_button.isEnabled()
    assert widget.reject_memory_criticality_button.isEnabled()


# --- Ronda 3 (#520): una sola derivación desde el estado -------------------
#
# La propuesta mostrada y el arranque de un worker se recalculan desde el
# estado en cada transición (selección, fin del estado ocupado, fin del
# worker), en vez de decidirse con guardas sueltas en cada manejador
# (raíz de las rondas 1 y 2, ADR-001). Cada prueba fija una transición que
# antes abría un hueco.


@pytest.mark.gui
def test_manual_edit_before_the_worker_answers_never_resurrects_a_proposal(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CLAUDE-REV-R2-001: seleccionar un recuerdo sin marca (arranca el
    worker), fijar la criticidad a mano antes de que responda, reseleccionar
    el mismo recuerdo (ya marcado) y dejar terminar el worker viejo: la
    propuesta NO se muestra — el elemento ya no está sin marca — y por tanto
    «Confirmar» no puede sobrescribir el valor que el usuario acaba de fijar."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("sin criticidad todavía")
    propose_criticality_use_case = _BlockingProposeCriticalityUseCase(Criticality.CRITICO)
    set_criticality_use_case = _RecordingSetCriticalityUseCase()
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=set_criticality_use_case,
        thread_pool=thread_pool,
        prompt_line_value="IMPORTANTE",
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(lambda: propose_criticality_use_case.calls != [], timeout=5000)
    # Edición manual mientras el worker sigue en vuelo: escribe IMPORTANTE.
    widget.edit_memory_criticality_button.click()
    assert set_criticality_use_case.calls == [
        (CriticalityTargetKind.MEMORY, memory.id, Criticality.IMPORTANTE)
    ]
    # El doble no persiste: la lista debe ver el recuerdo ya marcado, como
    # lo vería tras una escritura real.
    dependencies.set_criticality_use_case.set(
        CriticalityTargetKind.MEMORY, memory.id, Criticality.IMPORTANTE
    )
    widget.refresh()
    widget.memories_list.setCurrentRow(0)
    propose_criticality_use_case.release()
    assert thread_pool.waitForDone(5000)
    qtbot.wait(200)
    assert propose_criticality_use_case.calls == [(CriticalityTargetKind.MEMORY, memory.id)]
    assert widget.memory_criticality_proposal_label.text() == ""
    assert not widget.confirm_memory_criticality_button.isEnabled()
    # Y aunque alguien pulsara Confirmar, no hay propuesta que escribir.
    widget.confirm_memory_criticality_button.click()
    assert len(set_criticality_use_case.calls) == 1


@pytest.mark.gui
def test_leaving_the_externally_busy_state_resumes_the_proposal_for_the_selection(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-001 (ronda 2): seleccionar un recuerdo sin marca mientras el
    panel está ocupado no arranca worker (CODEX-001 de la ronda 1); al
    dejar de estar ocupado, la selección vigente sí obtiene su propuesta sin
    que el usuario tenga que reseleccionar."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("sin criticidad todavía")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)
    widget.set_external_busy(True)
    widget.memories_list.setCurrentRow(0)
    assert propose_criticality_use_case.calls == []
    widget.set_external_busy(False)
    qtbot.waitUntil(
        lambda: widget.memory_criticality_proposal_label.text() == "Sirius propone: CRITICO",
        timeout=5000,
    )
    assert thread_pool.waitForDone(5000)
    assert propose_criticality_use_case.calls == [(CriticalityTargetKind.MEMORY, memory.id)]
    assert widget.confirm_memory_criticality_button.isEnabled()


@pytest.mark.gui
def test_correcting_a_memory_while_its_worker_is_in_flight_requests_the_new_revision(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-002 (ronda 2) y CLAUDE-REV-R3-001 (ronda 3): con el worker de
    la revisión v1 en vuelo, el usuario corrige el recuerdo (v2, mismo id) y
    lo reselecciona antes de que v1 termine. La revisión vigente recibe su
    propia consulta (el worker en vuelo de v1 no bloquea el de v2), y el
    resultado de v1 — que aquí se hace llegar DESPUÉS del de v2, con un
    valor distinto — se descarta por época: lo mostrado sigue siendo lo que
    respondió v2, y la caché no retrocede."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    memory = dependencies.save_manual_memory_use_case.save("contenido v1")
    propose_criticality_use_case = _SequencedBlockingProposeCriticalityUseCase(
        [Criticality.CRITICO, Criticality.IMPORTANTE]
    )
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
        prompt_multiline_value="contenido v2",
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(lambda: len(propose_criticality_use_case.calls) == 1, timeout=5000)
    widget.correct_memory_button.click()
    widget.memories_list.setCurrentRow(0)
    qtbot.waitUntil(lambda: len(propose_criticality_use_case.calls) == 2, timeout=5000)
    # Primero llega v2 (IMPORTANTE) y se muestra.
    propose_criticality_use_case.release(1)
    qtbot.waitUntil(
        lambda: widget.memory_criticality_proposal_label.text() == "Sirius propone: IMPORTANTE",
        timeout=5000,
    )
    # Después llega v1 (CRITICO), obsoleto: ni se muestra ni se cachea.
    propose_criticality_use_case.release(0)
    assert thread_pool.waitForDone(5000)
    qtbot.wait(200)
    assert widget.memory_criticality_proposal_label.text() == "Sirius propone: IMPORTANTE"
    assert propose_criticality_use_case.calls == [
        (CriticalityTargetKind.MEMORY, memory.id),
        (CriticalityTargetKind.MEMORY, memory.id),
    ]
    # Reseleccionar no vuelve a consultar y sigue mostrando lo de v2.
    widget.memories_list.setCurrentRow(-1)
    widget.memories_list.setCurrentRow(0)
    assert widget.memory_criticality_proposal_label.text() == "Sirius propone: IMPORTANTE"
    assert len(propose_criticality_use_case.calls) == 2


@pytest.mark.gui
def test_releasing_the_busy_state_without_resume_starts_no_proposal_worker(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """CODEX-001 (ronda 3): los flujos terminales de ``MainWindow`` (un envío
    que termina con el cierre ya solicitado; una restauración de copia que
    va a cerrar la ventana) liberan el estado ocupado sin reanudar la
    propuesta: no debe arrancar ningún worker — en producción sería una
    llamada a Ollama de hasta 30 s sobre una ventana que se cierra o una
    base recién restaurada."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("sin criticidad todavía")
    propose_criticality_use_case = _RecordingProposeCriticalityUseCase(Criticality.CRITICO)
    thread_pool = QThreadPool()
    widget = _build_widget(
        dependencies,
        _Recorder(),
        propose_criticality_use_case=propose_criticality_use_case,
        set_criticality_use_case=dependencies.set_criticality_use_case,
        thread_pool=thread_pool,
    )
    qtbot.addWidget(widget)
    widget.set_external_busy(True)
    widget.memories_list.setCurrentRow(0)
    assert propose_criticality_use_case.calls == []
    widget.set_external_busy(False, resume_proposals=False)
    assert thread_pool.waitForDone(200) is True or thread_pool.activeThreadCount() == 0
    assert propose_criticality_use_case.calls == []
    assert not widget.has_pending_criticality_proposal
    assert widget.memory_criticality_proposal_label.text() == ""
    # Los controles sí se han liberado.
    assert widget.save_memory_button.isEnabled()
