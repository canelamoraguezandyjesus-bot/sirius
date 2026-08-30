from datetime import UTC, datetime

import pytest

from sirius.application.decision_origin import DecisionOriginNotFoundError, GetDecisionOriginUseCase
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.event import DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, Event


def _decision(source_event_id: int | None) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=1,
        decision_id=1,
        version=1,
        content="Usar SQLite local en vez de un servidor remoto.",
        source_event_id=source_event_id,
        created_at=now,
    )
    return Decision(
        id=1,
        subject="Motor de persistencia",
        project_id=7,
        status=DecisionStatus.PROPOSED,
        current_revision=revision,
        created_at=now,
        updated_at=now,
    )


def _event(event_id: int = 5, message_id: int | None = None) -> Event:
    return Event(
        id=event_id,
        event_type=DECISION_PROPOSED_EVENT_TYPE,
        actor=USER_ACTOR,
        message_id=message_id,
        created_at=datetime.now(UTC),
        redacted_at=None,
    )


def _message(message_id: int = 3, content: str = "propongo usar SQLite local") -> Message:
    return Message(
        id=message_id,
        conversation_id=1,
        sequence=1,
        role=MessageRole.USER,
        content=content,
        created_at=datetime.now(UTC),
    )


class _StaticDecisionRepository:
    def __init__(self, decision: Decision | None) -> None:
        self._decision = decision

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("get_origin() must never create a proposal")

    def get_decision(self, decision_id: int) -> Decision:
        if self._decision is None:
            msg = f"Unknown decision id: {decision_id}"
            raise ValueError(msg)
        return self._decision

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("get_origin() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("get_origin() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("get_origin() must never list decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("get_origin() must never read a superseding decision")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("get_origin() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("get_origin() must never list archived decisions")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("get_origin() must never list proposed decisions")

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("get_origin() must never set a category")

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError("get_origin() must never set a category")

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError("get_origin() must never list uncategorized decisions")


class _StaticEventRepository:
    def __init__(self, event: Event | None) -> None:
        self._event = event

    def append(self, event_type: str, actor: str, message_id: int | None) -> Event:
        raise AssertionError("get_origin() must never append an event")

    def get_source(self, event_id: int) -> Event | None:
        return self._event


class _StaticConversationRepository:
    def __init__(self, message: Message | None) -> None:
        self._message = message
        self.queried_message_ids: list[int] = []

    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("get_origin() must never create a conversation")

    def get_main_conversation(self) -> Conversation | None:
        raise AssertionError("get_origin() must never read the conversation")

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
        raise AssertionError("get_origin() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        raise AssertionError("get_origin() must never list messages")

    def get_message(self, message_id: int) -> Message | None:
        self.queried_message_ids.append(message_id)
        return self._message

    def redact_message(self, message_id: int) -> Message:
        raise AssertionError("get_origin() must never redact a message")


def test_get_origin_raises_for_an_unknown_decision_id() -> None:
    use_case = GetDecisionOriginUseCase(
        _StaticDecisionRepository(None),
        _StaticEventRepository(None),
        _StaticConversationRepository(None),
    )

    with pytest.raises(DecisionOriginNotFoundError):
        use_case.get_origin(999)


def test_get_origin_raises_when_the_current_revision_has_no_recorded_origin() -> None:
    use_case = GetDecisionOriginUseCase(
        _StaticDecisionRepository(_decision(source_event_id=None)),
        _StaticEventRepository(None),
        _StaticConversationRepository(None),
    )

    with pytest.raises(DecisionOriginNotFoundError):
        use_case.get_origin(1)


def test_get_origin_raises_when_the_source_event_no_longer_exists() -> None:
    use_case = GetDecisionOriginUseCase(
        _StaticDecisionRepository(_decision(source_event_id=5)),
        _StaticEventRepository(None),
        _StaticConversationRepository(None),
    )

    with pytest.raises(DecisionOriginNotFoundError):
        use_case.get_origin(1)


def test_get_origin_exposes_subject_project_status_version_date_and_origin() -> None:
    conversation_repository = _StaticConversationRepository(_message())
    use_case = GetDecisionOriginUseCase(
        _StaticDecisionRepository(_decision(source_event_id=5)),
        _StaticEventRepository(_event(event_id=5, message_id=3)),
        conversation_repository,
    )

    origin = use_case.get_origin(1)

    assert origin.subject == "Motor de persistencia"
    assert origin.project_id == 7
    assert origin.status is DecisionStatus.PROPOSED
    assert origin.version == 1
    assert origin.created_at is not None
    assert origin.event_id == 5
    assert origin.event_type == DECISION_PROPOSED_EVENT_TYPE
    assert origin.actor == USER_ACTOR
    assert origin.message_id == 3
    assert origin.message_content == "propongo usar SQLite local"
    assert conversation_repository.queried_message_ids == [3]


def test_get_origin_without_a_source_message_leaves_message_content_none() -> None:
    conversation_repository = _StaticConversationRepository(None)
    use_case = GetDecisionOriginUseCase(
        _StaticDecisionRepository(_decision(source_event_id=5)),
        _StaticEventRepository(_event(event_id=5, message_id=None)),
        conversation_repository,
    )

    origin = use_case.get_origin(1)

    assert origin.message_id is None
    assert origin.message_content is None
    assert conversation_repository.queried_message_ids == []


def test_get_origin_handles_a_dangling_message_reference_safely() -> None:
    use_case = GetDecisionOriginUseCase(
        _StaticDecisionRepository(_decision(source_event_id=5)),
        _StaticEventRepository(_event(event_id=5, message_id=3)),
        _StaticConversationRepository(None),
    )

    origin = use_case.get_origin(1)

    assert origin.message_id == 3
    assert origin.message_content is None
