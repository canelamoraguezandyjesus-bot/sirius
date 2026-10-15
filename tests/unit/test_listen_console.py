"""La orden ``sirius-oye``: escucha, cuenta cada turno y cierra el micro al salir (ADR-242)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.application.local_listening import CHAT_LEAVES, Attended, HeardTurn
from sirius.application.send_message import SendMessageResult
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.listen_console import listen
from sirius.ports.llm import LLMErrorKind
from sirius.presentation.error_messages import failed_send_message


def _turno(
    oido: str,
    contesta: str,
    desenlace: MessageStatus = MessageStatus.COMPLETED,
    *,
    por_que: LLMErrorKind | None = None,
    propuesto: str | None = None,
) -> HeardTurn:
    """Un turno con el resultado de la charla tal como lo devuelve ella: los dos mensajes
    guardados, el de Sirius con lo que escribió y cómo acabó, y su operación."""
    hoy = datetime(2026, 10, 15, tzinfo=UTC)
    tuyo = Message(1, 1, 1, MessageRole.USER, oido, hoy, operation_id="op-1")
    suyo = Message(2, 1, 2, MessageRole.SIRIUS, contesta, hoy, "op-1", 1, desenlace)
    resultado = SendMessageResult(desenlace, tuyo, suyo, None, error_kind=por_que)
    return HeardTurn(oido, True, resultado, propuesto)


class _Oido:
    def __init__(self, aviso: str = "", atenciones: list[Attended | BaseException] | None = None):
        self.aviso = aviso
        self.atenciones = list(atenciones or [])
        self.parado = False

    def start(self) -> str:
        return self.aviso

    def attend(self) -> Attended:
        atencion = self.atenciones.pop(0)
        if isinstance(atencion, BaseException):
            raise atencion
        return atencion

    def stop(self) -> None:
        self.parado = True


def _escucha(oido: _Oido, vueltas: int) -> tuple[int, list[str], int]:
    dicho: list[str] = []
    pausas = 0

    def pausa() -> None:
        nonlocal pausas
        pausas += 1

    quedan = iter([True] * vueltas + [False])
    codigo = listen(
        oido,  # type: ignore[arg-type]
        dicho.append,
        keep_going=lambda: next(quedan),
        pause=pausa,
    )
    return codigo, dicho, pausas


def test_sin_el_oido_instalado_dice_el_aviso_y_sale_sin_escuchar() -> None:
    oido = _Oido(aviso="Para oírte me falta el modelo. Ejecuta: la orden")

    codigo, dicho, _ = _escucha(oido, 3)

    assert codigo == 1
    assert dicho == ["Para oírte me falta el modelo. Ejecuta: la orden"]
    assert oido.atenciones == []


def test_cuenta_cada_turno_espera_cuando_no_llega_nada_y_cierra_al_salir() -> None:
    turno = _turno("Buenos días, Sirius.", "Buenos días.")
    oido = _Oido(atenciones=[Attended(), Attended(turns=(turno,))])

    codigo, dicho, pausas = _escucha(oido, 2)

    assert codigo == 0
    assert dicho[1:] == ["Tú: Buenos días, Sirius.", "Sirius: Buenos días."]
    assert pausas == 1
    assert oido.parado


def test_si_la_charla_falla_a_medias_ensena_lo_escrito_y_el_aviso_como_la_ventana() -> None:
    # Rondas 12 y 13 de Codex sobre la PR #687: lo que llegó a escribir, con su marca, y el
    # mismo aviso que la ventana para ese fallo, con su referencia, sin adivinar el remedio.
    turno = _turno("Hola", "Ho", MessageStatus.FAILED, por_que=LLMErrorKind.TIMEOUT)
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == [
        "Tú: Hola",
        "Sirius: Ho (fallido)",
        failed_send_message(LLMErrorKind.TIMEOUT, "op-1"),
    ]


def test_si_la_charla_falla_sin_escribir_nada_lo_marca_igual() -> None:
    turno = _turno("Hola", "", MessageStatus.FAILED, por_que=LLMErrorKind.CONNECTION)
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == [
        "Tú: Hola",
        "Sirius: (fallido)",
        failed_send_message(LLMErrorKind.CONNECTION, "op-1"),
    ]


def test_un_turno_cancelado_se_ensena_como_en_la_ventana() -> None:
    turno = _turno("Hola", "Ho", MessageStatus.CANCELLED)
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == ["Tú: Hola", "Sirius: Ho (cancelado)", "Envío cancelado."]


def test_si_sirius_propone_recordar_algo_dice_donde_confirmarlo() -> None:
    turno = _turno("Me encanta el café", "¡Anotado!", propuesto="Le gusta el café")
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == [
        "Tú: Me encanta el café",
        "Sirius: ¡Anotado!",
        "Sirius propone recordar «Le gusta el café»: lo confirmas o lo rechazas en "
        "Memoria y decisiones, en la ventana.",
    ]


def test_si_deja_de_oir_mientras_escucha_lo_dice_y_sale() -> None:
    # Ronda 11 de Codex sobre la PR #687: la charla se fue a un modelo de fuera mientras
    # oía. El oído para y lo dice; la orden cuenta lo que ya oyó, dice el aviso y sale en
    # vez de esperar a un micro cerrado: otra vuelta pediría una atención que no hay.
    turno = _turno("Buenos días, Sirius.", "Buenos días.")
    oido = _Oido(atenciones=[Attended(turns=(turno,), notice=CHAT_LEAVES)])

    codigo, dicho, pausas = _escucha(oido, 5)

    assert codigo == 1
    assert dicho[1:] == ["Tú: Buenos días, Sirius.", "Sirius: Buenos días.", CHAT_LEAVES]
    assert pausas == 0
    assert oido.parado


def test_con_ctrl_c_tambien_cierra_el_micro() -> None:
    oido = _Oido(atenciones=[KeyboardInterrupt()])

    with pytest.raises(KeyboardInterrupt):
        _escucha(oido, 5)

    assert oido.parado
