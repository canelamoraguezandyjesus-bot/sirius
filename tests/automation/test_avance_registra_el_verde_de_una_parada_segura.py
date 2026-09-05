"""H-34: un verde de Quality durante `failed-safely` no puede quedar mudo.

Le pasó dos veces la noche del 30 al 31 de agosto (#435 y #442): la incidencia
estaba en `sirius:failed-safely`, un update-branch disparó Quality de nuevo, el
run terminó en verde… y nadie lo registró, porque `advance-sirius-after-quality`
buscaba candidatas ÚNICAMENTE en `sirius:ci-pending`. La cura manual fue
cirugía de etiquetas (reponer `ci-pending` y relanzar el run) — dos veces.

El arreglo: el resultado VERDE también considera candidatas en
`sirius:failed-safely` y las revive hacia revisión, retirando la etiqueta de
ORIGEN que corresponda; un resultado ROJO sigue actuando solo sobre
`ci-pending` (revivir una parada segura hacia corrección sería tomar una
decisión, no registrar un resultado).

Como el resto de guardianes de esta casa, se comprueba el guion SIN sus
comentarios: que algo esté NOMBRADO en un comentario no es que esté HECHO
(la lección de `test_corrector_ante_fallo_de_ci.py`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
AVANCE = RAIZ / ".github" / "workflows" / "advance-sirius-after-quality.yml"


def _doc() -> dict[Any, Any]:
    return dict(yaml.safe_load(AVANCE.read_text(encoding="utf-8")))


def _paso_de_avance() -> str:
    for job in (_doc().get("jobs") or {}).values():
        for paso in job.get("steps") or []:
            if "Advance" in str(paso.get("name", "")):
                return str(paso.get("run", ""))
    raise AssertionError("no encontré el paso de avance en advance-sirius-after-quality.yml")


def _sin_comentarios(guion: str) -> str:
    return "\n".join(linea for linea in guion.splitlines() if not linea.lstrip().startswith("#"))


def test_las_candidatas_incluyen_la_parada_segura() -> None:
    guion = _sin_comentarios(_paso_de_avance())
    assert '"sirius:ci-pending" "sirius:failed-safely"' in guion, (
        "el avance vuelve a buscar candidatas solo en ci-pending: un verde de "
        "Quality durante failed-safely quedaría otra vez sin registrar (H-34)"
    )


def test_un_resultado_rojo_no_revive_una_parada_segura() -> None:
    guion = _sin_comentarios(_paso_de_avance())
    assert (
        '[ "$etiqueta_origen" = "sirius:failed-safely" ] && [ "$CONCLUSION" != "success" ]' in guion
    ), (
        "falta la guarda que excluye failed-safely cuando el resultado no es "
        "verde: un rojo revivría una parada segura hacia corrección, que es una "
        "decisión y no un registro"
    )


def test_la_transicion_de_exito_retira_las_tres_etiquetas_fuente() -> None:
    """PR #477 rondas 3-5: las etiquetas-fuente van como removes (CSV) DENTRO
    de la transición verificada — retirar una ausente se tolera, y el estado
    no puede quedar con una fuente conviviendo con review-requested ni en
    primera ejecución ni en reintento. Re-anclada a conciencia con ADR-142:
    el tercer origen (`ready-for-merge`, deuda 10) entra en el mismo CSV por
    la misma razón — una aprobación caducada no puede convivir con la
    revisión repuesta."""
    guion = _sin_comentarios(_paso_de_avance())
    assert '"sirius:ci-pending,sirius:failed-safely,sirius:ready-for-merge"' in guion, (
        "la transición de éxito ya no retira las tres etiquetas-fuente en su "
        "verificación: una transición parcial anterior dejaría una fuente "
        "falsa conviviendo con el estado activo"
    )


def test_la_ambiguedad_nunca_pone_y_quita_failed_safely() -> None:
    """PR #477 ronda 5 (P1): si el origen ya era failed-safely, la parada
    ambigua no puede retirarla a la vez que la pone — la verificación del
    helper fallaría y la incidencia quedaría sin su etiqueta de parada."""
    guion = _sin_comentarios(_paso_de_avance())
    assert "remueve_ambiguedad" in guion
    assert 'remueve_ambiguedad=""' in guion


def test_una_incidencia_con_las_dos_etiquetas_cuenta_una_sola_vez() -> None:
    """PR #477 ronda 3 (P2): una transición parcial anterior puede dejar las
    dos etiquetas; contarla dos veces fabricaría una falsa ambigüedad y la
    parada segura intentaría poner y quitar failed-safely a la vez."""
    guion = _sin_comentarios(_paso_de_avance())
    assert "origen_de[$n]" in guion, (
        "desapareció la deduplicación por número de incidencia: una "
        "incidencia con las dos etiquetas se contaría dos veces (falsa "
        "ambigüedad)"
    )


def test_la_retirada_de_la_sobrante_es_reintentable() -> None:
    """PR #477 ronda 4 (P2): si la limpieza falla, el paso queda en rojo
    reintentable — no un warning que deja failed-safely como parada falsa
    junto a review-requested."""
    guion = _sin_comentarios(_paso_de_avance())
    assert "No se pudo listar las incidencias" in guion, (
        "la consulta de candidatas volvió a tragarse el fallo del productor "
        "(mapfile en sustitución de proceso): una lectura caída se "
        "convertiría en «no hay candidatas» y el verde se consumiría mudo"
    )


def test_una_lectura_caida_del_candidato_es_reintentable() -> None:
    """PR #477 ronda 6 (P1): la URL de la PR vive en los comentarios; una
    lectura caída no es «no referencia ninguna PR» — descartar al candidato
    consumiría el evento de un solo disparo con la incidencia parada."""
    guion = _sin_comentarios(_paso_de_avance())
    assert "lectura-candidato-fallida" in guion
