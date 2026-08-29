"""Toda afirmación comprobable de la Arquitectura Técnica 0.2 cita fichero y
línea reales (ADR-001), incidencia #415.

Esta prueba no comprueba que cada cita diga la verdad sobre el código citado
—eso es exactamente lo que la disciplina de evidencia deja al criterio
humano, no a una máquina—, sino la comprobación mecánica que sí es posible:
que el fichero citado existe en el árbol y que el rango de líneas citado cabe
dentro de su tamaño real. Mirrors ``tests/unit/test_documentation_single_source.py``:
fija la disposición que hace posible mantener el documento correcto, no su
contenido semántico.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

DOCUMENTO = REPO_ROOT / "docs" / "evolution" / "SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md"

# Una cita de fichero:línea o fichero:línea-línea entre backticks, p. ej.
# `src/sirius/domain/precedence.py:123-192` o `AGENTS.md:68`.
CITA = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|md)):(\d+)(?:-(\d+))?`")


def _texto() -> str:
    return DOCUMENTO.read_text(encoding="utf-8")


def test_el_documento_existe() -> None:
    assert DOCUMENTO.is_file()


@pytest.mark.parametrize(
    "encabezado",
    [
        "## 3. Sugerencias confirmadas",
        "## 4. Conflictos asistidos",
        "## 5. Proyectos históricos consultables",
        "## 6. Búsqueda mejorada y Mejor recuperación",
        "## 7. Impactos transversales",
        "## 8. Orden de construcción propuesto",
        "## 9. Decisiones pendientes del propietario",
    ],
)
def test_el_documento_cubre_los_bloques_del_encargo(encabezado: str) -> None:
    assert encabezado in _texto(), (
        f"Falta la sección «{encabezado}» que exige la incidencia #415 "
        f"({DOCUMENTO.relative_to(REPO_ROOT)})."
    )


def _citas() -> list[tuple[str, int, int | None]]:
    return [
        (ruta, int(inicio), int(fin) if fin else None)
        for ruta, inicio, fin in CITA.findall(_texto())
    ]


def test_hay_citas_de_fichero_y_linea() -> None:
    citas = _citas()
    assert len(citas) >= 50, (
        f"Solo se encontraron {len(citas)} citas de fichero:línea; el objetivo de "
        "la incidencia #415 exige citar fichero y línea en cada afirmación "
        "comprobable (ADR-001)."
    )


@pytest.mark.parametrize("cita", _citas(), ids=lambda c: f"{c[0]}:{c[1]}")
def test_cada_cita_resuelve_dentro_del_fichero_real(
    cita: tuple[str, int, int | None],
) -> None:
    ruta, inicio, fin = cita
    fichero = REPO_ROOT / ruta
    assert fichero.is_file(), f"La cita `{ruta}:{inicio}` señala un fichero que no existe."

    total_lineas = len(fichero.read_text(encoding="utf-8").splitlines())
    ultima_linea_citada = fin if fin is not None else inicio
    assert 1 <= inicio <= total_lineas, (
        f"`{ruta}:{inicio}` cita una línea fuera de rango (el fichero tiene {total_lineas} líneas)."
    )
    assert ultima_linea_citada <= total_lineas, (
        f"`{ruta}:{inicio}-{fin}` cita un rango que excede el fichero ({total_lineas} líneas)."
    )
    if fin is not None:
        assert inicio <= fin, f"`{ruta}:{inicio}-{fin}` tiene un rango invertido."


def test_el_documento_no_toca_docs_canonical_como_alcance_propio() -> None:
    """El alcance permitido de la incidencia #415 prohíbe modificar
    ``docs/canonical/``; esta prueba no puede comprobar la intención, pero sí
    que el documento nuevo vive fuera de ese árbol."""
    assert "docs/canonical" not in str(DOCUMENTO.relative_to(REPO_ROOT)).replace("\\", "/")
