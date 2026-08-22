"""Contrato v0.3 del benchmark de ADR-002, verificado contra los DOCX canónicos.

Estas pruebas no ejecutan T0, no ejecutan `ADR002-A/B/C/D` y no miden nada. Los
contratos v0.1 y v0.2 se siguen verificando aparte y sin cambios en
``test_corpus_contract.py`` y ``test_corpus_contract_v0_2.py``.

La segunda mitad del fichero son **pruebas negativas**: mutan una copia en
memoria de los artefactos y comprueban que el validador lo detecta. Una
comprobación que no falla ante la mutación correspondiente no vale nada.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.benchmark import build_corpus_v0_3 as B3
from experiments.adr002.benchmark import canonical_source_v0_3 as CS3
from experiments.adr002.benchmark import schema_v0_3 as S3
from experiments.adr002.benchmark import validate_corpus_v0_3 as V3

AQUI = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def canon() -> CS3.Canon:
    return CS3.cargar_canon()


@pytest.fixture(scope="module")
def artefactos() -> dict[str, Any]:
    return V3.cargar()


@pytest.fixture(scope="module")
def casos(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["cases_v0_3.json"]


@pytest.fixture(scope="module")
def referencias(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["references_v0_3.json"]


@pytest.fixture(scope="module")
def conformidad(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["conformance_corpus_v0_3.json"]


@pytest.fixture(scope="module")
def rendimiento(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["performance_corpus_v0_2.json"]


@pytest.fixture(scope="module")
def pdp(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["pdp_cases_v0_2.json"]


@pytest.fixture(scope="module")
def reglas(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["pdp_harness_rules_v0_1.json"]


@pytest.fixture(scope="module")
def proyeccion(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["t0_preexecution_projection_v0_1.json"]


@pytest.fixture(scope="module")
def lexico(conformidad: dict[str, Any], casos: dict[str, Any]) -> B3.LexicoProtegido:
    return B3.construir_lexico(conformidad, casos)


def fallos(funcion: Any, *args: Any) -> list[str]:
    """Ejecuta una comprobación del validador y devuelve los nombres que fallaron."""
    inf = V3.Informe()
    funcion(*args, inf)
    return [c["comprobacion"] for c in inf.fallos]


# ===========================================================================
# B-01 · lector canónico por identidad
# ===========================================================================


def test_cada_identidad_resuelve_a_una_sola_tabla() -> None:
    inventario = CS3.inventario_de_tablas()
    assert len(inventario) == len(CS3.IDENTIDADES)
    indices = {(t["documento"], t["indice_fisico"]) for t in inventario}
    assert len(indices) == len(inventario)


def test_el_anexo_b_y_el_registro_red_son_tablas_distintas() -> None:
    anexo = CS3.tabla("pdp_anexo_b")
    registro = CS3.tabla("pdp_registro_red")
    assert anexo.indice != registro.indice
    assert anexo.cabecera != registro.cabecera
    assert len(anexo.filas) == len(registro.filas) == 79


def test_las_invariantes_minimas_se_cumplen(canon: CS3.Canon) -> None:
    medidas = canon.medidas()
    assert medidas["casos_b04"] == 50
    assert medidas["filas_anexo_b"] == 79
    assert medidas["familias_pdp"] == 25
    assert medidas["casos_pdp"] == 28
    assert medidas["campos_ficha_pdp7"] == 14
    assert medidas["requisitos_b04"] == 32
    assert medidas["metricas_b04"] == 21
    assert medidas["ca_b04_nombrados_por_anexo_b"] >= 20


def test_la_ficha_pdp7_tiene_exactamente_los_catorce_campos_canonicos(canon: CS3.Canon) -> None:
    assert tuple(canon.ficha_pdp7) == CS3.CAMPOS_PDP7_CANONICOS


def test_las_familias_pdp_traen_su_texto_de_cobertura(canon: CS3.Canon) -> None:
    assert len(canon.familias) == 25
    assert all(d["cobertura_minima"] and d["nombre"] for d in canon.familias.values())


def test_el_anexo_b_conserva_las_metricas_externas() -> None:
    metricas = CS3.metricas_del_anexo_b()
    assert "B05-M16" in metricas["externas_canonicas"]
    assert "B08-M25" in metricas["externas_canonicas"]
    assert all("-M" in m for m in metricas["externas_canonicas"])


def test_las_metricas_abreviadas_arrastran_su_bloque() -> None:
    assert CS3._expandir_metricas("B08-M12/M25") == ["B08-M12", "B08-M25"]
    assert CS3._expandir_metricas("B04-M21/B05-M16") == ["B04-M21", "B05-M16"]
    assert CS3._expandir_metricas("PDP-M01\u2013M17") == [f"PDP-M{n:02d}" for n in range(1, 18)]


def test_el_anexo_b_es_bidireccional(casos: dict[str, Any]) -> None:
    asignaciones = CS3.asignaciones_canonicas_por_ca()
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    for ca, esperado in asignaciones.items():
        trazas = por_ca[ca]["trazabilidad"]
        assert set(esperado["red"]) == set(trazas["traza_red_canonica_anexo_b"]), ca
        assert set(esperado["metricas"]) == set(trazas["metrica_canonica_anexo_b"]), ca
        assert set(esperado["familias"]) == set(trazas["familia_canonica_anexo_b"]), ca


# ===========================================================================
# B-02 · corpus de rendimiento
# ===========================================================================


def test_el_corpus_de_rendimiento_tiene_la_escala_exacta(rendimiento: dict[str, Any]) -> None:
    conteos = B3.medir_distribucion(rendimiento)["conteos_reales"]
    assert conteos["mensajes"] == 5000
    assert conteos["recuerdos"] == 500
    assert conteos["decisiones"] == 50
    assert conteos["proyectos"] == 2
    assert conteos["proyectos_referenciados"] == 2


def test_la_distribucion_no_es_degenerada(rendimiento: dict[str, Any]) -> None:
    d = rendimiento["distribucion_observada"]
    inv = S3.INVARIANTES_DISTRIBUCION
    assert d["longitud_texto"]["longitudes_distintas"] >= inv["longitudes_distintas_min"]
    assert d["vocabulario"]["tamano"] >= inv["vocabulario_min"]
    assert (
        inv["zipf_pendiente_min"] <= d["vocabulario"]["pendiente_zipf"] <= inv["zipf_pendiente_max"]
    )
    assert d["textos"]["proporcion_distintos"] >= inv["textos_distintos_min"]
    assert max(d["reparto_por_proyecto"].values()) <= inv["cuota_maxima_por_proyecto"]
    assert d["fechas"]["meses_distintos"] >= inv["meses_distintos_min"]
    assert d["relaciones"]["tipos_distintos"] >= inv["tipos_de_relacion_min"]


def test_ningun_texto_de_rendimiento_usa_numero_de_secuencia(
    rendimiento: dict[str, Any],
) -> None:
    assert not [t for t in B3.textos_del_corpus(rendimiento) if any(c.isdigit() for c in t)]


def test_el_lexico_de_rendimiento_es_disjunto(
    lexico: B3.LexicoProtegido, rendimiento: dict[str, Any]
) -> None:
    assert not [t for t in B3.textos_del_corpus(rendimiento) if lexico.detectar(t)]


@pytest.mark.parametrize(("base", "variante"), S3.PARES_MINIMOS_DE_CONTAMINACION)
def test_la_contaminacion_detecta_los_pares_minimos(
    lexico: B3.LexicoProtegido, base: str, variante: str
) -> None:
    assert base in lexico.tokens
    assert lexico.detectar(variante)


def test_la_relacion_de_sufijo_reconoce_singular_y_plural() -> None:
    assert B3._relacion_de_sufijo("turnos", "turno")
    assert not B3._relacion_de_sufijo("turno", "turno")


# ===========================================================================
# B-03 · cierre exhaustivo de CA-47
# ===========================================================================


def test_el_cierre_de_ca47_se_deriva_del_corpus(conformidad: dict[str, Any]) -> None:
    cierre = B3.cierre_ca47(conformidad["items"])
    assert cierre == conformidad["cierre_exhaustivo_ca47"]


def test_ca47_r2_incluye_dec_005_009_y_014(conformidad: dict[str, Any]) -> None:
    assert {"DEC-005", "DEC-009", "DEC-014"} <= set(
        conformidad["cierre_exhaustivo_ca47"]["R2"]["elegibles"]
    )


def test_ca47_r3_incluye_dec_005_014_y_015(conformidad: dict[str, Any]) -> None:
    assert {"DEC-005", "DEC-014", "DEC-015"} <= set(
        conformidad["cierre_exhaustivo_ca47"]["R3"]["elegibles"]
    )


def test_las_tres_ramas_de_ca47_no_colapsan(conformidad: dict[str, Any]) -> None:
    conjuntos = {tuple(v["elegibles"]) for v in conformidad["cierre_exhaustivo_ca47"].values()}
    assert len(conjuntos) == 3


def test_los_prohibidos_de_ca47_son_el_complemento(conformidad: dict[str, Any]) -> None:
    for rama in conformidad["cierre_exhaustivo_ca47"].values():
        assert sorted(rama["elegibles"] + rama["prohibidos"]) == rama["universo_en_ambito"]


# ===========================================================================
# B-04 · casos funcionales frente a reglas del arnés
# ===========================================================================


def test_solo_dos_pdp_ca_son_casos_funcionales(casos: dict[str, Any]) -> None:
    assert {c["identificador_canonico"] for c in casos["nivel_1_pdp"]} == {
        "PDP-CA-09",
        "PDP-CA-22",
    }


def test_esos_dos_son_los_que_el_anexo_b_ancla() -> None:
    assert set(CS3.asignaciones_canonicas_por_pdp_ca()) == {"PDP-CA-09", "PDP-CA-22"}
    assert CS3.asignaciones_canonicas_por_pdp_ca()["PDP-CA-09"]["red"] == ["RED-017"]


def test_las_seis_reglas_viven_en_el_fichero_del_arnes(reglas: dict[str, Any]) -> None:
    assert {r["identificador_canonico"] for r in reglas["reglas"]} == set(S3.PDP_CA_REGLAS_DE_ARNES)
    for regla in reglas["reglas"]:
        assert not set(regla) & set(S3.CAMPOS_PROHIBIDOS_EN_REGLA)
        assert regla["regla_de_ejecucion"] and regla["evidencia_requerida"]
        assert regla["consecuencia"] and regla["estado_aplicabilidad"]


def test_los_veintiocho_pdp_ca_quedan_clasificados_sin_solape(
    canon: CS3.Canon, pdp: dict[str, Any]
) -> None:
    a = set(pdp["casos_funcionales_nivel_1"])
    b = set(pdp["reglas_de_protocolo_del_arnes"])
    c = set(pdp["casos_fuera_de_alcance"])
    assert a | b | c == set(canon.casos_pdp)
    assert not (a & b) and not (a & c) and not (b & c)


# ===========================================================================
# Ficha del PDP §7, tolerancias, insuficiencia y T0
# ===========================================================================


def test_cada_caso_lleva_los_catorce_campos_con_su_procedencia(casos: dict[str, Any]) -> None:
    esperados = set(S3.CAMPOS_PDP7.values()) | {S3.CAMPO_INSUFICIENCIA}
    for caso in casos["nivel_1"] + casos["nivel_1_pdp"]:
        assert set(caso["ficha_pdp_7"]) == esperados, caso["id"]
        for campo in caso["ficha_pdp_7"].values():
            assert set(campo) == set(S3.CLAVES_CAMPO)
            assert campo["estado"] in S3.ESTADOS_CAMPO
            assert campo["justificacion"]


@pytest.mark.parametrize(
    ("ca", "tolerancia"),
    [
        ("B04-CA-37", "ADR002-TOL-201"),
        ("B04-CA-48", "ADR002-TOL-201"),
        ("B04-CA-39", "ADR002-TOL-001"),
    ],
)
def test_tolerancia_id_frente_a_valor_pendiente(
    casos: dict[str, Any], ca: str, tolerancia: str
) -> None:
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    campo = por_ca[ca]["ficha_pdp_7"]["tolerancias"]
    assert campo["valor"]["tolerancia_id"] == tolerancia
    assert campo["valor"]["valor_pendiente_en"] == "ADR002-TOL-209"
    assert campo["estado"] == "PENDIENTE_TOL209"


def test_la_insuficiencia_esta_estructurada_por_rama(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        bloque = caso["ficha_pdp_7"][S3.CAMPO_INSUFICIENCIA]["valor"]
        assert bloque
        ramas = [r["sufijo"] for r in caso["instanciacion"]["ramas"]] or ["CASO_BASE"]
        assert [b["rama"] for b in bloque] == ramas
        for entrada in bloque:
            if entrada["aplica"] == "NO_APLICA":
                assert entrada["razon"]
            else:
                assert entrada["transiciones"]


def test_ca39_declara_no_aplica_con_razon(casos: dict[str, Any]) -> None:
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    bloque = por_ca["B04-CA-39"]["ficha_pdp_7"][S3.CAMPO_INSUFICIENCIA]["valor"]
    assert all(b["aplica"] == "NO_APLICA" and b["razon"] for b in bloque)


def test_ningun_artefacto_congelable_preve_t0(
    casos: dict[str, Any], referencias: dict[str, Any], reglas: dict[str, Any]
) -> None:
    crudo = json.dumps({"c": casos, "r": referencias, "a": reglas["reglas"]}, ensure_ascii=False)
    for clave in S3.CLAVES_PREVISION_T0:
        assert f'"{clave}"' not in crudo


def test_la_prevision_cubre_todos_los_casos_funcionales(
    casos: dict[str, Any], proyeccion: dict[str, Any]
) -> None:
    funcionales = {c["identificador_canonico"] for c in casos["nivel_1"] + casos["nivel_1_pdp"]}
    assert {p["identificador_canonico"] for p in proyeccion["proyecciones"]} == funcionales
    assert proyeccion["normativo"] is False
    assert proyeccion["congelable"] is False
    assert proyeccion["conteos"]["reglas_de_arnes_proyectadas"] == 0


def test_las_reglas_del_arnes_no_reciben_prevision(
    reglas: dict[str, Any], proyeccion: dict[str, Any]
) -> None:
    proyectados = {p["identificador_canonico"] for p in proyeccion["proyecciones"]}
    assert not proyectados & {r["identificador_canonico"] for r in reglas["reglas"]}


# ===========================================================================
# Validación completa
# ===========================================================================


@pytest.fixture(scope="module")
def validacion() -> tuple[V3.Informe, dict[str, Any]]:
    return V3.validar()


def test_el_validador_v0_3_no_encuentra_fallos(
    validacion: tuple[V3.Informe, dict[str, Any]],
) -> None:
    inf, _informe = validacion
    assert not inf.fallos, [c["comprobacion"] for c in inf.fallos]


def test_el_validador_no_escribe_en_el_arbol_de_trabajo() -> None:
    antes = V3._instantanea()
    V3.validar()
    assert V3._instantanea() == antes


def test_los_artefactos_anteriores_siguen_presentes() -> None:
    for nombre in V3.ARTEFACTOS_ANTERIORES:
        assert (AQUI / nombre).is_file(), nombre


# ===========================================================================
# Pruebas negativas · las catorce mutaciones del paquete 03C §7.3
# ===========================================================================


def test_negativa_01_tabla_docx_movida_o_equivocada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Apuntar la identidad del Anexo B al contexto del Registro RED debe fallar."""
    falsa = dict(CS3.IDENTIDADES)
    falsa["pdp_anexo_b"] = CS3.Identidad(
        documento=CS3.PDP,
        cabecera=CS3.IDENTIDADES["pdp_anexo_b"].cabecera,
        contexto=r"denominador final de RED-1\.0",
        filas=79,
        patron_col0=r"RED-\d{3}",
    )
    monkeypatch.setattr(CS3, "IDENTIDADES", falsa)
    with pytest.raises(CS3.TablaCanonicaError, match="0 tablas candidatas"):
        CS3.tabla("pdp_anexo_b")

    ambigua = dict(CS3.IDENTIDADES)
    ambigua["b04_casos_17"] = CS3.Identidad(
        documento=CS3.B04,
        cabecera=CS3.IDENTIDADES["b04_casos_17"].cabecera,
        contexto=r"17",
        filas=39,
    )
    monkeypatch.setattr(CS3, "IDENTIDADES", ambigua)
    with pytest.raises(CS3.TablaCanonicaError, match="2 tablas candidatas"):
        CS3.tabla("b04_casos_17")


def test_negativa_02_anexo_b_vacio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(CS3, "anexo_b", dict)
    with pytest.raises(CS3.FuenteCanonicaError, match="filas_anexo_b"):
        CS3.cargar_canon()


def test_negativa_03_asignacion_canonica_inventada(
    canon: CS3.Canon, casos: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    roto = copy.deepcopy(casos)
    roto["nivel_1"][0]["trazabilidad"]["traza_red_canonica_anexo_b"].append("RED-099")
    detectados = fallos(V3._anexo_b, roto, artefactos["benchmark_manifest_v0_3.json"])
    assert "artefacto -> canon: ninguna asignación marcada canónica fue inventada" in detectados
    assert "no se acepta ningún identificador inexistente" in detectados


def test_negativa_04_caracter_canonico_cambiado(
    canon: CS3.Canon, casos: dict[str, Any], referencias: dict[str, Any]
) -> None:
    roto = copy.deepcopy(casos)
    roto["nivel_1"][0]["canonico"]["entrada"] += " (editado)"
    detectados = fallos(V3._literalidad, canon, roto, referencias)
    assert "los cuatro campos canónicos coinciden carácter a carácter con el DOCX" in detectados


def test_negativa_05_campo_derivado_marcado_canonico(
    canon: CS3.Canon, casos: dict[str, Any]
) -> None:
    roto = copy.deepcopy(casos)
    roto["nivel_1"][0]["ficha_pdp_7"]["objetivo"]["estado"] = "CANONICO"
    detectados = fallos(V3._ficha_14_campos, canon, roto)
    assert "ningún campo de la ficha se marca CANONICO sin texto literal que lo fije" in detectados


def test_negativa_06_rama_m4_eliminada(canon: CS3.Canon, casos: dict[str, Any]) -> None:
    roto = copy.deepcopy(casos)
    for caso in roto["nivel_1"]:
        if caso["identificador_canonico"] == "B04-CA-09":
            caso["instanciacion"]["ramas"] = [
                r for r in caso["instanciacion"]["ramas"] if r["modo"] != "M4"
            ]
    detectados = fallos(V3._ramas, canon, roto)
    assert "CA-09, CA-10, CA-24 y CA-49 conservan su rama M4" in detectados


def test_negativa_07_ca47_colapsado_o_no_cerrado(
    conformidad: dict[str, Any], casos: dict[str, Any], referencias: dict[str, Any]
) -> None:
    colapsado = copy.deepcopy(casos)
    for caso in colapsado["nivel_1"]:
        if caso["identificador_canonico"] != "B04-CA-47":
            continue
        ramas = {r["sufijo"]: r for r in caso["instanciacion"]["ramas"]}
        ramas["R2"]["candidatos_elegibles"] = list(ramas["R1"]["candidatos_elegibles"])
        ramas["R2"]["candidatos_prohibidos"] = list(ramas["R1"]["candidatos_prohibidos"])
    detectados = fallos(V3._cierre_exhaustivo, conformidad, colapsado, referencias)
    assert "CA-47: el conjunto esperado es exactamente el conjunto elegible calculado" in detectados
    assert "CA-47: las tres ramas producen tres conjuntos distintos y no colapsan" in detectados

    recortado = copy.deepcopy(casos)
    for caso in recortado["nivel_1"]:
        if caso["identificador_canonico"] != "B04-CA-47":
            continue
        for rama in caso["instanciacion"]["ramas"]:
            if rama["sufijo"] == "R2":
                rama["candidatos_elegibles"] = ["DEC-014"]
    detectados = fallos(V3._cierre_exhaustivo, conformidad, recortado, referencias)
    assert (
        "CA-47 R2 incluye DEC-005, DEC-009 y DEC-014; R3 incluye DEC-005, DEC-014 y DEC-015"
        in detectados
    )


def test_negativa_08_veredicto_t0_anticipado(
    casos: dict[str, Any],
    referencias: dict[str, Any],
    reglas: dict[str, Any],
    proyeccion: dict[str, Any],
) -> None:
    roto = copy.deepcopy(casos)
    roto["nivel_1"][0]["t0"]["expresabilidad_prevista"] = "EXPRESABLE_PREVISTO"
    detectados = fallos(V3._t0, roto, referencias, reglas, proyeccion)
    assert "ningún artefacto congelable contiene previsión normativa sobre T0" in detectados


def test_negativa_09_conteo_real_alterado(
    conformidad: dict[str, Any], rendimiento: dict[str, Any]
) -> None:
    roto = copy.deepcopy(conformidad)
    roto["conteos"]["items"] = 999
    assert "los conteos del corpus de conformidad se cuentan sobre los datos" in fallos(
        V3._conformidad, roto
    )
    menos = copy.deepcopy(rendimiento)
    menos["mensajes"] = menos["mensajes"][:-1]
    detectados = fallos(V3._rendimiento, menos)
    assert (
        "5.000 mensajes, 500 recuerdos, 50 decisiones y 2 proyectos, contados sobre los datos"
        in detectados
    )


def test_negativa_10_mensaje_documento_o_relacion_alterado(
    conformidad: dict[str, Any],
) -> None:
    for coleccion, clave in (
        ("mensajes", "texto"),
        ("documentos", "titulo"),
        ("relaciones", "nota"),
    ):
        roto = copy.deepcopy(conformidad)
        roto[coleccion][0][clave] = "contenido sustituido"
        detectados = fallos(V3._conformidad, roto)
        assert "identidad de items, mensajes, documentos y relaciones intacta" in detectados, (
            coleccion
        )


def test_negativa_11_contaminacion_por_raiz_o_alias(
    conformidad: dict[str, Any], casos: dict[str, Any], rendimiento: dict[str, Any]
) -> None:
    for texto in (
        "El registro de turnos quedo registrado.",  # raíz y sufijo
        "Proyecto Atlas Alfa aparece en el relleno.",  # alias de entidad
        "Se fija el presupuesto maximo del proyecto.",  # n-grama y token
    ):
        roto = copy.deepcopy(rendimiento)
        roto["mensajes"][0]["texto"] = texto
        detectados = fallos(V3._contaminacion, conformidad, casos, roto)
        assert (
            "ningún texto del corpus de rendimiento contamina el léxico protegido" in detectados
        ), texto


def test_negativa_12_tecnologia_o_candidato_en_campo_neutral(
    canon: CS3.Canon, artefactos: dict[str, Any]
) -> None:
    roto = copy.deepcopy(artefactos)
    roto["cases_v0_3.json"]["nivel_1"][0]["instanciacion"]["consulta"]["valor"] = (
        "¿Qué devuelve ADR002-B con índice vectorial?"
    )
    detectados = fallos(V3._neutralidad, canon, roto)
    assert (
        "ningún campo neutral de un caso nombra tecnología o candidato sin canon que lo fije"
        in detectados
    )

    otro = copy.deepcopy(artefactos)
    otro["performance_corpus_v0_2.json"]["mensajes"][0]["texto"] = "Se evalua sqlite y faiss."
    detectados = fallos(V3._neutralidad, canon, otro)
    assert (
        "ni el corpus de rendimiento ni las reglas ni la previsión nombran tecnología o candidato"
        in detectados
    )


def test_negativa_13_distribucion_de_rendimiento_degenerada(
    rendimiento: dict[str, Any],
) -> None:
    roto = copy.deepcopy(rendimiento)
    plantilla = "Serie de volumen numero 00001 sin valor."
    for mensaje in roto["mensajes"]:
        mensaje["texto"] = plantilla
    for item in roto["items"]:
        item["text"] = plantilla
        item["condicion"] = None
        item["criticidad"] = None
    for documento in roto["documentos"]:
        documento["titulo"] = plantilla
        documento["texto"] = plantilla if documento["texto"] else None
        documento["afirmacion_atribuida"] = None
    for relacion in roto["relaciones"]:
        relacion["nota"] = plantilla
    roto["distribucion_observada"] = B3.medir_distribucion(roto)
    detectados = fallos(V3._rendimiento, roto)
    assert "sin plantilla repetida: los textos son prácticamente todos distintos" in detectados
    assert "vocabulario amplio con frecuencia aproximadamente Zipf" in detectados
    assert (
        "longitudes de texto con variación material y al menos veinte longitudes distintas"
        in detectados
    )
    assert "ningún texto usa un número de secuencia como fuente de variedad" in detectados


def test_negativa_14_campo_de_la_ficha_pdp7_anadido_o_perdido(
    canon: CS3.Canon, casos: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    perdido = copy.deepcopy(casos)
    del perdido["nivel_1"][0]["ficha_pdp_7"]["objetivo"]
    detectados = fallos(V3._ficha_14_campos, canon, perdido)
    assert (
        "cada caso funcional lleva los catorce campos del PDP §7 y la insuficiencia" in detectados
    )

    anadido = copy.deepcopy(casos)
    anadido["nivel_1"][0]["ficha_pdp_7"]["campo_inventado"] = {
        "valor": None,
        "fuente": "x",
        "seccion": "x",
        "estado": "DERIVADO_PROPUESTO",
        "justificacion": "x",
    }
    detectados = fallos(V3._ficha_14_campos, canon, anadido)
    assert (
        "cada caso funcional lleva los catorce campos del PDP §7 y la insuficiencia" in detectados
    )

    # Y en el propio canon: una fila añadida o perdida en la tabla del PDP §7.
    monkeypatch.setattr(
        CS3,
        "ficha_obligatoria_pdp7",
        lambda: {k: {"definicion": "", "congelacion": ""} for k in CS3.CAMPOS_PDP7_CANONICOS[:13]},
    )
    with pytest.raises(CS3.FuenteCanonicaError, match="campos_ficha_pdp7"):
        CS3.cargar_canon()
