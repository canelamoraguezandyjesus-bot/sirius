"""Validador v0.2 · comprueba **fidelidad al canon**, no solo coherencia interna.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.validate_corpus_v0_2

La diferencia con el validador v0.1 —que se conserva intacto— es que este abre
los tres `.docx` de `docs/architecture/canonical_sources/`, verifica sus huellas
contra el `MANIFEST.md` y compara **carácter a carácter** lo que los artefactos
dicen del canon con lo que el canon dice. Comprobar identificadores contra una
lista blanca no basta: eso fue exactamente el hueco que la auditoría explotó.

Escribe `artifacts/adr002_benchmark_preparation/validacion_corpus_v0.2.json`.

No ejecuta T0 ni ningún candidato y no mide rendimiento.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import build_corpus_v0_2 as B2
from experiments.adr002.benchmark import canonical_source as CS
from experiments.adr002.benchmark import schema_v0_2 as S2
from experiments.adr002.benchmark import validate_corpus as V1

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
SALIDA = RAIZ / "artifacts" / "adr002_benchmark_preparation" / "validacion_corpus_v0.2.json"

FICHEROS = (
    "conformance_corpus_v0_2.json",
    "performance_corpus_v0_1.json",
    "cases_v0_2.json",
    "references_v0_2.json",
    "pdp_cases_v0_1.json",
    "benchmark_manifest_v0_2.json",
)


class Informe:
    def __init__(self) -> None:
        self.comprobaciones: list[dict[str, Any]] = []

    def check(self, nombre: str, ok: bool, detalle: Any = None) -> bool:
        self.comprobaciones.append(
            {"comprobacion": nombre, "resultado": "OK" if ok else "FALLO", "detalle": detalle}
        )
        return ok

    @property
    def fallos(self) -> list[dict[str, Any]]:
        return [c for c in self.comprobaciones if c["resultado"] == "FALLO"]


def cargar() -> dict[str, Any]:
    return {n: json.loads((AQUI / n).read_text(encoding="utf-8")) for n in FICHEROS}


# --- 1. Huellas de las fuentes canónicas ------------------------------------


def _huellas(canon: CS.Canon, inf: Informe) -> None:
    malas = {n: h for n, h in canon.huellas.items() if not h["coincide"]}
    inf.check("SHA-256 de las tres fuentes coincide con el MANIFEST", not malas, malas)
    inf.check(
        "el canon extraído tiene el tamaño que el canon declara",
        len(canon.casos) == 50
        and len(canon.anexo) == 79
        and len(canon.familias) == 25
        and len(canon.ficha_pdp7) == 14
        and len(canon.casos_pdp) == 28,
        {
            "casos_b04": len(canon.casos),
            "filas_anexo_b": len(canon.anexo),
            "familias": len(canon.familias),
            "campos_pdp7": len(canon.ficha_pdp7),
            "pdp_ca": len(canon.casos_pdp),
        },
    )


# --- 2. Los cincuenta CA, exactamente una vez -------------------------------


def _ca_completos(casos: dict[str, Any], inf: Informe) -> None:
    vistos = [c["identificador_canonico"] for c in casos["nivel_1"]]
    faltan = [c for c in S2.CA_TOTALES if c not in vistos]
    dup = sorted({c for c in vistos if vistos.count(c) > 1})
    ajenos = [c for c in vistos if c not in S2.CA_TOTALES]
    inf.check("CA-01-50 sin ausencias", not faltan, {"faltan": faltan})
    inf.check("CA-01-50 sin duplicados", not dup, {"duplicados": dup})
    inf.check("CA-01-50 sin identificadores ajenos", not ajenos, {"ajenos": ajenos})
    inf.check(
        "CA-01-50 aparecen exactamente una vez",
        len(vistos) == 50 and not dup and not faltan,
        {"total": len(vistos)},
    )


# --- 3. Literalidad carácter a carácter contra el DOCX ----------------------


def _literalidad(
    canon: CS.Canon, casos: dict[str, Any], refs: dict[str, Any], inf: Informe
) -> None:
    campos = ("riesgo", "entrada", "resultado_esperado", "fallo_observable")
    diferencias: list[dict[str, Any]] = []
    for caso in casos["nivel_1"]:
        canonico = canon.casos[caso["identificador_canonico"]]
        for campo in campos:
            esperado = getattr(canonico, campo)
            obtenido = caso["canonico"][campo]
            if esperado != obtenido:
                diferencias.append(
                    {
                        "caso": caso["id"],
                        "campo": campo,
                        "canon": esperado,
                        "artefacto": obtenido,
                    }
                )
        if caso["canonico"]["seccion_exacta"] != canonico.seccion:
            diferencias.append({"caso": caso["id"], "campo": "seccion_exacta"})
    inf.check(
        "los cuatro campos canónicos coinciden carácter a carácter con el DOCX (casos)",
        not diferencias,
        {"diferencias": diferencias[:10], "total": len(diferencias)},
    )

    dif_refs: list[dict[str, Any]] = []
    for ref in refs["referencias_nivel_1"]:
        canonico = canon.casos[ref["identificador_canonico"]]
        for campo in campos:
            if getattr(canonico, campo) != ref["canonico"][campo]:
                dif_refs.append({"referencia": ref["caso"], "campo": campo})
    inf.check(
        "los cuatro campos canónicos coinciden carácter a carácter con el DOCX (referencias)",
        not dif_refs,
        {"diferencias": dif_refs[:10], "total": len(dif_refs)},
    )


# --- 4. Anexo B · RED <-> CA <-> M <-> F ------------------------------------


def _anexo_b(casos: dict[str, Any], inf: Informe) -> None:
    asignaciones = CS.asignaciones_canonicas_por_ca()
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    perdidas: list[dict[str, Any]] = []
    for ca, esperado in asignaciones.items():
        caso = por_ca.get(ca)
        if caso is None:
            perdidas.append({"ca": ca, "problema": "caso ausente"})
            continue
        trazas = caso["trazabilidad"]
        faltan_red = [r for r in esperado["red"] if r not in trazas["traza_red_canonica_anexo_b"]]
        faltan_m = [m for m in esperado["metricas"] if m not in trazas["metrica_canonica_anexo_b"]]
        faltan_f = [f for f in esperado["familias"] if f not in trazas["familia_canonica_anexo_b"]]
        if faltan_red or faltan_m or faltan_f:
            perdidas.append(
                {"ca": ca, "red": faltan_red, "metricas": faltan_m, "familias": faltan_f}
            )
    inf.check(
        "toda asignación del Anexo B está presente en la traza canónica del caso",
        not perdidas,
        {"perdidas": perdidas},
    )

    mezclas = [
        c["id"]
        for c in casos["nivel_1"]
        if set(c["trazabilidad"]["traza_red_adicional_derivada"])
        & set(c["trazabilidad"]["traza_red_canonica_anexo_b"])
    ]
    inf.check(
        "lo adicional derivado no se solapa con lo canónico del Anexo B",
        not mezclas,
        {"casos": mezclas},
    )

    sin_traza = [c["id"] for c in casos["nivel_1"] if not c["trazabilidad"]["requisito_verificado"]]
    inf.check("cada caso traza a un RF canónico", not sin_traza, {"casos": sin_traza})

    rf_malos = sorted(
        {
            rf
            for c in casos["nivel_1"]
            for rf in c["trazabilidad"]["requisito_verificado"]
            if rf not in S2.RF_TOTALES
        }
    )
    inf.check("todo RF citado pertenece a B04-RF-01-32", not rf_malos, {"rf": rf_malos})

    red_adr002 = {
        r
        for c in casos["nivel_1"]
        for r in c["trazabilidad"]["traza_red_canonica_anexo_b"]
        + c["trazabilidad"]["traza_red_adicional_derivada"]
    }
    inf.check(
        "RED-027-034 cubiertas por al menos un caso",
        set(S2.RED_ADR002) <= red_adr002,
        {"faltan": sorted(set(S2.RED_ADR002) - red_adr002)},
    )
    inf.check(
        "RED-040 no se usa como requisito propio de ADR-002",
        all(
            "RED-040"
            not in c["trazabilidad"]["traza_red_canonica_anexo_b"]
            + c["trazabilidad"]["traza_red_adicional_derivada"]
            for c in casos["nivel_1"]
        ),
        None,
    )


# --- 5. Ramas canónicas ----------------------------------------------------


def _ramas(canon: CS.Canon, casos: dict[str, Any], inf: Informe) -> None:
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}

    def modos_del_caso(caso: dict[str, Any]) -> set[str]:
        inst = caso["instanciacion"]
        return {inst["modo"]["valor"]} | {r["modo"] for r in inst["ramas"]}

    # 5.1 · todo modo que el canon nombre literalmente debe existir en el caso.
    perdidos: list[dict[str, Any]] = []
    for ca, canonico in canon.casos.items():
        texto = " ".join([canonico.entrada, canonico.resultado_esperado, canonico.fallo_observable])
        exigidos = set(B2._RX_MODO.findall(texto))
        if not exigidos:
            continue
        presentes = modos_del_caso(por_ca[ca])
        if not exigidos <= presentes:
            perdidos.append(
                {"ca": ca, "exigidos": sorted(exigidos), "presentes": sorted(presentes)}
            )
    inf.check(
        "todo modo nombrado literalmente por el canon está instanciado en el caso o una rama",
        not perdidos,
        {"casos": perdidos},
    )

    # 5.2 · las ramas M4 que el paquete 03B §4.3 exige nominalmente.
    sin_m4 = [ca for ca in B2.CA_CON_RAMA_M4_OBLIGATORIA if "M4" not in modos_del_caso(por_ca[ca])]
    inf.check("CA-09, CA-10, CA-24 y CA-49 tienen rama M4", not sin_m4, {"casos": sin_m4})

    # 5.3 · M1-M5 aparecen al menos una vez en el conjunto.
    todos = {m for c in casos["nivel_1"] for m in modos_del_caso(c)}
    inf.check(
        "los cinco modos M1-M5 aparecen al menos una vez",
        set(S2.MODOS) <= todos,
        {"faltan": sorted(set(S2.MODOS) - todos)},
    )

    # 5.4 · casos multirrama: al menos tres ramas y resultados diferenciados.
    problemas: list[dict[str, Any]] = []
    for ca in B2.CA_MULTIRRAMA_OBLIGATORIA:
        ramas = por_ca[ca]["instanciacion"]["ramas"]
        if len(ramas) < 3:
            problemas.append({"ca": ca, "ramas": len(ramas)})
            continue
        firmas = {
            (
                tuple(r["candidatos_elegibles"]),
                tuple(r["candidatos_prohibidos"]),
                r["estado_suficiencia_esperado"],
            )
            for r in ramas
        }
        if len(firmas) != len(ramas):
            problemas.append({"ca": ca, "problema": "ramas indistinguibles", "firmas": len(firmas)})
    inf.check(
        "CA-36, CA-47 y CA-48 tienen tres ramas con resultado esperado distinto",
        not problemas,
        {"casos": problemas},
    )

    # 5.5 · CA-47: los tres ejes temporales dan tres conjuntos distintos.
    ramas47 = por_ca["B04-CA-47"]["instanciacion"]["ramas"]
    conjuntos = {tuple(sorted(r["candidatos_elegibles"])) for r in ramas47}
    inf.check(
        "CA-47: occurred_at, valid_time y recorded_at devuelven tres conjuntos distintos",
        len(conjuntos) == 3,
        {"conjuntos": sorted(conjuntos)},
    )

    # 5.6 · CA-48: la rama no autorizada y la de ausencia real son indistinguibles.
    ramas48 = {r["sufijo"]: r for r in por_ca["B04-CA-48"]["instanciacion"]["ramas"]}
    no_autorizada = ramas48.get("R2", {})
    ausencia = ramas48.get("R3", {})
    inf.check(
        "CA-48: la rama no autorizada y la de ausencia real declaran salida externa equivalente",
        bool(no_autorizada)
        and bool(ausencia)
        and no_autorizada["candidatos_elegibles"] == ausencia["candidatos_elegibles"] == []
        and no_autorizada["estado_suficiencia_esperado"] != ausencia["estado_suficiencia_esperado"]
        and no_autorizada["tolerancia_pendiente"] == ausencia["tolerancia_pendiente"],
        {
            "no_autorizada": no_autorizada.get("estado_suficiencia_esperado"),
            "ausencia_real": ausencia.get("estado_suficiencia_esperado"),
        },
    )

    # 5.7 · vocabularios de rama.
    malas = [
        r["sufijo"]
        for c in casos["nivel_1"]
        for r in c["instanciacion"]["ramas"]
        if r["modo"] not in S2.MODOS
        or r["clase"] not in S2.CLASES_RAMA
        or r["estado_suficiencia_esperado"] not in S2.ESTADOS_SUFICIENCIA
    ]
    inf.check("las ramas usan vocabulario canónico", not malas, {"ramas": malas})


# --- 6. Ficha obligatoria del PDP §7 ---------------------------------------


def _ficha_pdp7(canon: CS.Canon, casos: dict[str, Any], inf: Informe) -> None:
    esperados = set(S2.CAMPOS_PDP7.values()) | {S2.CAMPO_INSUFICIENCIA}
    inf.check(
        "el mapa de campos cubre los catorce del PDP §7 leídos del DOCX",
        set(S2.CAMPOS_PDP7) == set(canon.ficha_pdp7),
        {
            "solo_en_esquema": sorted(set(S2.CAMPOS_PDP7) - set(canon.ficha_pdp7)),
            "solo_en_canon": sorted(set(canon.ficha_pdp7) - set(S2.CAMPOS_PDP7)),
        },
    )
    faltan: dict[str, list[str]] = {}
    estados_malos: list[str] = []
    for caso in casos["nivel_1"]:
        ficha = caso.get("ficha_pdp_7", {})
        ausentes = sorted(esperados - set(ficha))
        if ausentes:
            faltan[caso["id"]] = ausentes
        for clave, campo in ficha.items():
            if campo.get("estado") not in S2.ESTADOS_CAMPO:
                estados_malos.append(f"{caso['id']}.{clave}")
    inf.check(
        "cada caso lleva los catorce campos del PDP §7 y la insuficiencia", not faltan, faltan
    )
    inf.check("todo campo de la ficha declara un estado válido", not estados_malos, estados_malos)

    # Las tolerancias que dependen de TOL-209 se declaran, no se inventan.
    sin_declarar = [
        caso["id"]
        for caso in casos["nivel_1"]
        if caso["identificador_canonico"] in B2.CA_TOLERANCIA_PENDIENTE
        and caso["ficha_pdp_7"]["tolerancias"]["estado"] != "PENDIENTE_TOL209"
    ]
    inf.check(
        "CA-37, CA-39 y CA-48 declaran su tolerancia como PENDIENTE_TOL209, sin inventar banda",
        not sin_declarar,
        {"casos": sin_declarar},
    )

    sin_insuficiencia = [
        caso["id"]
        for caso in casos["nivel_1"]
        if caso["instanciacion"]["etapa"]["valor"] not in (None, "E0")
        and not caso["ficha_pdp_7"][S2.CAMPO_INSUFICIENCIA]["valor"]
    ]
    inf.check(
        "todo caso que resuelve más allá de E0 declara la condición de insuficiencia por "
        "transición",
        not sin_insuficiencia,
        {"casos": sin_insuficiencia},
    )


# --- 7. Separación canon / instanciación -----------------------------------


def _separacion(casos: dict[str, Any], refs: dict[str, Any], inf: Informe) -> None:
    problemas: list[str] = []
    for caso in casos["nivel_1"]:
        canonico = caso["canonico"]
        if canonico["modificable"] is not False:
            problemas.append(f"{caso['id']}: bloque canónico modificable")
        if set(canonico) != {
            "fuente",
            "seccion_exacta",
            "riesgo",
            "entrada",
            "resultado_esperado",
            "fallo_observable",
            "modificable",
        }:
            problemas.append(f"{caso['id']}: el bloque canónico contiene campos no canónicos")
        inst = caso["instanciacion"]
        if inst["estado"] != S2.ESTADO_NO_CONGELADO:
            problemas.append(f"{caso['id']}: instanciación declarada congelada")
        for campo in S2.CAMPOS_INSTANCIACION:
            if campo not in inst:
                problemas.append(f"{caso['id']}: falta el campo de instanciación {campo}")
                continue
            fuente = inst[campo]["fuente"]
            estado = inst[campo]["estado"]
            if estado not in S2.ESTADOS_CAMPO:
                problemas.append(f"{caso['id']}.{campo}: estado inválido")
            if estado == "DERIVADO_PROPUESTO" and "§17" in fuente:
                problemas.append(f"{caso['id']}.{campo}: derivado atribuido a B04 §17")
    inf.check("canon e instanciación están separados y etiquetados", not problemas, problemas[:20])

    # Ningún campo de instanciación puede declararse congelado por §17/§17.1.
    indebidos: list[str] = []
    for ref in refs["referencias_nivel_1"]:
        if ref["canonico"]["fuente"] != S2.FUENTE_CANONICA_CA:
            indebidos.append(f"{ref['caso']}: fuente canónica inesperada")
        if ref["instanciacion"]["modificable"] is not True:
            indebidos.append(f"{ref['caso']}: instanciación marcada no modificable")
        for campo, meta in ref["instanciacion"]["fuente_por_campo"].items():
            if meta["estado"] == "CANONICO" and "§17" in meta["fuente"]:
                continue
            if "§17/§17.1" in meta["fuente"]:
                indebidos.append(f"{ref['caso']}.{campo}: congelado por §17 sin ser canónico")
    inf.check(
        "ninguna referencia declara instanciación congelada por B04 §17/§17.1",
        not indebidos,
        indebidos[:20],
    )


# --- 8. Cardinalidad, parada y la única regla canónica ---------------------


def _cardinalidad_y_parada(canon: CS.Canon, casos: dict[str, Any], inf: Informe) -> None:
    inf.check(
        "la regla canónica «EXHAUSTIVA -> S1 deshabilitado» se lee del DOCX",
        CS.s1_prohibida_en_exhaustiva(),
        {"regla": canon.__class__ and CS.reglas_cardinalidad_b04().get("EXHAUSTIVA")},
    )
    malos = [
        c["id"]
        for c in casos["nivel_1"]
        if c["instanciacion"]["cardinalidad"]["valor"] == "EXHAUSTIVA"
        and c["instanciacion"]["parada"]["valor"] == "S1"
    ]
    inf.check("ninguna instanciación EXHAUSTIVA para por S1", not malos, {"casos": malos})

    # Solo es CANONICO lo que el texto canónico del propio caso nombra.
    indebidos: list[dict[str, Any]] = []
    for caso in casos["nivel_1"]:
        canonico = canon.casos[caso["identificador_canonico"]]
        texto = " ".join([canonico.entrada, canonico.resultado_esperado, canonico.fallo_observable])
        for campo, patron in (
            ("cardinalidad", None),
            ("etapa", B2._RX_ETAPA),
            ("parada", B2._RX_PARADA),
            ("modo", B2._RX_MODO),
        ):
            meta = caso["instanciacion"][campo]
            if meta["estado"] != "CANONICO":
                continue
            valor = meta["valor"]
            presente = (valor in texto) if patron is None else (valor in patron.findall(texto))
            if not presente:
                indebidos.append({"caso": caso["id"], "campo": campo, "valor": valor})
    inf.check(
        "solo se marca CANONICO el valor que el texto canónico del propio caso nombra",
        not indebidos,
        {"campos": indebidos},
    )

    # CA-02, CA-22, CA-39 y CA-47: retirada la atribución canónica.
    vigilados = ("B04-CA-02", "B04-CA-22", "B04-CA-39", "B04-CA-47")
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    atribuidos = [
        ca
        for ca in vigilados
        if por_ca[ca]["instanciacion"]["cardinalidad"]["estado"] == "CANONICO"
        or por_ca[ca]["instanciacion"]["parada"]["estado"] == "CANONICO"
    ]
    inf.check(
        "CA-02, CA-22, CA-39 y CA-47 no atribuyen EXHAUSTIVA ni S5 al canon",
        not atribuidos,
        {"casos": atribuidos},
    )

    ca39 = por_ca["B04-CA-39"]["instanciacion"]
    inf.check(
        "CA-39 no usa vocabulario de cardinalidad ni de parada de recuperación",
        ca39["cardinalidad"]["valor"] is None and ca39["parada"]["valor"] is None,
        {
            "cardinalidad": ca39["cardinalidad"]["valor"],
            "parada": ca39["parada"]["valor"],
        },
    )

    vocab_malo = [
        c["id"]
        for c in casos["nivel_1"]
        if (
            c["instanciacion"]["modo"]["valor"] not in S2.MODOS
            or c["instanciacion"]["etapa"]["valor"] not in S2.ETAPAS
            or (
                c["instanciacion"]["parada"]["valor"] is not None
                and c["instanciacion"]["parada"]["valor"] not in S2.PARADAS
            )
            or (
                c["instanciacion"]["cardinalidad"]["valor"] is not None
                and c["instanciacion"]["cardinalidad"]["valor"] not in S2.CARDINALIDADES
            )
        )
    ]
    inf.check(
        "vocabulario canónico de modo, etapa, parada y cardinalidad", not vocab_malo, vocab_malo
    )


# --- 9. Ningún veredicto frente a T0 ---------------------------------------


def _sin_veredicto_t0(casos: dict[str, Any], inf: Informe) -> None:
    problemas: list[str] = []
    for grupo in ("nivel_1", "nivel_1_pdp"):
        for caso in casos[grupo]:
            if "ejecutable_por_t0" in caso:
                problemas.append(f"{caso['id']}: conserva el campo de veredicto del v0.1")
            t0 = caso.get("t0", {})
            if t0.get("estado_t0") != S2.ESTADO_T0:
                problemas.append(f"{caso['id']}: estado_t0 != NO_MEDIDO")
            if t0.get("no_es_veredicto") is not True:
                problemas.append(f"{caso['id']}: no declara no_es_veredicto")
            if t0.get("expresabilidad_prevista") not in S2.EXPRESABILIDAD:
                problemas.append(f"{caso['id']}: previsión fuera de vocabulario")
            if not t0.get("fundamento_de_prevision"):
                problemas.append(f"{caso['id']}: previsión sin fundamento")
    inf.check("ningún caso emite veredicto frente a T0", not problemas, problemas[:20])

    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    inf.check(
        "CA-39 se declara no ejecutable con una sola implementación",
        por_ca["B04-CA-39"]["t0"]["expresabilidad_prevista"]
        == "NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION",
        {"prevision": por_ca["B04-CA-39"]["t0"]["expresabilidad_prevista"]},
    )

    # Criterio único: si una dimensión requerida es AUSENTE, no se prevé que pase.
    unificados = ("B04-CA-01", "B04-CA-04", "B04-CA-09", "B04-CA-10", "B04-CA-11")
    incoherentes = [
        ca
        for ca in unificados
        if por_ca[ca]["t0"]["expresabilidad_prevista"] == "EXPRESABLE_PREVISTO"
        and "AUSENTE" in por_ca[ca]["t0"]["estado_por_requisito"].values()
    ]
    inf.check(
        "criterio de expresabilidad único en CA-01, CA-04, CA-09, CA-10 y CA-11",
        not incoherentes,
        {"casos": incoherentes},
    )


# --- 10. PDP-CA y denominadores de familias -------------------------------


def _pdp(canon: CS.Canon, casos: dict[str, Any], pdp: dict[str, Any], inf: Informe) -> None:
    aplicables = set(pdp["casos_ejecutados_por_ADR002"])
    excluidos = set(pdp["casos_fuera_de_alcance"])
    inf.check(
        "los veintiocho PDP-CA quedan clasificados sin solapamiento ni hueco",
        aplicables | excluidos == set(canon.casos_pdp) and not (aplicables & excluidos),
        {
            "aplicables": len(aplicables),
            "excluidos": len(excluidos),
            "totales": len(canon.casos_pdp),
        },
    )
    instanciados = {c["identificador_canonico"] for c in casos["nivel_1_pdp"]}
    inf.check(
        "todo PDP-CA aplicable está instanciado como nivel 1",
        instanciados == aplicables,
        {"solo_aplicables": sorted(aplicables - instanciados)},
    )
    sin_criterio = [p for p, d in pdp["casos_ejecutados_por_ADR002"].items() if not d["criterios"]]
    inf.check("todo PDP-CA aplicable declara su criterio", not sin_criterio, sin_criterio)
    sin_responsable = [p for p, d in pdp["casos_fuera_de_alcance"].items() if not d["responsable"]]
    inf.check("todo PDP-CA excluido declara su responsable", not sin_responsable, sin_responsable)
    literales = [
        c["identificador_canonico"]
        for c in casos["nivel_1_pdp"]
        if c["canonico"]["resultado_esperado"]
        != canon.casos_pdp[c["identificador_canonico"]].resultado_esperado
        or c["canonico"]["entrada_adversarial"]
        != canon.casos_pdp[c["identificador_canonico"]].entrada_adversarial
    ]
    inf.check(
        "los PDP-CA instanciados reproducen su texto canónico carácter a carácter",
        not literales,
        {"casos": literales},
    )

    fam = pdp["familias_pdp"]
    inf.check(
        "familias PDP reportadas por los cuatro denominadores, sin agregarlos",
        fam["1_destino_directo_adr002_arq00_20"]["familias"] == CS.familias_destino_adr002()
        and fam["2_entradas_obligatorias_declaradas"]["familias"]
        == list(S2.FAMILIAS_ENTRADA_ADR002)
        and "familias" in fam["3_tocadas_por_casos_sin_atribuir_cierre"]
        and "familias" in fam["4_fuera_de_alcance_de_adr002"],
        {
            "destino_directo": fam["1_destino_directo_adr002_arq00_20"]["familias"],
            "entradas": fam["2_entradas_obligatorias_declaradas"]["familias"],
        },
    )
    inf.check(
        "no se declara ninguna cifra agregada de «cobertura de familias de ADR-002»",
        "20/25" not in json.dumps(fam, ensure_ascii=False)
        and "cuatro denominadores distintos" in fam["advertencia"],
        {"advertencia": fam["advertencia"]},
    )


# --- 11. Dimensiones y fenómenos del corpus de conformidad -----------------


def _fenomenos(conformidad: dict[str, Any], inf: Informe) -> None:
    interno = V1.Informe()
    V1._fenomenos(conformidad, interno)
    faltan = interno.comprobaciones[0]["detalle"]["faltan"]
    inf.check(
        "fenómenos obligatorios representados en el corpus de conformidad", not faltan, faltan
    )

    interno2 = V1.Informe()
    V1._dimensiones(conformidad, interno2)
    fallos = [c for c in interno2.comprobaciones if c["resultado"] == "FALLO"]
    inf.check("las siete dimensiones ortogonales usan vocabulario canónico", not fallos, fallos)

    interno3 = V1.Informe()
    V1._criticidad(conformidad, interno3)
    fallos3 = [c for c in interno3.comprobaciones if c["resultado"] == "FALLO"]
    inf.check("toda marca crítica lleva nivel, razón, fuente y regla", not fallos3, fallos3)

    ids = [i["id"] for i in conformidad["items"]]
    inf.check("ids del corpus de conformidad sin duplicados", len(ids) == len(set(ids)), None)

    crudo = json.dumps(conformidad, ensure_ascii=False).lower()
    prohibidos = ["@gmail", "@hotmail", "http://", "https://", "password", "api_key", "secret"]
    hallados = [p for p in prohibidos if p in crudo]
    inf.check("sin datos reales, URLs ni secretos", not hallados, {"encontrados": hallados})


# --- 12. Consistencia entre los dos corpus --------------------------------


def _dos_corpus(
    conformidad: dict[str, Any],
    rendimiento: dict[str, Any],
    manifiesto: dict[str, Any],
    inf: Informe,
) -> None:
    inf.check(
        "los dos corpus comparten versión de contrato y semilla",
        conformidad["version_contrato"] == rendimiento["version_contrato"] == S2.VERSION_CONTRATO
        and conformidad["semilla"] == rendimiento["semilla"] == S2.SEMILLA,
        {
            "contrato": [conformidad["version_contrato"], rendimiento["version_contrato"]],
            "semilla": [conformidad["semilla"], rendimiento["semilla"]],
        },
    )
    objetivo = rendimiento["escala_declarada"]["objetivo"]
    inf.check(
        "el corpus de rendimiento alcanza exactamente 5.000 mensajes, 500 recuerdos y 50 "
        "decisiones",
        rendimiento["conteos"]["mensajes"] == objetivo["mensajes"] == 5000
        and rendimiento["conteos"]["recuerdos"] == objetivo["recuerdos"] == 500
        and rendimiento["conteos"]["decisiones"] == objetivo["decisiones"] == 50,
        rendimiento["conteos"],
    )
    inf.check(
        "la escala de referencia declarada es la de ADR002-TOL-208",
        rendimiento["escala_declarada"]["escala_de_referencia"] == S2.ESCALA_RENDIMIENTO,
        rendimiento["escala_declarada"]["escala_de_referencia"],
    )
    inf.check(
        "las escalas proyectables declaradas son 500 / 5.000 / 50.000",
        rendimiento["escala_declarada"]["escalas_proyectables"] == list(S2.ESCALAS_PROYECCION),
        rendimiento["escala_declarada"]["escalas_proyectables"],
    )

    # Los anclajes del corpus de conformidad viajan sin alterar.
    por_id = {i["id"]: i for i in rendimiento["items"]}
    alterados = [
        i["id"] for i in conformidad["items"] if i["id"] not in por_id or por_id[i["id"]] != i
    ]
    inf.check(
        "todo anclaje del corpus de conformidad está en el de rendimiento sin alterar",
        not alterados,
        {"alterados": alterados[:10], "total": len(alterados)},
    )

    # El relleno vive en su proyecto y no comparte vocabulario con los anclajes.
    relleno = [i for i in rendimiento["items"] if i["id"].startswith("VOL-")]
    fuera = [i["id"] for i in relleno if i["project_id"] != S2.PROYECTO_VOLUMEN]
    inf.check(
        "el relleno de volumen vive en el proyecto reservado", not fuera, {"items": fuera[:10]}
    )
    contaminados = [
        i["id"] for i in relleno if any(t in i["text"].lower() for t in S2.TERMINOS_ANCLA)
    ]
    mensajes_relleno = [m for m in rendimiento["mensajes"] if m["id"].startswith("VOL-")]
    contaminados += [
        m["id"] for m in mensajes_relleno if any(t in m["texto"].lower() for t in S2.TERMINOS_ANCLA)
    ]
    inf.check(
        "ningún texto de volumen contiene un término de anclaje canónico",
        not contaminados,
        {"items": contaminados[:10], "total": len(contaminados)},
    )
    inf.check(
        "el corpus de rendimiento declara que no crea referencias funcionales",
        "NO crea referencias funcionales" in rendimiento["proposito"],
        None,
    )
    inf.check(
        "el manifiesto declara la relación entre los dos corpus y su prohibición cruzada",
        "prohibicion" in manifiesto["relacion_entre_corpus"]
        and manifiesto["artefactos"]["corpus_conformidad"]["fichero"]
        == "conformance_corpus_v0_2.json"
        and manifiesto["artefactos"]["corpus_rendimiento"]["fichero"]
        == "performance_corpus_v0_1.json",
        None,
    )
    inf.check(
        "el manifiesto no declara satisfecha ninguna puerta de arranque",
        "TOL-208, TOL-209 y TOL-210 siguen NO SATISFECHAS" in manifiesto["advertencia"]
        and "no está aprobada" in manifiesto["advertencia"],
        manifiesto["advertencia"],
    )


# --- 13. Determinismo y conservación del v0.1 -----------------------------


def _determinismo(inf: Informe) -> None:
    antes = {n: (AQUI / n).read_bytes() for n in FICHEROS}
    B2.main()
    primera = {n: (AQUI / n).read_bytes() for n in FICHEROS}
    B2.main()
    segunda = {n: (AQUI / n).read_bytes() for n in FICHEROS}
    inf.check(
        "regeneración doble byte a byte idéntica",
        antes == primera == segunda,
        {
            "difieren_primera": [n for n in FICHEROS if antes[n] != primera[n]],
            "difieren_segunda": [n for n in FICHEROS if primera[n] != segunda[n]],
        },
    )


def _v0_1_intacto(inf: Informe) -> None:
    v1 = ("corpus_v0_1.json", "cases_v0_1.json", "references_v0_1.json")
    presentes = [n for n in v1 if (AQUI / n).is_file()]
    inf.check("los tres artefactos v0.1 siguen presentes", presentes == list(v1), presentes)
    interno = V1.Informe()
    _corpus, casos, refs = V1.cargar()
    V1._ca_completos(casos, interno)
    V1._referencias(casos, refs, interno)
    fallos = [c for c in interno.comprobaciones if c["resultado"] == "FALLO"]
    inf.check("el contrato del v0.1 sigue cumpliéndose sin cambios", not fallos, fallos)


# --- main ------------------------------------------------------------------


def main() -> int:
    canon = CS.cargar_canon()
    art = cargar()
    conformidad = art["conformance_corpus_v0_2.json"]
    rendimiento = art["performance_corpus_v0_1.json"]
    casos = art["cases_v0_2.json"]
    refs = art["references_v0_2.json"]
    pdp = art["pdp_cases_v0_1.json"]
    manifiesto = art["benchmark_manifest_v0_2.json"]

    inf = Informe()
    _huellas(canon, inf)
    _ca_completos(casos, inf)
    _literalidad(canon, casos, refs, inf)
    _anexo_b(casos, inf)
    _ramas(canon, casos, inf)
    _ficha_pdp7(canon, casos, inf)
    _separacion(casos, refs, inf)
    _cardinalidad_y_parada(canon, casos, inf)
    _sin_veredicto_t0(casos, inf)
    _pdp(canon, casos, pdp, inf)
    _fenomenos(conformidad, inf)
    _dos_corpus(conformidad, rendimiento, manifiesto, inf)
    _v0_1_intacto(inf)
    _determinismo(inf)

    informe = {
        "documento": "Validación v0.2 del benchmark de ADR-002 contra las fuentes canónicas",
        "version_contrato": S2.VERSION_CONTRATO,
        "estado": S2.ESTADO_NO_CONGELADO,
        "no_ejecuta": ["T0", "ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D"],
        "puertas": {
            "SRC-ADR002-01": "SATISFECHA",
            "ADR002-TOL-207": "NO SATISFECHA · no se aprueba en esta ronda",
            "ADR002-TOL-208": "NO SATISFECHA · el corpus no está congelado y T0 no se ha ejecutado",
            "ADR002-TOL-209": "NO SATISFECHA",
            "ADR002-TOL-210": "NO SATISFECHA",
        },
        "fuentes_canonicas": canon.huellas,
        "resumen": {
            "comprobaciones": len(inf.comprobaciones),
            "ok": len(inf.comprobaciones) - len(inf.fallos),
            "fallos": len(inf.fallos),
            "veredicto": "VALIDO" if not inf.fallos else "INVALIDO",
        },
        "cobertura": {
            "ca_b04": {"cubiertos": len(casos["nivel_1"]), "de": 50},
            "pdp_ca": pdp["conteos"],
            "ramas_canonicas": casos["conteos"]["ramas_canonicas"],
            "familias_pdp": {
                clave: valor.get("familias")
                for clave, valor in pdp["familias_pdp"].items()
                if isinstance(valor, dict)
            },
        },
        "corpus": {
            "conformidad": conformidad["conteos"],
            "rendimiento": rendimiento["conteos"],
            "escala_rendimiento": rendimiento["escala_declarada"],
        },
        "prevision_t0": {
            "estado": S2.ESTADO_T0,
            "reparto": _reparto_t0(casos),
            "nota": "Previsión, no veredicto. T0 no se ha ejecutado.",
        },
        "comprobaciones": inf.comprobaciones,
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(informe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"comprobaciones: {len(inf.comprobaciones)}  fallos: {len(inf.fallos)}")
    for c in inf.fallos:
        print(f"  FALLO: {c['comprobacion']} -> {c['detalle']}")
    print(f"informe: {SALIDA.relative_to(RAIZ)}")
    return 1 if inf.fallos else 0


def _reparto_t0(casos: dict[str, Any]) -> dict[str, list[str]]:
    salida: dict[str, list[str]] = {}
    for caso in casos["nivel_1"]:
        salida.setdefault(caso["t0"]["expresabilidad_prevista"], []).append(
            caso["identificador_canonico"]
        )
    return {k: sorted(v) for k, v in sorted(salida.items())}


if __name__ == "__main__":
    raise SystemExit(main())
