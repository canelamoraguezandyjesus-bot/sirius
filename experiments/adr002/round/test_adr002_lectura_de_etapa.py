"""Las dos lecturas de la conformidad de etapa, la publicada y la canónica.

El §3 de `SIRIUS_0.2_ADR_002_TRES_PREGUNTAS_ABIERTAS_RESUELTAS_CONTRA_EL_CANON_v1.0.md`
encontró que la métrica publicada exige `origen == etapa declarada`, y que el
canon es más laxo: `B04` autoriza expandir **solo por insuficiencia**, de modo
que resolver en `E1` cuando `E1` basta es obediencia y no incumplimiento.

Las cifras publicadas **no se corrigen** —cambiar una medición después de verla
es lo que el §8.1 prohíbe—, así que aquí conviven las dos lecturas: se comprueba
que la publicada sigue siendo la que se publicó, que la canónica da lo que el
documento afirma, y —lo que de verdad importa— que **el orden entre los cuatro
candidatos no depende de cuál se use**.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

RAIZ: Final = Path(__file__).resolve().parents[3]
EVIDENCIA: Final = RAIZ / "artifacts/adr002_round/ronda_primaria_v0.2_evidencia.json"
ARTEFACTO: Final = RAIZ / "artifacts/adr002_round/ronda_primaria_v0.2.json"

ORDEN: Final[tuple[str, ...]] = ("E0", "E1", "E2", "E3", "E4", "E5")
EXPANSION: Final[tuple[str, ...]] = ("E1", "E2", "E3", "E4")

#: Lo que el §3.1 del documento publica. Si alguna cambiara sin que el documento
#: cambie, una de las dos estaría mintiendo.
CANONICA_ESPERADA: Final[dict[str, int]] = {
    "T0-control": 0,
    "ADR002-A": 44,
    "ADR002-B": 42,
    "ADR002-C": 44,
    "ADR002-D": 42,
}


def _evidencia() -> dict[str, object]:
    return json.loads(EVIDENCIA.read_text(encoding="utf-8"))


def _conformidad_canonica(veredictos: list[dict], casos: dict[str, dict]) -> tuple[int, int]:
    """Sin salto y resuelto **en o antes** de la etapa declarada.

    Un participante que no recorre `E0-E5` **no conforma**: no conforma pronto,
    es que no hay política escalonada que juzgar. La primera versión de este
    cálculo daba `46/46` al control justamente por dejar pasar ese vacío, que es
    peor defecto que el que venía a corregir.
    """
    conformes = puntuables = 0
    for v in veredictos:
        if not v["adjudicable"] or not v["etapa_puntua"]:
            continue
        puntuables += 1
        if not v["etapas_recorridas"]:
            continue
        recorridas = [e for e in v["etapas_recorridas"] if e in EXPANSION]
        posiciones = [EXPANSION.index(e) for e in recorridas]
        sin_salto = posiciones == sorted(posiciones) and (
            not posiciones or posiciones == list(range(len(posiciones)))
        )
        declarada = casos[v["caso"]]["etapa_esperada"]
        razon = v["razon_de_etapa"]
        origen = razon.split("resuelto en ")[1][:2] if "resuelto en " in razon else None
        a_tiempo = (
            origen is None
            or declarada in ("E0", "E5")
            or ORDEN.index(origen) <= ORDEN.index(declarada)
        )
        conformes += sin_salto and a_tiempo
    return conformes, puntuables


def test_la_lectura_canonica_da_lo_que_el_documento_afirma() -> None:
    evidencia = _evidencia()
    casos = {c["caso"]: c for c in evidencia["casos"]}  # type: ignore[union-attr]
    for participante, lista in evidencia["veredictos"].items():  # type: ignore[union-attr]
        conformes, puntuables = _conformidad_canonica(lista, casos)
        assert puntuables == 46, participante
        assert conformes == CANONICA_ESPERADA[participante], participante


def test_el_control_no_conforma_por_no_tener_etapas() -> None:
    """Una métrica que premia no tener el mecanismo es peor que una que mide mal."""
    evidencia = _evidencia()
    casos = {c["caso"]: c for c in evidencia["casos"]}  # type: ignore[union-attr]
    conformes, _ = _conformidad_canonica(evidencia["veredictos"]["T0-control"], casos)  # type: ignore[index]
    assert conformes == 0


def test_la_lectura_publicada_no_se_ha_tocado() -> None:
    """§8.1: una medición no se reescribe después de verla, ni para mejorarla."""
    artefacto = json.loads(ARTEFACTO.read_text(encoding="utf-8"))
    publicadas = {p: c["casos_con_etapa_conforme"] for p, c in artefacto["conformidad"].items()}
    assert publicadas == {
        "T0-control": 0,
        "ADR002-A": 32,
        "ADR002-B": 30,
        "ADR002-C": 32,
        "ADR002-D": 30,
    }


def test_el_orden_entre_los_candidatos_no_depende_de_la_lectura() -> None:
    """Lo que decide la recomendación: la conclusión es la misma con las dos."""
    artefacto = json.loads(ARTEFACTO.read_text(encoding="utf-8"))
    candidatos = ("ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D")
    publicada = {p: artefacto["conformidad"][p]["casos_con_etapa_conforme"] for p in candidatos}
    canonica = {p: CANONICA_ESPERADA[p] for p in candidatos}
    for mejor in ("ADR002-A", "ADR002-C"):
        for peor in ("ADR002-B", "ADR002-D"):
            assert publicada[mejor] > publicada[peor], (mejor, peor)
            assert canonica[mejor] > canonica[peor], (mejor, peor)
    assert publicada["ADR002-A"] == publicada["ADR002-C"]
    assert canonica["ADR002-A"] == canonica["ADR002-C"]
