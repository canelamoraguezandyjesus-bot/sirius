"""El oído de verdad, cableado con módulos de mentira en lugar de sus bibliotecas (ADR-242).

Las bibliotecas son del extra ``voz``, que Quality no instala: aquí se pone un módulo de
mentira en el sitio de cada una y se mira cómo las usa Sirius. Que suenen y acierten lo
mira el propietario en su ordenador (E-R03-01). Lo que sí se mira aquí, porque es lo que
cierra la puerta a bajar algo o a guardar audio: el modelo se carga solo de su carpeta y
con ``local_files_only``, y Smart Turn no puede escribir el audio de cada turno.
"""

from __future__ import annotations

import ast
import importlib.abc
import importlib.machinery
import os
import sys
import types
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

import sirius.adapters.audio.local_listening as local_listening_module
from sirius.adapters.audio.local_listening import (
    BLOCK_SAMPLES,
    SAMPLE_RATE,
    FasterWhisperTranscriber,
    PipecatTurnDetector,
    SoundDeviceMicrophone,
    load_listening_engines,
    load_listening_model,
)
from sirius.ports.local_voice import TurnSignal, VoiceUnavailable

# --- Los módulos de mentira ---------------------------------------------------------


@dataclass
class _Estado:
    name: str


class _PortAudioError(Exception):
    pass


class _Flujo:
    def __init__(self, **opciones: Any) -> None:
        self.opciones = opciones
        self.arrancado = False
        self.parado = False
        self.cerrado = False
        self.falla_al_arrancar = False
        self.falla_al_parar = False
        self.falla_al_cerrar = False

    def start(self) -> None:
        if self.falla_al_arrancar:
            raise _PortAudioError("Error querying device -1")
        self.arrancado = True

    def stop(self) -> None:
        if self.falla_al_parar:
            raise _PortAudioError("Unanticipated host error")
        self.parado = True

    def close(self) -> None:
        if self.falla_al_cerrar:
            raise _PortAudioError("Unanticipated host error")
        self.cerrado = True


@dataclass
class _SoundDevice:
    flujos: list[_Flujo] = field(default_factory=list)
    sin_micro: bool = False
    PortAudioError: type[Exception] = _PortAudioError

    def RawInputStream(self, **opciones: Any) -> _Flujo:
        flujo = _Flujo(**opciones)
        flujo.falla_al_arrancar = self.sin_micro
        self.flujos.append(flujo)
        return flujo


class _Silero:
    """Dice los estados que se le escriban, uno por trozo."""

    def __init__(self, estados: list[str]) -> None:
        self._estados = list(estados)
        self.params = types.SimpleNamespace(start_secs=0.2)
        self.frecuencia: int | None = None
        self.trozos: list[bytes] = []
        self.soltado = False

    async def cleanup(self) -> None:
        self.soltado = True

    def set_sample_rate(self, frecuencia: int) -> None:
        self.frecuencia = frecuencia

    async def analyze_audio(self, trozo: bytes) -> _Estado:
        self.trozos.append(trozo)
        return _Estado(self._estados.pop(0))


class _SmartTurn:
    def __init__(self) -> None:
        self.frecuencia: int | None = None
        self.anadidos: list[tuple[bytes, bool]] = []
        self.inicios: list[float] = []
        self.analisis = 0
        self.completo_al_anadir: set[int] = set()
        self.veredicto = "INCOMPLETE"
        self.soltado = False

    async def cleanup(self) -> None:
        self.soltado = True

    def set_sample_rate(self, frecuencia: int) -> None:
        self.frecuencia = frecuencia

    def update_vad_start_secs(self, segundos: float) -> None:
        self.inicios.append(segundos)

    def append_audio(self, trozo: bytes, hablando: bool) -> _Estado:
        self.anadidos.append((trozo, hablando))
        if len(self.anadidos) - 1 in self.completo_al_anadir:
            return _Estado("COMPLETE")
        return _Estado("INCOMPLETE")

    async def analyze_end_of_turn(self) -> tuple[_Estado, None]:
        self.analisis += 1
        return _Estado(self.veredicto), None


@dataclass
class _Segmento:
    text: str


class _Whisper:
    creados: list[tuple[tuple[Any, ...], dict[str, Any]]] = []  # noqa: RUF012
    falla_al_cargar: Exception | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        falla = type(self).falla_al_cargar
        if falla is not None:
            raise falla
        type(self).creados.append((args, kwargs))
        self.pedidos: list[tuple[Any, dict[str, Any]]] = []

    def transcribe(self, audio: Any, **opciones: Any) -> tuple[Iterator[_Segmento], object]:
        self.pedidos.append((audio, opciones))
        return iter([_Segmento(" Hola, "), _Segmento("qué tal "), _Segmento("  ")]), object()


class _Muestras:
    def __init__(self, datos: bytes, tipo: str) -> None:
        self.datos = datos
        self.tipo = tipo

    def astype(self, tipo: str) -> _Muestras:
        return _Muestras(self.datos, tipo)

    def __truediv__(self, divisor: float) -> tuple[bytes, str, float]:
        return (self.datos, self.tipo, divisor)


def _numpy() -> types.ModuleType:
    modulo = types.ModuleType("numpy")
    modulo.int16 = "int16"  # type: ignore[attr-defined]
    modulo.float32 = "float32"  # type: ignore[attr-defined]
    modulo.frombuffer = lambda datos, dtype: _Muestras(datos, dtype)  # type: ignore[attr-defined]
    return modulo


@dataclass
class _Loguru:
    llamadas: list[tuple[str, Any]] = field(default_factory=list)

    def remove(self) -> None:
        self.llamadas.append(("remove", None))

    def add(self, destino: Any, *, level: str) -> None:
        self.llamadas.append(("add", level))


@dataclass
class _Bibliotecas:
    sounddevice: _SoundDevice
    loguru: _Loguru
    analizadores: list[Any]


@pytest.fixture
def bibliotecas(monkeypatch: pytest.MonkeyPatch) -> _Bibliotecas:
    """Pone un módulo de mentira en el sitio de cada biblioteca del extra ``voz``."""
    monkeypatch.setattr(_Whisper, "creados", [])
    sounddevice = _SoundDevice()
    loguru = _Loguru()
    analizadores: list[Any] = []

    def modulo(nombre: str, **atributos: Any) -> None:
        nuevo = types.ModuleType(nombre)
        for clave, valor in atributos.items():
            setattr(nuevo, clave, valor)
        monkeypatch.setitem(sys.modules, nombre, nuevo)

    def silero(*, sample_rate: int) -> _Silero:
        analizador = _Silero([])
        analizador.creado_a = sample_rate  # type: ignore[attr-defined]
        analizadores.append(analizador)
        return analizador

    def smart_turn(*, sample_rate: int) -> _SmartTurn:
        analizador = _SmartTurn()
        analizador.creado_a = sample_rate  # type: ignore[attr-defined]
        analizadores.append(analizador)
        return analizador

    monkeypatch.setitem(sys.modules, "numpy", _numpy())
    monkeypatch.setitem(sys.modules, "sounddevice", sounddevice)
    modulo("faster_whisper", WhisperModel=_Whisper)
    modulo("loguru", logger=loguru)
    for paquete in ("pipecat", "pipecat.audio", "pipecat.audio.turn", "pipecat.audio.vad"):
        modulo(paquete)
    modulo("pipecat.audio.turn.smart_turn")
    modulo("pipecat.audio.turn.smart_turn.local_smart_turn_v3", LocalSmartTurnAnalyzerV3=smart_turn)
    modulo("pipecat.audio.vad.silero", SileroVADAnalyzer=silero)
    return _Bibliotecas(sounddevice, loguru, analizadores)


# --- Cargar el oído -----------------------------------------------------------------


def test_sin_el_extra_instalado_no_carga_y_lo_arregla_la_orden_de_instalar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(sys.modules, "numpy", None)

    with pytest.raises(VoiceUnavailable) as fallo:
        load_listening_engines(tmp_path)

    assert fallo.value.fixed_by_install
    assert "numpy" in fallo.value.reason


class _NoCarga(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Una biblioteca nativa que está pero no carga lo suyo: falla al importarse con OSError,
    como sounddevice sin PortAudio o CTranslate2 si una de sus DLL no carga."""

    def __init__(self, nombre: str) -> None:
        self._nombre = nombre

    def find_spec(self, nombre: str, *args: object) -> importlib.machinery.ModuleSpec | None:
        if nombre != self._nombre:
            return None
        return importlib.machinery.ModuleSpec(nombre, self)

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> None:
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        raise OSError("PortAudio library not found" if self._nombre == "sounddevice" else "DLL")


def test_si_una_biblioteca_nativa_no_carga_tampoco_se_cae(
    bibliotecas: _Bibliotecas, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delitem(sys.modules, "sounddevice")
    monkeypatch.setattr(sys, "meta_path", [_NoCarga("sounddevice"), *sys.meta_path])

    with pytest.raises(VoiceUnavailable) as fallo:
        load_listening_engines(tmp_path)

    assert fallo.value.fixed_by_install
    assert "PortAudio" in fallo.value.reason


def test_si_faster_whisper_no_carga_con_oserror_tambien_lo_dice(
    bibliotecas: _Bibliotecas, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Ronda 3 de Codex sobre la PR #687: CTranslate2 carga sus DLL con ctypes y puede
    # fallar con OSError; el import que se movió en la ronda 2 solo atrapaba ImportError.
    monkeypatch.delitem(sys.modules, "faster_whisper")
    monkeypatch.setattr(sys, "meta_path", [_NoCarga("faster_whisper"), *sys.meta_path])

    with pytest.raises(VoiceUnavailable) as fallo:
        load_listening_model(tmp_path)

    assert fallo.value.fixed_by_install
    assert "faster_whisper no carga" in fallo.value.reason


def test_ninguna_funcion_del_oido_importa_por_su_cuenta() -> None:
    # Todas las bibliotecas del oído entran por `_import`, que traduce ImportError y
    # OSError: un import suelto dentro de una función es como volvió el fallo de H-242.
    fuente = Path(local_listening_module.__file__).read_text(encoding="utf-8")
    sueltos = [
        f"{funcion.name}:{nodo.lineno}"
        for funcion in ast.walk(ast.parse(fuente))
        if isinstance(funcion, ast.FunctionDef | ast.AsyncFunctionDef)
        for nodo in ast.walk(funcion)
        if isinstance(nodo, ast.Import | ast.ImportFrom)
    ]

    assert sueltos == []


def test_el_modelo_se_carga_solo_de_su_carpeta_y_sin_bajar_nada(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    load_listening_engines(tmp_path / "faster-whisper-small")

    assert _Whisper.creados == [
        (
            (str(tmp_path / "faster-whisper-small"),),
            {"device": "cpu", "compute_type": "int8", "local_files_only": True},
        )
    ]


def test_smart_turn_no_puede_escribir_el_audio_de_cada_turno(
    bibliotecas: _Bibliotecas, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PIPECAT_SMART_TURN_LOG_DATA", "1")

    load_listening_engines(tmp_path)

    assert "PIPECAT_SMART_TURN_LOG_DATA" not in os.environ


def test_los_analizadores_oyen_a_16_khz_y_pipecat_solo_avisa_por_consola(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    load_listening_engines(tmp_path)

    assert [a.creado_a for a in bibliotecas.analizadores] == [SAMPLE_RATE, SAMPLE_RATE]
    assert [a.frecuencia for a in bibliotecas.analizadores] == [SAMPLE_RATE, SAMPLE_RATE]
    assert bibliotecas.loguru.llamadas == [("remove", None), ("add", "WARNING")]
    assert bibliotecas.sounddevice.flujos == [], "cargar no abre el micro"


def test_si_el_modelo_no_carga_lo_arregla_la_orden_de_instalar(
    bibliotecas: _Bibliotecas, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(_Whisper, "falla_al_cargar", RuntimeError("Unable to open 'model.bin'"))

    with pytest.raises(VoiceUnavailable) as fallo:
        load_listening_engines(tmp_path)

    assert fallo.value.fixed_by_install
    assert "model.bin" in fallo.value.reason


# --- El micro -----------------------------------------------------------------------


def test_el_micro_capta_a_16_khz_mono_en_trozos_de_512_y_los_da_en_orden() -> None:
    sounddevice = _SoundDevice()
    micro = SoundDeviceMicrophone(sounddevice)

    micro.open()
    micro.open()

    (flujo,) = sounddevice.flujos
    assert flujo.arrancado
    callback = flujo.opciones.pop("callback")
    assert flujo.opciones == {
        "samplerate": SAMPLE_RATE,
        "blocksize": BLOCK_SAMPLES,
        "channels": 1,
        "dtype": "int16",
    }
    assert micro.read() is None
    callback(memoryview(b"\x01\x02"), 1, None, None)
    callback(memoryview(b"\x03\x04"), 1, None, None)
    assert micro.read() == b"\x01\x02"
    assert micro.read() == b"\x03\x04"
    assert micro.read() is None


def test_al_cerrar_el_micro_se_tira_lo_que_nadie_leyo() -> None:
    sounddevice = _SoundDevice()
    micro = SoundDeviceMicrophone(sounddevice)
    micro.open()
    callback = sounddevice.flujos[0].opciones["callback"]
    callback(memoryview(b"\x01\x02"), 1, None, None)

    micro.close()

    assert sounddevice.flujos[0].parado
    assert sounddevice.flujos[0].cerrado
    assert micro.read() is None


def test_sin_micro_no_lo_arregla_la_orden_de_instalar_y_no_deja_nada_abierto() -> None:
    sounddevice = _SoundDevice(sin_micro=True)
    micro = SoundDeviceMicrophone(sounddevice)

    with pytest.raises(VoiceUnavailable) as fallo:
        micro.open()

    assert not fallo.value.fixed_by_install
    assert "micrófono" in fallo.value.reason
    assert sounddevice.flujos[0].cerrado, "el flujo que no arrancó se cierra"


def test_si_pararlo_falla_el_micro_se_cierra_igual_tira_lo_captado_y_no_falla() -> None:
    sounddevice = _SoundDevice()
    micro = SoundDeviceMicrophone(sounddevice)
    micro.open()
    flujo = sounddevice.flujos[0]
    flujo.opciones["callback"](memoryview(b"\x01\x02"), 1, None, None)
    flujo.falla_al_parar = True

    micro.close()

    assert flujo.cerrado
    assert micro.read() is None


def test_cerrado_el_micro_no_llega_audio_aunque_portaudio_lo_siga_mandando() -> None:
    # Ronda 3 de Codex sobre la PR #687: si PortAudio no paraba ni cerraba, el flujo seguía
    # captando. Ahora lo que mande una apertura pasada ya no entra, y al volver a abrir
    # solo entra lo del flujo nuevo.
    sounddevice = _SoundDevice()
    micro = SoundDeviceMicrophone(sounddevice)
    micro.open()
    viejo = sounddevice.flujos[0]
    viejo.falla_al_parar = True
    viejo.falla_al_cerrar = True

    micro.close()
    viejo.opciones["callback"](memoryview(b"\x01\x02"), 1, None, None)

    assert micro.read() is None
    micro.open()
    nuevo = sounddevice.flujos[1]
    viejo.opciones["callback"](memoryview(b"\x03\x04"), 1, None, None)
    nuevo.opciones["callback"](memoryview(b"\x05\x06"), 1, None, None)
    assert micro.read() == b"\x05\x06"
    assert micro.read() is None


# --- Silero y Smart Turn, encadenados como en Pipecat -------------------------------


def _detector(estados: list[str]) -> tuple[PipecatTurnDetector, _Silero, _SmartTurn]:
    silero = _Silero(estados)
    smart_turn = _SmartTurn()
    return PipecatTurnDetector(lambda: silero, lambda: smart_turn), silero, smart_turn


def test_sin_voz_no_empieza_turno_y_cada_trozo_pasa_por_los_dos() -> None:
    detector, silero, smart_turn = _detector(["QUIET", "STARTING"])

    assert detector.listen(b"a") is TurnSignal.QUIET
    assert detector.listen(b"b") is TurnSignal.QUIET

    assert silero.trozos == [b"a", b"b"]
    assert smart_turn.anadidos == [(b"a", False), (b"b", False)]
    assert smart_turn.inicios == []


def test_con_voz_confirmada_el_turno_empieza_y_smart_turn_lo_sabe() -> None:
    detector, _, smart_turn = _detector(["SPEAKING", "SPEAKING", "STOPPING"])

    assert [detector.listen(t) for t in (b"a", b"b", b"c")] == [TurnSignal.VOICE] * 3

    assert smart_turn.inicios == [0.2], "una vez, al empezar a hablar"
    assert [hablando for _, hablando in smart_turn.anadidos] == [True, True, True]
    assert smart_turn.analisis == 0


def test_cuando_silero_deja_de_oir_voz_decide_smart_turn() -> None:
    detector, _, smart_turn = _detector(["SPEAKING", "QUIET", "SPEAKING", "QUIET"])
    smart_turn.veredicto = "INCOMPLETE"

    assert detector.listen(b"a") is TurnSignal.VOICE
    assert detector.listen(b"b") is TurnSignal.QUIET, "una pausa a media frase"
    assert smart_turn.analisis == 1

    smart_turn.veredicto = "COMPLETE"
    assert detector.listen(b"c") is TurnSignal.VOICE
    assert detector.listen(b"d") is TurnSignal.ENDED
    assert smart_turn.analisis == 2


def test_el_silencio_largo_acaba_el_turno_aunque_smart_turn_dijera_que_no() -> None:
    detector, _, smart_turn = _detector(["SPEAKING", "QUIET", "QUIET", "QUIET"])
    smart_turn.completo_al_anadir = {3}

    signals = [detector.listen(t) for t in (b"a", b"b", b"c", b"d")]

    assert signals == [TurnSignal.VOICE, TurnSignal.QUIET, TurnSignal.QUIET, TurnSignal.ENDED]
    assert smart_turn.analisis == 1


def test_reiniciar_es_tener_silero_y_smart_turn_nuevos_y_soltar_los_viejos() -> None:
    # Ronda 1 de Codex sobre la PR #687: al parar a media frase, el detector se quedaba
    # en el turno viejo.
    creados: list[tuple[_Silero, _SmartTurn]] = []

    def silero() -> _Silero:
        analizador = _Silero(["SPEAKING", "SPEAKING", "QUIET"])
        creados.append((analizador, _SmartTurn()))
        return analizador

    detector = PipecatTurnDetector(silero, lambda: creados[-1][1])
    assert detector.listen(b"a") is TurnSignal.VOICE

    detector.reset()

    (viejo_silero, viejo_turno), (nuevo_silero, nuevo_turno) = creados
    assert viejo_silero.soltado and viejo_turno.soltado
    assert not nuevo_silero.soltado and not nuevo_turno.soltado
    assert nuevo_silero.frecuencia == nuevo_turno.frecuencia == SAMPLE_RATE
    # El turno viejo no sigue: lo primero que oye lo oye el Silero nuevo, desde cero.
    assert detector.listen(b"b") is TurnSignal.VOICE
    assert nuevo_turno.inicios == [0.2], "empieza un turno nuevo, no sigue el viejo"
    assert nuevo_silero.trozos == [b"b"]


def test_si_no_se_pueden_cargar_los_nuevos_se_queda_con_los_que_tenia() -> None:
    # Ronda 2 de Codex sobre la PR #687: el reinicio sustituía antes de tener el par nuevo.
    silero_creados: list[_Silero] = []
    turno_creados: list[_SmartTurn] = []

    def silero() -> _Silero:
        silero_creados.append(_Silero(["SPEAKING", "SPEAKING"]))
        return silero_creados[-1]

    def smart_turn() -> _SmartTurn:
        if turno_creados:
            raise RuntimeError("sin memoria para otra sesión ONNX")
        turno_creados.append(_SmartTurn())
        return turno_creados[-1]

    detector = PipecatTurnDetector(silero, smart_turn)

    with pytest.raises(RuntimeError, match="sin memoria"):
        detector.reset()

    viejo, a_medias = silero_creados
    assert a_medias.soltado, "el Silero nuevo que no llegó a usarse se suelta"
    assert not viejo.soltado and not turno_creados[0].soltado
    assert detector.listen(b"a") is TurnSignal.VOICE
    assert viejo.trozos == [b"a"], "sigue oyendo con el par que tenía"


def test_si_soltar_un_analizador_viejo_falla_el_reinicio_sigue_valiendo() -> None:
    creados: list[_Silero] = []

    def silero() -> _Silero:
        creados.append(_Silero(["SPEAKING"]))
        return creados[-1]

    detector = PipecatTurnDetector(silero, _SmartTurn)

    async def no_se_suelta() -> None:
        raise RuntimeError("la sesión ONNX no se libera")

    creados[0].cleanup = no_se_suelta  # type: ignore[method-assign]

    detector.reset()

    assert detector.listen(b"a") is TurnSignal.VOICE
    assert creados[1].trozos == [b"a"], "oye con el par nuevo"


# --- faster-whisper -----------------------------------------------------------------


def test_transcribe_el_turno_entero_en_espanol_y_junta_los_trozos_de_texto() -> None:
    modelo = _Whisper()

    texto = FasterWhisperTranscriber(modelo, _numpy()).transcribe([b"\x01\x00", b"\x02\x00"])

    assert texto == "Hola, qué tal"
    ((audio, opciones),) = modelo.pedidos
    assert audio == (b"\x01\x00\x02\x00", "float32", 32768.0)
    assert opciones == {"language": "es", "condition_on_previous_text": False}
