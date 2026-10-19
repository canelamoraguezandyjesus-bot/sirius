"""La vista de verdad, cableada con módulos de mentira en lugar de OpenCV y MediaPipe (pieza
D de la 0.4, ADR-262).

Las bibliotecas son del extra ``ojos``, que Quality no instala: aquí se pone un módulo de
mentira en el sitio de cada una y se mira cómo las usa Sirius. Que MediaPipe acierte quién
habla y quién mira lo mide el propietario con su cámara (E-R04-01 y E-R04-02). Lo que sí se
mira aquí: que sin el modelo no carga nada, que lo que no carga lo dice sin tumbar a
Sirius, que la cámara que no se abre o deja de dar imagen se suelta y se dice, y cómo se
saca de cada cara dónde está, si mueve la boca, si mira y su recorte.
"""

from __future__ import annotations

import ast
import importlib.abc
import importlib.machinery
import io
import math
import sys
import types
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

import sirius.adapters.vision.local_sight as vista_module
from sirius.adapters.vision.local_sight import (
    EYE_DEGREES,
    FAILURES_TO_GIVE_UP,
    LOOKING_ASIDE_DEGREES,
    LOOKING_DOWN_DEGREES,
    LOOKING_UP_DEGREES,
    MOST_FACES,
    TALKING_SPREAD,
    TOOLS,
    MediaPipeFaces,
    OpenCvCamera,
    import_sight_library,
    load_sight_engines,
)
from sirius.infrastructure.local_sight_installation import FACE_MODEL_MEMBERS
from sirius.ports.local_sight import CameraUnavailable, SightUnavailable

# --- Los módulos de mentira ---------------------------------------------------------


class _Fotograma:
    """Un fotograma de ``alto`` por ``ancho`` píxeles, como lo da OpenCV, que es un array de
    numpy: cortarlo con ``[arriba:abajo, izquierda:derecha]`` da una vista que sigue
    agarrada a él (``base``) y ve lo que le cambie; ``copy`` da uno suelto."""

    def __init__(
        self,
        pixeles: list[list[int]],
        base: _Fotograma | None = None,
        corte: tuple[slice, slice] | None = None,
    ) -> None:
        self._pixeles = pixeles
        self.base = base
        self._corte = corte

    @classmethod
    def de(cls, alto: int, ancho: int) -> _Fotograma:
        return cls([[fila * 1000 + columna for columna in range(ancho)] for fila in range(alto)])

    @property
    def pixeles(self) -> list[list[int]]:
        if self.base is None or self._corte is None:
            return self._pixeles
        filas, columnas = self._corte
        return [fila[columnas] for fila in self.base.pixeles[filas]]

    @property
    def shape(self) -> tuple[int, int, int]:
        pixeles = self.pixeles
        return (len(pixeles), len(pixeles[0]) if pixeles else 0, 3)

    def __getitem__(self, corte: tuple[slice, slice]) -> _Fotograma:
        return _Fotograma([], base=self, corte=corte)

    def copy(self) -> _Fotograma:
        return _Fotograma([list(fila) for fila in self.pixeles])


@dataclass
class _Captura:
    indice: int
    backend: int
    abierta: bool = True
    lecturas: list[_Fotograma | None] = field(default_factory=list)
    soltada: int = 0
    falla_al_soltar: Exception | None = None

    def isOpened(self) -> bool:
        return self.abierta

    def read(self) -> tuple[bool, _Fotograma | None]:
        fotograma = self.lecturas.pop(0) if self.lecturas else _Fotograma.de(2, 2)
        return fotograma is not None, fotograma

    def release(self) -> None:
        self.soltada += 1
        if self.falla_al_soltar is not None:
            raise self.falla_al_soltar


@dataclass
class _Punto:
    x: float
    y: float


@dataclass
class _Forma:
    category_name: str
    score: float


@dataclass
class _Resultado:
    face_landmarks: list[list[_Punto]]
    face_blendshapes: list[list[_Forma]]
    facial_transformation_matrixes: list[list[list[float]]]


def _cabeza(
    a_la_derecha: float = 0.0,
    abajo: float = 0.0,
    donde: tuple[float, float, float] = (0.0, 0.0, -50.0),
) -> list[list[float]]:
    """La matriz que da MediaPipe de una cabeza en ``donde``, en centímetros desde la cámara
    (x a la derecha de la imagen, y arriba, la cámara mirando hacia -z), que apunta
    ``a_la_derecha`` grados hacia la derecha de la imagen y ``abajo`` grados hacia abajo."""
    g, b = math.radians(a_la_derecha), math.radians(abajo)
    # Primero hacia abajo, alrededor del eje de lado a lado; después, al lado.
    giro = [
        [math.cos(g), math.sin(g) * math.sin(b), math.sin(g) * math.cos(b)],
        [0.0, math.cos(b), -math.sin(b)],
        [-math.sin(g), math.cos(g) * math.sin(b), math.cos(g) * math.cos(b)],
    ]
    return [[*giro[fila], donde[fila]] for fila in range(3)] + [[0.0, 0.0, 0.0, 1.0]]


def _de_frente() -> list[list[float]]:
    return _cabeza()


@dataclass
class _CaraVista:
    """Una cara como la da MediaPipe: su caja de puntos, la boca y los ojos y cómo gira."""

    izquierda: float
    derecha: float
    arriba: float = 0.2
    abajo: float = 0.6
    boca: float = 0.0
    ojos: dict[str, float] = field(default_factory=dict)
    giro: list[list[float]] = field(default_factory=_de_frente)

    def puntos(self) -> list[_Punto]:
        return [
            _Punto(self.izquierda, self.arriba),
            _Punto(self.derecha, self.arriba),
            _Punto(self.izquierda, self.abajo),
            _Punto(self.derecha, self.abajo),
        ]

    def formas(self) -> list[_Forma]:
        return [_Forma("jawOpen", self.boca), *(_Forma(n, v) for n, v in self.ojos.items())]


class _Detector:
    """El Face Landmarker de mentira: da las caras que le pongan, y apunta con qué momento
    le preguntan y qué imagen le dan."""

    def __init__(self) -> None:
        self.caras: list[list[_CaraVista]] = []
        self.momentos: list[int] = []
        self.imagenes: list[Any] = []

    def detect_for_video(self, image: Any, moment: int) -> _Resultado:
        self.momentos.append(moment)
        self.imagenes.append(image)
        caras = self.caras.pop(0) if self.caras else []
        return _Resultado(
            [c.puntos() for c in caras], [c.formas() for c in caras], [c.giro for c in caras]
        )


@dataclass
class _Bibliotecas:
    cv2: types.ModuleType
    capturas: list[_Captura]
    opciones: list[dict[str, Any]]
    detector: _Detector
    convertidos: list[tuple[Any, int]]


@pytest.fixture
def bibliotecas(monkeypatch: pytest.MonkeyPatch) -> _Bibliotecas:
    """Pone OpenCV y MediaPipe de mentira en el sitio de los de verdad."""
    capturas: list[_Captura] = []
    opciones: list[dict[str, Any]] = []
    convertidos: list[tuple[Any, int]] = []
    detector = _Detector()

    def modulo(nombre: str, **atributos: Any) -> types.ModuleType:
        nuevo = types.ModuleType(nombre)
        for clave, valor in atributos.items():
            setattr(nuevo, clave, valor)
        monkeypatch.setitem(sys.modules, nombre, nuevo)
        return nuevo

    def captura(indice: int, backend: int) -> _Captura:
        nueva = _Captura(indice, backend)
        capturas.append(nueva)
        return nueva

    def convierte(fotograma: Any, codigo: int) -> Any:
        convertidos.append((fotograma, codigo))
        return ("rgb", fotograma)

    def crea(opcion: types.SimpleNamespace) -> _Detector:
        opciones.append(vars(opcion))
        return detector

    cv2 = modulo(
        "cv2", CAP_DSHOW=700, CAP_ANY=0, COLOR_BGR2RGB=4, VideoCapture=captura, cvtColor=convierte
    )
    modulo(
        "mediapipe",
        Image=lambda **kw: types.SimpleNamespace(**kw),
        ImageFormat=types.SimpleNamespace(SRGB="SRGB"),
    )
    modulo("mediapipe.tasks")
    modulo("mediapipe.tasks.python", BaseOptions=lambda **kw: types.SimpleNamespace(**kw))
    modulo(
        "mediapipe.tasks.python.vision",
        FaceLandmarkerOptions=lambda **kw: types.SimpleNamespace(**kw),
        RunningMode=types.SimpleNamespace(VIDEO="VIDEO"),
        FaceLandmarker=types.SimpleNamespace(create_from_options=crea),
    )
    return _Bibliotecas(cv2, capturas, opciones, detector, convertidos)


@pytest.fixture
def modelo(tmp_path: Path) -> Path:
    ruta = tmp_path / "face_landmarker.task"
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zip_:
        for nombre in FACE_MODEL_MEMBERS:
            zip_.writestr(nombre, b"pesos")
    ruta.write_bytes(salida.getvalue())
    return ruta


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 10.0

    def __call__(self) -> float:
        return self.ahora


def _caras(bibliotecas: _Bibliotecas, modelo: Path, reloj: _Reloj | None = None) -> MediaPipeFaces:
    return MediaPipeFaces(modelo, clock=reloj or _Reloj())


# --- Cargar la vista -----------------------------------------------------------------


def test_sin_el_modelo_de_las_caras_no_carga_nada(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    importadas: list[str] = []
    monkeypatch.setattr(vista_module, "import_sight_library", importadas.append)

    with pytest.raises(SightUnavailable) as fallo:
        load_sight_engines(tmp_path / "face_landmarker.task")

    assert fallo.value.reason == "falta el modelo de las caras"
    assert importadas == []


def test_con_el_modelo_carga_mediapipe_en_modo_de_video_sin_abrir_la_camara(
    bibliotecas: _Bibliotecas, modelo: Path
) -> None:
    motores = load_sight_engines(modelo)

    assert isinstance(motores.camera, OpenCvCamera)
    assert isinstance(motores.detector, MediaPipeFaces)
    assert motores.detector.name == "mediapipe"
    (opcion,) = bibliotecas.opciones
    assert vars(opcion["base_options"]) == {"model_asset_path": str(modelo)}
    assert opcion["running_mode"] == "VIDEO"
    assert opcion["num_faces"] == MOST_FACES == 4
    assert opcion["output_face_blendshapes"] is True
    assert opcion["output_facial_transformation_matrixes"] is True
    assert bibliotecas.capturas == [], "cargar no abre la cámara"


@pytest.mark.parametrize("biblioteca", ["cv2", "mediapipe", "mediapipe.tasks.python.vision"])
def test_sin_el_extra_ojos_avisa_y_no_tumba_a_sirius(
    bibliotecas: _Bibliotecas, modelo: Path, monkeypatch: pytest.MonkeyPatch, biblioteca: str
) -> None:
    monkeypatch.setitem(sys.modules, biblioteca, None)

    with pytest.raises(SightUnavailable) as fallo:
        load_sight_engines(modelo)

    assert fallo.value.reason.startswith(f"{biblioteca} no carga")


class _QueNoCarga(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Una biblioteca nativa que falla al importarse con lo que quiera, como una DLL."""

    def __init__(self, nombre: str, error: Exception) -> None:
        self.nombre = nombre
        self.error = error

    def find_spec(
        self, fullname: str, path: Sequence[str] | None, target: types.ModuleType | None = None
    ) -> importlib.machinery.ModuleSpec | None:
        del path, target
        return importlib.machinery.ModuleSpec(fullname, self) if fullname == self.nombre else None

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> types.ModuleType | None:
        del spec
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        del module
        raise self.error


@pytest.mark.parametrize(
    "error",
    [OSError("DLL load failed while importing cv2"), RuntimeError("numpy 2 incompatible")],
)
def test_una_biblioteca_nativa_que_no_carga_avisa_y_no_tumba_a_sirius(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    monkeypatch.delitem(sys.modules, "cv2", raising=False)
    monkeypatch.setattr(sys, "meta_path", [_QueNoCarga("cv2", error), *sys.meta_path])

    with pytest.raises(SightUnavailable) as fallo:
        import_sight_library("cv2")

    assert fallo.value.reason == f"cv2 no carga ({error})"


def test_un_modelo_que_esta_y_no_carga_avisa_y_no_tumba_a_sirius(
    bibliotecas: _Bibliotecas, modelo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_carga(opcion: object) -> None:
        raise RuntimeError("Unable to open zip archive")

    vision = sys.modules["mediapipe.tasks.python.vision"]
    monkeypatch.setattr(
        vision, "FaceLandmarker", types.SimpleNamespace(create_from_options=no_carga)
    )

    with pytest.raises(SightUnavailable) as fallo:
        load_sight_engines(modelo)

    assert fallo.value.reason == "el modelo de las caras no carga (Unable to open zip archive)"


def test_ninguna_funcion_de_la_vista_importa_por_su_cuenta() -> None:
    # Todas sus bibliotecas entran por `import_sight_library`, que traduce cualquier fallo:
    # un import suelto dentro de una función tumbaría a Sirius si falla (H-242).
    fuente = Path(vista_module.__file__).read_text(encoding="utf-8")
    sueltos = [
        f"{funcion.name}:{nodo.lineno}"
        for funcion in ast.walk(ast.parse(fuente))
        if isinstance(funcion, ast.FunctionDef | ast.AsyncFunctionDef)
        for nodo in ast.walk(funcion)
        if isinstance(nodo, ast.Import | ast.ImportFrom)
    ]

    assert sueltos == []


# --- La cámara -----------------------------------------------------------------------


@pytest.mark.parametrize(("plataforma", "backend"), [("win32", 700), ("linux", 0)])
def test_abre_la_primera_camara_con_directshow_en_windows(
    bibliotecas: _Bibliotecas, monkeypatch: pytest.MonkeyPatch, plataforma: str, backend: int
) -> None:
    monkeypatch.setattr(sys, "platform", plataforma)
    camara = OpenCvCamera()

    camara.open()

    (captura,) = bibliotecas.capturas
    assert (captura.indice, captura.backend) == (0, backend)


def test_sin_camara_o_si_la_tiene_otro_programa_la_suelta_y_lo_dice(
    bibliotecas: _Bibliotecas, monkeypatch: pytest.MonkeyPatch
) -> None:
    def cerrada(indice: int, backend: int) -> _Captura:
        nueva = _Captura(indice, backend, abierta=False)
        bibliotecas.capturas.append(nueva)
        return nueva

    monkeypatch.setattr(bibliotecas.cv2, "VideoCapture", cerrada)
    camara = OpenCvCamera()

    with pytest.raises(CameraUnavailable) as fallo:
        camara.open()

    assert fallo.value.reason == "no hay cámara, o la tiene otro programa"
    assert bibliotecas.capturas[0].soltada == 1
    assert camara.read() is None, "no se queda con una cámara que no se abrió"


def test_da_cada_fotograma_y_uno_que_no_llega_es_nada(bibliotecas: _Bibliotecas) -> None:
    camara = OpenCvCamera()
    camara.open()
    fotograma = _Fotograma.de(2, 3)
    bibliotecas.capturas[0].lecturas.extend([fotograma, None])

    assert camara.read() is fotograma
    assert camara.read() is None


def test_diez_lecturas_seguidas_sin_imagen_dan_la_camara_por_perdida(
    bibliotecas: _Bibliotecas,
) -> None:
    camara = OpenCvCamera()
    camara.open()
    captura = bibliotecas.capturas[0]
    captura.lecturas.extend([None] * (FAILURES_TO_GIVE_UP - 1))
    captura.lecturas.append(_Fotograma.de(1, 1))
    captura.lecturas.extend([None] * FAILURES_TO_GIVE_UP)

    for _ in range(FAILURES_TO_GIVE_UP - 1):
        assert camara.read() is None
    assert camara.read() is not None, "una buena empieza la cuenta de nuevo"
    for _ in range(FAILURES_TO_GIVE_UP - 1):
        assert camara.read() is None
    with pytest.raises(CameraUnavailable) as fallo:
        camara.read()

    assert FAILURES_TO_GIVE_UP == 10
    assert fallo.value.reason == "la cámara ha dejado de dar imagen"


def test_soltarla_la_suelta_una_vez_y_no_falla_aunque_falle_ella(
    bibliotecas: _Bibliotecas,
) -> None:
    camara = OpenCvCamera()
    assert camara.read() is None, "cerrada no da nada"
    camara.close()
    camara.open()
    captura = bibliotecas.capturas[0]
    captura.falla_al_soltar = RuntimeError("ya no está")

    camara.close()
    camara.close()

    assert captura.soltada == 1
    assert camara.read() is None


# --- Las caras -----------------------------------------------------------------------


def test_le_da_a_mediapipe_el_fotograma_en_rgb(bibliotecas: _Bibliotecas, modelo: Path) -> None:
    caras = _caras(bibliotecas, modelo)
    fotograma = _Fotograma.de(4, 4)

    caras.detect(fotograma)

    assert bibliotecas.convertidos == [(fotograma, 4)]
    (imagen,) = bibliotecas.detector.imagenes
    assert vars(imagen) == {"image_format": "SRGB", "data": ("rgb", fotograma)}


def test_los_momentos_del_modo_de_video_siempre_crecen(
    bibliotecas: _Bibliotecas, modelo: Path
) -> None:
    reloj = _Reloj()
    caras = _caras(bibliotecas, modelo, reloj)

    caras.detect(_Fotograma.de(2, 2))
    caras.detect(_Fotograma.de(2, 2))
    reloj.ahora = 9.0
    caras.detect(_Fotograma.de(2, 2))
    reloj.ahora = 12.5
    caras.detect(_Fotograma.de(2, 2))

    assert bibliotecas.detector.momentos == [10_000, 10_001, 10_002, 12_500]


def test_donde_esta_cada_cara_es_el_centro_de_sus_puntos(
    bibliotecas: _Bibliotecas, modelo: Path
) -> None:
    caras = _caras(bibliotecas, modelo)
    bibliotecas.detector.caras.append([_CaraVista(0.1, 0.3), _CaraVista(0.6, 0.9)])

    vistas = caras.detect(_Fotograma.de(10, 10))

    assert [cara.x for cara in vistas] == pytest.approx([0.2, 0.75])


def test_el_recorte_es_una_copia_de_su_trozo_del_fotograma(
    bibliotecas: _Bibliotecas, modelo: Path
) -> None:
    caras = _caras(bibliotecas, modelo)
    bibliotecas.detector.caras.append([_CaraVista(0.2, 0.5, arriba=0.1, abajo=0.4)])
    fotograma = _Fotograma.de(10, 10)

    (cara,) = caras.detect(fotograma)
    recorte = cara.crop
    fotograma.pixeles[2][3] = -1

    assert recorte.shape[:2] == (4, 4)
    assert recorte.pixeles[0] == [1002, 1003, 1004, 1005]
    assert recorte.base is None, "el recorte se queda agarrado al fotograma entero"
    assert -1 not in [p for fila in recorte.pixeles for p in fila], "no es una copia"


def test_una_cara_que_se_sale_por_un_borde_se_recorta_hasta_el_borde(
    bibliotecas: _Bibliotecas, modelo: Path
) -> None:
    caras = _caras(bibliotecas, modelo)
    bibliotecas.detector.caras.append([_CaraVista(-0.2, 0.15, arriba=-0.1, abajo=1.3)])

    (cara,) = caras.detect(_Fotograma.de(10, 10))

    assert cara.crop.shape[:2] == (10, 2)


def _boca(
    bibliotecas: _Bibliotecas, caras: MediaPipeFaces, reloj: _Reloj, *aperturas: float
) -> list[bool]:
    """Lo abierta que tiene la boca la misma cara en fotogramas de 0,1 s en 0,1 s; si habla
    en cada uno."""
    hablando: list[bool] = []
    for apertura in aperturas:
        bibliotecas.detector.caras.append([_CaraVista(0.4, 0.6, boca=apertura)])
        (cara,) = caras.detect(_Fotograma.de(2, 2))
        hablando.append(cara.talking)
        reloj.ahora += 0.1
    return hablando


def test_mueve_la_boca_si_lo_abierta_que_la_tiene_cambia_en_el_ultimo_segundo(
    bibliotecas: _Bibliotecas, modelo: Path
) -> None:
    reloj = _Reloj()
    caras = _caras(bibliotecas, modelo, reloj)

    hablando = _boca(
        bibliotecas, caras, reloj, 0.1, 0.1 + TALKING_SPREAD * 0.5, 0.1 + TALKING_SPREAD * 1.5
    )

    assert hablando == [False, False, True]
    assert TALKING_SPREAD == 0.08


def test_una_boca_quieta_aunque_abierta_no_habla_y_lo_de_hace_mas_de_un_segundo_se_olvida(
    bibliotecas: _Bibliotecas, modelo: Path
) -> None:
    reloj = _Reloj()
    caras = _caras(bibliotecas, modelo, reloj)

    hablando = _boca(bibliotecas, caras, reloj, 0.1, 0.5, *([0.5] * 11))

    assert hablando[1] is True
    assert hablando[-1] is False, "se acuerda de la boca de hace más de un segundo"


def test_sigue_cada_boca_por_donde_esta_su_cara(bibliotecas: _Bibliotecas, modelo: Path) -> None:
    reloj = _Reloj()
    caras = _caras(bibliotecas, modelo, reloj)
    quieta, habla = (0.1, 0.3), (0.6, 0.8)
    bibliotecas.detector.caras.append([_CaraVista(*quieta, boca=0.4), _CaraVista(*habla, boca=0.0)])
    caras.detect(_Fotograma.de(2, 2))
    reloj.ahora += 0.1
    # MediaPipe las da en otro orden: cada boca sigue con su cara.
    bibliotecas.detector.caras.append([_CaraVista(*habla, boca=0.4), _CaraVista(*quieta, boca=0.4)])

    vistas = caras.detect(_Fotograma.de(2, 2))

    assert [(round(c.x, 2), c.talking) for c in vistas] == [(0.7, True), (0.2, False)]


#: Lo que dio MediaPipe 1.1.1 de la foto de pruebas de siempre, la de OpenCV, de una cara
#: que mira a la cámara con la cabeza girada unos 20 grados y los ojos compensándolo: su
#: matriz y lo que dice de sus ojos; y lo mismo de la foto volteada. Fijan hacia dónde va
#: cada cosa en lo que da MediaPipe de verdad.
_FOTO = (
    [
        [0.937, 0.129, 0.323, 2.724],
        [-0.057, 0.973, -0.224, -3.395],
        [-0.343, 0.192, 0.919, -42.361],
        [0.0, 0.0, 0.0, 1.0],
    ],
    {
        "eyeLookDownLeft": 0.0,
        "eyeLookDownRight": 0.01,
        "eyeLookInLeft": 0.83,
        "eyeLookInRight": 0.0,
        "eyeLookOutLeft": 0.0,
        "eyeLookOutRight": 0.86,
        "eyeLookUpLeft": 0.63,
        "eyeLookUpRight": 0.59,
    },
)
_FOTO_VOLTEADA = (
    [
        [0.938, -0.113, -0.328, -2.75],
        [0.045, 0.977, -0.207, -3.393],
        [0.344, 0.179, 0.922, -42.525],
        [0.0, 0.0, 0.0, 1.0],
    ],
    {
        "eyeLookDownLeft": 0.01,
        "eyeLookDownRight": 0.01,
        "eyeLookInLeft": 0.0,
        "eyeLookInRight": 0.88,
        "eyeLookOutLeft": 0.87,
        "eyeLookOutRight": 0.0,
        "eyeLookUpLeft": 0.45,
        "eyeLookUpRight": 0.46,
    },
)
#: Los ojos del todo hacia la izquierda de la imagen, y hacia la derecha.
_OJOS_A_LA_IZQUIERDA = {"eyeLookInLeft": 1.0, "eyeLookOutRight": 1.0}
_OJOS_A_LA_DERECHA = {"eyeLookOutLeft": 1.0, "eyeLookInRight": 1.0}


@pytest.mark.parametrize(
    ("cabeza", "ojos", "mira"),
    [
        pytest.param(_de_frente(), {}, True, id="de frente"),
        pytest.param(_cabeza(15), {}, True, id="la cabeza un poco a un lado"),
        pytest.param(_cabeza(30), {}, False, id="la cabeza a un lado"),
        pytest.param(_cabeza(-30), {}, False, id="la cabeza al otro"),
        pytest.param(
            _cabeza(30), _OJOS_A_LA_IZQUIERDA, True, id="la cabeza a un lado y los ojos a el"
        ),
        pytest.param(_cabeza(30), _OJOS_A_LA_DERECHA, False, id="la cabeza y los ojos a un lado"),
        pytest.param(
            _de_frente(),
            {"eyeLookOutLeft": 0.8, "eyeLookInRight": 0.8},
            False,
            id="los ojos a un lado",
        ),
        pytest.param(
            _cabeza(-26.57, donde=(25.0, 0.0, -50.0)), {}, True, id="desde un lado, a la camara"
        ),
        pytest.param(
            _cabeza(0, donde=(25.0, 0.0, -50.0)), {}, False, id="desde un lado, al frente"
        ),
        pytest.param(
            _cabeza(abajo=-26.57, donde=(0.0, -25.0, -50.0)),
            {},
            True,
            id="desde abajo, a la camara",
        ),
        pytest.param(_cabeza(abajo=25), {}, True, id="a la pantalla, debajo de la camara"),
        pytest.param(_cabeza(abajo=45), {}, False, id="al teclado"),
        pytest.param(_cabeza(abajo=-20), {}, False, id="por encima de la camara"),
        pytest.param(
            _cabeza(abajo=45),
            {"eyeLookUpLeft": 0.6, "eyeLookUpRight": 0.6},
            True,
            id="la cabeza al teclado y los ojos a la pantalla",
        ),
        pytest.param(_cabeza(180), {}, False, id="de espaldas"),
        pytest.param(*_FOTO, True, id="la foto de pruebas"),
        pytest.param(*_FOTO_VOLTEADA, True, id="la foto de pruebas volteada"),
        pytest.param(_FOTO[0], {}, False, id="la foto de pruebas sin sus ojos"),
    ],
)
def test_le_mira_si_adonde_apuntan_la_cabeza_y_los_ojos_va_hacia_el(
    bibliotecas: _Bibliotecas,
    modelo: Path,
    cabeza: list[list[float]],
    ojos: dict[str, float],
    mira: bool,
) -> None:
    caras = _caras(bibliotecas, modelo)
    bibliotecas.detector.caras.append([_CaraVista(0.4, 0.6, ojos=ojos, giro=cabeza)])

    (cara,) = caras.detect(_Fotograma.de(2, 2))

    assert cara.looking is mira
    assert (EYE_DEGREES, LOOKING_ASIDE_DEGREES) == (30.0, 20.0)
    assert (LOOKING_UP_DEGREES, LOOKING_DOWN_DEGREES) == (15.0, 35.0)


def test_una_cabeza_en_la_misma_camara_no_mira_a_ningun_sitio(
    bibliotecas: _Bibliotecas, modelo: Path
) -> None:
    caras = _caras(bibliotecas, modelo)
    bibliotecas.detector.caras.append([_CaraVista(0.4, 0.6, giro=_cabeza(donde=(0.0, 0.0, 0.0)))])

    (cara,) = caras.detect(_Fotograma.de(2, 2))

    assert cara.looking is False


def test_sin_saber_como_gira_la_cabeza_no_cuenta_que_mire(
    bibliotecas: _Bibliotecas, modelo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caras = _caras(bibliotecas, modelo)
    bibliotecas.detector.caras.append([_CaraVista(0.4, 0.6)])
    original = bibliotecas.detector.detect_for_video

    def sin_giro(image: Any, moment: int) -> _Resultado:
        resultado = original(image, moment)
        resultado.facial_transformation_matrixes = []
        resultado.face_blendshapes = []
        return resultado

    monkeypatch.setattr(bibliotecas.detector, "detect_for_video", sin_giro)

    (cara,) = caras.detect(_Fotograma.de(2, 2))

    assert (cara.looking, cara.talking) == (False, False)


def test_con_que_ve_es_lo_que_importa_al_cargar() -> None:
    # PA-R04-06 lee con qué ve de `TOOLS`: tiene que ser lo que importa la vista, por
    # `import_sight_library`, con OpenCV por su nombre y no por el de su módulo, `cv2`.
    fuente = Path(vista_module.__file__).read_text(encoding="utf-8")
    importadas = {
        nodo.args[0].value
        for nodo in ast.walk(ast.parse(fuente))
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Name)
        and nodo.func.id == "import_sight_library"
        and nodo.args
        and isinstance(nodo.args[0], ast.Constant)
        and isinstance(nodo.args[0].value, str)
    }
    herramientas = {"opencv" if m == "cv2" else m.split(".")[0] for m in importadas}

    assert importadas >= {"cv2", "mediapipe"}
    assert herramientas == set(TOOLS)
