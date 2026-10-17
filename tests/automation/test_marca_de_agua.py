"""La marca de agua de la voz de personaje puede cargar con lo que fija el lock (ADR-250).

Chatterbox crea al cargar la marca de agua de Perth, que dice que el audio es generado.
Perth la deja en ``None`` si su importación falla, y entonces Chatterbox se rompe al
crearla: en su ordenador, «'NoneType' object is not callable». Lo que fallaba:
`resemble-perth` 1.0.1 importa ``pkg_resources`` (``perth/perth_net/__init__.py``, en su
primera línea), y `setuptools` lo quitó en la 82; `uv.lock` fijaba la 84.0.0.

Quality no instala el extra `personaje`, así que aquí se mira el lock: mientras lleve un
Perth del que no se sepa que ya no importa ``pkg_resources``, su `setuptools` tiene que
traerlo. La marca de agua no se quita nunca: si un Perth nuevo deja de necesitarlo, se
comprueba leyendo su código y se añade a la lista de abajo.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

#: Las versiones de `resemble-perth` que se ha comprobado que ya no importan
#: ``pkg_resources``. Ninguna, hoy: la 1.0.1 lo importa.
PERTH_SIN_PKG_RESOURCES: frozenset[str] = frozenset()

#: La primera versión de `setuptools` que ya no trae ``pkg_resources``: la 82.0.0 y la
#: 83.0.0 no lo traen; la 80.9.0 y la 81.0.0, sí.
SETUPTOOLS_SIN_PKG_RESOURCES = (82,)


def _versiones(nombre: str, lock: dict[str, object]) -> list[str]:
    paquetes = lock.get("package")
    assert isinstance(paquetes, list)
    return [str(p["version"]) for p in paquetes if isinstance(p, dict) and p.get("name") == nombre]


def _numeros(version: str) -> tuple[int, ...]:
    return tuple(int(parte) for parte in version.split(".") if parte.isdigit())


def test_con_un_perth_que_importa_pkg_resources_el_lock_trae_un_setuptools_que_lo_tiene() -> None:
    lock = tomllib.loads((RAIZ / "uv.lock").read_text(encoding="utf-8"))
    perth = [v for v in _versiones("resemble-perth", lock) if v not in PERTH_SIN_PKG_RESOURCES]
    if not perth:
        return
    setuptools = _versiones("setuptools", lock)
    assert setuptools, f"el lock lleva resemble-perth {perth} y ningún setuptools"
    sin_pkg_resources = [v for v in setuptools if _numeros(v)[:1] >= SETUPTOOLS_SIN_PKG_RESOURCES]
    assert not sin_pkg_resources, (
        f"el lock lleva resemble-perth {perth}, que importa pkg_resources, y setuptools "
        f"{sin_pkg_resources}, que ya no lo trae: la voz de personaje no carga (ADR-250)"
    )


def test_la_guarda_compara_las_versiones_por_su_numero() -> None:
    assert _numeros("81.0.0") < SETUPTOOLS_SIN_PKG_RESOURCES
    assert _numeros("82.0.0")[:1] >= SETUPTOOLS_SIN_PKG_RESOURCES
    assert _numeros("100.1.0")[:1] >= SETUPTOOLS_SIN_PKG_RESOURCES
    assert _numeros("9.0.0")[:1] < SETUPTOOLS_SIN_PKG_RESOURCES
