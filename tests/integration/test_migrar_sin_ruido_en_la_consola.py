"""Migrar al arrancar no pinta las líneas de Alembic en la consola (ADR-252).

Sirius migra la base cada vez que arranca, y el registro de alembic.ini, el de su línea de
órdenes, pintaba en la consola «INFO [alembic.runtime.migration] …». Ahora Sirius migra sin
él, y lo que servía, que el esquema cambió, queda en su diario. Se mira en un Python aparte,
que el registro de Alembic es de todo el proceso.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from sirius.adapters.persistence.migrations import get_supported_schema_version

pytestmark = pytest.mark.integration

_SIRIUS_MIGRA = """
import logging
import sys
from pathlib import Path

from sirius.adapters.persistence.migrations import upgrade_to_head

diario = logging.getLogger("sirius")
diario.setLevel(logging.INFO)
diario.addHandler(logging.StreamHandler(sys.stdout))
upgrade_to_head(Path(sys.argv[1]))
upgrade_to_head(Path(sys.argv[1]))
print("raíz:", len(logging.getLogger().handlers))
"""

_LA_LINEA_DE_ORDENES_MIGRA = """
import sys

from alembic import command
from alembic.config import Config

from sirius.adapters.persistence.migrations import _resource_root

raiz = _resource_root()
config = Config(str(raiz / "alembic.ini"))
config.set_main_option("script_location", str(raiz / "migrations"))
config.set_main_option("sqlalchemy.url", f"sqlite:///{sys.argv[1]}")
command.upgrade(config, "head")
"""


def _corre(guion: str, base: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", guion, str(base)],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )


def test_sirius_migra_sin_pintar_alembic_y_apunta_el_cambio_de_esquema(tmp_path: Path) -> None:
    salida = _corre(_SIRIUS_MIGRA, tmp_path / "sirius.db")

    assert salida.stderr == ""
    # Una vez, la que cambió; la segunda no cambia nada. Y sin manejadores nuevos.
    assert salida.stdout.splitlines() == [
        f"La base pasa del esquema vacío al {get_supported_schema_version()}",
        "raíz: 0",
    ]


def test_la_linea_de_ordenes_de_alembic_sigue_con_su_registro(tmp_path: Path) -> None:
    salida = _corre(_LA_LINEA_DE_ORDENES_MIGRA, tmp_path / "sirius.db")

    assert "INFO  [alembic.runtime.migration] Running upgrade" in salida.stderr
