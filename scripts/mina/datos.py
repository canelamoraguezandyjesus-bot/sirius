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
