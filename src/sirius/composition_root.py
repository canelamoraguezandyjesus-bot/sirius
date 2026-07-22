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
from sirius.adapters.llm.openai_credential_validator import OpenAICredentialValidator
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.llm.unconfigured import UnconfiguredLLMProvider
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
from sirius.adapters.persistence.sqlite_llm_usage_repository import (
    SqliteLLMUsageRepository,
    build_sqlite_llm_usage_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.adapters.secrets.keyring_store import build_keyring_secret_store
from sirius.application.api_key_settings import ApiKeySettingsUseCase
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_decision import ArchiveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.budget_status import GetBudgetStatusUseCase
from sirius.application.context import ContextBuilder
from sirius.application.correct_memory import CorrectMemoryUseCase
from sirius.application.create_backup import CreateBackupUseCase
from sirius.application.decision_origin import GetDecisionOriginUseCase
from sirius.application.delete_memory import DeleteMemoryUseCase
from sirius.application.detect_precedence_conflicts import DetectPrecedenceConflictsUseCase
from sirius.application.get_conversation_history import GetConversationHistoryUseCase
from sirius.application.initial_project import InitialProjectUseCase
from sirius.application.knowledge_overview import GetKnowledgeOverviewUseCase
from sirius.application.memory_origin import GetMemoryOriginUseCase
from sirius.application.project_continuity import ProjectContinuityUseCase
from sirius.application.project_lifecycle import ProjectLifecycleUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.restore_backup import RestoreBackupUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.send_message import SendMessageUseCase
from sirius.application.supersede_decision import SupersedeDecisionUseCase
from sirius.application.validate_and_save_api_key import ValidateAndSaveApiKeyUseCase
from sirius.application.validate_backup import ValidateBackupUseCase
from sirius.config.llm_provider_settings import (
    LLMProviderConfigurationError,
    LLMProviderKind,
    resolve_openai_api_key,
    resolve_openai_provider_settings,
    resolve_provider_kind,
)
from sirius.config.settings import load_settings, save_settings
from sirius.infrastructure.logging import get_logger
from sirius.ports.llm import LLMProvider
from sirius.ports.secrets import SecretStore

_logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ConversationDependencies:
    """Everything ``MainWindow`` needs to drive its tabs, already wired.

    Secret-related presentation access is intentionally narrow. The window
    can inspect existence, delete a saved key, or invoke validation-before-save;
    it never receives the raw ``SecretStore`` and can never read a key back.

    ``close_database_connections`` is not a use case: it is the minimal
    SQLAlchemy-lifecycle mechanism a safe backup restoration needs. Every
    repository built here keeps a pooled connection to ``sirius.db`` open for
    the life of the window; on Windows that pooled connection blocks the
    atomic file replace ``RestoreBackupUseCase`` performs. Calling this
    disposes every pool so the replace can proceed — after which ``MainWindow``
    must stop using its existing use cases and ask the user to reopen Sirius.

    ``activate_configured_llm_provider`` is likewise not a use case: it is the
    minimal recomposition mechanism the B2a first-run onboarding needs to
    switch ``send_message_use_case`` from the safe fake/unconfigured provider
    it was built with onto the real OpenAI adapter, in the same run, right
    after a candidate key passes ``ValidateAndSaveApiKeyUseCase``. Without it,
    activating a freshly saved key would need a full restart, because the
    provider is otherwise selected once, at startup.
    """

    send_message_use_case: SendMessageUseCase
    get_history_use_case: GetConversationHistoryUseCase
    get_budget_status_use_case: GetBudgetStatusUseCase
    api_key_settings_use_case: ApiKeySettingsUseCase
    validate_and_save_api_key_use_case: ValidateAndSaveApiKeyUseCase
    initial_project_use_case: InitialProjectUseCase
    project_continuity_use_case: ProjectContinuityUseCase
    project_lifecycle_use_case: ProjectLifecycleUseCase
    save_manual_memory_use_case: SaveManualMemoryUseCase
    get_memory_origin_use_case: GetMemoryOriginUseCase
    correct_memory_use_case: CorrectMemoryUseCase
    archive_memory_use_case: ArchiveMemoryUseCase
    delete_memory_use_case: DeleteMemoryUseCase
    propose_decision_use_case: ProposeDecisionUseCase
    approve_decision_use_case: ApproveDecisionUseCase
    get_decision_origin_use_case: GetDecisionOriginUseCase
    supersede_decision_use_case: SupersedeDecisionUseCase
    archive_decision_use_case: ArchiveDecisionUseCase
    detect_precedence_conflicts_use_case: DetectPrecedenceConflictsUseCase
    get_knowledge_overview_use_case: GetKnowledgeOverviewUseCase
    create_backup_use_case: CreateBackupUseCase
    validate_backup_use_case: ValidateBackupUseCase
    restore_backup_use_case: RestoreBackupUseCase
    close_database_connections: Callable[[], None]
    activate_configured_llm_provider: Callable[[], None]


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
    event_repository = build_sqlite_event_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    knowledge_search_repository = build_sqlite_knowledge_search_repository(database_path)
    llm_usage_repository = build_sqlite_llm_usage_repository(database_path)
    # Shared by every use case that must write more than one repository
    # atomically: SaveManualMemoryUseCase (B4a); ProposeDecisionUseCase and
    # ApproveDecisionUseCase (B4b); CorrectMemoryUseCase and
    # SupersedeDecisionUseCase (B4c); ArchiveMemoryUseCase,
    # DeleteMemoryUseCase and ArchiveDecisionUseCase (B4d).
    unit_of_work = build_sqlite_unit_of_work(database_path)

    rank_relevant_knowledge_use_case = RankRelevantKnowledgeUseCase(
        memory_repository=memory_repository,
        decision_repository=decision_repository,
        project_repository=project_repository,
        knowledge_search_repository=knowledge_search_repository,
    )
    context_builder = ContextBuilder(
        identity_repository=identity_repository,
        project_repository=project_repository,
        memory_repository=memory_repository,
        conversation_repository=conversation_repository,
        decision_repository=decision_repository,
        rank_relevant_knowledge_use_case=rank_relevant_knowledge_use_case,
        event_repository=event_repository,
        token_counter=CharacterHeuristicTokenCounter(),
    )
    send_message_use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=conversation_repository,
        llm_provider=_build_llm_provider(
            database_path, secret_store, llm_usage_repository=llm_usage_repository
        ),
    )
    get_history_use_case = GetConversationHistoryUseCase(conversation_repository)

    # B7c: reads the *same* llm_usage_repository instance the OpenAI
    # provider's own BudgetTracker writes to (built above, shared here), so
    # the non-blocking warning and the provider's blocking check always
    # agree on this month's spend. warn_threshold_usd is DR-018's fixed 15
    # USD (BudgetPolicy's default, never configurable); monthly_limit_usd
    # mirrors _build_llm_provider's own resolution of the configured budget.
    try:
        budget_settings = resolve_openai_provider_settings(load_settings())
    except LLMProviderConfigurationError:
        budget_settings = resolve_openai_provider_settings({})
    get_budget_status_use_case = GetBudgetStatusUseCase(
        usage_repository=llm_usage_repository,
        warn_threshold_usd=BudgetPolicy().warn_threshold_usd,
        monthly_limit_usd=budget_settings.monthly_budget_usd,
    )

    backup_service = build_sqlite_backup_service(database_path, backups_dir)

    repositories = (
        conversation_repository,
        identity_repository,
        project_repository,
        memory_repository,
        event_repository,
        decision_repository,
        knowledge_search_repository,
        llm_usage_repository,
        unit_of_work,
    )

    def close_database_connections() -> None:
        for repository in repositories:
            repository.close()

    def activate_configured_llm_provider() -> None:
        """Select "openai" and rebuild the provider from the now-saved key.

        Onboarding only ever offers OpenAI (Product §5.1: "El proveedor y el
        modelo de referencia aparecen preseleccionados" — no selector), so a
        successful validate-and-save implies this choice; recording it in
        ``settings.json`` is what lets ``_build_llm_provider`` pick the real
        adapter instead of silently keeping "fake".
        """
        settings = dict(load_settings())
        settings["llm_provider"] = LLMProviderKind.OPENAI.value
        save_settings(settings)
        send_message_use_case.set_llm_provider(
            _build_llm_provider(
                database_path, secret_store, llm_usage_repository=llm_usage_repository
            )
        )

    return ConversationDependencies(
        send_message_use_case=send_message_use_case,
        get_history_use_case=get_history_use_case,
        get_budget_status_use_case=get_budget_status_use_case,
        api_key_settings_use_case=ApiKeySettingsUseCase(secret_store),
        validate_and_save_api_key_use_case=ValidateAndSaveApiKeyUseCase(
            OpenAICredentialValidator(), secret_store
        ),
        initial_project_use_case=InitialProjectUseCase(project_repository),
        project_continuity_use_case=ProjectContinuityUseCase(project_repository),
        project_lifecycle_use_case=ProjectLifecycleUseCase(project_repository),
        save_manual_memory_use_case=SaveManualMemoryUseCase(unit_of_work),
        get_memory_origin_use_case=GetMemoryOriginUseCase(
            memory_repository, event_repository, conversation_repository
        ),
        correct_memory_use_case=CorrectMemoryUseCase(unit_of_work),
        archive_memory_use_case=ArchiveMemoryUseCase(unit_of_work),
        delete_memory_use_case=DeleteMemoryUseCase(unit_of_work),
        propose_decision_use_case=ProposeDecisionUseCase(unit_of_work),
        approve_decision_use_case=ApproveDecisionUseCase(unit_of_work),
        get_decision_origin_use_case=GetDecisionOriginUseCase(
            decision_repository, event_repository, conversation_repository
        ),
        supersede_decision_use_case=SupersedeDecisionUseCase(unit_of_work),
        archive_decision_use_case=ArchiveDecisionUseCase(unit_of_work),
        detect_precedence_conflicts_use_case=DetectPrecedenceConflictsUseCase(
            memory_repository, decision_repository
        ),
        get_knowledge_overview_use_case=GetKnowledgeOverviewUseCase(
            memory_repository, decision_repository
        ),
        create_backup_use_case=CreateBackupUseCase(backup_service),
        validate_backup_use_case=ValidateBackupUseCase(backup_service),
        restore_backup_use_case=RestoreBackupUseCase(backup_service),
        close_database_connections=close_database_connections,
        activate_configured_llm_provider=activate_configured_llm_provider,
    )
