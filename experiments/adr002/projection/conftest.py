"""Hace importable el paquete ``experiments`` al ejecutar estas pruebas.

Mismo patron que ``experiments/adr002/candidates/conftest.py``. El proyecto usa
``--import-mode=importlib``, que no anade la raiz del repositorio a
``sys.path``. Sin esto, ``uv run pytest experiments/adr002/projection`` no
podria importar ``experiments.adr002.projection``.

No altera la configuracion de pruebas de Sirius 0.1: vive dentro de la ruta
experimental autorizada y solo se carga al lanzar estas pruebas.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
