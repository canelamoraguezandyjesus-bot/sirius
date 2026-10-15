"""La voz de verdad, cableada con módulos de mentira en lugar de Piper y sounddevice (ADR-243).

Las bibliotecas son del extra ``voz``, que Quality no instala: aquí se pone un módulo de
mentira en el sitio de cada una y se mira cómo las usa Sirius. Que suene bien lo mira el
propietario en su ordenador (E-R03-01 y E-R03-02). Lo que sí se mira aquí, porque es lo
que cierra la puerta a bajar algo o a apuntar lo dicho: la voz se carga solo de su
fichero, y Piper no puede escribir en ningún diario el texto que dice.
"""

from __future__ import annotations

import ast
import importlib
import logging
import sys
import types
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

import sirius.adapters.audio.local_speaking as local_speaking_module
from sirius.adapters.audio.local_speaking import (
    ECHO_TAIL_SECONDS,
    PiperSpeech,
    SoundDeviceSpeaker,
    check_speaking_libraries,
    load_speaking_engines,
)
from sirius.adapters.audio.voice_libraries import TEXT_TO_SPEECH, voice_tools
from sirius.ports.local_voice import VoiceUnavailable

_FRECUENCIA = 22_050


class _PortAudioError(Exception):
    pass


class _Flujo:
    def __init__(self, **opciones: Any) -> None:
        self.opciones = opciones
        self.latency = 0.1
        self.arrancado = False
        self.cerrado = False
        self.falla_al_arrancar = False

    def start(self) -> None:
        if self.falla_al_arrancar:
            raise _PortAudioError("Error querying device -1")
        self.arrancado = True

    def close(self) -> None:
        self.cerrado = True


@dataclass
class _SoundDevice:
    flujos: list[_Flujo] = field(default_factory=list)
    sin_altavoz: bool = False
    no_se_crea: bool = False
    PortAudioError: type[Exception] = _PortAudioError

    def RawOutputStream(self, **opciones: Any) -> _Flujo:
        if self.no_se_crea:
            raise _PortAudioError("Invalid sample rate")
        flujo = _Flujo(**opciones)
        flujo.falla_al_arrancar = self.sin_altavoz
        self.flujos.append(flujo)
        return flujo


@dataclass
class _Trozo:
    audio_int16_bytes: bytes


class _VozDePiper:
    def __init__(self) -> None:
        self.config = types.SimpleNamespace(sample_rate=_FRECUENCIA)
        self.dichas: list[str] = []

    def synthesize(self, texto: str) -> Iterator[_Trozo]:
        self.dichas.append(texto)
        # Una frase por trozo, como Piper.
        for frase in texto.split(". "):
            yield _Trozo(frase.encode())


class _PiperVoice:
    cargas: list[tuple[tuple[Any, ...], dict[str, Any]]] = []  # noqa: RUF012
    falla_al_cargar: Exception | None = None

    @staticmethod
    def load(*args: Any, **kwargs: Any) -> _VozDePiper:
        falla = _PiperVoice.falla_al_cargar
        if falla is not None:
            raise falla
        _PiperVoice.cargas.append((args, kwargs))
        return _VozDePiper()


@pytest.fixture
def sounddevice(monkeypatch: pytest.MonkeyPatch) -> _SoundDevice:
    """Pone un Piper y un sounddevice de mentira, y deja el registrador de Piper como estaba."""
    monkeypatch.setattr(_PiperVoice, "cargas", [])
    monkeypatch.setattr(_PiperVoice, "falla_al_cargar", None)
    piper = types.ModuleType("piper")
    piper.PiperVoice = _PiperVoice  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "piper", piper)
    falso = _SoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", falso)
    registrador = logging.getLogger("piper")
    monkeypatch.setattr(registrador, "level", registrador.level)
    return falso


# --- Cargar la voz ------------------------------------------------------------------


def test_carga_la_voz_solo_de_su_fichero_y_abre_el_altavoz_a_su_frecuencia(
    sounddevice: _SoundDevice, tmp_path: Path
) -> None:
    modelo = tmp_path / "es_ES-davefx-medium.onnx"

    motores = load_speaking_engines(modelo)

    # Solo el modelo: su configuración, a su lado, y nada de carpetas para bajar cosas.
    assert _PiperVoice.cargas == [((modelo,), {})]
    (flujo,) = sounddevice.flujos
    assert {k: v for k, v in flujo.opciones.items() if k != "callback"} == {
        "samplerate": _FRECUENCIA,
        "channels": 1,
        "dtype": "int16",
    }
    assert flujo.arrancado
    assert motores.speaker.latency == 0.1


def test_sin_el_extra_instalado_avisa_y_no_tumba_a_sirius(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(sys.modules, "piper", None)

    with pytest.raises(VoiceUnavailable) as fallo:
        load_speaking_engines(tmp_path / "voz.onnx")

    assert fallo.value.reason.startswith("piper no carga")


def test_comprobar_las_bibliotecas_mira_piper_y_sounddevice(
    sounddevice: _SoundDevice, monkeypatch: pytest.MonkeyPatch
) -> None:
    check_speaking_libraries()
    monkeypatch.setitem(sys.modules, "sounddevice", None)

    with pytest.raises(VoiceUnavailable) as fallo:
        check_speaking_libraries()

    assert fallo.value.reason.startswith("sounddevice no carga")


class _InvalidProtobuf(Exception):
    """Como los errores de onnxruntime, que heredan de Exception y de nada más concreto."""


@pytest.mark.parametrize(
    "error",
    [_InvalidProtobuf("INVALID_PROTOBUF"), ValueError("Expecting value: line 1 column 1")],
)
def test_una_voz_que_esta_y_no_carga_avisa_y_no_tumba_a_sirius(
    sounddevice: _SoundDevice, tmp_path: Path, error: Exception
) -> None:
    _PiperVoice.falla_al_cargar = error

    with pytest.raises(VoiceUnavailable) as fallo:
        load_speaking_engines(tmp_path / "voz.onnx")

    assert fallo.value.reason == f"la voz no carga ({error})"
    assert sounddevice.flujos == [], "sin voz no abre el altavoz"


def test_sin_altavoz_avisa_y_no_deja_nada_abierto(
    sounddevice: _SoundDevice, tmp_path: Path
) -> None:
    sounddevice.sin_altavoz = True

    with pytest.raises(VoiceUnavailable) as fallo:
        load_speaking_engines(tmp_path / "voz.onnx")

    assert fallo.value.reason == "no puedo abrir el altavoz (Error querying device -1)"
    (flujo,) = sounddevice.flujos
    assert flujo.cerrado


def test_si_el_altavoz_no_admite_la_voz_avisa(sounddevice: _SoundDevice, tmp_path: Path) -> None:
    sounddevice.no_se_crea = True

    with pytest.raises(VoiceUnavailable) as fallo:
        load_speaking_engines(tmp_path / "voz.onnx")

    assert fallo.value.reason == "no puedo abrir el altavoz (Invalid sample rate)"


def test_lo_que_dice_piper_no_llega_a_ningun_diario(
    sounddevice: _SoundDevice, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Piper apunta en DEBUG el texto de cada frase (`PiperVoice.synthesize`).
    load_speaking_engines(tmp_path / "voz.onnx")

    with caplog.at_level(logging.DEBUG):
        logging.getLogger("piper.voice").debug("text=%s", "La clave es Zarzamora")

    assert "zarzamora" not in caplog.text.casefold()


def test_ninguna_funcion_de_la_voz_importa_por_su_cuenta() -> None:
    # Todas entran por `import_voice_library`, que traduce cualquier fallo al importar.
    fuente = Path(local_speaking_module.__file__).read_text(encoding="utf-8")
    sueltos = [
        f"{funcion.name}:{nodo.lineno}"
        for funcion in ast.walk(ast.parse(fuente))
        if isinstance(funcion, ast.FunctionDef | ast.AsyncFunctionDef)
        for nodo in ast.walk(funcion)
        if isinstance(nodo, ast.Import | ast.ImportFrom)
    ]

    assert sueltos == []


def test_habla_con_piper_porque_es_lo_que_importa_al_cargar(
    sounddevice: _SoundDevice, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # PA-R03-08 lee con qué habla de `voice_tools`: tiene que ser lo que carga de verdad.
    importados: list[str] = []
    importa = importlib.import_module

    def apunta(nombre: str, *args: Any) -> types.ModuleType:
        importados.append(nombre)
        return importa(nombre, *args)

    monkeypatch.setattr(importlib, "import_module", apunta)

    load_speaking_engines(tmp_path / "voz.onnx")

    assert voice_tools()["habla"] == "piper"
    assert TEXT_TO_SPEECH in importados


# --- Piper --------------------------------------------------------------------------


def test_cada_frase_sale_en_las_muestras_de_16_bits_que_da_piper() -> None:
    voz = _VozDePiper()

    sonido = PiperSpeech(voz).say("Hola. Adiós.")

    assert sonido == b"HolaAdi\xc3\xb3s."
    assert voz.dichas == ["Hola. Adiós."]


# --- El altavoz ---------------------------------------------------------------------


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 50.0

    def __call__(self) -> float:
        return self.ahora


def _altavoz(reloj: _Reloj | None = None) -> tuple[SoundDeviceSpeaker, Any]:
    sounddevice = _SoundDevice()
    altavoz = SoundDeviceSpeaker(sounddevice, _FRECUENCIA, clock=reloj or _Reloj())
    return altavoz, sounddevice.flujos[0].opciones["callback"]


def test_suena_lo_que_le_dan_en_orden_y_lo_que_falta_es_silencio() -> None:
    altavoz, llena = _altavoz()
    altavoz.play(b"abcd")
    altavoz.play(b"ef")
    salida = bytearray(4)

    llena(salida, 2, None, None)
    assert bytes(salida) == b"abcd"
    llena(salida, 2, None, None)
    assert bytes(salida) == b"ef\x00\x00"
    llena(salida, 2, None, None)
    assert bytes(salida) == b"\x00\x00\x00\x00"


def test_sigue_sonando_hasta_que_lo_ultimo_sale_y_pasa_la_cola_del_eco() -> None:
    reloj = _Reloj()
    altavoz, llena = _altavoz(reloj)
    assert not altavoz.playing

    altavoz.play(b"abcd")
    assert altavoz.playing, "lo que espera en la cola también suena"
    llena(bytearray(4), 2, None, None)

    # Lo último sale con la latencia del flujo, y su eco dura un poco más en la habitación.
    final = 0.1 + 2 / _FRECUENCIA + ECHO_TAIL_SECONDS
    reloj.ahora = 50.0 + final - 0.001
    assert altavoz.playing
    reloj.ahora = 50.0 + final + 0.001
    assert not altavoz.playing


def test_callar_tira_lo_que_esperaba_y_deja_de_sonar() -> None:
    altavoz, llena = _altavoz()
    altavoz.play(b"abcd")
    llena(bytearray(2), 1, None, None)

    altavoz.stop()

    assert not altavoz.playing
    salida = bytearray(2)
    llena(salida, 1, None, None)
    assert bytes(salida) == b"\x00\x00"
