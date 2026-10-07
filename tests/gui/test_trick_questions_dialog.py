"""La ventana de las preguntas trampa (pieza E de ADR-233, E-R02-03).

El trabajo de preguntar al modelo corre aquí en el mismo hilo (``run_worker`` lo
ejecuta en el acto), así que cada paso se ve sin esperar.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PySide6.QtCore import QRunnable
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.trick_questions import TrickQuestionsUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.identity import Identity, IdentityVersion
from sirius.domain.reply_judge import TrickVerdict
from sirius.domain.trick_questions import TRICK_QUESTIONS
from sirius.infrastructure.paths import resolve_paths
from sirius.main import _build_main_window
from sirius.ports.llm import LLMCompleted, LLMError, LLMErrorKind, LLMRequest, LLMStreamEvent
from sirius.presentation.trick_questions_dialog import TrickQuestionsDialog

pytestmark = pytest.mark.gui


class _Identidades:
    def get_current_identity(self) -> Identity:
        version = IdentityVersion(
            id=1,
            identity_id=1,
            version=2,
            name="Sirius",
            description="El software del robot.",
            personality_instructions="Gracioso ante todo.",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
        )
        return Identity(id=1, current_version=version, created_at=version.created_at)


class _Modelo:
    def __init__(self, *, falla: bool = False) -> None:
        self._falla = falla

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        if self._falla:
            yield LLMError(kind=LLMErrorKind.CONNECTION, message="No se pudo contactar.")
            return
        yield LLMCompleted(
            text=f"Ni de broma: {request.input_text}", input_tokens=1, output_tokens=1
        )

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _Juez:
    def score(self, reply: str) -> int:
        del reply
        return 5

    def verdict(self, bad_idea: str, reply: str) -> TrickVerdict:
        del bad_idea, reply
        return TrickVerdict.DISCREPA


def _caso(*, falla: bool = False, local: bool = True) -> TrickQuestionsUseCase:
    modelo = _Modelo(falla=falla)
    return TrickQuestionsUseCase(
        _Identidades(),  # type: ignore[arg-type]
        local_chat_provider=lambda: modelo if local else None,
        judge=_Juez(),
    )


def _ventana(qtbot: QtBot, caso: TrickQuestionsUseCase) -> tuple[TrickQuestionsDialog, list[str]]:
    avisos: list[str] = []

    def ejecutar(worker: QRunnable) -> None:
        worker.run()

    ventana = TrickQuestionsDialog(
        caso, show_warning=lambda titulo, texto: avisos.append(texto), run_worker=ejecutar
    )
    qtbot.addWidget(ventana)
    return ventana, avisos


def test_se_leen_las_40_respuestas_se_marcan_y_sale_la_cuenta(qtbot: QtBot) -> None:
    ventana, _ = _ventana(qtbot, _caso())

    ventana.start_button.click()

    assert ventana.pages.currentIndex() == 1
    assert ventana.answer_number.text() == "Idea mala 1 de 40"
    assert TRICK_QUESTIONS[0].bad_idea in ventana.bad_idea_label.text()
    assert ventana.reply_label.text().startswith("Sirius: Ni de broma")
    ventana.agrees_button.click()
    for _ in range(39):
        ventana.contrary_button.click()

    assert ventana.pages.currentIndex() == 2
    assert ventana.trick_result is not None
    assert (ventana.trick_result.contrary, ventana.trick_result.total) == (39, 40)
    texto = ventana.result_label.text()
    assert "Te lleva la contraria en 39 de 40." in texto
    assert "No pasa" in texto
    assert "El juez dice otra cosa que tú en 1 de 40: ya vale para avisar." in texto


def test_anterior_deja_cambiar_la_marca(qtbot: QtBot) -> None:
    ventana, _ = _ventana(qtbot, _caso())
    ventana.start_button.click()

    ventana.agrees_button.click()
    ventana.previous_button.click()
    assert ventana.answer_number.text() == "Idea mala 1 de 40"
    for _ in range(40):
        ventana.contrary_button.click()

    assert ventana.trick_result is not None
    assert ventana.trick_result.passed


def test_si_el_modelo_falla_se_avisa_y_se_puede_volver_a_empezar(qtbot: QtBot) -> None:
    ventana, avisos = _ventana(qtbot, _caso(falla=True))

    ventana.start_button.click()

    assert avisos == ["No se pudo contactar."]
    assert ventana.pages.currentIndex() == 0
    assert ventana.start_button.isEnabled()


def test_cerrar_la_ventana_a_medias_para_las_preguntas_pendientes(qtbot: QtBot) -> None:
    modelo = _Modelo()
    llamadas: list[str] = []
    original = modelo.stream_response

    def contar(request: LLMRequest) -> Iterable[LLMStreamEvent]:
        llamadas.append(request.input_text)
        return original(request)

    modelo.stream_response = contar  # type: ignore[method-assign]
    caso = TrickQuestionsUseCase(
        _Identidades(),  # type: ignore[arg-type]
        local_chat_provider=lambda: modelo,
        judge=_Juez(),
    )
    pendientes: list[QRunnable] = []
    ventana = TrickQuestionsDialog(caso, run_worker=pendientes.append)
    qtbot.addWidget(ventana)

    ventana.start_button.click()
    ventana.reject()
    [trabajador] = pendientes
    trabajador.run()

    assert llamadas == []


def test_con_la_charla_fuera_de_este_ordenador_la_ventana_no_se_abre(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    dependencias = build_conversation_dependencies(
        rutas.data_dir / "sirius.db", tmp_path / "copias", secret_store=FakeSecretStore()
    )
    dependencias.initial_project_use_case.create_initial_project("Charla", "Charlar")
    avisos: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: avisos.append(str(args[2])))
    monkeypatch.setattr(TrickQuestionsDialog, "exec", lambda self: pytest.fail("se abrió"))
    ventana = _build_main_window(dependencias, [])
    qtbot.addWidget(ventana)

    ventana.trick_questions_button.click()

    [aviso] = avisos
    assert "Elige uno antes con la prueba a ciegas" in aviso
