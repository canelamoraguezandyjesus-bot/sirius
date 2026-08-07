"""La adjudicación de cierre: que no mida, y que no perdone.

Lo que estas pruebas vigilan es que el cierre **no pueda declarar conforme a
nadie por descuido**. Una adjudicación que agrega obligaciones y devuelve un
booleano es exactamente donde un aprobado se cuela: basta olvidar una en la
conjunción para que el resultado suba sin que nadie lo note.

Por eso hay una prueba que exige que **toda** obligación declarada entre en el
veredicto, escrita de forma que falle si alguien añade una y olvida sumarla.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any, Final

from experiments.adr002.round import closure as cl

RAIZ: Final = Path(__file__).resolve().parents[3]


def _veredicto(**cambios: Any) -> cl.Veredicto:
    """Un veredicto que cumple todo, salvo lo que se le cambie."""
    base = {
        "participante": "X",
        "contaminacion_cero": True,
        "fuga_de_ambito_cero": True,
        "confusion_de_polaridad_cero": True,
        "conformidad_de_etapa": True,
        "borrado_y_regeneracion": True,
        "recall_critico_completo": True,
        "omisiones_criticas": 0,
        "casos_con_omision_critica": (),
        "marcado_de_m2_completo": True,
    }
    return cl.Veredicto(**{**base, **cambios})


# ---------------------------------------------------------------------------
# A. No mide
# ---------------------------------------------------------------------------


def test_el_cierre_no_ejecuta_ni_cronometra_nada() -> None:
    """Adjudica lo medido. Si midiera, sería otra corrida sin acta."""
    fuente = (RAIZ / "experiments/adr002/round/closure.py").read_text(encoding="utf-8")
    sin_docstrings = re.sub(r'"""(?:.|\n)*?"""', "", fuente)
    for prohibido in ("engine.recuperar", "PuertoSqlite", "construir_desde_la_familia"):
        assert prohibido not in sin_docstrings, prohibido
    for prohibido in ("perf_counter", "monotonic(", "timeit"):
        assert prohibido not in sin_docstrings, prohibido


# ---------------------------------------------------------------------------
# B. Ninguna obligación puede quedarse fuera del veredicto
# ---------------------------------------------------------------------------


def test_toda_obligacion_declarada_entra_en_el_veredicto() -> None:
    """La prueba que impide el aprobado por olvido.

    Recorre **cada** campo booleano del veredicto y comprueba que ponerlo en
    falso basta para dejar de ser conforme. Si alguien añadiese una obligación
    y olvidase sumarla a la conjunción, este recorrido lo diría, porque el
    campo existiría y no cambiaría nada.
    """
    booleanos = [
        campo.name
        for campo in dataclasses.fields(cl.Veredicto)
        if campo.type is bool
        or campo.name.endswith(("_cero", "_completo", "_etapa", "_regeneracion"))
    ]
    assert len(booleanos) >= 7, booleanos
    for campo in booleanos:
        incumple = _veredicto(**{campo: False})
        assert not incumple.conforme, f"{campo} no entra en la conjuncion del veredicto"
        assert incumple.incumplimientos, campo


def test_conforme_exige_todas_y_ninguna_media_compensa() -> None:
    assert _veredicto().conforme
    assert not _veredicto(recall_critico_completo=False).conforme
    assert not _veredicto(marcado_de_m2_completo=False).conforme


# ---------------------------------------------------------------------------
# C. B04-M01: el umbral es cero, y no se negocia
# ---------------------------------------------------------------------------


def test_una_sola_omision_critica_basta_para_incumplir() -> None:
    """`§14 R1`: «una omisión crítica reproducible elimina la alternativa»."""
    assert cl.UMBRAL_DE_RECALL_CRITICO == 0
    uno = _veredicto(recall_critico_completo=False, omisiones_criticas=1)
    assert not uno.conforme
    assert "recall_critico_B04_M01" in uno.incumplimientos


def test_las_omisiones_se_leen_de_la_evidencia_y_no_se_recalculan() -> None:
    """Contarlas otra vez sería medir de nuevo, y con otro criterio."""
    evidencia = {
        "veredictos": {
            "X": [
                {"caso": "N1-01", "adjudicable": True, "criticos_pendientes": ["DECISION:3"]},
                {"caso": "N1-02", "adjudicable": True, "criticos_pendientes": []},
                #: Un caso no adjudicable no cuenta, ni para bien ni para mal.
                {"caso": "N1-03", "adjudicable": False, "criticos_pendientes": ["MEMORIA:9"]},
            ]
        }
    }
    total, casos = cl.omisiones_criticas_por_caso(evidencia, "X")
    assert total == 1
    assert casos == ("N1-01",)


def test_el_cierre_cita_la_norma_que_aplica_y_dice_por_que_faltaba() -> None:
    assert "B04-M01" in cl.CITA_M01
    assert "100% por caso" in cl.CITA_M01
    assert "elimina la alternativa" in cl.CITA_M01
    assert "criticos_pendientes_total" in cl.POR_QUE_NO_ESTABA


# ---------------------------------------------------------------------------
# D. El control no puede aprobar el marcado por no publicarlo
# ---------------------------------------------------------------------------


def test_quien_no_publica_marca_no_acredita_el_marcado() -> None:
    """No es un aprobado por omisión: es que no hay marca que leer."""
    normativo = {
        "conformidad": {
            "T0-control": {
                "puertas": {
                    "contaminacion_cero": True,
                    "fuga_de_ambito_cero": True,
                    "confusion_de_polaridad_cero": True,
                    "conformidad_de_etapa": True,
                    "borrado_y_regeneracion": True,
                }
            }
        }
    }
    evidencia: dict[str, Any] = {"veredictos": {"T0-control": []}}
    marcado = {"por_participante": {"T0-control": {"medible": False, "razon": "sin explicacion"}}}
    veredicto = cl.adjudicar(normativo, evidencia, {"por_participante": {}}, marcado)[0]
    assert not veredicto.marcado_de_m2_completo
    assert not veredicto.conforme


# ---------------------------------------------------------------------------
# E. Lo común no separa alternativas, y el artefacto lo dice
# ---------------------------------------------------------------------------


def test_lo_que_incumplen_los_cuatro_se_declara_como_condicion_de_cierre() -> None:
    veredictos = [
        _veredicto(participante=nombre, recall_critico_completo=False, omisiones_criticas=16)
        for nombre in ("ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D")
    ]
    documento = cl.documento(veredictos)
    assert documento["incumplimientos_comunes_a_los_cuatro"] == ["recall_critico_B04_M01"]
    assert "no separa alternativas" in documento["que_significa_lo_comun"]
    assert documento["ninguno_conforme"] is True


def test_una_obligacion_que_solo_falla_uno_no_es_comun() -> None:
    """Distinguir lo común de lo propio es lo que hace útil el cierre."""
    veredictos = [
        _veredicto(participante="ADR002-A"),
        _veredicto(participante="ADR002-B", confusion_de_polaridad_cero=False),
        _veredicto(participante="ADR002-C"),
        _veredicto(participante="ADR002-D"),
    ]
    documento = cl.documento(veredictos)
    assert documento["incumplimientos_comunes_a_los_cuatro"] == []


# ---------------------------------------------------------------------------
# F. El contraste que hace comprobable que la corrección no movió nada
# ---------------------------------------------------------------------------


def test_el_contraste_detecta_una_conformidad_que_se_movio() -> None:
    """Si una cifra hubiera cambiado, el paquete no habría sido de presentación."""
    actual = {"conformidad": {"X": {"casos_con_resultado_exacto": 23, "puertas": {}}}}
    igual = {"conformidad": {"X": {"casos_con_resultado_exacto": 23, "puertas": {}}}}
    distinta = {"conformidad": {"X": {"casos_con_resultado_exacto": 24, "puertas": {}}}}
    assert cl.contraste_de_conformidad(actual, igual)["conformidad_identica"]
    contraste = cl.contraste_de_conformidad(actual, distinta)
    assert not contraste["conformidad_identica"]
    assert "X" in contraste["diferencias"]


# ---------------------------------------------------------------------------
# G. El artefacto publicado
# ---------------------------------------------------------------------------


def test_el_artefacto_de_cierre_no_elige_alternativa() -> None:
    ruta = RAIZ / cl.SALIDA
    if not ruta.exists():
        return
    documento = json.loads(ruta.read_text(encoding="utf-8"))
    assert documento["estado"] == "ADJUDICACION"
    assert "no_elige" in documento
    assert documento["obligacion_adjudicada_por_primera_vez"]["identificador"] == "B04-M01"
