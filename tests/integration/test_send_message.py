from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import Base, MessageModel
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.context import ContextBuilder
from sirius.application.send_message import SendMessageUseCase
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.llm import (
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMProvider,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)


class _FailBeforeFirstDeltaProvider:
    """Test double: fails immediately, before any text delta."""

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMError(kind=LLMErrorKind.CONNECTION, message="no se pudo contactar")

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _FailAfterDeltasProvider:
    """Test double: yields a couple of deltas, then fails."""

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMTextDelta(text="empez")
        yield LLMTextDelta(text="ando...")
        yield LLMError(
            kind=LLMErrorKind.TIMEOUT, message="tardó demasiado", partial_text="empezando..."
        )

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _StaticLLMProvider:
    """A minimal, hand-written LLMProvider — not FakeLLMProvider — proving
    SendMessageUseCase only depends on the port, never on a concrete adapter.
    """

    def __init__(self, fixed_reply: str) -> None:
        self._fixed_reply = fixed_reply

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMTextDelta(text=self._fixed_reply)
        yield LLMCompleted(
            text=self._fixed_reply, input_tokens=1, output_tokens=len(self._fixed_reply)
        )

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


def _seed_bootstrap_singletons(database_path: Path) -> None:
    """Mimic initialize_persistence(): ContextBuilder itself never seeds these."""
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_project_repository(database_path).get_or_create_active_project()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()


def _build_use_case(
    database_path: Path,
    llm_provider: LLMProvider,
    conversation_repository: ConversationRepository | None = None,
) -> SendMessageUseCase:
    Base.metadata.create_all(build_engine(database_path))
    _seed_bootstrap_singletons(database_path)
    repository = conversation_repository or build_sqlite_conversation_repository(database_path)
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        memory_repository=build_sqlite_memory_repository(database_path),
        conversation_repository=repository,
    )
    return SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=repository,
        llm_provider=llm_provider,
    )


@pytest.mark.integration
def test_send_message_invokes_the_provider_and_persists_both_messages(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    result = use_case.send_message("hola Sirius")

    assert result.outcome is MessageStatus.COMPLETED
    assert result.user_message.role is MessageRole.USER
    assert result.user_message.content == "hola Sirius"
    assert result.user_message.status is MessageStatus.COMPLETED
    assert result.sirius_message.role is MessageRole.SIRIUS
    assert result.sirius_message.content == "Respuesta simulada de Sirius."
    assert result.sirius_message.status is MessageStatus.COMPLETED
    assert result.user_message.sequence == 1
    assert result.sirius_message.sequence == 2


@pytest.mark.integration
def test_set_llm_provider_swaps_the_provider_used_by_a_later_send(tmp_path: Path) -> None:
    """B2a: onboarding activates the real provider in the same run via this
    seam, without rebuilding SendMessageUseCase or its persistence."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _StaticLLMProvider("respuesta original"))

    use_case.set_llm_provider(_StaticLLMProvider("respuesta activada"))
    result = use_case.send_message("hola")

    assert result.sirius_message.content == "respuesta activada"


@pytest.mark.integration
def test_send_message_persists_messages_in_order_in_the_conversation(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    use_case.send_message("primero")

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    messages = conversation_repository.list_messages(conversation.id)

    assert [m.content for m in messages] == ["primero", "Respuesta simulada de Sirius."]
    assert [m.role for m in messages] == [MessageRole.USER, MessageRole.SIRIUS]


@pytest.mark.integration
def test_send_message_uses_context_built_from_current_identity_and_project(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    result = use_case.send_message("hola")

    assert result.context.identity.current_version.name == "Sirius"
    assert result.context.current_user_message == "hola"


@pytest.mark.integration
def test_send_message_records_operation_id_and_identity_version(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    result = use_case.send_message("hola", operation_id="op-123")

    assert result.user_message.operation_id == "op-123"
    assert result.sirius_message.operation_id == "op-123"
    assert result.user_message.identity_version is None
    assert result.sirius_message.identity_version == result.context.identity.current_version.version


@pytest.mark.integration
def test_send_message_reports_deltas_in_order_via_on_delta(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider(chunks=("uno ", "dos ", "tres")))
    received: list[str] = []

    result = use_case.send_message("hola", on_delta=received.append)

    assert received == ["uno ", "dos ", "tres"]
    assert result.sirius_message.content == "uno dos tres"


@pytest.mark.integration
def test_send_message_works_with_any_injected_llm_provider(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _StaticLLMProvider("otra respuesta"))

    result = use_case.send_message("hola")

    assert result.outcome is MessageStatus.COMPLETED
    assert result.sirius_message.content == "otra respuesta"


@pytest.mark.integration
def test_send_message_persists_a_failed_message_with_partial_text_before_any_delta(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _FailBeforeFirstDeltaProvider())

    result = use_case.send_message("hola")

    assert result.outcome is MessageStatus.FAILED
    assert result.error_kind is LLMErrorKind.CONNECTION
    assert result.sirius_message.status is MessageStatus.FAILED
    assert result.sirius_message.content == ""

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    messages = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in messages] == ["hola", ""]
    assert [m.role for m in messages] == [MessageRole.USER, MessageRole.SIRIUS]
    assert [m.status for m in messages] == [MessageStatus.COMPLETED, MessageStatus.FAILED]


@pytest.mark.integration
def test_send_message_persists_a_failed_message_with_the_streamed_partial_text(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _FailAfterDeltasProvider())
    received: list[str] = []

    result = use_case.send_message("hola", on_delta=received.append)

    assert received == ["empez", "ando..."]
    assert result.outcome is MessageStatus.FAILED
    assert result.error_kind is LLMErrorKind.TIMEOUT
    assert result.sirius_message.status is MessageStatus.FAILED
    assert result.sirius_message.content == "empezando..."

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    messages = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in messages] == ["hola", "empezando..."]


@pytest.mark.integration
def test_send_message_cancelled_before_streaming_persists_an_empty_cancelled_message(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    use_case.cancel("op-cancel-early")
    result = use_case.send_message("hola", operation_id="op-cancel-early")

    assert result.outcome is MessageStatus.CANCELLED
    assert result.sirius_message.status is MessageStatus.CANCELLED
    assert result.sirius_message.content == ""

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    messages = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in messages] == ["hola", ""]
    assert [m.status for m in messages] == [MessageStatus.COMPLETED, MessageStatus.CANCELLED]


@pytest.mark.integration
def test_send_message_cancelled_mid_stream_persists_the_partial_text_as_cancelled(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(
        database_path, FakeLLMProvider(chunks=("uno ", "dos ", "tres ", "cuatro"))
    )
    received: list[str] = []

    def _cancel_after_second_delta(text: str) -> None:
        received.append(text)
        if len(received) == 2:
            use_case.cancel("op-cancel-mid")

    result = use_case.send_message(
        "hola", operation_id="op-cancel-mid", on_delta=_cancel_after_second_delta
    )

    assert received == ["uno ", "dos "]
    assert result.outcome is MessageStatus.CANCELLED
    assert result.sirius_message.status is MessageStatus.CANCELLED
    assert result.sirius_message.content == "uno dos "

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    messages = conversation_repository.list_messages(conversation.id)
    assert [m.content for m in messages] == ["hola", "uno dos "]


@pytest.mark.integration
def test_cancelling_repeatedly_is_a_safe_no_op(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    use_case.cancel("op-repeat")
    use_case.cancel("op-repeat")
    use_case.cancel("op-repeat")
    result = use_case.send_message("hola", operation_id="op-repeat")

    assert result.outcome is MessageStatus.CANCELLED


@pytest.mark.integration
def test_cancelled_and_failed_messages_are_excluded_from_a_future_context(
    tmp_path: Path,
) -> None:
    """SIRIUS-ARQ-0.1 S5.1/S5.2: partial messages stay in history for
    traceability but must never feed a future context."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _FailAfterDeltasProvider())
    use_case.send_message("primero")

    completed_use_case = _build_use_case(database_path, FakeLLMProvider())
    result = completed_use_case.send_message("segundo")

    recent_contents = [m.content for m in result.context.recent_messages]
    assert "empezando..." not in recent_contents  # the FAILED Sirius reply is excluded
    assert "primero" in recent_contents  # the user's own message is COMPLETED and stays


@pytest.mark.integration
def test_send_message_keeps_only_the_user_message_when_persisting_the_reply_fails(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    _seed_bootstrap_singletons(database_path)
    real_conversation_repository = build_sqlite_conversation_repository(database_path)
    failing_repository = _FailOnNthAppendConversationRepository(
        real_conversation_repository, fail_on_call=2
    )
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        memory_repository=build_sqlite_memory_repository(database_path),
        conversation_repository=real_conversation_repository,
    )
    use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=failing_repository,
        llm_provider=FakeLLMProvider(),
    )

    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        use_case.send_message("hola", operation_id="op-mid-failure")

    messages = real_conversation_repository.list_messages(
        real_conversation_repository.get_or_create_main_conversation().id
    )
    assert [m.content for m in messages] == ["hola"]
    assert [m.role for m in messages] == [MessageRole.USER]


@pytest.mark.integration
def test_retrying_after_a_mid_operation_persistence_failure_does_not_duplicate_the_user_message(
    tmp_path: Path,
) -> None:
    """Requirement: retrying the same operation_id after a persistence
    failure must never duplicate the USER message. The first attempt fails
    while persisting Sirius's reply (after the user message already made
    it in); the retry, with a healthy repository, must reuse that same USER
    row and record the SIRIUS reply this time.
    """
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    _seed_bootstrap_singletons(database_path)
    real_conversation_repository = build_sqlite_conversation_repository(database_path)
    failing_repository = _FailOnNthAppendConversationRepository(
        real_conversation_repository, fail_on_call=2
    )
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        memory_repository=build_sqlite_memory_repository(database_path),
        conversation_repository=real_conversation_repository,
    )
    failing_use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=failing_repository,
        llm_provider=FakeLLMProvider(),
    )
    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        failing_use_case.send_message("hola", operation_id="op-retry")

    # Reopen the store (a brand-new repository, simulating an app restart)
    # and retry the exact same operation with a healthy repository.
    reopened_repository = build_sqlite_conversation_repository(database_path)
    retry_use_case = SendMessageUseCase(
        context_builder=ContextBuilder(
            identity_repository=build_sqlite_identity_repository(database_path),
            project_repository=build_sqlite_project_repository(database_path),
            memory_repository=build_sqlite_memory_repository(database_path),
            conversation_repository=reopened_repository,
        ),
        conversation_repository=reopened_repository,
        llm_provider=FakeLLMProvider(),
    )

    result = retry_use_case.send_message("hola", operation_id="op-retry")

    assert result.outcome is MessageStatus.COMPLETED
    messages = reopened_repository.list_messages(
        reopened_repository.get_or_create_main_conversation().id
    )
    assert [m.role for m in messages] == [MessageRole.USER, MessageRole.SIRIUS]
    assert [m.content for m in messages] == ["hola", "Respuesta simulada de Sirius."]
    # Still exactly one USER row for this operation_id: the retry reused it.
    user_rows = [m for m in messages if m.role is MessageRole.USER]
    assert len(user_rows) == 1


@pytest.mark.integration
def test_a_cancelled_or_failed_reply_can_be_resent_without_duplicating_the_user_message(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _FailAfterDeltasProvider())
    use_case.send_message("hola", operation_id="op-resend")

    resend_use_case = _build_use_case(database_path, FakeLLMProvider())
    resend_use_case.send_message("hola", operation_id="op-resend")

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    messages = conversation_repository.list_messages(conversation.id)
    user_rows = [m for m in messages if m.role is MessageRole.USER]
    assert len(user_rows) == 1


@pytest.mark.integration
def test_database_rejects_two_sirius_rows_for_the_same_operation_id(tmp_path: Path) -> None:
    """The unique constraint is the ultimate backstop against duplicate
    persistence, independent of the use case's own idempotency pre-check."""
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    _seed_bootstrap_singletons(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()

    session_factory = build_session_factory(build_engine(database_path))
    now = datetime.now(UTC).replace(tzinfo=None)
    with session_scope(session_factory) as session:
        session.add(
            MessageModel(
                conversation_id=conversation.id,
                sequence=1,
                role=MessageRole.SIRIUS,
                content="uno",
                created_at=now,
                operation_id="op-direct-dup",
                status=MessageStatus.COMPLETED,
            )
        )

    with (
        pytest.raises(IntegrityError),
        session_scope(session_factory) as session,
    ):
        session.add(
            MessageModel(
                conversation_id=conversation.id,
                sequence=2,
                role=MessageRole.SIRIUS,
                content="dos",
                created_at=now,
                operation_id="op-direct-dup",
                status=MessageStatus.COMPLETED,
            )
        )
        session.flush()

    messages = conversation_repository.list_messages(conversation.id)
    assert len(messages) == 1
