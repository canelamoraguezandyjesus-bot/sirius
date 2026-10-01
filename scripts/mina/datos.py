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
DATOS = Path(os.environ.get("MINA_DATOS", str(AQUI / "datos")))
RAW = DATOS / "raw"
PRDIR = DATOS / "raw_pr"
HISTORIALES = DATOS / "historiales"
