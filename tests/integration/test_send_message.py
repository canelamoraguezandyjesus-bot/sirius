from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.models import DecisionModel, MessageModel
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
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.age import care_block
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.context import Context, ContextBuilder
from sirius.application.presence import HEADING, RULE
from sirius.application.project_continuity import ProjectContinuityUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.send_message import (
    ChatLeavesThisComputer,
    SendMessageUseCase,
    render_instructions,
)
from sirius.application.sight_log import HEADING as SEEN_HEADING
from sirius.application.sight_log import INTRO as SEEN_INTRO
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import DecisionStatus
from sirius.domain.memory import MemoryStatus
from sirius.domain.project import is_configured
from sirius.ports.age import AgeReading
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
from sirius.ports.project_repository import ProjectRepository


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

    def __init__(self, fixed_reply: str, *, memory_suggestion: str | None = None) -> None:
        self._fixed_reply = fixed_reply
        self._memory_suggestion = memory_suggestion

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMTextDelta(text=self._fixed_reply)
        yield LLMCompleted(
            text=self._fixed_reply,
            input_tokens=1,
            output_tokens=len(self._fixed_reply),
            memory_suggestion=self._memory_suggestion,
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

    def get_message(self, message_id: int) -> Message | None:
        return self._delegate.get_message(message_id)

    def redact_message(self, message_id: int) -> Message:
        return self._delegate.redact_message(message_id)


def _seed_bootstrap_singletons(database_path: Path) -> None:
    """Mimic initialize_persistence() plus a configured active project:
    ContextBuilder requires one (B3c), and neither it nor SendMessageUseCase
    ever creates one as a side effect. Idempotent across repeated calls
    against the same database — several tests reopen the store and call this
    again through ``_build_use_case``.
    """
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    active_project = project_repository.get_active_project()
    if active_project is None or not is_configured(active_project):
        project_repository.create_project(
            "Proyecto de prueba",
            "Objetivo de prueba",
            state_summary="estado inicial",
            blockers=(),
            next_step="siguiente paso inicial",
        )
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()


def _build_context_builder(
    database_path: Path,
    conversation_repository: ConversationRepository,
    project_repository: ProjectRepository | None = None,
) -> ContextBuilder:
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    project_repository = project_repository or build_sqlite_project_repository(database_path)
    rank_relevant_knowledge_use_case = RankRelevantKnowledgeUseCase(
        memory_repository=memory_repository,
        decision_repository=decision_repository,
        project_repository=project_repository,
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
    )
    return ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=project_repository,
        memory_repository=memory_repository,
        conversation_repository=conversation_repository,
        decision_repository=decision_repository,
        rank_relevant_knowledge_use_case=rank_relevant_knowledge_use_case,
        event_repository=build_sqlite_event_repository(database_path),
        token_counter=CharacterHeuristicTokenCounter(),
    )


def _build_use_case(
    database_path: Path,
    llm_provider: LLMProvider,
    conversation_repository: ConversationRepository | None = None,
) -> SendMessageUseCase:
    upgrade_to_head(database_path)
    _seed_bootstrap_singletons(database_path)
    repository = conversation_repository or build_sqlite_conversation_repository(database_path)
    context_builder = _build_context_builder(database_path, repository)
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
def test_solo_en_este_ordenador_no_guarda_ni_envia_nada_a_un_modelo_de_fuera(
    tmp_path: Path,
) -> None:
    # Ronda 10 de Codex sobre la PR #687: la voz del robot pide que nada salga, y se
    # comprueba el mismo modelo con el que se enviaría. `_StaticLLMProvider` no dice que
    # se quede aquí, así que cuenta como de fuera.
    database_path = tmp_path / "sirius.db"
    preguntas: list[LLMRequest] = []

    class _DeFuera(_StaticLLMProvider):
        def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
            preguntas.append(request)
            return super().stream_response(request)

    use_case = _build_use_case(database_path, _DeFuera("contestada fuera"))

    with pytest.raises(ChatLeavesThisComputer):
        use_case.send_message("mi secreto", only_on_this_computer=True)

    assert preguntas == []
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    assert conversation_repository.list_messages(conversation.id) == []


@pytest.mark.integration
def test_solo_en_este_ordenador_envia_con_el_modelo_que_comprobo_aunque_cambie(
    tmp_path: Path,
) -> None:
    # El mismo cambio de la ronda 10, más tarde: Configuración pasa la charla a un
    # modelo de fuera mientras se prepara el turno, ya comprobado el de aquí.
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    _seed_bootstrap_singletons(database_path)
    repository = build_sqlite_conversation_repository(database_path)
    contexto = _build_context_builder(database_path, repository)
    preguntas_fuera: list[LLMRequest] = []

    class _DeFuera(_StaticLLMProvider):
        def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
            preguntas_fuera.append(request)
            return super().stream_response(request)

    class _CambiaElModeloMientrasLoPrepara:
        def build(self, current_user_message: str) -> Context:
            use_case.set_llm_provider(_DeFuera("contestada fuera"))
            return contexto.build(current_user_message)

    use_case = SendMessageUseCase(
        context_builder=cast(ContextBuilder, _CambiaElModeloMientrasLoPrepara()),
        conversation_repository=repository,
        llm_provider=FakeLLMProvider(),
    )

    result = use_case.send_message("mi secreto", only_on_this_computer=True)

    assert preguntas_fuera == []
    assert result.sirius_message.content == "Respuesta simulada de Sirius."


@pytest.mark.integration
def test_solo_en_este_ordenador_envia_con_un_modelo_de_aqui(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    result = use_case.send_message("hola", only_on_this_computer=True)

    assert result.outcome is MessageStatus.COMPLETED


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
def test_send_message_never_creates_memory_as_a_side_effect(tmp_path: Path) -> None:
    """B4a, RF-019/PA-010: memory is created only by an explicit save order,
    never automatically by an ordinary conversation turn."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    use_case.send_message("recuerda que prefiero respuestas breves")

    memory_repository = build_sqlite_memory_repository(database_path)
    assert memory_repository.list_current_memories() == []


@pytest.mark.integration
def test_send_message_never_creates_or_approves_a_decision_as_a_side_effect(
    tmp_path: Path,
) -> None:
    """B4b, RF-020/PA-011: debating or exploring alternatives in an ordinary
    conversation turn never creates or approves a decision — only an
    explicit call to ``ProposeDecisionUseCase``/``ApproveDecisionUseCase``
    can, and ``SendMessageUseCase`` never calls either."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    use_case.send_message("deberíamos usar SQLite o un servidor remoto, debatamos las opciones")

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        assert session.scalars(select(DecisionModel)).first() is None


@pytest.mark.integration
def test_send_message_never_corrects_a_memory_as_a_side_effect(tmp_path: Path) -> None:
    """B4c, RF-022: a memory is corrected only by an explicit call to
    ``CorrectMemoryUseCase``, never automatically by an ordinary
    conversation turn discussing or restating it."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("El usuario prefiere respuestas breves")

    use_case.send_message("en realidad prefiero respuestas detalladas")

    memory_repository = build_sqlite_memory_repository(database_path)
    unchanged = memory_repository.get_memory(memory.id)
    assert unchanged.current_revision.version == 1
    assert unchanged.current_revision.content == "El usuario prefiere respuestas breves"


@pytest.mark.integration
def test_send_message_never_supersedes_a_decision_as_a_side_effect(tmp_path: Path) -> None:
    """B4c, RF-023: a decision is superseded only by an explicit call to
    ``SupersedeDecisionUseCase``, never automatically by an ordinary
    conversation turn debating a replacement."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())
    project_repository = build_sqlite_project_repository(database_path)
    project = project_repository.get_active_project()
    assert project is not None
    unit_of_work = build_sqlite_unit_of_work(database_path)
    approved = ApproveDecisionUseCase(unit_of_work).approve(
        ProposeDecisionUseCase(unit_of_work)
        .propose("Motor de persistencia", project.id, "Usar SQLite local")
        .id,
        confirmed=True,
    )

    use_case.send_message("deberíamos sustituir esa decisión por PostgreSQL")

    decision_repository = build_sqlite_decision_repository(database_path)
    unchanged = decision_repository.get_decision(approved.id)
    assert unchanged.status is DecisionStatus.APPROVED
    assert unchanged.supersedes_decision_id is None
    assert decision_repository.get_superseding_decision(approved.id) is None


@pytest.mark.integration
def test_send_message_never_archives_or_deletes_a_memory_as_a_side_effect(
    tmp_path: Path,
) -> None:
    """B4d, RF-024/RF-025: a memory is archived or deleted only by an
    explicit call to ``ArchiveMemoryUseCase``/``DeleteMemoryUseCase``, never
    automatically by an ordinary conversation turn discussing it."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("El usuario prefiere respuestas breves")

    use_case.send_message("olvida lo que dije antes, ya no importa")

    memory_repository = build_sqlite_memory_repository(database_path)
    unchanged = memory_repository.get_memory(memory.id)

    assert unchanged.status is MemoryStatus.CURRENT
    assert unchanged.current_revision.content == "El usuario prefiere respuestas breves"


@pytest.mark.integration
def test_send_message_never_archives_a_decision_as_a_side_effect(tmp_path: Path) -> None:
    """B4d, RF-024: a decision is archived only by an explicit call to
    ``ArchiveDecisionUseCase``, never automatically by an ordinary
    conversation turn."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())
    project_repository = build_sqlite_project_repository(database_path)
    project = project_repository.get_active_project()
    assert project is not None
    unit_of_work = build_sqlite_unit_of_work(database_path)
    approved = ApproveDecisionUseCase(unit_of_work).approve(
        ProposeDecisionUseCase(unit_of_work)
        .propose("Motor de persistencia", project.id, "Usar SQLite local")
        .id,
        confirmed=True,
    )

    use_case.send_message("esa decisión ya no aplica, archívala")

    decision_repository = build_sqlite_decision_repository(database_path)
    unchanged = decision_repository.get_decision(approved.id)
    assert unchanged.status is DecisionStatus.APPROVED
    assert decision_repository.list_archived_decisions() == []


@pytest.mark.integration
def test_send_message_never_creates_resolves_or_approves_a_precedence_conflict(
    tmp_path: Path,
) -> None:
    """B4e, RF-026/PA-014/DR-011: an ordinary conversation turn never
    creates, corrects, resolves, or approves a memory or a decision, so it
    can never create or silently resolve a precedence conflict either — no
    call site in ``SendMessageUseCase`` reaches
    ``sirius.domain.precedence`` or ``DetectPrecedenceConflictsUseCase``."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())
    project_repository = build_sqlite_project_repository(database_path)
    project = project_repository.get_active_project()
    assert project is not None
    unit_of_work = build_sqlite_unit_of_work(database_path)
    save_memory = SaveManualMemoryUseCase(unit_of_work).save
    first = save_memory(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project.id
    )
    second = save_memory(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project.id
    )

    use_case.send_message("deberíamos resolver esa contradicción sobre el motor de persistencia")

    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    assert memory_repository.get_memory(first.id).status is MemoryStatus.CURRENT
    assert memory_repository.get_memory(second.id).status is MemoryStatus.CURRENT
    assert decision_repository.list_current_decisions() == []


@pytest.mark.integration
def test_send_message_uses_context_built_from_current_identity_and_project(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    result = use_case.send_message("hola")

    assert result.context is not None
    assert result.context.identity.current_version.name == "Sirius"
    assert result.context.current_user_message == "hola"


@pytest.mark.integration
def test_send_message_context_reflects_a_project_continuity_update(tmp_path: Path) -> None:
    """B3b: state/blockers/next step updated via ProjectContinuityUseCase flow
    into the very next context sent to the (simulated) provider."""
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project_repository.create_project(
        "Sirius 0.1",
        "Cerrar B3b",
        state_summary="estado inicial",
        blockers=(),
        next_step="siguiente paso inicial",
    )
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    ProjectContinuityUseCase(project_repository).update(
        "estado actualizado", "bloqueo pendiente", "siguiente paso actualizado"
    )

    context_builder = _build_context_builder(
        database_path, build_sqlite_conversation_repository(database_path), project_repository
    )
    use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=build_sqlite_conversation_repository(database_path),
        llm_provider=FakeLLMProvider(),
    )
    result = use_case.send_message("hola")

    assert result.context is not None
    instructions = render_instructions(result.context)
    assert "Nombre: Sirius 0.1" in instructions
    assert "Estado: estado actualizado" in instructions
    assert "Bloqueos: bloqueo pendiente" in instructions
    assert "Siguiente paso: siguiente paso actualizado" in instructions


@pytest.mark.integration
def test_send_message_records_operation_id_and_identity_version(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider())

    result = use_case.send_message("hola", operation_id="op-123")

    assert result.user_message.operation_id == "op-123"
    assert result.sirius_message.operation_id == "op-123"
    assert result.user_message.identity_version is None
    assert result.context is not None
    assert result.sirius_message.identity_version == result.context.identity.current_version.version


@pytest.mark.integration
def test_send_message_reports_deltas_in_order_via_on_delta(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider(chunks=("uno ", "dos ", "tres")))
    received: list[str] = []

    result = use_case.send_message("hola", on_delta=received.append)

    # Los trozos son los que da el filtro de los gestos: un blanco del final espera a lo que
    # sigue, por si va delante de una etiqueta (ADR-261). Juntos dicen lo mismo.
    assert received == ["uno", " dos", " tres"]
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

    assert received == ["uno", " dos"]
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

    assert result.context is not None
    recent_contents = [m.content for m in result.context.recent_messages]
    assert "empezando..." not in recent_contents  # the FAILED Sirius reply is excluded
    assert "primero" in recent_contents  # the user's own message is COMPLETED and stays


@pytest.mark.integration
def test_send_message_keeps_only_the_user_message_when_persisting_the_reply_fails(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    _seed_bootstrap_singletons(database_path)
    real_conversation_repository = build_sqlite_conversation_repository(database_path)
    failing_repository = _FailOnNthAppendConversationRepository(
        real_conversation_repository, fail_on_call=2
    )
    context_builder = _build_context_builder(database_path, real_conversation_repository)
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
    upgrade_to_head(database_path)
    _seed_bootstrap_singletons(database_path)
    real_conversation_repository = build_sqlite_conversation_repository(database_path)
    failing_repository = _FailOnNthAppendConversationRepository(
        real_conversation_repository, fail_on_call=2
    )
    context_builder = _build_context_builder(database_path, real_conversation_repository)
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
        context_builder=_build_context_builder(database_path, reopened_repository),
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
    upgrade_to_head(database_path)
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


@pytest.mark.integration
def test_send_message_mirrors_the_memory_suggestion_when_the_turn_completes_with_one(
    tmp_path: Path,
) -> None:
    """SIRIUS-ARQ-0.2 §3.2/§3.6 (M6): the mirror field is a verbatim copy of
    ``LLMCompleted.memory_suggestion`` — ``SendMessageUseCase`` transports it
    without interpreting it or calling ``ProposeMemorySuggestionUseCase``
    itself (that decision belongs to the interface surface, never here)."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(
        database_path,
        _StaticLLMProvider("respuesta", memory_suggestion="recuerda esto"),
    )

    result = use_case.send_message("hola")

    assert result.outcome is MessageStatus.COMPLETED
    assert result.memory_suggestion == "recuerda esto"


@pytest.mark.integration
def test_send_message_mirror_is_none_when_the_provider_proposes_nothing(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _StaticLLMProvider("respuesta"))

    result = use_case.send_message("hola")

    assert result.outcome is MessageStatus.COMPLETED
    assert result.memory_suggestion is None


@pytest.mark.integration
def test_send_message_mirror_is_none_for_a_failed_turn_even_if_a_completed_double_would_carry_one(
    tmp_path: Path,
) -> None:
    """Only ``outcome is COMPLETED`` ever copies the mirror field (§3.2):
    ``LLMCancelled``/``LLMError`` carry no ``memory_suggestion`` field at all
    — there is nothing to copy, and the mirror stays ``None``."""
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _FailAfterDeltasProvider())

    result = use_case.send_message("hola")

    assert result.outcome is MessageStatus.FAILED
    assert result.memory_suggestion is None


class _ModeloConNombre(FakeLLMProvider):
    """Un modelo de mentira con nombre, que apunta a quién le piden cancelar."""

    def __init__(self, nombre: str, chunks: Iterable[str] = ("uno ", "dos ", "tres")) -> None:
        super().__init__(chunks=chunks)
        self.model_name = nombre
        self.cancelados: list[str] = []

    def cancel(self, operation_id: str) -> None:
        self.cancelados.append(operation_id)
        super().cancel(operation_id)


class _Apuntador:
    """Hace de marcas y de resumen: apunta el modelo con que se atribuye y se resume."""

    def __init__(self) -> None:
        self.atribuidas: list[str | None] = []
        self.resumidas_con: list[object] = []
        self.resumidas_tras: list[str | None] = []

    def record_model(self, message_id: int, model: str | None) -> None:
        self.atribuidas.append(model)

    def maybe_summarize(
        self, conversation_id: int, provider: object, operation_id: str | None = None
    ) -> bool:
        self.resumidas_con.append(provider)
        self.resumidas_tras.append(operation_id)
        return False


def _con_modelo_que_cambia(
    tmp_path: Path, antes: _ModeloConNombre
) -> tuple[SendMessageUseCase, _Apuntador]:
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    _seed_bootstrap_singletons(database_path)
    repository = build_sqlite_conversation_repository(database_path)
    apuntador = _Apuntador()
    use_case = SendMessageUseCase(
        context_builder=_build_context_builder(database_path, repository),
        conversation_repository=repository,
        llm_provider=antes,
        reply_marks=apuntador,  # type: ignore[arg-type]
        summary_service=apuntador,  # type: ignore[arg-type]
    )
    return use_case, apuntador


@pytest.mark.integration
def test_si_la_charla_cambia_de_modelo_a_mitad_esa_respuesta_sigue_con_el_suyo(
    tmp_path: Path,
) -> None:
    """Ronda 3 de Codex: elegir otro modelo con una respuesta en curso no puede hacer
    que esa respuesta se atribuya o se resuma con el nuevo."""
    antes = _ModeloConNombre("modelo-de-antes")
    despues = _ModeloConNombre("modelo-de-despues")
    use_case, apuntador = _con_modelo_que_cambia(tmp_path, antes)

    def cambia_a_mitad(texto: str) -> None:
        if texto.strip() == "uno":
            use_case.set_llm_provider(despues)

    result = use_case.send_message("hola", on_delta=cambia_a_mitad)

    assert result.outcome is MessageStatus.COMPLETED
    assert apuntador.atribuidas == ["modelo-de-antes"]
    assert apuntador.resumidas_con == [antes]
    assert use_case.llm_provider is despues


@pytest.mark.integration
def test_cancelar_tras_cambiar_de_modelo_para_la_respuesta_que_va_en_curso(
    tmp_path: Path,
) -> None:
    """Ronda 3 de Codex: cancelar tiene que llegar al modelo que está contestando,
    no al nuevo, o la petición de antes seguiría saliendo y costando."""
    antes = _ModeloConNombre("modelo-de-antes")
    despues = _ModeloConNombre("modelo-de-despues")
    use_case, _ = _con_modelo_que_cambia(tmp_path, antes)

    def cambia_y_cancela(texto: str) -> None:
        if texto.strip() == "uno":
            use_case.set_llm_provider(despues)
            use_case.cancel("op-a-mitad")

    result = use_case.send_message("hola", operation_id="op-a-mitad", on_delta=cambia_y_cancela)

    assert result.outcome is MessageStatus.CANCELLED
    assert antes.cancelados == ["op-a-mitad"]
    assert despues.cancelados == []


@pytest.mark.integration
def test_avisa_de_que_acabo_bien_con_la_respuesta_guardada_y_antes_de_resumir(
    tmp_path: Path,
) -> None:
    """ADR-243: la voz del robot dice lo que le quedaba en cuanto la respuesta acaba, sin
    esperar al resumen de la charla, que pide otra respuesta al modelo y puede tardar."""
    use_case, apuntador = _con_modelo_que_cambia(tmp_path, _ModeloConNombre("modelo"))
    repositorio = build_sqlite_conversation_repository(tmp_path / "sirius.db")
    vistos: list[tuple[list[str | None], int, int]] = []

    def acabo() -> None:
        charla = repositorio.get_or_create_main_conversation()
        guardados = [m.content for m in repositorio.list_messages(charla.id)]
        vistos.append((guardados, len(apuntador.atribuidas), len(apuntador.resumidas_con)))

    result = use_case.send_message("hola", on_completed=acabo)

    assert result.outcome is MessageStatus.COMPLETED
    assert vistos == [(["hola", "uno dos tres"], 0, 0)]
    assert (len(apuntador.atribuidas), len(apuntador.resumidas_con)) == (1, 1)


@pytest.mark.integration
def test_si_la_respuesta_no_acaba_bien_no_avisa_de_que_acabo(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, _FailAfterDeltasProvider())
    acabadas: list[str] = []

    result = use_case.send_message("hola", on_completed=lambda: acabadas.append("acabó"))

    assert result.outcome is MessageStatus.FAILED
    assert acabadas == []


@pytest.mark.integration
def test_si_la_respuesta_se_cancela_no_avisa_de_que_acabo(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    use_case = _build_use_case(database_path, FakeLLMProvider(chunks=("uno ", "dos ")))
    acabadas: list[str] = []

    result = use_case.send_message(
        "hola",
        operation_id="op-a-medias",
        on_delta=lambda texto: use_case.cancel("op-a-medias"),
        on_completed=lambda: acabadas.append("acabó"),
    )

    assert result.outcome is MessageStatus.CANCELLED
    assert acabadas == []


@pytest.mark.integration
def test_cortarle_por_voz_a_mitad_guarda_lo_escrito_como_respuesta_acabada(
    tmp_path: Path,
) -> None:
    """ADR-254: cortarle por voz no es cancelar el envío. Deja de escribir, como al
    cancelar, pero lo escrito hasta ahí queda como su respuesta, acabada: se le atribuye su
    modelo y el modelo lo lee después. Tras el corte no se resume: lo nuevo no espera."""
    modelo = _ModeloConNombre("modelo-local", chunks=("uno ", "dos ", "tres ", "cuatro"))
    use_case, apuntador = _con_modelo_que_cambia(tmp_path, modelo)
    recibidos: list[str] = []

    def corta_tras_el_segundo(texto: str) -> None:
        recibidos.append(texto)
        if len(recibidos) == 2:
            use_case.cut("op-cortada")

    result = use_case.send_message(
        "hola", operation_id="op-cortada", on_delta=corta_tras_el_segundo
    )

    assert recibidos == ["uno", " dos"]
    # Corta la respuesta y, por si ya resumía, el resumen de ese turno.
    assert modelo.cancelados == ["op-cortada", "resumen-op-cortada"]
    assert result.outcome is MessageStatus.COMPLETED
    assert result.sirius_message.status is MessageStatus.COMPLETED
    assert result.sirius_message.content == "uno dos "
    assert apuntador.atribuidas == ["modelo-local"]
    assert apuntador.resumidas_con == []

    siguiente = use_case.send_message("¿Y qué más?")

    assert siguiente.context is not None
    assert "uno dos " in [m.content for m in siguiente.context.recent_messages]


@pytest.mark.integration
def test_al_acabar_el_turno_mira_si_toca_resumir_con_su_operacion(tmp_path: Path) -> None:
    """ADR-254: el resumen va con la operación del turno, para que cortarle lo corte."""
    modelo = _ModeloConNombre("modelo-local")
    use_case, apuntador = _con_modelo_que_cambia(tmp_path, modelo)

    use_case.send_message("hola", operation_id="op-entera")

    assert apuntador.resumidas_tras == ["op-entera"]


@pytest.mark.integration
def test_si_le_cortan_con_la_respuesta_ya_escrita_no_mira_si_toca_resumir(
    tmp_path: Path,
) -> None:
    """Revisión del corte (ADR-254): le cortan con el modelo ya acabado, mientras dice la
    última frase. La respuesta queda entera, porque acabó, pero no se resume: sería otra
    petición al modelo, y lo nuevo esperaría detrás."""
    modelo = _ModeloConNombre("modelo-local", chunks=("uno ", "dos ", "tres."))
    use_case, apuntador = _con_modelo_que_cambia(tmp_path, modelo)

    result = use_case.send_message(
        "hola", operation_id="op-al-acabar", on_completed=lambda: use_case.cut("op-al-acabar")
    )

    assert result.outcome is MessageStatus.COMPLETED
    assert result.sirius_message.content == "uno dos tres."
    assert apuntador.atribuidas == ["modelo-local"]
    assert apuntador.resumidas_con == []


@pytest.mark.integration
def test_cortarle_antes_de_que_escriba_nada_deja_su_respuesta_vacia_y_acabada(
    tmp_path: Path,
) -> None:
    modelo = _ModeloConNombre("modelo-local")
    use_case, _ = _con_modelo_que_cambia(tmp_path, modelo)

    use_case.cut("op-sin-empezar")
    result = use_case.send_message("hola", operation_id="op-sin-empezar")

    assert result.outcome is MessageStatus.COMPLETED
    assert result.sirius_message.content == ""
    # Y al acabar se olvida que la cortaron: no se queda apuntada para siempre.
    assert not use_case._was_cut("op-sin-empezar")


# --- Quién hay (pieza E de la 0.4, ADR-263) -------------------------------------------


class _ProveedorQueApunta(_StaticLLMProvider):
    """Contesta siempre lo mismo y apunta cada petición, con sus instrucciones."""

    def __init__(self) -> None:
        super().__init__("vale")
        self.peticiones: list[LLMRequest] = []

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(request)
        yield from super().stream_response(request)


def _quien_hay(instrucciones: str) -> list[str]:
    """Las líneas de «# Quién hay», sin el título ni la regla."""
    lineas = instrucciones.splitlines()
    if HEADING not in lineas:
        return []
    desde = lineas.index(HEADING) + 1
    hasta = lineas.index(RULE, desde)
    return lineas[desde:hasta]


@pytest.mark.integration
def test_el_modelo_lee_quien_le_habla_y_a_quienes_tiene_delante(tmp_path: Path) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)
    use_case.set_presence(lambda: ("Pepe", None))

    use_case.send_message("hola", speaker="Marta")

    [peticion] = proveedor.peticiones
    assert _quien_hay(peticion.instructions) == [
        "Te habla Marta.",
        "Tienes delante a Pepe.",
        "Tienes delante a alguien sin identificar.",
    ]
    assert "hola" not in peticion.instructions, "quién hay no se mezcla con lo dicho"


@pytest.mark.integration
def test_lo_escrito_en_la_ventana_no_lleva_quien_lo_escribe(tmp_path: Path) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)
    use_case.set_presence(lambda: ())

    use_case.send_message("hola")

    [peticion] = proveedor.peticiones
    assert _quien_hay(peticion.instructions) == ["No tienes a nadie delante."]


@pytest.mark.integration
def test_sin_vista_ni_quien_hable_no_hay_seccion_de_quien_hay(tmp_path: Path) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)
    use_case.send_message("uno")
    use_case.set_presence(lambda: None)
    use_case.send_message("dos")

    assert all(HEADING not in p.instructions for p in proveedor.peticiones)


@pytest.mark.integration
def test_si_no_se_sabe_quien_hay_se_apunta_una_vez_y_la_charla_sigue(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)

    def rota() -> tuple[str | None, ...] | None:
        msg = "la cámara en /ruta/secreta"
        raise RuntimeError(msg)

    use_case.set_presence(rota)

    primera = use_case.send_message("uno", speaker="Marta")
    use_case.send_message("dos")

    assert primera.outcome is MessageStatus.COMPLETED
    assert _quien_hay(proveedor.peticiones[0].instructions) == ["Te habla Marta."]
    assert HEADING not in proveedor.peticiones[1].instructions
    avisos = [r for r in caplog.records if "No se sabe a quiénes tiene delante" in r.getMessage()]
    assert len(avisos) == 1
    assert "RuntimeError" in avisos[0].getMessage()
    assert "/ruta/secreta" not in caplog.text


# --- Con quién se corta (pieza F de la 0.4, ADR-264) ------------------------------------


def _con_recordatorio(tmp_path: Path, proveedor: LLMProvider) -> SendMessageUseCase:
    """Como ``_build_use_case``, con el recordatorio de la semilla, lo último que lee."""
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    _seed_bootstrap_singletons(database_path)
    repository = build_sqlite_conversation_repository(database_path)
    return SendMessageUseCase(
        context_builder=_build_context_builder(database_path, repository),
        conversation_repository=repository,
        llm_provider=proveedor,
        reminder="El recordatorio de la semilla.",
    )


@pytest.mark.integration
def test_con_un_crio_delante_la_peticion_lleva_la_regla_tras_quien_hay_y_antes_del_recordatorio(
    tmp_path: Path,
) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _con_recordatorio(tmp_path, proveedor)
    use_case.set_presence(lambda: (None, None))
    use_case.set_ages(lambda: (AgeReading(40, sure=True), AgeReading(8, sure=True)))

    use_case.send_message("hola", speaker="Marta")

    [peticion] = proveedor.peticiones
    instrucciones = peticion.instructions
    assert instrucciones.count(care_block()) == 1
    assert instrucciones.index(RULE) < instrucciones.index(care_block())
    assert instrucciones.endswith(f"{care_block()}\n\nEl recordatorio de la semilla.")
    assert "hola" not in instrucciones


@pytest.mark.integration
def test_con_solo_adultos_bien_vistos_no_la_lleva_y_con_uno_dudoso_si(tmp_path: Path) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)
    edades: list[tuple[AgeReading | None, ...]] = [
        (AgeReading(40, sure=True), AgeReading(30, sure=True)),
        (AgeReading(40, sure=True), AgeReading(30, sure=False)),
        (AgeReading(40, sure=True), None),
        (AgeReading(70, sure=True),),
    ]
    use_case.set_ages(lambda: edades[len(proveedor.peticiones)])

    for texto in ("uno", "dos", "tres", "cuatro"):
        use_case.send_message(texto)

    assert [care_block() in p.instructions for p in proveedor.peticiones] == [
        False,
        True,
        True,
        True,
    ]


@pytest.mark.integration
def test_sin_vista_o_sin_nadie_delante_no_la_lleva(tmp_path: Path) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)
    use_case.send_message("uno")
    use_case.set_ages(lambda: None)
    use_case.send_message("dos")
    use_case.set_ages(lambda: ())
    use_case.send_message("tres")

    assert all(care_block() not in p.instructions for p in proveedor.peticiones)


@pytest.mark.integration
def test_si_no_se_sabe_la_edad_de_nadie_la_lleva_ante_la_duda_y_se_apunta_una_vez(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)

    def rota() -> tuple[AgeReading | None, ...] | None:
        msg = "la cámara en /ruta/secreta"
        raise RuntimeError(msg)

    use_case.set_ages(rota)

    primera = use_case.send_message("uno")
    use_case.send_message("dos")

    assert primera.outcome is MessageStatus.COMPLETED
    assert all(care_block() in p.instructions for p in proveedor.peticiones)
    avisos = [r for r in caplog.records if "No se sabe la edad" in r.getMessage()]
    assert len(avisos) == 1
    assert "RuntimeError" in avisos[0].getMessage()
    assert "/ruta/secreta" not in caplog.text


# --- Lo que ha visto (pieza G de la 0.4, ADR-265) ---------------------------------------


@pytest.mark.integration
def test_el_modelo_lee_lo_que_ha_visto_antes_de_quien_hay(tmp_path: Path) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)
    use_case.set_presence(lambda: ("Marta",))
    use_case.set_seen(
        lambda: ("A las 18:02 vino Marta.", "A las 18:10 vino alguien sin identificar.")
    )

    use_case.send_message("¿quién ha venido?")

    [peticion] = proveedor.peticiones
    lineas = peticion.instructions.splitlines()
    desde = lineas.index(SEEN_HEADING)
    assert lineas[desde : desde + 4] == [
        SEEN_HEADING,
        SEEN_INTRO,
        "A las 18:02 vino Marta.",
        "A las 18:10 vino alguien sin identificar.",
    ]
    assert desde < lineas.index(HEADING), "lo que vio, antes de quién hay"
    assert "¿quién ha venido?" not in peticion.instructions


@pytest.mark.integration
def test_sin_nada_visto_no_hay_seccion(tmp_path: Path) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)
    use_case.send_message("uno")
    use_case.set_seen(lambda: ())
    use_case.send_message("dos")

    assert all(SEEN_HEADING not in p.instructions for p in proveedor.peticiones)


@pytest.mark.integration
def test_si_no_se_sabe_lo_que_ha_visto_se_apunta_una_vez_y_la_charla_sigue(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    proveedor = _ProveedorQueApunta()
    use_case = _build_use_case(tmp_path / "sirius.db", proveedor)

    def roto() -> tuple[str, ...]:
        msg = "Marta, en /ruta/secreta"
        raise RuntimeError(msg)

    use_case.set_seen(roto)

    primera = use_case.send_message("uno")
    use_case.send_message("dos")

    assert primera.outcome is MessageStatus.COMPLETED
    assert all(SEEN_HEADING not in p.instructions for p in proveedor.peticiones)
    avisos = [r for r in caplog.records if "No se sabe lo que ha visto" in r.getMessage()]
    assert len(avisos) == 1
    assert "RuntimeError" in avisos[0].getMessage()
    assert "/ruta/secreta" not in caplog.text
