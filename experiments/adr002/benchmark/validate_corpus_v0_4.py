"""Validador v0.4 · adjudicación recalculada por un oráculo independiente.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.validate_corpus_v0_4

Regla de independencia (matriz de aceptación, criterio 6): este módulo **no
importa ni reutiliza** ``evaluar_universo`` ni ninguna función de cierre del
generador. Todo cierre, censo, huella, colisión y guarda se recalcula aquí
con un oráculo propio —iteración plana, ``datetime`` real, tokenizador
propio— que lee las reglas **declarativamente** desde los artefactos JSON.
``build_corpus_v0_4`` solo se importa dentro de la comprobación de
determinismo, para regenerar en un directorio temporal.

El único fichero que escribe es su propio informe, y solo desde ``main()``.

No ejecuta T0, no implementa ni ejecuta ADR002-A/B/C/D y no mide rendimiento.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import canonical_source_v0_4 as CS4
from experiments.adr002.benchmark import schema_v0_4 as S4
from experiments.adr002.benchmark import validate_corpus as V1

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
SALIDA = RAIZ / "artifacts" / "adr002_benchmark_preparation" / "validacion_corpus_v0.4.json"

FICHEROS = (
    "conformance_corpus_v0_4.json",
    "cases_v0_4.json",
    "references_v0_4.json",
    "pdp_cases_v0_3.json",
    "pdp_harness_rules_v0_2.json",
    "t0_preexecution_projection_v0_2.json",
    "benchmark_manifest_v0_4.json",
)

ARTEFACTOS_ANTERIORES = (
    "corpus_v0_1.json",
    "cases_v0_1.json",
    "references_v0_1.json",
    "conformance_corpus_v0_2.json",
    "performance_corpus_v0_1.json",
    "cases_v0_2.json",
    "references_v0_2.json",
    "pdp_cases_v0_1.json",
    "benchmark_manifest_v0_2.json",
    "conformance_corpus_v0_3.json",
    "performance_corpus_v0_2.json",
    "cases_v0_3.json",
    "references_v0_3.json",
    "pdp_cases_v0_2.json",
    "pdp_harness_rules_v0_1.json",
    "t0_preexecution_projection_v0_1.json",
    "benchmark_manifest_v0_3.json",
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


def cargar(directorio: Path | None = None) -> dict[str, Any]:
    base = directorio or AQUI
    return {n: json.loads((base / n).read_text(encoding="utf-8")) for n in FICHEROS}


# ===========================================================================
# ORÁCULO · reimplementación independiente del cierre de dominios
# ===========================================================================


def _o_norm(texto: str | None) -> list[str]:
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    plano = "".join(ch for ch in descompuesto if not unicodedata.combining(ch)).lower()
    return [t for t in re.split(r"[^0-9a-z]+", plano) if t]


def _o_fecha(valor: str | None) -> datetime | None:
    return None if valor is None else datetime.fromisoformat(valor.replace("Z", "+00:00"))


def _o_ancla(texto: str | None, ancla: dict[str, Any] | None) -> bool:
    if not ancla:
        return True
    tokens = _o_norm(texto)
    for termino in ancla.get("todas") or []:
        if not any(t.startswith(termino) for t in tokens):
            return False
    alguna = ancla.get("alguna") or []
    return not alguna or any(t.startswith(term) for term in alguna for t in tokens)


def _o_en_ambito(project_id: str, dominio: dict[str, Any], proyectos: dict[str, Any]) -> bool:
    regla = dominio.get("regla_multiproyecto", "SOLO_PROYECTO")
    objetivo = dominio["ambito"]
    if regla == "GLOBAL_TODOS" or project_id == objetivo:
        return True
    if regla == "CON_GLOBAL" and project_id == "PRJ-GLOBAL":
        return True
    if regla == "CON_LISTAS_CERRADAS":
        candidato = proyectos.get(project_id, {})
        return candidato.get("tipo") == "MULTI_PROYECTO_CERRADO" and objetivo in candidato.get(
            "miembros_lista_cerrada", []
        )
    return False


def _o_tiempo(temporalidad: dict[str, Any], tiempo: dict[str, Any] | None) -> str | None:
    """None si pasa; si no, la dimensión temporal que lo excluye."""
    if not tiempo or tiempo.get("operador") in (None, "SIN_FILTRO"):
        return None
    operador = tiempo["operador"]
    vf, vt = _o_fecha(temporalidad.get("valid_from")), _o_fecha(temporalidad.get("valid_to"))
    if operador == "VIGENTE_EN_INSTANTE":
        instante = _o_fecha(tiempo["instante"])
        if (vf is not None and vf > instante) or (vt is not None and instante >= vt):
            return "tiempo_valido"
        return None
    if operador == "SOLAPA_INTERVALO":
        desde, hasta = _o_fecha(tiempo["desde"]), _o_fecha(tiempo["hasta"])
        if (vf is not None and vf > hasta) or (vt is not None and vt < desde):
            return "tiempo_valido"
        return None
    if operador == "OCCURRED_EN_INTERVALO":
        occurred = _o_fecha(temporalidad.get("occurred_at"))
        if occurred is None or not (
            _o_fecha(tiempo["desde"]) <= occurred < _o_fecha(tiempo["hasta"])
        ):
            return "occurred_at"
        return None
    if operador == "REGISTRADO_HASTA":
        registrado = _o_fecha(temporalidad.get("recorded_at"))
        if registrado is None or registrado > _o_fecha(tiempo["hasta"]):
            return "recorded_at"
        return None
    raise AssertionError(f"oráculo: operador temporal desconocido {operador}")


def oraculo_universo(corpus: dict[str, Any], dominio: dict[str, Any]) -> dict[str, Any]:
    """Cierre recalculado con lógica propia a partir del dominio declarado."""
    proyectos = {p["id"]: p for p in corpus["proyectos"]}
    entidades = {e["id"]: e for e in corpus["entidades"]}
    estados: dict[str, tuple[str, ...] | list[str]] = dict(S4.ESTADOS_ELEGIBLES_DEFECTO)
    estados.update(dominio.get("estados") or {})
    ancla = dominio.get("ancla")
    entidad = dominio.get("entidad")
    colecciones = dominio.get("colecciones", ["items"])
    kinds = dominio.get("kinds")
    criticidad = dominio.get("criticidad")
    sin_texto = dominio.get("incluir_sin_texto") or []
    declaradas = dominio.get("prohibiciones_declaradas") or {}
    ruido_distractor = dominio.get("ruido_es_distractor", True)

    def entidad_ok(item: dict[str, Any]) -> bool:
        if not entidad:
            return True
        ids = item.get("entity_ids") or []
        if "entidad" in entidad:
            return entidad["entidad"] in ids
        return any(
            entidades.get(x, {}).get("grupo_homonimo") == entidad["grupo_homonimo"] for x in ids
        )

    candidatos: list[str] = []
    elegibles: list[str] = []
    excluidos: dict[str, str] = {}
    prohibidos: dict[str, str] = {}

    if "items" in colecciones:
        for item in corpus["items"]:
            if kinds and item["kind"] not in kinds:
                continue
            if not _o_en_ambito(item["project_id"], dominio, proyectos):
                continue
            if not entidad_ok(item):
                continue
            if criticidad and (
                not item["criticidad"] or item["criticidad"]["nivel"] not in criticidad
            ):
                continue
            vacio = not item["text"] and item["disponibilidad"] in sin_texto
            if not (item["text"] and _o_ancla(item["text"], ancla)) and not vacio:
                continue
            candidatos.append(item["id"])
            if item["no_usar_como_memoria"]:
                prohibidos[item["id"]] = "PUERTA_NO_USAR_COMO_MEMORIA"
            elif item["id"] in declaradas:
                prohibidos[item["id"]] = declaradas[item["id"]]
            elif item["sensibilidad"] not in estados["sensibilidad"]:
                prohibidos[item["id"]] = "PUERTA_PROPOSITO_NO_AUTORIZADO"
            elif ruido_distractor and item.get("traza") == ["RUIDO"]:
                prohibidos[item["id"]] = "DISTRACTOR_RUIDO"
            elif item["confirmacion"] not in estados["confirmacion"]:
                excluidos[item["id"]] = "confirmacion"
            elif item["validez"] not in estados["validez"]:
                excluidos[item["id"]] = "validez"
            elif item["disponibilidad"] not in estados["disponibilidad"]:
                excluidos[item["id"]] = "disponibilidad"
            else:
                dimension = _o_tiempo(item["temporalidad"], dominio.get("tiempo"))
                if dimension:
                    excluidos[item["id"]] = dimension
                else:
                    elegibles.append(item["id"])
    if "mensajes" in colecciones:
        for mensaje in corpus["mensajes"]:
            if not _o_en_ambito(mensaje["project_id"], dominio, proyectos):
                continue
            vacio = not mensaje["texto"] and "MENSAJE_DESTRUIDO" in sin_texto
            if not (mensaje["texto"] and _o_ancla(mensaje["texto"], ancla)) and not vacio:
                continue
            candidatos.append(mensaje["id"])
            if mensaje["no_guardar"]:
                excluidos[mensaje["id"]] = "no_guardar"
            elif mensaje["redactado"]:
                excluidos[mensaje["id"]] = "redactado"
            elif mensaje["id"] in declaradas:
                prohibidos[mensaje["id"]] = declaradas[mensaje["id"]]
            else:
                elegibles.append(mensaje["id"])
    if "documentos" in colecciones:
        for documento in corpus["documentos"]:
            texto = " ".join(filter(None, [documento["titulo"], documento.get("texto")]))
            if not _o_ancla(texto, ancla):
                continue
            candidatos.append(documento["id"])
            if not documento["accesible"]:
                excluidos[documento["id"]] = "accesible"
            else:
                elegibles.append(documento["id"])

    elegibles = sorted(elegibles)
    limite = dominio.get("limite")
    pendientes: list[str] = []
    resultado = list(elegibles)
    if limite:
        criticos = {
            i["id"]
            for i in corpus["items"]
            if i["criticidad"] and i["criticidad"]["nivel"] == "CRITICO"
        }
        if limite.get("desempate") == "CRITICOS_PRIMERO_LUEGO_ID":
            orden = sorted(elegibles, key=lambda x: (x not in criticos, x))
        else:
            orden = elegibles
        n = limite["n"]
        if limite["tipo"] == "OBJETIVO":
            n = max(n, sum(1 for x in orden if x in criticos))
        resultado = sorted(orden[:n])
        pendientes = sorted(orden[n:])
    return {
        "candidatos": sorted(candidatos),
        "elegibles": elegibles,
        "resultado": resultado,
        "pendientes": pendientes,
        "excluidos": excluidos,
        "prohibidos": prohibidos,
    }


def _sha(datos: Any) -> str:
    return hashlib.sha256(
        json.dumps(datos, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _adjudicaciones(casos: dict[str, Any]):
    """(etiqueta, cardinalidad, adjudicacion, portador) de todo cierre declarado."""
    for caso in casos["nivel_1"]:
        adjudicacion = caso.get("adjudicacion") or {}
        if adjudicacion.get("dominio"):
            yield (
                caso["identificador_canonico"],
                caso["instanciacion"]["cardinalidad"]["valor"],
                adjudicacion,
                caso,
            )
        for rama in caso["instanciacion"]["ramas"]:
            rama_adj = rama.get("adjudicacion") or {}
            if rama_adj.get("dominio"):
                yield (
                    f"{caso['identificador_canonico']}/{rama['sufijo']}",
                    rama.get("cardinalidad_de_la_rama"),
                    rama_adj,
                    rama,
                )


# ===========================================================================
# 1. Canon, lector y fidelidad
# ===========================================================================


def _canon(canon: CS4.Canon, manifiesto: dict[str, Any], inf: Informe) -> None:
    malas = {n: h for n, h in canon.huellas.items() if not h["coincide"]}
    inf.check("SHA-256 de las tres fuentes coincide con el MANIFEST", not malas, malas)
    try:
        CS4.verificar_censo_de_cabeceras()
        inf.check("censo global de cabeceras: tablas reales == identidades que las reclaman", True)
    except CS4.TablaCanonicaError as error:
        inf.check(
            "censo global de cabeceras: tablas reales == identidades que las reclaman",
            False,
            str(error),
        )
    try:
        CS4.verificar_metricas_estrictas()
        inf.check("las 79 celdas de métricas expanden de forma estricta, sin texto crudo", True)
    except CS4.FuenteCanonicaError as error:
        inf.check(
            "las 79 celdas de métricas expanden de forma estricta, sin texto crudo",
            False,
            str(error),
        )
    inf.check(
        "el manifiesto reproduce censo e inventario del lector",
        manifiesto["censo_de_cabeceras"] == CS4.censo_de_cabeceras()
        and manifiesto["tablas_canonicas"] == CS4.inventario_de_tablas(),
        None,
    )


def _literalidad(
    canon: CS4.Canon, casos: dict[str, Any], refs: dict[str, Any], inf: Informe
) -> None:
    vistos = [c["identificador_canonico"] for c in casos["nivel_1"]]
    inf.check(
        "B04-CA-01-50 aparecen exactamente una vez",
        sorted(vistos) == sorted(S4.CA_TOTALES) and len(vistos) == 50,
        {"total": len(vistos)},
    )
    diferencias: list[Any] = []
    for caso in casos["nivel_1"]:
        canonico = canon.casos[caso["identificador_canonico"]]
        for campo in S4.CAMPOS_CANONICOS:
            if getattr(canonico, campo) != caso["canonico"][campo]:
                diferencias.append((caso["id"], campo))
    for ref in refs["referencias_nivel_1"]:
        if ref["tipo_referencia"] != S4.TIPO_REFERENCIA_RECUPERACION:
            continue
        canonico = canon.casos[ref["identificador_canonico"]]
        for campo in S4.CAMPOS_CANONICOS:
            if getattr(canonico, campo) != ref["canonico"][campo]:
                diferencias.append((ref["caso"], campo))
    for caso in casos["nivel_1_pdp"]:
        canonico_pdp = canon.casos_pdp[caso["identificador_canonico"]]
        if (
            caso["canonico"]["entrada_adversarial"] != canonico_pdp.entrada_adversarial
            or caso["canonico"]["resultado_esperado"] != canonico_pdp.resultado_esperado
        ):
            diferencias.append((caso["id"], "pdp"))
    inf.check(
        "los campos canónicos coinciden carácter a carácter con el DOCX",
        not diferencias,
        diferencias[:10],
    )


def _anexo_b(casos: dict[str, Any], inf: Informe) -> None:
    asignaciones = CS4.asignaciones_canonicas_por_ca()
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    perdidas: list[Any] = []
    inventadas: list[Any] = []
    for ca, caso in por_ca.items():
        esperado = asignaciones.get(
            ca, {"red": [], "metricas": [], "familias": [], "metricas_externas": []}
        )
        trazas = caso["trazabilidad"]
        if (
            set(trazas["traza_red_canonica_anexo_b"]) != set(esperado["red"])
            or set(trazas["metrica_canonica_anexo_b"]) != set(esperado["metricas"])
            or set(trazas["metrica_canonica_externa_anexo_b"]) != set(esperado["metricas_externas"])
            or set(trazas["familia_canonica_anexo_b"]) != set(esperado["familias"])
        ):
            (perdidas if esperado["red"] else inventadas).append(ca)
    inf.check("Anexo B canon -> artefacto sin pérdidas", not perdidas, perdidas)
    inf.check("Anexo B artefacto -> canon sin invenciones", not inventadas, inventadas)
    metricas = CS4.metricas_del_anexo_b()
    inf.check(
        "B05-M16 y B08-M25 conservadas como referencias externas",
        "B05-M16" in metricas["externas_canonicas"] and "B08-M25" in metricas["externas_canonicas"],
        None,
    )


# ===========================================================================
# 2. Adjudicación · invariantes y recálculo por oráculo
# ===========================================================================


def _adjudicacion_recalculada(
    conformidad: dict[str, Any], casos: dict[str, Any], inf: Informe
) -> None:
    diferencias: list[Any] = []
    total = 0
    for etiqueta, _card, adjudicacion, _portador in _adjudicaciones(casos):
        total += 1
        cierre = oraculo_universo(conformidad, adjudicacion["dominio"])
        if cierre["candidatos"] != adjudicacion["candidatos_considerados"]:
            diferencias.append((etiqueta, "candidatos", cierre["candidatos"]))
        if cierre["elegibles"] != adjudicacion["elegibles_semanticos"]:
            diferencias.append((etiqueta, "elegibles", cierre["elegibles"]))
        if cierre["resultado"] != adjudicacion["resultado_esperado"]:
            diferencias.append((etiqueta, "resultado", cierre["resultado"]))
        if cierre["pendientes"] != adjudicacion["pendientes_por_limite"]:
            diferencias.append((etiqueta, "pendientes", cierre["pendientes"]))
        declarados_exc = {e["id"]: e["dimension"] for e in adjudicacion["excluidos_por_estado"]}
        if declarados_exc != cierre["excluidos"]:
            diferencias.append((etiqueta, "excluidos", cierre["excluidos"]))
        declarados_pro = {p["id"]: p["razon"] for p in adjudicacion["prohibidos_entre_candidatos"]}
        if declarados_pro != cierre["prohibidos"]:
            diferencias.append((etiqueta, "prohibidos", cierre["prohibidos"]))
    inf.check(
        "el oráculo independiente reproduce las 66 adjudicaciones declaradas",
        not diferencias and total == 66,
        {"total": total, "diferencias": diferencias[:8]},
    )


def _invariantes_adjudicacion(casos: dict[str, Any], inf: Informe) -> None:
    problemas: list[Any] = []
    exhaustivas = 0
    for etiqueta, cardinalidad, adj, portador in _adjudicaciones(casos):
        resultado = set(adj["resultado_esperado"])
        elegibles = set(adj["elegibles_semanticos"])
        pendientes = set(adj["pendientes_por_limite"])
        excluidos = {e["id"] for e in adj["excluidos_por_estado"]}
        prohibidos = {p["id"] for p in adj["prohibidos_entre_candidatos"]}
        candidatos = set(adj["candidatos_considerados"])
        decoys = {d["id"] for d in adj["decoys_fuera_de_ambito"]}
        if cardinalidad == "EXHAUSTIVA":
            exhaustivas += 1
            if resultado != elegibles:
                problemas.append((etiqueta, "EXHAUSTIVA: resultado != elegibles"))
            if resultado | excluidos | prohibidos != candidatos:
                problemas.append((etiqueta, "EXHAUSTIVA: el complemento no es exacto"))
        elif cardinalidad == "ACOTADA":
            if resultado | pendientes != elegibles or resultado & pendientes:
                problemas.append(
                    (etiqueta, "ACOTADA: resultado y pendientes no forman los elegibles o solapan")
                )
        else:
            if resultado != elegibles or pendientes:
                problemas.append((etiqueta, "EXACTA: resultado != elegibles o hay pendientes"))
        if pendientes & (excluidos | prohibidos | decoys):
            problemas.append((etiqueta, "un pendiente por límite figura como prohibido"))
        if decoys & candidatos:
            problemas.append((etiqueta, "un decoy figura entre los candidatos"))
        if not resultado <= candidatos or not elegibles <= candidatos:
            problemas.append((etiqueta, "resultado o elegibles fuera de candidatos"))
        razones_malas = {p["razon"] for p in adj["prohibidos_entre_candidatos"]} - set(
            S4.RAZONES_DE_PROHIBICION
        )
        if razones_malas:
            problemas.append((etiqueta, f"razones fuera de vocabulario {razones_malas}"))
        dimensiones_malas = {e["dimension"] for e in adj["excluidos_por_estado"]} - set(
            S4.DIMENSIONES_DE_EXCLUSION
        )
        if dimensiones_malas:
            problemas.append((etiqueta, f"dimensiones fuera de vocabulario {dimensiones_malas}"))
        # coherencia con los campos legacy del portador
        if "instanciacion" in portador:
            inst = portador["instanciacion"]
            if inst["elegibles"]["valor"] != adj["resultado_esperado"]:
                problemas.append((etiqueta, "instanciacion.elegibles != resultado_esperado"))
            esperado_prohibidos = sorted(excluidos | prohibidos | decoys)
            if inst["prohibidos"]["valor"] != esperado_prohibidos:
                problemas.append((etiqueta, "instanciacion.prohibidos incoherente"))
        elif "candidatos_elegibles" in portador:
            if portador["candidatos_elegibles"] != adj["resultado_esperado"]:
                problemas.append((etiqueta, "rama.candidatos_elegibles != resultado"))
            if portador["candidatos_prohibidos"] != sorted(excluidos | prohibidos | decoys):
                problemas.append((etiqueta, "rama.candidatos_prohibidos incoherente"))
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}
    trece = [
        ca
        for ca, caso in por_ca.items()
        if caso["instanciacion"]["cardinalidad"]["valor"] == "EXHAUSTIVA"
    ]
    con_cierre = [
        ca
        for ca in trece
        if (por_ca[ca].get("adjudicacion") or {}).get("dominio")
        or all(r.get("adjudicacion") for r in por_ca[ca]["instanciacion"]["ramas"])
    ]
    inf.check(
        "los 13 casos EXHAUSTIVA declaran dominio y cierre calculable",
        len(trece) == 13 and sorted(con_cierre) == sorted(trece),
        {"exhaustiva": sorted(trece), "sin_cierre": sorted(set(trece) - set(con_cierre))},
    )
    inf.check(
        "invariantes de adjudicación (EXHAUSTIVA/ACOTADA/EXACTA, pendientes, decoys)",
        not problemas,
        problemas[:10],
    )
    inf.check(
        "las ramas EXHAUSTIVAS de CA-36 y CA-47 cierran con complemento exacto",
        exhaustivas >= 6,
        {"ramas_y_casos_exhaustivos_adjudicados": exhaustivas},
    )


def _puente_critico(conformidad: dict[str, Any], casos: dict[str, Any], inf: Informe) -> None:
    items = conformidad["items"]
    criticos_alfa = sorted(
        i["id"]
        for i in items
        if i["project_id"] == "PRJ-ALFA"
        and i["criticidad"]
        and i["criticidad"]["nivel"] == "CRITICO"
        and i["confirmacion"] == "CONFIRMADA"
        and i["validez"] == "VIGENTE"
        and i["disponibilidad"] == "DISPONIBLE"
    )
    inf.check(
        "PRJ-ALFA contiene exactamente los cinco críticos del canon de CA-31",
        criticos_alfa == sorted(S4.CRITICOS_ALFA_V0_4),
        criticos_alfa,
    )
    gamma = [i for i in items if i["id"] in S4.CRITICOS_GAMMA_V0_4]
    inf.check(
        "MEM-101…112 viven en PRJ-GAMMA con tiempo válido escalonado y texto Gamma",
        len(gamma) == 12
        and all(i["project_id"] == "PRJ-GAMMA" for i in gamma)
        and all(
            i["temporalidad"]["valid_from"] == S4.FECHAS_CRITICOS_GAMMA[i["id"]]
            and i["temporalidad"]["recorded_at"] == i["temporalidad"]["valid_from"]
            for i in gamma
        )
        and all("expediente Gamma" in i["text"] for i in gamma),
        None,
    )
    con_ca31 = [i["id"] for i in gamma if "CA-31" in json.dumps(i, ensure_ascii=False)]
    inf.check(
        "ninguna mención atribuye MEM-101…112 a CA-31; traza y criticidad compartidas",
        not con_ca31
        and all(i["traza"] == ["B04-CA-26", "B04-CA-38", "B04-CA-44"] for i in gamma)
        and all(i["criticidad"]["fuente"] == S4.FUENTE_CRITICIDAD_COMPARTIDA for i in gamma),
        con_ca31,
    )
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}

    def censo(proyecto: str, instante: str) -> int:
        t = _o_fecha(instante)
        total = 0
        for item in items:
            if item["project_id"] != proyecto:
                continue
            if not item["criticidad"] or item["criticidad"]["nivel"] != "CRITICO":
                continue
            if (
                item["confirmacion"] != "CONFIRMADA"
                or item["validez"] != "VIGENTE"
                or item["disponibilidad"] != "DISPONIBLE"
                or item["no_usar_como_memoria"]
            ):
                continue
            vf = _o_fecha(item["temporalidad"]["valid_from"])
            vt = _o_fecha(item["temporalidad"]["valid_to"])
            if (vf is not None and vf > t) or (vt is not None and t >= vt):
                continue
            total += 1
        return total

    fallos: list[Any] = []
    for ca, premisa in S4.PREMISAS_CRITICAS.items():
        adj = por_ca[ca]["adjudicacion"]
        medido = {
            "ambito": adj["dominio"]["ambito"],
            "elegibles": len(adj["elegibles_semanticos"]),
            "devueltos": len(adj["resultado_esperado"]),
            "pendientes": len(adj["pendientes_por_limite"]),
        }
        if medido != premisa:
            fallos.append((ca, "declarado", medido, premisa))
        # El censo se cuenta también sobre el CORPUS en el instante objetivo:
        # una premisa no puede sostenerse solo en la declaración del caso.
        tiempo = adj["dominio"].get("tiempo") or {}
        instante = tiempo.get("instante", S4.AHORA_DECLARADO)
        en_corpus = censo(premisa["ambito"], instante)
        if en_corpus != premisa["elegibles"]:
            fallos.append((ca, "censo_en_corpus", en_corpus, premisa["elegibles"]))
    inf.check(
        "puente canon<->censo: CA-31 5/5, CA-44 6/5/1, CA-26 11/11, CA-38 12/10/2",
        not fallos,
        fallos,
    )


def _barrido_dec016(
    conformidad: dict[str, Any], casos: dict[str, Any], manifiesto: dict, inf: Informe
) -> None:
    sin_016 = {**conformidad, "items": [i for i in conformidad["items"] if i["id"] != "DEC-016"]}
    cambios: list[str] = []
    for etiqueta, _card, adjudicacion, _p in _adjudicaciones(casos):
        con = oraculo_universo(conformidad, adjudicacion["dominio"])
        sin = oraculo_universo(sin_016, adjudicacion["dominio"])
        if con != sin:
            cambios.append(etiqueta)
    inf.check(
        "barrido de impacto de DEC-016: solo la rama R1 de B04-CA-36 cambia",
        cambios == ["B04-CA-36/R1"],
        cambios,
    )
    inf.check(
        "el manifiesto registra el barrido con la misma conclusión",
        manifiesto["barrido_impacto_dec016"]["cambios"] == ["B04-CA-36/R1"],
        manifiesto["barrido_impacto_dec016"],
    )
    dec016 = [i for i in conformidad["items"] if i["id"] == "DEC-016"]
    inf.check(
        "DEC-016 existe, expira antes de AHORA, no tiene sucesor y traza solo a CA-36",
        len(dec016) == 1
        and dec016[0]["temporalidad"]["valid_to"] == "2026-03-01T00:00:00Z"
        and dec016[0]["temporalidad"]["recorded_at"] <= dec016[0]["temporalidad"]["valid_from"]
        and dec016[0]["traza"] == ["B04-CA-36"]
        and not any(
            r
            for r in conformidad["relaciones"]
            if r["origen"] == "DEC-016" or r["destino"] == "DEC-016"
        ),
        None,
    )


# ===========================================================================
# 3. Canon frente a instanciación · modos, insuficiencia y tolerancias
# ===========================================================================


def _operacion_y_modo(canon: CS4.Canon, casos: dict[str, Any], inf: Informe) -> None:
    problemas: list[Any] = []
    for caso in casos["nivel_1"]:
        canonico = canon.casos[caso["identificador_canonico"]]
        texto = " ".join([canonico.entrada, canonico.resultado_esperado, canonico.fallo_observable])
        nombrados = set(re.findall(r"\bM[1-5]\b", texto))
        campo = caso["ficha_pdp_7"]["operacion_y_modo"]
        if campo["estado"] == "CANONICO":
            problemas.append((caso["id"], "el campo completo se declara CANONICO"))
        if campo["valor"]["operacion"]["estado"] != "DERIVADO_PROPUESTO":
            problemas.append((caso["id"], "la operación no es DERIVADO_PROPUESTO"))
        for modo in campo["valor"]["modos"]:
            canonico_esperado = modo["modo"] in nombrados
            if (modo["estado"] == "CANONICO") != canonico_esperado:
                problemas.append((caso["id"], modo["modo"], modo["estado"], sorted(nombrados)))
    inf.check(
        "cada modo se clasifica individualmente: CANONICO solo si el canon lo nombra",
        not problemas,
        problemas[:10],
    )


def _insuficiencia(casos: dict[str, Any], inf: Informe) -> None:
    problemas: list[Any] = []
    for caso in casos["nivel_1"] + casos["nivel_1_pdp"]:
        bloque = caso["ficha_pdp_7"][S4.CAMPO_INSUFICIENCIA]["valor"]
        ramas = caso.get("instanciacion", {}).get("ramas", [])
        esperadas = [r["sufijo"] for r in ramas] or ["CASO_BASE"]
        if [b["rama"] for b in bloque] != esperadas:
            problemas.append((caso["id"], "no está estructurada por rama"))
            continue
        por_sufijo = {r["sufijo"]: r for r in ramas}
        for entrada in bloque:
            rama = por_sufijo.get(entrada["rama"])
            if entrada["aplica"] == "NO_APLICA":
                if not entrada.get("razon"):
                    problemas.append((caso["id"], entrada["rama"], "NO_APLICA sin razón"))
                if rama and rama["modo"] in S4.MODOS_SIN_ESCALERA and rama["etapa_de_la_rama"]:
                    problemas.append((caso["id"], entrada["rama"], "NO_APLICA con etapa declarada"))
                continue
            transiciones = entrada.get("transiciones") or []
            if not transiciones:
                problemas.append((caso["id"], entrada["rama"], "APLICA sin transiciones"))
                continue
            if rama:
                if rama["etapa_de_la_rama"] is None:
                    problemas.append((caso["id"], entrada["rama"], "APLICA sin etapa de rama"))
                elif transiciones[-1]["siguiente_etapa_permitida"] != rama["etapa_de_la_rama"]:
                    problemas.append((caso["id"], entrada["rama"], "destino != etapa_de_la_rama"))
                if rama["modo"] in S4.MODOS_SIN_ESCALERA and rama["etapa_de_la_rama"] is None:
                    problemas.append((caso["id"], entrada["rama"], "M3/M4 con escalera heredada"))
            for transicion in transiciones:
                ajenas = set(transicion["variables_observadas"]) - S4.VARIABLES_INSUFICIENCIA
                if ajenas:
                    problemas.append(
                        (caso["id"], entrada["rama"], f"variables ajenas {sorted(ajenas)}")
                    )
    inf.check(
        "insuficiencia por rama: vocabulario cerrado, M3/M4 sin escalera heredada",
        not problemas,
        problemas[:10],
    )


def _tolerancias(casos: dict[str, Any], inf: Informe) -> None:
    problemas: list[Any] = []
    esperado = {
        "B04-CA-37": (S4.TOL_BANDA_DIFERENCIAL, S4.TOL_VALOR_PENDIENTE),
        "B04-CA-48": (S4.TOL_BANDA_DIFERENCIAL, S4.TOL_VALOR_PENDIENTE),
        "B04-CA-39": (S4.TOL_ORDEN_EQUIVALENCIA, S4.TOL_VALOR_PENDIENTE),
    }
    for caso in casos["nivel_1"] + casos["nivel_1_pdp"]:
        campo = caso["ficha_pdp_7"]["tolerancias"]
        valor = campo["valor"]
        pendiente = valor["valor_pendiente_en"] is not None
        if pendiente != (campo["estado"] == "PENDIENTE_TOL209"):
            problemas.append((caso["id"], "estado incoherente con el pendiente"))
        if pendiente:
            for clave in S4.CLAVES_TEXTO_TOLERANCIA:
                if S4.magnitud_inventada(valor.get(clave, "")):
                    problemas.append((caso["id"], clave, "magnitud numérica bajo PENDIENTE_TOL209"))
        ident = caso["identificador_canonico"]
        if (
            ident in esperado
            and (valor["tolerancia_id"], valor["valor_pendiente_en"]) != esperado[ident]
        ):
            problemas.append((ident, "tolerancia o pendiente incorrectos"))
    inf.check(
        "tolerancias: distinción id/pendiente y prohibición de magnitudes inventadas",
        not problemas,
        problemas,
    )


# ===========================================================================
# 4. PDP-CA · recuento, referencias 50+2, reglas del arnés y exclusiones
# ===========================================================================


def _recuento_oraculo(registro: dict[str, Any]) -> int:
    consumidores = registro["registros_sinteticos_de_consumidores"]
    grupos: dict[Any, list[str]] = {}
    for consumidor in consumidores:
        if "dependencias" in consumidor:
            clave = tuple(sorted(consumidor["dependencias"]))
        else:
            clave = consumidor["interprete"]
        grupos.setdefault(clave, []).append(consumidor["id"])
    return len(grupos)


def _pdp_funcionales(casos: dict[str, Any], refs: dict[str, Any], inf: Informe) -> None:
    funcionales = {c["identificador_canonico"]: c for c in casos["nivel_1_pdp"]}
    inf.check(
        "solo PDP-CA-09 y PDP-CA-22 son casos funcionales",
        set(funcionales) == set(S4.PDP_CA_FUNCIONALES),
        sorted(funcionales),
    )
    problemas: list[Any] = []
    for pdp, caso in funcionales.items():
        inst = caso["instanciacion"]
        for campo in S4.CAMPOS_RECUPERACION_NO_APLICABLES:
            if inst[campo]["valor"] is not None:
                problemas.append((pdp, campo, "vocabulario de recuperación con valor"))
        referencia = caso["ficha_pdp_7"]["referencia"]["valor"]
        if referencia["tipo_referencia"] != S4.TIPO_REFERENCIA_RECUENTO:
            problemas.append((pdp, "tipo_referencia"))
        if _recuento_oraculo(referencia) != referencia["recuento_esperado_independientes"]:
            problemas.append((pdp, "el recuento esperado no se deriva de los registros"))
        if "recuperacion_b04" in json.dumps(inst, ensure_ascii=False):
            problemas.append((pdp, "menciona la operación recuperacion_b04"))
        for par in referencia["pares_no_independientes"]:
            ids = {c["id"] for c in referencia["registros_sinteticos_de_consumidores"]}
            if not set(par) <= ids:
                problemas.append((pdp, "par no independiente fuera de los registros"))
    inf.check(
        "PDP-CA-09/22: recuento de independencia falsable, sin vocabulario de recuperación",
        not problemas,
        problemas,
    )
    conteos = refs["conteos"]
    inf.check(
        "references_v0_4 contiene 52 referencias: 50 de recuperación y 2 de recuento",
        conteos["referencias_totales"] == 52
        and conteos["referencias_recuperacion_b04"] == 50
        and conteos["referencias_recuento_pdp"] == 2,
        conteos,
    )
    tipos = Counter(r["tipo_referencia"] for r in refs["referencias_nivel_1"])
    inf.check(
        "los dos tipos de referencia no se confunden entre sí",
        tipos[S4.TIPO_REFERENCIA_RECUPERACION] == 50
        and tipos[S4.TIPO_REFERENCIA_RECUENTO] == 2
        and all(
            ("referencia_de_recuento" in r) == (r["tipo_referencia"] == S4.TIPO_REFERENCIA_RECUENTO)
            for r in refs["referencias_nivel_1"]
        ),
        dict(tipos),
    )


def _pdp_y_reglas(
    canon: CS4.Canon, pdp: dict[str, Any], reglas: dict[str, Any], inf: Informe
) -> None:
    a = set(pdp["casos_funcionales_nivel_1"])
    b = set(pdp["reglas_de_protocolo_del_arnes"])
    c = set(pdp["casos_fuera_de_alcance"])
    inf.check(
        "los 28 PDP-CA quedan en tres clases disjuntas (2/6/20)",
        a | b | c == set(canon.casos_pdp)
        and not (a & b or a & c or b & c)
        and (len(a), len(b), len(c)) == (2, 6, 20),
        {"funcionales": len(a), "reglas": len(b), "fuera": len(c)},
    )
    sin_red_mal = [
        k
        for k, v in pdp["casos_fuera_de_alcance"].items()
        if not v["red_que_lo_asigna"]
        and v["motivo"] != "Ninguna fila RED del Anexo B asigna este PDP-CA."
    ]
    inf.check("los PDP-CA sin fila RED llevan el motivo exacto", not sin_red_mal, sin_red_mal)
    sin_nota = [
        k
        for k, v in pdp["casos_fuera_de_alcance"].items()
        if "ADR-002" in v["responsable"] and "nota_responsable" not in v
    ]
    inf.check(
        "responsable_de_familia aclarado donde incluye ADR-002",
        not sin_nota,
        sin_nota,
    )
    problemas: list[Any] = []
    for regla in reglas["reglas"]:
        estado = regla.get("estado_de_la_fuente")
        if estado not in S4.ESTADOS_FUENTE_REGLA:
            problemas.append((regla["identificador_canonico"], estado))
        if not regla.get("justificacion_estado_fuente"):
            problemas.append((regla["identificador_canonico"], "sin justificación"))
        esperado = S4.ESTADO_FUENTE_POR_REGLA[regla["identificador_canonico"]][0]
        if estado != esperado:
            problemas.append((regla["identificador_canonico"], estado, esperado))
        for campo in S4.CAMPOS_PROHIBIDOS_EN_REGLA:
            if campo in regla:
                problemas.append((regla["identificador_canonico"], f"campo prohibido {campo}"))
    inf.check(
        "cada regla del arnés declara y justifica el estado de su fuente",
        not problemas,
        problemas,
    )


# ===========================================================================
# 5. T0 · fuera de todos los congelables, incluido el manifiesto
# ===========================================================================


def _t0(artefactos: dict[str, Any], casos: dict[str, Any], inf: Informe) -> None:
    hallazgos: list[Any] = []
    for nombre in S4.CONGELABLES_V0_4:
        if nombre == "performance_corpus_v0_2.json":
            crudo = (AQUI / nombre).read_text(encoding="utf-8")
        elif nombre == "pdp_harness_rules_v0_2.json":
            # `campos_prohibidos` ES la declaración de la prohibición: se
            # escanean las reglas, que es donde una previsión podría colarse.
            crudo = json.dumps(artefactos[nombre]["reglas"], ensure_ascii=False)
        else:
            crudo = json.dumps(artefactos[nombre], ensure_ascii=False)
        for clave in S4.CLAVES_PREVISION_T0:
            if f'"{clave}"' in crudo:
                hallazgos.append((nombre, clave))
        for valor in S4.VALORES_PREVISION_T0:
            if valor in crudo:
                hallazgos.append((nombre, valor))
    inf.check(
        "ningún congelable —manifiesto incluido— contiene previsión sobre T0",
        not hallazgos,
        hallazgos,
    )
    proyeccion = artefactos["t0_preexecution_projection_v0_2.json"]
    inf.check(
        "la proyección T0 sigue no normativa, no congelable y fuera de la lista",
        proyeccion["normativo"] is False
        and proyeccion["congelable"] is False
        and "t0_preexecution_projection_v0_2.json" not in S4.CONGELABLES_V0_4
        and proyeccion["congelables_excluidos"]["congelables"] == list(S4.CONGELABLES_V0_4),
        None,
    )
    funcionales = {c["identificador_canonico"] for c in casos["nivel_1"] + casos["nivel_1_pdp"]}
    proyectados = {p["identificador_canonico"] for p in proyeccion["proyecciones"]}
    inf.check(
        "la proyección cubre los 52 casos funcionales y ninguna regla del arnés",
        proyectados == funcionales
        and not proyectados & set(S4.PDP_CA_REGLAS_DE_ARNES)
        and proyeccion["conteos"]["reglas_de_arnes_proyectadas"] == 0,
        None,
    )
    estados = [
        c["id"]
        for c in casos["nivel_1"] + casos["nivel_1_pdp"] + casos["nivel_2"] + casos["nivel_3"]
        if c["t0"].get("estado_t0") != S4.ESTADO_T0
    ]
    inf.check("todo caso declara estado_t0 = NO_MEDIDO", not estados, estados)


# ===========================================================================
# 6. Corpus de rendimiento · huella, alcance y guardas por oráculo
# ===========================================================================


def _guardas_rendimiento(ruta_perf: Path, manifiesto: dict[str, Any], inf: Informe) -> dict:
    crudo = ruta_perf.read_bytes()
    sha = hashlib.sha256(crudo).hexdigest()
    inf.check(
        "performance_corpus_v0_2.json es byte a byte el congelado (SHA-256)",
        sha == S4.SHA256_PERFORMANCE_V0_2 == manifiesto["corpus_rendimiento"]["sha256"],
        {"sha256": sha},
    )
    alcance = manifiesto["corpus_rendimiento"]["alcance_de_medida"]
    inf.check(
        "el manifiesto delimita qué mide y qué NO mide el corpus de rendimiento",
        alcance["mide"] == list(S4.ALCANCE_RENDIMIENTO["mide"])
        and alcance["no_mide"] == list(S4.ALCANCE_RENDIMIENTO["no_mide"]),
        None,
    )
    perf = json.loads(crudo.decode("utf-8"))
    return calcular_guardas(perf)


def calcular_guardas(perf: dict[str, Any]) -> dict[str, Any]:
    """Oráculo de correlaciones: contadores propios, sin funciones del generador.

    El artefacto no transporta el mapa palabra->familia temática, así que la
    correlación tema<->proyecto se mide por coocurrencia token<->proyecto
    (información mutua), que es más fina que la familia y cubre el mismo
    riesgo: un proyecto identificable por vocabulario dispara la cota.
    """
    elementos = [(i["project_id"], i["text"]) for i in perf["items"]]
    elementos += [(m["project_id"], m["texto"]) for m in perf["mensajes"]]
    total_tokens: Counter[str] = Counter()
    por_proyecto: dict[str, Counter[str]] = {}
    for proyecto, texto in elementos:
        tokens = [t for t in _o_norm(texto) if len(t) >= 4]
        total_tokens.update(tokens)
        por_proyecto.setdefault(proyecto, Counter()).update(tokens)
    n_total = sum(total_tokens.values())
    im = 0.0
    for conteo in por_proyecto.values():
        peso_proyecto = sum(conteo.values()) / n_total
        for token, n in conteo.items():
            pxy = n / n_total
            px = peso_proyecto
            py = total_tokens[token] / n_total
            im += pxy * math.log2(pxy / (px * py))
    exceso_max = 0.0
    for eje in ("confirmacion", "validez", "sensibilidad", "polaridad"):
        base = Counter(i[eje] for i in perf["items"])
        n_items = len(perf["items"])
        por_token: dict[str, Counter[str]] = {}
        for item in perf["items"]:
            for token in set(_o_norm(item["text"])):
                if len(token) >= 4:
                    por_token.setdefault(token, Counter())[item[eje]] += 1
        for conteo in por_token.values():
            n = sum(conteo.values())
            if n < S4.GUARDAS_RENDIMIENTO["n_minimo_exceso"]:
                continue
            valor, k = conteo.most_common(1)[0]
            exceso = k / n - base[valor] / n_items
            exceso_max = max(exceso_max, exceso)
    uso_entidades: dict[str, set[str]] = {}
    for item in perf["items"]:
        for entidad in item.get("entity_ids", []):
            uso_entidades.setdefault(entidad, set()).add(item["project_id"])
    con_alias = [e["id"] for e in perf["entidades"] if e["alias"]]
    proyectos_min_alias = min((len(uso_entidades.get(e, set())) for e in con_alias), default=0)
    tipos = Counter(r["tipo"] for r in perf["relaciones"])
    cuota_tipo = max(tipos.values()) / len(perf["relaciones"])
    proyecto_de = {i["id"]: i["project_id"] for i in perf["items"]}
    intra = sum(
        1 for r in perf["relaciones"] if proyecto_de[r["origen"]] == proyecto_de[r["destino"]]
    ) / len(perf["relaciones"])
    return {
        "im_tema_proyecto_bits": round(im, 6),
        "exceso_estado_palabra_max": round(exceso_max, 4),
        "proyectos_minimos_por_entidad_con_alias": proyectos_min_alias,
        "cuota_maxima_tipo_relacion": round(cuota_tipo, 4),
        "relaciones_intra_proyecto": round(intra, 4),
    }


def _cotas_guardas(medidas: dict[str, Any], inf: Informe) -> None:
    cotas = S4.GUARDAS_RENDIMIENTO
    fallos = []
    if medidas["im_tema_proyecto_bits"] > cotas["im_tema_proyecto_bits_max"]:
        fallos.append("im_tema_proyecto")
    if medidas["exceso_estado_palabra_max"] > cotas["exceso_estado_palabra_max"]:
        fallos.append("exceso_estado_palabra")
    if (
        medidas["proyectos_minimos_por_entidad_con_alias"]
        < cotas["proyectos_minimos_por_entidad_con_alias"]
    ):
        fallos.append("alias_confinados")
    if medidas["cuota_maxima_tipo_relacion"] > cotas["cuota_maxima_tipo_relacion"]:
        fallos.append("cuota_tipo_relacion")
    if not (
        cotas["intra_proyecto_min"]
        <= medidas["relaciones_intra_proyecto"]
        <= cotas["intra_proyecto_max"]
    ):
        fallos.append("intra_proyecto")
    inf.check(
        "guardas de neutralidad sintética dentro de cota (oráculo independiente)",
        not fallos,
        {"fallan": fallos, "medidas": medidas},
    )


# ===========================================================================
# 7. Conformidad · identidad, colisiones y fenómenos
# ===========================================================================


def _conformidad(conformidad: dict[str, Any], inf: Informe) -> None:
    conteos_reales = {
        "proyectos": len(conformidad["proyectos"]),
        "entidades": len(conformidad["entidades"]),
        "items": len(conformidad["items"]),
        "recuerdos": sum(1 for i in conformidad["items"] if i["kind"] == "MEMORIA"),
        "decisiones": sum(1 for i in conformidad["items"] if i["kind"] == "DECISION"),
        "mensajes": len(conformidad["mensajes"]),
        "documentos": len(conformidad["documentos"]),
        "relaciones": len(conformidad["relaciones"]),
    }
    inf.check(
        "conteos contados sobre los datos: 95 items (79+16) tras añadir DEC-016",
        conformidad["conteos"] == conteos_reales
        and conteos_reales["items"] == 95
        and conteos_reales["decisiones"] == 16,
        {"declarado": conformidad["conteos"], "real": conteos_reales},
    )
    identidad_oraculo = {
        coleccion: {
            "conteo": len(conformidad[coleccion]),
            "huella_coleccion": _sha(conformidad[coleccion]),
            "huella_por_elemento": {e["id"]: _sha(e) for e in conformidad[coleccion]},
        }
        for coleccion in ("items", "mensajes", "documentos", "relaciones", "entidades", "proyectos")
    }
    inf.check(
        "identidad por elemento intacta (huellas recalculadas por el oráculo)",
        identidad_oraculo == conformidad["identidad"],
        None,
    )
    raices: dict[str, set[str]] = {}
    proyecto_de: dict[str, str] = {}
    for item in conformidad["items"]:
        proyecto_de[item["id"]] = item["project_id"]
        for token in _o_norm(item["text"]):
            if len(token) >= 6 and token not in S4.VACIAS:
                raices.setdefault(token[:6], set()).add(item["id"])
    colisiones = [
        {"raiz": raiz, "items": sorted(ids), "proyectos": sorted({proyecto_de[i] for i in ids})}
        for raiz, ids in sorted(raices.items())
        if len(ids) > 1 and len({proyecto_de[i] for i in ids}) > 1
    ]
    inf.check(
        "las colisiones por raíz declaradas coinciden con las recalculadas",
        colisiones == conformidad["colisiones_por_raiz_declaradas"],
        {
            "recalculadas": len(colisiones),
            "declaradas": len(conformidad["colisiones_por_raiz_declaradas"]),
        },
    )
    sub = V1.Informe()
    V1._fenomenos(conformidad, sub)
    faltan = sub.comprobaciones[0]["detalle"]["faltan"]
    inf.check("fenómenos obligatorios representados", not faltan, faltan)
    for nombre, funcion in (
        ("las siete dimensiones usan vocabulario canónico", V1._dimensiones),
        ("toda marca crítica lleva nivel, razón, fuente y regla", V1._criticidad),
    ):
        sub = V1.Informe()
        funcion(conformidad, sub)
        fallos = [c for c in sub.comprobaciones if c["resultado"] == "FALLO"]
        inf.check(nombre, not fallos, fallos)
    cierre47 = conformidad["cierre_exhaustivo_ca47"]
    inf.check(
        "el cierre de CA-47 del corpus conserva R1/R2/R3 verificados",
        cierre47["R1"]["elegibles"] == ["DEC-011", "DEC-015"]
        and cierre47["R2"]["elegibles"] == ["DEC-005", "DEC-009", "DEC-014"]
        and cierre47["R3"]["elegibles"] == ["DEC-005", "DEC-014", "DEC-015"],
        {k: v["elegibles"] for k, v in cierre47.items()},
    )


# ===========================================================================
# 8. Conservación, determinismo y no mutación
# ===========================================================================


def _instantanea() -> dict[str, tuple[int, bytes]]:
    return {p.name: (p.stat().st_size, p.read_bytes()) for p in sorted(AQUI.glob("*.json"))}


def _conservacion(inf: Informe) -> None:
    ausentes = [n for n in ARTEFACTOS_ANTERIORES if not (AQUI / n).is_file()]
    inf.check("los artefactos v0.1, v0.2 y v0.3 siguen presentes", not ausentes, ausentes)
    inf.check(
        "comportamiento mutante de validate_corpus_v0_2 documentado en el manifiesto",
        "validate_corpus_v0_2" in json.dumps(cargar()["benchmark_manifest_v0_4.json"]),
        None,
    )


def _determinismo(antes: dict[str, tuple[int, bytes]], inf: Informe) -> None:
    from experiments.adr002.benchmark import build_corpus_v0_4 as B4  # solo aquí

    with tempfile.TemporaryDirectory(prefix="adr002-v04-") as tmp:
        primero, segundo = Path(tmp) / "1", Path(tmp) / "2"
        B4.escribir_en(primero)
        B4.escribir_en(segundo)
        comprometidos = {n: (AQUI / n).read_bytes() for n in FICHEROS}
        uno = {n: (primero / n).read_bytes() for n in FICHEROS}
        dos = {n: (segundo / n).read_bytes() for n in FICHEROS}
        inf.check(
            "doble regeneración en temporal, byte a byte idéntica",
            uno == dos,
            [n for n in FICHEROS if uno[n] != dos[n]],
        )
        inf.check(
            "los artefactos comprometidos coinciden con la regeneración",
            comprometidos == uno,
            [n for n in FICHEROS if comprometidos[n] != uno[n]],
        )
    despues = _instantanea()
    inf.check(
        "validar no escribió en el árbol de trabajo",
        antes == despues,
        {
            "cambiados": [n for n in antes if antes.get(n) != despues.get(n)],
            "nuevos": [n for n in despues if n not in antes],
        },
    )


# ===========================================================================
# main
# ===========================================================================


def validar() -> tuple[Informe, dict[str, Any]]:
    antes = _instantanea()
    canon = CS4.cargar_canon()
    artefactos = cargar()
    conformidad = artefactos["conformance_corpus_v0_4.json"]
    casos = artefactos["cases_v0_4.json"]
    refs = artefactos["references_v0_4.json"]
    pdp = artefactos["pdp_cases_v0_3.json"]
    reglas = artefactos["pdp_harness_rules_v0_2.json"]
    manifiesto = artefactos["benchmark_manifest_v0_4.json"]

    inf = Informe()
    _canon(canon, manifiesto, inf)
    _literalidad(canon, casos, refs, inf)
    _anexo_b(casos, inf)
    _adjudicacion_recalculada(conformidad, casos, inf)
    _invariantes_adjudicacion(casos, inf)
    _puente_critico(conformidad, casos, inf)
    _barrido_dec016(conformidad, casos, manifiesto, inf)
    _operacion_y_modo(canon, casos, inf)
    _insuficiencia(casos, inf)
    _tolerancias(casos, inf)
    _pdp_funcionales(casos, refs, inf)
    _pdp_y_reglas(canon, pdp, reglas, inf)
    _t0(artefactos, casos, inf)
    medidas = _guardas_rendimiento(AQUI / "performance_corpus_v0_2.json", manifiesto, inf)
    _cotas_guardas(medidas, inf)
    _conformidad(conformidad, inf)
    _conservacion(inf)
    _determinismo(antes, inf)

    informe = {
        "documento": "Validación v0.4 del benchmark de ADR-002 contra las fuentes canónicas",
        "version_contrato": S4.VERSION_CONTRATO,
        "estado": S4.ESTADO_NO_CONGELADO,
        "no_ejecuta": ["T0", "ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D"],
        "independencia": (
            "El validador no importa evaluar_universo ni ninguna función de cierre del "
            "generador: recalcula las 66 adjudicaciones, huellas, colisiones y guardas con "
            "un oráculo propio que lee los dominios declarados en los artefactos."
        ),
        "puertas": {
            "SRC-ADR002-01": "SATISFECHA",
            "ADR002-TOL-207": "NO SATISFECHA · no se aprueba en esta ronda",
            "ADR002-TOL-208": "NO SATISFECHA · nada se congela; nueva auditoría pendiente",
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
        "universo_critico": manifiesto["universo_critico"],
        "barrido_impacto_dec016": manifiesto["barrido_impacto_dec016"],
        "guardas_rendimiento": {
            "nombre": S4.NOMBRE_GUARDAS,
            "cotas": dict(S4.GUARDAS_RENDIMIENTO),
            "medidas": medidas,
        },
        "comprobaciones": inf.comprobaciones,
    }
    return inf, informe


def main() -> int:
    inf, informe = validar()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(informe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"comprobaciones: {len(inf.comprobaciones)}  fallos: {len(inf.fallos)}")
    for fallo in inf.fallos:
        print(f"  FALLO: {fallo['comprobacion']} -> {str(fallo['detalle'])[:200]}")
    print(f"informe: {SALIDA.relative_to(RAIZ)}")
    return 1 if inf.fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
