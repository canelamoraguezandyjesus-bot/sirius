"""Los orígenes que la ruta de avance acepta, fijados (ADR-142, deuda 10).

La lógica de selección vive en bash dentro de
`.github/workflows/advance-sirius-after-quality.yml`, así que estas pruebas
la fijan sobre el texto, igual que `test_recon_stuck_007` fija el cron del
reconciliador: no ejecutan el workflow, impiden que una edición le quite sin
querer un origen, una puerta de solo-verdes o el guard de aprobación
vigente. El porqué de cada pieza está en ADR-142; el desglose de los dos
rebotes del 04-09 que motivan el origen nuevo, en la bitácora del ciclo
(entradas 25 y 29).
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
AVANCE = RAIZ / ".github" / "workflows" / "advance-sirius-after-quality.yml"


def _texto() -> str:
    return AVANCE.read_text(encoding="utf-8")


def test_los_tres_origenes_estan_en_el_bucle_de_candidatas() -> None:
    """H-34 dejó dos orígenes (`ci-pending`, `failed-safely`); ADR-142 añade
    `ready-for-merge` para que una aprobación caducada por el avance de main
    vuelva sola a revisión (bitácora, entradas 25 y 29: dos veces el 04-09
    a mano)."""
    encontrado = re.search(
        r"for etiqueta_origen in ([^\n]+); do",
        _texto(),
    )
    assert encontrado, "el bucle de orígenes de candidatas ya no existe con esa forma"
    origenes = encontrado.group(1)
    assert '"sirius:ci-pending"' in origenes
    assert '"sirius:failed-safely"' in origenes
    assert '"sirius:ready-for-merge"' in origenes


def test_los_origenes_de_revivir_solo_aceptan_verdes() -> None:
    """Un rojo solo actúa sobre `ci-pending`: revivir una parada segura o
    degradar una aprobación por un rojo sería tomar una decisión, no
    registrar un resultado (la doctrina de H-34, extendida por ADR-142)."""
    texto = _texto()
    for origen in ("sirius:failed-safely", "sirius:ready-for-merge"):
        patron = (
            r'if \[ "\$etiqueta_origen" = "' + re.escape(origen) + r'" \] '
            r'&& \[ "\$CONCLUSION" != "success" \]; then\n\s*continue'
        )
        assert re.search(patron, texto), f"el origen {origen} ya no tiene su puerta de solo-verdes"


def test_el_verde_retira_las_tres_etiquetas_fuente() -> None:
    """La transición verificada retira las etiquetas-fuente por CSV; si
    `ready-for-merge` no está en esa lista, una incidencia revivida quedaría
    con la aprobación caducada y la revisión nueva conviviendo."""
    assert '"noclose" "sirius:ci-pending,sirius:failed-safely,sirius:ready-for-merge"' in _texto()


def test_una_aprobacion_vigente_para_el_mismo_head_no_se_destruye() -> None:
    """El guard que mi receta manual no necesitaba y el workflow sí: si el
    head verde ES el aprobado (p. ej. un re-run de Quality sobre el head ya
    aprobado), reponer la revisión destruiría una aprobación válida y
    costaría una ronda entera. Con aprobación vigente, no se toca nada."""
    assert "sirius-verdict:reviewer:approved:${HEAD_SHA}" in _texto()
