"""Lo que recuerda haber visto, como texto (pieza G de la 0.4, ADR-265): quién llega, quién
se va y quién estaba, con su hora; lo que se le dice al modelo; y quien quita su permiso,
que deja de tener nombre."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

from sirius.application.local_sight import LocalSight
from sirius.application.sight_log import (
    ARRIVE_SECONDS,
    HEADING,
    INTRO,
    LEAVE_SECONDS,
    MOST_LINES,
    REMEMBER,
    TIDY_EVERY,
    SightLog,
    sight_block,
)
from sirius.ports.local_sight import CameraUnavailable, SeenFace, SightEngines
from sirius.ports.sight_log import Change, SeenChange

_ORDEN = "uv run --link-mode=copy --extra voz --extra ojos sirius-instala-la-voz"
#: Las seis de la tarde de un día cualquiera, en la hora de este ordenador.
_SEIS = datetime(2026, 10, 19, 18, 0).astimezone()


@dataclass
class _Almacen:
    """Dónde se apunta, de mentira: en una lista, y apunta lo que le piden."""

    apuntado: list[SeenChange] = field(default_factory=list)
    olvidados: list[str] = field(default_factory=list)
    borrados_antes_de: list[datetime] = field(default_factory=list)
    falla: Exception | None = None
    falla_al_olvidar: Exception | None = None
    falla_al_borrar: Exception | None = None

    def add(self, changes: Sequence[SeenChange]) -> None:
        if self.falla is not None:
            raise self.falla
        self.apuntado.extend(changes)

    def since(self, moment: datetime) -> tuple[SeenChange, ...]:
        return tuple(sorted((c for c in self.apuntado if c.at >= moment), key=lambda c: c.at))

    def drop_before(self, moment: datetime) -> int:
        if self.falla_al_borrar is not None:
            raise self.falla_al_borrar
        self.borrados_antes_de.append(moment)
        antes = len(self.apuntado)
        self.apuntado = [c for c in self.apuntado if c.at >= moment]
        return antes - len(self.apuntado)

    def forget(self, who: str) -> int:
        if self.falla_al_olvidar is not None:
            raise self.falla_al_olvidar
        self.olvidados.append(who)
        cambiados = [c for c in self.apuntado if c.who == who]
        self.apuntado = [
            SeenChange(c.at, c.change, None) if c.who == who else c for c in self.apuntado
        ]
        return len(cambiados)


class _Reloj:
    """El de la vista, en segundos, y el de pared, que avanza con él."""

    def __init__(self) -> None:
        self.ahora = 100.0
        self.pared = _SEIS

    def __call__(self) -> float:
        return self.ahora

    def hora(self) -> datetime:
        return self.pared.astimezone(UTC)

    def avanza(self, segundos: float) -> None:
        self.ahora += segundos
        self.pared += timedelta(seconds=segundos)


class _Montaje:
    def __init__(self, permiso: Sequence[str] = ("Marta", "Pepe")) -> None:
        self.reloj = _Reloj()
        self.almacen = _Almacen()
        self.permiso = list(permiso)
        self.log = SightLog(self.almacen, allowed=lambda: self.permiso, wall_clock=self.reloj.hora)

    def ve(self, *nombres: str | None, durante: float = 0.0, cada: float = 0.1) -> None:
        """Ve ``nombres`` en un fotograma y, si se dice, durante ``durante`` segundos más."""
        self.log.see(self.reloj.ahora, nombres)
        for _ in range(round(durante / cada)):
            self.reloj.avanza(cada)
            self.log.see(self.reloj.ahora, nombres)

    def apuntado(self) -> list[tuple[str, Change, str | None]]:
        return [(f"{c.at.astimezone():%H:%M:%S}", c.change, c.who) for c in self.almacen.apuntado]


@pytest.fixture
def en_tokio(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Este ordenador, con la hora de Tokio, nueve horas por delante de UTC y sin cambio de
    hora: así se ve si algo confunde la hora de este ordenador con UTC."""
    if not hasattr(time, "tzset"):
        pytest.skip("cambiar la zona horaria del proceso necesita time.tzset")
    monkeypatch.setenv("TZ", "Asia/Tokyo")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def _con_lo_primero(montaje: _Montaje, *nombres: str | None) -> None:
    """Lo primero que ve, dado por hecho, y lo apuntado olvidado: desde ahí, los cambios."""
    montaje.ve(*nombres, durante=ARRIVE_SECONDS + 0.1)
    montaje.almacen.apuntado.clear()


# --- Lo primero que ve ------------------------------------------------------------------


def test_lo_primero_que_ve_se_apunta_como_quien_ya_estaba_cuando_lleva_un_rato_igual() -> None:
    montaje = _Montaje()

    montaje.ve("Marta", None, durante=ARRIVE_SECONDS - 0.2)
    assert montaje.apuntado() == [], "aún no lleva un rato igual"
    montaje.ve("Marta", None, durante=0.3)

    assert montaje.apuntado() == [
        ("18:00:00", Change.THERE, "Marta"),
        ("18:00:00", Change.THERE, None),
    ]


def test_si_cambia_antes_de_dar_lo_primero_por_hecho_se_empieza_a_contar_otra_vez() -> None:
    montaje = _Montaje()

    montaje.ve("Marta", durante=ARRIVE_SECONDS - 1)
    montaje.ve("Marta", "Pepe", durante=ARRIVE_SECONDS - 1)
    assert montaje.apuntado() == []
    montaje.ve("Marta", "Pepe", durante=1.5)

    assert [cambio[1:] for cambio in montaje.apuntado()] == [
        (Change.THERE, "Marta"),
        (Change.THERE, "Pepe"),
    ]
    assert montaje.apuntado()[0][0] == "18:00:02", "desde que se ve igual"


def test_sin_nadie_delante_no_se_apunta_nada() -> None:
    montaje = _Montaje()

    montaje.ve(durante=60.0)

    assert montaje.apuntado() == []


# --- Quién llega y quién se va -----------------------------------------------------------


def test_alguien_llega_cuando_se_le_ve_un_rato_seguido_a_la_hora_en_que_se_le_vio() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, None)
    montaje.reloj.avanza(60.0)

    montaje.ve(None, "Marta", durante=ARRIVE_SECONDS - 0.2)
    assert montaje.apuntado() == [], "aún no ha llegado"
    montaje.ve(None, "Marta", durante=0.3)

    assert montaje.apuntado() == [("18:01:03", Change.CAME, "Marta")]


def test_quien_pasa_un_momento_o_se_pierde_un_fotograma_al_llegar_no_llega_aun() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, None)

    montaje.ve(None, "Marta", durante=ARRIVE_SECONDS - 0.5)
    montaje.ve(None)
    montaje.ve(None, "Marta", durante=ARRIVE_SECONDS - 0.5)

    assert montaje.apuntado() == []


def test_alguien_se_va_cuando_lleva_un_rato_sin_vérsele_a_la_hora_en_que_dejó_de_vérsele() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, None, "Marta")
    montaje.reloj.avanza(60.0)

    montaje.ve(None, durante=LEAVE_SECONDS - 0.2)
    assert montaje.apuntado() == [], "aún no se ha ido"
    montaje.ve(None, durante=0.3)

    assert montaje.apuntado() == [("18:01:03", Change.LEFT, "Marta")]


def test_quien_se_gira_un_momento_no_se_va() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, "Marta")

    montaje.ve(durante=LEAVE_SECONDS - 1)
    montaje.ve("Marta", durante=1.0)
    montaje.ve(durante=LEAVE_SECONDS - 1)

    assert montaje.apuntado() == []


def test_de_los_desconocidos_se_cuenta_cuantos_llegan_y_cuantos_se_van() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, None)

    montaje.ve(None, None, None, durante=0.5)
    montaje.ve(None, None, None, durante=ARRIVE_SECONDS)
    assert [cambio[1:] for cambio in montaje.apuntado()] == [(Change.CAME, None)] * 2

    montaje.almacen.apuntado.clear()
    montaje.ve(None, None, durante=LEAVE_SECONDS + 0.2)
    assert [cambio[1:] for cambio in montaje.apuntado()] == [(Change.LEFT, None)]


def test_un_desconocido_que_se_pierde_un_fotograma_al_llegar_llega_desde_que_vuelve() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, None)

    montaje.ve(None, None, durante=ARRIVE_SECONDS - 0.5)
    montaje.reloj.avanza(0.1)
    montaje.ve(None)
    montaje.reloj.avanza(0.1)
    vuelve = f"{montaje.reloj.pared:%H:%M:%S}"
    montaje.ve(None, None, durante=ARRIVE_SECONDS + 0.2)

    assert montaje.apuntado() == [(vuelve, Change.CAME, None)]


def test_de_dos_desconocidos_que_se_pierden_un_momento_se_va_solo_el_que_no_vuelve() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, None, None)

    montaje.reloj.avanza(0.1)
    montaje.ve()
    montaje.reloj.avanza(0.1)
    montaje.ve(None, durante=LEAVE_SECONDS + 0.2)

    assert [cambio[1:] for cambio in montaje.apuntado()] == [(Change.LEFT, None)]


def test_cuenta_lo_que_se_ve_seguido_y_no_un_fotograma_de_mas() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, None)

    montaje.ve(None, None, None)
    montaje.ve(None, None, durante=ARRIVE_SECONDS + 0.2)

    assert [cambio[1:] for cambio in montaje.apuntado()] == [(Change.CAME, None)], (
        "llegó uno: el tercero solo se vio un fotograma"
    )


# --- Al dejar de ver ---------------------------------------------------------------------


def test_al_dejar_de_ver_no_se_sabe_quien_se_va_y_al_volver_se_empieza_de_nuevo() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, "Marta")

    montaje.log.pause()
    montaje.reloj.avanza(60.0)
    montaje.ve("Pepe", durante=ARRIVE_SECONDS + 0.2)

    assert [cambio[1:] for cambio in montaje.apuntado()] == [(Change.THERE, "Pepe")], (
        "ni se fue Marta ni vino Pepe: es lo primero que ve al volver"
    )


# --- Quien quita su permiso ----------------------------------------------------------------


def test_quien_quita_su_permiso_pasa_a_ser_alguien_sin_identificar_sin_irse() -> None:
    montaje = _Montaje()
    montaje.ve("Marta", durante=ARRIVE_SECONDS + 0.2)

    montaje.log.forget("Marta")
    montaje.ve(None, durante=LEAVE_SECONDS * 2)

    assert montaje.almacen.olvidados == ["Marta"]
    assert [cambio[1:] for cambio in montaje.apuntado()] == [(Change.THERE, None)], (
        "su nombre se ha quitado de lo apuntado, y no se apunta que se fue"
    )


def test_un_fotograma_que_aun_la_nombraba_tras_quitar_el_permiso_no_la_hace_llegar() -> None:
    """La vista pudo reconocerla justo antes de quitar el permiso y decirlo justo después:
    lo que llevaba llegando se olvida con el permiso."""
    montaje = _Montaje()
    _con_lo_primero(montaje, None)
    montaje.ve(None, "Marta", durante=ARRIVE_SECONDS - 0.5)

    montaje.log.forget("Marta")
    montaje.reloj.avanza(0.6)
    montaje.ve(None, "Marta")

    assert all(cambio[2] != "Marta" for cambio in montaje.apuntado())


def test_un_cambio_suyo_a_medias_tampoco_se_apunta_con_su_nombre() -> None:
    montaje = _Montaje()
    _con_lo_primero(montaje, None)
    montaje.ve(None, "Marta", durante=ARRIVE_SECONDS - 1)

    montaje.log.forget("Marta")
    montaje.ve(None, None, durante=ARRIVE_SECONDS + 0.2)

    assert all(cambio[2] is None for cambio in montaje.apuntado())


# --- Lo que se le dice al modelo ---------------------------------------------------------


def test_se_le_dice_cada_cambio_con_su_hora() -> None:
    montaje = _Montaje()
    montaje.ve(None, durante=ARRIVE_SECONDS + 0.2)
    montaje.reloj.avanza(120.0)
    montaje.ve(None, "Marta", durante=ARRIVE_SECONDS + 0.2)
    montaje.reloj.avanza(600.0)
    montaje.ve(None, durante=LEAVE_SECONDS + 0.2)

    assert montaje.log.lines() == (
        "A las 18:00, al abrir los ojos, estaba delante alguien sin identificar.",
        "A las 18:02 vino Marta.",
        "A las 18:12 se fue Marta.",
    )
    assert sight_block(montaje.log.lines()).splitlines()[:2] == [HEADING, INTRO]
    assert sight_block(()) == ""


@pytest.mark.usefixtures("en_tokio")
def test_la_hora_que_se_le_dice_es_la_de_este_ordenador() -> None:
    montaje = _Montaje()
    montaje.reloj.pared = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
    montaje.almacen.apuntado = [SeenChange(montaje.reloj.hora(), Change.CAME, "Marta")]

    assert montaje.log.lines() == ("A las 18:00 vino Marta.",)


def test_lo_de_ayer_se_dice_que_fue_ayer_y_lo_de_hace_mas_de_un_dia_no_se_dice() -> None:
    montaje = _Montaje()
    hoy = montaje.reloj.hora()
    montaje.almacen.apuntado = [
        SeenChange(hoy - REMEMBER - timedelta(minutes=1), Change.CAME, "Pepe"),
        SeenChange(hoy - timedelta(hours=19), Change.CAME, "Marta"),
        SeenChange(hoy, Change.LEFT, "Marta"),
    ]

    assert montaje.log.lines() == ("Ayer, a las 23:00 vino Marta.", "A las 18:00 se fue Marta.")


def test_se_le_dicen_como_mucho_los_cambios_mas_nuevos() -> None:
    montaje = _Montaje()
    hoy = montaje.reloj.hora()
    montaje.almacen.apuntado = [
        SeenChange(hoy - timedelta(minutes=minuto), Change.CAME, None)
        for minuto in range(MOST_LINES + 5, 0, -1)
    ]

    lineas = montaje.log.lines()

    assert len(lineas) == MOST_LINES
    assert lineas[-1] == "A las 17:59 vino alguien sin identificar."


def test_el_nombre_de_quien_ya_no_tiene_permiso_no_se_dice_y_se_quita(
    caplog: pytest.LogCaptureFixture,
) -> None:
    montaje = _Montaje(permiso=("Marta",))
    hoy = montaje.reloj.hora()
    montaje.almacen.apuntado = [
        SeenChange(hoy, Change.CAME, "Pepe"),
        SeenChange(hoy, Change.CAME, "Marta"),
    ]

    assert montaje.log.lines() == (
        "A las 18:00 vino alguien sin identificar.",
        "A las 18:00 vino Marta.",
    )
    assert montaje.almacen.olvidados == ["Pepe"]

    montaje.almacen.apuntado[0] = SeenChange(hoy, Change.CAME, "Pepe")
    montaje.almacen.falla_al_olvidar = OSError("la base, ocupada")
    with caplog.at_level(logging.ERROR):
        assert montaje.log.lines()[0] == "A las 18:00 vino alguien sin identificar.", (
            "aunque no se haya podido quitar"
        )
    assert "No se pudo quitar un nombre de lo que ha visto (OSError)" in caplog.text


# --- Apuntar ---------------------------------------------------------------------------


def test_al_apuntar_se_borra_lo_de_hace_mas_de_un_dia() -> None:
    montaje = _Montaje()

    montaje.ve(None)
    montaje.reloj.avanza(ARRIVE_SECONDS)
    montaje.ve(None)

    assert montaje.almacen.apuntado, "lo primero que ve, apuntado en este fotograma"
    assert montaje.almacen.borrados_antes_de == [montaje.reloj.hora() - REMEMBER]


def test_al_leerlo_tambien_se_borra_lo_de_hace_mas_de_un_dia_aunque_no_cambie_nada() -> None:
    montaje = _Montaje()
    hace_un_rato = montaje.reloj.hora() - timedelta(hours=1)
    montaje.almacen.apuntado = [
        SeenChange(montaje.reloj.hora() - REMEMBER - timedelta(minutes=1), Change.CAME, "Marta"),
        SeenChange(hace_un_rato, Change.CAME, "Pepe"),
    ]

    lineas = montaje.log.lines()

    assert [c.who for c in montaje.almacen.apuntado] == ["Pepe"], "lo de ayer ya no está"
    assert len(lineas) == 1


def test_lo_de_hace_mas_de_un_dia_se_borra_cada_minuto_aunque_no_cambie_nada_ni_se_lea() -> None:
    # Ronda 1 de Codex sobre la PR #703: sin cambios delante y sin charla, se va igual.
    montaje = _Montaje()
    montaje.almacen.apuntado = [
        SeenChange(montaje.reloj.hora() - REMEMBER - timedelta(minutes=1), Change.CAME, "Marta")
    ]

    montaje.log.tidy()
    assert montaje.almacen.apuntado == []
    assert montaje.almacen.borrados_antes_de == [montaje.reloj.hora() - REMEMBER]

    montaje.reloj.avanza(TIDY_EVERY.total_seconds() - 1)
    montaje.log.tidy()
    assert len(montaje.almacen.borrados_antes_de) == 1, "como mucho cada minuto"

    montaje.reloj.avanza(1)
    montaje.log.tidy()
    assert len(montaje.almacen.borrados_antes_de) == 2


def test_si_la_hora_del_ordenador_vuelve_atras_se_borra_igual() -> None:
    montaje = _Montaje()
    montaje.log.tidy()
    montaje.reloj.pared -= timedelta(hours=1)

    montaje.log.tidy()

    assert len(montaje.almacen.borrados_antes_de) == 2


def test_un_fallo_al_borrar_lo_viejo_se_dice_una_vez_y_se_lee_igual(
    caplog: pytest.LogCaptureFixture,
) -> None:
    montaje = _Montaje()
    montaje.almacen.apuntado = [
        SeenChange(montaje.reloj.hora() - timedelta(hours=1), Change.CAME, "Pepe")
    ]
    montaje.almacen.falla_al_borrar = OSError("disco lleno en /ruta/secreta")

    with caplog.at_level(logging.ERROR):
        primera = montaje.log.lines()
        segunda = montaje.log.lines()

    assert len(primera) == len(segunda) == 1
    errores = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errores == ["No se pudo borrar lo que ha visto hace más de un día (OSError)"]
    assert "/ruta/secreta" not in caplog.text


def test_un_fallo_al_apuntar_se_dice_una_vez_con_su_tipo_y_no_para_nada(
    caplog: pytest.LogCaptureFixture,
) -> None:
    montaje = _Montaje()
    montaje.almacen.falla = OSError("disco lleno en /ruta/secreta")

    with caplog.at_level(logging.ERROR):
        montaje.ve(None, durante=ARRIVE_SECONDS + 0.2)
        montaje.ve(None, "Marta", durante=ARRIVE_SECONDS + 0.2)

    errores = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errores == ["No se pudo apuntar lo que ha visto (OSError)"]
    assert "/ruta/secreta" not in caplog.text


# --- En la vista ---------------------------------------------------------------------------


class _Camara:
    def __init__(self) -> None:
        self.perdida = False

    def open(self) -> None:
        return None

    def read(self) -> str:
        if self.perdida:
            raise CameraUnavailable("desenchufada")
        return "fotograma"

    def close(self) -> None:
        return None


@dataclass
class _Detector:
    name: str = "mediapipe"
    caras: list[tuple[SeenFace[str], ...]] = field(default_factory=list)

    def detect(self, frame: str) -> tuple[SeenFace[str], ...]:
        del frame
        return self.caras.pop(0) if self.caras else ()


@dataclass
class _Quien:
    """Quien recuerda lo que ve, de mentira: apunta lo que le dice la vista."""

    vistos: list[tuple[float, tuple[str | None, ...]]] = field(default_factory=list)
    pausas: int = 0
    limpiezas: int = 0
    falla: Exception | None = None
    falla_al_limpiar: Exception | None = None

    def see(self, now: float, names: Sequence[str | None]) -> None:
        if self.falla is not None:
            raise self.falla
        self.vistos.append((now, tuple(names)))

    def pause(self) -> None:
        self.pausas += 1

    def tidy(self) -> None:
        if self.falla_al_limpiar is not None:
            raise self.falla_al_limpiar
        self.limpiezas += 1


class _Reconocer:
    version = 0

    def wants_face(self) -> bool:
        return False

    def take_face(self, crop: str) -> None:
        del crop

    def who_by_face(self, crop: str) -> str | None:
        return {"marta": "Marta"}.get(crop)


def _vista(quien: _Quien) -> tuple[LocalSight, _Detector, _Camara, _Reloj]:
    reloj, detector, camara = _Reloj(), _Detector(), _Camara()
    vista = LocalSight(
        load_engines=lambda: SightEngines(camara, detector),
        clock=reloj,
        install_command=_ORDEN,
        recognition=_Reconocer(),
        log=quien,
    )
    vista.start()
    return vista, detector, camara, reloj


def test_la_vista_le_dice_quien_es_cada_cara_de_cada_fotograma() -> None:
    quien = _Quien()
    vista, detector, _, reloj = _vista(quien)

    detector.caras.append((SeenFace(0.3, False, False, "marta"), SeenFace(0.7, True, True, "x")))
    vista.look()
    reloj.avanza(0.1)
    vista.look()

    assert quien.vistos == [(100.0, ("Marta", None)), (100.1, ())]


def test_al_parar_o_perder_la_camara_le_dice_que_ha_dejado_de_ver() -> None:
    quien = _Quien()
    vista, _, camara, _ = _vista(quien)

    vista.stop()
    assert quien.pausas == 1
    vista.start()
    camara.perdida = True
    vista.look()

    assert quien.pausas == 2
    assert not vista.seeing


def test_un_fallo_de_quien_recuerda_se_apunta_una_vez_y_la_vista_sigue(
    caplog: pytest.LogCaptureFixture,
) -> None:
    quien = _Quien(falla=RuntimeError("Marta"))
    vista, detector, _, _ = _vista(quien)

    with caplog.at_level(logging.ERROR):
        for _ in range(2):
            detector.caras.append((SeenFace(0.3, False, False, "marta"),))
            vista.look()

    assert vista.in_front_names() == ("Marta",)
    errores = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errores == ["Quien recuerda lo que ve ha fallado (RuntimeError)"]


def test_la_vista_le_pide_borrar_lo_viejo_en_cada_vuelta_vea_o_no() -> None:
    quien = _Quien()
    vista, _, camara, _ = _vista(quien)

    vista.look()
    vista.stop()
    vista.look()
    vista.start()
    camara.perdida = True
    vista.look()
    vista.look()

    assert quien.limpiezas == 4


def test_un_fallo_al_borrar_lo_viejo_se_apunta_una_vez_y_la_vista_sigue(
    caplog: pytest.LogCaptureFixture,
) -> None:
    quien = _Quien(falla_al_limpiar=OSError("disco lleno en /ruta/secreta"))
    vista, detector, _, _ = _vista(quien)

    with caplog.at_level(logging.ERROR):
        for _ in range(2):
            detector.caras.append((SeenFace(0.3, False, False, "marta"),))
            vista.look()

    assert vista.in_front_names() == ("Marta",)
    assert len(quien.vistos) == 2
    errores = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errores == ["Quien recuerda lo que ve ha fallado (OSError)"]
    assert "/ruta/secreta" not in caplog.text
