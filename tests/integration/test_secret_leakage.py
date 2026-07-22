"""End-to-end proof that an API key never leaks (V7A requirement #6).

A single fake key value is threaded through every path that touches
configuration, persistence, and error handling, then every place it could
have leaked — ``settings.json``, SQLite, log files, exceptions, and the
relevant dataclass reprs — is inspected for its literal presence.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from sirius.adapters.clock.fake import FakeClock
from sirius.adapters.export.filesystem_export_service import FilesystemExportService
from sirius.adapters.llm.budget import BudgetTracker
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
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
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.context import ContextBuilder
from sirius.application.export_structured import ExportStructuredUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.send_message import SendMessageUseCase
from sirius.config.llm_provider_settings import OpenAIProviderSettings
from sirius.config.secrets_config import OPENAI_API_KEY_SECRET_NAME
from sirius.config.settings import load_settings, save_settings
from sirius.domain.conversation import MessageRole
from sirius.infrastructure.logging import LOG_FILE_NAME, configure_logging, get_logger
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.llm import LLMError, LLMRequest

_FAKE_KEY = "sk-super-secret-value-should-never-leak-0000000000"


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


class _FakeResponses:
    def __init__(self, create_fn: Callable[..., object]) -> None:
        self._create_fn = create_fn

    def create(self, **kwargs: Any) -> object:
        return self._create_fn(**kwargs)


class _FakeOpenAIClient:
    def __init__(self, create_fn: Callable[..., object]) -> None:
        self.responses = _FakeResponses(create_fn)


class _FakeStream:
    def __init__(self, events: list[object]) -> None:
        self._events = events

    def __iter__(self) -> Iterator[object]:
        return iter(self._events)

    def close(self) -> None:
        pass


def _completed_event(output_text: str) -> SimpleNamespace:
    usage = SimpleNamespace(input_tokens=1, output_tokens=1)
    response = SimpleNamespace(usage=usage, output_text=output_text)
    return SimpleNamespace(type="response.completed", response=response)


@pytest.mark.integration
def test_key_never_appears_in_settings_json(tmp_path: Path) -> None:
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, _FAKE_KEY)

    save_settings(
        {
            "user_name": "Ada",
            "llm_provider": "openai",
            "openai_model": "gpt-5.6-terra",
            "openai_max_output_tokens": 4096,
            "openai_monthly_budget_usd": 20.0,
        }
    )

    settings_file = resolve_paths().config_dir / "settings.json"
    assert _FAKE_KEY not in settings_file.read_text(encoding="utf-8")
    assert _FAKE_KEY not in repr(load_settings())


@pytest.mark.integration
def test_key_never_appears_in_sqlite_after_a_full_send(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation_repository.get_or_create_main_conversation()
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

    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
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
        conversation_repository=conversation_repository,
        decision_repository=decision_repository,
        rank_relevant_knowledge_use_case=rank_relevant_knowledge_use_case,
        event_repository=build_sqlite_event_repository(database_path),
        token_counter=CharacterHeuristicTokenCounter(),
    )
    client = _FakeOpenAIClient(lambda **kwargs: _FakeStream([_completed_event("hola")]))
    provider = OpenAIResponsesProvider(
        client=client,  # type: ignore[arg-type]
        model="gpt-5.6-terra",
        budget_tracker=BudgetTracker(),
    )
    # The key was only ever used to build ``openai.OpenAI`` in the real
    # composition root; here we prove the adapter/use case never need to see
    # it again, so it cannot end up in anything they persist.
    use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=conversation_repository,
        llm_provider=provider,
    )

    use_case.send_message("hola Sirius")

    raw_bytes = database_path.read_bytes()
    assert _FAKE_KEY.encode("utf-8") not in raw_bytes


@pytest.mark.integration
def test_key_never_appears_in_logs_even_when_an_exception_message_embeds_it(
    tmp_path: Path,
) -> None:
    configure_logging(tmp_path)
    request_obj = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response_obj = httpx.Response(401, request=request_obj, json={})

    def _raise(**kwargs: Any) -> object:
        # Worst case: the SDK's own exception message embeds the key.
        raise openai.AuthenticationError(
            f"Incorrect API key provided: {_FAKE_KEY}", response=response_obj, body=None
        )

    client = _FakeOpenAIClient(_raise)
    provider = OpenAIResponsesProvider(
        client=client,  # type: ignore[arg-type]
        model="gpt-5.6-terra",
        budget_tracker=BudgetTracker(),
    )

    request = LLMRequest(operation_id="op-1", instructions="", input_text="hola")
    events = list(provider.stream_response(request))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, LLMError)
    assert _FAKE_KEY not in event.message

    logger = get_logger("sirius.adapters.llm.openai_responses")
    for handler in logger.handlers or get_logger("sirius").handlers:
        handler.flush()
    log_content = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert _FAKE_KEY not in log_content


@pytest.mark.integration
def test_key_is_absent_from_relevant_object_reprs() -> None:
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, _FAKE_KEY)

    settings = OpenAIProviderSettings(
        model="gpt-5.6-terra", max_output_tokens=4096, monthly_budget_usd=20.0
    )
    client = openai.OpenAI(api_key=_FAKE_KEY, max_retries=0)
    provider = OpenAIResponsesProvider(client=client, model="gpt-5.6-terra")

    assert _FAKE_KEY not in repr(settings)
    assert _FAKE_KEY not in repr(provider)
    assert _FAKE_KEY not in repr(secret_store)


@pytest.mark.integration
def test_key_never_appears_in_a_structured_export(tmp_path: Path) -> None:
    """RNF-013 for B9a: the S12.1 open export must never contain the API key,
    even when a real key is configured in the secret store at export time.

    ``ExportStructuredUseCase``/``FilesystemExportService`` never receive a
    ``SecretStore`` at all (they only read conversation, project, memory and
    decision repositories) — this proves that structurally, against the real
    SQLite adapters and every one of the six files the export writes.
    """
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, _FAKE_KEY)

    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "hola Sirius")

    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="En marcha",
        blockers=(),
        next_step="Siguiente paso",
    )

    unit_of_work = build_sqlite_unit_of_work(database_path)
    SaveManualMemoryUseCase(unit_of_work).save(
        "El usuario prefiere respuestas breves.", project_id=project.id
    )
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Formato de exportación", project.id, "Usar JSON/JSONL abierto"
    )
    ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)

    use_case = ExportStructuredUseCase(
        FilesystemExportService(FakeClock(datetime(2026, 3, 1, tzinfo=UTC))),
        conversation_repository,
        project_repository,
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    )

    result = use_case.export_structured(tmp_path / "exports")

    exported_files = list(result.iterdir())
    assert len(exported_files) == 6
    for exported_file in exported_files:
        assert _FAKE_KEY not in exported_file.read_text(encoding="utf-8")
