"""El registro de evidencia no puede acreditar un resultado con una prueba que no existe.

La fila de B4e citaba `test_detect_precedence_conflicts_use_case.py`, que nunca
existió en el repositorio: el registro afirmaba una comprobación que nadie podía
reproducir. Una cita rota es peor que una ausencia, porque se lee como evidencia.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRO = REPO_ROOT / "docs" / "implementation" / "V8_EXECUTION.md"

NOMBRE_DE_PRUEBA = re.compile(r"`(test_[a-z0-9_]+\.py)`")

# Pruebas citadas por filas históricas y retiradas después de forma legítima.
# La lista EXIME, no afirma: cada entrada necesita su motivo escrito, para que
# la excepción sea una decisión y no un agujero por el que colar citas rotas.
HISTORICAS: dict[str, str] = {}


def test_toda_prueba_citada_en_el_registro_de_evidencia_existe() -> None:
    texto = REGISTRO.read_text(encoding="utf-8")
    citadas = sorted(set(NOMBRE_DE_PRUEBA.findall(texto)))
    assert citadas, (
        "El registro de evidencia dejó de citar pruebas: la extracción no encuentra nada."
    )

    ausentes = [
        nombre
        for nombre in citadas
        if nombre not in HISTORICAS and not list(REPO_ROOT.glob(f"tests/**/{nombre}"))
    ]

    assert not ausentes, (
        "El registro de evidencia acredita un resultado con pruebas que no existen: "
        f"{ausentes}. O la cita está mal, o la prueba se retiró sin anotarlo en HISTORICAS."
    )
