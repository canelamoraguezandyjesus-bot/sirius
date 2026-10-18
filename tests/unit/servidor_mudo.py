"""Un servidor que acepta conexiones y no contesta nunca, para las pruebas del cierre
(ADR-255): una petición contra él queda esperando su tope, y solo colgarla la corta."""

from __future__ import annotations

import socket
import threading

import httpx
import pytest

from sirius.infrastructure.network import ConnectionRegistry, http_client

__all__ = ["ServidorMudo", "quita_los_proxies", "se_cuelga_al_abrirse"]


class ServidorMudo:
    """Acepta conexiones en ``127.0.0.1`` y no contesta nunca."""

    def __init__(self) -> None:
        self._servidor = socket.socket()
        self._servidor.bind(("127.0.0.1", 0))
        self._servidor.listen(16)
        self._servidor.settimeout(0.05)
        self.puerto: int = self._servidor.getsockname()[1]
        self.aceptadas: list[socket.socket] = []
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._acepta, daemon=True)
        self._hilo.start()

    def _acepta(self) -> None:
        while not self._parar.is_set():
            try:
                conexion, _ = self._servidor.accept()
            except OSError:
                continue
            self.aceptadas.append(conexion)

    def cierra(self) -> None:
        self._parar.set()
        self._hilo.join(timeout=1)
        for conexion in self.aceptadas:
            conexion.close()
        self._servidor.close()


def quita_los_proxies(monkeypatch: pytest.MonkeyPatch) -> None:
    """El SDK de OpenAI lee los proxies del sistema: en estas pruebas no, que el servidor es
    local."""
    for nombre in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(nombre, raising=False)


def se_cuelga_al_abrirse(registro: ConnectionRegistry, servidor: ServidorMudo) -> bool:
    """Si una petición nueva, apuntada en ``registro``, se cuelga en cuanto conecta con el
    servidor mudo, en vez de esperar su tope de 0,3 s (ronda 4 de Codex sobre la #698)."""
    cliente = http_client(registry=registro, timeout=httpx.Timeout(0.3), trust_env=False)
    try:
        cliente.get(f"http://127.0.0.1:{servidor.puerto}/")
    except httpx.TimeoutException:
        return False
    except httpx.HTTPError:
        return True
    finally:
        cliente.close()
    raise AssertionError("el servidor mudo no contesta nunca")
