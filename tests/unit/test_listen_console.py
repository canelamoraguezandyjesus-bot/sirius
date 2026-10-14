"""La orden ``sirius-oye``: escucha, cuenta cada turno y cierra el micro al salir (ADR-242)."""

from __future__ import annotations

import pytest

from sirius.application.local_listening import Attended, HeardTurn
from sirius.listen_console import listen


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
    turno = HeardTurn("Buenos días, Sirius.", True, "Buenos días.")
    oido = _Oido(atenciones=[Attended(), Attended(turns=(turno,))])

    codigo, dicho, pausas = _escucha(oido, 2)

    assert codigo == 0
    assert dicho[1:] == ["Tú: Buenos días, Sirius.", "Sirius: Buenos días."]
    assert pausas == 1
    assert oido.parado


def test_si_sirius_no_pudo_contestar_lo_dice_en_vez_de_dejarlo_en_blanco() -> None:
    turno = HeardTurn("Hola", True, "", answered=False)
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == [
        "Tú: Hola",
        "Sirius no ha podido contestar: mira que su modelo esté abierto.",
    ]


def test_con_ctrl_c_tambien_cierra_el_micro() -> None:
    oido = _Oido(atenciones=[KeyboardInterrupt()])

    with pytest.raises(KeyboardInterrupt):
        _escucha(oido, 5)

    assert oido.parado
