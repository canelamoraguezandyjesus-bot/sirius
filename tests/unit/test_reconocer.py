"""Quién es quién, sin InsightFace ni ECAPA ni base: dar y quitar el permiso, reconocer, y
lo que no puede pasar (pieza E de la 0.4, ADR-263).

Las pruebas de aceptación (``tests/acceptance/test_robot_0_4_reconocer.py``) miran lo que ve
el propietario, con la ventana, la vista y el oído de verdad. Estas miran los bordes: que sin
nadie que diera permiso no saca ninguna huella, los pasos de dar permiso y lo que los
rompe, los umbrales, que la huella de un desconocido no se guarda, que lo que no carga se
dice una vez, y que la ventana no espera a que carguen los reconocedores.
"""

from __future__ import annotations

import logging
import math
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import pytest

from sirius.application.recognition import (
    CANNOT,
    DONE,
    FACE_ALIKE,
    FACE_SAMPLES,
    LONGEST_NAME,
    LOOK_AT_ME,
    NO_FACE_PRINT,
    NO_VOICE_PRINT,
    NOT_SAVED,
    SAY_IT,
    SAY_IT_AGAIN,
    UNKNOWN,
    VOICE_ALIKE,
    EnrollmentStep,
    Recognition,
    describe,
)
from sirius.ports.recognition import (
    Print,
    PrintKind,
    RecognitionEngines,
    RecognitionUnavailable,
    SealedPrint,
)

#: La huella de cada cara y de cada voz de mentira: la cara de un recorte es lo que dice el
#: recorte, y la voz de un turno, lo que suena en él.
_HUELLAS: dict[str, Print] = {
    "marta": (1.0, 0.0, 0.0),
    "pepe": (0.0, 1.0, 0.0),
    "lola": (0.0, 0.0, 1.0),
    # Marta en un fotograma movido: se parece a ella, pero menos que sus otras huellas.
    "marta-movida": (0.6, 0.8, 0.0),
}


def _unidad(*numeros: float) -> Print:
    largo = math.sqrt(sum(n * n for n in numeros))
    return tuple(n / largo for n in numeros)


@dataclass
class _Caras:
    name: str = "insightface"
    dadas: list[Print] = field(default_factory=list)
    falla: Exception | None = None

    def fingerprint(self, crop: str) -> Print:
        if self.falla is not None:
            raise self.falla
        huella = _HUELLAS[crop]
        self.dadas.append(huella)
        return huella


@dataclass
class _Voces:
    name: str = "speechbrain-ecapa"
    dadas: list[Print] = field(default_factory=list)
    falla: Exception | None = None

    def fingerprint(self, chunks: Sequence[str]) -> Print | None:
        if self.falla is not None:
            raise self.falla
        sonado = "".join(chunks)
        if not sonado:
            return None
        huella = _HUELLAS[sonado]
        self.dadas.append(huella)
        return huella


@dataclass
class _Almacen:
    """Las huellas guardadas, en memoria, ya selladas, como las deja la base."""

    filas: list[SealedPrint] = field(default_factory=list)
    lecturas: int = 0
    falla_al_guardar: Exception | None = None
    falla_al_borrar: Exception | None = None
    falla_al_leer: Exception | None = None

    def replace(self, person: str, prints: Sequence[SealedPrint]) -> None:
        if self.falla_al_guardar is not None:
            raise self.falla_al_guardar
        self.filas = [fila for fila in self.filas if fila.person != person] + list(prints)

    def all(self) -> tuple[SealedPrint, ...]:
        self.lecturas += 1
        if self.falla_al_leer is not None:
            raise self.falla_al_leer
        return tuple(self.filas)

    def remove(self, person: str) -> int:
        if self.falla_al_borrar is not None:
            raise self.falla_al_borrar
        antes = len(self.filas)
        self.filas = [fila for fila in self.filas if fila.person != person]
        return antes - len(self.filas)


@dataclass
class _Sellador:
    """Sella cada huella con un número que no dice nada de ella, y se acuerda de cuál era."""

    selladas: dict[bytes, Print] = field(default_factory=dict)
    falla_al_sellar: RecognitionUnavailable | None = None
    ilegibles: set[bytes] = field(default_factory=set)

    def seal(self, numbers: Print) -> bytes:
        if self.falla_al_sellar is not None:
            raise self.falla_al_sellar
        sello = f"sello-{len(self.selladas)}".encode()
        self.selladas[sello] = numbers
        return sello

    def open(self, sealed: bytes) -> Print:
        if sealed in self.ilegibles or sealed not in self.selladas:
            msg = "una huella guardada no se puede leer"
            raise RecognitionUnavailable(msg)
        return self.selladas[sealed]


class _Montaje:
    def __init__(
        self,
        almacen: _Almacen | None = None,
        sellador: _Sellador | None = None,
        carga: Callable[[], RecognitionEngines[str, str]] | None = None,
    ) -> None:
        self.caras = _Caras()
        self.voces = _Voces()
        self.almacen = almacen if almacen is not None else _Almacen()
        self.sellador = sellador if sellador is not None else _Sellador()
        self.cargas = 0
        self.falla_al_cargar: Exception | None = None
        self.reconocer: Recognition[str, str] = Recognition(
            load_engines=carga or self._carga, store=self.almacen, sealer=self.sellador
        )

    def _carga(self) -> RecognitionEngines[str, str]:
        self.cargas += 1
        if self.falla_al_cargar is not None:
            raise self.falla_al_cargar
        return RecognitionEngines(self.caras, self.voces)

    def da_permiso(self, nombre: str, cara: str, voz: str) -> None:
        self.reconocer.begin(nombre)
        for _ in range(FACE_SAMPLES):
            self.reconocer.take_face(cara)
        self.reconocer.take_voice([voz])
        assert self.reconocer.enrollment.step is EnrollmentStep.DONE

    def guardadas(self) -> list[tuple[str, PrintKind, Print]]:
        """Lo guardado, abierto con el sellador: de quién, de qué y qué huella."""
        return [(f.person, f.kind, self.sellador.selladas[f.sealed]) for f in self.almacen.filas]


# --- Sin nadie que diera permiso ------------------------------------------------------


def test_sin_nadie_que_diera_permiso_no_carga_los_reconocedores_ni_saca_huellas() -> None:
    montaje = _Montaje()

    assert montaje.reconocer.who_by_face("pepe") is None
    assert montaje.reconocer.who_by_voice(["pepe"]) is None

    assert not montaje.reconocer.knows_anyone()
    assert montaje.cargas == 0
    assert montaje.caras.dadas == []
    assert montaje.voces.dadas == []
    assert montaje.almacen.filas == []


# --- Dar el permiso -------------------------------------------------------------------


def test_dar_permiso_va_por_pasos_su_nombre_su_cara_y_su_voz(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    montaje = _Montaje()
    reconocer = montaje.reconocer
    version = reconocer.version

    empezado = reconocer.begin("  Marta   Ruiz ")
    assert empezado.step is EnrollmentStep.FACE
    assert empezado.name == "Marta Ruiz"
    assert empezado.notice == LOOK_AT_ME.format(name="Marta Ruiz")
    assert reconocer.wants_face()
    assert not reconocer.wants_voice()

    for _ in range(FACE_SAMPLES - 1):
        reconocer.take_face("marta")
    assert reconocer.wants_face(), "con menos fotogramas, sigue mirando"
    reconocer.take_face("marta")
    assert reconocer.wants_voice()
    assert reconocer.enrollment.notice == SAY_IT.format(name="Marta Ruiz")
    assert montaje.almacen.filas == [], "sin su voz no guarda nada"

    reconocer.take_voice(["marta"])

    assert reconocer.enrollment.step is EnrollmentStep.DONE
    assert reconocer.enrollment.notice == DONE.format(name="Marta Ruiz")
    assert montaje.guardadas() == [
        ("Marta Ruiz", PrintKind.FACE, _HUELLAS["marta"]),
        ("Marta Ruiz", PrintKind.VOICE, _HUELLAS["marta"]),
    ]
    assert all(fila.sealed.startswith(b"sello-") for fila in montaje.almacen.filas), (
        "se guardan selladas, no los números"
    )
    assert reconocer.people() == ("Marta Ruiz",)
    assert reconocer.knows_anyone()
    assert reconocer.version > version
    texto = caplog.text
    assert "Marta" not in texto, "el diario no lleva su nombre"
    assert "1.0" not in texto and "0.0" not in texto, "el diario no lleva sus huellas"


def test_de_su_cara_se_queda_la_huella_que_mas_se_parece_a_las_demas() -> None:
    montaje = _Montaje()
    reconocer = montaje.reconocer
    reconocer.begin("Marta")

    for cara in ("marta-movida", "marta", "marta", "marta", "marta"):
        reconocer.take_face(cara)
    reconocer.take_voice(["marta"])

    assert FACE_SAMPLES == 5
    [cara_guardada] = [h for _, tipo, h in montaje.guardadas() if tipo is PrintKind.FACE]
    assert cara_guardada == _HUELLAS["marta"]


def test_una_voz_sin_bastante_voz_pide_repetirla_y_no_guarda_nada() -> None:
    montaje = _Montaje()
    reconocer = montaje.reconocer
    reconocer.begin("Marta")
    for _ in range(FACE_SAMPLES):
        reconocer.take_face("marta")

    reconocer.take_voice([""])

    assert reconocer.wants_voice()
    assert reconocer.enrollment.notice == SAY_IT_AGAIN.format(name="Marta")
    assert montaje.almacen.filas == []
    reconocer.take_voice(["marta"])
    assert reconocer.enrollment.step is EnrollmentStep.DONE


def test_un_nombre_vacio_o_muy_largo_no_empieza_nada() -> None:
    reconocer = _Montaje().reconocer

    assert reconocer.begin("   ").step is EnrollmentStep.IDLE
    assert reconocer.begin("x" * (LONGEST_NAME + 1)).step is EnrollmentStep.IDLE
    assert reconocer.begin("x" * LONGEST_NAME).step is EnrollmentStep.FACE


def test_lo_que_llega_fuera_de_su_paso_no_cuenta() -> None:
    montaje = _Montaje()
    reconocer = montaje.reconocer

    reconocer.take_face("marta")
    reconocer.take_voice(["marta"])
    assert reconocer.enrollment.step is EnrollmentStep.IDLE

    reconocer.begin("Marta")
    reconocer.take_voice(["marta"])
    assert reconocer.wants_face(), "la voz antes de la cara no cuenta"
    assert montaje.almacen.filas == []
    assert montaje.voces.dadas == []


def test_cancelar_no_guarda_nada_y_lo_que_llega_despues_no_cuenta() -> None:
    montaje = _Montaje()
    reconocer = montaje.reconocer
    reconocer.begin("Marta")
    for _ in range(FACE_SAMPLES):
        reconocer.take_face("marta")

    reconocer.cancel()
    reconocer.take_voice(["marta"])

    assert reconocer.enrollment.step is EnrollmentStep.IDLE
    assert montaje.almacen.filas == []
    assert reconocer.people() == ()


def test_cancelar_mientras_se_saca_la_huella_de_su_voz_no_guarda_nada() -> None:
    """La ventana cancela mientras el oído saca la huella de la voz, que tarda: lo que
    llega después no guarda nada, ni deja el permiso dado."""
    montaje = _Montaje()
    reconocer = montaje.reconocer
    reconocer.begin("Marta")
    for _ in range(FACE_SAMPLES):
        reconocer.take_face("marta")
    original = montaje.voces.fingerprint

    def mientras_cancela(chunks: Sequence[str]) -> Print | None:
        reconocer.cancel()
        return original(chunks)

    montaje.voces.fingerprint = mientras_cancela  # type: ignore[method-assign]

    reconocer.take_voice(["marta"])

    assert montaje.almacen.filas == []
    assert reconocer.enrollment.step is EnrollmentStep.IDLE
    assert not reconocer.knows_anyone()


def test_empezar_otra_vez_olvida_las_caras_del_permiso_de_antes() -> None:
    montaje = _Montaje()
    reconocer = montaje.reconocer
    reconocer.begin("Marta")
    for _ in range(FACE_SAMPLES - 1):
        reconocer.take_face("marta")

    reconocer.begin("Pepe")
    reconocer.take_face("pepe")

    assert reconocer.wants_face(), "una cara de Pepe no completa las de Marta"


def test_dar_permiso_otra_vez_cambia_sus_huellas_por_las_nuevas() -> None:
    montaje = _Montaje()
    montaje.da_permiso("Marta", "marta", "marta")

    montaje.da_permiso("Marta", "lola", "lola")

    assert montaje.guardadas() == [
        ("Marta", PrintKind.FACE, _HUELLAS["lola"]),
        ("Marta", PrintKind.VOICE, _HUELLAS["lola"]),
    ]
    assert montaje.reconocer.who_by_face("lola") == "Marta"
    assert montaje.reconocer.who_by_face("marta") is None


# --- Reconocer ------------------------------------------------------------------------


def test_reconoce_por_la_cara_y_por_la_voz_a_quien_dio_permiso_y_a_nadie_mas() -> None:
    montaje = _Montaje()
    montaje.da_permiso("Marta", "marta", "marta")
    reconocer = montaje.reconocer

    assert reconocer.who_by_face("marta") == "Marta"
    assert reconocer.who_by_voice(["marta"]) == "Marta"
    assert reconocer.who_by_face("pepe") is None
    assert reconocer.who_by_voice(["pepe"]) is None
    assert reconocer.who_by_voice([""]) is None, "sin bastante voz, nadie"


def test_la_huella_de_un_desconocido_se_compara_y_no_se_guarda() -> None:
    montaje = _Montaje()
    montaje.da_permiso("Marta", "marta", "marta")
    guardadas = list(montaje.almacen.filas)
    selladas = dict(montaje.sellador.selladas)

    montaje.reconocer.who_by_face("pepe")
    montaje.reconocer.who_by_voice(["pepe"])

    assert _HUELLAS["pepe"] in montaje.caras.dadas
    assert _HUELLAS["pepe"] in montaje.voces.dadas
    assert montaje.almacen.filas == guardadas
    assert montaje.sellador.selladas == selladas, "ni siquiera se sella"


@pytest.mark.parametrize(
    ("de_que", "umbral"), [(PrintKind.FACE, FACE_ALIKE), (PrintKind.VOICE, VOICE_ALIKE)]
)
def test_parecerse_lo_que_pide_basta_y_un_poco_menos_no(de_que: PrintKind, umbral: float) -> None:
    montaje = _Montaje()
    montaje.da_permiso("Marta", "marta", "marta")
    justo = (umbral, math.sqrt(1 - umbral * umbral), 0.0)
    menos = _unidad(umbral - 0.01, math.sqrt(1 - umbral * umbral), 0.0)
    _HUELLAS["justo"], _HUELLAS["menos"] = justo, menos
    try:
        if de_que is PrintKind.FACE:
            assert montaje.reconocer.who_by_face("justo") == "Marta"
            assert montaje.reconocer.who_by_face("menos") is None
        else:
            assert montaje.reconocer.who_by_voice(["justo"]) == "Marta"
            assert montaje.reconocer.who_by_voice(["menos"]) is None
    finally:
        del _HUELLAS["justo"], _HUELLAS["menos"]


def test_entre_dos_que_se_parecen_gana_el_que_mas_y_la_cara_no_se_compara_con_voces() -> None:
    montaje = _Montaje()
    montaje.da_permiso("Marta", "marta", "pepe")
    montaje.da_permiso("Pepe", "pepe", "marta")
    _HUELLAS["entre"] = _unidad(0.6, 0.8, 0.0)
    try:
        assert montaje.reconocer.who_by_face("entre") == "Pepe"
        assert montaje.reconocer.who_by_voice(["entre"]) == "Marta"
    finally:
        del _HUELLAS["entre"]


def test_al_volver_a_abrir_lee_las_huellas_guardadas_y_le_reconoce() -> None:
    antes = _Montaje()
    antes.da_permiso("Marta", "marta", "marta")

    despues = _Montaje(almacen=antes.almacen, sellador=antes.sellador)

    assert despues.reconocer.people() == ("Marta",)
    assert despues.reconocer.who_by_face("marta") == "Marta"
    assert despues.reconocer.who_by_voice(["marta"]) == "Marta"


# --- Quitar el permiso ----------------------------------------------------------------


def test_quitar_el_permiso_borra_sus_huellas_y_deja_de_reconocerle() -> None:
    montaje = _Montaje()
    montaje.da_permiso("Marta", "marta", "marta")
    montaje.da_permiso("Pepe", "pepe", "pepe")
    version = montaje.reconocer.version

    assert montaje.reconocer.forget("Marta")

    assert [persona for persona, _, _ in montaje.guardadas()] == ["Pepe", "Pepe"]
    assert montaje.reconocer.who_by_face("marta") is None
    assert montaje.reconocer.who_by_voice(["marta"]) is None
    assert montaje.reconocer.who_by_face("pepe") == "Pepe"
    assert montaje.reconocer.people() == ("Pepe",)
    assert montaje.reconocer.version > version


def test_si_no_se_pueden_borrar_lo_dice_y_no_cambia_nada() -> None:
    montaje = _Montaje()
    montaje.da_permiso("Marta", "marta", "marta")
    montaje.almacen.falla_al_borrar = RuntimeError("la base está ocupada")
    version = montaje.reconocer.version

    assert not montaje.reconocer.forget("Marta")

    assert montaje.reconocer.who_by_face("marta") == "Marta"
    assert montaje.reconocer.people() == ("Marta",)
    assert montaje.reconocer.version == version


def test_las_huellas_que_no_se_pueden_leer_no_reconocen_pero_se_pueden_borrar(
    caplog: pytest.LogCaptureFixture,
) -> None:
    antes = _Montaje()
    antes.da_permiso("Marta", "marta", "marta")
    sellador = _Sellador(selladas=dict(antes.sellador.selladas))
    sellador.ilegibles = {fila.sealed for fila in antes.almacen.filas}

    despues = _Montaje(almacen=antes.almacen, sellador=sellador)

    assert despues.reconocer.people() == ("Marta",), "la lista para olvidar la enseña"
    assert not despues.reconocer.knows_anyone()
    assert despues.reconocer.who_by_face("marta") is None
    assert "Hay 2 huellas guardadas que no se pueden leer" in caplog.text
    assert despues.reconocer.forget("Marta")
    assert despues.almacen.filas == []
    assert despues.reconocer.people() == ()


def test_si_la_base_no_se_puede_leer_no_reconoce_a_nadie_y_no_lo_vuelve_a_intentar(
    caplog: pytest.LogCaptureFixture,
) -> None:
    montaje = _Montaje(almacen=_Almacen(falla_al_leer=RuntimeError("disco roto, /ruta/secreta")))

    assert not montaje.reconocer.knows_anyone()
    assert montaje.reconocer.people() == ()
    assert montaje.reconocer.who_by_face("marta") is None

    assert montaje.almacen.lecturas == 1
    assert "RuntimeError" in caplog.text
    assert "/ruta/secreta" not in caplog.text, "del fallo, solo su tipo"


# --- Lo que no carga o falla ----------------------------------------------------------


def test_si_no_cargan_los_reconocedores_lo_dice_al_dar_permiso_y_no_lo_vuelve_a_intentar() -> None:
    montaje = _Montaje()
    motivo = "falta el modelo de reconocer caras"
    montaje.falla_al_cargar = RecognitionUnavailable(motivo)
    reconocer = montaje.reconocer
    reconocer.begin("Marta")

    reconocer.take_face("marta")

    assert reconocer.enrollment.step is EnrollmentStep.FAILED
    assert reconocer.enrollment.notice == CANNOT.format(reason=motivo)
    assert reconocer.unavailable == motivo
    otra_vez = reconocer.begin("Marta")
    assert otra_vez.step is EnrollmentStep.FAILED, "lo dice en el acto, sin mirarle"
    assert otra_vez.notice == CANNOT.format(reason=motivo)
    assert montaje.cargas == 1
    assert montaje.almacen.filas == []


def test_un_fallo_que_no_se_espera_al_cargar_tambien_se_dice_y_no_se_reintenta() -> None:
    montaje = _Montaje()
    montaje.falla_al_cargar = RuntimeError("una DLL")
    reconocer = montaje.reconocer
    reconocer.begin("Marta")

    reconocer.take_face("marta")
    reconocer.take_face("marta")

    assert reconocer.enrollment.notice == CANNOT.format(
        reason="los modelos de reconocer no cargan (una DLL)"
    )
    assert montaje.cargas == 1


def test_sin_poder_cargar_quien_dio_permiso_antes_es_sin_identificar() -> None:
    antes = _Montaje()
    antes.da_permiso("Marta", "marta", "marta")
    despues = _Montaje(almacen=antes.almacen, sellador=antes.sellador)
    despues.falla_al_cargar = RecognitionUnavailable("falta el modelo de reconocer voces")

    assert despues.reconocer.who_by_face("marta") is None
    assert despues.reconocer.who_by_voice(["marta"]) is None
    assert despues.cargas == 1


@pytest.mark.parametrize("de_que", ["cara", "voz"])
def test_si_falla_sacar_una_huella_al_dar_permiso_lo_dice_con_el_tipo_en_el_diario(
    de_que: str, caplog: pytest.LogCaptureFixture
) -> None:
    montaje = _Montaje()
    reconocer = montaje.reconocer
    reconocer.begin("Marta")
    if de_que == "cara":
        montaje.caras.falla = ValueError("tensor raro en /ruta/secreta")
        reconocer.take_face("marta")
        motivo = NO_FACE_PRINT
    else:
        for _ in range(FACE_SAMPLES):
            reconocer.take_face("marta")
        montaje.voces.falla = ValueError("tensor raro en /ruta/secreta")
        reconocer.take_voice(["marta"])
        motivo = NO_VOICE_PRINT

    assert reconocer.enrollment.step is EnrollmentStep.FAILED
    assert reconocer.enrollment.notice == CANNOT.format(reason=motivo)
    assert "ValueError" in caplog.text
    assert "/ruta/secreta" not in caplog.text
    assert montaje.almacen.filas == []


def test_sin_almacen_seguro_para_la_llave_no_guarda_nada_y_lo_dice() -> None:
    motivo = "este ordenador no tiene un almacén seguro para la llave de las huellas"
    montaje = _Montaje(sellador=_Sellador(falla_al_sellar=RecognitionUnavailable(motivo)))

    montaje.reconocer.begin("Marta")
    for _ in range(FACE_SAMPLES):
        montaje.reconocer.take_face("marta")
    montaje.reconocer.take_voice(["marta"])

    assert montaje.reconocer.enrollment.notice == CANNOT.format(reason=motivo)
    assert montaje.almacen.filas == []
    assert not montaje.reconocer.knows_anyone()


def test_si_no_se_pueden_guardar_lo_dice_y_no_le_reconoce() -> None:
    montaje = _Montaje(almacen=_Almacen(falla_al_guardar=RuntimeError("base llena")))

    montaje.reconocer.begin("Marta")
    for _ in range(FACE_SAMPLES):
        montaje.reconocer.take_face("marta")
    montaje.reconocer.take_voice(["marta"])

    assert montaje.reconocer.enrollment.step is EnrollmentStep.FAILED
    assert montaje.reconocer.enrollment.notice == CANNOT.format(reason=NOT_SAVED)
    assert montaje.reconocer.people() == ()
    assert montaje.reconocer.who_by_face("marta") is None


# --- Los hilos ------------------------------------------------------------------------


def test_la_ventana_lee_y_cambia_el_permiso_mientras_cargan_los_reconocedores() -> None:
    """Cargar InsightFace y ECAPA tarda segundos, en el hilo de la vista; la ventana mira el
    permiso dos veces por segundo y no puede esperar a que acaben."""
    soltar = threading.Event()
    cargando = threading.Event()
    montaje: _Montaje

    def carga_lenta() -> RecognitionEngines[str, str]:
        cargando.set()
        assert soltar.wait(10)
        return RecognitionEngines(montaje.caras, montaje.voces)

    montaje = _Montaje(carga=carga_lenta)
    reconocer = montaje.reconocer
    reconocer.begin("Marta")
    vista = threading.Thread(target=reconocer.take_face, args=("marta",), daemon=True)
    vista.start()
    assert cargando.wait(5)
    hechas: list[str] = []

    def ventana() -> None:
        reconocer.people()
        reconocer.knows_anyone()
        reconocer.cancel()
        reconocer.begin("Pepe")
        reconocer.forget("Lola")
        hechas.append("todo")

    hilo = threading.Thread(target=ventana, daemon=True)
    hilo.start()
    hilo.join(5)
    # Lo que hizo la ventana mientras aún cargaban: después ya no vale, que soltarlos la
    # dejaría acabar.
    a_tiempo = list(hechas)
    soltar.set()
    vista.join(5)
    hilo.join(5)

    assert a_tiempo == ["todo"], "la ventana se ha quedado esperando a los reconocedores"
    assert reconocer.enrollment.name == "Pepe", "la cara de antes de cancelar no cuenta"
    assert reconocer.wants_face()


def test_describe_dice_el_nombre_o_sin_identificar() -> None:
    assert describe("Marta") == "Marta"
    assert describe(None) == UNKNOWN == "sin identificar"
