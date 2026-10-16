"""Una carpeta temporal que se borra al acabar sin tapar lo ya dicho (ADR-247).

Las órdenes de sus evaluaciones trabajan sobre copias en una carpeta temporal y la borran
al acabar. En Windows no se borra un fichero que alguien tiene abierto, y el 16-10-2026 la
orden de E-R02-05 se rompió ahí, al salir, sin llegar a decir si pasaba. Con esta carpeta,
la orden dice lo suyo antes de borrar, y si no puede borrar, lo avisa y sigue.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

__all__ = ["temporary_folder"]


@contextmanager
def temporary_folder(prefix: str, warn: Callable[[str], None]) -> Iterator[Path]:
    """Una carpeta temporal nueva, que se borra al salir; si no se puede, ``warn`` lo dice."""
    folder = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield folder
    finally:
        try:
            shutil.rmtree(folder)
        except OSError as error:
            warn(f"Aviso: no se pudo borrar la carpeta temporal {folder}. {error}")
