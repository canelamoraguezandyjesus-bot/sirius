"""Composition root for the desktop application.

Wires the SQLite adapters and an LLM provider (fake or OpenAI, see
``sirius.config.llm_provider_settings``) into the application layer's use
cases, producing exactly what ``MainWindow`` needs. This module is the only
place, outside tests, allowed to know about both the persistence adapters
and the LLM provider on one side and the presentation layer's dependency
shape on the other: ``MainWindow`` itself must never import SQLAlchemy, a
SQLite adapter, ``openai``, or any LLM provider directly (AGENTS.md: "la
interfaz no accede directamente a SQLite ni al proveedor LLM").
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openai

from sirius.adapters.llm.budget import BudgetTracker
from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_llm_usage_repository import (
    build_sqlite_llm_usage_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.context import ContextBuilder
from sirius.application.get_conversation_history import GetConversationHistoryUseCase
from sirius.application.send_message import SendMessageUseCase
from sirius.config.llm_provider_settings import (
    LLMProviderConfigurationError,
    LLMProviderKind,
    resolve_openai_api_key,
    resolve_openai_provider_settings,
    resolve_provider_kind,
)
from sirius.ports.llm import LLMProvider


@dataclass(frozen=True, slots=True)
class ConversationDependencies:
    """Everything ``MainWindow`` needs to drive the conversation tab, already wired."""

    send_message_use_case: SendMessageUseCase
    get_history_use_case: GetConversationHistoryUseCase


def _build_llm_provider(database_path: Path) -> LLMProvider:
    """Build the LLM provider selected by ``SIRIUS_LLM_PROVIDER`` (default: fake).

    Provisional until V7: the OpenAI API key is read only from
    ``OPENAI_API_KEY`` and never persisted anywhere. If "openai" is selected
    without a usable key or model, this raises a clear, safe, typed error
    instead of silently falling back or attempting a call. Only "fake" and
    "openai" are ever valid; ``resolve_provider_kind`` itself raises for
    anything else (never a silent fallback).

    The SDK's own retry loop is disabled (``max_retries=0``): the adapter
    already has its own tested retry policy (S9 "Reintentos"), and letting
    both retry independently would multiply attempts unpredictably.
    """
    provider_kind = resolve_provider_kind()
    if provider_kind is LLMProviderKind.FAKE:
        return FakeLLMProvider()

    api_key = resolve_openai_api_key()
    if not api_key:
        msg = (
            "SIRIUS_LLM_PROVIDER=openai requiere la variable de entorno "
            "OPENAI_API_KEY; no se ha encontrado ninguna clave."
        )
        raise LLMProviderConfigurationError(msg)

    settings = resolve_openai_provider_settings()  # raises if model/limits are invalid

    client = openai.OpenAI(api_key=api_key, max_retries=0)
    budget_tracker = BudgetTracker(
        usage_repository=build_sqlite_llm_usage_repository(database_path)
    )
    return OpenAIResponsesProvider(
        client=client,
        model=settings.model,
        max_output_tokens=settings.max_output_tokens,
        budget_tracker=budget_tracker,
    )


def build_conversation_dependencies(database_path: Path) -> ConversationDependencies:
    """Build repositories and use cases wired to the local SQLite database."""
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
        llm_provider=_build_llm_provider(database_path),
    )
    get_history_use_case = GetConversationHistoryUseCase(conversation_repository)

    return ConversationDependencies(
        send_message_use_case=send_message_use_case,
        get_history_use_case=get_history_use_case,
    )
