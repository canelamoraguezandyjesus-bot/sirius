"""Composition root for the desktop application.

Wires the SQLite adapters, the secret store, and an LLM provider (fake or
OpenAI, see ``sirius.config.llm_provider_settings``) into the application
layer's use cases, producing exactly what ``MainWindow`` needs. This module
is the only place, outside tests, allowed to know about both the persistence
adapters/secret store and the LLM provider on one side and the presentation
layer's dependency shape on the other: ``MainWindow`` itself must never
import SQLAlchemy, a SQLite adapter, ``openai``, ``keyring``, or any LLM
provider directly (AGENTS.md: "No accedas a SQLite, OpenAI o secretos desde
la interfaz").
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import openai

from sirius.adapters.backup.sqlite_backup_service import build_sqlite_backup_service
from sirius.adapters.llm.budget import BudgetPolicy, BudgetTracker
from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
from sirius.adapters.llm.unconfigured import UnconfiguredLLMProvider
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_llm_usage_repository import (
    SqliteLLMUsageRepository,
    build_sqlite_llm_usage_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.keyring_store import build_keyring_secret_store
from sirius.application.api_key_settings import ApiKeySettingsUseCase
from sirius.application.context import ContextBuilder
from sirius.application.create_backup import CreateBackupUseCase
from sirius.application.get_conversation_history import GetConversationHistoryUseCase
from sirius.application.restore_backup import RestoreBackupUseCase
from sirius.application.send_message import SendMessageUseCase
from sirius.application.validate_backup import ValidateBackupUseCase
from sirius.config.llm_provider_settings import (
    LLMProviderConfigurationError,
    LLMProviderKind,
    resolve_openai_api_key,
    resolve_openai_provider_settings,
    resolve_provider_kind,
)
from sirius.config.settings import load_settings
from sirius.infrastructure.logging import get_logger
from sirius.ports.llm import LLMProvider
from sirius.ports.secrets import SecretStore

_logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ConversationDependencies:
    """Everything ``MainWindow`` needs to drive its tabs, already wired.

    ``api_key_settings_use_case`` is the *only* secret-related dependency
    ``MainWindow`` ever receives: it can check whether a key exists, save
    one, or delete one, but never read one back. The raw ``SecretStore`` (and
    the actual key value) stay inside this module.

    ``close_database_connections`` is not a use case: it is the minimal
    SQLAlchemy-lifecycle mechanism a safe backup restoration needs. Every
    repository built here keeps a pooled connection to ``sirius.db`` open for
    the life of the window; on Windows that pooled connection blocks the
    atomic file replace ``RestoreBackupUseCase`` performs. Calling this
    disposes every pool so the replace can proceed — after which ``MainWindow``
    must stop using its existing use cases and ask the user to reopen Sirius.
    """

    send_message_use_case: SendMessageUseCase
    get_history_use_case: GetConversationHistoryUseCase
    api_key_settings_use_case: ApiKeySettingsUseCase
    create_backup_use_case: CreateBackupUseCase
    validate_backup_use_case: ValidateBackupUseCase
    restore_backup_use_case: RestoreBackupUseCase
    close_database_connections: Callable[[], None]


def _build_llm_provider(
    database_path: Path,
    secret_store: SecretStore,
    *,
    llm_usage_repository: SqliteLLMUsageRepository | None = None,
) -> LLMProvider:
    """Build the LLM provider selected by persisted settings (default: fake).

    If "openai" is selected but not usable (no key, invalid model/limits),
    this never raises: it returns an ``UnconfiguredLLMProvider`` that reports
    the same safe, already-vetted error only when a message is actually sent,
    so the application always starts (V7A: "no debe cerrarse
    inesperadamente"). The fake provider always works, with no configuration
    at all.

    ``llm_usage_repository`` lets the caller supply an already-built
    repository (so it can also track its engine for disposal); when omitted,
    one is built internally exactly as before.

    The SDK's own retry loop is disabled (``max_retries=0``): the adapter
    already has its own tested retry policy (S9 "Reintentos"), and letting
    both retry independently would multiply attempts unpredictably.
    """
    settings = load_settings()
    try:
        provider_kind = resolve_provider_kind(settings)
        if provider_kind is LLMProviderKind.FAKE:
            _logger.info("Proveedor LLM seleccionado: fake")
            return FakeLLMProvider()

        api_key = resolve_openai_api_key(secret_store)
        if not api_key:
            msg = (
                "El proveedor 'openai' está seleccionado pero no hay ninguna clave "
                "de API guardada. Añádela en la pestaña Configuración."
            )
            raise LLMProviderConfigurationError(msg)

        provider_settings = resolve_openai_provider_settings(settings)
    except LLMProviderConfigurationError as exc:
        _logger.warning("Configuración de proveedor LLM inválida: %s", exc)
        return UnconfiguredLLMProvider(str(exc))

    _logger.info("Proveedor LLM seleccionado: openai (modelo=%s)", provider_settings.model)
    client = openai.OpenAI(api_key=api_key, max_retries=0)
    budget_tracker = BudgetTracker(
        policy=BudgetPolicy(monthly_limit_usd=provider_settings.monthly_budget_usd),
        usage_repository=llm_usage_repository or build_sqlite_llm_usage_repository(database_path),
    )
    return OpenAIResponsesProvider(
        client=client,
        model=provider_settings.model,
        max_output_tokens=provider_settings.max_output_tokens,
        budget_tracker=budget_tracker,
    )


def build_conversation_dependencies(
    database_path: Path,
    backups_dir: Path,
    secret_store: SecretStore | None = None,
) -> ConversationDependencies:
    """Build repositories, the secret store, and use cases wired to SQLite.

    ``secret_store`` defaults to the real ``KeyringSecretStore`` (production);
    tests inject a ``FakeSecretStore`` instead so nothing ever touches the
    real Windows Credential Manager.
    """
    secret_store = secret_store or build_keyring_secret_store()
    conversation_repository = build_sqlite_conversation_repository(database_path)
    identity_repository = build_sqlite_identity_repository(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    llm_usage_repository = build_sqlite_llm_usage_repository(database_path)

    context_builder = ContextBuilder(
        identity_repository=identity_repository,
        project_repository=project_repository,
        memory_repository=memory_repository,
        conversation_repository=conversation_repository,
    )
    send_message_use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=conversation_repository,
        llm_provider=_build_llm_provider(
            database_path, secret_store, llm_usage_repository=llm_usage_repository
        ),
    )
    get_history_use_case = GetConversationHistoryUseCase(conversation_repository)

    backup_service = build_sqlite_backup_service(database_path, backups_dir)

    repositories = (
        conversation_repository,
        identity_repository,
        project_repository,
        memory_repository,
        llm_usage_repository,
    )

    def close_database_connections() -> None:
        for repository in repositories:
            repository.close()

    return ConversationDependencies(
        send_message_use_case=send_message_use_case,
        get_history_use_case=get_history_use_case,
        api_key_settings_use_case=ApiKeySettingsUseCase(secret_store),
        create_backup_use_case=CreateBackupUseCase(backup_service),
        validate_backup_use_case=ValidateBackupUseCase(backup_service),
        restore_backup_use_case=RestoreBackupUseCase(backup_service),
        close_database_connections=close_database_connections,
    )
