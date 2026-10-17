"""Toda orden de uv que Sirius enseña al propietario lleva ``--link-mode=copy`` (punto 19
de la incidencia #696).

Su carpeta de Sirius está en OneDrive, y lo que pega en PowerShell tiene que ir bien ahí:
con ``--link-mode=copy``, uv copia lo que instala en vez de enlazarlo a su caché. La guarda
mira cada texto de ``src/sirius`` que lleve ``uv run`` o ``uv sync``, salvo los docstrings,
que no llegan a la pantalla, a la consola ni a un aviso. Es determinista: lee ficheros con
``ast``, no ejecuta nada y cuesta milisegundos.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src" / "sirius"
_ORDEN = re.compile(r"\buv (?:run|sync)\b")
_CON_COPIA = re.compile(r"\buv (?:run|sync) --link-mode=copy\b")


def _docstrings(arbol: ast.Module) -> set[int]:
    """Los nodos que son docstrings, por su ``id``: esos no llegan a la pantalla."""
    vistos: set[int] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            primero = nodo.body[0] if nodo.body else None
            if (
                isinstance(primero, ast.Expr)
                and isinstance(primero.value, ast.Constant)
                and isinstance(primero.value.value, str)
            ):
                vistos.add(id(primero.value))
    return vistos


def _ordenes_de_uv() -> list[tuple[str, int, str]]:
    """Cada texto de ``src/sirius`` con una orden de uv dentro: fichero, línea y texto."""
    ordenes: list[tuple[str, int, str]] = []
    for fichero in sorted(_SRC.rglob("*.py")):
        arbol = ast.parse(fichero.read_text(encoding="utf-8"))
        docstrings = _docstrings(arbol)
        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Constant)
                and isinstance(nodo.value, str)
                and id(nodo) not in docstrings
                and _ORDEN.search(nodo.value)
            ):
                ordenes.append((fichero.relative_to(_SRC).as_posix(), nodo.lineno, nodo.value))
    return ordenes


def test_toda_orden_de_uv_que_se_le_ensena_lleva_link_mode_copy() -> None:
    sin_copia = [
        (fichero, linea, texto)
        for fichero, linea, texto in _ordenes_de_uv()
        if len(_ORDEN.findall(texto)) != len(_CON_COPIA.findall(texto))
    ]

    assert sin_copia == [], (
        "Estas órdenes de uv se le enseñan sin --link-mode=copy, y su carpeta de Sirius "
        "está en OneDrive (punto 19 de la #696)."
    )


def test_la_guarda_ve_las_ordenes_que_hay() -> None:
    """Anti-vacua: si la guarda dejara de ver las órdenes, la de arriba pasaría sin mirar
    nada. Hoy las enseñan la instalación de la voz y la orden que la instala."""
    ficheros = {fichero for fichero, _linea, _texto in _ordenes_de_uv()}

    assert {"infrastructure/local_voice_installation.py", "install_local_voice.py"} <= ficheros
