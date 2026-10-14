"""El oído del robot, del micro a la charla (ADR-242), con un doble en cada pieza.

Las pruebas de aceptación (``tests/acceptance/test_robot_0_3_voz.py``) miran lo que ve
el propietario; estas miran los bordes del servicio que allí no salen: lo que guarda de
antes de la voz, un turno sin palabras, lo que pasa si falta algo, si la charla falla o
si se para a medias, y que el diario no se quede con nada de lo oído.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from types import SimpleNamespace
from typing import cast

import pytest

from sirius.application.local_listening import Attended, HeardTurn, LocalListening
from sirius.application.send_message import SendMessageResult
from sirius.domain.conversation import MessageStatus
from sirius.ports.local_voice import ListeningEngines, TurnSignal, VoiceUnavailable

FIN = "fin"


def voz(texto: str) -> str:
    return f"voz:{texto}"


class _Micro:
    """Un micro con lo que va a sonar ya escrito: ``voz:...`` es voz, vacío es silencio."""

    def __init__(self) -> None:
        self.pendientes: list[str] = []
        self.abierto = False
        self.aperturas = 0
        self.falla_al_abrir: VoiceUnavailable | None = None

    def open(self) -> None:
        if self.falla_al_abrir is not None:
            raise self.falla_al_abrir
        self.abierto = True
        self.aperturas += 1

    def close(self) -> None:
        self.abierto = False

    def read(self) -> str | None:
        assert self.abierto, "se ha leído el micro cerrado"
        return self.pendientes.pop(0) if self.pendientes else None


class _Detector:
    def __init__(self) -> None:
        self.vistos: list[str] = []

    def listen(self, chunk: str) -> TurnSignal:
        self.vistos.append(chunk)
        if chunk == FIN:
            return TurnSignal.ENDED
        return TurnSignal.VOICE if chunk.startswith("voz:") else TurnSignal.QUIET


class _Transcriptor:
    def __init__(self) -> None:
        self.turnos: list[list[str]] = []
        self.devuelve: str | None = None

    def transcribe(self, chunks: Sequence[str]) -> str:
        self.turnos.append(list(chunks))
        if self.devuelve is not None:
            return self.devuelve
        return " ".join(c.removeprefix("voz:") for c in chunks if c.startswith("voz:"))


class _Charla:
    def __init__(self) -> None:
        self.mensajes: list[str] = []
        self.falla: Exception | None = None
        self.desenlace = MessageStatus.COMPLETED

    def send_message(self, user_text: str) -> SendMessageResult:
        self.mensajes.append(user_text)
        if self.falla is not None:
            falla, self.falla = self.falla, None
            raise falla
        respuesta = SimpleNamespace(
            outcome=self.desenlace, sirius_message=SimpleNamespace(content=f"R: {user_text}")
        )
        return cast("SendMessageResult", respuesta)


class _Instalacion:
    def __init__(self) -> None:
        self.faltan: tuple[str, ...] = ()

    @property
    def install_command(self) -> str:
        return "la orden de instalar"

    def missing(self) -> tuple[str, ...]:
        return self.faltan


class _Oido:
    """Todo junto, con el servicio montado como en producción."""

    def __init__(self, *, antes: int = 2) -> None:
        self.micro = _Micro()
        self.detector = _Detector()
        self.transcriptor = _Transcriptor()
        self.charla = _Charla()
        self.instalacion = _Instalacion()
        self.cargas = 0
        self.falla_al_cargar: VoiceUnavailable | None = None
        self.servicio: LocalListening[str] = LocalListening(
            chat=self.charla,
            installation=self.instalacion,
            load_engines=self._carga,
            pre_roll=antes,
        )

    def _carga(self) -> ListeningEngines[str]:
        self.cargas += 1
        if self.falla_al_cargar is not None:
            raise self.falla_al_cargar
        return ListeningEngines(self.micro, self.detector, self.transcriptor)

    def suena(self, *trozos: str) -> Attended:
        self.micro.pendientes.extend(trozos)
        return self.servicio.attend()


def test_un_turno_va_a_la_charla_con_lo_que_sono_justo_antes_de_la_voz() -> None:
    oido = _Oido(antes=2)
    assert oido.servicio.start() == ""

    atendido = oido.suena("", "a", "b", voz("Hola"), "", FIN)

    assert atendido == Attended(turns=(HeardTurn("Hola", True, "R: Hola"),))
    # Los dos trozos de antes de la voz, para no cortarle la primera sílaba; no más.
    assert oido.transcriptor.turnos == [["a", "b", voz("Hola"), "", FIN]]
    assert oido.charla.mensajes == ["Hola"]


def test_cada_trozo_se_le_ensena_al_detector_una_vez_y_en_orden() -> None:
    oido = _Oido()
    oido.servicio.start()

    oido.suena("", voz("Uno"), "", FIN, "", voz("Dos"), FIN)

    assert oido.detector.vistos == ["", voz("Uno"), "", FIN, "", voz("Dos"), FIN]


def test_sin_fin_de_turno_espera_y_lo_cierra_cuando_el_detector_lo_dice() -> None:
    oido = _Oido()
    oido.servicio.start()

    assert oido.suena(voz("Estaba pensando"), "", "") == Attended()
    assert oido.transcriptor.turnos == []
    assert oido.charla.mensajes == []

    atendido = oido.suena("", FIN)

    assert [t.heard for t in atendido.turns] == ["Estaba pensando"]
    assert oido.transcriptor.turnos == [[voz("Estaba pensando"), "", "", "", FIN]]


def test_un_fin_de_turno_sin_voz_delante_ni_empieza_turno_ni_transcribe() -> None:
    # Whisper se inventa frases sobre el silencio: sin voz no hay turno que transcribir.
    oido = _Oido(antes=1)
    oido.servicio.start()

    assert oido.suena("", FIN, "") == Attended()
    assert oido.transcriptor.turnos == []
    assert oido.charla.mensajes == []

    atendido = oido.suena(voz("Hola"), FIN)

    assert [t.heard for t in atendido.turns] == ["Hola"]
    # El turno empezó con la voz y lo de justo antes, no con aquel fin suelto.
    assert oido.transcriptor.turnos == [["", voz("Hola"), FIN]]


def test_dos_turnos_en_una_sola_atencion_se_devuelven_en_orden() -> None:
    oido = _Oido()
    oido.servicio.start()

    atendido = oido.suena(voz("Uno"), FIN, voz("Dos"), FIN)

    assert [t.heard for t in atendido.turns] == ["Uno", "Dos"]
    assert oido.charla.mensajes == ["Uno", "Dos"]


def test_un_turno_sin_palabras_no_va_a_la_charla() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.transcriptor.devuelve = "   "

    assert oido.suena(voz("ruido"), FIN) == Attended()
    assert oido.charla.mensajes == []

    oido.transcriptor.devuelve = None
    assert [t.heard for t in oido.suena(voz("Hola"), FIN).turns] == ["Hola"]


def test_si_falta_el_modelo_avisa_con_la_orden_y_no_carga_ni_abre_nada() -> None:
    oido = _Oido()
    oido.instalacion.faltan = ("el modelo de oír (faster-whisper small)",)

    aviso = oido.servicio.start()

    assert "el modelo de oír (faster-whisper small)" in aviso
    assert "la orden de instalar" in aviso
    assert oido.cargas == 0
    assert not oido.micro.abierto
    assert not oido.servicio.listening
    oido.micro.pendientes.append(voz("Hola"))
    assert oido.servicio.attend() == Attended(notice=aviso), "sin escuchar no se lee el micro"
    assert oido.micro.pendientes == [voz("Hola")]


def test_si_faltan_varias_cosas_las_dice_todas() -> None:
    oido = _Oido()
    oido.instalacion.faltan = ("el modelo de oír", "la voz", "el detector")

    assert "me falta el modelo de oír, la voz y el detector en este ordenador" in (
        oido.servicio.start()
    )


def test_si_el_oido_no_carga_avisa_con_la_orden() -> None:
    oido = _Oido()
    oido.falla_al_cargar = VoiceUnavailable("falta pipecat", fixed_by_install=True)

    aviso = oido.servicio.start()

    assert "No puedo oírte: falta pipecat." in aviso
    assert "la orden de instalar" in aviso
    assert not oido.servicio.listening


def test_sin_microfono_avisa_sin_la_orden_que_no_lo_arregla() -> None:
    oido = _Oido()
    oido.micro.falla_al_abrir = VoiceUnavailable("no hay micrófono", fixed_by_install=False)

    aviso = oido.servicio.start()

    assert aviso == "No puedo oírte: no hay micrófono."
    assert not oido.servicio.listening


def test_arrancar_dos_veces_no_vuelve_a_cargar_ni_a_abrir() -> None:
    oido = _Oido()

    assert oido.servicio.start() == ""
    assert oido.servicio.start() == ""

    assert oido.cargas == 1
    assert oido.micro.aperturas == 1


def test_un_aviso_se_quita_cuando_ya_puede_oir() -> None:
    oido = _Oido()
    oido.instalacion.faltan = ("el modelo de oír",)
    assert oido.servicio.start()

    oido.instalacion.faltan = ()

    assert oido.servicio.start() == ""
    assert oido.servicio.attend() == Attended()


def test_parar_cierra_el_micro_y_olvida_el_turno_a_medias() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.suena(voz("Lo que no acabó"), "")

    oido.servicio.stop()

    assert not oido.micro.abierto
    assert oido.servicio.attend() == Attended()
    oido.servicio.start()
    atendido = oido.suena(voz("Hola"), FIN)
    assert [t.heard for t in atendido.turns] == ["Hola"]
    assert oido.transcriptor.turnos == [[voz("Hola"), FIN]]


def test_si_la_charla_falla_el_turno_no_se_queda_a_medias() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.falla = RuntimeError("el modelo no contesta")

    with pytest.raises(RuntimeError, match="el modelo no contesta"):
        oido.suena(voz("Primero"), FIN)

    atendido = oido.suena(voz("Segundo"), FIN)
    assert [t.heard for t in atendido.turns] == ["Segundo"]
    assert oido.transcriptor.turnos[-1] == [voz("Segundo"), FIN]


def test_si_la_charla_no_acaba_bien_el_turno_lo_dice() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.desenlace = MessageStatus.FAILED

    (turno,) = oido.suena(voz("Hola"), FIN).turns

    assert turno.heard == "Hola"
    assert not turno.answered


def test_el_diario_no_se_queda_con_nada_de_lo_oido(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Una migración anterior en el mismo proceso (Alembic, `fileConfig`) apaga los
    # registradores que ya existían: se enciende el del oído para poder leerlo.
    monkeypatch.setattr(logging.getLogger("sirius.application.local_listening"), "disabled", False)
    oido = _Oido()
    oido.servicio.start()

    with caplog.at_level(logging.DEBUG):
        oido.suena(voz("La clave es Zarzamora"), FIN)

    assert "Turno de voz entregado a la charla" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()
