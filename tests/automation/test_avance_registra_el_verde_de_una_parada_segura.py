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


def test_la_transicion_retira_la_etiqueta_de_origen_no_una_fija() -> None:
    guion = _sin_comentarios(_paso_de_avance())
    assert guion.count('"${origen_de[$issue_number]}"') >= 2, (
        "las transiciones tienen que retirar la etiqueta de ORIGEN de cada "
        "incidencia (ci-pending o failed-safely); retirar siempre ci-pending "
        "dejaría failed-safely puesta junto a review-requested, un estado doble "
        "que la máquina de estados no contempla"
    )
