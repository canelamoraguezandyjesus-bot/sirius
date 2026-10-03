"""Un aviso se reproduce si el detector de hoy ve SU fichero y SU tramo (Codex, PR #665, ronda 8).

Contar como reproducido un aviso porque el detector encuentra cualquier familia
en el historial no sustentaba el «13 de 13» del informe: con varias familias en
una incidencia, un aviso cuyo fichero y tramo el detector de hoy ya no ve
contaba igual. `coinciden` compara evidencia a evidencia.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

RAIZ = Path(__file__).resolve().parents[2]
MINA = RAIZ / "scripts" / "mina"


def _cargar(nombre: str) -> ModuleType:
    if str(MINA) not in sys.path:
        sys.path.insert(0, str(MINA))
    spec = importlib.util.spec_from_file_location(nombre, MINA / f"{nombre}.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


ra = _cargar("reproducir_avisos")


def test_un_aviso_se_reproduce_solo_si_cada_evidencia_tiene_hoy_su_fichero_y_su_tramo() -> None:
    publicadas = (("src/x.py", (1, 2, 3)),)
    assert ra.coinciden(publicadas, [("src/x.py", (1, 2, 3))]), "mismo fichero, mismo tramo"
    assert ra.coinciden(publicadas, [("src/x.py", (1, 2, 3, 4))]), "el de hoy contiene el publicado"
    assert not ra.coinciden(publicadas, [("src/x.py", (2, 3, 4))]), (
        "ronda 9 de Codex: solapar no basta; hoy ya no se ve la ronda 1 que el aviso publico"
    )
    assert not ra.coinciden(publicadas, [("src/y.py", (1, 2, 3))]), "otra familia no reproduce esta"
    assert not ra.coinciden(publicadas, [("src/x.py", (5, 6, 7))]), "otro tramo del mismo fichero"
    assert not ra.coinciden((), [("src/x.py", (1, 2, 3))]), "un aviso sin evidencias no afirma nada"

    dos = (("src/x.py", (1, 2, 3)), ("src/y.py", (4, 5, 6)))
    assert ra.coinciden(dos, [("src/x.py", (1, 2, 3)), ("src/y.py", (4, 5, 6, 7))])
    assert not ra.coinciden(dos, [("src/x.py", (1, 2, 3))]), "cada evidencia publicada, no alguna"
