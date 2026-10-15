"""El puente entre el hilo del oído y el de la ventana (ADR-244).

El oído pregunta y avisa desde su hilo; la ventana contesta y se entera en el suyo. Desde
el hilo de la ventana todo es directo; desde otro, la pregunta espera a que la ventana la
conteste, y los avisos le llegan en su hilo.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Sequence

import pytest
from pytestqt.qtbot import QtBot

from sirius.application.local_listening import HeardTurn
from sirius.presentation.listening_bridge import ListeningBridge

pytestmark = pytest.mark.gui


class _Ventana:
    """Hace de la ventana: apunta en qué hilo le llega cada cosa y contesta lo que se le
    diga."""

    def __init__(self, espera: Sequence[threading.Event] | None = ()) -> None:
        self.espera = espera
        self.falla: Exception | None = None
        self.preguntas: list[tuple[str, str, int]] = []
        self.acabados: list[tuple[HeardTurn | None, int]] = []
        self.paros: list[tuple[str, int]] = []

    def begin_voice_turn(self, operation_id: str, heard: str) -> Sequence[threading.Event] | None:
        self.preguntas.append((operation_id, heard, threading.get_ident()))
        if self.falla is not None:
            raise self.falla
        return self.espera

    def finish_voice_turn(self, turn: HeardTurn | None) -> None:
        self.acabados.append((turn, threading.get_ident()))

    def listening_stopped(self, notice: str) -> None:
        self.paros.append((notice, threading.get_ident()))


class _Hilo(threading.Thread):
    """El hilo del oído: hace una cosa y guarda lo que devuelve."""

    def __init__(self, hacer: object) -> None:
        super().__init__(daemon=True)
        self._hacer = hacer
        self.resultado: object = None

    def run(self) -> None:
        assert callable(self._hacer)
        self.resultado = self._hacer()


def _turno() -> HeardTurn:
    return HeardTurn("Sirius, hola", True, None, "op-1")


def test_desde_el_hilo_de_la_ventana_pregunta_directamente(qtbot: QtBot) -> None:
    ventana = _Ventana()
    puente = ListeningBridge(ventana)

    assert puente.may_answer("op-1", "Sirius, hola")
    assert ventana.preguntas == [("op-1", "Sirius, hola", threading.get_ident())]


def test_si_la_ventana_no_lo_deja_ir_el_turno_no_va(qtbot: QtBot) -> None:
    ventana = _Ventana(espera=None)
    puente = ListeningBridge(ventana)

    assert not puente.may_answer("op-1", "Sirius, hola")


def test_si_la_ventana_falla_al_preguntarle_el_turno_no_va_y_solo_se_apunta_el_tipo(
    qtbot: QtBot, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        logging.getLogger("sirius.presentation.listening_bridge"), "disabled", False
    )
    ventana = _Ventana()
    ventana.falla = RuntimeError("la clave es Zarzamora")
    puente = ListeningBridge(ventana)

    with caplog.at_level(logging.ERROR):
        assert not puente.may_answer("op-1", "Sirius, hola")

    assert "(RuntimeError)" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()


def test_desde_otro_hilo_la_pregunta_se_contesta_en_el_de_la_ventana(qtbot: QtBot) -> None:
    ventana = _Ventana()
    puente = ListeningBridge(ventana)
    oido = _Hilo(lambda: puente.may_answer("op-1", "Sirius, hola"))

    oido.start()
    qtbot.waitUntil(lambda: not oido.is_alive(), timeout=5000)

    assert oido.resultado is True
    assert ventana.preguntas == [("op-1", "Sirius, hola", threading.get_ident())]


def test_desde_otro_hilo_espera_a_que_acabe_lo_de_segundo_plano(qtbot: QtBot) -> None:
    juez = threading.Event()
    ventana = _Ventana(espera=[juez])
    puente = ListeningBridge(ventana)
    oido = _Hilo(lambda: puente.may_answer("op-1", "Sirius, hola"))

    oido.start()
    qtbot.waitUntil(lambda: bool(ventana.preguntas), timeout=5000)
    oido.join(0.2)
    assert oido.is_alive(), "entregó el turno con el juez aún puntuando"
    juez.set()
    oido.join(5)

    assert oido.resultado is True


def test_los_avisos_llegan_a_la_ventana_en_su_hilo(qtbot: QtBot) -> None:
    ventana = _Ventana()
    puente = ListeningBridge(ventana)
    turno = _turno()

    def avisa() -> None:
        puente.answered(turno)
        puente.answered(None)
        puente.stopped("No puedo oírte.")

    oido = _Hilo(avisa)
    oido.start()
    oido.join(5)
    qtbot.waitUntil(lambda: len(ventana.acabados) == 2 and bool(ventana.paros), timeout=5000)

    aqui = threading.get_ident()
    assert ventana.acabados == [(turno, aqui), (None, aqui)]
    assert ventana.paros == [("No puedo oírte.", aqui)]


def test_desde_el_hilo_de_la_ventana_los_avisos_llegan_en_el_acto(qtbot: QtBot) -> None:
    ventana = _Ventana()
    puente = ListeningBridge(ventana)
    turno = _turno()

    puente.answered(turno)
    puente.stopped("No puedo oírte.")

    assert [t for t, _ in ventana.acabados] == [turno]
    assert [n for n, _ in ventana.paros] == ["No puedo oírte."]


def test_si_la_ventana_falla_al_enterarse_no_rompe_al_oido(
    qtbot: QtBot, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        logging.getLogger("sirius.presentation.listening_bridge"), "disabled", False
    )

    class _Rota(_Ventana):
        def finish_voice_turn(self, turn: HeardTurn | None) -> None:
            raise RuntimeError("rota")

        def listening_stopped(self, notice: str) -> None:
            raise RuntimeError("rota")

    puente = ListeningBridge(_Rota())

    with caplog.at_level(logging.ERROR):
        puente.answered(_turno())
        puente.stopped("No puedo oírte.")

    assert caplog.text.count("(RuntimeError)") == 2
