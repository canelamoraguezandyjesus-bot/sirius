"""Colgar la red de Sirius mientras una ventana se cierra (ADR-255).

La presentación no sabe de sockets ni de clientes de red: el punto de composición le da a
cada ventana lo que cuelga, y la ventana solo dice cuándo pide cerrarse y cuándo se cerró
de verdad (ronda 4 de Codex sobre la #698).
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["ConnectionCloser"]


class ConnectionCloser(Protocol):
    def begin_close(self) -> None:
        """Una ventana pide cerrarse: cuelga lo que está en vuelo y, hasta ``end_close``,
        toda conexión que se abra, también la que estaba a medio abrir al pedirlo."""
        ...

    def end_close(self) -> None:
        """La ventana se cerró de verdad: lo que se abra desde ahora ya no se cuelga, porque
        tras cambiar de proyecto se abre otra ventana con las mismas dependencias.

        Cada ``begin_close`` lleva el suyo: con dos ventanas cerrándose a la vez, se cuelga
        hasta que se cierra la última.
        """
        ...
