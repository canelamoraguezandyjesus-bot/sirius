"""La vista, con quien reconoce caras (pieza E de la 0.4, ADR-263): quién es cada cara, sin
reconocerla en cada fotograma, la cara de quien da permiso, y a quiénes dice que tiene
delante."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pytest

from sirius.application.local_sight import (
    RECOGNIZE_AGAIN_SECONDS,
    SAME_FACE_GAP_SECONDS,
    SAME_PLACE,
    Glimpse,
    LocalSight,
)
from sirius.ports.local_sight import SeenFace, SightEngines

_ORDEN = "uv run --link-mode=copy --extra voz --extra ojos sirius-instala-la-voz"


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
    falla: Exception | None = None

    def detect(self, frame: str) -> tuple[SeenFace[str], ...]:
        if self.falla is not None:
            raise self.falla
        return self.caras.pop(0) if self.caras else ()


@dataclass
class _Reconocer:
    """Quien reconoce caras, de mentira: de cada recorte, el nombre que tenga apuntado."""

    nombres: dict[str, str] = field(default_factory=lambda: {"marta": "Marta"})
    version: int = 0
    quiere_cara: bool = False
    preguntadas: list[str] = field(default_factory=list)
    tomadas: list[str] = field(default_factory=list)
    falla: Exception | None = None

    def wants_face(self) -> bool:
        return self.quiere_cara

    def take_face(self, crop: str) -> None:
        self.tomadas.append(crop)

    def who_by_face(self, crop: str) -> str | None:
        self.preguntadas.append(crop)
        if self.falla is not None:
            raise self.falla
        return self.nombres.get(crop)


class _Montaje:
    def __init__(self, reconocer: _Reconocer | None = None) -> None:
        self.reloj = _Reloj()
        self.detector = _Detector()
        self.reconocer = reconocer if reconocer is not None else _Reconocer()
        self.vista = LocalSight(
            load_engines=lambda: SightEngines(_Camara(), self.detector),
            clock=self.reloj,
            install_command=_ORDEN,
            recognition=self.reconocer,
        )
        self.vista.start()

    def ve(self, *caras: tuple[str, float], despues: float = 0.1) -> None:
        """Pasa ``despues`` segundos y mira una vez, con cada cara, su recorte y dónde está."""
        self.reloj.ahora += despues
        self.detector.caras.append(tuple(SeenFace(x, False, False, crop) for crop, x in caras))
        self.vista.look()


def test_cada_cara_lleva_quien_es_y_la_de_un_desconocido_ninguno() -> None:
    montaje = _Montaje()

    montaje.ve(("pepe", 0.7), ("marta", 0.3))

    assert [cara.who for cara in montaje.vista.in_front()] == [None, "Marta"]
    assert montaje.vista.in_front_names() == (None, "Marta")


def test_una_cara_que_sigue_donde_estaba_no_se_vuelve_a_reconocer_hasta_pasado_un_rato() -> None:
    montaje = _Montaje()
    montaje.ve(("marta", 0.3))

    # Fotograma a fotograma, como mira la vista, moviéndose sin salir de su sitio.
    for _ in range(round(RECOGNIZE_AGAIN_SECONDS / 0.1) - 2):
        montaje.ve(("marta", 0.3 + SAME_PLACE * 0.9))
    assert montaje.reconocer.preguntadas == ["marta"]
    assert montaje.vista.in_front_names() == ("Marta",), "con lo que recuerda de ella"

    montaje.ve(("marta", 0.3), despues=0.3)
    assert montaje.reconocer.preguntadas == ["marta", "marta"]


def test_quien_ocupa_el_sitio_de_otra_tras_un_fotograma_sin_nadie_no_hereda_su_nombre() -> None:
    # Ronda 1 de Codex sobre la PR #703: si Marta se va y alguien ocupa su sitio, estar
    # donde estaba ella no le hace Marta.
    montaje = _Montaje()
    montaje.ve(("marta", 0.3))
    montaje.ve()

    montaje.ve(("pepe", 0.3))

    assert montaje.vista.in_front_names() == (None,)
    assert montaje.reconocer.preguntadas == ["marta", "pepe"]


def test_tras_un_rato_sin_mirar_una_cara_en_el_mismo_sitio_se_reconoce_de_nuevo() -> None:
    montaje = _Montaje()
    montaje.ve(("marta", 0.3))

    montaje.ve(("pepe", 0.3), despues=SAME_FACE_GAP_SECONDS + 0.1)

    assert montaje.vista.in_front_names() == (None,)
    assert montaje.reconocer.preguntadas == ["marta", "pepe"]


def test_una_cara_que_aparece_en_otro_sitio_se_reconoce_en_el_acto() -> None:
    montaje = _Montaje()
    montaje.ve(("marta", 0.3))

    montaje.ve(("marta", 0.3 + SAME_PLACE * 1.1))

    assert montaje.reconocer.preguntadas == ["marta", "marta"]


def test_dos_caras_cerca_no_se_cambian_el_nombre() -> None:
    montaje = _Montaje(_Reconocer(nombres={"marta": "Marta", "pepe": "Pepe"}))
    montaje.ve(("marta", 0.40), ("pepe", 0.50))

    montaje.ve(("pepe", 0.52), ("marta", 0.41))

    assert montaje.vista.in_front_names() == ("Pepe", "Marta")
    assert montaje.reconocer.preguntadas == ["marta", "pepe"]


def test_una_cara_nueva_junto_a_una_conocida_no_hereda_su_nombre() -> None:
    montaje = _Montaje(_Reconocer(nombres={"marta": "Marta"}))
    montaje.ve(("marta", 0.40))

    montaje.ve(("marta", 0.39), ("pepe", 0.43))

    assert montaje.vista.in_front_names() == ("Marta", None)
    assert montaje.reconocer.preguntadas == ["marta", "pepe"]


def test_si_alguien_da_o_quita_su_permiso_vuelve_a_mirar_a_todos() -> None:
    montaje = _Montaje()
    montaje.ve(("marta", 0.3), ("pepe", 0.7))

    montaje.reconocer.version += 1
    montaje.reconocer.nombres = {"pepe": "Pepe"}
    montaje.ve(("marta", 0.3), ("pepe", 0.7))

    assert montaje.reconocer.preguntadas == ["marta", "pepe", "marta", "pepe"]
    assert montaje.vista.in_front_names() == (None, "Pepe")


def test_mientras_alguien_da_permiso_su_cara_va_a_quien_reconoce_si_esta_sola() -> None:
    montaje = _Montaje(_Reconocer(quiere_cara=True))

    montaje.ve(("marta", 0.5))
    montaje.ve(("marta", 0.5))
    montaje.ve(("marta", 0.4), ("pepe", 0.7))
    montaje.ve()

    assert montaje.reconocer.tomadas == ["marta", "marta"]


def test_un_fallo_de_quien_reconoce_se_apunta_una_vez_y_esa_vez_nadie_es_nadie(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)
    montaje = _Montaje()
    montaje.reconocer.falla = RuntimeError("un tensor en /ruta/secreta")

    montaje.ve(("marta", 0.3))
    montaje.ve(("marta", 0.3), despues=RECOGNIZE_AGAIN_SECONDS)

    assert [cara.who for cara in montaje.vista.in_front()] == [None]
    assert montaje.vista.seeing, "sigue viendo"
    errores = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errores) == 1
    assert "RuntimeError" in errores[0].getMessage()
    assert "/ruta/secreta" not in caplog.text


def test_sin_ver_no_dice_a_quien_tiene_delante_y_sin_nadie_dice_que_nadie() -> None:
    montaje = _Montaje()
    montaje.ve()
    assert montaje.vista.in_front_names() == ()

    montaje.vista.stop()

    assert montaje.vista.in_front_names() is None


def test_sin_quien_reconozca_todos_son_sin_identificar() -> None:
    reloj = _Reloj()
    detector = _Detector(caras=[(SeenFace(0.3, False, False, "marta"),)])
    vista = LocalSight(
        load_engines=lambda: SightEngines(_Camara(), detector),
        clock=reloj,
        install_command=_ORDEN,
    )
    vista.start()
    vista.look()

    assert [cara.who for cara in vista.in_front()] == [None]
    assert vista.in_front_names() == (None,)


# --- Cuando no sabe quién hay, no lo dice (ronda 2 de Codex sobre la PR #703) ----------


def test_si_el_detector_falla_no_dice_a_quien_tiene_delante_y_despues_reconoce_de_nuevo() -> None:
    montaje = _Montaje(_Reconocer(nombres={"marta": "Marta", "pepe": "Pepe"}))
    montaje.ve(("marta", 0.3))
    montaje.detector.falla = RuntimeError("MediaPipe")

    montaje.reloj.ahora += 0.1
    montaje.vista.look()
    assert montaje.vista.in_front_names() is None

    montaje.detector.falla = None
    montaje.ve(("pepe", 0.3))
    assert montaje.vista.in_front_names() == ("Pepe",)
    assert montaje.reconocer.preguntadas == ["marta", "pepe"]


def test_al_abrir_la_camara_hasta_el_primer_fotograma_no_dice_quien_hay() -> None:
    montaje = _Montaje()

    assert montaje.vista.in_front_names() is None
    montaje.ve()
    assert montaje.vista.in_front_names() == ()


def test_mientras_reconoce_una_cara_nueva_no_dice_quien_hay() -> None:
    montaje = _Montaje()
    montaje.ve(("marta", 0.3))
    durante: list[tuple[str | None, ...] | None] = []
    reconoce = montaje.reconocer.who_by_face

    def mirando(crop: str) -> str | None:
        durante.append(montaje.vista.in_front_names())
        return reconoce(crop)

    montaje.reconocer.who_by_face = mirando  # type: ignore[method-assign]
    montaje.ve(("marta", 0.3), ("pepe", 0.7))

    assert durante == [None]
    assert montaje.vista.in_front_names() == ("Marta", None)


# --- Lo que sabe, de una vez y comprobado al leerlo (ronda 3 de Codex sobre la PR #703) --


def test_si_alguien_quita_su_permiso_su_nombre_deja_de_valer_en_el_acto() -> None:
    """Con su cara quieta en su sitio, quitar el permiso no ponía en duda a nadie, y hasta
    volver a reconocer a todos se seguía diciendo su nombre. Lo reconocido con otros
    permisos no vale desde que cambian, sin esperar a que la vista vuelva a mirar."""
    montaje = _Montaje()
    montaje.ve(("marta", 0.3), ("pepe", 0.7))
    assert montaje.vista.in_front_names() == ("Marta", None)

    del montaje.reconocer.nombres["marta"]
    montaje.reconocer.version += 1

    assert montaje.vista.in_front_names() is None
    assert [cara.who for cara in montaje.vista.in_front()] == [None, None]
    montaje.ve(("marta", 0.3), ("pepe", 0.7))
    assert montaje.vista.in_front_names() == (None, None)


def test_si_quita_su_permiso_mientras_se_la_reconoce_su_nombre_no_se_da_por_actual() -> None:
    montaje = _Montaje()
    reconocer = montaje.reconocer
    reconoce = reconocer.who_by_face

    def y_lo_quita(crop: str) -> str | None:
        quien = reconoce(crop)
        reconocer.nombres.pop("marta", None)
        reconocer.version += 1
        return quien

    reconocer.who_by_face = y_lo_quita  # type: ignore[method-assign]
    montaje.ve(("marta", 0.3))

    assert montaje.vista.in_front_names() is None
    assert [cara.who for cara in montaje.vista.in_front()] == [None]


def test_quien_lee_los_nombres_mientras_la_vista_entra_en_duda_no_lee_que_no_hay_nadie() -> None:
    """Si el hilo de la vista entraba en duda entre dos lecturas de quien la lee, este
    juntaba lo de dos momentos, y la duda se leía como que no hay nadie. Lo que sabe se lee
    de una sola vez: lo de antes, o que no lo sabe."""
    detector, reloj = _Detector(), _Reloj()

    class _DudaAlLeerla(LocalSight):
        def in_front(self) -> tuple[Glimpse, ...]:
            # El hilo de la vista, justo ahora: el detector falla.
            detector.falla = RuntimeError("MediaPipe")
            self.look()
            detector.falla = None
            return super().in_front()

    vista = _DudaAlLeerla(
        load_engines=lambda: SightEngines(_Camara(), detector),
        clock=reloj,
        install_command=_ORDEN,
        recognition=_Reconocer(),
    )
    vista.start()
    detector.caras.append((SeenFace(0.3, False, False, "marta"),))
    vista.look()

    assert vista.in_front_names() in (("Marta",), None)


def test_si_vuelve_a_abrir_la_camara_mientras_reconoce_lo_de_antes_no_vale_para_lo_nuevo() -> None:
    montaje = _Montaje(_Reconocer(nombres={"marta": "Marta", "pepe": "Pepe"}))
    reconoce = montaje.reconocer.who_by_face
    reabiertas: list[str] = []

    def reabriendo(crop: str) -> str | None:
        if not reabiertas:
            reabiertas.append(crop)
            montaje.vista.stop()
            montaje.vista.start()
        return reconoce(crop)

    montaje.reconocer.who_by_face = reabriendo  # type: ignore[method-assign]
    montaje.ve(("marta", 0.3))
    assert montaje.vista.in_front_names() is None, "de la vez nueva aún no ha leído nada"

    montaje.ve(("pepe", 0.3))

    assert montaje.vista.in_front_names() == ("Pepe",)
    assert montaje.reconocer.preguntadas == ["marta", "pepe"], "Pepe no hereda el de Marta"
