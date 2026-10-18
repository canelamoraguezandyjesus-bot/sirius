"""GUI tests for validate-before-save credential handling."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import cast

import openai
import pytest
from PySide6.QtCore import QRunnable, QThreadPool
from pytestqt.qtbot import QtBot

from sirius.adapters.llm.openai_credential_validator import OpenAICredentialValidator
from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.validate_and_save_api_key import ValidateAndSaveApiKeyUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.infrastructure.network import ConnectionRegistry, openai_client
from sirius.ports.connections import ConnectionCloser
from sirius.ports.credential_validation import (
    CredentialValidationError,
    CredentialValidationKind,
    CredentialValidator,
)
from sirius.presentation.validated_main_window import ValidatedMainWindow


class _RecordingValidator:
    def __init__(self, error: CredentialValidationError | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def validate(self, credential: str, model: str) -> None:
        self.calls.append((credential, model))
        if self.error is not None:
            raise self.error


class _ImmediateThreadPool:
    def start(self, worker: QRunnable) -> None:
        worker.run()


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path) -> Path:
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
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
    return database_path


def _build_window(
    database_path: Path,
    validator: CredentialValidator,
    secret_store: FakeSecretStore,
    *,
    connections: ConnectionCloser | None = None,
) -> ValidatedMainWindow:
    dependencies = build_conversation_dependencies(
        database_path,
        database_path.parent / "backups",
        secret_store=secret_store,
    )
    window = ValidatedMainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        get_budget_status_use_case=dependencies.get_budget_status_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        validate_and_save_api_key_use_case=ValidateAndSaveApiKeyUseCase(
            validator,
            secret_store,
        ),
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
        connections=connections,
        show_warning=lambda title, text: None,
        show_information=lambda title, text: None,
    )
    window._thread_pool = cast(QThreadPool, _ImmediateThreadPool())
    return window


@pytest.mark.gui
def test_valid_key_is_saved_and_restart_is_explained(qtbot: QtBot, tmp_path: Path) -> None:
    validator = _RecordingValidator()
    secret_store = FakeSecretStore()
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"),
        validator,
        secret_store,
    )
    qtbot.addWidget(window)
    window.api_key_input.setText("sk-candidate")
    window.model_input.setText("gpt-model")

    window._save_api_key()

    qtbot.waitUntil(lambda: not window._is_credential_busy)
    assert validator.calls == [("sk-candidate", "gpt-model")]
    assert window._api_key_settings_use_case.has_key()
    assert window.api_key_input.text() == ""
    assert "Reinicia Sirius" in window.key_feedback_label.text()


@pytest.mark.gui
def test_rejected_key_is_not_saved_and_safe_message_is_shown(
    qtbot: QtBot,
    tmp_path: Path,
) -> None:
    validator = _RecordingValidator(
        CredentialValidationError(CredentialValidationKind.AUTHENTICATION)
    )
    secret_store = FakeSecretStore()
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"),
        validator,
        secret_store,
    )
    qtbot.addWidget(window)
    window.api_key_input.setText("sk-invalid")
    window.model_input.setText("gpt-model")

    window._save_api_key()

    qtbot.waitUntil(lambda: not window._is_credential_busy)
    assert not window._api_key_settings_use_case.has_key()
    assert window.api_key_input.text() == ""
    assert window.key_feedback_label.text() == "La clave no es válida."


@pytest.mark.gui
def test_cerrar_mientras_valida_cuelga_la_peticion_y_no_espera_a_su_tope(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ronda 3 de Codex sobre la #698: el cierre se aplazaba hasta que acabara la
    validación, sin colgarla, y ni llegaba a la salida: la petición a OpenAI seguía hasta su
    tope de 10 s. Con el validador de verdad, contra un servidor que acepta y no contesta
    (ADR-255)."""
    # Aquí y no arriba: hay sondas que importan este módulo en otro proceso, sin las
    # rutas de las pruebas.
    from servidor_mudo import ServidorMudo, quita_los_proxies

    quita_los_proxies(monkeypatch)
    servidor = ServidorMudo()
    registro = ConnectionRegistry()
    try:
        validator = OpenAICredentialValidator(
            lambda credential: openai_client(
                registry=registro,
                api_key=credential,
                base_url=f"http://127.0.0.1:{servidor.puerto}/v1",
                max_retries=0,
                timeout=10.0,
            )
        )
        window = _build_window(
            _bootstrapped_database(tmp_path / "sirius.db"),
            validator,
            FakeSecretStore(),
            connections=registro,
        )
        window._thread_pool = QThreadPool()
        qtbot.addWidget(window)
        window.show()
        window.api_key_input.setText("sk-candidate")
        window.model_input.setText("gpt-model")
        window._save_api_key()
        qtbot.waitUntil(lambda: bool(servidor.aceptadas), timeout=5000)

        empieza = time.perf_counter()
        window.close()
        qtbot.waitUntil(lambda: not window.isVisible(), timeout=3000)

        assert time.perf_counter() - empieza < 1
        assert window._api_key_settings_use_case.has_key() is False
    finally:
        servidor.cierra()


@pytest.mark.gui
def test_cerrar_antes_de_que_la_validacion_conecte_la_cuelga_al_conectar(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ronda 4 de Codex sobre la #698: si se pedía cerrar con la conexión de la validación
    aún abriéndose, colgar no la encontraba, y el cierre volvía a esperar a su tope de 10 s.
    Hasta que la ventana se cierra de verdad, lo que se abre se cuelga en el acto; después
    ya no (ADR-255)."""
    # Aquí y no arriba: hay sondas que importan este módulo en otro proceso, sin las
    # rutas de las pruebas.
    from servidor_mudo import ServidorMudo, quita_los_proxies, se_cuelga_al_abrirse

    quita_los_proxies(monkeypatch)
    servidor = ServidorMudo()
    registro = ConnectionRegistry()
    abriendose = threading.Event()
    sigue = threading.Event()

    def cliente_que_tarda_en_conectar(credential: str) -> openai.OpenAI:
        cliente = openai_client(
            registry=registro,
            api_key=credential,
            base_url=f"http://127.0.0.1:{servidor.puerto}/v1",
            max_retries=0,
            timeout=10.0,
        )
        # La primera vez, el SDK carga aquí sus recursos, casi un segundo que no es del cierre.
        _ = cliente.models
        abriendose.set()
        sigue.wait(timeout=5)
        return cliente

    try:
        window = _build_window(
            _bootstrapped_database(tmp_path / "sirius.db"),
            OpenAICredentialValidator(cliente_que_tarda_en_conectar),
            FakeSecretStore(),
            connections=registro,
        )
        window._thread_pool = QThreadPool()
        qtbot.addWidget(window)
        window.show()
        window.api_key_input.setText("sk-candidate")
        window.model_input.setText("gpt-model")
        window._save_api_key()
        assert abriendose.wait(timeout=5)

        empieza = time.perf_counter()
        window.close()
        sigue.set()
        qtbot.waitUntil(lambda: not window.isVisible(), timeout=3000)

        assert time.perf_counter() - empieza < 1
        assert servidor.aceptadas, "la validación tenía que llegar a conectar"
        assert window._api_key_settings_use_case.has_key() is False
        assert not se_cuelga_al_abrirse(registro, servidor)
    finally:
        sigue.set()
        servidor.cierra()
