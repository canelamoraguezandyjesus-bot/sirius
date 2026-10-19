"""La edad de verdad, cableada con módulos de mentira en lugar de InsightFace y numpy (pieza F
de la 0.4, ADR-264).

La biblioteca es del extra ``ojos``, que Quality no instala: aquí se pone un módulo de
mentira en el sitio de cada una y se mira cómo las usa Sirius. Que acierte la edad lo mide
el propietario (E-R04-04). Lo que sí se mira aquí: que sin el modelo no carga nada, que lo
que no carga lo dice, que ONNX Runtime se calla antes de cargar, que la cara va con su caja,
y cuándo se lee segura.
"""

from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from sirius.adapters.audio.voice_libraries import ONNX_RUNTIME_TELEMETRY
from sirius.adapters.recognition.age import (
    MOST_TURNED,
    SMALLEST_SURE_FACE,
    InsightFaceAges,
    load_age_estimator,
    reads_sure,
)
from sirius.adapters.vision.local_sight import FaceCrop
from sirius.infrastructure.local_sight_installation import AGE_MODEL
from sirius.ports.age import AgeReading, AgeUnavailable

# --- Los módulos de mentira ---------------------------------------------------------


@dataclass
class _Array:
    """Lo que da numpy: los números y su tipo."""

    numeros: Any
    dtype: str


@dataclass
class _Atributos:
    """El modelo de la edad de InsightFace, de mentira: da si parece hombre o mujer y la
    edad, como el de verdad, y apunta qué le llega."""

    model_file: str
    preparado: list[int] = field(default_factory=list)
    vistas: list[tuple[Any, Any]] = field(default_factory=list)
    edad: int = 41

    def prepare(self, ctx_id: int) -> None:
        self.preparado.append(ctx_id)

    def get(self, img: Any, face: Any) -> tuple[int, int]:
        self.vistas.append((img, face))
        return 1, self.edad


@dataclass
class _Bibliotecas:
    modelos: list[_Atributos] = field(default_factory=list)
    telemetria_apagada: list[str | None] = field(default_factory=list)
    falla: Exception | None = None


@pytest.fixture
def bibliotecas(monkeypatch: pytest.MonkeyPatch) -> _Bibliotecas:
    """Pone numpy, ONNX Runtime e InsightFace de mentira en su sitio."""
    estado = _Bibliotecas()
    monkeypatch.delenv(ONNX_RUNTIME_TELEMETRY, raising=False)

    def modulo(nombre: str, **atributos: Any) -> None:
        nuevo = types.ModuleType(nombre)
        for clave, valor in atributos.items():
            setattr(nuevo, clave, valor)
        monkeypatch.setitem(sys.modules, nombre, nuevo)

    def atributos(model_file: str) -> _Atributos:
        if estado.falla is not None:
            raise estado.falla
        nuevo = _Atributos(model_file)
        estado.modelos.append(nuevo)
        return nuevo

    modulo("numpy", float32="float32", array=lambda numeros, dtype: _Array(numeros, dtype))
    modulo(
        "onnxruntime",
        disable_telemetry_events=lambda: estado.telemetria_apagada.append(
            os.environ.get(ONNX_RUNTIME_TELEMETRY)
        ),
    )
    modulo("insightface")
    modulo("insightface.model_zoo")
    modulo("insightface.model_zoo.attribute", Attribute=atributos)
    modulo("insightface.app")
    modulo("insightface.app.common", Face=lambda **kw: types.SimpleNamespace(**kw))
    return estado


def _modelo(tmp_path: Path) -> Path:
    """La carpeta de los modelos de InsightFace, solo con el de la edad, sin vaciar."""
    carpeta = tmp_path / "insightface"
    carpeta.mkdir()
    (carpeta / AGE_MODEL).write_bytes(b"pesos")
    return carpeta


def _recorte(
    *,
    lado: float = 120.0,
    alto: float | None = None,
    ojos: tuple[float, float] = (40.0, 80.0),
    nariz: float = 60.0,
) -> FaceCrop:
    """Un recorte con su caja, de ``lado`` de ancho y ``alto`` de alto, y sus cinco puntos:
    los dos ojos, en ``ojos``, la nariz en ``nariz`` y las comisuras."""
    return FaceCrop(
        image="la imagen del recorte",
        box=(10.0, 20.0, 10.0 + lado, 20.0 + (lado if alto is None else alto)),
        points=((ojos[0], 50.0), (ojos[1], 50.0), (nariz, 70.0), (45.0, 90.0), (75.0, 90.0)),
    )


# --- Cargar -------------------------------------------------------------------------


@pytest.mark.parametrize("contenido", [None, b""], ids=["sin el fichero", "vacío"])
def test_sin_el_modelo_de_la_edad_no_carga_nada_y_lo_dice(
    bibliotecas: _Bibliotecas, tmp_path: Path, contenido: bytes | None
) -> None:
    carpeta = _modelo(tmp_path)
    if contenido is None:
        (carpeta / AGE_MODEL).unlink()
    else:
        (carpeta / AGE_MODEL).write_bytes(contenido)

    with pytest.raises(AgeUnavailable) as error:
        load_age_estimator(carpeta)

    assert error.value.reason == "falta el modelo de la edad"
    assert bibliotecas.modelos == []


def test_con_el_modelo_carga_el_de_la_edad_de_insightface_en_el_procesador(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    carpeta = _modelo(tmp_path)

    estimador = load_age_estimator(carpeta)

    assert estimador.name == "insightface"
    [modelo] = bibliotecas.modelos
    assert modelo.model_file == str(carpeta / AGE_MODEL)
    assert modelo.preparado == [-1], "en el procesador: la gráfica es de la charla"


def test_onnx_runtime_se_calla_antes_de_cargar_el_modelo_de_la_edad(
    bibliotecas: _Bibliotecas, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    carpeta = _modelo(tmp_path)
    vistas: list[int] = []
    modulo = sys.modules["insightface.model_zoo.attribute"]
    original = modulo.Attribute

    def atributos(model_file: str) -> _Atributos:
        vistas.append(len(bibliotecas.telemetria_apagada))
        nuevo: _Atributos = original(model_file)
        return nuevo

    monkeypatch.setattr(modulo, "Attribute", atributos)

    load_age_estimator(carpeta)

    assert bibliotecas.telemetria_apagada == ["1"], "con la variable puesta antes"
    assert vistas == [1], "y antes de cargar el modelo"


def test_lo_que_no_carga_lo_dice_con_su_causa(bibliotecas: _Bibliotecas, tmp_path: Path) -> None:
    bibliotecas.falla = RuntimeError("un onnx roto")

    with pytest.raises(AgeUnavailable) as error:
        load_age_estimator(_modelo(tmp_path))

    assert error.value.reason == "el modelo de la edad no carga (un onnx roto)"


def test_una_biblioteca_que_no_esta_lo_dice_con_su_nombre(
    bibliotecas: _Bibliotecas, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "insightface.model_zoo.attribute", None)

    with pytest.raises(AgeUnavailable, match=r"insightface\.model_zoo\.attribute no carga"):
        load_age_estimator(_modelo(tmp_path))

    assert bibliotecas.modelos == []


# --- La edad ------------------------------------------------------------------------


def test_la_edad_va_con_el_recorte_y_su_caja_y_no_se_queda_con_nada_mas(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    estimador = InsightFaceAges(_modelo(tmp_path))
    recorte = _recorte()

    lectura = estimador.estimate(recorte)

    assert lectura == AgeReading(years=41, sure=True)
    [modelo] = bibliotecas.modelos
    [(imagen, cara)] = modelo.vistas
    assert imagen == "la imagen del recorte"
    assert cara.bbox == _Array(recorte.box, "float32")
    assert type(lectura.years) is int


def test_la_edad_de_una_cara_lejana_o_girada_no_se_lee_segura(
    bibliotecas: _Bibliotecas, tmp_path: Path
) -> None:
    estimador = InsightFaceAges(_modelo(tmp_path))

    assert estimador.estimate(_recorte(lado=SMALLEST_SURE_FACE - 1)) == AgeReading(41, False)
    assert estimador.estimate(_recorte(nariz=75.0)) == AgeReading(41, False)


# --- Si se lee segura -----------------------------------------------------------------


def test_una_cara_grande_y_de_frente_se_lee_segura() -> None:
    assert reads_sure(_recorte())


def test_desde_el_lado_que_mira_el_modelo_la_edad_se_lee_segura_y_por_debajo_no() -> None:
    assert reads_sure(_recorte(lado=SMALLEST_SURE_FACE))
    assert not reads_sure(_recorte(lado=SMALLEST_SURE_FACE - 0.5))


def test_cuenta_el_lado_mayor_de_la_cara() -> None:
    assert reads_sure(_recorte(lado=40.0, alto=SMALLEST_SURE_FACE))
    assert not reads_sure(_recorte(lado=40.0, alto=SMALLEST_SURE_FACE - 0.5))


@pytest.mark.parametrize("hacia", [1, -1], ids=["a la derecha", "a la izquierda"])
def test_girada_hasta_su_limite_se_lee_segura_y_mas_no(hacia: int) -> None:
    ojos = (40.0, 80.0)
    medio, entre = 60.0, 40.0

    assert reads_sure(_recorte(ojos=ojos, nariz=medio + hacia * MOST_TURNED * entre))
    assert not reads_sure(_recorte(ojos=ojos, nariz=medio + hacia * (MOST_TURNED + 0.01) * entre))


@pytest.mark.parametrize("ojos", [(60.0, 60.0), (80.0, 40.0)], ids=["juntos", "al revés"])
def test_con_los_ojos_juntos_o_al_reves_de_perfil_no_se_lee_segura(
    ojos: tuple[float, float],
) -> None:
    assert not reads_sure(_recorte(ojos=ojos, nariz=60.0))
