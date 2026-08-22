"""Contrato de la familia sucesora de conformidad v0.5.

Positivas: que la familia materializada cumple lo que su paquete preinscribe.
Negativas **por mutacion**: que cada validador se dispara cuando debe. Un
validador que nunca falla no valida; aqui cada mutacion se ejecuta sobre una
copia en memoria y **el arbol no se toca**.

No ejecuta T0, no implementa ni ejecuta ADR002-A/B/C/D y no mide rendimiento.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.benchmark import build_corpus_v0_5 as B5
from experiments.adr002.benchmark import schema_v0_5 as S5
from experiments.adr002.benchmark import validate_corpus_v0_5 as V5

AQUI = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def artefactos() -> dict[str, Any]:
    return V5.cargar()


@pytest.fixture(scope="module")
def corpus(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["conformance_corpus_v0_5.json"]


def _informe(funcion: Any, *args: Any) -> V5.Informe:
    inf = V5.Informe()
    funcion(*args, inf)
    return inf


# ---------------------------------------------------------------------------
# Positivas
# ---------------------------------------------------------------------------


def test_el_validador_completo_esta_en_verde() -> None:
    inf, _ = V5.validar()
    assert inf.fallos == [], inf.fallos
    assert len(inf.comprobaciones) >= 90


def test_la_v0_4_permanece_intacta_byte_a_byte() -> None:
    for nombre, esperado in S5.BLOBS_V0_4.items():
        assert V5._blob_git((AQUI / nombre).read_bytes()) == esperado, nombre


def test_los_siete_sucesores_existen_y_no_pisan_ningun_congelado() -> None:
    for nombre in S5.CONGELABLES_V0_5:
        assert (AQUI / nombre).exists(), nombre
    assert not set(S5.CONGELABLES_V0_5) & set(S5.BLOBS_V0_4)


def test_cobertura_total_de_los_tres_canales(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    ids = {i["id"] for i in corpus["items"]}
    for nombre in (
        "subject_keys_v0_1.json",
        "property_keys_v0_1.json",
        "applied_criticality_v0_1.json",
    ):
        assert set(artefactos[nombre]["valores"]) == ids, nombre


def test_la_ausencia_es_null_y_no_elimina_el_item(artefactos: dict[str, Any]) -> None:
    valores = artefactos["subject_keys_v0_1.json"]["valores"]
    assert None in valores.values()
    assert "" not in valores.values()


def test_ninguna_clave_de_sujeto_es_prefijo_de_otra(artefactos: dict[str, Any]) -> None:
    presentes = sorted({v for v in artefactos["subject_keys_v0_1.json"]["valores"].values() if v})
    assert presentes
    assert not [(a, b) for a in presentes for b in presentes if a != b and b.startswith(a)]


def test_identidades_distintas_con_el_mismo_sujeto_comparten_clave(
    artefactos: dict[str, Any],
) -> None:
    valores = [v for v in artefactos["subject_keys_v0_1.json"]["valores"].values() if v]
    assert len(valores) > len(set(valores))


def test_property_key_es_opaca_y_de_formato_cerrado(artefactos: dict[str, Any]) -> None:
    presentes = [v for v in artefactos["property_keys_v0_1.json"]["valores"].values() if v]
    assert presentes
    assert all(S5.RX_PROPERTY_KEY.match(v) for v in presentes)


def test_la_custodia_vive_una_sola_vez_en_el_manifiesto(artefactos: dict[str, Any]) -> None:
    canales = artefactos["benchmark_manifest_v0_5.json"]["canales_laterales"]
    for canal in canales.values():
        assert {"fuente_de_asignacion", "version_del_vocabulario", "regla_de_validacion"} <= set(
            canal
        )
    for nombre in ("subject_keys_v0_1.json", "property_keys_v0_1.json"):
        for valor in artefactos[nombre]["valores"].values():
            assert valor is None or isinstance(valor, str)


def test_el_censo_de_criticidad_es_propio_y_no_el_de_la_v0_4(artefactos: dict[str, Any]) -> None:
    censo = artefactos["applied_criticality_v0_1.json"]["censo"]
    assert censo["items"] == 97
    assert censo["sin_criticidad"] == 78
    assert (censo["items"], censo["sin_criticidad"]) != (95, 76)


def test_la_fuente_bruta_de_criticidad_no_cruza(artefactos: dict[str, Any]) -> None:
    crudo = json.dumps(artefactos["applied_criticality_v0_1.json"], ensure_ascii=False)
    assert "B04-CA-01" not in crudo
    assert S5.FUENTE_CRITICIDAD_COMPARTIDA not in crudo


def test_los_bloques_heredados_de_casos_y_referencias_no_cambian(
    artefactos: dict[str, Any],
) -> None:
    casos_v0_4 = json.loads((AQUI / "cases_v0_4.json").read_text(encoding="utf-8"))
    refs_v0_4 = json.loads((AQUI / "references_v0_4.json").read_text(encoding="utf-8"))
    for bloque in ("nivel_1", "nivel_1_pdp", "nivel_2", "nivel_3"):
        assert artefactos["cases_v0_5.json"][bloque] == casos_v0_4[bloque]
    assert (
        artefactos["references_v0_5.json"]["referencias_nivel_1"]
        == refs_v0_4["referencias_nivel_1"]
    )


def test_el_delta_comparte_cero_tokens_con_el_tokenizador_real(corpus: dict[str, Any]) -> None:
    por_id = {i["id"]: i for i in corpus["items"]}
    origen = por_id[S5.ITEM_ORIGEN_DELTA]["text"]
    destino = por_id[S5.ITEM_DESTINO_DELTA]["text"]
    compartidos = V5._terminos_del_indice([origen]) & V5._terminos_del_indice([destino])
    assert compartidos == set(), sorted(compartidos)


def test_el_barrido_de_impacto_recalcula_66_dominios_sin_cambios(corpus: dict[str, Any]) -> None:
    barrido = B5.barrido_impacto_delta(corpus)
    assert barrido["cambios"] == []
    assert barrido["adjudicaciones_recalculadas"] == S5.DOMINIOS_RECALCULADOS


def test_la_proyeccion_t0_no_se_regenera(artefactos: dict[str, Any]) -> None:
    proyeccion = artefactos["benchmark_manifest_v0_5.json"]["proyeccion_t0"]
    assert proyeccion["regenerada"] is False
    assert proyeccion["blob_observado"] == S5.PROYECCION_T0_BLOB_OBSERVADO
    assert not (AQUI / "t0_preexecution_projection_v0_3.json").exists()
    assert "NO EXISTE" in proyeccion["arnes_de_conformidad_de_t0"]


def test_el_rendimiento_se_hereda_y_no_se_mide(artefactos: dict[str, Any]) -> None:
    rendimiento = artefactos["benchmark_manifest_v0_5.json"]["rendimiento"]
    assert rendimiento["blob"] == S5.BLOBS_V0_4["performance_corpus_v0_2.json"]
    assert rendimiento["sha256"] == S5.SHA256_PERFORMANCE_V0_2
    crudo = json.dumps(artefactos["benchmark_manifest_v0_5.json"], ensure_ascii=False)
    assert "latencia_medida" not in crudo


def test_la_frontera_entrada_oraculo_esta_separada(artefactos: dict[str, Any]) -> None:
    caso = artefactos["cases_v0_5.json"]["nivel_4"][0]
    assert set(caso["entrada"]) & set(caso["oraculo"]) == set()
    entrada = json.dumps(caso["entrada"], ensure_ascii=False)
    for prohibido in ("resultado_esperado", "elegibles", "prohibidos", "parada_esperada"):
        assert prohibido not in entrada


# ---------------------------------------------------------------------------
# Negativas por mutacion · el arbol NO se toca
# ---------------------------------------------------------------------------


def test_negativa_01_falta_una_entrada_en_el_canal_lateral(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    canal = copy.deepcopy(artefactos["property_keys_v0_1.json"])
    canal["valores"].pop(next(iter(canal["valores"])))
    assert _informe(V5._property_keys, corpus, canal).fallos


def test_negativa_02_un_valor_de_property_key_alterado(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    canal = copy.deepcopy(artefactos["property_keys_v0_1.json"])
    clave = next(k for k, v in canal["valores"].items() if v)
    canal["valores"][clave] = "PK-000000000000"
    assert _informe(V5._property_keys, corpus, canal).fallos


def test_negativa_03_una_clave_de_sujeto_inventada(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    canal = copy.deepcopy(artefactos["subject_keys_v0_1.json"])
    clave = next(k for k, v in canal["valores"].items() if v is None)
    canal["valores"][clave] = "sujetoinventado"
    assert _informe(V5._subject_keys, corpus, canal).fallos


def test_negativa_04_la_ausencia_representada_como_cadena_vacia(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    canal = copy.deepcopy(artefactos["subject_keys_v0_1.json"])
    clave = next(k for k, v in canal["valores"].items() if v is None)
    canal["valores"][clave] = ""
    assert _informe(V5._subject_keys, corpus, canal).fallos


def test_negativa_05_un_identificador_de_caso_en_la_razon_segura(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    canal = copy.deepcopy(artefactos["applied_criticality_v0_1.json"])
    clave = next(k for k, v in canal["valores"].items() if v)
    canal["valores"][clave]["razon_segura"] = "Instanciacion de B04-CA-26"
    assert _informe(V5._criticidad, corpus, canal).fallos


def test_negativa_06_la_fuente_bruta_filtrada_al_plano_comun(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    canal = copy.deepcopy(artefactos["applied_criticality_v0_1.json"])
    clave = next(k for k, v in canal["valores"].items() if v)
    canal["valores"][clave]["fuente_de_politica"] = "B04-CA-42"
    assert _informe(V5._criticidad, corpus, canal).fallos


def test_negativa_07_el_censo_copiado_de_la_v0_4(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    canal = copy.deepcopy(artefactos["applied_criticality_v0_1.json"])
    canal["censo"] = {
        "items": 95,
        "sin_criticidad": 76,
        "con_criticidad": 19,
        "distribucion_por_nivel": {"CRITICO": 18, "IMPORTANTE": 1},
        "fuentes_de_politica": {},
        "razones_seguras_distintas": 8,
        "reglas_de_politica_distintas": 7,
    }
    assert _informe(V5._criticidad, corpus, canal).fallos


def test_negativa_08_una_fuente_bruta_fuera_de_la_tabla_cerrada() -> None:
    corpus_falso = {
        "items": [
            {
                "id": "MEM-000",
                "text": "t",
                "entity_ids": [],
                "criticidad": {
                    "nivel": "CRITICO",
                    "razon": "r",
                    "fuente": "FUENTE-QUE-NADIE-APROBO",
                    "regla": "CRIT-01",
                },
            }
        ]
    }
    with pytest.raises(S5.ContratoFamiliaV05Error):
        B5.construir_criticidad_aplicada(corpus_falso)


def test_negativa_09_un_campo_sin_terna_asignada() -> None:
    with pytest.raises(S5.ContratoFamiliaV05Error):
        S5.capacidad_de("campo_nuevo_sin_clasificar")


def test_negativa_10_los_extremos_comparten_un_token() -> None:
    delta = B5.construir_delta()
    delta["items"][1]["text"] = "El rotor municipal permanece archivado."
    assert B5.fallos_de_condicion_lexica(delta)


def test_negativa_11_el_delta_altera_una_adjudicacion_heredada(corpus: dict[str, Any]) -> None:
    """Un extremo del delta colocado dentro del universo de un caso heredado.

    El barrido compara el corpus con delta contra el corpus sin delta, de modo
    que solo un **extremo del propio delta** puede disparar el fallo: un intruso
    presente en las dos versiones seria invisible para la comparacion, que es
    justo el punto ciego que esta prueba fija.
    """
    contaminado = copy.deepcopy(corpus)
    extremo = next(i for i in contaminado["items"] if i["id"] == S5.ITEM_ORIGEN_DELTA)
    extremo["project_id"] = "PRJ-ALFA"
    extremo["ambito"] = "GLOBAL"
    extremo["text"] = "El usuario prefiere que redactes en tono directo y sin adornos."
    with pytest.raises(S5.ContratoFamiliaV05Error):
        B5.barrido_impacto_delta(contaminado)


def test_negativa_12_sin_la_arista_el_destino_deja_de_ser_aportado(
    corpus: dict[str, Any],
) -> None:
    sin_arista = copy.deepcopy(corpus)
    sin_arista["relaciones"] = [r for r in sin_arista["relaciones"] if r["id"] != S5.RELACION_DELTA]
    assert B5._un_salto_relacional(sin_arista, [S5.ITEM_ORIGEN_DELTA]) == []
    assert B5._un_salto_relacional(corpus, [S5.ITEM_ORIGEN_DELTA]) == [S5.ITEM_DESTINO_DELTA]


def test_negativa_13_la_arista_con_tipo_excluido(corpus: dict[str, Any]) -> None:
    mutado = copy.deepcopy(corpus)
    arista = next(r for r in mutado["relaciones"] if r["id"] == S5.RELACION_DELTA)
    arista["tipo"] = "SUSTITUYE_A"
    assert _informe(V5._delta, mutado).fallos


def test_negativa_14_una_nota_de_la_arista_que_revela_el_caso(corpus: dict[str, Any]) -> None:
    mutado = copy.deepcopy(corpus)
    arista = next(r for r in mutado["relaciones"] if r["id"] == S5.RELACION_DELTA)
    arista["nota"] = "B04-CA-26: el destino esperado del discriminante."
    assert _informe(V5._delta, mutado).fallos


def test_negativa_15_un_conteo_declarado_que_no_cuadra(corpus: dict[str, Any]) -> None:
    mutado = copy.deepcopy(corpus)
    mutado["conteos"]["items"] = 96
    assert _informe(V5._corpus, mutado).fallos


def test_negativa_16_un_bloque_heredado_alterado(artefactos: dict[str, Any]) -> None:
    mutados = copy.deepcopy(artefactos)
    mutados["cases_v0_5.json"]["nivel_1"][0]["id"] = "N1-99"
    assert _informe(V5._herencia_intacta, mutados).fallos


def test_negativa_17_el_manifiesto_olvida_un_heredado(artefactos: dict[str, Any]) -> None:
    mutados = copy.deepcopy(artefactos)
    mutados["benchmark_manifest_v0_5.json"]["custodia"]["heredados_por_blob"].pop(
        "performance_corpus_v0_2.json"
    )
    assert _informe(V5._manifiesto, mutados).fallos


def test_negativa_18_el_oraculo_del_caso_reclama_el_destino(artefactos: dict[str, Any]) -> None:
    mutados = copy.deepcopy(artefactos)
    caso = mutados["cases_v0_5.json"]["nivel_4"][0]
    caso["oraculo"]["alcance_lexico_estructurado"] = [
        S5.ITEM_ORIGEN_DELTA,
        S5.ITEM_DESTINO_DELTA,
    ]
    assert _informe(V5._discriminante, mutados).fallos


def test_negativa_19_un_limite_estrecho_que_fingiria_el_discriminante(
    artefactos: dict[str, Any],
) -> None:
    mutados = copy.deepcopy(artefactos)
    mutados["cases_v0_5.json"]["nivel_4"][0]["entrada"]["peticion"]["limite_duro"] = 1
    assert _informe(V5._discriminante, mutados).fallos


def test_negativa_20_un_campo_de_oraculo_colado_en_la_entrada(
    artefactos: dict[str, Any],
) -> None:
    mutados = copy.deepcopy(artefactos)
    mutados["cases_v0_5.json"]["nivel_4"][0]["entrada"]["elegibles"] = [S5.ITEM_ORIGEN_DELTA]
    assert _informe(V5._frontera_entrada_oraculo, mutados).fallos
