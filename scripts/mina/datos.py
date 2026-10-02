"""Donde viven los datos de la mina: el volcado de `descargar.py` y lo que los guiones escriben.

El volcado no entra en el repositorio (376 incidencias y 233 PR en JSON, con
los comentarios enteros): se apunta con la variable de entorno `MINA_DATOS` y,
si no esta, es `scripts/mina/datos/` (ignorada por git). Todos los guiones de
esta carpeta leen y escriben ahi, y ninguno depende del directorio desde el que
se invoque ni de donde viva el clon.

Orden de la cadena, cada paso sobre lo que dejo el anterior:
`descargar.py` -> `descargar_pr.py` -> `analizar.py` -> `analizar_pr.py`,
`reproducir_avisos.py`, `falsos_negativos.py`; `cerrado_por_inalcanzable.py`
lee el registro de defectos del arbol, no el volcado.
"""

from __future__ import annotations

import os
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
_DECLARADO = os.environ.get("MINA_DATOS")
# Una ruta relativa en MINA_DATOS se ancla a la raiz del repositorio, no al
# directorio de invocacion: la misma cadena lee el mismo volcado desde la raiz
# y desde scripts/mina/ (Codex, PR #665 ronda 2).
DATOS = Path(_DECLARADO) if _DECLARADO else AQUI / "datos"
if not DATOS.is_absolute():
    DATOS = RAIZ / DATOS
DATOS = DATOS.resolve()
RAW = DATOS / "raw"
PRDIR = DATOS / "raw_pr"
HISTORIALES = DATOS / "historiales"


def parcial_de(definitivo: Path) -> Path:
    """Donde se descarga ANTES de publicar: al lado del definitivo, con `.parcial`."""
    return definitivo.with_name(definitivo.name + ".parcial")


def publicar_volcado(parcial: Path, definitivo: Path) -> None:
    """Sustituye el volcado definitivo por el parcial, entero, o no lo toca.

    Sobrescribir cada fichero no daba atomicidad: una descarga que fallara a
    medias dejaba un indice nuevo con historiales viejos y `analizar.py`
    mezclaba las dos fotos sin aviso (Codex, PR #665, ronda 6). La descarga
    escribe en `parcial` y solo al terminar entera se publica aqui: el
    definitivo anterior se aparta, el parcial pasa a definitivo y el anterior
    se borra. Si la descarga muere antes, `parcial` queda a la vista y el
    definitivo sigue siendo la ultima foto completa.
    """
    import shutil

    anterior = definitivo.with_name(definitivo.name + ".anterior")
    shutil.rmtree(anterior, ignore_errors=True)
    if definitivo.exists():
        definitivo.rename(anterior)
    try:
        parcial.rename(definitivo)
    except OSError:
        # El segundo renombrado fallo: el anterior vuelve a su sitio para que el
        # definitivo no quede AUSENTE y el parcial siga a la vista (Codex, PR
        # #665, ronda 7). Si el anterior no existia, no hay nada que devolver.
        if anterior.exists():
            anterior.rename(definitivo)
        raise
    shutil.rmtree(anterior, ignore_errors=True)
