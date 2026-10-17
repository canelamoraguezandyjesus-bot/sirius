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
from types import SimpleNamespace
from typing import Any, cast

import pytest

import sirius.adapters.audio.local_speaking as local_speaking_module
from sirius.adapters.audio.local_speaking import (
    BLOCK_FRAMES,
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

    def stop(self) -> None:
        self.arrancado = False

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
    def __init__(self, locutores: dict[str, int] | None = None) -> None:
        self.config = types.SimpleNamespace(sample_rate=_FRECUENCIA, speaker_id_map=locutores or {})
        self.dichas: list[str] = []
        self.configuraciones: list[object] = []

    def synthesize(self, texto: str, syn_config: object = None) -> Iterator[_Trozo]:
        self.dichas.append(texto)
        self.configuraciones.append(syn_config)
        # Una frase por trozo, como Piper.
        for frase in texto.split(". "):
            yield _Trozo(frase.encode())


class _PiperVoice:
    cargas: list[tuple[tuple[Any, ...], dict[str, Any]]] = []  # noqa: RUF012
    falla_al_cargar: Exception | None = None
    #: Los locutores que trae la voz que se carga: sharvard, un hombre y una mujer.
    locutores: dict[str, int] = {}  # noqa: RUF012
    cargadas: list[_VozDePiper] = []  # noqa: RUF012

    @staticmethod
    def load(*args: Any, **kwargs: Any) -> _VozDePiper:
        falla = _PiperVoice.falla_al_cargar
        if falla is not None:
            raise falla
        _PiperVoice.cargas.append((args, kwargs))
        voz = _VozDePiper(_PiperVoice.locutores)
        _PiperVoice.cargadas.append(voz)
        return voz


@dataclass(frozen=True)
class _SynthesisConfig:
    speaker_id: int | None = None


@pytest.fixture
def sounddevice(monkeypatch: pytest.MonkeyPatch) -> _SoundDevice:
    """Pone un Piper y un sounddevice de mentira, y deja el registrador de Piper como estaba."""
    monkeypatch.setattr(_PiperVoice, "cargas", [])
    monkeypatch.setattr(_PiperVoice, "falla_al_cargar", None)
    monkeypatch.setattr(_PiperVoice, "locutores", {})
    monkeypatch.setattr(_PiperVoice, "cargadas", [])
    piper = types.ModuleType("piper")
    piper.PiperVoice = _PiperVoice  # type: ignore[attr-defined]
    piper.SynthesisConfig = _SynthesisConfig  # type: ignore[attr-defined]
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
        "blocksize": BLOCK_FRAMES,
        "channels": 1,
        "dtype": "int16",
    }
    assert flujo.arrancado
    # A lo sumo: lo que puede esperar al siguiente bloque y lo que tarda en salir (ronda 1
    # de Codex sobre la PR #688).
    assert motores.speaker.latency == BLOCK_FRAMES / _FRECUENCIA + 0.1


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


def test_callar_tira_lo_que_esperaba_y_lo_ya_dado_sigue_sonando_hasta_salir() -> None:
    # Ronda 1 de Codex sobre la PR #688: lo que PortAudio ya tiene sale igual, y hasta que
    # sale no se puede decir que calla, o el oído abriría el micro con su voz aún sonando.
    reloj = _Reloj()
    altavoz, llena = _altavoz(reloj)
    altavoz.play(b"abcd")
    llena(bytearray(2), 1, None, None)

    altavoz.stop()

    salida = bytearray(2)
    llena(salida, 1, None, None)
    assert bytes(salida) == b"\x00\x00", "lo que esperaba ya no se da"
    final = 0.1 + 1 / _FRECUENCIA + ECHO_TAIL_SECONDS
    reloj.ahora = 50.0 + final - 0.001
    assert altavoz.playing
    reloj.ahora = 50.0 + final + 0.001
    assert not altavoz.playing


def test_callar_lo_que_aun_no_habia_empezado_calla_en_el_acto() -> None:
    altavoz, _llena = _altavoz()
    altavoz.play(b"abcd")

    altavoz.stop()

    assert not altavoz.playing


# --- Pieza E: lo que empieza a sonar y lo que oye la cancelación de eco (ADR-245) ---


def test_cuenta_lo_que_empieza_a_sonar_y_no_lo_que_tira_al_callar() -> None:
    altavoz, llena = _altavoz()
    altavoz.play(b"abcd")
    altavoz.play(b"ef")
    altavoz.play(b"gh")
    assert altavoz.started == 0, "lo que espera en la cola aún no ha empezado"

    llena(bytearray(4), 2, None, None)
    assert altavoz.started == 1
    llena(bytearray(2), 1, None, None)
    assert altavoz.started == 2, "empieza en cuanto sale su primera muestra"

    altavoz.stop()
    llena(bytearray(4), 2, None, None)
    assert altavoz.started == 2, "lo que se tiró al callar no llega a empezar"
    altavoz.play(b"ijkl")
    llena(bytearray(4), 2, None, None)
    assert altavoz.started == 3, "lo que suena después cuenta una vez, y lo tirado nunca"


class _Eco:
    def __init__(self) -> None:
        self.oido: list[tuple[bytes, float]] = []
        #: El flujo del altavoz, para ver cómo estaba al soltar la APM.
        self.flujo: _Flujo | None = None
        #: Si el flujo seguía arrancado cuando se soltó la APM; ``None``, sin soltar.
        self.soltada_con_el_flujo_arrancado: bool | None = None

    def played(self, block: bytes, at: float) -> None:
        self.oido.append((block, at))

    def close(self) -> None:
        self.soltada_con_el_flujo_arrancado = self.flujo is not None and self.flujo.arrancado


def test_le_da_a_la_cancelacion_de_eco_cada_bloque_con_la_hora_a_la_que_se_oye() -> None:
    reloj = _Reloj()
    sounddevice = _SoundDevice()
    eco = _Eco()
    altavoz = SoundDeviceSpeaker(sounddevice, _FRECUENCIA, clock=reloj, echo=eco)  # type: ignore[arg-type]
    llena = sounddevice.flujos[0].opciones["callback"]
    altavoz.play(b"ab")

    llena(bytearray(4), 2, None, None)
    reloj.ahora = 51.0
    llena(bytearray(4), 2, None, None)

    # Silencio incluido: la cancelación necesita lo que sale, suene o no.
    assert eco.oido == [(b"ab\x00\x00", 50.0 + 0.1), (b"\x00\x00\x00\x00", 51.0 + 0.1)]


def test_la_hora_a_la_que_se_oye_cada_bloque_es_la_del_dac_de_portaudio() -> None:
    # Ronda 1 de Codex sobre la PR #690: la latencia del flujo es una media; PortAudio dice,
    # bloque a bloque, cuándo llega al DAC su primera muestra. Esa hora va a la
    # cancelación de eco y a hasta cuándo suena.
    reloj = _Reloj()
    sounddevice = _SoundDevice()
    eco = _Eco()
    altavoz = SoundDeviceSpeaker(sounddevice, _FRECUENCIA, clock=reloj, echo=eco)  # type: ignore[arg-type]
    llena = sounddevice.flujos[0].opciones["callback"]
    altavoz.play(b"ab")

    llena(bytearray(4), 2, SimpleNamespace(outputBufferDacTime=700.03, currentTime=700.0), None)

    ((bloque, hora),) = eco.oido
    assert bloque == b"ab\x00\x00"
    assert hora == pytest.approx(50.0 + 0.03)
    final = 0.03 + 2 / _FRECUENCIA + ECHO_TAIL_SECONDS
    reloj.ahora = 50.0 + final - 0.001
    assert altavoz.playing
    reloj.ahora = 50.0 + final + 0.001
    assert not altavoz.playing


def test_sin_hora_del_dac_que_tenga_sentido_se_oye_con_la_latencia_del_flujo() -> None:
    reloj = _Reloj()
    sounddevice = _SoundDevice()
    eco = _Eco()
    SoundDeviceSpeaker(sounddevice, _FRECUENCIA, clock=reloj, echo=eco)  # type: ignore[arg-type]
    llena = sounddevice.flujos[0].opciones["callback"]

    for horas in (
        # Cero es como dice PortAudio que no la sabe.
        SimpleNamespace(outputBufferDacTime=0.0, currentTime=0.0),
        SimpleNamespace(outputBufferDacTime=0.0, currentTime=700.0),
        SimpleNamespace(outputBufferDacTime=699.0, currentTime=700.0),
        SimpleNamespace(outputBufferDacTime=705.0, currentTime=700.0),
    ):
        llena(bytearray(4), 2, horas, None)

    assert [hora for _bloque, hora in eco.oido] == [50.0 + 0.1] * 4


def test_cargar_la_voz_trae_la_cancelacion_de_eco_si_se_puede_y_el_altavoz_la_alimenta(
    sounddevice: _SoundDevice, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    eco = _Eco()
    monkeypatch.setattr(local_speaking_module, "load_echo_canceller", lambda rate: eco)

    motores = load_speaking_engines(tmp_path / "es_ES-davefx-medium.onnx")

    assert cast(object, motores.echo_canceller) is eco
    motores.speaker.play(b"ab")
    sounddevice.flujos[0].opciones["callback"](bytearray(2), 1, None, None)
    assert [bloque for bloque, _ in eco.oido] == [b"ab"]


def test_sin_cancelacion_de_eco_la_voz_carga_igual(
    sounddevice: _SoundDevice, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "livekit", None)
    monkeypatch.setitem(sys.modules, "livekit.rtc", None)

    motores = load_speaking_engines(tmp_path / "es_ES-davefx-medium.onnx")

    assert motores.echo_canceller is None


# --- Las voces de la prueba a ciegas (pieza F, ADR-246) -------------------------------


def test_sharvard_habla_con_su_locutor_masculino(sounddevice: _SoundDevice, tmp_path: Path) -> None:
    _PiperVoice.locutores = {"M": 0, "F": 1}

    motores = load_speaking_engines(tmp_path / "es_ES-sharvard-medium.onnx")
    motores.voice.say("Buenos días, jefe.")

    [voz] = _PiperVoice.cargadas
    assert voz.configuraciones == [_SynthesisConfig(speaker_id=0)]


def test_una_voz_sin_el_locutor_que_pide_el_catalogo_no_carga_ni_abre_el_altavoz(
    sounddevice: _SoundDevice, tmp_path: Path
) -> None:
    _PiperVoice.locutores = {"F": 0}

    with pytest.raises(VoiceUnavailable, match="no trae el locutor M"):
        load_speaking_engines(tmp_path / "es_ES-sharvard-medium.onnx")

    assert sounddevice.flujos == []


def test_las_voces_de_un_locutor_hablan_sin_pedir_ninguno(
    sounddevice: _SoundDevice, tmp_path: Path
) -> None:
    motores = load_speaking_engines(tmp_path / "es_ES-carlfm-x_low.onnx")
    motores.voice.say("Hola.")

    [voz] = _PiperVoice.cargadas
    assert voz.configuraciones == [None]


def test_la_voz_de_personaje_se_carga_de_su_carpeta_con_el_altavoz_a_su_frecuencia(
    sounddevice: _SoundDevice, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cargadas: list[Path] = []

    def carga(carpeta: Path) -> SimpleNamespace:
        cargadas.append(carpeta)
        return SimpleNamespace(sample_rate=24_000, say=lambda texto: b"")

    monkeypatch.setattr(local_speaking_module, "load_character_voice", carga)
    carpeta = tmp_path / "chatterbox-multilingual"

    load_speaking_engines(carpeta)

    assert cargadas == [carpeta]
    assert _PiperVoice.cargas == []
    (flujo,) = sounddevice.flujos
    assert flujo.opciones["samplerate"] == 24_000


def test_soltar_el_altavoz_tira_lo_que_esperaba_y_cierra_el_flujo() -> None:
    sounddevice = _SoundDevice()
    altavoz = SoundDeviceSpeaker(sounddevice, _FRECUENCIA, clock=_Reloj())
    altavoz.play(b"abcd")

    altavoz.close()

    (flujo,) = sounddevice.flujos
    assert not flujo.arrancado
    assert flujo.cerrado
    assert not altavoz.playing


def test_soltar_el_altavoz_suelta_la_apm_con_el_flujo_ya_parado() -> None:
    sounddevice = _SoundDevice()
    eco = _Eco()
    altavoz = SoundDeviceSpeaker(sounddevice, _FRECUENCIA, clock=_Reloj(), echo=eco)  # type: ignore[arg-type]
    eco.flujo = sounddevice.flujos[0]

    altavoz.close()

    # Parado el flujo, PortAudio ya no le da lo que suena a la APM que se suelta.
    assert eco.soltada_con_el_flujo_arrancado is False


def test_soltar_un_altavoz_que_no_se_deja_cerrar_no_falla_y_lo_apunta(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    sounddevice = _SoundDevice()
    eco = _Eco()
    altavoz = SoundDeviceSpeaker(sounddevice, _FRECUENCIA, clock=_Reloj(), echo=eco)  # type: ignore[arg-type]

    def no_se_deja() -> None:
        raise _PortAudioError("Stream is not open")

    flujo = sounddevice.flujos[0]
    flujo.stop = no_se_deja  # type: ignore[method-assign]
    flujo.close = no_se_deja  # type: ignore[method-assign]

    with caplog.at_level(logging.WARNING, logger="sirius"):
        altavoz.close()

    assert "No se ha podido parar el altavoz: Stream is not open" in caplog.text
    assert "No se ha podido cerrar el altavoz: Stream is not open" in caplog.text
    # La APM se suelta igual: lo que suene después ya no se le da (ADR-252).
    assert eco.soltada_con_el_flujo_arrancado is not None
