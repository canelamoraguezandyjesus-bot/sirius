"""El registro de conexiones de ADR-255: qué apunta y qué cuelga, sin red de verdad."""

from __future__ import annotations

import socket
from collections.abc import Iterator

import pytest

from sirius.infrastructure.network import ConnectionRegistry


class _Flujo:
    """Lo que httpcore pasa como ``return_value`` al abrir una conexión."""

    def __init__(self, conexion: socket.socket) -> None:
        self._conexion = conexion

    def get_extra_info(self, nombre: str) -> object:
        return self._conexion if nombre == "socket" else None


@pytest.fixture
def par() -> Iterator[tuple[socket.socket, socket.socket]]:
    nuestro, suyo = socket.socketpair()
    yield nuestro, suyo
    nuestro.close()
    suyo.close()


@pytest.fixture
def otro_par() -> Iterator[tuple[socket.socket, socket.socket]]:
    nuestro, suyo = socket.socketpair()
    yield nuestro, suyo
    nuestro.close()
    suyo.close()


def _colgado(nuestro: socket.socket, suyo: socket.socket) -> bool:
    """Si ``nuestro`` está colgado: el otro extremo lee el fin de la conexión."""
    suyo.settimeout(0.5)
    try:
        return suyo.recv(1) == b""
    except TimeoutError:
        return False


@pytest.mark.parametrize(
    "evento",
    [
        "connection.connect_tcp.complete",
        # La TLS envuelve a la TCP y es la que queda viva: con ella se cuelga.
        "connection.start_tls.complete",
        # Con proxy, httpcore cambia el prefijo del evento.
        "proxy.start_tls.complete",
        "socks.connect_tcp.complete",
    ],
)
def test_apunta_la_conexion_que_se_abre_y_la_cuelga_al_cerrar(
    evento: str, par: tuple[socket.socket, socket.socket]
) -> None:
    nuestro, suyo = par
    registro = ConnectionRegistry()

    registro.trace(evento, {"return_value": _Flujo(nuestro)})

    assert registro.hang_up_all() == 1
    assert _colgado(nuestro, suyo)


def test_no_apunta_lo_que_no_abre_una_conexion(par: tuple[socket.socket, socket.socket]) -> None:
    nuestro, suyo = par
    registro = ConnectionRegistry()

    registro.trace("connection.connect_tcp.started", {"return_value": _Flujo(nuestro)})
    registro.trace("http11.send_request_headers.complete", {"return_value": _Flujo(nuestro)})

    assert registro.hang_up_all() == 0
    assert not _colgado(nuestro, suyo)


def test_una_conexion_ya_cerrada_no_cuenta(par: tuple[socket.socket, socket.socket]) -> None:
    nuestro, _ = par
    registro = ConnectionRegistry()
    registro.trace("connection.connect_tcp.complete", {"return_value": _Flujo(nuestro)})
    nuestro.close()

    assert registro.hang_up_all() == 0


def test_al_salir_cuelga_en_el_acto_lo_que_se_abre_despues(
    par: tuple[socket.socket, socket.socket],
) -> None:
    nuestro, suyo = par
    registro = ConnectionRegistry()
    registro.hang_up_all(final=True)

    registro.trace("connection.connect_tcp.complete", {"return_value": _Flujo(nuestro)})

    assert _colgado(nuestro, suyo)


def test_colgar_sin_salir_no_cuelga_lo_que_se_abre_despues(
    par: tuple[socket.socket, socket.socket],
) -> None:
    nuestro, suyo = par
    registro = ConnectionRegistry()
    registro.hang_up_all()

    registro.trace("connection.connect_tcp.complete", {"return_value": _Flujo(nuestro)})

    assert not _colgado(nuestro, suyo)


def test_al_pedir_cerrar_una_ventana_cuelga_lo_abierto(
    par: tuple[socket.socket, socket.socket],
) -> None:
    nuestro, suyo = par
    registro = ConnectionRegistry()
    registro.trace("connection.connect_tcp.complete", {"return_value": _Flujo(nuestro)})

    registro.begin_close()

    assert _colgado(nuestro, suyo)


def test_mientras_se_cierra_una_ventana_cuelga_en_el_acto_lo_que_se_abre(
    par: tuple[socket.socket, socket.socket],
) -> None:
    """Ronda 4 de Codex sobre la #698: una conexión a medio abrir al pedir cerrar no estaba
    apuntada al colgar, y seguía hasta su tope. Hasta que la ventana se cierra de verdad, lo
    que se abre se cuelga en el acto."""
    nuestro, suyo = par
    registro = ConnectionRegistry()
    registro.begin_close()

    registro.trace("connection.connect_tcp.complete", {"return_value": _Flujo(nuestro)})

    assert _colgado(nuestro, suyo)


def test_al_cerrarse_de_verdad_la_ventana_no_cuelga_lo_que_se_abre_despues(
    par: tuple[socket.socket, socket.socket],
) -> None:
    """Tras cambiar de proyecto se abre otra ventana con las mismas dependencias."""
    nuestro, suyo = par
    registro = ConnectionRegistry()
    registro.begin_close()
    registro.end_close()

    registro.trace("connection.connect_tcp.complete", {"return_value": _Flujo(nuestro)})

    assert not _colgado(nuestro, suyo)


def test_con_dos_ventanas_cerrandose_cuelga_hasta_que_se_cierra_la_ultima(
    par: tuple[socket.socket, socket.socket], otro_par: tuple[socket.socket, socket.socket]
) -> None:
    registro = ConnectionRegistry()
    registro.begin_close()
    registro.begin_close()
    registro.end_close()

    registro.trace("connection.connect_tcp.complete", {"return_value": _Flujo(par[0])})
    assert _colgado(*par)

    registro.end_close()
    registro.trace("connection.connect_tcp.complete", {"return_value": _Flujo(otro_par[0])})
    assert not _colgado(*otro_par)


def test_un_fin_de_cierre_de_mas_no_deja_sin_colgar_el_siguiente(
    par: tuple[socket.socket, socket.socket],
) -> None:
    nuestro, suyo = par
    registro = ConnectionRegistry()
    registro.end_close()
    registro.begin_close()

    registro.trace("connection.connect_tcp.complete", {"return_value": _Flujo(nuestro)})

    assert _colgado(nuestro, suyo)
