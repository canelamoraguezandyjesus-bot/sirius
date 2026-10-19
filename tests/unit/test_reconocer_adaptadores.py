"""Reconocer de verdad, cableado con módulos de mentira en lugar de InsightFace, ECAPA, torch
y numpy (pieza E de la 0.4, ADR-263).

Las bibliotecas son del extra ``ojos``, que Quality no instala: aquí se pone un módulo de
mentira en el sitio de cada una y se mira cómo las usa Sirius. Que acierten lo mide el
propietario (E-R04-03). Lo que sí se mira aquí: que sin los modelos no carga nada, que lo
que no carga lo dice, que ONNX Runtime se calla antes de cargar, que la cara va con su caja
y sus cinco puntos, que ECAPA se carga sin red y sin enlaces, y cómo se lee lo que sonó.
"""

from __future__ import annotations

import math
import os
import sys
import types
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from sirius.adapters.audio.voice_libraries import ONNX_RUNTIME_TELEMETRY
from sirius.adapters.recognition.engines import (
    SAMPLE_RATE,
    SHORTEST_VOICE_SECONDS,
    EcapaPrints,
    InsightFacePrints,
    load_recognition_engines,
)
from sirius.adapters.vision.local_sight import FaceCrop
from sirius.infrastructure.local_sight_installation import (
    FACE_RECOGNITION_FILES,
    FACE_RECOGNITION_MODEL,
    VOICE_RECOGNITION_FILES,
)
from sirius.ports.recognition import RecognitionUnavailable

# --- Los módulos de mentira ---------------------------------------------------------


@dataclass
class _Array:
    """Lo que da numpy: los números y su tipo."""

    numeros: Any
    dtype: str

    def tolist(self) -> Any:
        return self.numeros


class _Tensor:
    """Un tensor de torch de mentira: sus números en una lista, y su forma."""

    def __init__(self, numeros: list[float], forma: tuple[int, ...]) -> None:
        self.numeros = numeros
        self.forma = forma

    def to(self, tipo: str) -> _Tensor:
        assert tipo == "float32"
        return _Tensor([float(n) for n in self.numeros], self.forma)

    def __truediv__(self, divisor: float) -> _Tensor:
        return _Tensor([n / divisor for n in self.numeros], self.forma)

    def unsqueeze(self, eje: int) -> _Tensor:
        assert eje == 0
        return _Tensor(self.numeros, (1, *self.forma))

    def squeeze(self) -> _Tensor:
        return _Tensor(self.numeros, tuple(d for d in self.forma if d != 1))

    def tolist(self) -> list[float]:
        return list(self.numeros)


@dataclass
class _Arcface:
    ruta: str
    preparado: list[int] = field(default_factory=list)
    vistas: list[tuple[Any, Any]] = field(default_factory=list)
    huella: list[float] = field(default_factory=lambda: [3.0, 4.0])

    def prepare(self, ctx_id: int) -> None:
        self.preparado.append(ctx_id)

    def get(self, img: Any, face: Any) -> _Array:
        self.vistas.append((img, face))
        return _Array(self.huella, "float32")


@dataclass
class _Ecapa:
    opciones: dict[str, Any]
    oidas: list[_Tensor] = field(default_factory=list)
    huella: list[float] = field(default_factory=lambda: [0.0, 6.0, 8.0])

    def encode_batch(self, ondas: _Tensor) -> _Tensor:
        self.oidas.append(ondas)
        return _Tensor(self.huella, (1, 1, len(self.huella)))


@dataclass
class _Bibliotecas:
    arcfaces: list[_Arcface] = field(default_factory=list)
    ecapas: list[_Ecapa] = field(default_factory=list)
    telemetria_apagada: list[str | None] = field(default_factory=list)
    falla_arcface: Exception | None = None
    falla_ecapa: Exception | None = None


@pytest.fixture
def bibliotecas(monkeypatch: pytest.MonkeyPatch) -> _Bibliotecas:
    """Pone numpy, ONNX Runtime, InsightFace, torch y SpeechBrain de mentira en su sitio."""
    estado = _Bibliotecas()
    monkeypatch.delenv(ONNX_RUNTIME_TELEMETRY, raising=False)

    def modulo(nombre: str, **atributos: Any) -> types.ModuleType:
        nuevo = types.ModuleType(nombre)
        for clave, valor in atributos.items():
            setattr(nuevo, clave, valor)
        monkeypatch.setitem(sys.modules, nombre, nuevo)
        return nuevo

    def arcface(ruta: str) -> _Arcface:
        if estado.falla_arcface is not None:
            raise estado.falla_arcface
        nuevo = _Arcface(ruta)
        estado.arcfaces.append(nuevo)
        return nuevo

    def from_hparams(**opciones: Any) -> _Ecapa:
        if estado.falla_ecapa is not None:
            raise estado.falla_ecapa
        nuevo = _Ecapa(opciones)
        estado.ecapas.append(nuevo)
        return nuevo

    @contextmanager
    def no_grad() -> Iterator[None]:
        yield

    def frombuffer(datos: bytearray, dtype: str) -> _Tensor:
        assert dtype == "int16"
        muestras = [
            int.from_bytes(datos[i : i + 2], "little", signed=True) for i in range(0, len(datos), 2)
        ]
        return _Tensor([float(m) for m in muestras], (len(muestras),))

    modulo("numpy", float32="float32", array=lambda numeros, dtype: _Array(numeros, dtype))
    modulo(
        "onnxruntime",
        disable_telemetry_events=lambda: estado.telemetria_apagada.append(
            os.environ.get(ONNX_RUNTIME_TELEMETRY)
        ),
    )
    modulo("insightface")
    modulo("insightface.model_zoo")
    modulo("insightface.model_zoo.arcface_onnx", ArcFaceONNX=arcface)
    modulo("insightface.app")
    modulo("insightface.app.common", Face=lambda **kw: types.SimpleNamespace(**kw))
    modulo("torch", int16="int16", float32="float32", frombuffer=frombuffer, no_grad=no_grad)
    modulo("speechbrain")
    modulo("speechbrain.inference")
    modulo(
        "speechbrain.inference.speaker",
        EncoderClassifier=types.SimpleNamespace(from_hparams=from_hparams),
    )
    modulo("speechbrain.utils")
    modulo(
        "speechbrain.utils.fetching",
        FetchConfig=lambda **kw: types.SimpleNamespace(**kw),
        LocalStrategy=types.SimpleNamespace(NO_LINK="no_link", SYMLINK="symlink"),
    )
    return estado


def _modelos(tmp_path: Path) -> tuple[Path, Path]:
    """Las carpetas de los modelos, con cada fichero que se espera, sin vaciar."""
    caras, voces = tmp_path / "insightface", tmp_path / "ecapa"
    for carpeta, nombres in ((caras, FACE_RECOGNITION_FILES), (voces, VOICE_RECOGNITION_FILES)):
        carpeta.mkdir()
        for nombre in nombres:
            (carpeta / nombre).write_bytes(b"pesos")
    return caras, voces


def _cerca(huella: Sequence[float] | None, esperada: Sequence[float]) -> bool:
    """Si ``huella`` es ``esperada`` salvo redondeo. Sin ``pytest.approx``, que mira numpy
    en ``sys.modules`` y aquí encontraría el de mentira."""
    return (
        huella is not None
        and len(huella) == len(esperada)
        and all(math.isclose(a, b, abs_tol=1e-9) for a, b in zip(huella, esperada, strict=True))
    )


def _recorte() -> FaceCrop:
    return FaceCrop(
        image="la imagen del recorte",
        box=(1.0, 2.0, 30.0, 40.0),
        points=((5.0, 10.0), (20.0, 10.0), (12.0, 18.0), (7.0, 28.0), (18.0, 28.0)),
    )


def _sonado(segundos: float, valor: int = 16384) -> list[bytes]:
    """Lo que sonó en un turno: ``segundos`` de muestras de 16 bits, en dos trozos."""
    muestras = int(segundos * SAMPLE_RATE)
    todo = valor.to_bytes(2, "little", signed=True) * muestras
    return [todo[: len(todo) // 2], todo[len(todo) // 2 :]]


# --- Cargar -------------------------------------------------------------------------


def test_sin_los_modelos_no_carga_nada_y_dice_cual_falta(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    caras, voces = _modelos(tmp_path)
    (voces / VOICE_RECOGNITION_FILES[1]).write_bytes(b"")

    with pytest.raises(RecognitionUnavailable, match="falta el modelo de reconocer voces"):
        load_recognition_engines(caras, voces)
    (caras / FACE_RECOGNITION_MODEL).unlink()
    with pytest.raises(RecognitionUnavailable, match="falta el modelo de reconocer caras"):
        load_recognition_engines(caras, voces)

    assert bibliotecas.arcfaces == []
    assert bibliotecas.ecapas == []


def test_con_los_modelos_carga_insightface_y_ecapa(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    caras, voces = _modelos(tmp_path)

    motores = load_recognition_engines(caras, voces)

    assert motores.faces.name == "insightface"
    assert motores.voices.name == "speechbrain-ecapa"
    [arcface] = bibliotecas.arcfaces
    assert arcface.ruta == str(caras / FACE_RECOGNITION_MODEL)
    assert arcface.preparado == [-1], "en el procesador: la gráfica es de la charla"


def test_onnx_runtime_se_calla_antes_de_cargar_el_modelo_de_las_caras(
    bibliotecas: _Bibliotecas, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caras, voces = _modelos(tmp_path)
    vistas: list[int] = []
    modulo = sys.modules["insightface.model_zoo.arcface_onnx"]
    original = modulo.ArcFaceONNX

    def arcface(ruta: str) -> _Arcface:
        vistas.append(len(bibliotecas.telemetria_apagada))
        nuevo: _Arcface = original(ruta)
        return nuevo

    monkeypatch.setattr(modulo, "ArcFaceONNX", arcface)

    load_recognition_engines(caras, voces)

    assert bibliotecas.telemetria_apagada == ["1"], "con la variable puesta antes"
    assert vistas == [1], "y antes de cargar el modelo"


def test_ecapa_se_carga_sin_red_sin_enlaces_y_en_el_procesador(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    caras, voces = _modelos(tmp_path)

    load_recognition_engines(caras, voces)

    [ecapa] = bibliotecas.ecapas
    opciones = ecapa.opciones
    assert opciones["source"] == opciones["savedir"] == str(voces)
    assert opciones["run_opts"] == {"device": "cpu"}
    assert opciones["overrides"] == {"pretrained_path": str(voces)}
    assert opciones["fetch_config"].allow_network is False
    assert opciones["local_strategy"] == "no_link", "en Windows, enlazar pide administrador"


@pytest.mark.parametrize("de_que", ["cara", "voz"])
def test_lo_que_no_carga_lo_dice_con_su_causa(
    bibliotecas: _Bibliotecas, tmp_path: Path, de_que: str
) -> None:
    caras, voces = _modelos(tmp_path)
    if de_que == "cara":
        bibliotecas.falla_arcface = RuntimeError("un onnx roto")
        motivo = "el modelo de reconocer caras no carga (un onnx roto)"
    else:
        bibliotecas.falla_ecapa = RuntimeError("un ckpt roto")
        motivo = "el modelo de reconocer voces no carga (un ckpt roto)"

    with pytest.raises(RecognitionUnavailable) as error:
        load_recognition_engines(caras, voces)

    assert error.value.reason == motivo


def test_una_biblioteca_que_no_esta_lo_dice_con_su_nombre(
    bibliotecas: _Bibliotecas, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caras, voces = _modelos(tmp_path)
    monkeypatch.setitem(sys.modules, "speechbrain.inference.speaker", None)

    with pytest.raises(RecognitionUnavailable, match=r"speechbrain\.inference\.speaker no carga"):
        load_recognition_engines(caras, voces)


# --- La cara ------------------------------------------------------------------------


def test_la_huella_de_una_cara_va_con_su_recorte_su_caja_y_sus_cinco_puntos(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    caras, _ = _modelos(tmp_path)
    reconocedor = InsightFacePrints(caras)

    huella = reconocedor.fingerprint(_recorte())

    [arcface] = bibliotecas.arcfaces
    [(imagen, cara)] = arcface.vistas
    assert imagen == "la imagen del recorte"
    assert cara.bbox == _Array((1.0, 2.0, 30.0, 40.0), "float32")
    assert cara.kps == _Array(_recorte().points, "float32")
    assert _cerca(huella, (0.6, 0.8)), "con longitud uno"


# --- La voz -------------------------------------------------------------------------


def test_la_huella_de_una_voz_lee_lo_que_sono_como_numeros_de_menos_uno_a_uno(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    _, voces = _modelos(tmp_path)
    reconocedor = EcapaPrints(voces)

    huella = reconocedor.fingerprint(_sonado(1.0))

    [ecapa] = bibliotecas.ecapas
    [onda] = ecapa.oidas
    assert onda.forma == (1, SAMPLE_RATE), "un turno, con todas sus muestras"
    assert set(onda.numeros) == {0.5}, "16384 de 32768"
    assert _cerca(huella, (0.0, 0.6, 0.8)), "con longitud uno"


def test_con_menos_de_medio_segundo_no_hay_huella_y_ni_se_le_pide(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    _, voces = _modelos(tmp_path)
    reconocedor = EcapaPrints(voces)

    assert SHORTEST_VOICE_SECONDS == 0.5
    assert reconocedor.fingerprint(_sonado(0.49)) is None
    assert reconocedor.fingerprint([]) is None
    assert bibliotecas.ecapas[0].oidas == []
    assert reconocedor.fingerprint(_sonado(0.5)) is not None


def test_un_byte_suelto_al_final_no_rompe_la_huella(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    _, voces = _modelos(tmp_path)
    reconocedor = EcapaPrints(voces)

    reconocedor.fingerprint([*_sonado(0.5), b"\x01"])

    assert len(bibliotecas.ecapas[0].oidas[0].numeros) == SAMPLE_RATE // 2


def test_una_huella_de_ceros_no_es_de_nadie(bibliotecas: _Bibliotecas, tmp_path: Path) -> None:
    _, voces = _modelos(tmp_path)
    reconocedor = EcapaPrints(voces)
    bibliotecas.ecapas[0].huella = [0.0, 0.0, 0.0]

    assert reconocedor.fingerprint(_sonado(1.0)) is None
