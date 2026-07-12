"""Composition root for the desktop application.

Wires the SQLite adapters and ``FakeLLMProvider`` into the application layer's
use cases, producing exactly what ``MainWindow`` needs. This module is the
only place, outside tests, allowed to know about both the persistence
adapters and the LLM provider on one side and the presentation layer's
dependency shape on the other: ``MainWindow`` itself must never import
SQLAlchemy, a SQLite adapter, or an LLM provider directly (AGENTS.md: "la
interfaz no accede directamente a SQLite ni al proveedor LLM").
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.context import ContextBuilder
from sirius.application.get_conversation_history import GetConversationHistoryUseCase
from sirius.application.send_message import SendMessageUseCase


@dataclass(frozen=True, slots=True)
class ConversationDependencies:
    """Everything ``MainWindow`` needs to drive the conversation tab, already wired."""

    send_message_use_case: SendMessageUseCase
    get_history_use_case: GetConversationHistoryUseCase


def build_conversation_dependencies(database_path: Path) -> ConversationDependencies:
    """Build repositories and use cases wired to the local SQLite database.

    Uses ``FakeLLMProvider`` exclusively (V6A); wiring a real provider later
    only requires changing this function, never ``presentation`` or
    ``application``.
    """
    conversation_repository = build_sqlite_conversation_repository(database_path)
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        memory_repository=build_sqlite_memory_repository(database_path),
        conversation_repository=conversation_repository,
    )
    send_message_use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=conversation_repository,
        llm_provider=FakeLLMProvider(),
    )
    get_history_use_case = GetConversationHistoryUseCase(conversation_repository)

    return ConversationDependencies(
        send_message_use_case=send_message_use_case,
        get_history_use_case=get_history_use_case,
    )
