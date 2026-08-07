"""El marcado de `M2`: que se mida de verdad y no se apruebe en el vacío.

El riesgo de esta medición no es equivocar el veredicto: es **aprobar sin
presentarse**. Si ningún candidato devolviera un solo elemento no vigente,
«nunca lo presenta como actual» saldría en verde sin haberse comprobado nada.
Por eso hay una prueba dedicada a que los tres estados que `M2` nombra se
ejerciten realmente, y no basta con que la cifra final sea buena.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

from experiments.adr002.round import m2_marking as m2

RAIZ: Final = Path(__file__).resolve().parents[3]


def _artefacto() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads((RAIZ / m2.SALIDA).read_text(encoding="utf-8"))
    return datos


# ---------------------------------------------------------------------------
# A. No mide tiempo y no toca nada congelado
# ---------------------------------------------------------------------------


def test_el_marcado_no_cronometra_nada() -> None:
    for modulo in ("m2_marking.py", "execute_m2.py"):
        fuente = (RAIZ / f"experiments/adr002/round/{modulo}").read_text(encoding="utf-8")
        sin_docstrings = re.sub(r'"""(?:.|\n)*?"""', "", fuente)
        for prohibido in ("perf_counter", "monotonic(", "timeit"):
            assert prohibido not in sin_docstrings, f"{modulo}: {prohibido}"


def test_el_marcado_no_modifica_la_metrica_publicada() -> None:
    """`metrics.py` produjo las cifras de `v0.1` y `v0.2`. No se toca.

    La comprobación es de acto: este módulo no importa `metrics` ni lo llama.
    """
    fuente = (RAIZ / "experiments/adr002/round/m2_marking.py").read_text(encoding="utf-8")
    sin_docstrings = re.sub(r'"""(?:.|\n)*?"""', "", fuente)
    assert "import metrics" not in sin_docstrings
    assert "from experiments.adr002.round import metrics" not in sin_docstrings


# ---------------------------------------------------------------------------
# B. Lo que impide que esto sea un aprobado en el vacío
# ---------------------------------------------------------------------------


def test_los_tres_estados_de_m2_se_ejercitaron_de_verdad() -> None:
    """Sin esto, «nunca como actual» sería verde por no haber devuelto nada.

    Es la prueba que convierte un booleano en evidencia: los cuatro candidatos
    devolvieron elementos archivados, sustituidos **y** finalizados, y los tres
    volvieron marcados.
    """
    artefacto = _artefacto()
    for participante, resumen in artefacto["por_participante"].items():
        if not resumen["medible"]:
            continue
        assert resumen["los_tres_estados_se_ejercitaron"], (
            f"{participante}: solo se ejercitaron "
            f"{resumen['estados_historicos_ejercitados']}; sin los tres, M2.1 aprueba "
            f"sin presentarse"
        )
        assert resumen["no_vigentes_devueltos"] > 0, participante


def test_un_no_vigente_devuelto_como_vigente_se_detecta() -> None:
    """El control negativo: si la marca fuese falsa, se vería."""
    sustituida = m2.EstadoCanonico("DECISION:2", validez="SUSTITUIDA", disponibilidad="DISPONIBLE")
    assert not sustituida.es_vigente
    mal = m2.Marca("N1-01", "X", "DECISION:2", m2.MARCA_DE_VIGENTE, "aplicable a T; registrado R")
    bien = m2.Marca(
        "N1-01", "X", "DECISION:2", m2.MARCA_DE_NO_VIGENTE, "aplicable a T; registrado R"
    )
    assert m2.presentado_como_actual(mal, sustituida)
    assert not m2.presentado_como_actual(bien, sustituida)


def test_marcar_de_mas_no_cuenta_como_incumplimiento_de_m2() -> None:
    """`M2` prohíbe presentar lo viejo como actual, no lo contrario.

    Contar las dos direcciones haría que un candidato prudente de más pareciera
    incumplir la norma histórica, que dice otra cosa.
    """
    vigente = m2.EstadoCanonico("MEMORIA:1", validez="VIGENTE", disponibilidad="DISPONIBLE")
    prudente = m2.Marca(
        "N1-01", "X", "MEMORIA:1", m2.MARCA_DE_NO_VIGENTE, "aplicable a T; registrado R"
    )
    assert not m2.presentado_como_actual(prudente, vigente)


# ---------------------------------------------------------------------------
# C. Los ejes: vigente lo es en los dos, y lo purgado no es «histórico»
# ---------------------------------------------------------------------------


def test_archivado_no_es_actual_aunque_su_validez_sea_vigente() -> None:
    """Un archivado sigue siendo válido y ha dejado de ser actual."""
    archivada = m2.EstadoCanonico("MEMORIA:4", validez="VIGENTE", disponibilidad="ARCHIVADA")
    assert not archivada.es_vigente
    assert archivada.estado_que_m2_nombraria == "archivado"


def test_lo_purgado_no_se_nombra_vigente_ni_se_cuenta_como_fallo_de_marcado() -> None:
    """El defecto que tuvo la primera versión, fijado.

    `PURGADA` y `NO_GUARDADA` salían nombradas «vigente» a la vez que
    ``es_vigente`` las daba por no vigentes. Además no son estados históricos:
    si aparecen, el defecto es de contaminación, que es mucho más grave y lo
    mide la puerta 1.
    """
    for disponibilidad in ("PURGADA", "NO_GUARDADA"):
        estado = m2.EstadoCanonico("MEMORIA:9", validez="VIGENTE", disponibilidad=disponibilidad)
        assert not estado.es_recuperable
        assert estado.estado_que_m2_nombraria == "no recuperable"
        assert estado.estado_que_m2_nombraria not in m2.ESTADOS_QUE_M2_NOMBRA


def test_las_dos_marcas_temporales_se_exigen_por_separado() -> None:
    completa = m2.Marca("N1-01", "X", "MEMORIA:1", "vigente", "aplicable a T; registrado R")
    sin_registro = m2.Marca("N1-01", "X", "MEMORIA:1", "vigente", "aplicable a T")
    assert m2.separa_tiempo_valido_de_corte(completa)
    assert not m2.separa_tiempo_valido_de_corte(sin_registro)


# ---------------------------------------------------------------------------
# D. La obligación que no se cumple, y que es de la capa común
# ---------------------------------------------------------------------------


def test_una_sola_marca_de_no_vigencia_no_distingue_tres_estados() -> None:
    marcas = [
        m2.Marca("N1-01", "X", "DECISION:2", "no vigente", "t"),
        m2.Marca("N1-02", "X", "MEMORIA:4", "no vigente", "t"),
        m2.Marca("N1-03", "X", "MEMORIA:1", "vigente", "t"),
    ]
    distingue, razon = m2.distingue_los_tres_estados(marcas)
    assert not distingue
    assert "M3 y M4" in razon


def test_el_incumplimiento_de_m2_3_es_identico_en_los_cuatro() -> None:
    """No separa alternativas: es de la capa común, no de ningún candidato.

    Importa para el cierre: si el defecto fuese de un candidato, elegir otro lo
    evitaría. Siendo de la capa compartida, lo arrastraría cualquiera.
    """
    artefacto = _artefacto()
    medibles = {
        p: r["m2_3_distingue_los_tres_estados"]
        for p, r in artefacto["por_participante"].items()
        if r["medible"]
    }
    assert len(medibles) == 4
    assert set(medibles.values()) == {False}


def test_el_control_no_se_puede_medir_y_se_dice_por_que() -> None:
    """`T0` no publica explicación: no hay marca que leer, y se declara."""
    artefacto = _artefacto()
    control = artefacto["por_participante"]["T0-control"]
    assert control["medible"] is False
    assert "no publica explicacion" in control["razon"]


# ---------------------------------------------------------------------------
# E. Que observar de nuevo no haya cambiado ninguna cifra publicada
# ---------------------------------------------------------------------------


def test_la_observacion_declara_que_no_es_una_medicion_nueva() -> None:
    artefacto = _artefacto()
    assert "no_toca_nada_congelado" in artefacto
    assert "no_modifica_metrics" in artefacto
    assert artefacto["estado"] == "EVIDENCIA"


def test_las_divergencias_se_detectarian_si_las_hubiera() -> None:
    """El control que hace publicable esta observación, probado en negativo."""
    from experiments.adr002.round import execute_m2 as em

    publicado = {"N1-01": ("MEMORIA:1", "MEMORIA:2")}
    assert em.divergencias({"N1-01": ("MEMORIA:2", "MEMORIA:1")}, publicado) == []
    assert em.divergencias({"N1-01": ("MEMORIA:1",)}, publicado) == ["N1-01"]
