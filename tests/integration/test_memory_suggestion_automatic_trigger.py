"""M6, SIRIUS-ARQ-0.2 §3.2/§3.6: the automatic memory-suggestion trigger.

Exercises directly the presentation-layer surface that orchestrates sending a
message —``propose_suggestion_if_completed_with_one``, the function
``MainWindow._on_finished`` calls, never ``SendMessageUseCase`` itself
(§0.1.2)— against a real ``send_message_use_case``/``propose_memory_suggestion_use_case``
pair wired by ``build_conversation_dependencies``, with a hand-written test
``LLMProvider`` swapped in via ``set_llm_provider`` that already exposes the
separated port contract (``LLMCompleted.text`` clean,
``LLMCompleted.memory_suggestion`` apart — never the delimiter mixed into
either). No GUI, no Qt widget, is ever built here.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.send_message import SendMessageUseCase
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.domain.conversation import MessageStatus
from sirius.ports.llm import (
    MEMORY_SUGGESTION_DELIMITER,
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMProvider,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)
from sirius.presentation.memory_suggestion_trigger import propose_suggestion_if_completed_with_one


def _bootstrapped_dependencies(tmp_path: Path) -> ConversationDependencies:
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
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


class _CompletedProvider:
    """A well-behaved test double: ``text`` is already clean and
    ``memory_suggestion`` already separated — exactly the contract §3.2
    requires every concrete adapter to uphold before a single event reaches
    ``SendMessageUseCase``."""

    def __init__(self, text: str, *, memory_suggestion: str | None) -> None:
        self._text = text
        self._memory_suggestion = memory_suggestion
        self.calls = 0

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        self.calls += 1
        yield LLMTextDelta(text=self._text)
        yield LLMCompleted(
            text=self._text,
            input_tokens=1,
            output_tokens=len(self._text),
            memory_suggestion=self._memory_suggestion,
        )

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _CancelledAfterDelimiterStartedProvider:
    """A well-behaved test double simulating a turn cancelled right after the
    provider had already produced the delimiter and a raw proposal in its
    underlying output: by the time it reaches this port, per §3.2, that raw
    tail is already gone from ``partial_text``."""

    def __init__(self, visible_text: str) -> None:
        self._visible_text = visible_text
        self.calls = 0

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        self.calls += 1
        yield LLMTextDelta(text=self._visible_text)
        yield LLMCancelled(partial_text=self._visible_text)

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _FailedAfterDelimiterStartedProvider:
    """Same as above, but the turn fails instead of being cancelled."""

    def __init__(self, visible_text: str) -> None:
        self._visible_text = visible_text
        self.calls = 0

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        self.calls += 1
        yield LLMTextDelta(text=self._visible_text)
        yield LLMError(
            kind=LLMErrorKind.CONNECTION,
            message="no se pudo contactar",
            partial_text=self._visible_text,
        )

    def cancel(self, operation_id: str) -> None:
        del operation_id


def _swap_provider(send_message_use_case: SendMessageUseCase, provider: LLMProvider) -> None:
    send_message_use_case.set_llm_provider(provider)


@pytest.mark.integration
def test_completed_with_a_suggestion_proposes_it_exactly_once_and_text_stays_clean(
    tmp_path: Path,
) -> None:
    """Closes CODEX-001: counting calls to propose() alone would accept a
    corrupted persisted/shown text, so this also checks
    ``sirius_message.content`` (persisted) and the ``on_delta`` concatenation
    (shown) are both exactly ``LLMCompleted.text``, with no delimiter or raw
    proposal in either."""
    dependencies = _bootstrapped_dependencies(tmp_path)
    provider = _CompletedProvider("Claro, entendido.", memory_suggestion="prefiere brevedad")
    _swap_provider(dependencies.send_message_use_case, provider)
    received: list[str] = []

    result = dependencies.send_message_use_case.send_message("hola", on_delta=received.append)
    propose_suggestion_if_completed_with_one(
        result, dependencies.propose_memory_suggestion_use_case
    )

    assert provider.calls == 1
    assert result.sirius_message.content == "Claro, entendido."
    assert "".join(received) == "Claro, entendido."
    assert MEMORY_SUGGESTION_DELIMITER not in result.sirius_message.content
    assert MEMORY_SUGGESTION_DELIMITER not in "".join(received)

    pending = dependencies.get_knowledge_overview_use_case.get_overview().pending_suggestions
    assert len(pending) == 1
    assert pending[0].content == "prefiere brevedad"
    assert pending[0].source_event_id is not None


@pytest.mark.integration
def test_completed_without_a_suggestion_proposes_nothing(tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    provider = _CompletedProvider("Respuesta normal.", memory_suggestion=None)
    _swap_provider(dependencies.send_message_use_case, provider)

    result = dependencies.send_message_use_case.send_message("hola")
    propose_suggestion_if_completed_with_one(
        result, dependencies.propose_memory_suggestion_use_case
    )

    assert provider.calls == 1
    pending = dependencies.get_knowledge_overview_use_case.get_overview().pending_suggestions
    assert pending == ()


@pytest.mark.integration
def test_cancelled_turn_proposes_nothing_even_with_a_delimiter_already_started(
    tmp_path: Path,
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    provider = _CancelledAfterDelimiterStartedProvider("Empezando a responder...")
    _swap_provider(dependencies.send_message_use_case, provider)

    result = dependencies.send_message_use_case.send_message("hola")
    propose_suggestion_if_completed_with_one(
        result, dependencies.propose_memory_suggestion_use_case
    )

    assert provider.calls == 1
    assert result.outcome is MessageStatus.CANCELLED
    assert result.sirius_message.status is MessageStatus.CANCELLED
    assert result.sirius_message.content == "Empezando a responder..."
    assert MEMORY_SUGGESTION_DELIMITER not in (result.sirius_message.content or "")
    pending = dependencies.get_knowledge_overview_use_case.get_overview().pending_suggestions
    assert pending == ()


@pytest.mark.integration
def test_failed_turn_proposes_nothing_even_with_a_delimiter_already_started(tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    provider = _FailedAfterDelimiterStartedProvider("Empezando a responder...")
    _swap_provider(dependencies.send_message_use_case, provider)

    result = dependencies.send_message_use_case.send_message("hola")
    propose_suggestion_if_completed_with_one(
        result, dependencies.propose_memory_suggestion_use_case
    )

    assert provider.calls == 1
    assert result.outcome is MessageStatus.FAILED
    assert result.sirius_message.status is MessageStatus.FAILED
    assert result.sirius_message.content == "Empezando a responder..."
    assert MEMORY_SUGGESTION_DELIMITER not in (result.sirius_message.content or "")
    pending = dependencies.get_knowledge_overview_use_case.get_overview().pending_suggestions
    assert pending == ()
