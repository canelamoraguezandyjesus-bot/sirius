"""Ver aquí lo que en Windows no deja borrar una carpeta: un fichero que este proceso
tiene abierto (ADR-247).

En Linux se borra un fichero abierto sin queja; en Windows no: «está siendo utilizado por
otro proceso», WinError 32. Las órdenes de sus evaluaciones trabajan en carpetas
temporales y las borran al acabar, así que una conexión a SQLite que nadie cierra las
rompe en su ordenador y aquí pasaría sin verse. Se mira en ``/proc/self/fd``, que solo hay
en Linux.
"""

from __future__ import annotations

import gc
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

#: Si este sistema deja ver qué ficheros tiene abiertos el proceso.
PUEDE_MIRAR = Path("/proc/self/fd").is_dir()


def abiertos_en(carpeta: Path) -> list[str]:
    """Los ficheros de ``carpeta`` que este proceso tiene abiertos, uno por cada vez."""
    raiz = os.path.realpath(carpeta) + os.sep
    abiertos: list[str] = []
    for descriptor in Path("/proc/self/fd").iterdir():
        try:
            destino = os.readlink(descriptor)
        except OSError:
            continue
        if destino.startswith(raiz):
            abiertos.append(destino)
    return sorted(abiertos)


def vigila_lo_que_se_borra(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, list[str]]]:
    """Antes de cada ``shutil.rmtree``, apunta qué ficheros de esa carpeta siguen abiertos."""
    verdadero = shutil.rmtree
    borrados: list[tuple[Path, list[str]]] = []

    def rmtree(ruta: Any, *args: Any, **kwargs: Any) -> None:
        borrados.append((Path(ruta), abiertos_en(Path(ruta))))
        verdadero(ruta, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", rmtree)
    return borrados


@contextmanager
def sin_recolector() -> Iterator[None]:
    """Sin el recolector de ciclos, lo que nadie cierra sigue abierto al borrar, como en su
    ordenador; con él, a veces lo cerraría antes y la prueba pasaría por suerte."""
    gc.collect()
    gc.disable()
    try:
        yield
    finally:
        gc.enable()
