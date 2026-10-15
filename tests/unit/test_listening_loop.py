"""El bucle que atiende al oído en su hilo mientras la ventana está abierta (ADR-244)."""

from __future__ import annotations

import logging
import threading

import pytest

from sirius.application.listening_loop import PAUSE_SECONDS, ListeningLoop
from sirius.application.local_listening import Attended, HeardTurn


class _Oido:
    """Apunta cada vez que lo atienden; devuelve lo que se le diga, o falla."""

    def __init__(self, respuestas: list[Attended | Exception] | None = None) -> None:
        self.respuestas = list(respuestas or [])
        self.atenciones = 0
        self.atendido = threading.Event()

    def attend(self) -> Attended:
        self.atenciones += 1
        self.atendido.set()
        if self.respuestas:
            respuesta = self.respuestas.pop(0)
            if isinstance(respuesta, Exception):
                raise respuesta
            return respuesta
        return Attended()


def _turno() -> HeardTurn:
    return HeardTurn("Sirius, hola", True, None, "op-1")


def _espera(condicion: threading.Event) -> None:
    assert condicion.wait(5)


def test_la_pausa_es_la_del_micro_de_verdad() -> None:
    assert PAUSE_SECONDS == 0.03


def test_atiende_en_su_hilo_hasta_que_se_le_pide_parar() -> None:
    oido = _Oido()
    bucle = ListeningLoop(oido, pause_seconds=0.001)

    bucle.start()
    _espera(oido.atendido)
    assert bucle.running
    bucle.stop()

    assert bucle.wait(5)
    assert not bucle.running


def test_si_trae_turnos_vuelve_a_atender_sin_esperar() -> None:
    # Una pausa larguísima: si esperara tras un turno, no daría la segunda vuelta.
    oido = _Oido([Attended(turns=(_turno(),)), Attended(turns=(_turno(),))])
    hecho = threading.Event()
    atiende = oido.attend

    def atiende_y_avisa() -> Attended:
        respuesta = atiende()
        if oido.atenciones == 3:
            hecho.set()
        return respuesta

    oido.attend = atiende_y_avisa  # type: ignore[method-assign]
    bucle = ListeningLoop(oido, pause_seconds=60)
    bucle.start()
    try:
        _espera(hecho)
    finally:
        bucle.stop()
        assert bucle.wait(5)


def test_si_no_llega_nada_espera_la_pausa_antes_de_volver() -> None:
    oido = _Oido()
    bucle = ListeningLoop(oido, pause_seconds=60)
    bucle.start()
    try:
        _espera(oido.atendido)
        assert not bucle.wait(0.2)
        assert oido.atenciones == 1
    finally:
        bucle.stop()
        assert bucle.wait(5)


def test_un_fallo_que_se_escapa_no_lo_mata_y_solo_apunta_el_tipo(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logging.getLogger("sirius.application.listening_loop"), "disabled", False)
    oido = _Oido([RuntimeError("la clave es Zarzamora")])
    dos = threading.Event()
    atiende = oido.attend

    def atiende_y_cuenta() -> Attended:
        try:
            return atiende()
        finally:
            if oido.atenciones == 2:
                dos.set()

    oido.attend = atiende_y_cuenta  # type: ignore[method-assign]
    bucle = ListeningLoop(oido, pause_seconds=60, failure_pause_seconds=0.001)
    with caplog.at_level(logging.ERROR):
        bucle.start()
        try:
            _espera(dos)
        finally:
            bucle.stop()
            assert bucle.wait(5)

    assert "El oído se interrumpió (RuntimeError)" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()


def test_tras_un_fallo_espera_antes_de_volver_a_intentarlo() -> None:
    oido = _Oido([RuntimeError("roto")])
    bucle = ListeningLoop(oido, pause_seconds=0.001, failure_pause_seconds=60)
    bucle.start()
    try:
        _espera(oido.atendido)
        assert not bucle.wait(0.2)
        assert oido.atenciones == 1
    finally:
        bucle.stop()
        assert bucle.wait(5)


def test_parar_o_esperar_sin_haber_arrancado_no_falla() -> None:
    bucle = ListeningLoop(_Oido())

    bucle.stop()

    assert bucle.wait(0.1)
    assert not bucle.running
