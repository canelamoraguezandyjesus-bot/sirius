"""Hace importable el paquete ``experiments`` al ejecutar estas pruebas.

El proyecto usa ``--import-mode=importlib``, que no añade la raiz del
repositorio a ``sys.path``. Sin esto, ``uv run pytest experiments/adr001``
no podria importar ``experiments.adr001``. No altera la configuracion de
pruebas de Sirius 0.1: vive dentro de la ruta experimental autorizada y
solo se carga cuando se lanzan estas pruebas.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
