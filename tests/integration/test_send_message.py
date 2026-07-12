from collections.abc import Iterable
from pathlib import Path

import pytest

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
from sirius.application.context import ContextBuilder
from sirius.application.send_message import SendMessageUseCase
from sirius.domain.conversation import Conversation, Message, MessageRole
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.llm import LLMChunk, LLMProvider, LLMRequest


class _RaisingLLMProvider:
    """Test double: always fails, to exercise the provider-failure path."""

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMChunk]:
        del request
        raise RuntimeError("simulated provider failure")

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

    def stream_response(self, request: LLMRequest) -> Iterable[LLMChunk]:
        del request
        yield LLMChunk(text=self._fixed_reply)

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

    def append_message(self, conversation_id: int, role: MessageRole, content: str) -> Message:
        self._calls += 1
        if self._calls == self._fail_on_call:
            msg = "simulated persistence failure"
            raise RuntimeError(msg)
        return self._delegate.append_message(conversation_id, role, content)

    def list_messages(self, conversation_id: int) -> list[Message]:
        return self._delegate.list_messages(conversation_id)


def _seed_bootstrap_singletons(database_path: Path) -> None:
    """Mimic initialize_persistence(): ContextBuilder itself never seeds these."""
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_project_repository(database_path).get_or_create_active_project()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()


def _build_use_case(database_path: Path, llm_provider: LLMProvider) -> SendMessageUseCase:
    Base.metadata.create_all(build_engine(database_path))
    _seed_bootstrap_singletons(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        memory_repository=build_sqlite_memory_repository(database_path),
        conversation_repository=conversation_repository,
    )
    return SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=conversation_repository,
        llm_provider=llm_provider,
    )


@pytest.mark.integration
def test_send_message_invokes_the_fake_provider_and_persists_both_messages(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    result = use_case.send_message("hola Sirius")

    assert result.user_message.role is MessageRole.USER
    assert result.user_message.content == "hola Sirius"
    assert result.sirius_message.role is MessageRole.SIRIUS
    assert result.sirius_message.content == "Respuesta simulada de Sirius."
    assert result.user_message.sequence == 1
    assert result.sirius_message.sequence == 2


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
def test_send_message_works_with_any_injected_llm_provider(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _StaticLLMProvider("otra respuesta"))

    result = use_case.send_message("hola")

    assert result.sirius_message.content == "otra respuesta"


@pytest.mark.integration
def test_send_message_keeps_the_user_message_when_the_provider_fails(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _RaisingLLMProvider())

    with pytest.raises(RuntimeError, match="simulated provider failure"):
        use_case.send_message("hola")

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    messages = conversation_repository.list_messages(conversation.id)

    assert [m.content for m in messages] == ["hola"]
    assert [m.role for m in messages] == [MessageRole.USER]


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
        use_case.send_message("hola")

    messages = real_conversation_repository.list_messages(
        real_conversation_repository.get_or_create_main_conversation().id
    )
    assert [m.content for m in messages] == ["hola"]
    assert [m.role for m in messages] == [MessageRole.USER]
