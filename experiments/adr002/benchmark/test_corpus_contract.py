"""Contrato del corpus del benchmark de ADR-002.

Estas pruebas no ejecutan T0 ni T1-T4 y no miden rendimiento: comprueban que
el corpus, los casos y las referencias respetan el contrato canónico de
B04 v1.0 APROBADO y del Plan de Pruebas + RED/PDP v1.0 APROBADO.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.benchmark import CORPUS_SEED
from experiments.adr002.benchmark import schema as S
from experiments.adr002.benchmark import validate_corpus as V

AQUI = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def artefactos() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return V.cargar()


@pytest.fixture(scope="module")
def corpus(artefactos: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return artefactos[0]


@pytest.fixture(scope="module")
def casos(artefactos: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return artefactos[1]


@pytest.fixture(scope="module")
def referencias(artefactos: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return artefactos[2]


# --- cobertura canónica -----------------------------------------------------


def test_los_50_ca_aparecen_exactamente_una_vez(casos: dict[str, Any]) -> None:
    vistos = [c["identificador_canonico"] for c in casos["nivel_1"]]
    assert len(vistos) == 50
    assert sorted(vistos) == sorted(S.CA_TOTALES)
    assert len(set(vistos)) == 50


def test_no_se_inventa_ningun_identificador_canonico(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        assert caso["identificador_canonico"] in S.CA_TOTALES
        for rf in caso["requisito_verificado"]:
            assert rf in S.RF_TOTALES
        for m in caso["metrica_y_umbral"]:
            assert m in S.M_TOTALES
        for fam in caso["familia_pdp"]:
            assert fam in S.FAMILIAS_PDP


def test_las_ocho_delegaciones_red_de_adr002_estan_cubiertas(casos: dict[str, Any]) -> None:
    cubiertas = {r for c in casos["nivel_1"] for r in c["traza_red"]}
    assert set(S.RED_ADR002) <= cubiertas


def test_red_040_no_se_usa_como_requisito_propio(casos: dict[str, Any]) -> None:
    """RED-040 pertenece a B05/ADR-003B: ADR-002 solo registra la interfaz."""
    for caso in casos["nivel_1"]:
        assert "RED-040" not in caso["traza_red"]


# --- contrato de B04 --------------------------------------------------------


def test_vocabularios_canonicos(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        assert caso["modo"] in S.MODOS
        assert caso["etapa_esperada"] in S.ETAPAS
        assert caso["parada_esperada"] in S.PARADAS
        assert caso["cardinalidad"] in S.CARDINALIDADES
        assert caso["criticidad"] in S.NIVEL_CRITICIDAD


def test_una_consulta_exhaustiva_nunca_termina_por_s1(casos: dict[str, Any]) -> None:
    """B04 §15.2 y §15.3: S1 está deshabilitado en cardinalidad EXHAUSTIVA."""
    for caso in casos["nivel_1"]:
        if caso["cardinalidad"] == "EXHAUSTIVA":
            assert caso["parada_esperada"] != "S1", caso["id"]


def test_hay_casos_de_las_tres_cardinalidades(casos: dict[str, Any]) -> None:
    presentes = {c["cardinalidad"] for c in casos["nivel_1"]}
    assert set(S.CARDINALIDADES) <= presentes


def test_toda_marca_critica_lleva_nivel_razon_fuente_y_regla(corpus: dict[str, Any]) -> None:
    """B04 §6 y B04-RF-23: prohibido el auto-marcado libre."""
    for item in corpus["items"]:
        if item["criticidad"] is not None:
            assert set(item["criticidad"]) == {"nivel", "razon", "fuente", "regla"}
            assert item["criticidad"]["nivel"] in S.NIVEL_CRITICIDAD
            assert item["criticidad"]["regla"]
            assert item["criticidad"]["fuente"]


def test_las_siete_dimensiones_son_ortogonales_y_canonicas(corpus: dict[str, Any]) -> None:
    """ADR-001 consecuencia 7: no se condensan en un enum monolítico."""
    for item in corpus["items"]:
        assert item["confirmacion"] in S.CONFIRMACION
        assert item["validez"] in S.VALIDEZ
        assert item["disponibilidad"] in S.DISPONIBILIDAD
        assert item["sensibilidad"] in S.SENSIBILIDAD
        assert item["ambito"] in S.AMBITO
        assert item["autoridad"] in S.AUTORIDAD
        assert set(S.CAMPOS_TEMPORALIDAD) <= set(item["temporalidad"])


def test_tiempo_valido_y_tiempo_de_registro_estan_separados(corpus: dict[str, Any]) -> None:
    """ADR-001 consecuencia 6 y B04-RF-07/RF-08."""
    con_tres_ejes = [
        i
        for i in corpus["items"]
        if i["temporalidad"]["occurred_at"]
        and i["temporalidad"]["valid_from"]
        and i["temporalidad"]["recorded_at"]
    ]
    assert con_tres_ejes, "CA-47 exige al menos un elemento con los tres ejes distintos"
    for item in con_tres_ejes:
        t = item["temporalidad"]
        assert len({t["occurred_at"], t["valid_from"], t["recorded_at"]}) == 3


# --- integridad de casos y referencias --------------------------------------


def test_todo_id_citado_existe_en_el_corpus(corpus: dict[str, Any], casos: dict[str, Any]) -> None:
    conocidos = (
        {i["id"] for i in corpus["items"]}
        | {m["id"] for m in corpus["mensajes"]}
        | {d["id"] for d in corpus["documentos"]}
        | {r["id"] for r in corpus["relaciones"]}
        | {e["id"] for e in corpus["entidades"]}
        | {p["id"] for p in corpus["proyectos"]}
    )
    for caso in casos["nivel_1"]:
        citados = {
            *caso["datos_sinteticos"],
            *caso["candidatos_elegibles"],
            *caso["candidatos_prohibidos"],
        }
        assert citados <= conocidos, caso["id"]


def test_elegibles_y_prohibidos_son_disjuntos(casos: dict[str, Any]) -> None:
    """La lista de prohibidos es tan vinculante como la de elegibles."""
    for caso in casos["nivel_1"]:
        assert not (set(caso["candidatos_elegibles"]) & set(caso["candidatos_prohibidos"]))


def test_cada_caso_declara_los_campos_obligatorios(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        for campo in S.CAMPOS_CASO:
            assert campo in caso, f"{caso['id']} sin {campo}"


def test_cada_caso_de_nivel_1_tiene_referencia_congelada(
    casos: dict[str, Any], referencias: dict[str, Any]
) -> None:
    ids_casos = {c["id"] for c in casos["nivel_1"]}
    ids_refs = {r["caso"] for r in referencias["referencias_nivel_1"]}
    assert ids_casos == ids_refs
    for ref in referencias["referencias_nivel_1"]:
        assert ref["modificable"] is False
        assert ref["congelada_por"].startswith("B04 v1.0 APROBADO")


def test_los_tres_niveles_estan_separados(casos: dict[str, Any]) -> None:
    assert casos["conteos"]["nivel_1"] == 50
    assert casos["conteos"]["nivel_2"] >= 1
    assert casos["conteos"]["nivel_3"] >= 1
    for caso in casos["nivel_2"]:
        assert caso["justificacion_nivel2"], caso["id"]


# --- fenómenos que el corpus debe poder expresar ----------------------------


@pytest.mark.parametrize(
    "fenomeno",
    [
        "negación",
        "condición",
        "apoyo",
        "refutación",
        "conflicto",
        "corrección",
        "sustitución",
        "homónimos",
        "alias ambiguos",
        "eliminado/purgado",
        "no guardado",
        "archivado",
        "restringido",
        "no usar como memoria",
        "no consolidable",
        "sin soporte",
        "candidata",
        "rechazada",
        "fuente inaccesible",
        "separación por proyecto",
        "lista multi-proyecto cerrada",
        "tiempo válido y de registro",
        "tres ejes temporales distintos",
    ],
)
def test_el_corpus_expresa_cada_fenomeno_exigido(corpus: dict[str, Any], fenomeno: str) -> None:
    informe = V.Informe()
    V._fenomenos(corpus, informe)
    faltan = informe.comprobaciones[0]["detalle"]["faltan"]
    assert fenomeno not in faltan


# --- disciplina del corpus --------------------------------------------------


def test_semilla_fija_y_sin_datos_reales(corpus: dict[str, Any]) -> None:
    assert corpus["semilla"] == CORPUS_SEED
    assert corpus["datos_reales"] == "ninguno; corpus sintético determinista"
    assert corpus["red"] == "no utilizada"
    crudo = json.dumps(corpus, ensure_ascii=False).lower()
    for prohibido in ("http://", "https://", "@gmail", "password", "api_key", "secret"):
        assert prohibido not in crudo


def test_ids_estables_y_sin_duplicados(corpus: dict[str, Any]) -> None:
    for coleccion in ("items", "mensajes", "documentos", "relaciones", "entidades", "proyectos"):
        ids = [x["id"] for x in corpus[coleccion]]
        assert len(ids) == len(set(ids)), coleccion


def test_el_corpus_no_depende_del_reloj(corpus: dict[str, Any]) -> None:
    """El "ahora" es un dato declarado, no la hora de ejecución."""
    assert corpus["ahora_declarado"] == "2026-06-15T00:00:00Z"


def test_ningun_caso_no_expresable_fue_eliminado(casos: dict[str, Any]) -> None:
    """Especificación de benchmark v0.2 §3 principio 6."""
    estados = {c["ejecutable_por_t0"] for c in casos["nivel_1"]}
    assert "NO_EXPRESABLE" in estados
    assert len(casos["nivel_1"]) == 50


def test_los_ficheros_json_son_deterministas() -> None:
    """Mismo commit, mismos bytes: PDP §11 paso 1 y RED-005."""
    antes = {
        n: (AQUI / n).read_bytes()
        for n in ("corpus_v0_1.json", "cases_v0_1.json", "references_v0_1.json")
    }
    from experiments.adr002.benchmark import build_corpus

    build_corpus.main()
    for nombre, contenido in antes.items():
        assert (AQUI / nombre).read_bytes() == contenido, nombre


def test_el_validador_completo_pasa_sin_fallos() -> None:
    assert V.main() == 0
