"""La vista del robot, sin cámara ni MediaPipe: lo que ve, lo que recuerda y adónde mira la
cara (pieza D de la 0.4, ADR-262).

Las pruebas de aceptación (``tests/acceptance/test_robot_0_4_ojos.py``) miran lo que ve
el propietario, con la ventana de verdad. Estas miran los bordes: que sin cámara lo dice y
sigue, que lo que deja de dar imagen la suelta, que un fallo del detector no la para, que
de lo visto solo se recuerdan números y que se olvida a los 30 s; el bucle que la atiende;
y la atención, que decide adónde mira la cara con lo que ve y en qué está el oído.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

import pytest

from sirius.application.attention import AWAY, Attention
from sirius.application.local_listening import VoicePhase
from sirius.application.local_sight import (
    CANNOT_SEE,
    MEMORY_SECONDS,
    NO_CAMERA,
    Glimpse,
    LocalSight,
)
from sirius.application.sight_loop import EVERY_SECONDS, FAILURE_PAUSE_SECONDS, SightLoop
from sirius.ports.local_sight import CameraUnavailable, SeenFace, SightEngines, SightUnavailable

_ORDEN = "uv run --link-mode=copy --extra voz --extra ojos sirius-instala-la-voz"


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 50.0

    def __call__(self) -> float:
        return self.ahora


class _Fotograma:
    """Un fotograma de mentira: solo lo leen la cámara y el detector."""


@dataclass
class _Camara:
    abierta: bool = False
    aperturas: int = 0
    cierres: int = 0
    falla_al_abrir: CameraUnavailable | None = None
    #: Lo que dará cada lectura, en orden; con todo leído, ``None``.
    lecturas: list[_Fotograma | CameraUnavailable | None] = field(default_factory=list)

    def open(self) -> None:
        self.aperturas += 1
        if self.falla_al_abrir is not None:
            raise self.falla_al_abrir
        self.abierta = True

    def read(self) -> _Fotograma | None:
        siguiente = self.lecturas.pop(0) if self.lecturas else _Fotograma()
        if isinstance(siguiente, CameraUnavailable):
            raise siguiente
        return siguiente

    def close(self) -> None:
        self.cierres += 1
        self.abierta = False


@dataclass
class _Detector:
    name: str = "mediapipe"
    #: Las caras de cada fotograma, en orden; sin más, ninguna.
    caras: list[tuple[SeenFace[str], ...] | Exception] = field(default_factory=list)
    vistos: list[_Fotograma] = field(default_factory=list)

    def detect(self, frame: _Fotograma) -> tuple[SeenFace[str], ...]:
        self.vistos.append(frame)
        siguiente = self.caras.pop(0) if self.caras else ()
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


def _cara(x: float, *, habla: bool = False, mira: bool = False) -> SeenFace[str]:
    return SeenFace(x=x, talking=habla, looking=mira, crop="recorte de la cara")


class _Montaje:
    def __init__(self) -> None:
        self.reloj = _Reloj()
        self.camara = _Camara()
        self.detector = _Detector()
        self.cargas = 0
        self.falla_al_cargar: SightUnavailable | None = None
        self.vista = LocalSight(load_engines=self._carga, clock=self.reloj, install_command=_ORDEN)

    def _carga(self) -> SightEngines[_Fotograma, str]:
        self.cargas += 1
        if self.falla_al_cargar is not None:
            raise self.falla_al_cargar
        return SightEngines(self.camara, self.detector)

    def ve(self, *caras: SeenFace[str]) -> None:
        """Mira una vez, con ``caras`` delante."""
        self.detector.caras.append(caras)
        self.vista.look()


# --- Arrancar y soltar ---------------------------------------------------------------


def test_no_carga_nada_hasta_que_empieza_a_ver_y_entonces_abre_la_camara() -> None:
    montaje = _Montaje()
    assert montaje.cargas == 0
    assert not montaje.vista.seeing
    assert montaje.vista.tools == ()

    assert montaje.vista.start() == ""

    assert (montaje.cargas, montaje.camara.aperturas) == (1, 1)
    assert montaje.vista.seeing
    assert montaje.vista.notice == ""
    assert montaje.vista.tools == ("mediapipe",)


def test_empezar_viendo_ya_no_vuelve_a_abrirla_y_tras_soltarla_la_abre_sin_recargar() -> None:
    montaje = _Montaje()
    montaje.vista.start()
    montaje.vista.start()
    assert montaje.camara.aperturas == 1

    montaje.vista.stop()
    assert not montaje.vista.seeing
    assert montaje.camara.cierres == 1
    montaje.vista.start()

    assert (montaje.cargas, montaje.camara.aperturas) == (1, 2)


def test_sin_lo_que_instala_la_orden_dice_por_que_con_la_orden_y_sigue(
    caplog: pytest.LogCaptureFixture,
) -> None:
    montaje = _Montaje()
    montaje.falla_al_cargar = SightUnavailable("falta el modelo de las caras")

    with caplog.at_level(logging.INFO):
        aviso = montaje.vista.start()

    assert aviso == CANNOT_SEE.format(reason="falta el modelo de las caras", command=_ORDEN)
    assert aviso.startswith("No puedo verte: falta el modelo de las caras.")
    assert _ORDEN in aviso and aviso.endswith("Sigo oyéndote y hablando.")
    assert montaje.vista.notice == aviso
    assert not montaje.vista.seeing
    assert "falta el modelo de las caras" in caplog.text


def test_sin_camara_lo_dice_y_sigue_y_la_vuelve_a_buscar_al_volver_a_empezar() -> None:
    montaje = _Montaje()
    montaje.camara.falla_al_abrir = CameraUnavailable("no hay cámara, o la tiene otro programa")

    aviso = montaje.vista.start()

    assert aviso == NO_CAMERA.format(reason="no hay cámara, o la tiene otro programa")
    assert aviso == "Sin cámara: no hay cámara, o la tiene otro programa. Sigo oyéndote y hablando."
    assert not montaje.vista.seeing
    montaje.camara.falla_al_abrir = None
    assert montaje.vista.start() == ""
    assert montaje.vista.seeing and montaje.vista.notice == ""
    assert montaje.cargas == 1


def test_soltarla_sin_haberla_abierto_no_hace_nada() -> None:
    montaje = _Montaje()
    montaje.vista.stop()
    assert montaje.camara.cierres == 0


# --- Mirar ---------------------------------------------------------------------------


def test_sin_ver_mirar_no_lee_la_camara() -> None:
    montaje = _Montaje()
    montaje.ve(_cara(0.5, habla=True))

    assert montaje.detector.vistos == []
    assert montaje.vista.in_front() == ()


def test_de_lo_que_ve_solo_recuerda_donde_esta_si_habla_y_si_le_mira() -> None:
    montaje = _Montaje()
    montaje.vista.start()

    montaje.ve(_cara(0.3, habla=True, mira=True), _cara(0.7))

    assert montaje.vista.in_front() == (Glimpse(0.3, True, True), Glimpse(0.7, False, False))
    recordado = [cara for _, caras in montaje.vista._history for cara in caras]
    assert all(type(cara) is Glimpse for cara in recordado), "un recorte se queda"
    assert not any(isinstance(v, _Fotograma) for v in vars(montaje.vista).values())


def test_si_la_camara_deja_de_dar_imagen_la_suelta_y_lo_dice(
    caplog: pytest.LogCaptureFixture,
) -> None:
    montaje = _Montaje()
    montaje.vista.start()
    montaje.ve(_cara(0.5))
    montaje.camara.lecturas.append(CameraUnavailable("la cámara ha dejado de dar imagen"))

    with caplog.at_level(logging.WARNING):
        montaje.vista.look()

    assert not montaje.vista.seeing
    assert montaje.camara.cierres == 1
    assert montaje.vista.notice == NO_CAMERA.format(reason="la cámara ha dejado de dar imagen")
    assert montaje.vista.in_front() == (), "sin ver, no tiene a nadie delante"
    assert "dejado de dar imagen" in caplog.text


def test_un_fotograma_que_no_llega_no_cuenta() -> None:
    montaje = _Montaje()
    montaje.vista.start()
    montaje.camara.lecturas.append(None)

    montaje.vista.look()

    assert montaje.detector.vistos == []
    assert montaje.vista._history == ()


def test_un_fallo_del_detector_no_la_para_y_se_apunta_una_vez_sin_lo_que_dice(
    caplog: pytest.LogCaptureFixture,
) -> None:
    montaje = _Montaje()
    montaje.vista.start()
    montaje.detector.caras.extend([ValueError("fotograma de Marta raro"), ValueError("otra")])

    with caplog.at_level(logging.ERROR):
        montaje.vista.look()
        montaje.vista.look()
    montaje.ve(_cara(0.5, habla=True))

    errores = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errores) == 1
    assert "ValueError" in errores[0].getMessage()
    assert "Marta" not in caplog.text
    assert montaje.vista.talker_x() == 0.5


def test_olvida_lo_que_vio_hace_mas_de_treinta_segundos() -> None:
    montaje = _Montaje()
    montaje.vista.start()
    montaje.ve(_cara(0.2, habla=True, mira=True))
    empezo = montaje.reloj.ahora

    montaje.reloj.ahora += MEMORY_SECONDS + 0.1
    montaje.ve(_cara(0.8))

    assert MEMORY_SECONDS == 30.0
    assert [momento for momento, _ in montaje.vista._history] == [montaje.reloj.ahora]
    assert not montaje.vista.talker_looked_since(empezo - 1)


# --- Lo que dice de lo visto ---------------------------------------------------------


def test_quien_habla_y_quien_mira_son_los_del_ultimo_fotograma_y_el_mas_al_centro() -> None:
    montaje = _Montaje()
    montaje.vista.start()
    montaje.ve(_cara(0.1, habla=True))
    montaje.ve(_cara(0.2, habla=True), _cara(0.6, habla=True, mira=True), _cara(0.45, mira=True))

    assert montaje.vista.talker_x() == 0.6
    assert montaje.vista.watcher_x() == 0.45
    montaje.ve(_cara(0.3))
    assert montaje.vista.talker_x() is None
    assert montaje.vista.watcher_x() is None


def test_le_hablan_a_el_si_desde_ese_momento_alguien_le_miraba_mientras_hablaba() -> None:
    montaje = _Montaje()
    montaje.vista.start()
    montaje.ve(_cara(0.5, habla=True, mira=True))
    antes = montaje.reloj.ahora
    montaje.reloj.ahora += 2
    desde = montaje.reloj.ahora
    montaje.ve(_cara(0.5, habla=True), _cara(0.3, mira=True))

    assert montaje.vista.talker_looked_since(antes)
    assert not montaje.vista.talker_looked_since(desde), "habla uno y mira otro"
    montaje.ve(_cara(0.5, habla=True, mira=True))
    assert montaje.vista.talker_looked_since(desde)


# --- El bucle que la atiende ---------------------------------------------------------


class _Vista:
    def __init__(self, fallos: int = 0) -> None:
        self.miradas = 0
        self.fallos = fallos
        self.mirado = threading.Event()
        self.dos_veces = threading.Event()

    def look(self) -> None:
        self.miradas += 1
        if self.miradas >= 2:
            self.dos_veces.set()
        self.mirado.set()
        if self.fallos:
            self.fallos -= 1
            raise RuntimeError("fallo de Marta")


def test_el_bucle_mira_unas_diez_veces_por_segundo_en_su_hilo_hasta_que_para() -> None:
    assert EVERY_SECONDS == 0.1
    vista = _Vista()
    bucle = SightLoop(vista, every_seconds=0.001)

    bucle.start()
    assert vista.dos_veces.wait(5)
    assert bucle.running
    bucle.stop()

    assert bucle.wait(5)
    assert not bucle.running


def test_un_fallo_que_se_escapa_no_mata_el_bucle_y_se_apunta_solo_su_tipo(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert FAILURE_PAUSE_SECONDS == 1.0
    vista = _Vista(fallos=1)
    bucle = SightLoop(vista, every_seconds=0.001, failure_pause_seconds=0.001)

    with caplog.at_level(logging.ERROR):
        bucle.start()
        assert vista.dos_veces.wait(5)
        bucle.stop()
        assert bucle.wait(5)

    assert "RuntimeError" in caplog.text
    assert "Marta" not in caplog.text


def test_parar_un_bucle_que_no_ha_empezado_no_espera() -> None:
    bucle = SightLoop(_Vista())
    bucle.stop()
    assert bucle.wait(0.01)


def test_el_hilo_de_la_vista_no_retiene_a_sirius_al_salir() -> None:
    bucle = SightLoop(_Vista())
    assert bucle._thread.daemon
    assert bucle._thread.name == "sirius-vista"


# --- Adónde mira la cara -------------------------------------------------------------


@dataclass
class _Oido:
    phase: VoicePhase = VoicePhase.QUIET


@dataclass
class _Ve:
    habla: float | None = None
    mira: float | None = None

    def talker_x(self) -> float | None:
        return self.habla

    def watcher_x(self) -> float | None:
        return self.mira


def test_oyendo_mira_a_quien_habla() -> None:
    atencion = Attention(_Oido(VoicePhase.HEARING), _Ve(habla=0.25))
    assert atencion.gaze() == (-0.5, 0.0)


@pytest.mark.parametrize(
    ("quien", "lado"),
    [(0.8, -1.0), (0.2, 1.0), (None, 1.0)],
    ids=["le hablo desde la derecha", "le hablo desde la izquierda", "sin ver a nadie"],
)
def test_pensando_aparta_la_vista_arriba_y_al_lado_contrario_de_quien_le_hablo(
    quien: float | None, lado: float
) -> None:
    oido, ve = _Oido(VoicePhase.HEARING), _Ve(habla=quien)
    atencion = Attention(oido, ve)
    atencion.gaze()
    oido.phase, ve.habla = VoicePhase.THINKING, None

    assert atencion.gaze() == (lado * AWAY[0], AWAY[1])
    assert AWAY == (0.55, 0.65)


def test_hablando_mira_a_quien_le_hablo_aunque_ya_no_mueva_la_boca() -> None:
    oido, ve = _Oido(VoicePhase.HEARING), _Ve(habla=0.75)
    atencion = Attention(oido, ve)
    atencion.gaze()
    oido.phase, ve.habla, ve.mira = VoicePhase.SPEAKING, None, 0.1

    assert atencion.gaze() == (0.5, 0.0)


def test_hablando_sin_saber_quien_le_hablo_mira_a_quien_hable_o_le_mire() -> None:
    oido, ve = _Oido(VoicePhase.SPEAKING), _Ve(mira=0.1)
    assert Attention(oido, ve).gaze() == pytest.approx((-0.8, 0.0))


def test_en_nada_mira_a_quien_habla_si_no_a_quien_le_mira_y_si_no_a_su_aire() -> None:
    ve = _Ve(habla=0.5, mira=0.1)
    atencion = Attention(_Oido(), ve)
    assert atencion.gaze() == (0.0, 0.0)
    ve.habla = None
    assert atencion.gaze() == pytest.approx((-0.8, 0.0))
    ve.mira = None
    assert atencion.gaze() is None


def test_lo_que_ve_sin_oirle_no_cambia_a_quien_le_hablo() -> None:
    oido, ve = _Oido(VoicePhase.HEARING), _Ve(habla=0.8)
    atencion = Attention(oido, ve)
    atencion.gaze()
    oido.phase, ve.habla = VoicePhase.QUIET, 0.2
    atencion.gaze()
    oido.phase, ve.habla = VoicePhase.THINKING, None

    assert atencion.gaze() == (-AWAY[0], AWAY[1]), "se fijó en quien habló sin hablarle a él"


def test_sin_vista_aparta_la_vista_al_pensar_y_lo_demas_lo_mira_a_su_aire() -> None:
    oido = _Oido(VoicePhase.THINKING)
    atencion = Attention(oido, None)
    assert atencion.gaze() == (AWAY[0], AWAY[1])
    for fase in (VoicePhase.HEARING, VoicePhase.SPEAKING, VoicePhase.QUIET):
        oido.phase = fase
        assert atencion.gaze() is None


def test_sin_oido_mira_como_en_nada() -> None:
    assert Attention(None, _Ve(habla=0.5)).gaze() == (0.0, 0.0)
    assert Attention(None, None).gaze() is None
