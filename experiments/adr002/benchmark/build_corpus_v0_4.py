"""Generador v0.4 · cierre de adjudicación del corpus (paquete 03D).

Ejecuta:

    uv run python -m experiments.adr002.benchmark.build_corpus_v0_4

El modelo pasa a tener tres capas explícitas:

1. ``canonico``      — el texto literal del DOCX; no se reescribe;
2. ``instanciacion`` — las decisiones sintéticas declaradas;
3. ``adjudicacion``  — qué elementos entran, salen, se devuelven o quedan
   pendientes, **calculado** desde un dominio declarado. Ningún conjunto
   esperado se escribe a mano: se deriva con ``evaluar_universo`` y el
   validador lo recalcula con un oráculo que no comparte este código.

Qué cierra respecto del v0.3 —conservado intacto—:

* los **13 casos EXHAUSTIVA** declaran dominio y cierre calculable;
* el **universo crítico** se reconcilia con las premisas numéricas del canon:
  5 críticos en ALFA (CA-31), 6/11/12 vigentes en GAMMA en el instante
  objetivo de CA-44/CA-26/CA-38, mediante el traslado de MEM-101…112 y el
  escalonado de su tiempo válido;
* ``operacion_y_modo`` clasifica **cada modo individualmente**;
* la condición de insuficiencia se deriva de la **etapa de la rama** y su
  modo; M3/M4 no heredan la escalera E0-E5;
* ``PDP-CA-09/22`` dejan de fingir ser consultas de recuperación: llevan una
  referencia de **recuento de independencia de consumidores**, falsable;
* toda previsión T0 vive fuera de los congelables (lista explícita).

No ejecuta T0, no implementa ni ejecuta ADR002-A/B/C/D y no mide nada.
``performance_corpus_v0_2.json`` no se toca: su huella se congela aparte.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import build_corpus as V1
from experiments.adr002.benchmark import build_corpus_v0_2 as B2
from experiments.adr002.benchmark import build_corpus_v0_3 as B3
from experiments.adr002.benchmark import canonical_source_v0_4 as CS4
from experiments.adr002.benchmark import schema_v0_4 as S4

AQUI = Path(__file__).resolve().parent

FICHEROS = (
    "conformance_corpus_v0_4.json",
    "cases_v0_4.json",
    "references_v0_4.json",
    "pdp_cases_v0_3.json",
    "pdp_harness_rules_v0_2.json",
    "t0_preexecution_projection_v0_2.json",
    "benchmark_manifest_v0_4.json",
)

_AHORA = S4.AHORA_DECLARADO

# ===========================================================================
# 1. Corpus de conformidad v0.4 · traslado crítico y nuevo anclaje DEC-016
# ===========================================================================

DEC_016: dict[str, Any] = V1._item(
    "DEC-016",
    "DECISION",
    "PRJ-ALFA",
    "El aforo de la sala de reuniones del expediente era de 12 personas.",
    autoridad="DOCUMENTO_CANONICO",
    temporalidad=V1._temporalidad(
        valid_from="2026-01-05T00:00:00Z",
        valid_to="2026-03-01T00:00:00Z",
        recorded_at="2026-01-05T00:00:00Z",
    ),
    traza=["B04-CA-36"],
)


def _trasladar_criticos(item: dict[str, Any]) -> dict[str, Any]:
    """MEM-101…112: a PRJ-GAMMA, texto Gamma, tiempo escalonado, sin CA-31."""
    numero = item["id"].rsplit("-", 1)[1]
    nuevo = copy.deepcopy(item)
    nuevo["project_id"] = "PRJ-GAMMA"
    nuevo["text"] = (
        f"Restricción esencial dispersa número {int(numero) - 100} del expediente Gamma."
    )
    valid_from = S4.FECHAS_CRITICOS_GAMMA[item["id"]]
    nuevo["temporalidad"] = V1._temporalidad(valid_from=valid_from, recorded_at=valid_from)
    nuevo["traza"] = ["B04-CA-26", "B04-CA-38", "B04-CA-44"]
    nuevo["criticidad"] = {
        "nivel": "CRITICO",
        "razon": "Restricción esencial etiquetada por el corpus antes de ejecutar.",
        "fuente": S4.FUENTE_CRITICIDAD_COMPARTIDA,
        "regla": "CRIT-06",
    }
    return nuevo


def construir_items_v0_4() -> list[dict[str, Any]]:
    base = V1.construir_corpus()
    items: list[dict[str, Any]] = []
    for item in base["items"]:
        if item["id"] in S4.CRITICOS_GAMMA_V0_4:
            items.append(_trasladar_criticos(item))
        else:
            items.append(copy.deepcopy(item))
    items.extend(copy.deepcopy(i) for i in B2.ITEMS_ANADIDOS)
    items.append(copy.deepcopy(DEC_016))
    return items


# ===========================================================================
# 2. Motor de cierre · evaluar_universo
# ===========================================================================
# El validador NO importa esta función: la recalcula con un oráculo propio.


def _p(instante: str | None) -> datetime | None:
    return None if instante is None else datetime.fromisoformat(instante.replace("Z", "+00:00"))


def _tokens(texto: str | None) -> list[str]:
    return B3.normalizar(texto).split()


def _ancla_coincide(texto: str | None, ancla: dict[str, list[str]] | None) -> bool:
    if not ancla:
        return True
    tokens = _tokens(texto)
    todas = ancla.get("todas") or []
    alguna = ancla.get("alguna") or []
    if todas and not all(any(t.startswith(a) for t in tokens) for a in todas):
        return False
    return not alguna or any(any(t.startswith(a) for t in tokens) for a in alguna)


def _en_ambito(project_id: str, dominio: dict[str, Any], proyectos: dict[str, Any]) -> bool:
    regla = dominio.get("regla_multiproyecto", "SOLO_PROYECTO")
    ambito = dominio["ambito"]
    if regla == "GLOBAL_TODOS":
        return True
    if project_id == ambito:
        return True
    if regla == "CON_GLOBAL" and project_id == "PRJ-GLOBAL":
        return True
    if regla == "CON_LISTAS_CERRADAS":
        proyecto = proyectos.get(project_id)
        if proyecto and proyecto.get("tipo") == "MULTI_PROYECTO_CERRADO":
            return ambito in proyecto.get("miembros_lista_cerrada", [])
    return False


def _tiempo_pasa(temporalidad: dict[str, Any], tiempo: dict[str, Any] | None) -> tuple[bool, str]:
    """(pasa, dimensión-que-falla). Un extremo desconocido no descalifica."""
    if not tiempo or tiempo.get("operador") in (None, "SIN_FILTRO"):
        return True, ""
    operador = tiempo["operador"]
    if operador == "VIGENTE_EN_INSTANTE":
        instante = _p(tiempo["instante"])
        desde, hasta = _p(temporalidad.get("valid_from")), _p(temporalidad.get("valid_to"))
        if desde is not None and desde > instante:
            return False, "tiempo_valido"
        if hasta is not None and instante >= hasta:
            return False, "tiempo_valido"
        return True, ""
    if operador == "SOLAPA_INTERVALO":
        inicio, fin = _p(tiempo["desde"]), _p(tiempo["hasta"])
        desde, hasta = _p(temporalidad.get("valid_from")), _p(temporalidad.get("valid_to"))
        if desde is not None and desde > fin:
            return False, "tiempo_valido"
        if hasta is not None and hasta < inicio:
            return False, "tiempo_valido"
        return True, ""
    if operador == "OCCURRED_EN_INTERVALO":
        valor = _p(temporalidad.get("occurred_at"))
        if valor is None or not (_p(tiempo["desde"]) <= valor < _p(tiempo["hasta"])):
            return False, "occurred_at"
        return True, ""
    if operador == "REGISTRADO_HASTA":
        valor = _p(temporalidad.get("recorded_at"))
        if valor is None or valor > _p(tiempo["hasta"]):
            return False, "recorded_at"
        return True, ""
    raise S4.ContratoCorpusV04Error(f"operador temporal desconocido: {operador}")


def _entidad_coincide(item: dict[str, Any], regla: dict[str, str] | None, entidades: dict) -> bool:
    if not regla:
        return True
    ids = item.get("entity_ids") or []
    if "entidad" in regla:
        return regla["entidad"] in ids
    if "grupo_homonimo" in regla:
        return any(
            entidades.get(e, {}).get("grupo_homonimo") == regla["grupo_homonimo"] for e in ids
        )
    raise S4.ContratoCorpusV04Error(f"regla de entidad desconocida: {regla}")


def evaluar_universo(corpus: dict[str, Any], dominio: dict[str, Any]) -> dict[str, Any]:
    """Calcula candidatos, elegibles, exclusiones y prohibiciones de un dominio."""
    proyectos = {p["id"]: p for p in corpus["proyectos"]}
    entidades = {e["id"]: e for e in corpus["entidades"]}
    estados = {**S4.ESTADOS_ELEGIBLES_DEFECTO, **(dominio.get("estados") or {})}
    ancla = dominio.get("ancla")
    colecciones = dominio.get("colecciones", ["items"])
    kinds = dominio.get("kinds")
    sin_texto = dominio.get("incluir_sin_texto") or []
    declaradas = dominio.get("prohibiciones_declaradas") or {}
    ruido_distractor = dominio.get("ruido_es_distractor", True)

    criticidad_dominio = dominio.get("criticidad")
    candidatos: list[dict[str, Any]] = []
    if "items" in colecciones:
        for item in corpus["items"]:
            if kinds and item["kind"] not in kinds:
                continue
            if not _en_ambito(item["project_id"], dominio, proyectos):
                continue
            if not _entidad_coincide(item, dominio.get("entidad"), entidades):
                continue
            if criticidad_dominio and (
                not item["criticidad"] or item["criticidad"]["nivel"] not in criticidad_dominio
            ):
                continue
            vacio_incluible = not item["text"] and item["disponibilidad"] in sin_texto
            if not (_ancla_coincide(item["text"], ancla) and item["text"]) and not vacio_incluible:
                continue
            candidatos.append(item)
    if "mensajes" in colecciones:
        for mensaje in corpus["mensajes"]:
            if not _en_ambito(mensaje["project_id"], dominio, proyectos):
                continue
            vacio_incluible = not mensaje["texto"] and "MENSAJE_DESTRUIDO" in sin_texto
            if (
                not (_ancla_coincide(mensaje["texto"], ancla) and mensaje["texto"])
                and not vacio_incluible
            ):
                continue
            candidatos.append({"__mensaje__": True, **mensaje})
    if "documentos" in colecciones:
        for documento in corpus["documentos"]:
            texto = " ".join(filter(None, [documento["titulo"], documento.get("texto")]))
            if not _ancla_coincide(texto, ancla):
                continue
            candidatos.append({"__documento__": True, **documento})

    elegibles: list[str] = []
    excluidos: list[dict[str, str]] = []
    prohibidos: list[dict[str, str]] = []
    for c in candidatos:
        ident = c["id"]
        if c.get("__documento__"):
            if not c["accesible"]:
                excluidos.append(
                    {
                        "id": ident,
                        "dimension": "accesible",
                        "valor": "False",
                        "razon": "documento requerido no disponible",
                    }
                )
            else:
                elegibles.append(ident)
            continue
        if c.get("__mensaje__"):
            if c["no_guardar"] or c["redactado"]:
                dimension = "no_guardar" if c["no_guardar"] else "redactado"
                excluidos.append(
                    {
                        "id": ident,
                        "dimension": dimension,
                        "valor": "True",
                        "razon": "contenido destruido o redactado: no existe en ningún espacio",
                    }
                )
            elif ident in declaradas:
                prohibidos.append({"id": ident, "razon": declaradas[ident]})
            else:
                elegibles.append(ident)
            continue
        # items -----------------------------------------------------------
        if c["no_usar_como_memoria"]:
            prohibidos.append({"id": ident, "razon": "PUERTA_NO_USAR_COMO_MEMORIA"})
            continue
        if ident in declaradas:
            prohibidos.append({"id": ident, "razon": declaradas[ident]})
            continue
        if c["sensibilidad"] not in estados["sensibilidad"]:
            prohibidos.append({"id": ident, "razon": "PUERTA_PROPOSITO_NO_AUTORIZADO"})
            continue
        if ruido_distractor and c.get("traza") == ["RUIDO"]:
            prohibidos.append({"id": ident, "razon": "DISTRACTOR_RUIDO"})
            continue
        fallo = None
        for dimension in ("confirmacion", "validez", "disponibilidad"):
            if c[dimension] not in estados[dimension]:
                fallo = (dimension, c[dimension])
                break
        if fallo is None:
            pasa, dimension_t = _tiempo_pasa(c["temporalidad"], dominio.get("tiempo"))
            if not pasa:
                excluidos.append(
                    {
                        "id": ident,
                        "dimension": dimension_t,
                        "valor": json.dumps(c["temporalidad"].get("valid_to"))
                        if dimension_t == "tiempo_valido"
                        else json.dumps(c["temporalidad"].get(dimension_t)),
                        "razon": "fuera del filtro temporal declarado",
                    }
                )
            else:
                elegibles.append(ident)
        else:
            excluidos.append(
                {
                    "id": ident,
                    "dimension": fallo[0],
                    "valor": fallo[1],
                    "razon": "estado fuera de los permitidos por el dominio",
                }
            )

    # límite y desempate -------------------------------------------------
    elegibles = sorted(elegibles)
    limite = dominio.get("limite")
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
            n_criticos = sum(1 for x in orden if x in criticos)
            n = max(n, n_criticos)
        resultado = orden[:n]
        pendientes = orden[n:]
    else:
        resultado = list(elegibles)
        pendientes = []

    return {
        "candidatos_considerados": sorted(c["id"] for c in candidatos),
        "elegibles_semanticos": elegibles,
        "resultado_esperado": sorted(resultado),
        "resultado_en_orden_de_desempate": resultado if limite else None,
        "pendientes_por_limite": sorted(pendientes),
        "excluidos_por_estado": sorted(excluidos, key=lambda x: x["id"]),
        "prohibidos_entre_candidatos": sorted(prohibidos, key=lambda x: x["id"]),
    }


def adjudicar(
    corpus: dict[str, Any], dominio: dict[str, Any], justificacion: str
) -> dict[str, Any]:
    cierre = evaluar_universo(corpus, dominio)
    decoys = dominio.get("decoys") or []
    ids_candidatos = set(cierre["candidatos_considerados"])
    for decoy in decoys:
        if decoy["id"] in ids_candidatos:
            raise S4.ContratoCorpusV04Error(
                f"decoy {decoy['id']} aparece entre los candidatos: no es un decoy"
            )
    return {
        "dominio": dominio,
        **{k: cierre[k] for k in cierre if k != "resultado_en_orden_de_desempate"},
        "resultado_en_orden_de_desempate": cierre["resultado_en_orden_de_desempate"],
        "decoys_fuera_de_ambito": decoys,
        "estado": "DERIVADO_PROPUESTO",
        "justificacion": justificacion,
    }


# ===========================================================================
# 3. Dominios declarados · un dominio por caso y por rama con resultados
# ===========================================================================

_VIGENTE_AHORA = {"operador": "VIGENTE_EN_INSTANTE", "instante": _AHORA}


def _dom(**kwargs: Any) -> dict[str, Any]:
    dominio: dict[str, Any] = {
        "colecciones": ["items"],
        "kinds": ["MEMORIA", "DECISION"],
        "regla_multiproyecto": "SOLO_PROYECTO",
        "tiempo": _VIGENTE_AHORA,
    }
    dominio.update(kwargs)
    return dominio


_D_SENSIBLE_TITULAR = _dom(
    ambito="PRJ-ALFA", ancla={"alguna": ["sensib", "salud", "medic", "titular"]}
)
_D_PREF_REUNIONES = _dom(ambito="PRJ-ALFA", ancla={"todas": ["pref", "reunio"]})
_D_PRESUPUESTO_BETA = _dom(ambito="PRJ-BETA", ancla={"todas": ["presup"]})

DOMINIOS: dict[str, dict[str, Any]] = {
    "B04-CA-01": _dom(
        ambito="GLOBAL", regla_multiproyecto="GLOBAL_TODOS", ancla={"todas": ["redact"]}
    ),
    "B04-CA-02": _dom(
        ambito="PRJ-MADEIRA",
        ancla={"alguna": ["alquil", "coche", "automo", "vehicu", "transp", "viaje"]},
        decoys=[
            {
                "id": "MEM-003",
                "razon": "restricción inversa de PRJ-CANARIAS: contaminaría otros viajes (CA-02)",
            }
        ],
    ),
    "B04-CA-03": _dom(
        ambito="PRJ-GAMMA",
        regla_multiproyecto="CON_LISTAS_CERRADAS",
        ancla={"todas": ["calida"]},
        decoys=[
            {
                "id": "DEC-001",
                "razon": "pertenece a LISTA-CERRADA-AB; Gamma no es miembro y no hereda (CA-03)",
            }
        ],
    ),
    "B04-CA-04": _dom(ambito="PRJ-ALFA", ancla={"todas": ["format", "inform"]}),
    "B04-CA-05": _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["presup"]},
        estados={"validez": ["SUSTITUIDA"]},
        tiempo={"operador": "SIN_FILTRO"},
    ),
    "B04-CA-06": _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["mensajer"]},
        tiempo={"operador": "VIGENTE_EN_INSTANTE", "instante": "2026-09-15T00:00:00Z"},
    ),
    "B04-CA-07": _dom(ambito="PRJ-ALFA", ancla={"todas": ["manten"]}),
    "B04-CA-08": _D_PRESUPUESTO_BETA,
    "B04-CA-09": _D_PREF_REUNIONES,
    "B04-CA-10": _dom(ambito="PRJ-ALFA", ancla={"todas": ["horari", "entreg"]}),
    "B04-CA-11": _dom(
        ambito="PRJ-ALFA", ancla={"todas": ["retira"]}, incluir_sin_texto=["PURGADA"]
    ),
    "B04-CA-12": _D_SENSIBLE_TITULAR,
    "B04-CA-13": _dom(ambito="PRJ-ALFA", entidad={"entidad": "ENT-PROY-ALFA"}),
    "B04-CA-14": _dom(
        ambito="GLOBAL",
        regla_multiproyecto="GLOBAL_TODOS",
        entidad={"grupo_homonimo": "JUAN"},
    ),
    "B04-CA-15": _dom(ambito="PRJ-ALFA", colecciones=["documentos"], ancla={"todas": ["alcanc"]}),
    "B04-CA-16": _dom(
        ambito="PRJ-GAMMA",
        colecciones=["items", "mensajes"],
        ancla={"alguna": ["firmas", "circui"]},
    ),
    "B04-CA-17": _dom(ambito="PRJ-ALFA", ancla={"todas": ["teletr"]}),
    "B04-CA-18": _dom(ambito="PRJ-ALFA", colecciones=["documentos"], ancla={"todas": ["anexo"]}),
    "B04-CA-19": _dom(ambito="PRJ-ALFA", ancla={"todas": ["plataf"]}),
    "B04-CA-20": _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["vuelo", "escala"]},
        decoys=[
            {
                "id": "MEM-015",
                "razon": "regla inversa de PRJ-BETA: fuera del ámbito consultado (CA-20)",
            }
        ],
    ),
    "B04-CA-21": _dom(ambito="PRJ-ALFA", ancla={"todas": ["acept", "escala"]}),
    "B04-CA-22": _dom(
        ambito="PRJ-BETA",
        regla_multiproyecto="CON_LISTAS_CERRADAS",
        kinds=["DECISION"],
        tiempo={
            "operador": "SOLAPA_INTERVALO",
            "desde": "2026-01-10T00:00:00Z",
            "hasta": "2026-03-20T00:00:00Z",
        },
    ),
    "B04-CA-23": _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["presup"]},
        estados={"validez": ["VIGENTE", "SUSTITUIDA"]},
        tiempo={"operador": "SIN_FILTRO"},
    ),
    "B04-CA-24": _dom(ambito="PRJ-ALFA", ancla={"todas": ["alcanc"]}),
    "B04-CA-25": _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["atlas"]},
        decoys=[
            {
                "id": "MEM-018",
                "razon": "usa «Atlas» en PRJ-GAMMA: el ámbito evita el cruce (CA-25)",
            }
        ],
    ),
    "B04-CA-26": _dom(
        ambito="PRJ-GAMMA",
        criticidad=["CRITICO"],
        tiempo={"operador": "VIGENTE_EN_INSTANTE", "instante": "2026-04-01T00:00:00Z"},
        limite={"n": 10, "tipo": "OBJETIVO", "desempate": "CRITICOS_PRIMERO_LUEGO_ID"},
    ),
    "B04-CA-27": _D_PRESUPUESTO_BETA,
    "B04-CA-28": _dom(
        ambito="PRJ-ALFA",
        colecciones=["items", "mensajes"],
        ancla={"alguna": ["sesion", "guarda"]},
        incluir_sin_texto=["NO_GUARDADA", "MENSAJE_DESTRUIDO"],
    ),
    "B04-CA-29": _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["plazo"]},
        estados={"confirmacion": ["CONFIRMADA", "CANDIDATA"]},
    ),
    "B04-CA-30": _dom(
        ambito="PRJ-ALFA",
        regla_multiproyecto="CON_GLOBAL",
        ancla={"alguna": ["redact", "presup", "ahorr"]},
        limite={"n": 3, "tipo": "OBJETIVO", "desempate": "CRITICOS_PRIMERO_LUEGO_ID"},
    ),
    "B04-CA-31": _dom(
        ambito="PRJ-ALFA",
        criticidad=["CRITICO"],
        decoys=[
            {
                "id": "MEM-002",
                "razon": "crítico de PRJ-MADEIRA: fuera del ámbito consultado (CA-31)",
            }
        ],
    ),
    "B04-CA-32": _dom(
        ambito="PRJ-BETA",
        kinds=["DECISION"],
        ancla={"todas": ["aforo"]},
        estados={"validez": ["VIGENTE", "SUSTITUIDA"]},
        tiempo={"operador": "REGISTRADO_HASTA", "hasta": "2026-03-01T00:00:00Z"},
    ),
    "B04-CA-33": _dom(ambito="PRJ-ALFA", ancla={"todas": ["presup"]}),
    "B04-CA-34": _dom(
        ambito="PRJ-ALFA",
        ancla={"alguna": ["planif", "calend", "versio", "vuelo", "ahorr", "presup"]},
        ruido_es_distractor=False,
        limite={"n": 10, "tipo": "OBJETIVO", "desempate": "CRITICOS_PRIMERO_LUEGO_ID"},
    ),
    "B04-CA-35": _dom(
        ambito="PRJ-ALFA",
        colecciones=["items", "mensajes"],
        ancla={"alguna": ["prueba", "memoria"]},
        prohibiciones_declaradas={"MSG-012": "PUERTA_MARCA_EN_CONTENIDO"},
    ),
    "B04-CA-37": _D_SENSIBLE_TITULAR,
    "B04-CA-38": _dom(
        ambito="PRJ-GAMMA",
        criticidad=["CRITICO"],
        tiempo=_VIGENTE_AHORA,
        limite={"n": 10, "tipo": "DURO", "desempate": "ID"},
    ),
    "B04-CA-40": _dom(ambito="PRJ-ALFA", ancla={"todas": ["presup"]}),
    "B04-CA-41": _dom(
        ambito="PRJ-ALFA",
        entidad={"entidad": "ENT-VEHICULO"},
        decoys=[
            {"id": "MEM-002", "razon": "misma entidad en PRJ-MADEIRA: fuera de ámbito (CA-41)"},
            {"id": "MEM-003", "razon": "misma entidad en PRJ-CANARIAS: fuera de ámbito (CA-41)"},
        ],
    ),
    "B04-CA-42": _dom(ambito="PRJ-ALFA", entidad={"entidad": "ENT-POSTGRESQL"}),
    "B04-CA-43": _dom(ambito="PRJ-ALFA", ancla={"alguna": ["entregab", "equipo"]}),
    "B04-CA-44": _dom(
        ambito="PRJ-GAMMA",
        criticidad=["CRITICO"],
        tiempo={"operador": "VIGENTE_EN_INSTANTE", "instante": "2026-02-01T00:00:00Z"},
        limite={"n": 5, "tipo": "DURO", "desempate": "ID"},
    ),
    "B04-CA-45": _dom(
        ambito="PRJ-ALFA", colecciones=["items", "mensajes"], ancla={"todas": ["presup"]}
    ),
    "B04-CA-46": _dom(ambito="PRJ-BETA", ancla={"todas": ["nomina"]}),
    "B04-CA-48": _D_SENSIBLE_TITULAR,
    "B04-CA-49": _dom(
        ambito="PRJ-ALFA", colecciones=["items", "mensajes"], ancla={"todas": ["pref", "reunio"]}
    ),
    "B04-CA-50": _dom(ambito="PRJ-ALFA", ancla={"todas": ["almace", "acceso"]}),
}

JUSTIFICACIONES: dict[str, str] = {
    "B04-CA-05": "la consulta pide expresamente la versión anterior: el dominio es lo sustituido",
    "B04-CA-22": (
        "solapamiento de tiempo válido sobre el intervalo ya instanciado en v0.1; las "
        "decisiones de listas cerradas que contienen BETA aplican a BETA (semántica de CA-03)"
    ),
    "B04-CA-23": "la consulta pide la vigente y la reemplazada: ambas valideces entran",
    "B04-CA-25": "«Ámbito evita cruces»: el resultado en ámbito se devuelve, no se pide aclaración",
    "B04-CA-29": "afirmación externa: se devuelve atribuida a la fuente, nunca como hecho propio",
    "B04-CA-30": (
        "la premisa canónica es «Tres resultados con señales distintas»: preferencia global, "
        "decisión de proyecto y restricción condicionada"
    ),
    "B04-CA-31": "los cinco críticos del canon son los cinco críticos elegibles de PRJ-ALFA",
    "B04-CA-32": (
        "corte de registro: lo que Sirius sabía el 1 de marzo incluye la versión hoy "
        "sustituida; la corrección de abril queda tras el corte"
    ),
    "B04-CA-34": (
        "la premisa canónica es «tres críticos y siete ordinarios»: el paquete de contexto "
        "incluye ruido ordinario real; con objetivo 10 y críticos primero quedan 3+7 y un "
        "ordinario pendiente"
    ),
    "B04-CA-38": "límite duro 10 sobre los 12 críticos vigentes en el instante objetivo",
    "B04-CA-44": "límite duro 5 sobre los 6 críticos vigentes en el instante objetivo, con empate",
}

# Resultados esperados: el generador ABORTA si el cierre calculado difiere.
ESPERADOS: dict[str, dict[str, list[str]]] = {
    "B04-CA-01": {"resultado": ["MEM-001"]},
    "B04-CA-02": {"resultado": ["MEM-002"]},
    "B04-CA-03": {"resultado": []},
    "B04-CA-04": {"resultado": []},
    "B04-CA-05": {"resultado": ["DEC-002"]},
    "B04-CA-06": {"resultado": ["DEC-004"]},
    "B04-CA-07": {"resultado": ["MEM-005"]},
    "B04-CA-08": {"resultado": ["DEC-005", "MEM-006"]},
    "B04-CA-09": {"resultado": []},
    "B04-CA-10": {"resultado": []},
    "B04-CA-11": {"resultado": []},
    "B04-CA-12": {"resultado": []},
    "B04-CA-13": {"resultado": ["MEM-011"]},
    "B04-CA-14": {"resultado": ["MEM-012", "MEM-013"]},
    "B04-CA-15": {"resultado": ["DOC-005"]},
    "B04-CA-16": {"resultado": ["MEM-027", "MSG-011"]},
    "B04-CA-17": {"resultado": []},
    "B04-CA-18": {"resultado": []},
    "B04-CA-19": {"resultado": ["DEC-006", "DEC-007", "DEC-008"]},
    "B04-CA-20": {"resultado": ["MEM-014"]},
    "B04-CA-21": {"resultado": ["MEM-016"]},
    "B04-CA-22": {"resultado": ["DEC-001", "DEC-005", "DEC-009", "DEC-011", "DEC-014", "DEC-015"]},
    "B04-CA-23": {"resultado": ["DEC-002", "DEC-003"]},
    "B04-CA-24": {"resultado": []},
    "B04-CA-25": {"resultado": ["MEM-011"]},
    "B04-CA-26": {
        "resultado": [f"MEM-{n}" for n in range(101, 112)],
        "pendientes": [],
    },
    "B04-CA-27": {"resultado": ["DEC-005", "MEM-006"]},
    "B04-CA-28": {"resultado": []},
    "B04-CA-29": {"resultado": ["MEM-020"]},
    "B04-CA-30": {"resultado": ["DEC-003", "MEM-001", "MEM-016"], "pendientes": []},
    "B04-CA-31": {"resultado": ["DEC-003", "DEC-010", "MEM-014", "MEM-016", "MEM-025"]},
    "B04-CA-32": {"resultado": ["DEC-012"]},
    "B04-CA-33": {"resultado": ["DEC-003"]},
    "B04-CA-34": {"pendientes_n": 1, "criticos_en_resultado": 3, "resultado_n": 10},
    "B04-CA-35": {"resultado": []},
    "B04-CA-37": {"resultado": []},
    "B04-CA-38": {
        "resultado": [f"MEM-{n}" for n in range(101, 111)],
        "pendientes": ["MEM-111", "MEM-112"],
    },
    "B04-CA-40": {"resultado": ["DEC-003"]},
    "B04-CA-41": {"resultado": ["MEM-022"]},
    "B04-CA-42": {"resultado": ["DEC-010"]},
    "B04-CA-43": {"resultado": ["MEM-023", "MEM-024"]},
    "B04-CA-44": {
        "resultado": [f"MEM-{n}" for n in range(101, 106)],
        "pendientes": ["MEM-106"],
    },
    "B04-CA-45": {"resultado": ["DEC-003", "MSG-010"]},
    "B04-CA-46": {"resultado": []},
    "B04-CA-48": {"resultado": []},
    "B04-CA-49": {"resultado": ["MSG-020"]},
    "B04-CA-50": {"resultado": ["MEM-025"]},
}

# --- Dominios por rama ------------------------------------------------------

DOMINIOS_RAMA: dict[tuple[str, str], dict[str, Any]] = {
    ("B04-CA-09", "R1"): _D_PREF_REUNIONES,
    ("B04-CA-09", "R2"): _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["pref", "reunio"]},
        estados={"confirmacion": ["CANDIDATA"]},
    ),
    ("B04-CA-10", "R1"): _dom(ambito="PRJ-ALFA", ancla={"todas": ["horari", "entreg"]}),
    ("B04-CA-10", "R2"): _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["horari", "entreg"]},
        estados={"confirmacion": ["RECHAZADA"]},
    ),
    ("B04-CA-24", "R1"): _dom(ambito="PRJ-ALFA", ancla={"todas": ["alcanc"]}),
    ("B04-CA-24", "R2"): _dom(
        ambito="PRJ-ALFA", ancla={"todas": ["alcanc"]}, estados={"validez": ["SIN_SOPORTE"]}
    ),
    ("B04-CA-35", "R1"): DOMINIOS["B04-CA-35"],
    ("B04-CA-35", "R2"): _dom(
        ambito="PRJ-ALFA", colecciones=["mensajes"], ancla={"alguna": ["prueba", "memoria"]}
    ),
    ("B04-CA-36", "R1"): _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["aforo"]},
        decoys=[
            {"id": "DEC-012", "razon": "aforo de PRJ-BETA: fuera del ámbito consultado (CA-36)"},
            {"id": "DEC-013", "razon": "aforo de PRJ-BETA: fuera del ámbito consultado (CA-36)"},
        ],
    ),
    ("B04-CA-36", "R2"): _D_PREF_REUNIONES,
    ("B04-CA-36", "R3"): _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["clave"]},
        decoys=[
            {
                "id": "MEM-018",
                "razon": "el nombre en clave vive en PRJ-GAMMA: fuera del ámbito (CA-36)",
            }
        ],
    ),
    ("B04-CA-47", "R1"): _dom(
        ambito="PRJ-BETA",
        kinds=["DECISION"],
        tiempo={
            "operador": "OCCURRED_EN_INTERVALO",
            "desde": "2026-01-01T00:00:00Z",
            "hasta": "2026-02-01T00:00:00Z",
        },
    ),
    ("B04-CA-47", "R2"): _dom(
        ambito="PRJ-BETA",
        kinds=["DECISION"],
        tiempo={"operador": "VIGENTE_EN_INSTANTE", "instante": "2026-01-20T00:00:00Z"},
    ),
    ("B04-CA-47", "R3"): _dom(
        ambito="PRJ-BETA",
        kinds=["DECISION"],
        tiempo={"operador": "REGISTRADO_HASTA", "hasta": "2026-02-15T00:00:00Z"},
    ),
    ("B04-CA-48", "R1"): _dom(
        ambito="PRJ-ALFA",
        ancla={"alguna": ["sensib", "salud", "medic", "titular"]},
        estados={"sensibilidad": ["ORDINARIA", "RESTRINGIDA"]},
    ),
    ("B04-CA-48", "R2"): _D_SENSIBLE_TITULAR,
    ("B04-CA-48", "R3"): _dom(ambito="PRJ-ALFA", ancla={"todas": ["clinic"]}),
    ("B04-CA-49", "R1"): _dom(
        ambito="PRJ-ALFA", colecciones=["mensajes"], ancla={"todas": ["pref", "reunio"]}
    ),
    ("B04-CA-49", "R2"): _dom(
        ambito="PRJ-ALFA",
        ancla={"todas": ["pref", "reunio"]},
        estados={"confirmacion": ["CANDIDATA"]},
    ),
}

ESPERADOS_RAMA: dict[tuple[str, str], list[str]] = {
    ("B04-CA-09", "R1"): [],
    ("B04-CA-09", "R2"): ["MEM-007"],
    ("B04-CA-10", "R1"): [],
    ("B04-CA-10", "R2"): ["MEM-008"],
    ("B04-CA-24", "R1"): [],
    ("B04-CA-24", "R2"): ["MEM-017"],
    ("B04-CA-35", "R1"): [],
    ("B04-CA-35", "R2"): ["MSG-012"],
    ("B04-CA-36", "R1"): [],
    ("B04-CA-36", "R2"): [],
    ("B04-CA-36", "R3"): [],
    ("B04-CA-47", "R1"): ["DEC-011", "DEC-015"],
    ("B04-CA-47", "R2"): ["DEC-005", "DEC-009", "DEC-014"],
    ("B04-CA-47", "R3"): ["DEC-005", "DEC-014", "DEC-015"],
    ("B04-CA-48", "R1"): ["MEM-010"],
    ("B04-CA-48", "R2"): [],
    ("B04-CA-48", "R3"): [],
    ("B04-CA-49", "R1"): ["MSG-020"],
    ("B04-CA-49", "R2"): ["MEM-007"],
}

# Ramas cuyo cierre es EXHAUSTIVO dentro de su dominio.
RAMAS_EXHAUSTIVAS: frozenset[tuple[str, str]] = frozenset(
    {(ca, r) for (ca, r) in DOMINIOS_RAMA if ca in ("B04-CA-36", "B04-CA-47")}
)

# Etapa real de cada rama. None = el modo no recorre la escalera E0-E5.
ETAPA_DE_RAMA: dict[tuple[str, str], str | None] = {
    ("B04-CA-09", "R1"): "E1",
    ("B04-CA-09", "R2"): None,
    ("B04-CA-10", "R1"): "E1",
    ("B04-CA-10", "R2"): None,
    ("B04-CA-24", "R1"): "E1",
    ("B04-CA-24", "R2"): None,
    ("B04-CA-35", "R1"): "E4",
    ("B04-CA-35", "R2"): None,
    ("B04-CA-36", "R1"): "E4",
    ("B04-CA-36", "R2"): "E4",
    ("B04-CA-36", "R3"): "E4",
    ("B04-CA-47", "R1"): "E1",
    ("B04-CA-47", "R2"): "E1",
    ("B04-CA-47", "R3"): "E1",
    ("B04-CA-48", "R1"): "E0",
    ("B04-CA-48", "R2"): "E0",
    ("B04-CA-48", "R3"): "E0",
    ("B04-CA-49", "R1"): "E4",
    ("B04-CA-49", "R2"): None,
}

# Instanciaciones que cambian respecto de v0.1/v0.3, con su motivo.
CONSULTAS_V0_4: dict[str, str] = {
    "B04-CA-26": "Enumera las restricciones esenciales del expediente Gamma.",
    "B04-CA-30": (
        "Resume mi preferencia de redacción, el presupuesto vigente y la condición de "
        "ahorro en escalas, con su razón."
    ),
}
AMBITOS_V0_4: dict[str, str] = {
    "B04-CA-26": "PRJ-GAMMA",
    "B04-CA-38": "PRJ-GAMMA",
    "B04-CA-44": "PRJ-GAMMA",
}
TIEMPOS_V0_4: dict[str, str] = {
    "B04-CA-26": "2026-04-01T00:00:00Z",
    "B04-CA-38": _AHORA,
    "B04-CA-44": "2026-02-01T00:00:00Z",
}

RAMA_36_R1_V0_4: dict[str, Any] = {
    "sufijo": "R1",
    "clase": "CANONICA_REQUERIDA",
    "objetivo": "Variante cuyo único hallazgo es histórico.",
    "fuente_canonica_de_la_rama": "B04 §17 CA-36 «Dato está solo histórico»",
    "modo": "M1",
    "consulta": "¿Qué aforo tiene autorizado la sala de reuniones del expediente?",
    "proposito": "responder_al_usuario",
    "permiso": "AUTORIZADO",
    "ambito": "PRJ-ALFA",
    "tiempo_objetivo": _AHORA,
    "corte_registro": None,
    "candidatos_elegibles": [],
    "candidatos_prohibidos": ["DEC-016"],
    "esperado_rama": "Estado interno SOLO_HISTORICO, distinto de ausencia real.",
    "estado_suficiencia_esperado": "SOLO_HISTORICO",
    "tolerancia_pendiente": None,
}


# ===========================================================================
# 4. Casos v0.4
# ===========================================================================

_RX_MODO = B3._RX_MODO
_RX_ETAPA = B3._RX_ETAPA
_RX_PARADA = B3._RX_PARADA


def _campo(valor: Any, fuente: str, seccion: str, estado: str, justificacion: str) -> dict:
    return {
        "valor": valor,
        "fuente": fuente,
        "seccion": seccion,
        "estado": estado,
        "justificacion": justificacion,
    }


def _derivado(valor: Any, justificacion: str, seccion: str = "n/a") -> dict[str, Any]:
    return _campo(valor, S4.FUENTE_INSTANCIACION, seccion, "DERIVADO_PROPUESTO", justificacion)


def _texto_canonico(caso: CS4.CasoCanonico) -> str:
    return " ".join([caso.entrada, caso.resultado_esperado, caso.fallo_observable])


def _canonico_si_literal(
    valor: Any, caso: CS4.CasoCanonico, patron: re.Pattern[str] | None, justificacion: str
) -> dict[str, Any]:
    if valor is None:
        return _derivado(None, justificacion)
    texto = _texto_canonico(caso)
    literal = (valor in texto) if patron is None else (valor in set(patron.findall(texto)))
    if literal:
        return _campo(
            valor,
            S4.FUENTE_CANONICA_CA,
            caso.seccion,
            "CANONICO",
            "el texto canónico del propio caso nombra este valor literalmente",
        )
    return _derivado(valor, justificacion)


def _operacion_y_modo(caso: CS4.CasoCanonico, modos: list[str]) -> dict[str, Any]:
    """Cada modo se clasifica individualmente; la operación es siempre derivada."""
    nombrados = set(_RX_MODO.findall(_texto_canonico(caso)))
    detalle = [
        {
            "modo": modo,
            "estado": "CANONICO" if modo in nombrados else "DERIVADO_PROPUESTO",
            "fuente": caso.seccion if modo in nombrados else S4.FUENTE_INSTANCIACION,
        }
        for modo in modos
    ]
    return _campo(
        {
            "operacion": {"valor": "recuperacion_b04", "estado": "DERIVADO_PROPUESTO"},
            "modos": detalle,
        },
        f"{caso.seccion} y {S4.FUENTE_INSTANCIACION}",
        caso.seccion,
        "DERIVADO_PROPUESTO",
        (
            "la operación es vocabulario del arnés y cada modo se clasifica por separado: "
            f"canónicos {sorted(m['modo'] for m in detalle if m['estado'] == 'CANONICO')}, "
            f"derivados {sorted(m['modo'] for m in detalle if m['estado'] != 'CANONICO')}"
        ),
    )


def _insuficiencia_de_rama(rama: str, modo: str | None, etapa: str | None) -> dict[str, Any]:
    if modo in S4.MODOS_SIN_ESCALERA and etapa is None:
        return {
            "rama": rama,
            "aplica": "NO_APLICA",
            "razon": (
                f"{modo} no recorre la escalera E0-E5: es una vista de gestión o de "
                "verificación directa (B04 §5); la política de expansión gobierna la "
                "recuperación ordinaria (B04 §15.1)"
            ),
        }
    if etapa is None:
        return {
            "rama": rama,
            "aplica": "NO_APLICA",
            "razon": "la rama no declara etapa de resolución",
        }
    if etapa == "E0":
        return {
            "rama": rama,
            "aplica": "NO_APLICA",
            "razon": (
                "la rama resuelve en E0: no existe transición posterior que autorizar, y una "
                "expansión sería una decisión libre prohibida por B04-RF-14"
            ),
        }
    orden = ["E0", "E1", "E2", "E3", "E4", "E5"]
    transiciones = []
    for actual, siguiente in itertools.pairwise(orden):
        if orden.index(actual) >= orden.index(etapa):
            break
        datos = B3.TRANSICIONES[f"{actual}->{siguiente}"]
        transiciones.append(
            {
                "etapa_actual": actual,
                "variables_observadas": datos["variables"].split("|"),
                "predicado": datos["predicado"],
                "umbral_o_condicion_logica": datos["umbral"],
                "siguiente_etapa_permitida": siguiente,
                "fuente": "B04 v1.0 APROBADO §15.1 y §15.2 · B04-RF-14 y B04-RF-16",
                "estado": "DERIVADO_PROPUESTO",
            }
        )
    return {"rama": rama, "aplica": "APLICA", "transiciones": transiciones}


def _condicion_insuficiencia(
    ident: str, etapa_caso: str | None, ramas: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if ident == "B04-CA-39":
        return [
            {
                "rama": "CASO_BASE",
                "aplica": "NO_APLICA",
                "razon": (
                    "el caso es un arnés de equivalencia entre dos realizaciones, no una "
                    "consulta de recuperación: el canon no le asigna etapa de expansión"
                ),
            }
        ]
    if not ramas:
        return [_insuficiencia_de_rama("CASO_BASE", None, etapa_caso)]
    return [
        _insuficiencia_de_rama(r["sufijo"], r["modo"], r.get("etapa_de_la_rama")) for r in ramas
    ]


def _prohibidos_legacy(adjudicacion: dict[str, Any]) -> list[str]:
    ids = {e["id"] for e in adjudicacion["excluidos_por_estado"]}
    ids |= {p["id"] for p in adjudicacion["prohibidos_entre_candidatos"]}
    ids |= {d["id"] for d in adjudicacion["decoys_fuera_de_ambito"]}
    return sorted(ids)


def _ramas_v0_4(corpus: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Ramas v0.3 con etapa de rama, adjudicación calculada y CA-36-R1 re-anclada."""
    ramas: dict[str, list[dict[str, Any]]] = {}
    base = {
        ca: [copy.deepcopy(r) for r in lista] for ca, lista in B2.RAMAS.items() if ca != "B04-CA-47"
    }
    base["B04-CA-36"] = [
        copy.deepcopy(RAMA_36_R1_V0_4),
        *(copy.deepcopy(r) for r in B2.RAMAS["B04-CA-36"] if r["sufijo"] != "R1"),
    ]
    base["B04-CA-47"] = [copy.deepcopy(r) for r in B3._ramas_ca47(B3.cierre_ca47(corpus["items"]))]
    for rama in base["B04-CA-47"]:
        rama.pop("cierre", None)
        rama.pop("cardinalidad_de_la_rama", None)
    for ca, lista in sorted(base.items()):
        salida = []
        for rama in lista:
            clave = (ca, rama["sufijo"])
            rama["etapa_de_la_rama"] = ETAPA_DE_RAMA[clave]
            dominio = DOMINIOS_RAMA.get(clave)
            if dominio is not None:
                adjudicacion = adjudicar(
                    corpus,
                    dominio,
                    JUSTIFICACIONES.get(
                        ca, f"cierre calculado de la rama {rama['sufijo']} de {ca}"
                    ),
                )
                esperado = ESPERADOS_RAMA[clave]
                if adjudicacion["resultado_esperado"] != sorted(esperado):
                    raise S4.ContratoCorpusV04Error(
                        f"{ca} {rama['sufijo']}: cierre calculado "
                        f"{adjudicacion['resultado_esperado']} != esperado {sorted(esperado)}"
                    )
                if clave in RAMAS_EXHAUSTIVAS:
                    rama["cardinalidad_de_la_rama"] = "EXHAUSTIVA"
                    union = (
                        set(adjudicacion["resultado_esperado"])
                        | {e["id"] for e in adjudicacion["excluidos_por_estado"]}
                        | {p["id"] for p in adjudicacion["prohibidos_entre_candidatos"]}
                    )
                    if union != set(adjudicacion["candidatos_considerados"]):
                        raise S4.ContratoCorpusV04Error(
                            f"{ca} {rama['sufijo']}: el complemento no es exacto"
                        )
                else:
                    rama["cardinalidad_de_la_rama"] = "EXACTA"
                rama["adjudicacion"] = adjudicacion
                rama["candidatos_elegibles"] = adjudicacion["resultado_esperado"]
                rama["candidatos_prohibidos"] = _prohibidos_legacy(adjudicacion)
            salida.append(rama)
        ramas[ca] = salida
    return ramas


def _ficha_pdp7_v0_4(
    fila: dict[str, Any],
    caso: CS4.CasoCanonico,
    ramas: list[dict[str, Any]],
    adjudicacion: dict[str, Any] | None,
    consulta: str,
    ambito: str,
    t_obj: str,
) -> dict[str, Any]:
    ident = caso.identificador
    asignaciones = CS4.asignaciones_canonicas_por_ca().get(ident, {})
    familias = sorted(set(fila["fam"]) | set(asignaciones.get("familias", [])))
    modos = sorted({fila["modo"]} | {r["modo"] for r in ramas})
    resultado = adjudicacion["resultado_esperado"] if adjudicacion else fila["eleg"]
    prohibidos = _prohibidos_legacy(adjudicacion) if adjudicacion else fila["prohib"]
    return {
        "id_y_familia": _derivado(
            {"id": ident, "familias": familias},
            "el canon fija el ID; la familia procede del Anexo B y de la instanciación",
            S4.FUENTE_PDP7,
        ),
        "objetivo": _derivado(
            f"Demostrar o romper: {caso.resultado_esperado}",
            "derivado del resultado esperado canónico; el canon no redacta objetivos de prueba",
            caso.seccion,
        ),
        "entrada": _campo(
            caso.entrada,
            S4.FUENTE_CANONICA_CA,
            caso.seccion,
            "CANONICO",
            "columna «Entrada» del propio caso, carácter a carácter",
        ),
        "unidad_de_trabajo": _derivado(
            {
                "objetivo": f"Adjudicar {ident} sobre el corpus de conformidad congelable.",
                "inicio": "alta de la petición de recuperación instanciada",
                "cierre": "adjudicación registrada de todas las ramas del caso",
            },
            "unidad declarada por el arnés; el canon no la fija para este caso",
            S4.FUENTE_PDP7,
        ),
        "operacion_y_modo": _operacion_y_modo(caso, modos),
        "ambito": _derivado(
            sorted({ambito} | {r["ambito"] for r in ramas if r["ambito"]}),
            "ámbito sintético del corpus; el canon no nombra proyectos",
        ),
        "tiempo_y_corte": _derivado(
            {
                "tiempo_objetivo": t_obj,
                "corte_registro": fila["corte"],
                "por_rama": [
                    {
                        "rama": r["sufijo"],
                        "tiempo_objetivo": r["tiempo_objetivo"],
                        "corte_registro": r["corte_registro"],
                    }
                    for r in ramas
                ],
            },
            "fechas sintéticas declaradas; nunca el reloj de ejecución",
        ),
        "referencia": _derivado(
            {
                "tipo_referencia": S4.TIPO_REFERENCIA_RECUPERACION,
                "resultado_esperado_canonico": caso.resultado_esperado,
                "resultado_esperado": resultado,
                "pendientes_por_limite": (
                    adjudicacion["pendientes_por_limite"] if adjudicacion else []
                ),
                "prohibidos": prohibidos,
                "orden": fila["orden"],
            },
            "el esperado es canónico; los conjuntos proceden de la adjudicación calculada",
        ),
        "criticidad": _derivado(
            fila["crit"], "adjudicación de prueba del corpus; B04 §6 cuarto origen de criticidad"
        ),
        "tolerancias": B3._tolerancias_del_caso(ident),
        "senales_observables": _derivado(
            [
                "conjunto de ids elegibles devueltos",
                "ids prohibidos que aparecieron",
                "pendientes por límite declarados sin revelar contenido",
                "estado interno de suficiencia adjudicado",
                "estado externo emitido",
                "modo adjudicado y puertas aplicadas",
                "etapas recorridas y parada",
                "razón por resultado y razón de orden",
            ],
            "señales que el arnés puede observar sin revelar contenido protegido",
        ),
        "fallo": _campo(
            caso.fallo_observable,
            S4.FUENTE_CANONICA_CA,
            caso.seccion,
            "CANONICO",
            "columna «Fallo observable» del propio caso, carácter a carácter",
        ),
        "evidencia": _derivado(
            "Registro por rama: petición efectiva, plan, puertas, etapas, parada, suficiencia, "
            "resultado obtenido y esperado, veredicto y razón. No altera la referencia.",
            "el PDP §7 exige evidencia posterior sin alterar la referencia; el contenido lo "
            "aporta el arnés",
        ),
        "resultado": _derivado(
            None, "se rellena tras adjudicar; hoy no hay ninguna ejecución", S4.FUENTE_PDP7
        ),
        S4.CAMPO_INSUFICIENCIA: _derivado(
            _condicion_insuficiencia(ident, fila["etapa"], ramas),
            "Especificación de benchmark §5 campo 12: condición que autoriza cada transición, "
            "derivada del modo y la etapa reales de cada rama",
        ),
    }


def _caso_nivel1(
    fila: dict[str, Any],
    canon: CS4.Canon,
    corpus: dict[str, Any],
    ramas_por_ca: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    ident = fila["ca"]
    caso = canon.casos[ident]
    numero = int(ident.rsplit("-", 1)[1])
    ramas = ramas_por_ca.get(ident, [])
    consulta = CONSULTAS_V0_4.get(ident, fila["consulta"])
    ambito = AMBITOS_V0_4.get(ident, fila["ambito"])
    t_obj = TIEMPOS_V0_4.get(ident, fila["t_obj"])
    sin_vocabulario = ident in B2.CA_SIN_VOCABULARIO_DE_PARADA
    cardinalidad = None if sin_vocabulario else fila["card"]
    parada = None if sin_vocabulario else fila["parada"]

    dominio = DOMINIOS.get(ident)
    adjudicacion: dict[str, Any] | None = None
    if dominio is not None:
        adjudicacion = adjudicar(
            corpus, dominio, JUSTIFICACIONES.get(ident, f"cierre calculado del dominio de {ident}")
        )
        esperado = ESPERADOS[ident]
        if "resultado" in esperado and adjudicacion["resultado_esperado"] != sorted(
            esperado["resultado"]
        ):
            raise S4.ContratoCorpusV04Error(
                f"{ident}: cierre calculado {adjudicacion['resultado_esperado']} != esperado "
                f"{sorted(esperado['resultado'])}"
            )
        if "pendientes" in esperado and adjudicacion["pendientes_por_limite"] != sorted(
            esperado["pendientes"]
        ):
            raise S4.ContratoCorpusV04Error(
                f"{ident}: pendientes {adjudicacion['pendientes_por_limite']} != "
                f"{sorted(esperado['pendientes'])}"
            )
        if "resultado_n" in esperado:
            criticos = {
                i["id"]
                for i in corpus["items"]
                if i["criticidad"] and i["criticidad"]["nivel"] == "CRITICO"
            }
            en_resultado = len(set(adjudicacion["resultado_esperado"]) & criticos)
            if (
                len(adjudicacion["resultado_esperado"]) != esperado["resultado_n"]
                or en_resultado != esperado["criticos_en_resultado"]
                or len(adjudicacion["pendientes_por_limite"]) != esperado["pendientes_n"]
            ):
                raise S4.ContratoCorpusV04Error(
                    f"{ident}: {len(adjudicacion['resultado_esperado'])} devueltos "
                    f"({en_resultado} críticos) y {len(adjudicacion['pendientes_por_limite'])} "
                    f"pendientes no cumplen la premisa {esperado}"
                )
        if (
            cardinalidad == "EXHAUSTIVA"
            and adjudicacion["resultado_esperado"] != adjudicacion["elegibles_semanticos"]
        ):
            raise S4.ContratoCorpusV04Error(f"{ident}: EXHAUSTIVA sin cierre exacto")

    ramas_adjudicadas = [r for r in ramas if r.get("adjudicacion")]
    if adjudicacion:
        elegibles = adjudicacion["resultado_esperado"]
        prohibidos = _prohibidos_legacy(adjudicacion)
    elif ramas_adjudicadas:
        union_eleg = {x for r in ramas_adjudicadas for x in r["candidatos_elegibles"]}
        union_prohib = {x for r in ramas_adjudicadas for x in r["candidatos_prohibidos"]}
        elegibles = sorted(union_eleg)
        prohibidos = sorted(union_prohib - union_eleg)
    else:
        elegibles = list(fila["eleg"])
        prohibidos = list(fila["prohib"])
    orden = fila["orden"]
    if (adjudicacion or ramas_adjudicadas) and orden is not None and sorted(orden) != elegibles:
        orden = (adjudicacion or {}).get("resultado_en_orden_de_desempate") or None

    if adjudicacion or ramas_adjudicadas:
        # Los datos del caso son exactamente lo que la adjudicación considera.
        datos_set: set[str] = set()
        if adjudicacion:
            datos_set |= set(adjudicacion["candidatos_considerados"])
            datos_set |= {d["id"] for d in adjudicacion["decoys_fuera_de_ambito"]}
        for r in ramas_adjudicadas:
            datos_set |= set(r["adjudicacion"]["candidatos_considerados"])
            datos_set |= {d["id"] for d in r["adjudicacion"]["decoys_fuera_de_ambito"]}
        datos = sorted(datos_set)
    else:
        datos = sorted(fila["datos"])

    caso_v4 = {
        "id": f"N1-{numero:02d}",
        "nivel": 1,
        "clase": "CASO_FUNCIONAL",
        "identificador_canonico": ident,
        "canonico": {
            "fuente": S4.FUENTE_CANONICA_CA,
            "seccion_exacta": caso.seccion,
            "riesgo": caso.riesgo,
            "entrada": caso.entrada,
            "resultado_esperado": caso.resultado_esperado,
            "fallo_observable": caso.fallo_observable,
            "modificable": False,
        },
        "instanciacion": {
            "fuente": S4.FUENTE_INSTANCIACION,
            "estado": S4.ESTADO_NO_CONGELADO,
            "consulta": _derivado(consulta, "consulta sintética instanciada"),
            "modo": _canonico_si_literal(
                fila["modo"], caso, _RX_MODO, "modo elegido por la instanciación"
            ),
            "proposito": _derivado(fila["proposito"], "propósito autorizado del arnés"),
            "permiso": _derivado(fila["permiso"], "permiso declarado por el arnés"),
            "ambito": _derivado(ambito, "ámbito sintético del corpus"),
            "tiempo_objetivo": _derivado(t_obj, "fecha declarada, no el reloj"),
            "corte_registro": _derivado(fila["corte"], "fecha declarada, no el reloj"),
            "cardinalidad": _canonico_si_literal(
                cardinalidad,
                caso,
                None,
                "elección de instanciación; la regla canónica aplicable es B04 §15.2: si la "
                "instanciación es EXHAUSTIVA, S1 está prohibida",
            ),
            "etapa": _canonico_si_literal(
                fila["etapa"], caso, _RX_ETAPA, "etapa elegida por la instanciación"
            ),
            "parada": _canonico_si_literal(
                parada, caso, _RX_PARADA, "parada elegida por la instanciación"
            ),
            "orden": _derivado(
                {"valor": orden, "tipo": B3._tipo_orden(orden)},
                "ids sintéticos; el canon no fija secuencia",
            ),
            "elegibles": _derivado(elegibles, "resultado esperado de la adjudicación calculada"),
            "prohibidos": _derivado(
                prohibidos,
                "excluidos por estado, prohibidos por puerta y decoys: su aparición es fallo",
            ),
            "explicacion_esperada": _derivado(
                fila["expl"], "explicación mínima exigida por B04-RF-28"
            ),
            "ramas": ramas,
        },
        "trazabilidad": B3._trazabilidad(fila, ident),
        "t0": dict(B3.T0_NO_MEDIDO) | {"prevision_en": "t0_preexecution_projection_v0_2.json"},
        "datos_sinteticos": datos,
        "corpus": "conformidad",
        "evidencia_minima": B3.EVIDENCIA_MINIMA,
    }
    if adjudicacion is not None:
        caso_v4["adjudicacion"] = adjudicacion
    elif ident == "B04-CA-39":
        caso_v4["adjudicacion"] = {
            "estado": "NO_APLICA",
            "justificacion": (
                "arnés de equivalencia entre dos realizaciones: sus conjuntos son la muestra "
                "compartida de entrada, no un resultado de recuperación adjudicable"
            ),
        }
    elif ramas:
        caso_v4["adjudicacion"] = {
            "estado": "VER_RAMAS",
            "justificacion": "la adjudicación vive en cada rama del caso",
        }
    caso_v4["ficha_pdp_7"] = _ficha_pdp7_v0_4(
        fila, caso, ramas, adjudicacion, consulta, ambito, t_obj
    )
    return caso_v4


# ===========================================================================
# 5. PDP-CA funcionales · recuento de independencia, no recuperación
# ===========================================================================

REGISTROS_RECUENTO: dict[str, dict[str, Any]] = {
    "PDP-CA-09": {
        "regla": (
            "Dos consumidores que comparten una dependencia específica cuentan como uno, "
            "no como dos independientes."
        ),
        "consumidores": [
            {"id": "CONS-A", "dependencias": ["dependencia-comun-especifica"]},
            {"id": "CONS-B", "dependencias": ["dependencia-comun-especifica"]},
            {"id": "CONS-C", "dependencias": ["dependencia-propia"]},
        ],
        "pares_no_independientes": [["CONS-A", "CONS-B"]],
        "recuento_esperado_independientes": 2,
        "fallo_falsable": (
            "Una adjudicación que cuente CONS-A y CONS-B como dos consumidores "
            "independientes suspende el caso."
        ),
    },
    "PDP-CA-22": {
        "regla": (
            "Dos consumidores con el mismo intérprete y distinta configuración cuentan como "
            "un solo consumidor."
        ),
        "consumidores": [
            {"id": "CONS-D", "interprete": "interprete-uno", "configuracion": "config-a"},
            {"id": "CONS-E", "interprete": "interprete-uno", "configuracion": "config-b"},
            {"id": "CONS-F", "interprete": "interprete-dos", "configuracion": "config-a"},
        ],
        "pares_no_independientes": [["CONS-D", "CONS-E"]],
        "recuento_esperado_independientes": 2,
        "fallo_falsable": (
            "Una adjudicación que cuente CONS-D y CONS-E como dos consumidores "
            "independientes suspende el caso; la portabilidad no queda demostrada."
        ),
    },
}


def _no_aplica_recuperacion(justificacion: str) -> dict[str, Any]:
    return _derivado(None, f"NO_APLICA: {justificacion}")


def _caso_pdp_funcional(
    pdp: str, orden: int, canon: CS4.Canon, anclaje: dict[str, list[str]]
) -> dict[str, Any]:
    caso = canon.casos_pdp[pdp]
    registro = REGISTROS_RECUENTO[pdp]
    razon = "el caso adjudica un recuento de independencia, no una consulta de recuperación"
    referencia = {
        "tipo_referencia": S4.TIPO_REFERENCIA_RECUENTO,
        "resultado_esperado_canonico": caso.resultado_esperado,
        "regla_de_recuento": registro["regla"],
        "registros_sinteticos_de_consumidores": registro["consumidores"],
        "pares_no_independientes": registro["pares_no_independientes"],
        "recuento_esperado_independientes": registro["recuento_esperado_independientes"],
        "fallo_falsable": registro["fallo_falsable"],
    }
    ficha = {
        "id_y_familia": _derivado(
            {"id": pdp, "familias": anclaje["familias"]},
            "el ID es canónico; la familia procede del Anexo B",
            S4.FUENTE_PDP7,
        ),
        "objetivo": _derivado(
            f"Demostrar o romper: {caso.resultado_esperado}",
            "derivado del resultado esperado canónico",
            S4.FUENTE_PDP9,
        ),
        "entrada": _campo(
            caso.entrada_adversarial,
            S4.FUENTE_PDP9,
            "PDP §9",
            "CANONICO",
            "columna «Entrada adversarial» del propio caso, carácter a carácter",
        ),
        "unidad_de_trabajo": _derivado(
            {
                "objetivo": f"Adjudicar {pdp} sobre el registro sintético de consumidores.",
                "inicio": "declaración del inventario de consumidores",
                "cierre": "adjudicación registrada del recuento de consumidores independientes",
            },
            "unidad declarada por el arnés",
            S4.FUENTE_PDP7,
        ),
        "operacion_y_modo": _derivado(
            {
                "operacion": {"valor": "adjudicacion_de_recuento", "estado": "DERIVADO_PROPUESTO"},
                "modos": [],
            },
            razon,
        ),
        "ambito": _derivado(
            ["REGISTRO_DE_EJECUCION"], "adjudica sobre el registro del arnés, no sobre el corpus"
        ),
        "tiempo_y_corte": _derivado(
            {"tiempo_objetivo": _AHORA, "corte_registro": None, "por_rama": []},
            "fecha declarada, no el reloj",
        ),
        "referencia": _derivado(
            referencia, "referencia de recuento falsable sobre registros sintéticos declarados"
        ),
        "criticidad": _derivado("CRITICO", "adjudicación de prueba del arnés"),
        "tolerancias": B3._tolerancias_del_caso("B04-CA-39"),
        "senales_observables": _derivado(
            [
                "inventario de dependencias de cada consumidor",
                "intérprete, versión y configuración de cada consumidor",
                "recuento de consumidores declarados independientes",
            ],
            "señales del registro de ejecución del arnés",
        ),
        "fallo": _campo(
            caso.resultado_esperado,
            S4.FUENTE_PDP9,
            "PDP §9",
            "CANONICO",
            "el resultado esperado canónico define el fallo por negación",
        ),
        "evidencia": _derivado(
            "Inventario de dependencias, intérprete, versión y configuración de cada consumidor.",
            "el PDP §7 exige evidencia posterior sin alterar la referencia",
        ),
        "resultado": _derivado(
            None, "se rellena tras adjudicar; hoy no hay ninguna ejecución", S4.FUENTE_PDP7
        ),
        S4.CAMPO_INSUFICIENCIA: _derivado(
            [
                {
                    "rama": "CASO_BASE",
                    "aplica": "NO_APLICA",
                    "razon": (
                        "el recuento de independencia no recorre la escalera E0-E5: no hay "
                        "expansión que autorizar"
                    ),
                }
            ],
            "Especificación de benchmark §5 campo 12",
        ),
    }
    return {
        "id": f"N1-PDP-{orden:02d}",
        "nivel": 1,
        "clase": "CASO_FUNCIONAL",
        "identificador_canonico": pdp,
        "canonico": {
            "fuente": S4.FUENTE_PDP9,
            "seccion_exacta": "PDP §9",
            "entrada_adversarial": caso.entrada_adversarial,
            "resultado_esperado": caso.resultado_esperado,
            "modificable": False,
        },
        "anclaje_canonico": {
            "criterio": "ANEXO_B_RED_CON_CASO_O_METRICA_DE_B04",
            "red": anclaje["red"],
            "casos_b04": anclaje["casos_b04"],
            "metricas_b04": anclaje["metricas"],
            "metricas_externas": anclaje["metricas_externas"],
            "familias": anclaje["familias"],
        },
        "instanciacion": {
            "fuente": S4.FUENTE_INSTANCIACION,
            "estado": S4.ESTADO_NO_CONGELADO,
            "consulta": _no_aplica_recuperacion(razon),
            "modo": _no_aplica_recuperacion(razon),
            "proposito": _derivado("adjudicar_disciplina_del_arnes", "propósito del arnés"),
            "permiso": _derivado("AUTORIZADO", "permiso declarado por el arnés"),
            "ambito": _derivado("REGISTRO_DE_EJECUCION", "adjudica sobre el registro del arnés"),
            "tiempo_objetivo": _derivado(_AHORA, "fecha declarada, no el reloj"),
            "corte_registro": _derivado(None, "el caso no declara corte de registro"),
            "cardinalidad": _no_aplica_recuperacion(razon),
            "etapa": _no_aplica_recuperacion(razon),
            "parada": _no_aplica_recuperacion(razon),
            "orden": _no_aplica_recuperacion(razon),
            "elegibles": _no_aplica_recuperacion(razon),
            "prohibidos": _no_aplica_recuperacion(razon),
            "explicacion_esperada": _derivado(
                "por qué cada consumidor cuenta o no cuenta como independiente",
                "explicación mínima exigida por B04-RF-28",
            ),
            "ramas": [],
        },
        "ficha_pdp_7": ficha,
        "t0": dict(B3.T0_NO_MEDIDO) | {"prevision_en": "t0_preexecution_projection_v0_2.json"},
        "corpus": "conformidad",
        "evidencia_minima": B3.EVIDENCIA_MINIMA,
    }


# ===========================================================================
# 6. Corpus, casos, referencias y artefactos v0.4
# ===========================================================================


def construir_corpus_conformidad(canon: CS4.Canon) -> dict[str, Any]:
    base = V1.construir_corpus()
    items = construir_items_v0_4()
    memorias = [i for i in items if i["kind"] == "MEMORIA"]
    decisiones = [i for i in items if i["kind"] == "DECISION"]
    corpus: dict[str, Any] = {
        "documento": "Corpus de CONFORMIDAD del benchmark de ADR-002",
        "proposito": (
            "Adjudicar puertas, exactitud, contaminación, negación, ámbito, tiempo, conflicto, "
            "ausencia y explicación. NO se usa para fijar cifras de rendimiento absoluto."
        ),
        "version": S4.VERSION_CORPUS_CONFORMIDAD,
        "version_contrato": S4.VERSION_CONTRATO,
        "estado": S4.ESTADO_NO_CONGELADO,
        "semilla": S4.SEMILLA,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_4.py",
        "hereda_de": "conformance_corpus_v0_3.json",
        "fuente_canonica": {n: h["sha256_real"] for n, h in sorted(canon.huellas.items())},
        "datos_reales": "ninguno; corpus sintético determinista",
        "red": "no utilizada",
        "ahora_declarado": S4.AHORA_DECLARADO,
        "cambios_v0_4": {
            "traslado_critico": {
                "items": sorted(S4.CRITICOS_GAMMA_V0_4),
                "a_proyecto": "PRJ-GAMMA",
                "tiempo_valido_escalonado": dict(sorted(S4.FECHAS_CRITICOS_GAMMA.items())),
                "motivo": (
                    "Reconciliar las premisas numéricas canónicas: cinco críticos en ALFA "
                    "(CA-31) y 6/11/12 vigentes en Gamma en el instante objetivo de "
                    "CA-44/CA-26/CA-38. Ámbito y tiempo válido son dimensiones duras que el "
                    "canon ya gobierna."
                ),
            },
            "anclaje_anadido": {
                "item": "DEC-016",
                "motivo": (
                    "Hacer verdadera la premisa SOLO_HISTORICO de la rama R1 de B04-CA-36: "
                    "una decisión expirada sin sucesor en el ámbito consultado."
                ),
            },
        },
        "cierre_exhaustivo_ca47": B3.cierre_ca47(items),
        "colisiones_por_raiz_declaradas": B3.colisiones_por_raiz_entre_anclajes(items),
        "conteos": {
            "proyectos": len(base["proyectos"]),
            "entidades": len(base["entidades"]),
            "items": len(items),
            "recuerdos": len(memorias),
            "decisiones": len(decisiones),
            "mensajes": len(base["mensajes"]),
            "documentos": len(base["documentos"]),
            "relaciones": len(base["relaciones"]),
        },
        "proyectos": base["proyectos"],
        "entidades": base["entidades"],
        "items": items,
        "mensajes": base["mensajes"],
        "documentos": base["documentos"],
        "relaciones": base["relaciones"],
    }
    corpus["identidad"] = B3.identidad_de_colecciones(corpus)
    return corpus


def barrido_impacto_dec016(corpus: dict[str, Any]) -> dict[str, Any]:
    """Recalcula todas las adjudicaciones sin DEC-016: solo CA-36-R1 puede cambiar."""
    sin = copy.deepcopy(corpus)
    sin["items"] = [i for i in sin["items"] if i["id"] != "DEC-016"]
    cambios: list[str] = []
    for ident, dominio in sorted(DOMINIOS.items()):
        con_016 = evaluar_universo(corpus, dominio)
        sin_016 = evaluar_universo(sin, dominio)
        if con_016 != sin_016:
            cambios.append(ident)
    for (ca, sufijo), dominio in sorted(DOMINIOS_RAMA.items()):
        con_016 = evaluar_universo(corpus, dominio)
        sin_016 = evaluar_universo(sin, dominio)
        if con_016 != sin_016:
            cambios.append(f"{ca}/{sufijo}")
    if cambios != ["B04-CA-36/R1"]:
        raise S4.ContratoCorpusV04Error(
            f"el barrido de impacto de DEC-016 detectó cambios fuera de CA-36-R1: {cambios}"
        )
    return {
        "adjudicaciones_recalculadas": len(DOMINIOS) + len(DOMINIOS_RAMA),
        "cambios": cambios,
        "regla": "solo la rama R1 de B04-CA-36 puede cambiar al añadir DEC-016",
    }


def construir_casos(canon: CS4.Canon, corpus: dict[str, Any]) -> dict[str, Any]:
    ramas_por_ca = _ramas_v0_4(corpus)
    nivel1 = [_caso_nivel1(fila, canon, corpus, ramas_por_ca) for fila in V1.CA]
    anclajes = CS4.asignaciones_canonicas_por_pdp_ca()
    nivel1_pdp = [
        _caso_pdp_funcional(pdp, orden, canon, anclajes[pdp])
        for orden, pdp in enumerate(S4.PDP_CA_FUNCIONALES, start=1)
    ]
    return {
        "documento": "Casos del benchmark de ADR-002",
        "version": S4.VERSION_CONTRATO,
        "estado": S4.ESTADO_NO_CONGELADO,
        "hereda_de": "cases_v0_3.json",
        "regla_de_separacion": (
            "Tres capas: el bloque `canonico` procede literalmente de las fuentes DOCX y no se "
            "reescribe; el bloque `instanciacion` declara las decisiones sintéticas con fuente, "
            "sección, estado y justificación campo a campo; el bloque `adjudicacion` calcula "
            "candidatos, elegibles, resultado, pendientes, exclusiones y prohibiciones desde un "
            "dominio declarado. Ningún conjunto esperado se escribe a mano."
        ),
        "modelo_de_adjudicacion": {
            "candidatos_considerados": "se calculan desde el dominio y la consulta",
            "elegibles_semanticos": (
                "todos los que cumplen las reglas, aunque un límite impida devolverlos"
            ),
            "resultado_esperado": "lo que debe devolver el caso",
            "pendientes_por_limite": "elegibles no devueltos por cardinalidad ACOTADA",
            "invariantes": [
                "EXHAUSTIVA: resultado_esperado == elegibles_semanticos",
                "ACOTADA: la unión de resultado y pendientes es exactamente elegibles, disjuntos",
                "un pendiente por límite nunca aparece como prohibido",
                "prohibidos_entre_candidatos incumplen una puerta declarada",
                "decoys_fuera_de_ambito no forman parte del complemento interno",
            ],
        },
        "niveles": {
            "1": (
                "Casos canónicos reutilizados: B04-CA-01-50 y los PDP-CA anclados por el "
                "Anexo B. El benchmark los ejecuta, no los reescribe."
            ),
            "2": "Casos arquitectónicos nuevos. Solo cuando ningún caso canónico los cubre.",
            "3": (
                "Ablaciones técnicas. Instrumentos de medida; nunca producen veredicto de "
                "conformidad, y por eso no llevan ficha de caso del PDP §7."
            ),
        },
        "conteos": {
            "nivel_1_b04": len(nivel1),
            "nivel_1_pdp": len(nivel1_pdp),
            "nivel_2": len(V1.NIVEL2),
            "nivel_3": len(V1.NIVEL3),
            "ramas_canonicas": sum(len(c["instanciacion"]["ramas"]) for c in nivel1),
            "casos_con_adjudicacion_calculada": sum(
                1 for c in nivel1 if c.get("adjudicacion", {}).get("dominio")
            ),
            "ramas_con_adjudicacion_calculada": sum(
                1 for c in nivel1 for r in c["instanciacion"]["ramas"] if r.get("adjudicacion")
            ),
        },
        "nivel_1": nivel1,
        "nivel_1_pdp": nivel1_pdp,
        "nivel_2": [B3._sin_veredicto_t0(c) for c in V1.NIVEL2],
        "nivel_3": [B3._sin_veredicto_t0(c) for c in V1.NIVEL3],
    }


def construir_referencias(casos: dict[str, Any]) -> dict[str, Any]:
    refs: list[dict[str, Any]] = []
    for caso in casos["nivel_1"]:
        inst = caso["instanciacion"]
        refs.append(
            {
                "caso": caso["id"],
                "identificador_canonico": caso["identificador_canonico"],
                "tipo_referencia": S4.TIPO_REFERENCIA_RECUPERACION,
                "canonico": {
                    "fuente": S4.FUENTE_CANONICA_CA,
                    "seccion_exacta": caso["canonico"]["seccion_exacta"],
                    "riesgo": caso["canonico"]["riesgo"],
                    "entrada": caso["canonico"]["entrada"],
                    "resultado_esperado": caso["canonico"]["resultado_esperado"],
                    "fallo_observable": caso["canonico"]["fallo_observable"],
                    "modificable": False,
                },
                "instanciacion": {
                    "fuente": S4.FUENTE_INSTANCIACION,
                    "estado": S4.ESTADO_NO_CONGELADO,
                    "modificable": True,
                    "cardinalidad": inst["cardinalidad"]["valor"],
                    "etapa": inst["etapa"]["valor"],
                    "parada": inst["parada"]["valor"],
                    "orden": inst["orden"]["valor"]["valor"],
                    "tipo_orden": inst["orden"]["valor"]["tipo"],
                    "elegibles": inst["elegibles"]["valor"],
                    "prohibidos": inst["prohibidos"]["valor"],
                    "ramas": [
                        {
                            "sufijo": r["sufijo"],
                            "clase": r["clase"],
                            "modo": r["modo"],
                            "etapa_de_la_rama": r["etapa_de_la_rama"],
                            "cardinalidad_de_la_rama": r.get("cardinalidad_de_la_rama"),
                            "elegibles": r["candidatos_elegibles"],
                            "prohibidos": r["candidatos_prohibidos"],
                            "estado_suficiencia_esperado": r["estado_suficiencia_esperado"],
                            "tolerancia_pendiente": r["tolerancia_pendiente"],
                            "adjudicacion": r.get("adjudicacion"),
                        }
                        for r in inst["ramas"]
                    ],
                    "fuente_por_campo": {
                        campo: {
                            "fuente": inst[campo]["fuente"],
                            "seccion": inst[campo]["seccion"],
                            "estado": inst[campo]["estado"],
                        }
                        for campo in S4.CAMPOS_INSTANCIACION
                    },
                },
                "adjudicacion": caso.get("adjudicacion"),
                "tolerancias": caso["ficha_pdp_7"]["tolerancias"]["valor"],
                "t0": {"estado_t0": S4.ESTADO_T0},
            }
        )
    for caso in casos["nivel_1_pdp"]:
        refs.append(
            {
                "caso": caso["id"],
                "identificador_canonico": caso["identificador_canonico"],
                "tipo_referencia": S4.TIPO_REFERENCIA_RECUENTO,
                "canonico": dict(caso["canonico"]),
                "referencia_de_recuento": caso["ficha_pdp_7"]["referencia"]["valor"],
                "tolerancias": caso["ficha_pdp_7"]["tolerancias"]["valor"],
                "t0": {"estado_t0": S4.ESTADO_T0},
            }
        )
    return {
        "documento": "Referencias del benchmark de ADR-002",
        "version": S4.VERSION_CONTRATO,
        "estado": S4.ESTADO_NO_CONGELADO,
        "hereda_de": "references_v0_3.json",
        "regla": (
            "El bloque `canonico` no cambia nunca. Cincuenta referencias son de recuperación "
            "B04 con adjudicación calculada; dos son de recuento de independencia de "
            "consumidores (PDP-CA-09 y PDP-CA-22) y no fingen ser referencias de "
            "recuperación. Ninguna contiene previsión sobre T0: solo el estado NO_MEDIDO."
        ),
        "conteos": {
            "referencias_totales": len(refs),
            "referencias_recuperacion_b04": sum(
                1 for r in refs if r["tipo_referencia"] == S4.TIPO_REFERENCIA_RECUPERACION
            ),
            "referencias_recuento_pdp": sum(
                1 for r in refs if r["tipo_referencia"] == S4.TIPO_REFERENCIA_RECUENTO
            ),
        },
        "referencias_nivel_1": refs,
    }


def construir_casos_pdp(canon: CS4.Canon) -> dict[str, Any]:
    base = B3.construir_casos_pdp(canon)
    base = copy.deepcopy(base)
    base["version"] = "0.3"
    base["version_contrato"] = S4.VERSION_CONTRATO
    base["hereda_de"] = "pdp_cases_v0_2.json"
    for datos in base["casos_fuera_de_alcance"].values():
        if not datos["red_que_lo_asigna"]:
            datos["motivo"] = "Ninguna fila RED del Anexo B asigna este PDP-CA."
        if "ADR-002" in datos["responsable"]:
            datos["nota_responsable"] = (
                "El responsable procede del destino de FAMILIA en ARQ-00 §20 "
                "(responsable_de_familia); no equivale a ejecutor_del_caso. Este PDP-CA "
                "queda fuera del alcance ejecutado por ADR-002."
            )
    return base


def construir_reglas_de_arnes(canon: CS4.Canon) -> dict[str, Any]:
    base = copy.deepcopy(B3.construir_reglas_de_arnes(canon))
    base["version"] = "0.2"
    base["version_contrato"] = S4.VERSION_CONTRATO
    base["hereda_de"] = "pdp_harness_rules_v0_1.json"
    base["estados_de_fuente"] = list(S4.ESTADOS_FUENTE_REGLA)
    for regla in base["reglas"]:
        estado, justificacion = S4.ESTADO_FUENTE_POR_REGLA[regla["identificador_canonico"]]
        regla["estado_de_la_fuente"] = estado
        regla["justificacion_estado_fuente"] = justificacion
    return base


def construir_proyeccion_t0(casos: dict[str, Any]) -> dict[str, Any]:
    proyeccion = B3.construir_proyeccion_t0(casos)
    proyeccion = copy.deepcopy(proyeccion)
    proyeccion["version"] = "0.2"
    proyeccion["version_contrato"] = S4.VERSION_CONTRATO
    proyeccion["hereda_de"] = "t0_preexecution_projection_v0_1.json"
    proyeccion["congelables_excluidos"] = {
        "regla": (
            "Este fichero NO pertenece a CONGELABLES_V0_4. Es no normativo, no congelable y "
            "se sustituye íntegramente por la ejecución real de T0."
        ),
        "congelables": list(S4.CONGELABLES_V0_4),
    }
    return proyeccion


def construir_manifiesto(
    canon: CS4.Canon,
    conformidad: dict[str, Any],
    casos: dict[str, Any],
    referencias: dict[str, Any],
    pdp: dict[str, Any],
    reglas: dict[str, Any],
    proyeccion: dict[str, Any],
    barrido: dict[str, Any],
) -> dict[str, Any]:
    sha_rendimiento = hashlib.sha256(
        (AQUI / "performance_corpus_v0_2.json").read_bytes()
    ).hexdigest()
    if sha_rendimiento != S4.SHA256_PERFORMANCE_V0_2:
        raise S4.ContratoCorpusV04Error(
            "performance_corpus_v0_2.json fue alterado: su huella no coincide con la congelada"
        )
    return {
        "documento": "Manifiesto del benchmark de ADR-002",
        "version_contrato": S4.VERSION_CONTRATO,
        "estado": S4.ESTADO_NO_CONGELADO,
        "semilla_compartida": S4.SEMILLA,
        "advertencia": (
            "Ninguna puerta de arranque queda satisfecha por este manifiesto. "
            "ADR002-TOL-207 no está aprobada; TOL-208, TOL-209 y TOL-210 siguen NO SATISFECHAS. "
            "T0 no se ha ejecutado y ADR002-A/B/C/D no se han implementado ni ejecutado. "
            "Después de este paquete NO se congela nada: la familia v0.4 queda sometida a "
            "una nueva auditoría independiente."
        ),
        "fuentes_canonicas": canon.huellas,
        "medidas_del_canon": canon.medidas(),
        "tablas_canonicas": CS4.inventario_de_tablas(),
        "censo_de_cabeceras": CS4.censo_de_cabeceras(),
        "metricas_del_anexo_b": CS4.metricas_del_anexo_b(),
        "congelables": {
            "lista": list(S4.CONGELABLES_V0_4),
            "no_congelables": list(S4.NO_CONGELABLES_V0_4),
            "regla": (
                "La proyección T0 no forma parte de los congelables. Ningún congelable puede "
                "contener previsiones sobre T0: solo estado_t0 = NO_MEDIDO y la referencia "
                "externa al fichero no normativo."
            ),
        },
        "corpus_rendimiento": {
            "fichero": "performance_corpus_v0_2.json",
            "sha256": sha_rendimiento,
            "regla": "byte a byte idéntico al commit 079ba763; cualquier alteración falla",
            "alcance_de_medida": {
                "mide": list(S4.ALCANCE_RENDIMIENTO["mide"]),
                "no_mide": list(S4.ALCANCE_RENDIMIENTO["no_mide"]),
                "motivo": S4.ALCANCE_RENDIMIENTO["motivo"],
            },
            "guardas": {
                "nombre": S4.NOMBRE_GUARDAS,
                "regla": (
                    "Guardas del arnés, no canon. Las calcula un oráculo independiente del "
                    "generador; si el corpus congelado no cumpliera una, el fallo se informa "
                    "sin regenerar el corpus ni relajar la cota."
                ),
                "cotas": dict(S4.GUARDAS_RENDIMIENTO),
            },
        },
        "universo_critico": {
            "premisas": {k: dict(v) for k, v in S4.PREMISAS_CRITICAS.items()},
            "criticos_alfa": list(S4.CRITICOS_ALFA_V0_4),
            "criticos_gamma": list(S4.CRITICOS_GAMMA_V0_4),
            "tiempo_valido_escalonado": dict(sorted(S4.FECHAS_CRITICOS_GAMMA.items())),
        },
        "barrido_impacto_dec016": barrido,
        "artefactos": {
            "corpus_conformidad": {
                "fichero": "conformance_corpus_v0_4.json",
                "version": conformidad["version"],
                "conteos": conformidad["conteos"],
            },
            "casos": {"fichero": "cases_v0_4.json", "conteos": casos["conteos"]},
            "referencias": {"fichero": "references_v0_4.json", "conteos": referencias["conteos"]},
            "casos_pdp": {"fichero": "pdp_cases_v0_3.json", "conteos": pdp["conteos"]},
            "reglas_de_arnes": {
                "fichero": "pdp_harness_rules_v0_2.json",
                "conteos": reglas["conteos"],
            },
            "proyeccion_t0": {
                "fichero": "t0_preexecution_projection_v0_2.json",
                "estado": proyeccion["estado"],
                "normativo": proyeccion["normativo"],
                "congelable": proyeccion["congelable"],
                "conteos": proyeccion["conteos"],
            },
        },
        "artefactos_anteriores_conservados": [
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
            "cases_v0_3.json",
            "references_v0_3.json",
            "pdp_cases_v0_2.json",
            "pdp_harness_rules_v0_1.json",
            "t0_preexecution_projection_v0_1.json",
            "benchmark_manifest_v0_3.json",
        ],
        "hallazgos_cerrados_en_v0_4": {
            "BLOQ-01": "los 13 casos EXHAUSTIVA declaran dominio y cierre calculable",
            "BLOQ-02": "CA-22, CA-25 y CA-31 cierran sobre el corpus; CA-36-R1 re-anclada",
            "BLOQ-03": "universo crítico reconciliado: 5 en ALFA y 6/11/12 en GAMMA por t_obj",
            "MAT-01": "operacion_y_modo clasifica cada modo individualmente",
            "MAT-02": "censo global de cabeceras en el lector v0.4",
            "MAT-03/04": "guardas absolutas de neutralidad sintética con oráculo independiente",
            "MAT-05": "insuficiencia por etapa y modo de la rama; M3/M4 no heredan E0-E5",
            "MAT-06": "PDP-CA-09/22 con referencia de recuento falsable; 52 referencias",
            "MAT-08": "vocabulario cerrado de variables y prohibición de magnitudes pendientes",
            "M12": "escaneo anti-T0 sobre la lista explícita de congelables",
        },
        "documentado_no_corregido": {
            "validate_corpus_v0_2": (
                "el validador histórico v0.2 reescribe (determinísticamente) los artefactos "
                "v0.2 al ejecutarse; se documenta y no se corrige modificando v0.2. Orden de "
                "ejecución recomendado: validadores históricos antes de congelar huellas."
            )
        },
    }


# ===========================================================================
# 7. Volcado
# ===========================================================================


def _volcar(ruta: Path, datos: dict[str, Any]) -> int:
    texto = json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    ruta.write_text(texto, encoding="utf-8")
    return len(texto.encode("utf-8"))


def construir_todo() -> dict[str, dict[str, Any]]:
    canon = CS4.cargar_canon()
    conformidad = construir_corpus_conformidad(canon)
    barrido = barrido_impacto_dec016(conformidad)
    casos = construir_casos(canon, conformidad)
    referencias = construir_referencias(casos)
    pdp = construir_casos_pdp(canon)
    reglas = construir_reglas_de_arnes(canon)
    proyeccion = construir_proyeccion_t0(casos)
    manifiesto = construir_manifiesto(
        canon, conformidad, casos, referencias, pdp, reglas, proyeccion, barrido
    )
    return {
        "conformance_corpus_v0_4.json": conformidad,
        "cases_v0_4.json": casos,
        "references_v0_4.json": referencias,
        "pdp_cases_v0_3.json": pdp,
        "pdp_harness_rules_v0_2.json": reglas,
        "t0_preexecution_projection_v0_2.json": proyeccion,
        "benchmark_manifest_v0_4.json": manifiesto,
    }


def escribir_en(directorio: Path) -> dict[str, int]:
    """El validador regenera en un temporal: validar nunca escribe en el árbol."""
    directorio.mkdir(parents=True, exist_ok=True)
    return {n: _volcar(directorio / n, d) for n, d in construir_todo().items()}


def main() -> None:
    for nombre, tamano in escribir_en(AQUI).items():
        print(f"{nombre}: {tamano} bytes")


if __name__ == "__main__":
    main()
