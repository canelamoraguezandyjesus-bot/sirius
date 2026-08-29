import threading
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pytestqt.qtbot import QtBot

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
from sirius.adapters.persistence.sqlite_llm_usage_repository import (
    build_sqlite_llm_usage_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.context import ContextBuilder
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.send_message import SendMessageUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.project import Project, ProjectRevision, ProjectStatus
from sirius.ports.backup import BackupError, BackupManifest, BackupResult
from sirius.ports.llm import (
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMProvider,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)
from sirius.presentation.main_window import MainWindow
from sirius.presentation.project_continuity_widget import NO_BLOCKERS_TEXT, ProjectContinuityWidget


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path, *, configure_project: bool = True) -> Path:
    """Mimic initialize_persistence(): schema + the three canonical singletons.

    ``configure_project=True`` (the default) also completes the placeholder
    project, representing an installation that has already been through
    B3a's first-project screen — the normal case ``MainWindow`` expects.
    """
    upgrade_to_head(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    if configure_project:
        project_repository.create_project(
            "Sirius 0.1",
            "Cerrar B3b",
            state_summary="en curso",
            blockers=(),
            next_step="escribir pruebas",
        )
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    return database_path


def _build_window(database_path: Path) -> MainWindow:
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=FakeSecretStore()
    )
    return MainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        get_budget_status_use_case=dependencies.get_budget_status_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        project_continuity_use_case=dependencies.project_continuity_use_case,
        project_lifecycle_use_case=dependencies.project_lifecycle_use_case,
        save_manual_memory_use_case=dependencies.save_manual_memory_use_case,
        get_memory_origin_use_case=dependencies.get_memory_origin_use_case,
        correct_memory_use_case=dependencies.correct_memory_use_case,
        archive_memory_use_case=dependencies.archive_memory_use_case,
        delete_memory_use_case=dependencies.delete_memory_use_case,
        propose_decision_use_case=dependencies.propose_decision_use_case,
        approve_decision_use_case=dependencies.approve_decision_use_case,
        get_decision_origin_use_case=dependencies.get_decision_origin_use_case,
        supersede_decision_use_case=dependencies.supersede_decision_use_case,
        archive_decision_use_case=dependencies.archive_decision_use_case,
        detect_precedence_conflicts_use_case=dependencies.detect_precedence_conflicts_use_case,
        get_knowledge_overview_use_case=dependencies.get_knowledge_overview_use_case,
        propose_memory_suggestion_use_case=dependencies.propose_memory_suggestion_use_case,
        confirm_memory_suggestion_use_case=dependencies.confirm_memory_suggestion_use_case,
        reject_memory_suggestion_use_case=dependencies.reject_memory_suggestion_use_case,
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        export_structured_use_case=dependencies.export_structured_use_case,
        historical_projects_use_case=dependencies.historical_projects_use_case,
        close_database_connections=dependencies.close_database_connections,
        show_warning=lambda title, text: None,
        show_information=lambda title, text: None,
    )


def _build_window_with_backup_use_case(
    database_path: Path, create_backup_use_case: Any
) -> MainWindow:
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=FakeSecretStore()
    )
    return MainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        get_budget_status_use_case=dependencies.get_budget_status_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        project_continuity_use_case=dependencies.project_continuity_use_case,
        project_lifecycle_use_case=dependencies.project_lifecycle_use_case,
        save_manual_memory_use_case=dependencies.save_manual_memory_use_case,
        get_memory_origin_use_case=dependencies.get_memory_origin_use_case,
        correct_memory_use_case=dependencies.correct_memory_use_case,
        archive_memory_use_case=dependencies.archive_memory_use_case,
        delete_memory_use_case=dependencies.delete_memory_use_case,
        propose_decision_use_case=dependencies.propose_decision_use_case,
        approve_decision_use_case=dependencies.approve_decision_use_case,
        get_decision_origin_use_case=dependencies.get_decision_origin_use_case,
        supersede_decision_use_case=dependencies.supersede_decision_use_case,
        archive_decision_use_case=dependencies.archive_decision_use_case,
        detect_precedence_conflicts_use_case=dependencies.detect_precedence_conflicts_use_case,
        get_knowledge_overview_use_case=dependencies.get_knowledge_overview_use_case,
        propose_memory_suggestion_use_case=dependencies.propose_memory_suggestion_use_case,
        confirm_memory_suggestion_use_case=dependencies.confirm_memory_suggestion_use_case,
        reject_memory_suggestion_use_case=dependencies.reject_memory_suggestion_use_case,
        create_backup_use_case=create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        export_structured_use_case=dependencies.export_structured_use_case,
        historical_projects_use_case=dependencies.historical_projects_use_case,
        close_database_connections=dependencies.close_database_connections,
        show_warning=lambda title, text: None,
        show_information=lambda title, text: None,
    )


@pytest.mark.gui
def test_main_window_has_expected_title(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.windowTitle() == "Sirius 0.1"


@pytest.mark.gui
def test_main_window_shows_the_project_continuity_widget_in_the_conversation_tab(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """B3b: the section lives in "Conversación" — no new tab for it is created."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    # El widget central es el conmutador entre la interfaz técnica y Model
    # Studio; las pestañas siguen existiendo igual, ahora con acceso directo.
    # M2 añade "Proyectos históricos" como cuarta pestaña, separada de esta.
    tabs = window.tabs
    assert tabs.count() == 4
    assert tabs.tabText(0) == "Conversación"
    assert tabs.tabText(1) == "Memoria y decisiones"
    assert tabs.tabText(2) == "Configuración"
    assert tabs.tabText(3) == "Proyectos históricos"
    assert isinstance(window.project_continuity_widget, ProjectContinuityWidget)
    assert window.project_continuity_widget.name_label.text() == "Sirius 0.1"
    assert window.project_continuity_widget.next_step_label.text() == "Ahora toca: escribir pruebas"


@pytest.mark.gui
def test_project_continuity_widget_shows_no_blockers_for_a_freshly_configured_project(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.project_continuity_widget.blockers_label.text() == NO_BLOCKERS_TEXT


@pytest.mark.gui
def test_main_window_built_without_a_configured_project_shows_a_safe_state(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Defensive: MainWindow built directly (bypassing the B3a gate) with only
    the bootstrap placeholder never creates a project and never crashes."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db", configure_project=False)
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.project_continuity_widget._current_summary is None


@pytest.mark.gui
def test_conversation_history_still_loads_alongside_the_continuity_widget(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.message_list is not None
    assert window.error_label.text() == ""


# --- Coordinación de estado ocupado (ProjectContinuityWidget.set_external_busy) ---


class _BlockingUntilReleasedProvider:
    """Test double: yields one delta, then blocks until the test calls
    ``release()`` — deterministic control over "a send/stream is genuinely
    in flight" without any arbitrary sleep, mirroring the double already
    used in ``tests/gui/test_conversation_ui.py``.
    """

    def __init__(self) -> None:
        self._continue_event = threading.Event()
        self._cancelled: set[str] = set()

    def health_check(self) -> bool:
        return True

    def release(self) -> None:
        self._continue_event.set()

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        yield LLMTextDelta(text="parcial")
        self._continue_event.wait(timeout=5)
        yield LLMCompleted(text="parcial completo", input_tokens=1, output_tokens=2)

    def cancel(self, operation_id: str) -> None:
        self._cancelled.add(operation_id)


class _FailingLLMProvider:
    """Test double: always fails before any delta, mirroring the one in
    ``tests/gui/test_conversation_ui.py``."""

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMError(kind=LLMErrorKind.CONNECTION, message="no se pudo contactar")

    def cancel(self, operation_id: str) -> None:
        del operation_id


def _swap_send_message_use_case(
    window: MainWindow, database_path: Path, llm_provider: LLMProvider
) -> None:
    conversation_repository = build_sqlite_conversation_repository(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    project_repository = build_sqlite_project_repository(database_path)
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
    window._send_message_use_case = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=conversation_repository,
        llm_provider=llm_provider,
    )


class _BlockingCreateBackupUseCase:
    """Blocks until the test calls ``release()``, mirroring the double
    already used in ``tests/gui/test_backup_recovery_ui.py``."""

    def __init__(self) -> None:
        self._continue_event = threading.Event()
        self._result: BackupResult | None = None
        self._error: Exception | None = None

    def set_result(self, result: BackupResult) -> None:
        self._result = result

    def set_error(self, error: Exception) -> None:
        self._error = error

    def release(self) -> None:
        self._continue_event.set()

    def create_backup(self, password: str) -> BackupResult:
        self._continue_event.wait(timeout=5)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _fake_backup_result(path: Path) -> BackupResult:
    manifest = BackupManifest(
        format="siriusbackup",
        app_version="0.1.0.dev0",
        schema_version="abc123",
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
        sha256="0" * 64,
    )
    return BackupResult(path=path, manifest=manifest, size_bytes=2048)


class _SpyProjectLifecycleUseCase:
    """Records whether ``complete_active_project()`` was ever actually
    invoked, without touching any real repository."""

    def __init__(self) -> None:
        self.complete_calls = 0

    def get_active_project(self) -> Project | None:
        raise AssertionError("must never be called from this test")

    def complete_active_project(self) -> Project:
        self.complete_calls += 1
        now = datetime.now(UTC)
        revision = ProjectRevision(
            id=1,
            project_id=1,
            version=1,
            objective="objetivo",
            state_summary="estado",
            blockers=(),
            next_step="siguiente",
            source_event_id=None,
            created_at=now,
        )
        return Project(
            id=1,
            name="Sirius 0.1",
            status=ProjectStatus.COMPLETED,
            current_revision=revision,
            created_at=now,
            updated_at=now,
            completed_at=now,
        )


@pytest.mark.gui
def test_completar_proyecto_is_disabled_while_sending_and_reenabled_when_finished(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)

    assert window.project_continuity_widget.complete_button.isEnabled() is True

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)

    assert window.project_continuity_widget.complete_button.isEnabled() is False
    assert window.project_continuity_widget.update_button.isEnabled() is False

    provider.release()

    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)
    assert window.project_continuity_widget.complete_button.isEnabled() is True
    assert window.project_continuity_widget.update_button.isEnabled() is True


@pytest.mark.gui
def test_completar_proyecto_stays_disabled_during_a_pending_cancellation(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)

    window.cancel_button.click()
    assert window.project_continuity_widget.complete_button.isEnabled() is False

    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)
    assert window.project_continuity_widget.complete_button.isEnabled() is True


@pytest.mark.gui
def test_completar_proyecto_is_disabled_during_backup_and_reenabled_after_success(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _BlockingCreateBackupUseCase()
    window = _build_window_with_backup_use_case(database_path, use_case)
    qtbot.addWidget(window)

    window.create_backup_password_input.setText("correct horse battery staple")
    window.create_backup_password_repeat_input.setText("correct horse battery staple")
    window.create_backup_button.click()

    assert window.project_continuity_widget.complete_button.isEnabled() is False

    use_case.set_result(_fake_backup_result(tmp_path / "b.siriusbackup"))
    use_case.release()

    qtbot.waitUntil(lambda: window.create_backup_button.isEnabled(), timeout=5000)
    assert window.project_continuity_widget.complete_button.isEnabled() is True


@pytest.mark.gui
def test_completar_proyecto_is_reenabled_after_a_backup_failure(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _BlockingCreateBackupUseCase()
    window = _build_window_with_backup_use_case(database_path, use_case)
    qtbot.addWidget(window)

    window.create_backup_password_input.setText("correct horse battery staple")
    window.create_backup_password_repeat_input.setText("correct horse battery staple")
    window.create_backup_button.click()

    assert window.project_continuity_widget.complete_button.isEnabled() is False

    use_case.set_error(BackupError("fallo simulado"))
    use_case.release()

    qtbot.waitUntil(lambda: window.create_backup_button.isEnabled(), timeout=5000)
    assert window.project_continuity_widget.complete_button.isEnabled() is True


@pytest.mark.gui
def test_retry_button_is_disabled_during_backup_and_reenabled_after_success(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """B7b: "Reintentar" respects the same busy exclusion as a normal send —
    disabled/hidden while a backup or restore operation is in progress."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _BlockingCreateBackupUseCase()
    window = _build_window_with_backup_use_case(database_path, use_case)
    qtbot.addWidget(window)
    window.show()
    _swap_send_message_use_case(window, database_path, _FailingLLMProvider())

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.retry_button.isVisible(), timeout=5000)
    assert window.retry_button.isEnabled() is True

    window.create_backup_password_input.setText("correct horse battery staple")
    window.create_backup_password_repeat_input.setText("correct horse battery staple")
    window.create_backup_button.click()

    assert window.retry_button.isVisible() is True
    assert window.retry_button.isEnabled() is False

    use_case.set_result(_fake_backup_result(tmp_path / "b.siriusbackup"))
    use_case.release()

    qtbot.waitUntil(lambda: window.create_backup_button.isEnabled(), timeout=5000)
    assert window.retry_button.isVisible() is True
    assert window.retry_button.isEnabled() is True


@pytest.mark.gui
def test_project_lifecycle_use_case_never_runs_while_a_send_is_in_progress(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Clicking a disabled button is a real, behavioral no-op in Qt (no
    ``clicked`` signal fires), so this proves the use case is genuinely
    never invoked — not merely that a warning was shown instead."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)
    spy = _SpyProjectLifecycleUseCase()
    window.project_continuity_widget._lifecycle_use_case = spy  # type: ignore[assignment]

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)

    window.project_continuity_widget.complete_button.click()

    assert spy.complete_calls == 0

    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)


# --- Aviso de presupuesto (B7c, RF-030/PA-018) ---------------------------


def _current_year_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


@pytest.mark.gui
def test_budget_warning_is_hidden_when_spend_is_below_the_warn_threshold(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    build_sqlite_llm_usage_repository(database_path).add_spent_usd(_current_year_month(), 5.0)
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.budget_warning_label.text() == ""


@pytest.mark.gui
def test_budget_warning_shows_the_amounts_once_spend_reaches_the_warn_threshold(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    build_sqlite_llm_usage_repository(database_path).add_spent_usd(_current_year_month(), 15.3)
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert "15.30" in window.budget_warning_label.text()
    assert "20.00" in window.budget_warning_label.text()


@pytest.mark.gui
def test_budget_warning_never_appears_with_the_simulated_provider(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """The fake provider never records usage: spend stays at 0.0, so no
    amount of sending through it should ever surface the warning."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert window.budget_warning_label.text() == ""


@pytest.mark.gui
def test_budget_warning_is_recalculated_only_after_the_send_completes(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)
    assert window.budget_warning_label.text() == ""

    provider = _BlockingUntilReleasedProvider()
    _swap_send_message_use_case(window, database_path, provider)
    # Spend crosses the warn threshold while the send is still in flight, via
    # a repository instance independent of the window's own — mirroring how
    # BudgetTracker.record_usage persists real usage after a real send.
    build_sqlite_llm_usage_repository(database_path).add_spent_usd(_current_year_month(), 16.0)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.message_list.count() == 2, timeout=5000)

    assert window.budget_warning_label.text() == ""

    provider.release()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert "16.00" in window.budget_warning_label.text()
