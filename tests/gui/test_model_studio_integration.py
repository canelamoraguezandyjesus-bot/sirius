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

from sirius.adapters.audio.fake import (
    FakeAudioCapture,
    FakeAudioPlayback,
    FakeSpeechToText,
    FakeTextToSpeech,
)
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
from sirius.application.studio_voice import StudioVoiceUseCase, VoiceSettings
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.domain.model_studio import StudioCaptureState, StudioInteractionState
from sirius.ports.audio_capture import AudioCaptureError, AudioCaptureErrorKind
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


def _build_window(
    database_path: Path, studio_voice_use_case: StudioVoiceUseCase | None = None
) -> MainWindow:
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
        studio_voice_use_case=studio_voice_use_case,
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


# --- Voz dentro de la ventana real --------------------------------------


def _voice_use_case(tmp_path: Path, **kwargs: object) -> StudioVoiceUseCase:
    directory = tmp_path / "audio"
    directory.mkdir(exist_ok=True)
    return StudioVoiceUseCase(
        audio_capture=kwargs.get("capture") or FakeAudioCapture(directory),  # type: ignore[arg-type]
        speech_to_text=kwargs.get("speech_to_text") or FakeSpeechToText(),  # type: ignore[arg-type]
        text_to_speech=kwargs.get("text_to_speech") or FakeTextToSpeech(directory),  # type: ignore[arg-type]
        audio_playback=kwargs.get("playback") or FakeAudioPlayback(),  # type: ignore[arg-type]
        settings=VoiceSettings(voice="onyx"),
    )


@pytest.mark.gui
def test_without_voice_the_microphone_says_why_it_is_off(qtbot: QtBot, tmp_path: Path) -> None:
    """Un control apagado sin explicación hace pensar que está roto."""
    window = _build_window(_bootstrapped_database(tmp_path / "sirius.db"))
    qtbot.addWidget(window)

    assert not window.studio_page.voice_available
    assert not window.studio_page.microphone_button.isEnabled()
    assert window.studio_page.microphone_button.toolTip()


@pytest.mark.gui
def test_one_click_listens_and_the_next_one_transcribes(qtbot: QtBot, tmp_path: Path) -> None:
    """Sin mantener nada pulsado: un clic empieza y otro para."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    voice = _voice_use_case(tmp_path, speech_to_text=FakeSpeechToText("enciende el led"))
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.microphone_button.click()
    assert window.studio_page.interaction_state is StudioInteractionState.ESCUCHANDO
    assert voice.is_listening

    window.studio_page.microphone_button.click()
    qtbot.waitUntil(
        lambda: window.studio_page.interaction_state is StudioInteractionState.REVISANDO,
        timeout=5000,
    )

    # El texto queda para revisar: nada se ha guardado todavía.
    assert window.studio_page.input.toPlainText() == "enciende el led"
    assert window.studio_page.message_count == 0
    assert window.message_list.count() == 0


@pytest.mark.gui
def test_the_reviewed_text_only_enters_the_conversation_when_sent(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    voice = _voice_use_case(tmp_path, speech_to_text=FakeSpeechToText("hola"))
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider(("Dime.",)))
    window.open_model_studio()

    window.studio_page.microphone_button.click()
    window.studio_page.microphone_button.click()
    qtbot.waitUntil(
        lambda: window.studio_page.interaction_state is StudioInteractionState.REVISANDO,
        timeout=5000,
    )
    # El usuario corrige antes de enviar.
    window.studio_page.set_input_text("hola Sirius")
    window.studio_page.send_button.click()
    _wait_idle(qtbot, window)

    assert window.studio_page.message_bodies()[0] == (MessageRole.USER, "hola Sirius")


@pytest.mark.gui
def test_a_microphone_failure_leaves_the_written_chat_usable(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    directory = tmp_path / "audio"
    directory.mkdir(exist_ok=True)
    voice = _voice_use_case(
        tmp_path,
        capture=FakeAudioCapture(
            directory,
            start_error=AudioCaptureError(AudioCaptureErrorKind.NO_DEVICE, "sin micro"),
        ),
    )
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider(("Vale.",)))
    window.open_model_studio()

    window.studio_page.microphone_button.click()

    assert window.studio_page.interaction_state is StudioInteractionState.ERROR
    assert window.studio_page.error_label.text()

    # Y aun así se puede seguir escribiendo.
    window.studio_page.input.setPlainText("sigo escribiendo")
    window.studio_page.send_button.click()
    _wait_idle(qtbot, window)

    assert window.studio_page.message_bodies()[-1] == (MessageRole.SIRIUS, "Vale.")


@pytest.mark.gui
def test_sirius_speaks_a_completed_answer_inside_model_studio(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    directory = tmp_path / "audio"
    directory.mkdir(exist_ok=True)
    text_to_speech = FakeTextToSpeech(directory)
    voice = _voice_use_case(tmp_path, text_to_speech=text_to_speech)
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider(("Monta el Uno.",)))
    window.open_model_studio()

    window.studio_page.input.setPlainText("¿por dónde empiezo?")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: len(text_to_speech.requests) == 1, timeout=5000)

    assert "Monta el Uno." in text_to_speech.requests[0].text


@pytest.mark.gui
def test_sirius_stays_quiet_in_the_technical_interface(qtbot: QtBot, tmp_path: Path) -> None:
    """Nadie espera que un chat de trabajo empiece a sonar solo."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    directory = tmp_path / "audio"
    directory.mkdir(exist_ok=True)
    text_to_speech = FakeTextToSpeech(directory)
    voice = _voice_use_case(tmp_path, text_to_speech=text_to_speech)
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider(("Vale.",)))

    window.message_input.setText("desde la interfaz técnica")
    window.send_button.click()
    _wait_idle(qtbot, window)

    assert text_to_speech.requests == []


@pytest.mark.gui
def test_leaving_model_studio_closes_the_microphone(qtbot: QtBot, tmp_path: Path) -> None:
    """Nada puede seguir escuchando en una superficie que ya no se ve."""
    voice = _voice_use_case(tmp_path)
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"), studio_voice_use_case=voice
    )
    qtbot.addWidget(window)
    window.open_model_studio()
    window.studio_page.microphone_button.click()
    assert voice.is_listening

    window.close_model_studio()

    assert not voice.is_listening


@pytest.mark.gui
def test_muting_and_stopping_reach_the_use_case(qtbot: QtBot, tmp_path: Path) -> None:
    voice = _voice_use_case(tmp_path)
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"), studio_voice_use_case=voice
    )
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.mute_button.setChecked(True)
    assert voice.is_muted

    window.studio_page.mute_button.setChecked(False)
    assert not voice.is_muted

    window.studio_page.stop_voice_button.click()
    assert not voice.is_speaking


@pytest.mark.gui
def test_the_surface_stops_saying_hablando_when_the_voice_ends(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Empezar a hablar lo sabe la ventana; terminar, solo el reproductor.

    Sin el aviso de vuelta, la superficie se quedaba anunciando «HABLANDO»
    indefinidamente después de que dejara de sonar.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    playback = FakeAudioPlayback()
    voice = _voice_use_case(tmp_path, playback=playback)
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider(("Monta el Uno.",)))
    window.open_model_studio()

    window.studio_page.input.setPlainText("¿por dónde empiezo?")
    window.studio_page.send_button.click()
    qtbot.waitUntil(
        lambda: window.studio_page.interaction_state is StudioInteractionState.HABLANDO,
        timeout=5000,
    )

    playback.finish()

    assert window.studio_page.interaction_state is StudioInteractionState.PREPARADO


@pytest.mark.gui
def test_the_end_of_the_voice_never_overrides_a_later_state(qtbot: QtBot, tmp_path: Path) -> None:
    """Si mientras sonaba ya se estaba escuchando, ese estado manda."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    playback = FakeAudioPlayback()
    voice = _voice_use_case(tmp_path, playback=playback)
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider(("Monta el Uno.",)))
    window.open_model_studio()

    window.studio_page.input.setPlainText("¿por dónde empiezo?")
    window.studio_page.send_button.click()
    qtbot.waitUntil(
        lambda: window.studio_page.interaction_state is StudioInteractionState.HABLANDO,
        timeout=5000,
    )
    window.studio_page.microphone_button.click()
    assert window.studio_page.interaction_state is StudioInteractionState.ESCUCHANDO

    playback.finish()

    assert window.studio_page.interaction_state is StudioInteractionState.ESCUCHANDO


@pytest.mark.gui
def test_the_speaker_icon_says_whether_there_is_sound(qtbot: QtBot, tmp_path: Path) -> None:
    """Un altavoz tachado permanente se lee como «no hay sonido».

    Es exactamente lo que ocurrió en la primera prueba real: el icono decía qué
    hacía el botón, no cómo estaba la voz. Ahora dice lo segundo.
    """
    voice = _voice_use_case(tmp_path)
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"), studio_voice_use_case=voice
    )
    qtbot.addWidget(window)
    window.open_model_studio()
    button = window.studio_page.mute_button

    assert "Silenciar" in button.toolTip()
    sounding = button.icon().pixmap(24, 24).toImage()

    button.setChecked(True)

    assert "activar" in button.toolTip()
    assert button.icon().pixmap(24, 24).toImage() != sounding

    button.setChecked(False)

    assert button.icon().pixmap(24, 24).toImage() == sounding


# --- Los dos botones que no hacían nada ---------------------------------


@pytest.mark.gui
def test_read_all_speaks_the_code_that_the_voice_normally_skips(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """«Leer todo» tiene que decir algo distinto de «Repetir», o no sirve.

    La voz resume un bloque de código en «te dejo el código en pantalla», que
    es lo correcto casi siempre. Grabando hay un momento en que sí quieres
    oírlo, para comentarlo mientras se ve.
    """
    directory = tmp_path / "audio"
    directory.mkdir(exist_ok=True)
    text_to_speech = FakeTextToSpeech(directory)
    voice = _voice_use_case(tmp_path, text_to_speech=text_to_speech)
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"), studio_voice_use_case=voice
    )
    qtbot.addWidget(window)
    window.open_model_studio()
    window._last_spoken_text = "Monta esto:\n```python\npin = 13\n```\nY ya está."

    window.studio_page.repeat_button.click()
    qtbot.waitUntil(lambda: len(text_to_speech.requests) == 1, timeout=5000)
    assert "pin = 13" not in text_to_speech.requests[0].text
    assert "código en pantalla" in text_to_speech.requests[0].text

    window.studio_page.read_all_button.click()
    qtbot.waitUntil(lambda: len(text_to_speech.requests) == 2, timeout=5000)
    assert "pin = 13" in text_to_speech.requests[1].text


@pytest.mark.gui
def test_both_buttons_are_alive_once_there_is_a_voice(qtbot: QtBot, tmp_path: Path) -> None:
    """Estaban dibujados y apagados para siempre, ocupando sitio en la barra."""
    voice = _voice_use_case(tmp_path)
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"), studio_voice_use_case=voice
    )
    qtbot.addWidget(window)

    assert window.studio_page.read_all_button.isEnabled()
    assert window.studio_page.settings_button.isEnabled()


@pytest.mark.gui
def test_choosing_a_voice_applies_it_and_saves_it(qtbot: QtBot, tmp_path: Path) -> None:
    """Elegir a oído exige oírlas, y lo elegido tiene que sobrevivir al cierre."""
    voice = _voice_use_case(tmp_path)
    guardadas: list[str] = []
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"), studio_voice_use_case=voice
    )
    window._save_studio_voice = guardadas.append
    qtbot.addWidget(window)

    window._apply_studio_voice("sage")

    assert voice.voice == "sage"
    assert guardadas == ["sage"]


@pytest.mark.gui
def test_a_voice_the_provider_does_not_have_is_ignored(qtbot: QtBot, tmp_path: Path) -> None:
    """Una voz inexistente convertiría cada respuesta siguiente en un error."""
    voice = _voice_use_case(tmp_path)
    anterior = voice.voice

    voice.set_voice("una-que-no-existe")

    assert voice.voice == anterior


# --- Empezar a hablar sin esperar a terminar de escribir -----------------


_RESPUESTA_LARGA = (
    "Empieza por el pin trece, que es el que lleva el led integrado. "
    "Luego conecta la resistencia de doscientos veinte ohmios en serie. "
    "Y por último comprueba la continuidad antes de soldar nada."
)


@pytest.mark.gui
def test_sirius_starts_talking_before_finishing_the_answer(qtbot: QtBot, tmp_path: Path) -> None:
    """Grabando, dos esperas seguidas mirando a la cámara son una de más.

    La primera frase se sintetiza mientras el resto todavía se escribe, así que
    las dos esperas se solapan en vez de sumarse.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    directory = tmp_path / "audio"
    directory.mkdir(exist_ok=True)
    text_to_speech = FakeTextToSpeech(directory)
    playback = FakeAudioPlayback()
    voice = _voice_use_case(tmp_path, text_to_speech=text_to_speech, playback=playback)
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider((_RESPUESTA_LARGA,)))
    window.open_model_studio()

    window.studio_page.input.setPlainText("¿por dónde empiezo?")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: len(text_to_speech.requests) >= 1, timeout=5000)

    primera = text_to_speech.requests[0].text
    assert primera.startswith("Empieza por el pin trece")
    assert "resistencia" not in primera, "no puede llevarse media respuesta de golpe"


@pytest.mark.gui
def test_nothing_is_said_twice(qtbot: QtBot, tmp_path: Path) -> None:
    """Lo ya leído no se repite al llegar el final: se lee solo lo que falta."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    directory = tmp_path / "audio"
    directory.mkdir(exist_ok=True)
    text_to_speech = FakeTextToSpeech(directory)
    playback = FakeAudioPlayback()
    voice = _voice_use_case(tmp_path, text_to_speech=text_to_speech, playback=playback)
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider((_RESPUESTA_LARGA,)))
    window.open_model_studio()

    window.studio_page.input.setPlainText("¿por dónde empiezo?")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: len(text_to_speech.requests) >= 1, timeout=5000)
    playback.finish()  # el primer trozo termina de sonar
    qtbot.waitUntil(lambda: len(text_to_speech.requests) == 2, timeout=5000)

    dicho = " ".join(peticion.text for peticion in text_to_speech.requests)
    assert dicho.count("pin trece") == 1
    assert "resistencia" in dicho
    assert "continuidad" in dicho


@pytest.mark.gui
def test_the_second_piece_waits_for_the_first_to_finish(qtbot: QtBot, tmp_path: Path) -> None:
    """El audio tiene que sonar en el orden en que se escribió.

    Sintetizar el segundo trozo mientras suena el primero podría hacerlos
    solapar, y dos voces de Sirius a la vez es lo peor que puede oírse.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    directory = tmp_path / "audio"
    directory.mkdir(exist_ok=True)
    text_to_speech = FakeTextToSpeech(directory)
    playback = FakeAudioPlayback()
    voice = _voice_use_case(tmp_path, text_to_speech=text_to_speech, playback=playback)
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider((_RESPUESTA_LARGA,)))
    window.open_model_studio()

    window.studio_page.input.setPlainText("¿por dónde empiezo?")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: len(text_to_speech.requests) >= 1, timeout=5000)
    _wait_idle(qtbot, window)

    qtbot.wait(200)
    assert len(text_to_speech.requests) == 1, "el segundo trozo no puede adelantarse"

    playback.finish()
    qtbot.waitUntil(lambda: len(text_to_speech.requests) == 2, timeout=5000)


@pytest.mark.gui
def test_cancelling_shuts_the_voice_up(qtbot: QtBot, tmp_path: Path) -> None:
    """La contrapartida de hablar antes, y su compensación.

    Hablar sin terminar significa que una respuesta cancelada puede haber
    sonado en parte. Lo que no puede pasar es que siga sonando: interrumpir a
    alguien es que deje de hablar, no que termine la frase.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    directory = tmp_path / "audio"
    directory.mkdir(exist_ok=True)
    text_to_speech = FakeTextToSpeech(directory)
    playback = FakeAudioPlayback()
    voice = _voice_use_case(tmp_path, text_to_speech=text_to_speech, playback=playback)
    window = _build_window(database_path, studio_voice_use_case=voice)
    qtbot.addWidget(window)
    _swap_provider(window, database_path, FakeLLMProvider((_RESPUESTA_LARGA,)))
    window.open_model_studio()

    window.studio_page.input.setPlainText("¿por dónde empiezo?")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: len(text_to_speech.requests) >= 1, timeout=5000)
    dichas = len(text_to_speech.requests)

    window._speak_if_studio_is_open(_RESPUESTA_LARGA, MessageStatus.CANCELLED)

    assert playback.stops >= 1, "la voz tiene que callarse"
    qtbot.wait(200)
    assert len(text_to_speech.requests) == dichas, "no se lee el resto de algo cancelado"
