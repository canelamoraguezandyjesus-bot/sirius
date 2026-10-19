"""La regla de los críos y los ancianos frágiles (pieza F de la 0.4, ADR-264): quién pide
cuidado, el estimador que se carga la primera vez, y la edad de cada cara en la vista, sin
estimarla en cada fotograma."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

import pytest

from sirius.application.age import CARE_HEADING, CARE_RULE, Ages, care_block, needs_care
from sirius.application.local_sight import RECOGNIZE_AGAIN_SECONDS, SAME_PLACE, LocalSight
from sirius.ports.age import AgeReading, AgeUnavailable
from sirius.ports.local_sight import SeenFace, SightEngines

_ORDEN = "uv run --link-mode=copy --extra voz --extra ojos sirius-instala-la-voz"


# --- Quién pide cuidado ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("anos", "cuidado"),
    [(5, True), (19, True), (20, False), (40, False), (64, False), (65, True), (90, True)],
)
def test_un_crio_es_quien_aparenta_menos_de_20_y_un_anciano_65_o_mas(
    anos: int, cuidado: bool
) -> None:
    assert needs_care([AgeReading(anos, sure=True)]) is cuidado


def test_ante_la_duda_tambien_aunque_aparente_un_adulto() -> None:
    assert needs_care([AgeReading(40, sure=False)])
    assert needs_care([None]), "una edad que no se sabe es duda"


def test_basta_uno_y_sin_nadie_no_hay_regla() -> None:
    adulto = AgeReading(40, sure=True)

    assert needs_care([adulto, AgeReading(8, sure=True), adulto])
    assert not needs_care([adulto, adulto])
    assert not needs_care([])


def test_la_regla_lleva_su_titulo_y_dice_que_no_insulta() -> None:
    bloque = care_block()

    assert bloque.splitlines()[0] == CARE_HEADING
    assert CARE_RULE in bloque
    assert "insultos" in CARE_RULE


# --- El estimador, que se carga la primera vez ----------------------------------------


@dataclass
class _Estimador:
    """Quien estima la edad, de mentira: de cada recorte, la edad que tenga apuntada."""

    name: str = "insightface"
    edades: dict[str, AgeReading] = field(
        default_factory=lambda: {"lucas": AgeReading(8, True), "marta": AgeReading(40, True)}
    )
    falla: Exception | None = None
    vistos: list[str] = field(default_factory=list)

    def estimate(self, crop: str) -> AgeReading:
        self.vistos.append(crop)
        if self.falla is not None:
            raise self.falla
        return self.edades[crop]


class _Carga:
    """Cuenta las veces que se carga, y falla si se le dice."""

    def __init__(self, estimador: _Estimador | None = None) -> None:
        self.estimador = estimador if estimador is not None else _Estimador()
        self.veces = 0
        self.falla: Exception | None = None

    def __call__(self) -> _Estimador:
        self.veces += 1
        if self.falla is not None:
            raise self.falla
        return self.estimador


def test_se_carga_la_primera_vez_que_hace_falta_y_solo_esa() -> None:
    carga = _Carga()
    edades = Ages(carga)

    assert carga.veces == 0, "construirlo no carga nada"
    assert edades.name == ""
    assert edades.estimate("lucas") == AgeReading(8, True)
    assert edades.estimate("marta") == AgeReading(40, True)
    assert carga.veces == 1
    assert edades.name == "insightface"
    assert edades.unavailable == ""


def test_si_no_carga_lo_dice_una_vez_no_lo_vuelve_a_intentar_y_la_edad_no_se_sabe(
    caplog: pytest.LogCaptureFixture,
) -> None:
    carga = _Carga()
    carga.falla = AgeUnavailable("falta el modelo de la edad")
    edades = Ages(carga)

    with caplog.at_level(logging.INFO):
        assert edades.estimate("lucas") is None
        assert edades.estimate("marta") is None

    assert carga.veces == 1
    assert edades.unavailable == "falta el modelo de la edad"
    avisos = [r.getMessage() for r in caplog.records if "estimar la edad" in r.getMessage()]
    assert avisos == ["No se puede estimar la edad: falta el modelo de la edad"]


def test_un_fallo_cualquiera_al_cargar_se_dice_con_su_causa() -> None:
    carga = _Carga()
    carga.falla = RuntimeError("un onnx roto")
    edades = Ages(carga)

    assert edades.estimate("lucas") is None
    assert edades.unavailable == "el modelo de la edad no carga (un onnx roto)"


def test_un_fallo_al_estimar_se_apunta_una_vez_con_su_tipo_y_esa_vez_no_se_sabe(
    caplog: pytest.LogCaptureFixture,
) -> None:
    estimador = _Estimador(falla=ValueError("Lucas, de ocho años"))
    edades = Ages(_Carga(estimador))

    with caplog.at_level(logging.ERROR):
        assert edades.estimate("lucas") is None
        assert edades.estimate("lucas") is None

    errores = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errores == ["El estimador de la edad ha fallado (ValueError)"]
    assert "Lucas" not in caplog.text, "ni lo que decía el fallo"
    estimador.falla = None
    assert edades.estimate("lucas") == AgeReading(8, True), "y la siguiente vez, sí"


def test_dos_hilos_a_la_vez_lo_cargan_una_sola_vez() -> None:
    soltar = threading.Event()
    estimador = _Estimador()
    veces: list[int] = []

    def carga() -> _Estimador:
        veces.append(1)
        assert soltar.wait(5)
        return estimador

    edades = Ages(carga)
    leidas: list[AgeReading | None] = []
    hilos = [
        threading.Thread(target=lambda: leidas.append(edades.estimate("lucas"))) for _ in range(2)
    ]
    for hilo in hilos:
        hilo.start()
    soltar.set()
    for hilo in hilos:
        hilo.join(5)

    assert veces == [1]
    assert leidas == [AgeReading(8, True), AgeReading(8, True)]


# --- La edad de cada cara, en la vista ------------------------------------------------


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 50.0

    def __call__(self) -> float:
        return self.ahora


class _Camara:
    def open(self) -> None:
        return None

    def read(self) -> str:
        return "fotograma"

    def close(self) -> None:
        return None


@dataclass
class _Detector:
    name: str = "mediapipe"
    caras: list[tuple[SeenFace[str], ...]] = field(default_factory=list)

    def detect(self, frame: str) -> tuple[SeenFace[str], ...]:
        return self.caras.pop(0) if self.caras else ()


class _Montaje:
    def __init__(self, estimador: _Estimador | None = None, *, con_edad: bool = True) -> None:
        self.reloj = _Reloj()
        self.detector = _Detector()
        self.estimador = estimador if estimador is not None else _Estimador()
        self.vista = LocalSight(
            load_engines=lambda: SightEngines(_Camara(), self.detector),
            clock=self.reloj,
            install_command=_ORDEN,
            ages=Ages(lambda: self.estimador) if con_edad else None,
        )
        self.vista.start()

    def ve(self, *caras: tuple[str, float], despues: float = 0.1) -> None:
        """Pasa ``despues`` segundos y mira una vez, con cada cara, su recorte y dónde está."""
        self.reloj.ahora += despues
        self.detector.caras.append(tuple(SeenFace(x, False, False, crop) for crop, x in caras))
        self.vista.look()


def test_cada_cara_lleva_la_edad_que_aparenta() -> None:
    montaje = _Montaje()

    montaje.ve(("marta", 0.3), ("lucas", 0.7))

    assert [cara.age for cara in montaje.vista.in_front()] == [
        AgeReading(40, True),
        AgeReading(8, True),
    ]
    assert montaje.vista.in_front_ages() == (AgeReading(40, True), AgeReading(8, True))


def test_sin_quien_reconozca_la_edad_se_estima_igual() -> None:
    montaje = _Montaje()

    montaje.ve(("lucas", 0.5))

    assert montaje.vista.in_front_names() == (None,)
    assert montaje.vista.in_front_ages() == (AgeReading(8, True),)


def test_una_cara_que_sigue_donde_estaba_no_se_vuelve_a_estimar_hasta_pasado_un_rato() -> None:
    montaje = _Montaje()
    montaje.ve(("lucas", 0.3))

    montaje.ve(("lucas", 0.3 + SAME_PLACE * 0.9), despues=RECOGNIZE_AGAIN_SECONDS * 0.4)
    montaje.ve(("lucas", 0.3), despues=RECOGNIZE_AGAIN_SECONDS * 0.5)
    assert montaje.estimador.vistos == ["lucas"]
    assert montaje.vista.in_front_ages() == (AgeReading(8, True),), "con lo que recuerda"

    montaje.ve(("lucas", 0.3), despues=RECOGNIZE_AGAIN_SECONDS * 0.2)
    assert montaje.estimador.vistos == ["lucas", "lucas"]


def test_una_cara_que_aparece_en_otro_sitio_se_estima_en_el_acto() -> None:
    montaje = _Montaje()
    montaje.ve(("marta", 0.3))

    montaje.ve(("marta", 0.3), ("lucas", 0.3 + SAME_PLACE * 1.1))

    assert montaje.estimador.vistos == ["marta", "lucas"]
    assert montaje.vista.in_front_ages() == (AgeReading(40, True), AgeReading(8, True))


def test_dos_caras_que_se_cruzan_no_se_quedan_las_dos_con_la_misma_edad() -> None:
    montaje = _Montaje()
    montaje.ve(("marta", 0.40))

    montaje.ve(("marta", 0.42), ("lucas", 0.38))

    assert montaje.estimador.vistos == ["marta", "lucas"], "la de antes vale para una sola"
    assert montaje.vista.in_front_ages() == (AgeReading(40, True), AgeReading(8, True))


def test_un_fallo_al_estimar_es_no_saber_la_edad_y_la_vista_sigue(
    caplog: pytest.LogCaptureFixture,
) -> None:
    montaje = _Montaje(_Estimador(falla=RuntimeError("roto")))

    with caplog.at_level(logging.ERROR):
        montaje.ve(("lucas", 0.5))
        montaje.ve(("lucas", 0.5), despues=RECOGNIZE_AGAIN_SECONDS)

    assert montaje.vista.in_front_ages() == (None,)
    assert montaje.vista.seeing
    errores = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errores == ["El estimador de la edad ha fallado (RuntimeError)"]


def test_un_fallo_de_quien_estima_que_se_le_escapa_a_la_vista_se_apunta_una_vez(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class _Rota:
        def estimate(self, crop: str) -> AgeReading | None:
            raise RuntimeError(crop)

    reloj = _Reloj()
    detector = _Detector()
    vista = LocalSight(
        load_engines=lambda: SightEngines(_Camara(), detector),
        clock=reloj,
        install_command=_ORDEN,
        ages=_Rota(),
    )
    vista.start()

    with caplog.at_level(logging.ERROR):
        for _ in range(2):
            detector.caras.append((SeenFace(0.5, False, False, "lucas"),))
            vista.look()

    assert vista.in_front_ages() == (None,)
    errores = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errores == ["Quien estima la edad ha fallado (RuntimeError)"]
    assert "lucas" not in caplog.text


def test_sin_ver_o_sin_quien_estime_la_edad_no_se_sabe_quien_hay() -> None:
    montaje = _Montaje()
    montaje.ve()
    assert montaje.vista.in_front_ages() == (), "ve, y no hay nadie"

    montaje.ve(("lucas", 0.5))
    montaje.vista.stop()
    assert montaje.vista.in_front_ages() is None

    sin_edad = _Montaje(con_edad=False)
    sin_edad.ve(("lucas", 0.5))
    assert sin_edad.vista.in_front_ages() is None
    assert sin_edad.estimador.vistos == []
