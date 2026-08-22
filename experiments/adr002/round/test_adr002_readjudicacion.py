"""La readjudicación: que corrija el criterio y **no** toque la medición.

Lo que estas pruebas vigilan no es que los números suban, sino que suban por la
razón declarada y que las cifras publicadas sigan donde estaban. Una
readjudicación que reescribiese la medición sería lo que el §8.1 prohíbe, con
otro nombre.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from experiments.adr002.round import readjudication as rj

RAIZ: Final = Path(__file__).resolve().parents[3]


def _cargar(ruta: str) -> dict[str, Any]:
    return json.loads((RAIZ / ruta).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# A. No mide, y se puede comprobar
# ---------------------------------------------------------------------------


def test_la_readjudicacion_no_ejecuta_ninguna_consulta() -> None:
    """Persigue actos: ni motor, ni puerto, ni proyección, ni cronómetro."""
    fuente = (RAIZ / "experiments/adr002/round/readjudication.py").read_text(encoding="utf-8")
    import re

    sin_docstrings = re.sub(r'"""(?:.|\n)*?"""', "", fuente)
    for prohibido in ("engine.recuperar", "PuertoSqlite", "construir_desde_la_familia"):
        assert prohibido not in sin_docstrings, prohibido
    for prohibido in ("perf_counter(", "monotonic(", "timeit"):
        assert prohibido not in sin_docstrings, prohibido


def test_las_cifras_publicadas_siguen_donde_estaban() -> None:
    """§8.1: la medición no se reescribe, ni siquiera para corregirla bien."""
    for version, contaminacion, etapa in (("v0.1", 5, 30), ("v0.2", 3, 32)):
        publicado = _cargar(f"artifacts/adr002_round/ronda_primaria_{version}.json")
        assert publicado["conformidad"]["ADR002-A"]["contaminacion_total"] == contaminacion
        assert publicado["conformidad"]["ADR002-A"]["casos_con_etapa_conforme"] == etapa


def test_el_artefacto_declara_que_no_es_una_medicion() -> None:
    documento = _cargar(rj.SALIDA)
    assert documento["estado"] == "READJUDICACION"
    assert "no se ejecuto ninguna consulta" in documento["no_es_una_medicion"]
    assert "no elige alternativa" in documento["no_elige"]


# ---------------------------------------------------------------------------
# B. Cada resolución, con su cita y su efecto
# ---------------------------------------------------------------------------


def test_cada_resolucion_lleva_su_cita_del_canon() -> None:
    """Aflojar un control sin citar el canon sería aflojarlo por conveniencia."""
    for cita in rj.NO_ADJUDICABLES_ANADIDOS.values():
        assert "B04" in cita and len(cita) > 60
    for _ids, cita in rj.PROHIBIDOS_RETIRADOS.values():
        assert "B04" in cita and "Permite" in cita


def test_retirar_un_prohibido_solo_alcanza_a_su_caso() -> None:
    """`DECISION:3` deja de contaminar en `CA-05` y en ningún otro sitio."""
    ids, _ = rj.PROHIBIDOS_RETIRADOS["B04-CA-05"]
    assert ids == ("DECISION:3",)
    assert len(rj.PROHIBIDOS_RETIRADOS) == 1


def test_la_contaminacion_de_los_cuatro_queda_en_cero() -> None:
    """Las tres que quedaban eran las dos declaradas no corregibles."""
    documento = _cargar(rj.SALIDA)
    for candidato in ("ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D"):
        fila = documento["por_participante"][candidato]
        assert fila["contaminacion_publicada"] == 3, candidato
        assert fila["contaminacion_readjudicada"] == 0, candidato
        assert fila["contaminacion_cero"] is True, candidato


def test_el_control_sigue_contaminando() -> None:
    """Retirar dos casos no absuelve a `T0`: su contaminación es de otra clase."""
    documento = _cargar(rj.SALIDA)
    assert documento["por_participante"]["T0-control"]["contaminacion_readjudicada"] > 0


# ---------------------------------------------------------------------------
# C. La cota de etapa, y la guarda que le faltaba
# ---------------------------------------------------------------------------


def test_resolver_antes_de_lo_declarado_conforma() -> None:
    """«Solo se expande cuando falta suficiencia»: parar pronto es obedecer."""
    assert rj.etapa_conforme_por_cota(
        ("E0", "E1", "E5"), "E4", "resuelto en E1, como el caso declara"
    )


def test_resolver_despues_de_lo_declarado_no_conforma() -> None:
    """Expandir de más sí es incumplir: la cota es cota, no vía libre."""
    assert not rj.etapa_conforme_por_cota(
        ("E0", "E1", "E2", "E5"), "E1", "resuelto en E2 y el caso declara E1"
    )


def test_saltarse_una_etapa_sigue_sin_conformar() -> None:
    assert not rj.etapa_conforme_por_cota(
        ("E0", "E1", "E3", "E5"), "E3", "resuelto en E3, como el caso declara"
    )


def test_sin_etapas_no_se_conforma_por_vacio() -> None:
    """La guarda que faltaba: el control pasaba de 0/46 a 46/46 sin ella.

    Una métrica que premia **no tener** el mecanismo es peor que una que lo
    mide mal, y esta lo premiaba: sin etapas, «sin saltos» se cumple solo.
    """
    assert not rj.etapa_conforme_por_cota((), "E1", "")
    documento = _cargar(rj.SALIDA)
    assert documento["por_participante"]["T0-control"]["etapa_readjudicada"] == 0


def test_la_conformidad_de_etapa_sube_pero_no_llega() -> None:
    """Sube porque el criterio era estricto de más; no llega porque quedan casos reales."""
    documento = _cargar(rj.SALIDA)
    for candidato, esperado in (("ADR002-A", 43), ("ADR002-C", 43), ("ADR002-B", 41)):
        fila = documento["por_participante"][candidato]
        assert fila["etapa_readjudicada"] == esperado, candidato
        assert fila["etapa_readjudicada"] > fila["etapa_publicada"], candidato
        assert fila["conformidad_de_etapa"] is False, candidato


def test_el_orden_entre_los_candidatos_no_cambia() -> None:
    """Lo que decide la recomendación sigue decidiéndola igual."""
    documento = _cargar(rj.SALIDA)
    por = documento["por_participante"]
    for mejor in ("ADR002-A", "ADR002-C"):
        for peor in ("ADR002-B", "ADR002-D"):
            assert por[mejor]["etapa_readjudicada"] > por[peor]["etapa_readjudicada"]
    assert por["ADR002-A"]["etapa_readjudicada"] == por["ADR002-C"]["etapa_readjudicada"]


def test_lo_que_el_canon_exige_y_nadie_mide_queda_declarado() -> None:
    """Callar una carencia propia la convierte en una cifra que nadie ve."""
    documento = _cargar(rj.SALIDA)
    pendiente = " ".join(documento["pendiente_de_medir"])
    assert "M2" in pendiente
    assert "marcado" in pendiente
