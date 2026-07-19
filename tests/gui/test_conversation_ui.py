import threading
from collections.abc import Iterable
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.context import ContextBuilder
from sirius.application.send_message import SendMessageUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.llm import (
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMProvider,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)
from sirius.presentation.main_window import MainWindow


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path) -> Path:
    """Mimic initialize_persistence(): schema + the three canonical singletons,
    plus a configured active project (B3c): ContextBuilder requires one."""
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="estado inicial",
        blockers=(),
        next_step="siguiente paso inicial",
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
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        project_continuity_use_case=dependencies.project_continuity_use_case,
        project_lifecycle_use_case=dependencies.project_lifecycle_use_case,
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        close_database_connections=dependencies.close_database_connections,
        show_warning=lambda title, text: None,
        show_information=lambda title, text: None,
    )


class _FailingLLMProvider:
    """Test double: always fails before any delta, to exercise the provider-failure path."""

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMError(kind=LLMErrorKind.CONNECTION, message="no se pudo contactar")

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _BlockingUntilReleasedProvider:
    """Test double: yields one delta, then blocks until the test calls ``release()``.

    Gives tests deterministic control over "cancel/close while a stream is
    genuinely in flight" without any arbitrary sleep: the worker thread
    parks on a real ``threading.Event`` until the test is ready to let it
    observe cancellation (or not).
    """

    def __init__(self) -> None:
        self._continue_event = threading.Event()
        self._cancelled: set[str] = set()

    def health_check(self) -> bool:
        return True

    def release(self) -> None:
        self._continue_event.set()

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        yield LLMTextDelta(text="parcial")
        self._continue_event.wait(timeout=5)
        if request.operation_id in self._cancelled:
            yield LLMCancelled(partial_text="parcial")
            return
        yield LLMCompleted(text="parcial completo", input_tokens=1, output_tokens=2)

    def cancel(self, operation_id: str) -> None:
        self._cancelled.add(operation_id)


class _FailOnNthAppendConversationRepository:
    """Wraps a real repository; raises on the Nth call to append_message."""

    def __init__(self, delegate: ConversationRepository, fail_on_call: int) -> None:
        self._delegate = delegate
        self._fail_on_call = fail_on_call
        self._calls = 0

    def get_or_create_main_conversation(self) -> Conversation:
        return self._delegate.get_or_create_main_conversation()

    def get_main_conversation(self) -> Conversation | None:
        return self._delegate.get_main_conversation()

    def append_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        *,
        operation_id: str | None = None,
        identity_version: int | None = None,
        status: MessageStatus = MessageStatus.COMPLETED,
    ) -> Message:
        self._calls += 1
        if self._calls == self._fail_on_call:
            msg = "simulated persistence failure"
            raise RuntimeError(msg)
        return self._delegate.append_message(
            conversation_id,
            role,
            content,
            operation_id=operation_id,
            identity_version=identity_version,
            status=status,
        )

    def list_messages(self, conversation_id: int) -> list[Message]:
        return self._delegate.list_messages(conversation_id)

    def get_message(self, message_id: int) -> Message | None:
        return self._delegate.get_message(message_id)

    def redact_message(self, message_id: int) -> Message:
        return self._delegate.redact_message(message_id)


def _swap_send_message_use_case(
    window: MainWindow,
    database_path: Path,
    llm_provider: LLMProvider,
    conversation_repository: ConversationRepository | None = None,
) -> None:
    repository = conversation_repository or build_sqlite_conversation_repository(database_path)
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        memory_repository=build_sqlite_memory_repository(database_path),
        conversation_repository=repository,
    )
    window._send_message_use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=repository,
        llm_provider=llm_provider,
    )


@pytest.mark.gui
def test_history_loads_in_stable_order_on_startup(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "uno")
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, "dos")
    conversation_repository.append_message(conversation.id, MessageRole.USER, "tres")

    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.message_list.count() == 3
    assert window.message_list.item(0).text() == "Tú: uno"
    assert window.message_list.item(1).text() == "Sirius: dos"
    assert window.message_list.item(2).text() == "Tú: tres"


@pytest.mark.gui
def test_loading_history_does_not_write_or_duplicate_anything(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "hola")

    window = _build_window(database_path)
    qtbot.addWidget(window)

    messages = conversation_repository.list_messages(conversation.id)
    assert len(messages) == 1
    assert window.message_list.count() == 1


@pytest.mark.gui
def test_sending_a_message_shows_user_and_reply_and_persists_both(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    window.message_input.setText("hola Sirius")
    window.send_button.click()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.message_list.count() == 2
    assert window.message_list.item(0).text() == "Tú: hola Sirius"
    assert window.message_list.item(1).text() == "Sirius: Respuesta simulada de Sirius."

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["hola Sirius", "Respuesta simulada de Sirius."]


@pytest.mark.gui
def test_response_streams_progressively_before_completion(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _swap_send_message_use_case(
        window, database_path, FakeLLMProvider(chunks=("uno ", "dos ", "tres"))
    )

    window.message_input.setText("hola")
    window.send_button.click()

    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)
    qtbot.waitUntil(
        lambda: window.message_list.item(1).text() == "Sirius: uno dos tres", timeout=5000
    )
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)


@pytest.mark.gui
def test_messages_persist_after_closing_and_reopening(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    first_window = _build_window(database_path)
    qtbot.addWidget(first_window)

    first_window.message_input.setText("recuerda esto")
    first_window.send_button.click()
    qtbot.waitUntil(lambda: first_window.send_button.isEnabled(), timeout=5000)
    first_window.close()

    second_window = _build_window(database_path)
    qtbot.addWidget(second_window)

    assert second_window.message_list.count() == 2
    assert second_window.message_list.item(0).text() == "Tú: recuerda esto"
    assert second_window.message_list.item(1).text() == "Sirius: Respuesta simulada de Sirius."


@pytest.mark.gui
def test_empty_or_blank_input_is_rejected(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    window.message_input.setText("   ")
    window.send_button.click()

    assert window.message_list.count() == 0
    assert window._is_sending is False


@pytest.mark.gui
def test_double_send_is_blocked_while_an_operation_is_in_progress(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    window.message_input.setText("primero")
    window.send_button.click()
    assert window.send_button.isEnabled() is False

    # A second click while sending must not queue a second worker/message.
    window.message_input.setText("segundo, mientras se envía el primero")
    window.send_button.click()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    # Only "primero" and its reply were ever persisted.
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["primero", "Respuesta simulada de Sirius."]


@pytest.mark.gui
def test_status_label_shows_and_clears_while_sending(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.status_label.text() == ""

    window.message_input.setText("hola")
    window.send_button.click()
    assert window.status_label.text() != ""

    qtbot.waitUntil(lambda: window.status_label.text() == "", timeout=5000)


@pytest.mark.gui
def test_cancel_button_is_visible_only_during_an_operation(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.show()

    assert window.cancel_button.isVisible() is False

    window.message_input.setText("hola")
    window.send_button.click()
    assert window.cancel_button.isVisible() is True

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)
    assert window.cancel_button.isVisible() is False


@pytest.mark.gui
def test_provider_failure_shows_a_clear_error_and_persists_the_failed_reply(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """A provider failure is a normal (non-crashing) outcome: the SIRIUS
    message is persisted as FAILED, with whatever partial text streamed
    (here none), and stays visible for traceability — it is never removed.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _swap_send_message_use_case(window, database_path, _FailingLLMProvider())

    window.message_input.setText("hola")
    window.send_button.click()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.error_label.text() != ""
    assert "no se pudo contactar" not in window.error_label.text()
    assert window.message_list.count() == 2
    assert window.message_list.item(0).text() == "Tú: hola"
    assert window.message_list.item(1).text() == "Sirius:  (fallido)"

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["hola", ""]
    assert [m.status for m in persisted] == [MessageStatus.COMPLETED, MessageStatus.FAILED]


@pytest.mark.gui
def test_persistence_failure_shows_a_clear_error_and_keeps_only_the_user_message(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    real_conversation_repository = build_sqlite_conversation_repository(database_path)
    failing_repository = _FailOnNthAppendConversationRepository(
        real_conversation_repository, fail_on_call=2
    )
    _swap_send_message_use_case(window, database_path, FakeLLMProvider(), failing_repository)

    window.message_input.setText("hola")
    window.send_button.click()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.error_label.text() != ""
    conversation = real_conversation_repository.get_or_create_main_conversation()
    persisted = real_conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["hola"]
    assert window.message_list.count() == 1
    assert window.message_list.item(0).text() == "Tú: hola"


@pytest.mark.gui
def test_first_persistence_failure_removes_the_optimistic_message(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    real_conversation_repository = build_sqlite_conversation_repository(database_path)
    failing_repository = _FailOnNthAppendConversationRepository(
        real_conversation_repository, fail_on_call=1
    )
    _swap_send_message_use_case(window, database_path, FakeLLMProvider(), failing_repository)

    window.message_input.setText("esto nunca se guarda")
    window.send_button.click()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.error_label.text() != ""
    assert window.message_list.count() == 0

    conversation = real_conversation_repository.get_or_create_main_conversation()
    persisted = real_conversation_repository.list_messages(conversation.id)
    assert persisted == []


@pytest.mark.gui
def test_clicking_cancel_stops_the_stream_and_reconciles_the_interface(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)
    assert window.message_list.item(1).text() == "Sirius: parcial"

    window.cancel_button.click()
    provider.release()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    # The cancelled partial text is never treated as a completed answer, but
    # SIRIUS-ARQ-0.1 S5.1 requires it to be conserved and shown, clearly
    # marked as cancelled, for traceability.
    assert window.error_label.text() != ""
    assert window.message_list.count() == 2
    assert window.message_list.item(0).text() == "Tú: hola"
    assert window.message_list.item(1).text() == "Sirius: parcial (cancelado)"

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["hola", "parcial"]
    assert [m.status for m in persisted] == [MessageStatus.COMPLETED, MessageStatus.CANCELLED]


@pytest.mark.gui
def test_clicking_cancel_twice_is_safe(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)

    window.cancel_button.click()
    assert window.cancel_button.isEnabled() is False
    window.cancel_button.click()  # a second click must be a harmless no-op

    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["hola", "parcial"]


@pytest.mark.gui
def test_closing_while_streaming_requests_cancellation_and_closes_once_done(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.show()
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)

    window.close()  # must return immediately: the close is deferred, not blocked

    # The window is still open right after close(): the GUI thread was never
    # blocked waiting, and cancellation was requested instead of killing
    # anything.
    assert window.isVisible() is True
    assert window._close_requested is True

    provider.release()
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=5000)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["hola", "parcial"]


@pytest.mark.gui
def test_send_worker_reference_is_retained_while_blocked_and_released_on_completion(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Mirrors the QThreadPool GC pitfall already guarded against for backup
    workers: without a strong Python-level reference to the in-flight
    SendMessageWorker, a fast-finishing QRunnable can be garbage-collected
    before its queued cross-thread signal is delivered, silently losing the
    result.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)

    assert window._active_send_worker is None

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)

    # The send is genuinely blocked mid-stream: the reference must still be held.
    assert window._active_send_worker is not None

    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window._active_send_worker is None
    assert window.message_list.item(1).text() == "Sirius: parcial completo"

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["hola", "parcial completo"]
    assert [m.status for m in persisted] == [MessageStatus.COMPLETED, MessageStatus.COMPLETED]


@pytest.mark.gui
def test_legitimately_empty_history_loads_without_error(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")

    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.message_list.count() == 0
    assert window.error_label.text() == ""
