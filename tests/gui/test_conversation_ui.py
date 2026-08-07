import itertools
import threading
from collections.abc import Iterable
from pathlib import Path

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import (
    QApplication,
    QStyledItemDelegate,
    QTextEdit,
)
from pytestqt.qtbot import QtBot

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
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
from sirius.presentation.error_messages import describe_error
from sirius.presentation.main_window import MainWindow
from sirius.presentation.message_view import MessageItemDelegate, MessageItemWidget


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path) -> Path:
    """Mimic initialize_persistence(): schema + the three canonical singletons,
    plus a configured active project (B3c): ContextBuilder requires one."""
    upgrade_to_head(database_path)
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
    """Test double: always fails before any delta, to exercise the provider-failure path."""

    def __init__(self, kind: LLMErrorKind = LLMErrorKind.CONNECTION) -> None:
        self._kind = kind

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMError(kind=self._kind, message="no se pudo contactar")

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _CrashingLLMProvider:
    """Test double: raises before yielding anything, to exercise the
    ``_on_crashed`` (unexpected worker exception) path rather than the
    normal ``LLMError`` outcome."""

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        msg = "simulated provider crash"
        raise RuntimeError(msg)
        yield  # pragma: no cover - makes this a generator function

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


class _BlockingMarkdownProvider:
    """Test double like ``_BlockingUntilReleasedProvider``, but the delta and
    final text contain Markdown syntax, to deterministically observe B8a's
    plain-text-while-streaming/rendered-once-finished behavior."""

    def __init__(self) -> None:
        self._continue_event = threading.Event()

    def health_check(self) -> bool:
        return True

    def release(self) -> None:
        self._continue_event.set()

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMTextDelta(text="**uno** ")
        self._continue_event.wait(timeout=5)
        yield LLMCompleted(text="**uno** dos", input_tokens=1, output_tokens=2)

    def cancel(self, operation_id: str) -> None:
        del operation_id


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
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    rank_relevant_knowledge_use_case = RankRelevantKnowledgeUseCase(
        memory_repository=memory_repository,
        decision_repository=decision_repository,
        project_repository=project_repository,
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
    )
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=project_repository,
        memory_repository=memory_repository,
        conversation_repository=repository,
        decision_repository=decision_repository,
        rank_relevant_knowledge_use_case=rank_relevant_knowledge_use_case,
        event_repository=build_sqlite_event_repository(database_path),
        token_counter=CharacterHeuristicTokenCounter(),
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
    assert window.error_label.text().startswith(describe_error(LLMErrorKind.CONNECTION))
    assert window.message_list.count() == 2
    assert window.message_list.item(0).text() == "Tú: hola"
    assert window.message_list.item(1).text() == "Sirius:  (fallido)"

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["hola", ""]
    assert [m.status for m in persisted] == [MessageStatus.COMPLETED, MessageStatus.FAILED]


@pytest.mark.gui
@pytest.mark.parametrize("kind", list(LLMErrorKind))
def test_each_llm_error_kind_shows_its_actionable_message(
    qtbot: QtBot, tmp_path: Path, kind: LLMErrorKind
) -> None:
    """B7a (RF-028): every ``LLMErrorKind`` reaches the interface as the
    matching actionable message from ``error_messages.describe_error``,
    never the provider's raw (potentially unsafe) ``LLMError.message``
    (RNF-018), and keeps the support reference."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _swap_send_message_use_case(window, database_path, _FailingLLMProvider(kind=kind))

    window.message_input.setText("hola")
    window.send_button.click()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    operation_id = conversation_repository.list_messages(conversation.id)[-1].operation_id

    assert window.error_label.text() == f"{describe_error(kind)} (ref: {operation_id})"
    assert "no se pudo contactar" not in window.error_label.text()


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

    # An unclassified crash (no LLMErrorKind available) still gets the safe
    # generic message from the same helper, not the raw exception text.
    assert window.error_label.text().startswith(describe_error(None))
    assert "simulated persistence failure" not in window.error_label.text()
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
    # marked as cancelled, for traceability. B7a only changes the FAILED
    # branch — CANCELLED keeps its own text unchanged.
    assert window.error_label.text() == "Envío cancelado."
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


# --- B7b: reintentar un envío fallido sin reescribirlo (D-05) --------------


@pytest.mark.gui
def test_retry_button_is_hidden_by_default(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.retry_button.isVisible() is False


@pytest.mark.gui
def test_failed_send_shows_retry_and_retrying_resends_the_same_text_under_a_new_operation_id(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.show()
    _swap_send_message_use_case(window, database_path, _FailingLLMProvider())

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.retry_button.isVisible() is True
    assert window._last_failed_text == "hola"

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    first_operation_id = conversation_repository.list_messages(conversation.id)[-1].operation_id

    # The retry reuses the normal send path with a working provider: it must
    # resend "hola" unchanged, under a brand-new operation_id, without the
    # user retyping anything, and hide "Reintentar" again once it succeeds.
    _swap_send_message_use_case(window, database_path, FakeLLMProvider())
    window.retry_button.click()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.retry_button.isVisible() is False
    assert window._last_failed_text is None

    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == [
        "hola",
        "",
        "hola",
        "Respuesta simulada de Sirius.",
    ]
    assert [m.status for m in persisted] == [
        MessageStatus.COMPLETED,
        MessageStatus.FAILED,
        MessageStatus.COMPLETED,
        MessageStatus.COMPLETED,
    ]
    assert persisted[-1].operation_id != first_operation_id
    assert window.message_list.count() == 4
    assert window.message_list.item(0).text() == "Tú: hola"
    assert window.message_list.item(1).text() == "Sirius:  (fallido)"
    assert window.message_list.item(2).text() == "Tú: hola"
    assert window.message_list.item(3).text() == "Sirius: Respuesta simulada de Sirius."


@pytest.mark.gui
def test_crashed_send_shows_retry_and_retrying_resends_the_same_text(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.show()
    _swap_send_message_use_case(window, database_path, _CrashingLLMProvider())

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.retry_button.isVisible() is True
    assert window._last_failed_text == "hola"

    _swap_send_message_use_case(window, database_path, FakeLLMProvider())
    window.retry_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.retry_button.isVisible() is False
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    persisted = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in persisted] == ["hola", "hola", "Respuesta simulada de Sirius."]


@pytest.mark.gui
def test_cancelled_send_never_shows_retry(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)

    window.cancel_button.click()
    provider.release()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.error_label.text() == "Envío cancelado."
    assert window.retry_button.isVisible() is False
    assert window._last_failed_text is None


@pytest.mark.gui
def test_starting_a_new_send_clears_a_pending_retry(qtbot: QtBot, tmp_path: Path) -> None:
    """Typing and sending a new message clears any failed-attempt state
    still pending, even though the new send does not itself fail."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.show()
    _swap_send_message_use_case(window, database_path, _FailingLLMProvider())

    window.message_input.setText("primero")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)
    assert window.retry_button.isVisible() is True

    _swap_send_message_use_case(window, database_path, FakeLLMProvider())
    window.message_input.setText("segundo")
    window.send_button.click()

    # The pending retry is cleared as soon as the new send starts, not only
    # once it finishes.
    assert window.retry_button.isVisible() is False
    assert window._last_failed_text is None

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)
    assert window.retry_button.isVisible() is False


@pytest.mark.gui
def test_retry_button_is_hidden_while_sending(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)

    assert window.retry_button.isVisible() is False

    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)


# --- B8a: renderizado de Markdown seguro en la conversación (D-06, RF-008, SP-07) ---


def _widget_at(window: MainWindow, index: int) -> MessageItemWidget:
    item = window.message_list.item(index)
    widget = window.message_list.itemWidget(item)
    assert isinstance(widget, MessageItemWidget)
    return widget


@pytest.mark.gui
def test_markdown_content_renders_instead_of_literal_syntax(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    markdown_content = (
        "# Título\n\n**negrita** y *cursiva*\n\n- uno\n- dos\n\n"
        "`codigo en linea`\n\n```\nbloque de codigo\n```"
    )
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, markdown_content)

    window = _build_window(database_path)
    qtbot.addWidget(window)

    rendered = _widget_at(window, 0).rendered_plain_text()
    assert "# Título" not in rendered
    assert "**negrita**" not in rendered
    assert "`codigo en linea`" not in rendered
    assert "Título" in rendered
    assert "negrita" in rendered
    assert "codigo en linea" in rendered
    assert "uno" in rendered
    assert "bloque de codigo" in rendered

    html = _widget_at(window, 0).rendered_html()
    assert "font-weight:700" in html


@pytest.mark.gui
def test_html_and_script_content_is_shown_literal_and_never_interpreted(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """SP-07: untrusted content is never active HTML — it is always escaped."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    unsafe_content = 'Hola <script>alert(1)</script> y <b onclick="doEvil()">falso</b>.'
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, unsafe_content)

    window = _build_window(database_path)
    qtbot.addWidget(window)

    widget = _widget_at(window, 0)
    rendered = widget.rendered_plain_text()
    assert "<script>alert(1)</script>" in rendered
    assert '<b onclick="doEvil()">falso</b>' in rendered

    html = widget.rendered_html()
    assert "<script>" not in html
    assert "<b onclick=" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


@pytest.mark.gui
def test_streaming_shows_literal_text_and_final_result_renders_as_markdown(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """The in-flight delta shows unrendered Markdown syntax (plain text, B8a's
    allowed simplification); once the provider completes, the same text is
    consolidated into safe, rendered Markdown. A real ``threading.Event``
    (mirroring ``_BlockingUntilReleasedProvider``) makes the mid-stream state
    deterministically observable instead of racing the worker thread.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingMarkdownProvider()
    _swap_send_message_use_case(window, database_path, provider)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)
    qtbot.waitUntil(lambda: _widget_at(window, 1).rendered_plain_text() == "**uno** ", timeout=5000)

    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    final_rendered = _widget_at(window, 1).rendered_plain_text()
    assert "**uno**" not in final_rendered
    assert "uno dos" in final_rendered


@pytest.mark.gui
def test_failed_status_suffix_is_preserved_in_the_rendered_widget(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _swap_send_message_use_case(window, database_path, _FailingLLMProvider())

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert "(fallido)" in _widget_at(window, 1).rendered_plain_text()


@pytest.mark.gui
def test_cancelled_status_suffix_is_preserved_in_the_rendered_widget(
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

    window.cancel_button.click()
    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert "(cancelado)" in _widget_at(window, 1).rendered_plain_text()


@pytest.mark.gui
def test_redacted_message_placeholder_is_preserved_in_the_rendered_widget(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    message = conversation_repository.append_message(conversation.id, MessageRole.USER, "secreto")
    conversation_repository.redact_message(message.id)

    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert "(mensaje redactado)" in _widget_at(window, 0).rendered_plain_text()


# --- B8b: bloques de código copiables (D-06, RF-008, cierre de D-06 junto a B8a) ---


class _BlockingCodeBlockProvider:
    """Like ``_BlockingMarkdownProvider``, but the delta/final text is a single
    fenced code block, to observe deterministically that streaming still shows
    it as unrendered plain text and the finished result segments it (B8b)."""

    _TEXT = "```\ncodigo en streaming\n```"

    def __init__(self) -> None:
        self._continue_event = threading.Event()

    def health_check(self) -> bool:
        return True

    def release(self) -> None:
        self._continue_event.set()

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMTextDelta(text=self._TEXT)
        self._continue_event.wait(timeout=5)
        yield LLMCompleted(text=self._TEXT, input_tokens=1, output_tokens=2)

    def cancel(self, operation_id: str) -> None:
        del operation_id


@pytest.mark.gui
def test_single_code_block_shows_copy_button_and_copies_exact_code(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    content = "Antes del bloque.\n\n```python\ndef f():\n    return 1\n```\n\nDespués del bloque."
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, content)

    window = _build_window(database_path)
    qtbot.addWidget(window)

    widget = _widget_at(window, 0)
    buttons = widget.copy_buttons()
    assert len(buttons) == 1

    buttons[0].click()
    clipboard = QApplication.clipboard()
    assert clipboard is not None
    assert clipboard.text() == "def f():\n    return 1"


@pytest.mark.gui
def test_multiple_code_blocks_each_show_own_copy_button_and_copy_independently(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    content = (
        "Primero:\n\n```\nprimer bloque\n```\n\nSegundo:\n\n```js\nsegundo bloque\n```\n\nFin."
    )
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, content)

    window = _build_window(database_path)
    qtbot.addWidget(window)

    widget = _widget_at(window, 0)
    buttons = widget.copy_buttons()
    assert len(buttons) == 2

    clipboard = QApplication.clipboard()
    assert clipboard is not None

    buttons[0].click()
    assert clipboard.text() == "primer bloque"

    buttons[1].click()
    assert clipboard.text() == "segundo bloque"


@pytest.mark.gui
def test_message_without_code_block_shows_no_copy_button(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    content = "# Título\n\n**negrita** y `codigo en linea`, sin ningún bloque cercado."
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, content)

    window = _build_window(database_path)
    qtbot.addWidget(window)

    widget = _widget_at(window, 0)
    assert widget.copy_buttons() == []
    rendered = widget.rendered_plain_text()
    assert "Título" in rendered
    assert "negrita" in rendered
    assert "codigo en linea" in rendered


@pytest.mark.gui
def test_prose_order_is_preserved_around_code_blocks(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    content = "antes\n\n```\nmedio\n```\n\ndespues"
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, content)

    window = _build_window(database_path)
    qtbot.addWidget(window)

    rendered = _widget_at(window, 0).rendered_plain_text()
    assert rendered.index("antes") < rendered.index("medio") < rendered.index("despues")


@pytest.mark.gui
def test_html_and_script_inside_code_block_is_shown_literal_and_never_interpreted(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """SP-07 also holds inside a fenced code block: shown/copied literal, never
    interpreted, even though the code block is not part of B8a's Markdown flow."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    unsafe_code = '<script>alert(1)</script>\n<b onclick="doEvil()">falso</b>'
    content = f"```\n{unsafe_code}\n```"
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, content)

    window = _build_window(database_path)
    qtbot.addWidget(window)

    widget = _widget_at(window, 0)
    buttons = widget.copy_buttons()
    assert len(buttons) == 1

    rendered = widget.rendered_plain_text()
    assert "<script>alert(1)</script>" in rendered
    assert '<b onclick="doEvil()">falso</b>' in rendered

    html = widget.rendered_html()
    assert "<script>" not in html
    assert "<b onclick=" not in html

    buttons[0].click()
    clipboard = QApplication.clipboard()
    assert clipboard is not None
    assert clipboard.text() == unsafe_code


@pytest.mark.gui
def test_streaming_final_result_segments_code_block_with_copy_button(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingCodeBlockProvider()
    _swap_send_message_use_case(window, database_path, provider)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)
    qtbot.waitUntil(
        lambda: _widget_at(window, 1).rendered_plain_text() == "```\ncodigo en streaming\n```",
        timeout=5000,
    )
    # B8a: no segmentation while streaming, so no "Copiar" button appears yet.
    assert _widget_at(window, 1).copy_buttons() == []

    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    widget = _widget_at(window, 1)
    buttons = widget.copy_buttons()
    assert len(buttons) == 1
    final_rendered = widget.rendered_plain_text()
    assert "```" not in final_rendered


# --- Bugfix: el historial debe poder leerse por completo (defecto ALTO,
# reproducido en el ejecutable empaquetado) ---
#
# Cubre los seis defectos reportados: mensajes solapados, texto oculto,
# mensajes recortados con puntos suspensivos, tener que copiar el texto fuera
# de Sirius para leerlo, el chat reducido a una franja por los paneles
# secundarios, y el historial ilegible tras cerrar y reabrir.


def _wait_for_real_layout(qtbot: QtBot, window: MainWindow) -> None:
    """Force the message list to receive a real (non-zero) column width
    before measuring row geometry.

    Without this, every ``_MessageBody`` would still be using its
    construction-time width fallback, and the exact race this suite guards
    against (ancho ficticio al construir vs. ancho real de la columna) would
    never be exercised.
    """
    window.resize(900, 600)
    window.show()
    qtbot.waitUntil(lambda: window.message_list.viewport().width() > 0, timeout=5000)
    QApplication.processEvents()


def _row_rects(window: MainWindow) -> list[QRect]:
    return [
        window.message_list.visualItemRect(window.message_list.item(index))
        for index in range(window.message_list.count())
    ]


def _assert_rows_do_not_overlap_in_chronological_order(window: MainWindow) -> None:
    """Every row must start at or below the bottom of the previous row, in the
    same order as the underlying (chronological) list: no vertical overlap
    and no row rendered out of order."""
    rects = _row_rects(window)
    for previous, current in itertools.pairwise(rects):
        assert previous.height() > 0
        assert current.y() >= previous.y() + previous.height(), (
            f"la fila en y={current.y()} se solapa con la fila anterior "
            f"(y={previous.y()}, alto={previous.height()})"
        )


@pytest.mark.gui
def test_two_consecutive_messages_do_not_overlap(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "uno")
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, "dos")

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    assert window.message_list.count() == 2
    _assert_rows_do_not_overlap_in_chronological_order(window)


@pytest.mark.gui
def test_long_message_increases_its_row_height(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "corto")
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, "palabra " * 400)

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    rects = _row_rects(window)
    assert rects[1].height() > rects[0].height()
    _assert_rows_do_not_overlap_in_chronological_order(window)


@pytest.mark.gui
def test_user_and_sirius_messages_render_in_distinct_blocks(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "pregunta")
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, "respuesta")

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    assert window.message_list.item(0).text() == "Tú: pregunta"
    assert window.message_list.item(1).text() == "Sirius: respuesta"
    assert window.message_list.item(0).font().bold() is False
    assert window.message_list.item(1).font().bold() is True
    _assert_rows_do_not_overlap_in_chronological_order(window)


@pytest.mark.gui
def test_visual_order_matches_chronological_order(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    for index, text in enumerate(["uno", "dos", "tres", "cuatro", "cinco"]):
        role = MessageRole.USER if index % 2 == 0 else MessageRole.SIRIUS
        conversation_repository.append_message(conversation.id, role, text)

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    tops = [rect.y() for rect in _row_rects(window)]
    assert tops == sorted(tops)
    assert len(set(tops)) == len(tops)
    _assert_rows_do_not_overlap_in_chronological_order(window)


@pytest.mark.gui
def test_scroll_area_contains_every_message(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    for index in range(30):
        role = MessageRole.USER if index % 2 == 0 else MessageRole.SIRIUS
        conversation_repository.append_message(conversation.id, role, f"mensaje numero {index}")

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    assert window.message_list.count() == 30
    _assert_rows_do_not_overlap_in_chronological_order(window)

    scrollbar = window.message_list.verticalScrollBar()
    assert scrollbar.maximum() > 0

    scrollbar.setValue(scrollbar.maximum())
    last_rect = window.message_list.visualItemRect(window.message_list.item(29))
    assert window.message_list.viewport().rect().intersects(last_rect)


@pytest.mark.gui
def test_streaming_message_grows_without_overlapping_neighbours(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)
    qtbot.waitUntil(lambda: _widget_at(window, 1).rendered_plain_text() == "parcial", timeout=5000)
    mid_stream_height = _row_rects(window)[1].height()
    _assert_rows_do_not_overlap_in_chronological_order(window)

    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)
    _assert_rows_do_not_overlap_in_chronological_order(window)
    assert _row_rects(window)[1].height() >= mid_stream_height

    # A message that arrives once the stream has finished must not be
    # invaded by the (now taller) row it grew into just before.
    _swap_send_message_use_case(window, database_path, FakeLLMProvider())
    window.message_input.setText("otra vez")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 4, timeout=5000)
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)
    _assert_rows_do_not_overlap_in_chronological_order(window)


@pytest.mark.gui
def test_reloading_the_conversation_still_has_no_overlap(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    first_window = _build_window(database_path)
    qtbot.addWidget(first_window)
    first_window.message_input.setText("mensaje antes de cerrar " + "palabra " * 60)
    first_window.send_button.click()
    qtbot.waitUntil(lambda: first_window.send_button.isEnabled(), timeout=5000)
    first_window.close()

    second_window = _build_window(database_path)
    qtbot.addWidget(second_window)
    _wait_for_real_layout(qtbot, second_window)

    assert second_window.message_list.count() == 2
    _assert_rows_do_not_overlap_in_chronological_order(second_window)


@pytest.mark.gui
def test_failed_message_and_its_retry_remain_legible_and_do_not_overlap(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)
    _swap_send_message_use_case(window, database_path, _FailingLLMProvider())

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)
    assert window.retry_button.isVisible() is True
    _assert_rows_do_not_overlap_in_chronological_order(window)

    _swap_send_message_use_case(window, database_path, FakeLLMProvider())
    window.retry_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.message_list.count() == 4
    assert window.message_list.item(0).text() == "Tú: hola"
    assert window.message_list.item(1).text() == "Sirius:  (fallido)"
    assert window.message_list.item(2).text() == "Tú: hola"
    assert window.message_list.item(3).text() == "Sirius: Respuesta simulada de Sirius."
    _assert_rows_do_not_overlap_in_chronological_order(window)


def _body_of(window: MainWindow, index: int) -> QTextEdit:
    """El primer cuerpo de texto del mensaje en ``index``."""
    bodies = _widget_at(window, index)._segment_bodies
    assert bodies, "el mensaje no tiene ningún cuerpo de texto"
    return bodies[0]


def _document_height(window: MainWindow, index: int) -> int:
    return int(_body_of(window, index).document().size().height())


def _ink_in_row_without_widget(window: MainWindow, index: int) -> int:
    """Píxeles distintos del fondo que pinta la FILA, sin contar su widget.

    Oculta momentáneamente el ``MessageItemWidget`` y cuenta lo que queda
    dibujado en el rectángulo de la fila. Es la única forma de comprobar de
    verdad que la lista no está pintando además el texto del item por debajo
    del widget transparente, que era el origen del texto duplicado y de la
    elipsis.
    """
    message_list = window.message_list
    item = message_list.item(index)
    widget = message_list.itemWidget(item)
    widget.setVisible(False)
    QApplication.processEvents()
    try:
        image = message_list.viewport().grab().toImage()
        rect = message_list.visualItemRect(item)
        background = image.pixel(1, 1)
        ink = 0
        for y in range(max(0, rect.top()), min(image.height(), rect.bottom())):
            for x in range(max(0, rect.left()), min(image.width(), rect.right())):
                if image.pixel(x, y) != background:
                    ink += 1
        return ink
    finally:
        widget.setVisible(True)
        QApplication.processEvents()


@pytest.mark.gui
def test_a_long_message_shows_all_of_its_content(qtbot: QtBot, tmp_path: Path) -> None:
    """Defecto 2: parte del texto quedaba oculta.

    El alto asignado a la fila debe cubrir el alto real del documento, y el
    texto renderizado debe contener tanto el principio como el final.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    content = "PRINCIPIO. " + ("relleno intermedio. " * 300) + "FINAL."
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, content)

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    rendered = _widget_at(window, 0).rendered_plain_text()
    assert "PRINCIPIO." in rendered
    assert "FINAL." in rendered

    body = _body_of(window, 0)
    assert body.height() >= _document_height(window, 0)
    assert window.message_list.item(0).sizeHint().height() >= _document_height(window, 0)


@pytest.mark.gui
def test_no_ellipsis_or_artificial_truncation_is_rendered(qtbot: QtBot, tmp_path: Path) -> None:
    """Defecto 3: los mensajes salían recortados con puntos suspensivos.

    La causa era el delegate por omisión, que pintaba el texto del item en una
    sola línea recortada (``ElideRight``) bajo el widget transparente. El texto
    del item se conserva para accesibilidad, pero ya no se pinta.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    content = "frase larga sin cortes " * 200
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, content)

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    delegate = window.message_list.itemDelegate()
    assert isinstance(delegate, MessageItemDelegate)
    assert window.message_list.textElideMode() is Qt.TextElideMode.ElideNone

    rendered = _widget_at(window, 0).rendered_plain_text()
    assert "…" not in rendered
    assert "..." not in rendered
    # El texto del item sigue completo: es el contrato de accesibilidad.
    assert len(window.message_list.item(0).text()) > 1000

    # Y sobre todo: la fila no pinta NADA de ese texto. Se mide en píxeles
    # reales, no en el valor intermedio de la opción de estilo: la primera
    # versión de este arreglo vaciaba option.text y llamaba a super().paint(),
    # que vuelve a llamar a initStyleOption y repuebla el texto, así que
    # aparentaba funcionar sin funcionar.
    assert _ink_in_row_without_widget(window, 0) == 0

    # Contraprueba: con el delegate por omisión, ese mismo texto sí se pinta.
    window.message_list.setItemDelegate(QStyledItemDelegate(window.message_list))
    QApplication.processEvents()
    assert _ink_in_row_without_widget(window, 0) > 0


@pytest.mark.gui
def test_resizing_the_window_recomputes_widths_and_heights(qtbot: QtBot, tmp_path: Path) -> None:
    """Un chat más estrecho necesita más líneas para el mismo texto."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(
        conversation.id, MessageRole.SIRIUS, "texto que reflui" + "r" * 20 + " " + "palabra " * 200
    )

    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.resize(1200, 700)
    window.show()
    qtbot.waitUntil(lambda: window.message_list.viewport().width() > 0, timeout=5000)
    QApplication.processEvents()

    wide_width = window.message_list.viewport().width()
    wide_height = window.message_list.item(0).sizeHint().height()

    window.resize(700, 700)
    QApplication.processEvents()
    qtbot.waitUntil(lambda: window.message_list.viewport().width() < wide_width, timeout=5000)
    QApplication.processEvents()

    narrow_width = window.message_list.viewport().width()
    narrow_height = window.message_list.item(0).sizeHint().height()

    assert narrow_width < wide_width
    assert narrow_height > wide_height
    assert narrow_height >= _document_height(window, 0)
    _assert_rows_do_not_overlap_in_chronological_order(window)


@pytest.mark.gui
def test_conversation_starts_with_more_space_than_the_side_panel(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Defecto 5: la conversación es la superficie principal de Sirius."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    sizes = window.conversation_splitter.sizes()
    assert len(sizes) == 2
    conversation_width, side_width = sizes
    assert conversation_width > side_width
    assert conversation_width > sum(sizes) / 2
    # El panel lateral no puede volver a comerse la columna del chat.
    assert window.side_panel_scroll.maximumWidth() <= 420


@pytest.mark.gui
def test_shrinking_the_side_panel_gives_the_chat_more_room(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    before = window.message_list.width()
    total = sum(window.conversation_splitter.sizes())
    window.conversation_splitter.setSizes([total, 0])
    QApplication.processEvents()

    assert window.message_list.width() > before


@pytest.mark.gui
def test_a_long_reply_can_be_read_in_full_without_copying_it_out(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Defecto 4: para leer una respuesta había que copiarla fuera de Sirius.

    Con el historial desplazado hasta el final, la última línea de una
    respuesta extensa tiene que quedar dentro del viewport, y el recorrido
    entre el principio y el final del mensaje debe ser posible sin salir de la
    aplicación.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    content = "PRIMERA LINEA.\n\n" + ("parrafo intermedio. " * 400) + "\n\nULTIMA LINEA."
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, content)

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    # Todo el texto está en el widget, no hace falta copiarlo a ningún sitio.
    rendered = _widget_at(window, 0).rendered_plain_text()
    assert "PRIMERA LINEA." in rendered
    assert "ULTIMA LINEA." in rendered

    # El cuerpo no tiene barra propia: su alto iguala al del documento, así que
    # nada queda recortado dentro del mensaje.
    body = _body_of(window, 0)
    assert body.verticalScrollBarPolicy() is Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert body.height() >= _document_height(window, 0)

    # El historial sí permite recorrer el mensaje de arriba abajo.
    scrollbar = window.message_list.verticalScrollBar()
    assert scrollbar.maximum() > 0
    scrollbar.setValue(scrollbar.maximum())
    QApplication.processEvents()
    row = window.message_list.visualItemRect(window.message_list.item(0))
    viewport = window.message_list.viewport().rect()
    assert row.bottom() <= viewport.bottom() + 1
    scrollbar.setValue(0)
    QApplication.processEvents()
    assert window.message_list.verticalScrollBar().value() == 0


@pytest.mark.gui
def test_opening_the_history_starts_at_the_last_message(qtbot: QtBot, tmp_path: Path) -> None:
    """Defecto 6: al reabrir, la conversación reciente parecía no estar."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    for index in range(25):
        role = MessageRole.USER if index % 2 == 0 else MessageRole.SIRIUS
        conversation_repository.append_message(conversation.id, role, f"mensaje {index}")

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    scrollbar = window.message_list.verticalScrollBar()
    assert scrollbar.maximum() > 0
    assert scrollbar.value() >= scrollbar.maximum() - 8
    _assert_rows_do_not_overlap_in_chronological_order(window)


@pytest.mark.gui
def test_scrolling_up_stops_the_history_from_following_new_messages(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """El seguimiento del final no debe robarle la vista a quien está leyendo."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    for index in range(25):
        conversation_repository.append_message(
            conversation.id, MessageRole.USER, f"mensaje {index}"
        )

    window = _build_window(database_path)
    qtbot.addWidget(window)
    _wait_for_real_layout(qtbot, window)

    window.message_list.verticalScrollBar().setValue(0)
    QApplication.processEvents()
    assert window._follow_history_bottom is False

    _swap_send_message_use_case(window, database_path, FakeLLMProvider())
    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    # La vista sigue arriba: no se le ha movido al usuario.
    assert window.message_list.verticalScrollBar().value() == 0
    _assert_rows_do_not_overlap_in_chronological_order(window)
