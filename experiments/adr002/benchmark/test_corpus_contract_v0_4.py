"""Contrato v0.4 del benchmark de ADR-002 · pruebas con oráculos independientes.

Regla de independencia: ninguna prueba de cierre, censo, guarda o fidelidad
importa funciones de ``build_corpus_v0_4``. Los oráculos viven en el propio
validador v0.4 —que no comparte código con el generador— o directamente en
este fichero. ``build_corpus_v0_4`` solo aparece dentro del validador para la
comprobación de determinismo.

La segunda mitad son las **mutaciones negativas obligatorias** del paquete
03D: cada control crítico se demuestra rompiéndolo. Las mutaciones sobre el
corpus regeneran los metadatos de forma coherente cuando procede, para
demostrar que la detección no depende de declaraciones rancias.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.benchmark import canonical_source_v0_3 as CS3
from experiments.adr002.benchmark import canonical_source_v0_4 as CS4
from experiments.adr002.benchmark import schema_v0_4 as S4
from experiments.adr002.benchmark import validate_corpus_v0_4 as V4

AQUI = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def canon() -> CS4.Canon:
    return CS4.cargar_canon()


@pytest.fixture(scope="module")
def artefactos() -> dict[str, Any]:
    return V4.cargar()


@pytest.fixture(scope="module")
def conformidad(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["conformance_corpus_v0_4.json"]


@pytest.fixture(scope="module")
def casos(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["cases_v0_4.json"]


@pytest.fixture(scope="module")
def referencias(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["references_v0_4.json"]


@pytest.fixture(scope="module")
def manifiesto(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["benchmark_manifest_v0_4.json"]


def fallos(funcion: Any, *args: Any) -> list[str]:
    inf = V4.Informe()
    funcion(*args, inf)
    return [c["comprobacion"] for c in inf.fallos]


def por_ca(casos: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["identificador_canonico"]: c for c in casos["nivel_1"]}


def coherente(corpus: dict[str, Any]) -> dict[str, Any]:
    """Regenera identidad, conteos y colisiones como lo haría el generador.

    Implementación propia del arnés de pruebas: demuestra que los controles
    del validador no dependen de metadatos rancios sino de recálculo real.
    """

    def sha(datos: Any) -> str:
        return hashlib.sha256(
            json.dumps(datos, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    corpus["identidad"] = {
        coleccion: {
            "conteo": len(corpus[coleccion]),
            "huella_coleccion": sha(corpus[coleccion]),
            "huella_por_elemento": {e["id"]: sha(e) for e in corpus[coleccion]},
        }
        for coleccion in ("items", "mensajes", "documentos", "relaciones", "entidades", "proyectos")
    }
    corpus["conteos"] = {
        "proyectos": len(corpus["proyectos"]),
        "entidades": len(corpus["entidades"]),
        "items": len(corpus["items"]),
        "recuerdos": sum(1 for i in corpus["items"] if i["kind"] == "MEMORIA"),
        "decisiones": sum(1 for i in corpus["items"] if i["kind"] == "DECISION"),
        "mensajes": len(corpus["mensajes"]),
        "documentos": len(corpus["documentos"]),
        "relaciones": len(corpus["relaciones"]),
    }
    raices: dict[str, set[str]] = {}
    proyecto_de = {i["id"]: i["project_id"] for i in corpus["items"]}
    for item in corpus["items"]:
        for token in V4._o_norm(item["text"]):
            if len(token) >= 6 and token not in S4.VACIAS:
                raices.setdefault(token[:6], set()).add(item["id"])
    corpus["colisiones_por_raiz_declaradas"] = [
        {"raiz": r, "items": sorted(ids), "proyectos": sorted({proyecto_de[i] for i in ids})}
        for r, ids in sorted(raices.items())
        if len(ids) > 1 and len({proyecto_de[i] for i in ids}) > 1
    ]
    return corpus


# ===========================================================================
# Lector canónico v0.4
# ===========================================================================


def test_censo_de_cabeceras_correcto() -> None:
    CS4.verificar_censo_de_cabeceras()
    censo = {tuple(f["cabecera"]): f for f in CS4.censo_de_cabeceras()}
    compartida = ("ID", "Riesgo", "Entrada", "Resultado esperado", "Fallo observable")
    assert censo[compartida]["n_reales"] == censo[compartida]["n_identidades"] == 2


@pytest.mark.parametrize(
    ("celda", "esperado"),
    [
        ("B04-M16", ["B04-M16"]),
        ("B08-M12/M25", ["B08-M12", "B08-M25"]),
        ("B04-M21/B05-M16", ["B04-M21", "B05-M16"]),
        ("PDP-M01\u2013M17", [f"PDP-M{n:02d}" for n in range(1, 18)]),
        (
            "B08-M29/B08-M32/PDP-M01/PDP-M02/PDP-M17",
            ["B08-M29", "B08-M32", "PDP-M01", "PDP-M02", "PDP-M17"],
        ),
    ],
)
def test_expansion_estricta_de_metricas(celda: str, esperado: list[str]) -> None:
    assert CS4.expandir_metricas_estricta(celda) == esperado


def test_expansion_estricta_conserva_prefijo_en_continuaciones() -> None:
    assert CS4.expandir_metricas_estricta("B08-M05/M12") == ["B08-M05", "B08-M12"]


def test_las_79_celdas_reales_expanden_estrictamente() -> None:
    CS4.verificar_metricas_estrictas()


# ===========================================================================
# Oráculo puente · universo crítico 5/6/11/12 sin funciones del generador
# ===========================================================================


def _criticos_vigentes(conformidad: dict[str, Any], proyecto: str, instante: str) -> list[str]:
    t = datetime.fromisoformat(instante.replace("Z", "+00:00"))
    salida = []
    for item in conformidad["items"]:
        if item["project_id"] != proyecto:
            continue
        if not item["criticidad"] or item["criticidad"]["nivel"] != "CRITICO":
            continue
        if item["confirmacion"] != "CONFIRMADA" or item["validez"] != "VIGENTE":
            continue
        if item["disponibilidad"] != "DISPONIBLE" or item["no_usar_como_memoria"]:
            continue
        vf = item["temporalidad"]["valid_from"]
        vt = item["temporalidad"]["valid_to"]
        if vf and datetime.fromisoformat(vf.replace("Z", "+00:00")) > t:
            continue
        if vt and t >= datetime.fromisoformat(vt.replace("Z", "+00:00")):
            continue
        salida.append(item["id"])
    return sorted(salida)


def test_puente_critico_5_6_11_12(conformidad: dict[str, Any], casos: dict[str, Any]) -> None:
    ca = por_ca(casos)
    assert _criticos_vigentes(conformidad, "PRJ-ALFA", S4.AHORA_DECLARADO) == list(
        S4.CRITICOS_ALFA_V0_4
    )
    assert len(_criticos_vigentes(conformidad, "PRJ-GAMMA", "2026-02-01T00:00:00Z")) == 6
    assert len(_criticos_vigentes(conformidad, "PRJ-GAMMA", "2026-04-01T00:00:00Z")) == 11
    assert len(_criticos_vigentes(conformidad, "PRJ-GAMMA", S4.AHORA_DECLARADO)) == 12
    esperado = {
        "B04-CA-31": (5, 5, 0),
        "B04-CA-44": (6, 5, 1),
        "B04-CA-26": (11, 11, 0),
        "B04-CA-38": (12, 10, 2),
    }
    for ident, (elegibles, devueltos, pendientes) in esperado.items():
        adj = ca[ident]["adjudicacion"]
        assert len(adj["elegibles_semanticos"]) == elegibles, ident
        assert len(adj["resultado_esperado"]) == devueltos, ident
        assert len(adj["pendientes_por_limite"]) == pendientes, ident


def test_desempate_de_ca44_declarado_y_reproducible(casos: dict[str, Any]) -> None:
    adj = por_ca(casos)["B04-CA-44"]["adjudicacion"]
    assert adj["dominio"]["limite"] == {"n": 5, "tipo": "DURO", "desempate": "ID"}
    assert adj["resultado_en_orden_de_desempate"] == sorted(adj["resultado_esperado"])
    assert adj["pendientes_por_limite"] == ["MEM-106"]


def test_ca26_documenta_expansion_de_10_a_11(casos: dict[str, Any]) -> None:
    adj = por_ca(casos)["B04-CA-26"]["adjudicacion"]
    assert adj["dominio"]["limite"]["n"] == 10
    assert adj["dominio"]["limite"]["tipo"] == "OBJETIVO"
    assert len(adj["resultado_esperado"]) == 11
    assert adj["pendientes_por_limite"] == []


def test_mem_101_112_sin_rastro_de_ca31(conformidad: dict[str, Any]) -> None:
    for item in conformidad["items"]:
        if item["id"] in S4.CRITICOS_GAMMA_V0_4:
            assert "CA-31" not in json.dumps(item, ensure_ascii=False), item["id"]
            assert item["traza"] == ["B04-CA-26", "B04-CA-38", "B04-CA-44"]
            assert item["criticidad"]["fuente"] == S4.FUENTE_CRITICIDAD_COMPARTIDA


# ===========================================================================
# Los 13 EXHAUSTIVA · invariantes leídas del JSON, sin generador
# ===========================================================================

LOS_13_EXHAUSTIVA = (
    "B04-CA-02",
    "B04-CA-03",
    "B04-CA-08",
    "B04-CA-11",
    "B04-CA-14",
    "B04-CA-17",
    "B04-CA-22",
    "B04-CA-25",
    "B04-CA-27",
    "B04-CA-28",
    "B04-CA-31",
    "B04-CA-36",
    "B04-CA-47",
)


def test_son_exactamente_trece_exhaustiva(casos: dict[str, Any]) -> None:
    exhaustivas = sorted(
        c["identificador_canonico"]
        for c in casos["nivel_1"]
        if c["instanciacion"]["cardinalidad"]["valor"] == "EXHAUSTIVA"
    )
    assert exhaustivas == sorted(LOS_13_EXHAUSTIVA)


@pytest.mark.parametrize("ident", LOS_13_EXHAUSTIVA)
def test_cada_exhaustiva_declara_dominio_y_cierra(casos: dict[str, Any], ident: str) -> None:
    caso = por_ca(casos)[ident]
    adjudicaciones = []
    if (caso.get("adjudicacion") or {}).get("dominio"):
        adjudicaciones.append(caso["adjudicacion"])
    for rama in caso["instanciacion"]["ramas"]:
        if rama.get("adjudicacion"):
            adjudicaciones.append(rama["adjudicacion"])
            assert rama["cardinalidad_de_la_rama"] in ("EXHAUSTIVA", "EXACTA")
    assert adjudicaciones, f"{ident} sin adjudicación calculable"
    for adj in adjudicaciones:
        assert adj["resultado_esperado"] == adj["elegibles_semanticos"]
        assert adj["pendientes_por_limite"] == []
        pendientes = set(adj["pendientes_por_limite"])
        prohibidos = {p["id"] for p in adj["prohibidos_entre_candidatos"]}
        assert not pendientes & prohibidos


def test_resultados_exactos_de_los_cierres_nombrados(casos: dict[str, Any]) -> None:
    ca = por_ca(casos)
    assert ca["B04-CA-02"]["adjudicacion"]["resultado_esperado"] == ["MEM-002"]
    assert ca["B04-CA-03"]["adjudicacion"]["resultado_esperado"] == []
    assert ca["B04-CA-08"]["adjudicacion"]["resultado_esperado"] == ["DEC-005", "MEM-006"]
    assert ca["B04-CA-22"]["adjudicacion"]["resultado_esperado"] == [
        "DEC-001",
        "DEC-005",
        "DEC-009",
        "DEC-011",
        "DEC-014",
        "DEC-015",
    ]
    assert ca["B04-CA-25"]["adjudicacion"]["resultado_esperado"] == ["MEM-011"]
    assert ca["B04-CA-31"]["adjudicacion"]["resultado_esperado"] == list(S4.CRITICOS_ALFA_V0_4)
    ramas47 = {r["sufijo"]: r for r in ca["B04-CA-47"]["instanciacion"]["ramas"]}
    assert ramas47["R1"]["candidatos_elegibles"] == ["DEC-011", "DEC-015"]
    assert ramas47["R2"]["candidatos_elegibles"] == ["DEC-005", "DEC-009", "DEC-014"]
    assert ramas47["R3"]["candidatos_elegibles"] == ["DEC-005", "DEC-014", "DEC-015"]
    exclusiones = {
        e["id"]: e["dimension"] for e in ca["B04-CA-22"]["adjudicacion"]["excluidos_por_estado"]
    }
    assert exclusiones == {"DEC-012": "validez", "DEC-013": "tiempo_valido"}
    assert ca["B04-CA-22"]["adjudicacion"]["dominio"]["tiempo"] == {
        "operador": "SOLAPA_INTERVALO",
        "desde": "2026-01-10T00:00:00Z",
        "hasta": "2026-03-20T00:00:00Z",
    }


def test_ca36_r1_es_solo_historico_por_dec016(casos: dict[str, Any]) -> None:
    rama = {r["sufijo"]: r for r in por_ca(casos)["B04-CA-36"]["instanciacion"]["ramas"]}["R1"]
    assert rama["estado_suficiencia_esperado"] == "SOLO_HISTORICO"
    exclusiones = rama["adjudicacion"]["excluidos_por_estado"]
    assert [(e["id"], e["dimension"]) for e in exclusiones] == [("DEC-016", "tiempo_valido")]
    assert rama["adjudicacion"]["resultado_esperado"] == []


def test_el_oraculo_del_validador_reproduce_todas_las_adjudicaciones(
    conformidad: dict[str, Any], casos: dict[str, Any]
) -> None:
    assert fallos(V4._adjudicacion_recalculada, conformidad, casos) == []
    assert fallos(V4._invariantes_adjudicacion, casos) == []


# ===========================================================================
# Canon/instanciación · modos, insuficiencia, tolerancias
# ===========================================================================


def test_modos_clasificados_individualmente(canon: CS4.Canon, casos: dict[str, Any]) -> None:
    assert fallos(V4._operacion_y_modo, canon, casos) == []
    ca = por_ca(casos)
    for ident, canonicos, derivados in (
        ("B04-CA-10", {"M4"}, {"M1"}),
        ("B04-CA-24", {"M1"}, {"M4"}),
        ("B04-CA-49", {"M4"}, {"M3"}),
        ("B04-CA-09", {"M1", "M4"}, set()),
    ):
        modos = ca[ident]["ficha_pdp_7"]["operacion_y_modo"]["valor"]["modos"]
        assert {m["modo"] for m in modos if m["estado"] == "CANONICO"} == canonicos, ident
        assert {m["modo"] for m in modos if m["estado"] == "DERIVADO_PROPUESTO"} == derivados


def test_operacion_siempre_derivada(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"] + casos["nivel_1_pdp"]:
        campo = caso["ficha_pdp_7"]["operacion_y_modo"]
        assert campo["estado"] == "DERIVADO_PROPUESTO"
        assert campo["valor"]["operacion"]["estado"] == "DERIVADO_PROPUESTO"


def test_insuficiencia_por_rama_y_vocabulario_cerrado(casos: dict[str, Any]) -> None:
    assert fallos(V4._insuficiencia, casos) == []
    ramas = {
        (c["identificador_canonico"], r["sufijo"]): r
        for c in casos["nivel_1"]
        for r in c["instanciacion"]["ramas"]
    }
    assert ramas[("B04-CA-49", "R2")]["etapa_de_la_rama"] is None  # M4: sin escalera
    assert ramas[("B04-CA-49", "R1")]["etapa_de_la_rama"] == "E4"  # M3 con E4 canónico
    bloque = {
        b["rama"]: b
        for c in casos["nivel_1"]
        if c["identificador_canonico"] == "B04-CA-49"
        for b in c["ficha_pdp_7"][S4.CAMPO_INSUFICIENCIA]["valor"]
    }
    assert bloque["R2"]["aplica"] == "NO_APLICA"
    assert "M4" in bloque["R2"]["razon"]
    assert bloque["R1"]["transiciones"][-1]["siguiente_etapa_permitida"] == "E4"


def test_magnitudes_permite_identificadores_y_rechaza_valores() -> None:
    assert not S4.magnitud_inventada("Depende de RED-032, B04-RF-26 y ADR002-TOL-209.")
    assert not S4.magnitud_inventada("Orden y equivalencia B04/B05: mismos críticos y estados.")
    assert S4.magnitud_inventada("banda congelada de 250 ms")
    assert S4.magnitud_inventada("al menos el 95 % de los casos")
    assert S4.magnitud_inventada("3 resultados por consulta")


def test_tolerancias_sin_magnitudes_pendientes(casos: dict[str, Any]) -> None:
    assert fallos(V4._tolerancias, casos) == []


# ===========================================================================
# PDP-CA · recuento, referencias 50+2, reglas y exclusiones
# ===========================================================================


def test_pdp_funcionales_sin_vocabulario_de_recuperacion(
    casos: dict[str, Any], referencias: dict[str, Any]
) -> None:
    assert fallos(V4._pdp_funcionales, casos, referencias) == []
    for caso in casos["nivel_1_pdp"]:
        inst = caso["instanciacion"]
        for campo in S4.CAMPOS_RECUPERACION_NO_APLICABLES:
            assert inst[campo]["valor"] is None
            assert "NO_APLICA" in inst[campo]["justificacion"]


def test_recuento_falsable_por_oraculo_propio(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1_pdp"]:
        ref = caso["ficha_pdp_7"]["referencia"]["valor"]
        grupos: dict[Any, list[str]] = {}
        for consumidor in ref["registros_sinteticos_de_consumidores"]:
            clave = (
                tuple(sorted(consumidor["dependencias"]))
                if "dependencias" in consumidor
                else consumidor["interprete"]
            )
            grupos.setdefault(clave, []).append(consumidor["id"])
        assert len(grupos) == ref["recuento_esperado_independientes"]
        assert any(len(v) > 1 for v in grupos.values()), "sin par no independiente: no falsable"


def test_referencias_50_mas_2(referencias: dict[str, Any]) -> None:
    tipos = [r["tipo_referencia"] for r in referencias["referencias_nivel_1"]]
    assert len(tipos) == 52
    assert tipos.count(S4.TIPO_REFERENCIA_RECUPERACION) == 50
    assert tipos.count(S4.TIPO_REFERENCIA_RECUENTO) == 2
    for ref in referencias["referencias_nivel_1"]:
        if ref["tipo_referencia"] == S4.TIPO_REFERENCIA_RECUENTO:
            assert "referencia_de_recuento" in ref
            assert "instanciacion" not in ref  # no finge ser una referencia de recuperación


def test_reglas_del_arnes_y_exclusiones(canon: CS4.Canon, artefactos: dict[str, Any]) -> None:
    assert (
        fallos(
            V4._pdp_y_reglas,
            canon,
            artefactos["pdp_cases_v0_3.json"],
            artefactos["pdp_harness_rules_v0_2.json"],
        )
        == []
    )
    estados = {
        r["identificador_canonico"]: r["estado_de_la_fuente"]
        for r in artefactos["pdp_harness_rules_v0_2.json"]["reglas"]
    }
    assert estados["PDP-CA-02"] == "APROBADO"
    assert estados["PDP-CA-03"] == "PROPUESTO"
    assert estados["PDP-CA-06"] == "PUERTA_NO_SATISFECHA"


def test_ca18_exacta_vacia_justificada(casos: dict[str, Any]) -> None:
    caso = por_ca(casos)["B04-CA-18"]
    assert caso["instanciacion"]["cardinalidad"]["valor"] == "EXACTA"
    adj = caso["adjudicacion"]
    assert adj["resultado_esperado"] == []
    assert [(e["id"], e["dimension"]) for e in adj["excluidos_por_estado"]] == [
        ("DOC-004", "accesible")
    ]
    assert caso["instanciacion"]["parada"]["valor"] == "S7"


# ===========================================================================
# T0, congelables, rendimiento y conservación
# ===========================================================================


def test_t0_fuera_de_congelables(artefactos: dict[str, Any], casos: dict[str, Any]) -> None:
    assert fallos(V4._t0, artefactos, casos) == []
    proyeccion = artefactos["t0_preexecution_projection_v0_2.json"]
    assert proyeccion["normativo"] is False and proyeccion["congelable"] is False
    assert "t0_preexecution_projection_v0_2.json" not in S4.CONGELABLES_V0_4


def test_rendimiento_intacto_y_delimitado(manifiesto: dict[str, Any]) -> None:
    sha = hashlib.sha256((AQUI / "performance_corpus_v0_2.json").read_bytes()).hexdigest()
    assert sha == S4.SHA256_PERFORMANCE_V0_2 == manifiesto["corpus_rendimiento"]["sha256"]
    alcance = manifiesto["corpus_rendimiento"]["alcance_de_medida"]
    assert "calidad_funcional" in alcance["no_mide"]
    assert "comparacion_de_senales_entre_ADR002_A_B_C_D" in alcance["no_mide"]
    assert "coste" in alcance["mide"]


def test_guardas_medidas_dentro_de_cota() -> None:
    perf = json.loads((AQUI / "performance_corpus_v0_2.json").read_text(encoding="utf-8"))
    medidas = V4.calcular_guardas(perf)
    inf = V4.Informe()
    V4._cotas_guardas(medidas, inf)
    assert not inf.fallos, medidas
    assert medidas["im_tema_proyecto_bits"] <= 0.01
    assert medidas["exceso_estado_palabra_max"] <= 0.25
    assert medidas["proyectos_minimos_por_entidad_con_alias"] >= 2
    assert medidas["cuota_maxima_tipo_relacion"] <= 0.40
    assert 0.35 <= medidas["relaciones_intra_proyecto"] <= 0.65


def test_artefactos_anteriores_intactos() -> None:
    for nombre in V4.ARTEFACTOS_ANTERIORES:
        assert (AQUI / nombre).is_file(), nombre


def test_validador_v0_4_en_verde_y_no_mutante() -> None:
    antes = V4._instantanea()
    inf, _informe = V4.validar()
    assert not inf.fallos, [c["comprobacion"] for c in inf.fallos]
    assert V4._instantanea() == antes


# ===========================================================================
# MUTACIONES NEGATIVAS OBLIGATORIAS (03D)
# ===========================================================================


def test_negativa_01_eliminar_mem006_de_ca08(
    conformidad: dict[str, Any], casos: dict[str, Any]
) -> None:
    roto = copy.deepcopy(casos)
    adj = por_ca(roto)["B04-CA-08"]["adjudicacion"]
    adj["resultado_esperado"] = ["DEC-005"]
    adj["elegibles_semanticos"] = ["DEC-005"]
    detectados = fallos(V4._adjudicacion_recalculada, conformidad, roto)
    assert "el oráculo independiente reproduce las 66 adjudicaciones declaradas" in detectados


def test_negativa_02_eliminar_dec014_de_ca22(
    conformidad: dict[str, Any], casos: dict[str, Any]
) -> None:
    roto = copy.deepcopy(casos)
    adj = por_ca(roto)["B04-CA-22"]["adjudicacion"]
    adj["resultado_esperado"] = [x for x in adj["resultado_esperado"] if x != "DEC-014"]
    adj["elegibles_semanticos"] = [x for x in adj["elegibles_semanticos"] if x != "DEC-014"]
    detectados = fallos(V4._adjudicacion_recalculada, conformidad, roto)
    assert "el oráculo independiente reproduce las 66 adjudicaciones declaradas" in detectados


def test_negativa_03_elegible_no_adjudicado_en_ca31(
    conformidad: dict[str, Any], casos: dict[str, Any]
) -> None:
    roto = coherente(copy.deepcopy(conformidad))
    sexto = copy.deepcopy(next(i for i in roto["items"] if i["id"] == "MEM-025"))
    sexto["id"] = "MEM-113"
    sexto["text"] = "El uso del montacargas requiere permiso escrito del responsable."
    roto["items"].append(sexto)
    roto = coherente(roto)
    detectados = fallos(V4._adjudicacion_recalculada, roto, casos)
    assert "el oráculo independiente reproduce las 66 adjudicaciones declaradas" in detectados
    detectados = fallos(V4._puente_critico, roto, casos)
    assert "PRJ-ALFA contiene exactamente los cinco críticos del canon de CA-31" in detectados


def test_negativa_04_pendiente_confundido_con_prohibido_en_ca44(
    conformidad: dict[str, Any], casos: dict[str, Any]
) -> None:
    roto = copy.deepcopy(casos)
    adj = por_ca(roto)["B04-CA-44"]["adjudicacion"]
    adj["pendientes_por_limite"] = []
    adj["prohibidos_entre_candidatos"].append({"id": "MEM-106", "razon": "DISTRACTOR_RUIDO"})
    detectados = fallos(V4._invariantes_adjudicacion, roto) + fallos(
        V4._adjudicacion_recalculada, conformidad, roto
    )
    assert any("invariantes de adjudicación" in d or "oráculo" in d for d in detectados)


def test_negativa_05_septimo_critico_vigente_en_ca44(
    conformidad: dict[str, Any], casos: dict[str, Any]
) -> None:
    roto = coherente(copy.deepcopy(conformidad))
    septimo = copy.deepcopy(next(i for i in roto["items"] if i["id"] == "MEM-101"))
    septimo["id"] = "MEM-113"
    septimo["text"] = "Restricción esencial dispersa número 13 del expediente Gamma."
    roto["items"].append(septimo)
    roto = coherente(roto)
    detectados = fallos(V4._puente_critico, roto, casos)
    assert "puente canon<->censo: CA-31 5/5, CA-44 6/5/1, CA-26 11/11, CA-38 12/10/2" in detectados
    detectados = fallos(V4._adjudicacion_recalculada, roto, casos)
    assert "el oráculo independiente reproduce las 66 adjudicaciones declaradas" in detectados


def test_negativa_06_traza_ca31_mantenida_en_mem101(
    conformidad: dict[str, Any], casos: dict[str, Any]
) -> None:
    roto = coherente(copy.deepcopy(conformidad))
    for item in roto["items"]:
        if item["id"] == "MEM-101":
            item["traza"] = ["B04-CA-26", "B04-CA-31", "B04-CA-38", "B04-CA-44"]
    roto = coherente(roto)
    detectados = fallos(V4._puente_critico, roto, casos)
    assert (
        "ninguna mención atribuye MEM-101…112 a CA-31; traza y criticidad compartidas" in detectados
    )


def test_negativa_07_variable_inexistente_en_insuficiencia(casos: dict[str, Any]) -> None:
    roto = copy.deepcopy(casos)
    bloque = roto["nivel_1"][0]["ficha_pdp_7"][S4.CAMPO_INSUFICIENCIA]["valor"]
    for entrada in bloque:
        if entrada.get("transiciones"):
            entrada["transiciones"][0]["variables_observadas"] = ["variable_inventada"]
    detectados = fallos(V4._insuficiencia, roto)
    assert "insuficiencia por rama: vocabulario cerrado, M3/M4 sin escalera heredada" in detectados


def test_negativa_08_magnitud_250ms_bajo_pendiente(casos: dict[str, Any]) -> None:
    roto = copy.deepcopy(casos)
    campo = por_ca(roto)["B04-CA-37"]["ficha_pdp_7"]["tolerancias"]
    campo["valor"]["regla"] = "banda congelada de 250 ms entre ausencia y no reportable"
    detectados = fallos(V4._tolerancias, roto)
    assert (
        "tolerancias: distinción id/pendiente y prohibición de magnitudes inventadas" in detectados
    )


def _duplicar_anexo_b_bajo_otro_contexto(destino: Path) -> None:
    """Reescribe el DOCX del Plan insertando una copia del Anexo B lejos de él."""
    origen = CS3.FUENTES / CS3.PDP
    with zipfile.ZipFile(origen) as zf:
        xml = zf.read("word/document.xml")
    apertura = re.compile(rb"<w:tbl(\s[^>]*?)?>")
    cierre = b"</w:tbl>"
    rangos: list[tuple[int, int]] = []
    pos = 0
    while True:
        m = apertura.search(xml, pos)
        if not m:
            break
        profundidad, cursor = 1, m.end()
        while profundidad:
            siguiente = apertura.search(xml, cursor)
            fin = xml.find(cierre, cursor)
            if siguiente and siguiente.start() < fin:
                profundidad += 1
                cursor = siguiente.end()
            else:
                profundidad -= 1
                cursor = fin + len(cierre)
        rangos.append((m.start(), cursor))
        pos = cursor
    anexo = next(
        (a, b) for a, b in rangos if b"Caso(s) exactos" in xml[a:b] and b"RED-079" in xml[a:b]
    )
    copia = xml[anexo[0] : anexo[1]]
    lejos = rangos[10][0]
    mutado = xml[:lejos] + copia + xml[lejos:]
    destino.mkdir(parents=True, exist_ok=True)
    for nombre in (CS3.B04, CS3.PDP, CS3.ARQ00, "MANIFEST.md"):
        (destino / nombre).write_bytes((CS3.FUENTES / nombre).read_bytes())
    with (
        zipfile.ZipFile(origen) as zin,
        zipfile.ZipFile(destino / CS3.PDP, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for info in zin.infolist():
            datos = mutado if info.filename == "word/document.xml" else zin.read(info.filename)
            zout.writestr(info, datos)


def test_negativa_09_anexo_b_duplicado_bajo_otro_contexto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _duplicar_anexo_b_bajo_otro_contexto(tmp_path)
    monkeypatch.setattr(CS3, "FUENTES", tmp_path)
    CS3.tablas.cache_clear()
    try:
        # El v0.3 no lo veía (la copia está bajo otro contexto): el censo v0.4 sí.
        assert len(CS3.anexo_b()) == 79
        with pytest.raises(CS3.TablaCanonicaError, match="cabecera"):
            CS4.verificar_censo_de_cabeceras()
    finally:
        monkeypatch.undo()
        CS3.tablas.cache_clear()


def test_negativa_10_metrica_externa_con_sintaxis_desconocida() -> None:
    for celda in ("B08-M12 y M25", "B08-M12 · B08-M25", "B05-M16 bis", "M25"):
        with pytest.raises(CS4.FuenteCanonicaError):
            CS4.expandir_metricas_estricta(celda)


def test_negativa_11_prevision_t0_copiada_al_manifiesto(
    artefactos: dict[str, Any], casos: dict[str, Any]
) -> None:
    rotos = copy.deepcopy(artefactos)
    rotos["benchmark_manifest_v0_4.json"]["prevision_t0"] = rotos[
        "t0_preexecution_projection_v0_2.json"
    ]["proyecciones"][:2]
    detectados = fallos(V4._t0, rotos, casos)
    assert "ningún congelable —manifiesto incluido— contiene previsión sobre T0" in detectados


def test_negativa_12_performance_corpus_alterado(
    tmp_path: Path, manifiesto: dict[str, Any]
) -> None:
    original = (AQUI / "performance_corpus_v0_2.json").read_text(encoding="utf-8")
    alterado = tmp_path / "performance_corpus_v0_2.json"
    alterado.write_text(original.replace("Arrecife", "Arrecife ", 1), encoding="utf-8")
    inf = V4.Informe()
    V4._guardas_rendimiento(alterado, manifiesto, inf)
    assert "performance_corpus_v0_2.json es byte a byte el congelado (SHA-256)" in [
        c["comprobacion"] for c in inf.fallos
    ]


def test_negativa_13_correlacion_tema_proyecto_coherente() -> None:
    perf = json.loads((AQUI / "performance_corpus_v0_2.json").read_text(encoding="utf-8"))
    marcadores = ("nebulosa", "cometa", "eclipse", "orbita", "satelite", "galaxia", "telar")
    for elemento in perf["items"]:
        texto = elemento["text"].lower()
        elemento["project_id"] = (
            "PRJ-ARRECIFE" if any(m in texto for m in marcadores) else "PRJ-CUMBRE"
        )
    for mensaje in perf["mensajes"]:
        texto = mensaje["texto"].lower()
        mensaje["project_id"] = (
            "PRJ-ARRECIFE" if any(m in texto for m in marcadores) else "PRJ-CUMBRE"
        )
    medidas = V4.calcular_guardas(perf)
    inf = V4.Informe()
    V4._cotas_guardas(medidas, inf)
    assert inf.fallos, medidas
    assert medidas["im_tema_proyecto_bits"] > S4.GUARDAS_RENDIMIENTO["im_tema_proyecto_bits_max"]


def test_negativa_13b_alias_confinados_y_relaciones_concentradas() -> None:
    perf = json.loads((AQUI / "performance_corpus_v0_2.json").read_text(encoding="utf-8"))
    con_alias = {e["id"] for e in perf["entidades"] if e["alias"]}
    for item in perf["items"]:
        if set(item["entity_ids"]) & con_alias:
            item["project_id"] = "PRJ-ARRECIFE"
    for relacion in perf["relaciones"][:150]:
        relacion["tipo"] = "APOYA"
    medidas = V4.calcular_guardas(perf)
    inf = V4.Informe()
    V4._cotas_guardas(medidas, inf)
    fallan = inf.fallos[0]["detalle"]["fallan"] if inf.fallos else []
    assert "alias_confinados" in fallan
    assert "cuota_tipo_relacion" in fallan


def test_negativa_14_una_dec016_que_cambia_otro_caso(
    conformidad: dict[str, Any], casos: dict[str, Any], manifiesto: dict[str, Any]
) -> None:
    roto = coherente(copy.deepcopy(conformidad))
    fuga = copy.deepcopy(next(i for i in roto["items"] if i["id"] == "DEC-016"))
    fuga["id"] = "DEC-017"
    fuga["project_id"] = "PRJ-BETA"
    fuga["text"] = "El presupuesto de contingencia era temporal."
    roto["items"].append(fuga)
    roto = coherente(roto)
    detectados = fallos(V4._adjudicacion_recalculada, roto, casos)
    assert "el oráculo independiente reproduce las 66 adjudicaciones declaradas" in detectados
    # Y el barrido directo: si DEC-016 viviera en BETA, arrastraría CA-22 y CA-47.
    encaminado = coherente(copy.deepcopy(conformidad))
    for item in encaminado["items"]:
        if item["id"] == "DEC-016":
            item["project_id"] = "PRJ-BETA"
    encaminado = coherente(encaminado)
    detectados = fallos(V4._barrido_dec016, encaminado, casos, manifiesto)
    assert "barrido de impacto de DEC-016: solo la rama R1 de B04-CA-36 cambia" in detectados
