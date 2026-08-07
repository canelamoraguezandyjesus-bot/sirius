"""Model Studio dentro de la ventana real: conmutación y conversación compartida.

La superficie no reimplementa el envío: pasa por el mismo
``SendMessageUseCase``, el mismo historial y la misma identidad que la interfaz
técnica. Estas pruebas comprueban justo eso, porque es lo que impide que
Model Studio se convierta en una segunda aplicación (§2 de la especificación).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
from PySide6.QtWidgets import QTabWidget
from pytestqt.qtbot import QtBot

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import build_sqlite_decision_repository
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_identity_repository import build_sqlite_identity_repository
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.context import ContextBuilder
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.send_message import SendMessageUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.conversation import MessageRole
from sirius.domain.model_studio import StudioCaptureState, StudioInteractionState
from sirius.ports.llm import LLMError, LLMErrorKind, LLMProvider, LLMRequest, LLMStreamEvent
from sirius.presentation.main_window import (
    MODEL_STUDIO_PAGE_INDEX,
    TECHNICAL_PAGE_INDEX,
    MainWindow,
)

_PROJECT_NAME = "HEAD-R1"


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path) -> Path:
    upgrade_to_head(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project_repository.create_project(
        _PROJECT_NAME,
        "Construir la cabeza robótica",
        state_summary="Montando la protoboard",
        blockers=(),
        next_step="Probar el primer servo",
    )
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    return database_path


def _build_window(database_path: Path) -> MainWindow:
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=FakeSecretStore()
    )
    return MainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        get_budget_status_use_case=dependencies.get_budget_status_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        project_continuity_use_case=dependencies.project_continuity_use_case,
        project_lifecycle_use_case=dependencies.project_lifecycle_use_case,
        save_manual_memory_use_case=dependencies.save_manual_memory_use_case,
        get_memory_origin_use_case=dependencies.get_memory_origin_use_case,
        correct_memory_use_case=dependencies.correct_memory_use_case,
        archive_memory_use_case=dependencies.archive_memory_use_case,
        delete_memory_use_case=dependencies.delete_memory_use_case,
        propose_decision_use_case=dependencies.propose_decision_use_case,
        approve_decision_use_case=dependencies.approve_decision_use_case,
        get_decision_origin_use_case=dependencies.get_decision_origin_use_case,
        supersede_decision_use_case=dependencies.supersede_decision_use_case,
        archive_decision_use_case=dependencies.archive_decision_use_case,
        detect_precedence_conflicts_use_case=dependencies.detect_precedence_conflicts_use_case,
        get_knowledge_overview_use_case=dependencies.get_knowledge_overview_use_case,
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        export_structured_use_case=dependencies.export_structured_use_case,
        close_database_connections=dependencies.close_database_connections,
        show_warning=lambda title, text: None,
        show_information=lambda title, text: None,
    )


class _FailingLLMProvider:
    """Falla antes de emitir nada, para ejercitar el camino de error."""

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMError(kind=LLMErrorKind.CONNECTION, message="no se pudo contactar")

    def cancel(self, operation_id: str) -> None:
        del operation_id


def _swap_provider(window: MainWindow, database_path: Path, llm_provider: LLMProvider) -> None:
    repository = build_sqlite_conversation_repository(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=project_repository,
        memory_repository=memory_repository,
        conversation_repository=repository,
        decision_repository=decision_repository,
        rank_relevant_knowledge_use_case=RankRelevantKnowledgeUseCase(
            memory_repository=memory_repository,
            decision_repository=decision_repository,
            project_repository=project_repository,
            knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
        ),
        event_repository=build_sqlite_event_repository(database_path),
        token_counter=CharacterHeuristicTokenCounter(),
    )
    window._send_message_use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=repository,
        llm_provider=llm_provider,
    )


def _wait_idle(qtbot: QtBot, window: MainWindow) -> None:
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)


# --- Conmutación ---------------------------------------------------------


@pytest.mark.gui
def test_sirius_opens_on_the_technical_interface(qtbot: QtBot, tmp_path: Path) -> None:
    """Model Studio no se activa solo: hay que pedirlo."""
    window = _build_window(_bootstrapped_database(tmp_path / "sirius.db"))
    qtbot.addWidget(window)

    assert not window.model_studio_open
    assert window._pages.currentIndex() == TECHNICAL_PAGE_INDEX


@pytest.mark.gui
def test_the_button_opens_model_studio_and_the_exit_returns(qtbot: QtBot, tmp_path: Path) -> None:
    window = _build_window(_bootstrapped_database(tmp_path / "sirius.db"))
    qtbot.addWidget(window)

    window.open_studio_button.click()
    assert window.model_studio_open
    assert window._pages.currentIndex() == MODEL_STUDIO_PAGE_INDEX

    window.studio_page.exit_button.click()
    assert not window.model_studio_open


@pytest.mark.gui
def test_leaving_model_studio_also_leaves_clean_mode(qtbot: QtBot, tmp_path: Path) -> None:
    """Nadie debe volver a la interfaz técnica con la ventana a pantalla completa."""
    window = _build_window(_bootstrapped_database(tmp_path / "sirius.db"))
    qtbot.addWidget(window)
    window.open_model_studio()
    window.studio_page.toggle_clean_mode()

    window.close_model_studio()

    assert not window.studio_page.clean_mode
    assert not window.model_studio_open


@pytest.mark.gui
def test_the_technical_interface_is_untouched(qtbot: QtBot, tmp_path: Path) -> None:
    """La página 0 conserva sus tres pestañas y su conversación de siempre."""
    window = _build_window(_bootstrapped_database(tmp_path / "sirius.db"))
    qtbot.addWidget(window)

    assert isinstance(window.tabs, QTabWidget)
    assert window.tabs.count() == 3
    assert window.tabs.tabText(0) == "Conversación"
    assert window.message_list is not None


# --- Conversación compartida --------------------------------------------


@pytest.mark.gui
def test_existing_history_appears_in_both_views(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    repository = build_sqlite_conversation_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    repository.append_message(conversation.id, MessageRole.USER, "uno")
    repository.append_message(conversation.id, MessageRole.SIRIUS, "dos")

    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.message_list.count() == 2
    assert window.studio_page.message_bodies() == [
        (MessageRole.USER, "uno"),
        (MessageRole.SIRIUS, "dos"),
    ]


@pytest.mark.gui
def test_sending_from_model_studio_uses_the_same_conversation(qtbot: QtBot, tmp_path: Path) -> None:
    """El envío pasa por ``SendMessageUseCase``, se persiste y se ve en las dos vistas."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider(("Hola ", "Andy.")))
    window.open_model_studio()

    window.studio_page.input.setPlainText("¿Qué tal?")
    window.studio_page.send_button.click()
    _wait_idle(qtbot, window)

    assert window.studio_page.message_bodies() == [
        (MessageRole.USER, "¿Qué tal?"),
        (MessageRole.SIRIUS, "Hola Andy."),
    ]
    # El historial persistido es el mismo, no una copia paralela.
    persisted = [
        (message.role, message.content) for message in window._get_history_use_case.get_history()
    ]
    assert persisted == [(MessageRole.USER, "¿Qué tal?"), (MessageRole.SIRIUS, "Hola Andy.")]
    assert window.message_list.count() == 2


@pytest.mark.gui
def test_sending_from_the_technical_interface_reaches_model_studio(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Las dos vistas son la misma conversación, se envíe desde donde se envíe."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider(("Vale.",)))

    window.message_input.setText("desde la interfaz técnica")
    window.send_button.click()
    _wait_idle(qtbot, window)

    assert window.studio_page.message_bodies() == [
        (MessageRole.USER, "desde la interfaz técnica"),
        (MessageRole.SIRIUS, "Vale."),
    ]


@pytest.mark.gui
def test_state_goes_through_thinking_and_back_to_ready(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider(("Ya está.",)))
    window.open_model_studio()
    seen: list[StudioInteractionState] = []

    window.studio_page.input.setPlainText("hola")
    window.studio_page.send_button.click()
    seen.append(window.studio_page.interaction_state)
    _wait_idle(qtbot, window)
    seen.append(window.studio_page.interaction_state)

    assert seen == [StudioInteractionState.PENSANDO, StudioInteractionState.PREPARADO]


@pytest.mark.gui
def test_a_failure_shows_the_reason_and_keeps_typing_available(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """§10: un fallo no puede inutilizar el chat escrito."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, _FailingLLMProvider())
    window.open_model_studio()

    window.studio_page.input.setPlainText("hola")
    window.studio_page.send_button.click()
    _wait_idle(qtbot, window)

    assert window.studio_page.interaction_state is StudioInteractionState.ERROR
    assert window.studio_page.error_label.text()
    assert window.studio_page.input.isEnabled()
    assert window.studio_page.send_button.isEnabled()


@pytest.mark.gui
def test_a_blank_send_from_model_studio_does_nothing(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.input.setPlainText("   ")
    window.studio_page.send_button.click()

    assert window.studio_page.message_count == 0
    assert window.message_list.count() == 0


# --- Contexto y captura --------------------------------------------------


@pytest.mark.gui
def test_the_aside_shows_the_active_project(qtbot: QtBot, tmp_path: Path) -> None:
    window = _build_window(_bootstrapped_database(tmp_path / "sirius.db"))
    qtbot.addWidget(window)

    window.open_model_studio()

    assert window.studio_page.project_label.text() == _PROJECT_NAME
    assert window.studio_page.context_block.value_text() == "Montando la protoboard"


@pytest.mark.gui
def test_capture_stays_deactivated(qtbot: QtBot, tmp_path: Path) -> None:
    """El Módulo Captura no existe todavía: nada puede afirmar que se graba."""
    window = _build_window(_bootstrapped_database(tmp_path / "sirius.db"))
    qtbot.addWidget(window)

    window.open_model_studio()

    assert window.studio_page.capture_state is StudioCaptureState.DESACTIVADO
    assert not window.studio_page.capture_button.isEnabled()
    assert not window.studio_page.microphone_button.isEnabled()
