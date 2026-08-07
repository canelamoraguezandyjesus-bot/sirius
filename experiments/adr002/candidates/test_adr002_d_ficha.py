"""``ADR002-D``: que la ficha diga lo que el codigo hace, y en ese orden.

Se ejecutan **solo despues** de que ``ficha_ADR002-D_v3.json`` sea ancestro
estricto del commit que las corre, que es la regla 3 de ``TOL-210``: una
ejecucion que no venga precedida por su ficha no es evidencia utilizable.

Lo que comprueban no es el comportamiento —eso lo hace la suite funcional—,
sino la **coherencia entre lo declarado y lo implementado**, que es
exactamente donde `C v1` fallo: una ficha puede describir un candidato que no
existe, y ninguna prueba de comportamiento lo detecta.

Se comprueba ademas la anterioridad que la restriccion 2 exige: el acta que
congelo el orden de las etapas tardias precede **estrictamente** tanto a la
implementacion como a la ficha, contra el grafo de Git y no contra una fecha.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates.adr002_d.candidate import (
    ACTA_DEL_ORDEN,
    ORDEN_CONGELADO,
    SENAL_RELACIONAL,
    SENAL_TARDIA,
    SENAL_VECTORIAL,
)
from experiments.adr002.cards import card_protocol as cp

RAIZ = Path(__file__).resolve().parents[3]
FICHA: Final = "artifacts/adr002_cards/ficha_ADR002-D_v3.json"
IMPLEMENTACION: Final = "experiments/adr002/candidates/adr002_d/candidate.py"
ACTA: Final = f"docs/architecture/{ACTA_DEL_ORDEN}"

#: Se fija al congelar la v2; si quedara desactualizada, la cita fallaria.
HUELLA_FICHA_D_V2: Final = "5ca687f88a7d194a922ca39eb32778c0ab02608c"

#: La v1, conservada y marcada, con la huella que la sustitucion recomputo.
HUELLA_FICHA_D_V1_SUSTITUIDA: Final = "0ca203f07ebc550a4e37f956f92aa1723f927572"

HUELLA_A_VIGENTE: Final = "d305073ce5bb21a07e8523969752a9f06a966d01"
HUELLA_B_VIGENTE: Final = "b7ea269da379fc0de324efa5ca2da7baa616d112"
HUELLA_C_VIGENTE: Final = "ef71f944536ffc07dd18b39278ba43da2776232c"


def _git(*argumentos: str) -> str:
    return subprocess.run(
        ["git", *argumentos], cwd=str(RAIZ), capture_output=True, text=True, check=False
    ).stdout.strip()


def _commit_de_entrada(ruta: str) -> str:
    entrada = _git("log", "--format=%H", "--diff-filter=A", "--", ruta)
    return "" if not entrada else entrada.splitlines()[-1]


def _es_ancestro(anterior: str, posterior: str) -> bool:
    if not anterior or not posterior or anterior == posterior:
        return False
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", anterior, posterior],
            cwd=str(RAIZ),
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def _la_ficha_es_ancestro_estricto() -> bool:
    return _es_ancestro(_commit_de_entrada(FICHA), _git("rev-parse", "HEAD"))


pytestmark = pytest.mark.skipif(
    not _la_ficha_es_ancestro_estricto(),
    reason=(
        "la ficha ADR002-D v2 aun no es ancestro estricto: ejecutar ahora "
        "produciria evidencia no utilizable (TOL-210, regla 3)"
    ),
)


@pytest.fixture(scope="module")
def ficha() -> dict:
    return json.loads((RAIZ / FICHA).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# A. Anterioridad: la ficha antes de la ejecucion, el orden antes de las dos
# --------------------------------------------------------------------------


def test_la_ficha_d_es_anterior_estricta_a_esta_ejecucion() -> None:
    entrada = _commit_de_entrada(FICHA)
    assert entrada, "la ficha v2 de ADR002-D no esta confirmada en el repositorio"
    assert _es_ancestro(entrada, _git("rev-parse", "HEAD"))


def test_el_orden_se_congelo_antes_que_la_implementacion() -> None:
    """Restriccion 2: el orden se declara **antes** de ejecutar, y se prueba."""
    acta = _commit_de_entrada(ACTA)
    implementacion = _commit_de_entrada(IMPLEMENTACION)
    assert acta, "el acta que congela el orden no esta confirmada"
    assert implementacion, "la implementacion de ADR002-D no esta confirmada"
    assert _es_ancestro(acta, implementacion), (
        "el acta del orden debe ser ancestro ESTRICTO del commit que implementa D"
    )


def test_el_orden_se_congelo_antes_que_la_ficha() -> None:
    assert _es_ancestro(_commit_de_entrada(ACTA), _commit_de_entrada(FICHA))


# --------------------------------------------------------------------------
# B. Identidad de la ficha
# --------------------------------------------------------------------------


def test_la_ficha_declara_la_identidad_correcta(ficha: dict) -> None:
    assert ficha["identidad"]["candidato"] == "ADR002-D"
    assert ficha["identidad"]["papel"] == cp.PAPEL_CANDIDATO
    assert ficha["identidad"]["version"] == 3
    assert ficha["identidad"]["sustituye_a"] == 2
    assert ficha["estado"] == cp.ESTADO_CONGELADA
    assert ficha["congelacion"]["huella"] == HUELLA_FICHA_D_V2
    assert ficha["no_contiene_resultados"] is True


def test_la_huella_declarada_se_recomputa(ficha: dict) -> None:
    """La huella no se cree: se recomputa sobre la forma canonica."""
    assert cp.huella_canonica(ficha) == ficha["congelacion"]["huella"]


def test_la_v1_se_conserva_marcada_y_la_v2_es_la_unica_congelada() -> None:
    """Una ficha sustituida se marca, no se borra ni se reescribe."""
    fichas = sorted((RAIZ / "artifacts/adr002_cards").glob("ficha_ADR002-D_*.json"))
    assert [ruta.name for ruta in fichas] == [
        "ficha_ADR002-D_v1.json",
        "ficha_ADR002-D_v2.json",
        "ficha_ADR002-D_v3.json",
    ]
    v1 = json.loads(
        (RAIZ / "artifacts/adr002_cards/ficha_ADR002-D_v1.json").read_text(encoding="utf-8")
    )
    assert v1["estado"] == cp.ESTADO_SUSTITUIDA
    assert v1["congelacion"]["huella"] == HUELLA_FICHA_D_V1_SUSTITUIDA
    assert cp.huella_canonica(v1) == HUELLA_FICHA_D_V1_SUSTITUIDA


# --------------------------------------------------------------------------
# C. Lo que solo ADR002-D declara: la restriccion acumulativa
# --------------------------------------------------------------------------


def test_la_senal_declarada_es_la_de_la_alternativa(ficha: dict) -> None:
    assert ficha["senal_tardia"]["habilitada"] == SENAL_TARDIA
    assert cp.senal_coherente("ADR002-D", ficha["senal_tardia"]["habilitada"])
    assert ficha["senal_tardia"]["coherente_con_la_alternativa"] is True


def test_la_restriccion_d_aplica_y_esta_completa(ficha: dict) -> None:
    bloque = ficha["restriccion_d"]
    assert cp.restriccion_d_aplicable("ADR002-D")
    assert bloque["aplica"] is True
    assert bloque["motivo_de_no_aplicacion"] is None
    for campo in (
        "senales_en_etapas_distintas",
        "orden_predefinido",
        "sin_coordinacion_simultanea",
        "como_se_demuestra_en_cada_ejecucion",
        "traza_a_b04_d15",
    ):
        assert cp.es_declaracion(bloque[campo]), campo


def test_la_ficha_declara_el_mismo_orden_que_el_codigo(ficha: dict) -> None:
    """Si la ficha y el codigo discrepasen en el orden, la ficha no valdria."""
    declarado = ficha["senal_tardia"]["orden_de_las_etapas_tardias"]
    assert f"E3 {SENAL_RELACIONAL}" in declarado
    assert f"E4 {SENAL_VECTORIAL}" in declarado
    assert declarado.index(f"E3 {SENAL_RELACIONAL}") < declarado.index(f"E4 {SENAL_VECTORIAL}")
    assert ORDEN_CONGELADO[0][1] == SENAL_RELACIONAL
    assert ORDEN_CONGELADO[1][1] == SENAL_VECTORIAL


def test_la_ficha_cita_el_acta_que_congelo_el_orden(ficha: dict) -> None:
    documento = json.dumps(ficha, ensure_ascii=False)
    assert ACTA_DEL_ORDEN in documento
    assert (RAIZ / ACTA).exists()


def test_la_ficha_asigna_cada_senal_a_una_etapa_distinta(ficha: dict) -> None:
    etapas = ficha["arquitectura"]["etapas_implementadas"]
    assert "RELACIONAL" in etapas["E3"] and "vectorial NO se abre" in etapas["E3"]
    assert "VECTORIAL" in etapas["E4"] and "relacional ya termino en E3" in etapas["E4"]
    for temprana in ("E0", "E1", "E2"):
        assert "Ninguna senal tardia se abre" in etapas[temprana]


# --------------------------------------------------------------------------
# D. Que la ficha no describa un candidato que no existe (leccion de C v1)
# --------------------------------------------------------------------------


def test_la_ficha_cita_las_versiones_vigentes_de_sus_dependencias(ficha: dict) -> None:
    documento = json.dumps(ficha, ensure_ascii=False)
    assert HUELLA_A_VIGENTE in documento, "debe citar A v6, la base vigente"
    assert HUELLA_B_VIGENTE in documento, "debe citar B v8, de donde toma la senal vectorial"
    assert HUELLA_C_VIGENTE in documento, "debe citar C v3, de donde toma la senal relacional"


@pytest.mark.parametrize(
    ("huella", "ruta"),
    [
        (HUELLA_A_VIGENTE, "artifacts/adr002_cards/ficha_ADR002-A_v6.json"),
        (HUELLA_B_VIGENTE, "artifacts/adr002_cards/ficha_ADR002-B_v8.json"),
        (HUELLA_C_VIGENTE, "artifacts/adr002_cards/ficha_ADR002-C_v3.json"),
    ],
)
def test_las_huellas_citadas_son_las_reales(huella: str, ruta: str) -> None:
    """No basta con citar una huella: tiene que ser la que la ficha citada tiene."""
    citada = json.loads((RAIZ / ruta).read_text(encoding="utf-8"))
    assert citada["estado"] == cp.ESTADO_CONGELADA
    assert citada["congelacion"]["huella"] == huella
    assert cp.huella_canonica(citada) == huella


def test_los_arboles_citados_existen_en_git(ficha: dict) -> None:
    documento = json.dumps(ficha, ensure_ascii=False)
    arboles = {
        "experiments/adr002/candidates": None,
        "experiments/adr002/candidates/common": None,
        "experiments/adr002/candidates/adr002_a": None,
        "experiments/adr002/candidates/adr002_b": None,
        "experiments/adr002/candidates/adr002_c": None,
        "experiments/adr002/candidates/adr002_d": None,
    }
    commit = ficha["huella_candidato"]["commit_del_prototipo"]
    for ruta in arboles:
        arbol = _git("rev-parse", f"{commit}:{ruta}")
        assert re.fullmatch(r"[0-9a-f]{40}", arbol), ruta
        assert arbol in documento, f"la ficha no cita el arbol real de {ruta}"


def test_la_ficha_declara_el_sustrato_lexico_real(ficha: dict) -> None:
    sustrato = ficha["arquitectura"]["sustrato_lexico"]
    assert "knowledge_fts" in sustrato
    assert "unicode61" in sustrato
    assert "remove_diacritics 1" in sustrato
    assert "sin clausula tokenize" in sustrato


def test_la_ficha_no_describe_un_indice_relacional_derivado(ficha: dict) -> None:
    """`ADR002-D` toma de `C` una fuente de entrada, no un indice construido."""
    relacional = next(
        componente
        for componente in ficha["componentes"]
        if componente["papel"] == "indice relacional"
    )
    assert "ninguno derivado" in relacional["nombre"]
    assert "no construye" in relacional["ruta_de_sustitucion"]
    assert [indice["nombre"] for indice in ficha["indices_no_lexicos"]] == [
        "indice vectorial distribucional disperso (sidecar SQLite)"
    ]


def test_la_ficha_declara_el_coordinador_como_lo_unico_propio(ficha: dict) -> None:
    coordinador = next(
        componente
        for componente in ficha["componentes"]
        if componente["papel"] == "coordinador de senales tardias"
    )
    assert "adr002_d" in coordinador["nombre"]
    assert ACTA_DEL_ORDEN in coordinador["version"]


# --------------------------------------------------------------------------
# E. Aritmetica declarada, recomputada
# --------------------------------------------------------------------------


def test_el_limite_extremo_a_extremo_es_la_suma_de_los_locales(ficha: dict) -> None:
    etapas = ficha["coste_por_etapa"]["etapas"]
    suma = sum(etapa["coste_local_limite_ns"] for etapa in etapas)
    assert suma == ficha["coste_por_etapa"]["coste_local_total_ns"]
    assert suma == ficha["coste_por_etapa"]["coste_extremo_a_extremo_ns"]
    assert suma == ficha["extremo_a_extremo"]["limite_duro_p99_ns"]


def test_e3_conserva_el_limite_de_la_base_y_e4_recibe_la_senal_vectorial(
    ficha: dict,
) -> None:
    """La aritmetica que el orden congelado obliga, comprobada contra A y B."""
    por_etapa = {e["etapa"]: e["coste_local_limite_ns"] for e in ficha["coste_por_etapa"]["etapas"]}
    a5 = json.loads(
        (RAIZ / "artifacts/adr002_cards/ficha_ADR002-A_v6.json").read_text(encoding="utf-8")
    )
    b7 = json.loads(
        (RAIZ / "artifacts/adr002_cards/ficha_ADR002-B_v8.json").read_text(encoding="utf-8")
    )
    de_a = {e["etapa"]: e["coste_local_limite_ns"] for e in a5["coste_por_etapa"]["etapas"]}
    de_b = {e["etapa"]: e["coste_local_limite_ns"] for e in b7["coste_por_etapa"]["etapas"]}
    assert por_etapa["E3"] == de_a["E3"], "E3 absorbe la senal relacional sin subir"
    holgura_vectorial = de_b["E3"] - de_a["E3"]
    assert por_etapa["E4"] == de_a["E4"] + holgura_vectorial
    assert (
        ficha["extremo_a_extremo"]["limite_duro_p99_ns"]
        == b7["extremo_a_extremo"]["limite_duro_p99_ns"]
    ), "mover una senal de etapa no anade trabajo"


def test_la_ficha_no_contiene_ningun_resultado(ficha: dict) -> None:
    documento = json.dumps(ficha, ensure_ascii=False).lower()
    for prohibido in ("p50 medido", "p95 medido", "observado:", "resultado obtenido"):
        assert prohibido not in documento
    assert ficha["no_contiene_resultados"] is True
