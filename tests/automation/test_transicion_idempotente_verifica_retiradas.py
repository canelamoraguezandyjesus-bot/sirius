"""PR #477 ronda 7 (P2): la salida idempotente de `sirius_transition` no puede
certificar una transición cuyo `remove_csv` sigue puesto — dejaría una parada
falsa (p. ej. `failed-safely`) conviviendo con el estado activo para siempre,
sin que ningún reintento la sanara."""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
LIBRERIA = RAIZ / "scripts" / "automation" / "sirius_issue.sh"


def _cuerpo_de_sirius_transition() -> str:
    texto = LIBRERIA.read_text(encoding="utf-8")
    inicio = texto.index("sirius_transition()")
    fin = texto.index("Etiqueta terminal garantizada", inicio)
    return texto[inicio:fin]


def test_la_salida_idempotente_comprueba_las_retiradas() -> None:
    tramo = _cuerpo_de_sirius_transition()
    sin_comentarios = "\n".join(
        linea for linea in tramo.splitlines() if not linea.lstrip().startswith("#")
    )
    assert "remove_csv" in sin_comentarios, (
        "la verificación del marcador presente ya no comprueba las etiquetas "
        "de remove_csv: una transición parcial quedaría certificada como "
        "completa con la parada falsa aún puesta"
    )
