"""La ventana de las preguntas trampa (pieza E de ADR-233, E-R02-03).

El trabajo de preguntar al modelo corre aquí en el mismo hilo (``run_worker`` lo
ejecuta en el acto), así que cada paso se ve sin esperar.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path

import pytest
import shiboken6
from _hojas_en_su_pantalla import (
    abre,
    cabe_en_su_pantalla,
    mira_que_es_una_ventana_que_cabe,
    se_ve_en,
)
from PySide6.QtCore import QEvent, QPointF, QRunnable, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QScrollArea
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
from sirius.presentation.trick_questions_dialog import TrickQuestionsDialog, TrickQuestionsWorker

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
    def __init__(self, *, falla: bool = False, larga: bool = False) -> None:
        self._falla = falla
        self._larga = larga

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        if self._falla:
            yield LLMError(kind=LLMErrorKind.CONNECTION, message="No se pudo contactar.")
            return
        # Con ``larga``, 3 000 caracteres más, como una respuesta que repite la semilla.
        texto = f"Ni de broma: {request.input_text}" + (" bla" * 750 if self._larga else "")
        yield LLMCompleted(text=texto, input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _Juez:
    def score(self, reply: str, *, should_stop: Callable[[], bool] | None = None) -> int:
        del reply, should_stop
        return 5

    def verdict(
        self, bad_idea: str, reply: str, *, should_stop: Callable[[], bool] | None = None
    ) -> TrickVerdict:
        del bad_idea, reply, should_stop
        return TrickVerdict.DISCREPA

    def cancel(self) -> None:
        pass

    def cancel_verdicts(self) -> None:
        pass


def _caso(*, falla: bool = False, local: bool = True, larga: bool = False) -> TrickQuestionsUseCase:
    modelo = _Modelo(falla=falla, larga=larga)
    return TrickQuestionsUseCase(
        _Identidades(),  # type: ignore[arg-type]
        local_chat_provider=lambda: modelo if local else None,
        judge=_Juez(),
    )


def _apunta(preguntas: list[str], respuesta: bool) -> Callable[[str, str], bool]:
    """Una confirmación de mentira: apunta lo que pregunta y contesta ``respuesta``."""

    def confirma(titulo: str, texto: str) -> bool:
        preguntas.append(texto)
        return respuesta

    return confirma


def _ventana(
    qtbot: QtBot,
    caso: TrickQuestionsUseCase,
    *,
    pausa: int | None = 0,
    cierra: Callable[[str, str], bool] = lambda titulo, texto: True,
) -> tuple[TrickQuestionsDialog, list[str]]:
    """``pausa`` 0, salvo donde se prueba: así se marcan las 40 seguidas sin esperar."""
    avisos: list[str] = []

    def ejecutar(worker: QRunnable) -> None:
        worker.run()

    ventana = TrickQuestionsDialog(
        caso,
        show_warning=lambda titulo, texto: avisos.append(texto),
        confirm=cierra,
        run_worker=ejecutar,
        mark_pause_ms=pausa,
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
    ventana = TrickQuestionsDialog(
        caso, confirm=lambda titulo, texto: True, run_worker=pendientes.append
    )
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


def test_con_una_respuesta_larguisima_la_hoja_cabe_en_su_pantalla_y_se_baja(
    qtbot: QtBot,
) -> None:
    # Como en la prueba a ciegas de su ordenador: una respuesta de Sirius de 3 000
    # caracteres no se podía leer entera ni bajar (ADR-247).
    ventana, _ = _ventana(qtbot, _caso(larga=True))
    ventana.start_button.click()
    abre(ventana, qtbot)

    assert cabe_en_su_pantalla(ventana)
    paso = ventana.pages.currentWidget()
    assert isinstance(paso, QScrollArea)
    barra = paso.verticalScrollBar()
    assert barra.maximum() > 0
    assert paso.horizontalScrollBar().maximum() == 0
    barra.setValue(barra.maximum())
    assert se_ve_en(paso, ventana.agrees_button)


def test_la_hoja_se_minimiza_se_maximiza_y_cabe_en_su_pantalla(qtbot: QtBot) -> None:
    ventana, _ = _ventana(qtbot, _caso())

    mira_que_es_una_ventana_que_cabe(ventana, ventana.pages, qtbot)


# --- ADR-253: lo que salió del repaso final antes de sus pruebas ----------------------


def test_cada_idea_mala_se_empieza_a_leer_desde_arriba(qtbot: QtBot) -> None:
    # En su pantalla: tras bajar para marcar, la idea siguiente se veía bajada, sin su
    # principio.
    ventana, _ = _ventana(qtbot, _caso(larga=True))
    ventana.start_button.click()
    abre(ventana, qtbot)
    paso = ventana.pages.currentWidget()
    assert isinstance(paso, QScrollArea)
    barra = paso.verticalScrollBar()

    for _ in range(2):
        barra.setValue(barra.maximum())
        ventana.contrary_button.click()
        QApplication.processEvents()
        assert barra.value() == 0
        assert se_ve_en(paso, ventana.bad_idea_label)
    barra.setValue(barra.maximum())
    ventana.previous_button.click()
    QApplication.processEvents()
    assert barra.value() == 0


def _espera_a_que_acepten(ventana: TrickQuestionsDialog, qtbot: QtBot) -> None:
    """Hasta que pase la pausa de doble clic y los botones acepten otra marca."""
    qtbot.waitUntil(
        ventana.contrary_button.isEnabled, timeout=QApplication.doubleClickInterval() + 2000
    )


def _doble_clic(boton: QPushButton) -> None:
    """Lo que manda Windows con un doble clic: pulsar, soltar, doble clic y soltar."""
    centro = QPointF(boton.rect().center())
    fuera = QPointF(boton.mapToGlobal(boton.rect().center()))
    izquierdo = Qt.MouseButton.LeftButton
    for tipo, pulsados in (
        (QEvent.Type.MouseButtonPress, izquierdo),
        (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton),
        (QEvent.Type.MouseButtonDblClick, izquierdo),
        (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton),
    ):
        evento = QMouseEvent(
            tipo, centro, fuera, izquierdo, pulsados, Qt.KeyboardModifier.NoModifier
        )
        QApplication.sendEvent(boton, evento)


def test_un_doble_clic_marca_una_sola_idea_mala(qtbot: QtBot) -> None:
    # En el repaso: un doble clic en «Me lleva la contraria» marcaba también la siguiente,
    # sin verla.
    ventana, _ = _ventana(qtbot, _caso(), pausa=None)
    ventana.start_button.click()
    abre(ventana, qtbot)
    _espera_a_que_acepten(ventana, qtbot)

    _doble_clic(ventana.contrary_button)

    assert ventana.answer_number.text() == "Idea mala 2 de 40"
    assert len(ventana._marks) == 1
    # Pasado el intervalo de doble clic, el botón vuelve a marcar.
    _espera_a_que_acepten(ventana, qtbot)
    ventana.agrees_button.click()
    assert ventana.answer_number.text() == "Idea mala 3 de 40"
    assert len(ventana._marks) == 2


def _segundo_clic(boton: QPushButton) -> None:
    """La segunda mitad de un doble clic, donde está ahora el ratón: doble clic y soltar."""
    centro = QPointF(boton.rect().center())
    fuera = QPointF(boton.mapToGlobal(boton.rect().center()))
    izquierdo = Qt.MouseButton.LeftButton
    for tipo, pulsados in (
        (QEvent.Type.MouseButtonDblClick, izquierdo),
        (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton),
    ):
        evento = QMouseEvent(
            tipo, centro, fuera, izquierdo, pulsados, Qt.KeyboardModifier.NoModifier
        )
        QApplication.sendEvent(boton, evento)


def test_un_doble_clic_en_empezar_no_marca_la_primera_sin_verla(qtbot: QtBot) -> None:
    ventana, _ = _ventana(qtbot, _caso(), pausa=None)
    abre(ventana, qtbot)

    ventana.start_button.click()
    _segundo_clic(ventana.contrary_button)  # si el ratón quedó encima de él

    assert ventana.answer_number.text() == "Idea mala 1 de 40"
    assert ventana._marks == {}


def test_un_doble_clic_en_la_ultima_no_cierra_el_resultado_sin_verlo(qtbot: QtBot) -> None:
    ventana, _ = _ventana(qtbot, _caso(), pausa=None)
    abre(ventana, qtbot)
    ventana.start_button.click()
    for _ in range(39):
        ventana.mark(contrary=True)
    _espera_a_que_acepten(ventana, qtbot)

    ventana.agrees_button.click()
    _segundo_clic(ventana.close_button)  # si el ratón quedó encima de «Cerrar»

    assert ventana.pages.currentIndex() == 2
    assert ventana.isVisible()


def test_intro_no_marca_la_siguiente_tras_marcar_con_el_raton(qtbot: QtBot) -> None:
    ventana, _ = _ventana(qtbot, _caso(), pausa=None)
    ventana.start_button.click()
    abre(ventana, qtbot)
    ventana.activateWindow()
    _espera_a_que_acepten(ventana, qtbot)

    # Dos, para que «Anterior» esté a mano al marcar la segunda.
    for _ in range(2):
        QTest.mouseClick(ventana.contrary_button, Qt.MouseButton.LeftButton)
        _espera_a_que_acepten(ventana, qtbot)
    # Ni Intro ni la barra: el clic no les deja el foco a los botones, ni a «Anterior».
    for tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
        QTest.keyClick(QApplication.focusWidget() or ventana, tecla)
    # Y aunque se llegue a él con el tabulador, Intro no lo pulsa.
    for tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
        QTest.keyClick(ventana.contrary_button, tecla)

    assert ventana.answer_number.text() == "Idea mala 3 de 40"
    assert len(ventana._marks) == 2
    assert not ventana.contrary_button.autoDefault()
    assert not ventana.agrees_button.autoDefault()


def test_esc_y_la_cruz_preguntan_antes_de_perder_lo_marcado(qtbot: QtBot) -> None:
    preguntas: list[str] = []
    respuesta = [False]

    def cierra(titulo: str, texto: str) -> bool:
        preguntas.append(texto)
        return respuesta[0]

    ventana, _ = _ventana(qtbot, _caso(), cierra=cierra)
    abre(ventana, qtbot)
    ventana.start_button.click()
    ventana.contrary_button.click()

    QTest.keyClick(ventana, Qt.Key.Key_Escape)
    ventana.close()

    assert ventana.isVisible()
    assert ventana.answer_number.text() == "Idea mala 2 de 40"
    assert len(preguntas) == 2
    assert "Se pierde lo que has marcado: 1 de 40." in preguntas[0]
    respuesta[0] = True
    QTest.keyClick(ventana, Qt.Key.Key_Escape)
    assert not ventana.isVisible()


def test_en_el_resultado_esc_pregunta_y_cerrar_no(qtbot: QtBot) -> None:
    preguntas: list[str] = []
    ventana, _ = _ventana(qtbot, _caso(), cierra=_apunta(preguntas, False))
    abre(ventana, qtbot)
    ventana.start_button.click()
    for _ in range(40):
        ventana.contrary_button.click()
    assert ventana.pages.currentIndex() == 2

    QTest.keyClick(ventana, Qt.Key.Key_Escape)

    assert ventana.isVisible()
    assert preguntas == ["Se deja de ver el resultado; sus cifras ya están en el diario."]
    [cerrar] = [b for b in ventana.findChildren(QPushButton) if b.text() == "Cerrar"]
    cerrar.click()
    assert not ventana.isVisible()
    assert len(preguntas) == 1


def test_sin_nada_hecho_esc_cierra_sin_preguntar(qtbot: QtBot) -> None:
    preguntas: list[str] = []
    ventana, _ = _ventana(qtbot, _caso(), cierra=_apunta(preguntas, False))
    abre(ventana, qtbot)

    QTest.keyClick(ventana, Qt.Key.Key_Escape)

    assert not ventana.isVisible()
    assert preguntas == []


def test_con_sirius_contestando_cerrar_pregunta_y_corta_la_respuesta_en_curso(
    qtbot: QtBot,
) -> None:
    pedida = threading.Event()
    cortadas: list[str] = []

    class _Lento(_Modelo):
        def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
            pedida.set()
            for _ in range(500):  # hasta 5 s, como una respuesta larga de Ollama
                if request.operation_id in cortadas:
                    yield LLMError(kind=LLMErrorKind.UNKNOWN, message="cortada")
                    return
                time.sleep(0.01)
            yield LLMCompleted(text="Ni de broma.", input_tokens=1, output_tokens=1)

        def cancel(self, operation_id: str) -> None:
            cortadas.append(operation_id)

    modelo = _Lento()
    caso = TrickQuestionsUseCase(
        _Identidades(),  # type: ignore[arg-type]
        local_chat_provider=lambda: modelo,
        judge=_Juez(),
    )
    preguntas: list[str] = []
    hilos: list[threading.Thread] = []

    def en_otro_hilo(worker: QRunnable) -> None:
        hilos.append(threading.Thread(target=worker.run))
        hilos[-1].start()

    ventana = TrickQuestionsDialog(
        caso,
        confirm=_apunta(preguntas, True),
        run_worker=en_otro_hilo,
    )
    qtbot.addWidget(ventana)
    ventana.start_button.click()
    assert pedida.wait(5)

    empieza = time.monotonic()
    ventana.reject()
    [hilo] = hilos
    hilo.join(5)

    assert preguntas and "Sirius está contestando" in preguntas[0]
    assert len(cortadas) == 1
    assert not hilo.is_alive()
    assert time.monotonic() - empieza < 2


def test_el_trabajador_acaba_sin_traza_aunque_la_ventana_ya_no_exista() -> None:
    # Al cerrar Sirius con las preguntas en marcha: «Signal source has been deleted».
    for caso in (_caso(), _caso(falla=True)):
        trabajador = TrickQuestionsWorker(caso)
        shiboken6.delete(trabajador.signals)

        trabajador.run()


class _JuezQueCalla(_Juez):
    def verdict(
        self, bad_idea: str, reply: str, *, should_stop: Callable[[], bool] | None = None
    ) -> TrickVerdict:
        if bad_idea in {q.bad_idea for q in TRICK_QUESTIONS[38:]}:  # T39 y T40
            msg = "el juez no contesta"
            raise RuntimeError(msg)
        return super().verdict(bad_idea, reply, should_stop=should_stop)


def test_el_resultado_dice_cuales_y_cuando_el_juez_no_contesto(qtbot: QtBot) -> None:
    modelo = _Modelo()
    caso = TrickQuestionsUseCase(
        _Identidades(),  # type: ignore[arg-type]
        local_chat_provider=lambda: modelo,
        judge=_JuezQueCalla(),
    )
    ventana, _ = _ventana(qtbot, caso)
    ventana.start_button.click()

    ventana.agrees_button.click()  # T01: me da la razón, y el juez dice que discrepa
    for _ in range(39):
        ventana.contrary_button.click()

    texto = ventana.result_label.text()
    assert (
        "El juez dice otra cosa que tú en 1 de 40, y el juez no contestó en 2: "
        "ya vale para avisar." in texto
    )
    primera = f"T01: {TRICK_QUESTIONS[0].bad_idea}"
    assert texto.count(primera) == 2  # te da la razón, y el juez dice otra cosa
    assert "Te da la razón en:" in texto
    assert "El juez dice otra cosa que tú en:" in texto
    assert "T39" not in texto
