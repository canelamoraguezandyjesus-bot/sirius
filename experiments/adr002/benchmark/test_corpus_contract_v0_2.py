"""Contrato v0.2 del benchmark de ADR-002, verificado contra los DOCX canónicos.

Estas pruebas no ejecutan T0, no ejecutan `ADR002-A/B/C/D` y no miden nada.
Comprueban que el corpus de conformidad, el de rendimiento, los casos, las
referencias y la matriz de PDP-CA son **fieles al canon**, no solo coherentes
entre sí. El contrato v0.1 se sigue verificando aparte, sin cambios, en
``test_corpus_contract.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.benchmark import build_corpus_v0_2 as B2
from experiments.adr002.benchmark import canonical_source as CS
from experiments.adr002.benchmark import schema_v0_2 as S2
from experiments.adr002.benchmark import validate_corpus_v0_2 as V2

AQUI = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def canon() -> CS.Canon:
    return CS.cargar_canon()


@pytest.fixture(scope="module")
def artefactos() -> dict[str, Any]:
    return V2.cargar()


@pytest.fixture(scope="module")
def casos(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["cases_v0_2.json"]


@pytest.fixture(scope="module")
def referencias(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["references_v0_2.json"]


@pytest.fixture(scope="module")
def conformidad(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["conformance_corpus_v0_2.json"]


@pytest.fixture(scope="module")
def rendimiento(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["performance_corpus_v0_1.json"]


@pytest.fixture(scope="module")
def pdp(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["pdp_cases_v0_1.json"]


# --- fuentes canónicas ------------------------------------------------------


def test_las_tres_huellas_coinciden_con_el_manifest(canon: CS.Canon) -> None:
    for nombre, huella in canon.huellas.items():
        assert huella["coincide"], nombre


def test_el_canon_extraido_tiene_el_tamano_declarado(canon: CS.Canon) -> None:
    assert len(canon.casos) == 50
    assert len(canon.anexo) == 79
    assert len(canon.familias) == 25
    assert len(canon.ficha_pdp7) == 14
    assert len(canon.casos_pdp) == 28
    assert len(canon.destinos) == 25


def test_la_regla_de_cardinalidad_se_lee_del_docx() -> None:
    assert CS.s1_prohibida_en_exhaustiva()
    assert "S1 deshabilitado" in CS.reglas_cardinalidad_b04()["EXHAUSTIVA"]


def test_las_alternativas_minimas_de_arq00_conservan_vectorial() -> None:
    alternativas = CS.alternativas_minimas_arq00()
    assert set(alternativas) == {"A", "B", "C", "D"}
    assert "vectorial" in alternativas["B"]
    assert "solo léxica/estructurada" in alternativas["A"]


# --- B-01 · Anexo B ---------------------------------------------------------


def test_toda_asignacion_del_anexo_b_esta_en_la_traza_canonica(casos: dict[str, Any]) -> None:
    asignaciones = CS.asignaciones_canonicas_por_ca()
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    for ca, esperado in asignaciones.items():
        trazas = por_ca[ca]["trazabilidad"]
        assert set(esperado["red"]) <= set(trazas["traza_red_canonica_anexo_b"]), ca
        assert set(esperado["metricas"]) <= set(trazas["metrica_canonica_anexo_b"]), ca
        assert set(esperado["familias"]) <= set(trazas["familia_canonica_anexo_b"]), ca


@pytest.mark.parametrize(
    ("red", "esperados"),
    [
        ("RED-027", ["B04-CA-01", "B04-CA-05", "B04-CA-08", "B04-CA-15"]),
        ("RED-028", ["B04-CA-06", "B04-CA-07", "B04-CA-32", "B04-CA-47"]),
        ("RED-029", ["B04-CA-40", "B04-CA-44"]),
        ("RED-030", ["B04-CA-19", "B04-CA-31", "B04-CA-38"]),
        ("RED-034", ["B04-CA-18", "B04-CA-24"]),
    ],
)
def test_las_cinco_filas_que_la_auditoria_senalo_estan_restituidas(
    casos: dict[str, Any], red: str, esperados: list[str]
) -> None:
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    for ca in esperados:
        assert red in por_ca[ca]["trazabilidad"]["traza_red_canonica_anexo_b"], (red, ca)


def test_lo_adicional_derivado_no_sustituye_al_anexo_b(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        canonica = set(caso["trazabilidad"]["traza_red_canonica_anexo_b"])
        adicional = set(caso["trazabilidad"]["traza_red_adicional_derivada"])
        assert not (canonica & adicional), caso["id"]


def test_red_040_no_se_usa_como_requisito_propio(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        trazas = caso["trazabilidad"]
        assert "RED-040" not in trazas["traza_red_canonica_anexo_b"]
        assert "RED-040" not in trazas["traza_red_adicional_derivada"]


# --- literalidad y unicidad -------------------------------------------------


def test_los_50_ca_aparecen_exactamente_una_vez(casos: dict[str, Any]) -> None:
    vistos = [c["identificador_canonico"] for c in casos["nivel_1"]]
    assert len(vistos) == 50
    assert sorted(vistos) == sorted(S2.CA_TOTALES)
    assert len(set(vistos)) == 50


def test_los_campos_canonicos_son_literales_caracter_a_caracter(
    canon: CS.Canon, casos: dict[str, Any], referencias: dict[str, Any]
) -> None:
    campos = ("riesgo", "entrada", "resultado_esperado", "fallo_observable")
    for caso in casos["nivel_1"]:
        original = canon.casos[caso["identificador_canonico"]]
        for campo in campos:
            assert caso["canonico"][campo] == getattr(original, campo), (caso["id"], campo)
    for ref in referencias["referencias_nivel_1"]:
        original = canon.casos[ref["identificador_canonico"]]
        for campo in campos:
            assert ref["canonico"][campo] == getattr(original, campo), (ref["caso"], campo)


@pytest.mark.parametrize(
    "ca",
    [
        "B04-CA-17",
        "B04-CA-18",
        "B04-CA-21",
        "B04-CA-29",
        "B04-CA-36",
        "B04-CA-37",
        "B04-CA-45",
        "B04-CA-47",
    ],
)
def test_las_comillas_tipograficas_del_canon_se_conservan(
    canon: CS.Canon, casos: dict[str, Any], ca: str
) -> None:
    """Los ocho casos donde el v0.1 sustituyó «“ ”» por «« »»."""
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == ca)
    texto_canon = canon.casos[ca].resultado_esperado + canon.casos[ca].fallo_observable
    texto_art = caso["canonico"]["resultado_esperado"] + caso["canonico"]["fallo_observable"]
    assert texto_art == texto_canon
    assert "«" not in texto_art or "«" in texto_canon


# --- B-02 / M-07 · canon frente a instanciación ----------------------------


def test_el_bloque_canonico_solo_contiene_lo_que_b04_fija(casos: dict[str, Any]) -> None:
    esperado = {
        "fuente",
        "seccion_exacta",
        "riesgo",
        "entrada",
        "resultado_esperado",
        "fallo_observable",
        "modificable",
    }
    for caso in casos["nivel_1"]:
        assert set(caso["canonico"]) == esperado, caso["id"]
        assert caso["canonico"]["modificable"] is False


def test_cada_campo_de_instanciacion_declara_su_fuente_individual(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        inst = caso["instanciacion"]
        assert inst["estado"] == S2.ESTADO_NO_CONGELADO
        for campo in S2.CAMPOS_INSTANCIACION:
            assert campo in inst, (caso["id"], campo)
            assert inst[campo]["fuente"], (caso["id"], campo)
            assert inst[campo]["estado"] in S2.ESTADOS_CAMPO, (caso["id"], campo)


def test_ningun_campo_derivado_se_atribuye_a_b04_seccion_17(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        for campo in S2.CAMPOS_INSTANCIACION:
            meta = caso["instanciacion"][campo]
            if meta["estado"] == "DERIVADO_PROPUESTO":
                assert "§17" not in meta["fuente"], (caso["id"], campo)


def test_la_instanciacion_de_las_referencias_es_modificable(referencias: dict[str, Any]) -> None:
    for ref in referencias["referencias_nivel_1"]:
        assert ref["canonico"]["modificable"] is False
        assert ref["instanciacion"]["modificable"] is True
        assert ref["instanciacion"]["estado"] == S2.ESTADO_NO_CONGELADO


@pytest.mark.parametrize("ca", ["B04-CA-02", "B04-CA-22", "B04-CA-39", "B04-CA-47"])
def test_no_se_atribuye_exhaustiva_ni_s5_al_canon(casos: dict[str, Any], ca: str) -> None:
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == ca)
    assert caso["instanciacion"]["cardinalidad"]["estado"] != "CANONICO"
    assert caso["instanciacion"]["parada"]["estado"] != "CANONICO"


def test_ca_39_no_usa_vocabulario_de_parada_de_recuperacion(casos: dict[str, Any]) -> None:
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == "B04-CA-39")
    assert caso["instanciacion"]["cardinalidad"]["valor"] is None
    assert caso["instanciacion"]["parada"]["valor"] is None


def test_ninguna_instanciacion_exhaustiva_para_por_s1(casos: dict[str, Any]) -> None:
    """Única regla cardinalidad->parada que B04 §15.2 fija literalmente."""
    for caso in casos["nivel_1"]:
        inst = caso["instanciacion"]
        if inst["cardinalidad"]["valor"] == "EXHAUSTIVA":
            assert inst["parada"]["valor"] != "S1", caso["id"]


def test_solo_es_canonico_lo_que_el_propio_caso_nombra(
    canon: CS.Canon, casos: dict[str, Any]
) -> None:
    for caso in casos["nivel_1"]:
        original = canon.casos[caso["identificador_canonico"]]
        texto = " ".join([original.entrada, original.resultado_esperado, original.fallo_observable])
        for campo, patron in (
            ("etapa", B2._RX_ETAPA),
            ("parada", B2._RX_PARADA),
            ("modo", B2._RX_MODO),
        ):
            meta = caso["instanciacion"][campo]
            if meta["estado"] == "CANONICO":
                assert meta["valor"] in patron.findall(texto), (caso["id"], campo)
        if caso["instanciacion"]["cardinalidad"]["estado"] == "CANONICO":
            assert caso["instanciacion"]["cardinalidad"]["valor"] in texto, caso["id"]


# --- M-01 / M-02 · ramas ---------------------------------------------------


def _modos(caso: dict[str, Any]) -> set[str]:
    inst = caso["instanciacion"]
    return {inst["modo"]["valor"]} | {r["modo"] for r in inst["ramas"]}


@pytest.mark.parametrize("ca", B2.CA_CON_RAMA_M4_OBLIGATORIA)
def test_las_ramas_m4_exigidas_existen(casos: dict[str, Any], ca: str) -> None:
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == ca)
    assert "M4" in _modos(caso)


def test_los_cinco_modos_aparecen_al_menos_una_vez(casos: dict[str, Any]) -> None:
    todos: set[str] = set()
    for caso in casos["nivel_1"]:
        todos |= _modos(caso)
    assert set(S2.MODOS) <= todos


def test_todo_modo_nombrado_por_el_canon_esta_instanciado(
    canon: CS.Canon, casos: dict[str, Any]
) -> None:
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    for ca, original in canon.casos.items():
        texto = " ".join([original.entrada, original.resultado_esperado, original.fallo_observable])
        exigidos = set(B2._RX_MODO.findall(texto))
        if exigidos:
            assert exigidos <= _modos(por_ca[ca]), ca


@pytest.mark.parametrize("ca", B2.CA_MULTIRRAMA_OBLIGATORIA)
def test_los_casos_multirrama_tienen_ramas_distinguibles(casos: dict[str, Any], ca: str) -> None:
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == ca)
    ramas = caso["instanciacion"]["ramas"]
    assert len(ramas) >= 3, ca
    firmas = {
        (
            tuple(r["candidatos_elegibles"]),
            tuple(r["candidatos_prohibidos"]),
            r["estado_suficiencia_esperado"],
        )
        for r in ramas
    }
    assert len(firmas) == len(ramas), ca


def test_ca_47_devuelve_tres_conjuntos_distintos(casos: dict[str, Any]) -> None:
    """El fallo canónico «colapsa las tres fechas» tiene que ser detectable."""
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == "B04-CA-47")
    conjuntos = {tuple(sorted(r["candidatos_elegibles"])) for r in caso["instanciacion"]["ramas"]}
    assert len(conjuntos) == 3


def test_ca_36_diferencia_los_tres_estados_seguros(casos: dict[str, Any]) -> None:
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == "B04-CA-36")
    estados = {r["estado_suficiencia_esperado"] for r in caso["instanciacion"]["ramas"]}
    assert estados == {"SOLO_HISTORICO", "SOLO_CANDIDATA", "FUERA_DE_AMBITO"}


def test_ca_48_tiene_par_diferencial_y_control_de_ausencia_real(casos: dict[str, Any]) -> None:
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == "B04-CA-48")
    ramas = {r["sufijo"]: r for r in caso["instanciacion"]["ramas"]}
    assert set(ramas) == {"R1", "R2", "R3"}
    assert ramas["R1"]["candidatos_elegibles"] == ["MEM-010"]
    assert ramas["R2"]["candidatos_elegibles"] == []
    assert ramas["R3"]["candidatos_elegibles"] == []
    assert ramas["R2"]["tolerancia_pendiente"] == ramas["R3"]["tolerancia_pendiente"]
    assert ramas["R2"]["tolerancia_pendiente"]


def test_las_ramas_usan_vocabulario_canonico(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        for rama in caso["instanciacion"]["ramas"]:
            assert rama["modo"] in S2.MODOS
            assert rama["clase"] in S2.CLASES_RAMA
            assert rama["estado_suficiencia_esperado"] in S2.ESTADOS_SUFICIENCIA
            assert rama["fuente_canonica_de_la_rama"]


# --- M-03 · ficha del PDP §7 ----------------------------------------------


def test_el_esquema_cubre_los_catorce_campos_del_pdp7(canon: CS.Canon) -> None:
    assert set(S2.CAMPOS_PDP7) == set(canon.ficha_pdp7)


def test_cada_caso_lleva_la_ficha_completa_del_pdp7(casos: dict[str, Any]) -> None:
    esperados = set(S2.CAMPOS_PDP7.values()) | {S2.CAMPO_INSUFICIENCIA}
    for caso in casos["nivel_1"]:
        assert esperados <= set(caso["ficha_pdp_7"]), caso["id"]


@pytest.mark.parametrize("ca", ["B04-CA-37", "B04-CA-39", "B04-CA-48"])
def test_las_tolerancias_que_faltan_se_declaran_pendientes_sin_inventarlas(
    casos: dict[str, Any], ca: str
) -> None:
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == ca)
    tolerancias = caso["ficha_pdp_7"]["tolerancias"]
    assert tolerancias["estado"] == "PENDIENTE_TOL209"
    assert "NO CONGELADA" in tolerancias["valor"]


def test_la_condicion_de_insuficiencia_se_declara_por_transicion(casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1"]:
        etapa = caso["instanciacion"]["etapa"]["valor"]
        condiciones = caso["ficha_pdp_7"][S2.CAMPO_INSUFICIENCIA]["valor"]
        if etapa in ("E0", None):
            continue
        assert condiciones, caso["id"]
        assert len(condiciones) == S2.ETAPAS.index(etapa)


# --- B-03 · ninguna previsión es veredicto --------------------------------


def test_ningun_caso_conserva_el_veredicto_t0_del_v0_1(casos: dict[str, Any]) -> None:
    for grupo in ("nivel_1", "nivel_1_pdp"):
        for caso in casos[grupo]:
            assert "ejecutable_por_t0" not in caso
            assert caso["t0"]["estado_t0"] == "NO_MEDIDO"
            assert caso["t0"]["no_es_veredicto"] is True
            assert caso["t0"]["expresabilidad_prevista"] in S2.EXPRESABILIDAD
            assert caso["t0"]["fundamento_de_prevision"]


def test_ca_39_no_es_ejecutable_con_una_sola_implementacion(casos: dict[str, Any]) -> None:
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == "B04-CA-39")
    assert caso["t0"]["expresabilidad_prevista"] == "NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION"


@pytest.mark.parametrize("ca", ["B04-CA-01", "B04-CA-04", "B04-CA-09", "B04-CA-10", "B04-CA-11"])
def test_criterio_de_expresabilidad_unico(casos: dict[str, Any], ca: str) -> None:
    """Si una dimensión requerida no existe en T0, no se prevé que el caso pase."""
    caso = next(c for c in casos["nivel_1"] if c["identificador_canonico"] == ca)
    estados = set(caso["t0"]["estado_por_requisito"].values())
    if "AUSENTE" in estados:
        assert caso["t0"]["expresabilidad_prevista"] == "NO_EXPRESABLE_PREVISTO", ca
    else:
        assert caso["t0"]["expresabilidad_prevista"] != "EXPRESABLE_PREVISTO" or not (
            estados & {"AUSENTE", "PARCIAL"}
        ), ca


# --- M-04 · PDP-CA --------------------------------------------------------


def test_los_veintiocho_pdp_ca_quedan_clasificados(canon: CS.Canon, pdp: dict[str, Any]) -> None:
    aplicables = set(pdp["casos_ejecutados_por_ADR002"])
    excluidos = set(pdp["casos_fuera_de_alcance"])
    assert aplicables | excluidos == set(canon.casos_pdp)
    assert not (aplicables & excluidos)


def test_todo_pdp_ca_aplicable_esta_instanciado(casos: dict[str, Any], pdp: dict[str, Any]) -> None:
    instanciados = {c["identificador_canonico"] for c in casos["nivel_1_pdp"]}
    assert instanciados == set(pdp["casos_ejecutados_por_ADR002"])


def test_los_pdp_ca_instanciados_son_literales(canon: CS.Canon, casos: dict[str, Any]) -> None:
    for caso in casos["nivel_1_pdp"]:
        original = canon.casos_pdp[caso["identificador_canonico"]]
        assert caso["canonico"]["entrada_adversarial"] == original.entrada_adversarial
        assert caso["canonico"]["resultado_esperado"] == original.resultado_esperado


def test_todo_pdp_ca_excluido_declara_responsable(pdp: dict[str, Any]) -> None:
    for identificador, datos in pdp["casos_fuera_de_alcance"].items():
        assert datos["responsable"], identificador
        assert datos["motivo"], identificador


def test_no_se_afirma_cobertura_de_los_304_casos(pdp: dict[str, Any]) -> None:
    assert "NO cubre los 304 casos" in pdp["advertencia"]


# --- denominadores de familias -------------------------------------------


def test_las_familias_se_reportan_por_cuatro_denominadores(pdp: dict[str, Any]) -> None:
    fam = pdp["familias_pdp"]
    assert fam["1_destino_directo_adr002_arq00_20"]["familias"] == CS.familias_destino_adr002()
    assert fam["2_entradas_obligatorias_declaradas"]["familias"] == list(S2.FAMILIAS_ENTRADA_ADR002)
    assert fam["3_tocadas_por_casos_sin_atribuir_cierre"]["familias"]
    assert fam["4_fuera_de_alcance_de_adr002"]["responsables"]
    assert "20/25" not in json.dumps(fam, ensure_ascii=False)


def test_el_destino_directo_de_adr002_es_el_de_arq00_20() -> None:
    assert CS.familias_destino_adr002() == ["F01", "F02", "F03", "F10", "F15", "F22", "F23"]


# --- M-05 · los dos corpus ------------------------------------------------


def test_el_corpus_de_rendimiento_alcanza_la_escala_de_tol_208(
    rendimiento: dict[str, Any],
) -> None:
    assert rendimiento["conteos"]["mensajes"] == 5000
    assert rendimiento["conteos"]["recuerdos"] == 500
    assert rendimiento["conteos"]["decisiones"] == 50
    assert rendimiento["escala_declarada"]["escala_de_referencia"] == S2.ESCALA_RENDIMIENTO


def test_los_dos_corpus_comparten_contrato_y_semilla(
    conformidad: dict[str, Any], rendimiento: dict[str, Any]
) -> None:
    assert conformidad["version_contrato"] == rendimiento["version_contrato"]
    assert conformidad["semilla"] == rendimiento["semilla"] == S2.SEMILLA


def test_los_anclajes_viajan_al_corpus_de_rendimiento_sin_alterar(
    conformidad: dict[str, Any], rendimiento: dict[str, Any]
) -> None:
    por_id = {i["id"]: i for i in rendimiento["items"]}
    for item in conformidad["items"]:
        assert item["id"] in por_id, item["id"]
        assert por_id[item["id"]] == item, item["id"]


def test_el_relleno_de_volumen_no_contamina_ninguna_respuesta_canonica(
    rendimiento: dict[str, Any],
) -> None:
    for item in rendimiento["items"]:
        if not item["id"].startswith("VOL-"):
            continue
        assert item["project_id"] == S2.PROYECTO_VOLUMEN, item["id"]
        bajo = item["text"].lower()
        for termino in S2.TERMINOS_ANCLA:
            assert termino not in bajo, (item["id"], termino)
    for mensaje in rendimiento["mensajes"]:
        if not mensaje["id"].startswith("VOL-"):
            continue
        bajo = mensaje["texto"].lower()
        for termino in S2.TERMINOS_ANCLA:
            assert termino not in bajo, (mensaje["id"], termino)


def test_el_corpus_de_conformidad_no_se_usa_para_rendimiento(
    conformidad: dict[str, Any], rendimiento: dict[str, Any]
) -> None:
    assert "NO se usa para fijar cifras de rendimiento" in conformidad["proposito"]
    assert "NO crea referencias funcionales" in rendimiento["proposito"]


def test_los_anclajes_anadidos_estan_declarados_con_su_motivo(
    conformidad: dict[str, Any],
) -> None:
    anadidos = conformidad["anclajes_anadidos"]
    assert anadidos["items"] == ["DEC-014", "DEC-015"]
    assert "B04-CA-47" in anadidos["motivo"]


# --- disciplina del corpus ------------------------------------------------


def test_el_corpus_no_depende_del_reloj(
    conformidad: dict[str, Any], rendimiento: dict[str, Any]
) -> None:
    assert conformidad["ahora_declarado"] == S2.AHORA_DECLARADO
    assert rendimiento["ahora_declarado"] == S2.AHORA_DECLARADO
    assert conformidad["red"] == rendimiento["red"] == "no utilizada"


def test_ningun_artefacto_declara_puertas_satisfechas(artefactos: dict[str, Any]) -> None:
    manifiesto = artefactos["benchmark_manifest_v0_2.json"]
    assert "TOL-208, TOL-209 y TOL-210 siguen NO SATISFECHAS" in manifiesto["advertencia"]
    assert "ADR002-TOL-207 no está aprobada" in manifiesto["advertencia"]
    for datos in artefactos.values():
        assert datos.get("estado") in (None, S2.ESTADO_NO_CONGELADO), datos.get("documento")


def test_los_artefactos_v0_1_siguen_presentes() -> None:
    for nombre in ("corpus_v0_1.json", "cases_v0_1.json", "references_v0_1.json"):
        assert (AQUI / nombre).is_file(), nombre


def test_los_ficheros_v0_2_son_deterministas() -> None:
    antes = {n: (AQUI / n).read_bytes() for n in V2.FICHEROS}
    B2.main()
    for nombre, contenido in antes.items():
        assert (AQUI / nombre).read_bytes() == contenido, nombre


def test_el_validador_v0_2_pasa_sin_fallos() -> None:
    assert V2.main() == 0
