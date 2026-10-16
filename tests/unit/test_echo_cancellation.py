"""La cancelación de eco de verdad, cableada con una APM de mentira (ADR-245).

``livekit`` es del extra ``voz``, que Quality no instala: aquí se pone una APM de mentira
que apunta lo que le dan, en orden, y se mira cómo la usa Sirius. Que aparte el eco de
verdad se midió con la APM de verdad en Linux (ADR-245, «Comprobación») y lo mide el
propietario en su ordenador (E-R03-03).
"""

from __future__ import annotations

import sys
import types
from array import array
from itertools import pairwise
from typing import Any

import pytest

from sirius.adapters.audio.echo_cancellation import (
    ECHO_REACH_SECONDS,
    ECHO_TAIL_SECONDS,
    FRAME_SAMPLES,
    RENDER_KEPT_SECONDS,
    WebRtcEchoCanceller,
    _Resampler,
    load_echo_canceller,
)
from sirius.ports.local_voice import Captured

_MICRO = 16_000
_VOZ = 22_050


def _muestras(*valores: int) -> bytes:
    return array("h", valores).tobytes()


def _de(datos: bytes) -> list[int]:
    return list(memoryview(datos).cast("h"))


class _Trama:
    """Como ``livekit.rtc.AudioFrame``: muestras de 16 bits que la APM cambia en su sitio."""

    def __init__(self, data: bytearray, sample_rate: int, channels: int, samples: int) -> None:
        assert (sample_rate, channels, samples) == (_MICRO, 1, FRAME_SAMPLES)
        assert len(data) == samples * 2
        self._data = data

    @property
    def data(self) -> memoryview:
        return memoryview(self._data).cast("h")


class _Apm:
    """Apunta lo que le dan, en orden; lo captado lo devuelve sumándole 1 a cada muestra."""

    def __init__(self) -> None:
        self.llamadas: list[tuple[str, Any]] = []

    def set_stream_delay_ms(self, retraso: int) -> None:
        self.llamadas.append(("retraso", retraso))

    def process_reverse_stream(self, trama: _Trama) -> None:
        self.llamadas.append(("suena", list(trama.data)))

    def process_stream(self, trama: _Trama) -> None:
        self.llamadas.append(("capta", list(trama.data)))
        for indice, muestra in enumerate(trama.data):
            trama.data[indice] = muestra + 1


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


def _cancelador(frecuencia: int = _MICRO) -> tuple[WebRtcEchoCanceller, _Apm, _Reloj]:
    apm, reloj = _Apm(), _Reloj()
    cancelador = WebRtcEchoCanceller(apm, _Trama, render_rate=frecuencia, clock=reloj)
    return cancelador, apm, reloj


def _trozo(valor: int, muestras: int = 512) -> bytes:
    return _muestras(*([valor] * muestras))


def test_lo_que_suena_entra_en_la_apm_antes_que_lo_captado_a_su_hora() -> None:
    cancelador, apm, reloj = _cancelador()
    cancelador.played(_trozo(1000, FRAME_SAMPLES), at=1.0)
    cancelador.played(_trozo(2000, FRAME_SAMPLES), at=2.0)

    # Captado a los 1,5 s, aunque se limpie a los 3 s: lo que se oyó a los 2 s aún no.
    reloj.ahora = 3.0
    cancelador.clean(Captured(_trozo(5, FRAME_SAMPLES), age=1.5))

    assert [que for que, _ in apm.llamadas] == ["suena", "retraso", "capta"]
    assert apm.llamadas[0][1] == [1000] * FRAME_SAMPLES
    cancelador.clean(Captured(_trozo(5, FRAME_SAMPLES), age=0.5))
    assert [que for que, _ in apm.llamadas[3:]] == ["suena", "retraso", "capta"]
    assert apm.llamadas[3][1] == [2000] * FRAME_SAMPLES


def test_lo_limpio_sale_de_la_apm_entero_y_con_una_trama_de_retraso_como_mucho() -> None:
    cancelador, apm, _reloj = _cancelador()

    salidas = [_de(cancelador.clean(Captured(_trozo(10))).chunk) for _ in range(5)]

    assert [len(salida) for salida in salidas] == [512] * 5
    # La salida empieza con una trama de silencio, y después va lo que devolvió la APM.
    seguido = [m for salida in salidas for m in salida]
    assert seguido[:FRAME_SAMPLES] == [0] * FRAME_SAMPLES
    assert set(seguido[FRAME_SAMPLES:]) == {11}
    # La APM recibe tramas de 10 ms, todas las que caben: 5 x 512 = 16 x 160.
    assert [que for que, _ in apm.llamadas].count("capta") == 16


def test_le_dice_a_la_apm_el_retraso_antes_de_cada_trozo() -> None:
    cancelador, apm, _reloj = _cancelador()

    cancelador.clean(Captured(_trozo(0)))

    assert apm.llamadas[0][0] == "retraso"
    assert all(que == "capta" for que, _ in apm.llamadas[1:])


def test_dice_si_su_voz_sonaba_cuando_el_micro_capto_el_trozo() -> None:
    cancelador, _apm, reloj = _cancelador()
    bloque = _trozo(3000, 1600)  # 0,1 s con voz
    cancelador.played(bloque, at=1.0)
    cancelador.played(_trozo(0, 1600), at=1.1)  # silencio: no cuenta
    fin = 1.1 + ECHO_TAIL_SECONDS

    reloj.ahora = fin - 0.01
    assert cancelador.clean(Captured(_trozo(0))).echoing
    reloj.ahora = fin + 0.01
    assert not cancelador.clean(Captured(_trozo(0))).echoing


def test_antes_de_que_suene_nada_no_hay_eco() -> None:
    cancelador, _apm, reloj = _cancelador()
    cancelador.played(_trozo(3000, 1600), at=5.0)

    reloj.ahora = 4.0
    assert not cancelador.clean(Captured(_trozo(0))).echoing


def _suena_cada_decima(cancelador: WebRtcEchoCanceller, hasta: float) -> None:
    """El altavoz da una trama de 10 ms cada décima de segundo, de 0 a ``hasta``."""
    for decima in range(round(hasta * 10)):
        cancelador.played(_trozo(1000, FRAME_SAMPLES), at=decima / 10)


def test_lo_que_sono_mucho_antes_de_lo_captado_no_se_le_da_a_la_apm() -> None:
    # Con el micro cerrado nadie limpia: al abrirlo, lo que sonó mientras tanto no deja eco
    # en lo que capta, y dárselo a la APM haría esperar al oído.
    cancelador, apm, reloj = _cancelador()
    _suena_cada_decima(cancelador, 60)
    reloj.ahora = 60.0

    cancelador.clean(Captured(_trozo(5, FRAME_SAMPLES)))

    # Solo lo que sonó en el último segundo antes de captarlo.
    assert ECHO_REACH_SECONDS == 1.0
    assert [que for que, _ in apm.llamadas].count("suena") == 10


def test_si_nadie_limpia_lo_que_suena_se_guarda_solo_lo_ultimo() -> None:
    cancelador, apm, reloj = _cancelador()
    _suena_cada_decima(cancelador, RENDER_KEPT_SECONDS + 80)
    reloj.ahora = RENDER_KEPT_SECONDS + 80

    # Captado hace dos minutos y medio: lo que sonaba entonces ya no está.
    cancelador.clean(Captured(_trozo(5, FRAME_SAMPLES), age=150))
    assert [que for que, _ in apm.llamadas].count("suena") == 0
    # Lo de hace un minuto, sí: lo que sonó el segundo antes de captarlo.
    cancelador.clean(Captured(_trozo(5, FRAME_SAMPLES), age=60.05))
    assert [que for que, _ in apm.llamadas].count("suena") == 10


def test_lo_que_suena_se_pasa_a_la_frecuencia_del_micro_sin_cortes_entre_bloques() -> None:
    remuestreo = _Resampler(_VOZ, _MICRO)
    rampa = list(range(2 * 2205))  # 0,2 s de una rampa
    salida: list[int] = []

    for inicio in range(0, len(rampa), 512):
        salida += _de(remuestreo.push(_muestras(*rampa[inicio : inicio + 512])))

    paso = _VOZ / _MICRO
    assert abs(len(salida) - len(rampa) * _MICRO / _VOZ) <= 1
    assert all(abs((b - a) - paso) <= 1 for a, b in pairwise(salida))
    assert salida[0] == 0


def test_a_la_misma_frecuencia_pasa_tal_cual() -> None:
    assert _Resampler(_MICRO, _MICRO).push(_muestras(1, 2, 3)) == _muestras(1, 2, 3)


def test_sin_livekit_no_hay_cancelador_y_sirius_no_cae(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "livekit", None)
    monkeypatch.setitem(sys.modules, "livekit.rtc", None)

    assert load_echo_canceller(_VOZ) is None


def _livekit(monkeypatch: pytest.MonkeyPatch, apm: type[Any]) -> None:
    rtc = types.ModuleType("livekit.rtc")
    rtc.AudioProcessingModule = apm  # type: ignore[attr-defined]
    rtc.AudioFrame = _Trama  # type: ignore[attr-defined]
    livekit = types.ModuleType("livekit")
    livekit.rtc = rtc  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "livekit", livekit)
    monkeypatch.setitem(sys.modules, "livekit.rtc", rtc)


def test_si_la_apm_no_arranca_no_hay_cancelador(monkeypatch: pytest.MonkeyPatch) -> None:
    class _ApmQueNoArranca:
        def __init__(self, **opciones: Any) -> None:
            raise OSError("no se encuentra la biblioteca")

    _livekit(monkeypatch, _ApmQueNoArranca)

    assert load_echo_canceller(_VOZ) is None


def test_carga_la_apm_con_la_cancelacion_de_eco_puesta(monkeypatch: pytest.MonkeyPatch) -> None:
    creadas: list[dict[str, Any]] = []

    class _ApmQueApunta(_Apm):
        def __init__(self, **opciones: Any) -> None:
            super().__init__()
            creadas.append(opciones)

    _livekit(monkeypatch, _ApmQueApunta)

    cancelador = load_echo_canceller(_VOZ)

    assert isinstance(cancelador, WebRtcEchoCanceller)
    assert creadas == [{"echo_cancellation": True, "high_pass_filter": True}]
