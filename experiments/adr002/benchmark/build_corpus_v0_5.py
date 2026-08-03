"""Generador v0.5 · familia sucesora de conformidad de ADR-002.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.build_corpus_v0_5

Materializa **junto a** la familia v0.4 —que no toca— los siete artefactos que
el paso 1 del plan aprobado exige:

1. ``conformance_corpus_v0_5.json``  — v0.4 mas el delta relacional discriminante
2. ``subject_keys_v0_1.json``        — canal lateral de la proyeccion definitiva
3. ``property_keys_v0_1.json``       — canal lateral del predicado
4. ``applied_criticality_v0_1.json`` — plano comun seguro de criticidad
5. ``cases_v0_5.json``               — casos heredados mas el caso discriminante
6. ``references_v0_5.json``          — referencias heredadas mas la del delta
7. ``benchmark_manifest_v0_5.json``  — cierre de la familia completa

**El orden importa y es la prueba de anterioridad.** Las tres funciones de canal
lateral reciben por firma el corpus y **nada mas**: no pueden leer casos,
referencias ni adjudicaciones porque no los tienen. El caso se construye
despues, sobre datos ya cerrados.

No ejecuta T0, no implementa ni ejecuta ADR002-A/B/C/D, no mide rendimiento y
no autoriza ningun benchmark. El corpus de rendimiento no se toca.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import build_corpus as V1
from experiments.adr002.benchmark import build_corpus_v0_3 as B3
from experiments.adr002.benchmark import build_corpus_v0_4 as B4
from experiments.adr002.benchmark import canonical_source_v0_4 as CS4
from experiments.adr002.benchmark import schema_v0_5 as S5

AQUI = Path(__file__).resolve().parent

FICHEROS = S5.CONGELABLES_V0_5


def _huella(datos: Any) -> str:
    return hashlib.sha256(
        json.dumps(datos, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


# ===========================================================================
# 1. Delta relacional discriminante
# ===========================================================================


def _item_del_delta(ident: str, texto: str, entidad: str) -> dict[str, Any]:
    """Item sintetico del delta, con **todas** las dimensiones P2 declaradas.

    Sin dato real, sin etiqueta de candidato y sin criticidad: el discriminante
    pone a prueba el alcance relacional, no la criticidad ni las puertas de
    estado, y cargarlo con marcas ajenas enturbiaria lo que mide.
    """
    return V1._item(
        ident,
        "MEMORIA",
        S5.PROYECTO_DELTA,
        texto,
        entity_ids=[entidad],
        autoridad="DOCUMENTO_CANONICO",
        temporalidad=V1._temporalidad(valid_from=S5.INSTANTE_DELTA, recorded_at=S5.INSTANTE_DELTA),
    )


def construir_delta() -> dict[str, Any]:
    """Las cuatro piezas del delta: proyecto, entidades, items y relacion."""
    return {
        "proyecto": {
            "id": S5.PROYECTO_DELTA,
            "nombre": "Proyecto Delta relacional",
            "alias": [],
            "tipo": "PROYECTO",
            "miembros_lista_cerrada": [],
        },
        "entidades": [
            {
                "id": S5.ENTIDAD_ORIGEN_DELTA,
                "nombre_canonico": "rotor",
                "alias": [],
                "grupo_homonimo": None,
                "nota": "Sujeto sintetico del extremo origen del delta relacional.",
            },
            {
                "id": S5.ENTIDAD_DESTINO_DELTA,
                "nombre_canonico": "bitacora",
                "alias": [],
                "grupo_homonimo": None,
                "nota": "Sujeto sintetico del extremo destino del delta relacional.",
            },
        ],
        "items": [
            _item_del_delta(S5.ITEM_ORIGEN_DELTA, S5.TEXTO_ORIGEN_DELTA, S5.ENTIDAD_ORIGEN_DELTA),
            _item_del_delta(
                S5.ITEM_DESTINO_DELTA, S5.TEXTO_DESTINO_DELTA, S5.ENTIDAD_DESTINO_DELTA
            ),
        ],
        "relacion": {
            "id": S5.RELACION_DELTA,
            "tipo": S5.TIPO_RELACION_DELTA,
            "origen": S5.ITEM_ORIGEN_DELTA,
            "destino": S5.ITEM_DESTINO_DELTA,
            "nota": "Dependencia explicita, tipada y dirigida entre dos sujetos distintos.",
        },
    }


def terminos_indexados(textos: list[str]) -> set[str]:
    """Terminos que el indice **real** produce: FTS5, ``unicode61``, rd=1.

    La identidad efectiva del indice de Sirius 0.1 es la que la migracion
    ``61be4bb269bf`` deja: ``CREATE VIRTUAL TABLE knowledge_fts USING fts5(...)``
    **sin clausula tokenize**, luego el predeterminado ``unicode61`` con
    ``remove_diacritics 1``. Aqui se reproduce esa misma configuracion por
    omision y se leen los terminos con ``fts5vocab``: la condicion lexica del
    delta se **mide**, no se estima a ojo.
    """
    conexion = sqlite3.connect(":memory:")
    try:
        conexion.execute("CREATE VIRTUAL TABLE t USING fts5(content)")
        conexion.execute("CREATE VIRTUAL TABLE v USING fts5vocab(t, row)")
        conexion.executemany("INSERT INTO t(content) VALUES (?)", [(x,) for x in textos])
        return {str(fila[0]) for fila in conexion.execute("SELECT term FROM v")}
    finally:
        conexion.close()


def fallos_de_condicion_lexica(delta: dict[str, Any]) -> list[str]:
    """Cero tokens compartidos entre los extremos. Falla cerrado."""
    origen, destino = delta["items"]
    compartidos = terminos_indexados([origen["text"]]) & terminos_indexados([destino["text"]])
    if compartidos:
        return [
            f"los extremos del delta comparten {len(compartidos)} tokens indexados: "
            f"{sorted(compartidos)}"
        ]
    return []


# ===========================================================================
# 2. Corpus de conformidad v0.5
# ===========================================================================


def construir_corpus_conformidad(canon: CS4.Canon) -> dict[str, Any]:
    """Corpus v0.4 regenerado desde el canon **mas** el delta. Append-only."""
    base = B4.construir_corpus_conformidad(canon)
    delta = construir_delta()
    if fallos := fallos_de_condicion_lexica(delta):
        raise S5.ContratoFamiliaV05Error("; ".join(fallos))
    if S5.TIPO_RELACION_DELTA in S5.TIPOS_EXCLUIDOS_DEL_DELTA:
        raise S5.ContratoFamiliaV05Error(
            f"el tipo del delta no puede ser {S5.TIPO_RELACION_DELTA}: la resolucion "
            f"exige un tipo distinto de la supersesion y del conflicto"
        )

    corpus = copy.deepcopy(base)
    corpus["version"] = S5.VERSION_CORPUS_CONFORMIDAD
    corpus["version_contrato"] = S5.VERSION_CONTRATO
    corpus["generador"] = "experiments/adr002/benchmark/build_corpus_v0_5.py"
    corpus["hereda_de"] = "conformance_corpus_v0_4.json"
    corpus["delta_v0_5"] = {
        "motivo": (
            "Delta relacional discriminante de ADR002-C: dos extremos sinteticos con "
            "cero tokens indexados compartidos, unidos por una dependencia explicita, "
            "tipada y dirigida. Permite falsar una senal exclusivamente "
            "lexica-estructurada sin alterar ninguna adjudicacion heredada."
        ),
        "proyecto": delta["proyecto"]["id"],
        "entidades": [e["id"] for e in delta["entidades"]],
        "items": [i["id"] for i in delta["items"]],
        "relacion": delta["relacion"]["id"],
        "tipo_de_relacion": S5.TIPO_RELACION_DELTA,
        "tipos_excluidos": list(S5.TIPOS_EXCLUIDOS_DEL_DELTA),
    }
    corpus["proyectos"] = [*base["proyectos"], delta["proyecto"]]
    corpus["entidades"] = [*base["entidades"], *delta["entidades"]]
    corpus["items"] = [*base["items"], *delta["items"]]
    corpus["relaciones"] = [*base["relaciones"], delta["relacion"]]

    items = corpus["items"]
    corpus["colisiones_por_raiz_declaradas"] = B3.colisiones_por_raiz_entre_anclajes(items)
    corpus["conteos"] = {
        "proyectos": len(corpus["proyectos"]),
        "entidades": len(corpus["entidades"]),
        "items": len(items),
        "recuerdos": sum(1 for i in items if i["kind"] == "MEMORIA"),
        "decisiones": sum(1 for i in items if i["kind"] == "DECISION"),
        "mensajes": len(corpus["mensajes"]),
        "documentos": len(corpus["documentos"]),
        "relaciones": len(corpus["relaciones"]),
    }
    corpus["identidad"] = B3.identidad_de_colecciones(corpus)
    return corpus


def barrido_impacto_delta(corpus: dict[str, Any]) -> dict[str, Any]:
    """Recalcula los 66 dominios con y sin delta. **Exige cero cambios.**

    Es el mismo patron que ``barrido_impacto_dec016`` de la v0.4, con la
    exigencia invertida: alli un caso podia cambiar, aqui **ninguno** puede.
    """
    sin = copy.deepcopy(corpus)
    del_delta = {S5.ITEM_ORIGEN_DELTA, S5.ITEM_DESTINO_DELTA}
    sin["items"] = [i for i in sin["items"] if i["id"] not in del_delta]
    sin["proyectos"] = [p for p in sin["proyectos"] if p["id"] != S5.PROYECTO_DELTA]
    sin["entidades"] = [
        e
        for e in sin["entidades"]
        if e["id"] not in (S5.ENTIDAD_ORIGEN_DELTA, S5.ENTIDAD_DESTINO_DELTA)
    ]

    dominios: dict[str, dict[str, Any]] = dict(B4.DOMINIOS)
    for (ca, sufijo), dominio in B4.DOMINIOS_RAMA.items():
        dominios[f"{ca}/{sufijo}"] = dominio

    cambios = [
        ident
        for ident, dominio in sorted(dominios.items())
        if B4.evaluar_universo(corpus, dominio) != B4.evaluar_universo(sin, dominio)
    ]
    if cambios:
        raise S5.ContratoFamiliaV05Error(
            f"el delta relacional altero adjudicaciones heredadas: {cambios}"
        )
    if len(dominios) != S5.DOMINIOS_RECALCULADOS:
        raise S5.ContratoFamiliaV05Error(
            f"se esperaban {S5.DOMINIOS_RECALCULADOS} dominios y hay {len(dominios)}"
        )
    return {
        "adjudicaciones_recalculadas": len(dominios),
        "cambios": cambios,
        "regla": "ninguna adjudicacion heredada puede cambiar al anadir el delta relacional",
        "razon_estructural": (
            "64 de los 66 dominios estan acotados a proyectos existentes y no pueden ver "
            "un proyecto nuevo. Los dos que usan GLOBAL_TODOS son B04-CA-01, anclado al "
            "prefijo 'redact' que el delta no contiene, y B04-CA-14, restringido al grupo "
            "homonimo JUAN que las entidades del delta no declaran."
        ),
    }


# ===========================================================================
# 3. Canales laterales · reciben el corpus y NADA MAS
# ===========================================================================


def construir_subject_keys(corpus: dict[str, Any]) -> dict[str, Any]:
    """Proyeccion definitiva de sujeto. Cobertura total, ``null`` incluido."""
    nombres = {e["id"]: e["nombre_canonico"] for e in corpus["entidades"]}
    valores: dict[str, str | None] = {}
    for item in corpus["items"]:
        declaradas = list(item.get("entity_ids") or [])
        if len(declaradas) != 1:
            valores[item["id"]] = None
            continue
        entidad = declaradas[0]
        if entidad not in nombres:
            raise S5.ContratoFamiliaV05Error(
                f"{item['id']} declara la entidad {entidad!r}, ausente del corpus"
            )
        clave = S5.slug_de_sujeto(nombres[entidad])
        if not S5.RX_SUBJECT_KEY.match(clave):
            raise S5.ContratoFamiliaV05Error(
                f"{item['id']}: clave de sujeto {clave!r} fuera del formato cerrado"
            )
        valores[item["id"]] = clave
    presentes = sorted({v for v in valores.values() if v is not None})
    for izquierda in presentes:
        for derecha in presentes:
            if izquierda != derecha and derecha.startswith(izquierda):
                raise S5.ContratoFamiliaV05Error(
                    f"la clave {izquierda!r} es prefijo de {derecha!r}: la familia "
                    f"estructural de E3 dejaria de coincidir con la entidad"
                )
    return {
        "documento": "Canal lateral de subject_key_experimental",
        "version": "0.1",
        "version_contrato": S5.VERSION_CONTRATO,
        "estado": S5.ESTADO_NO_CONGELADO,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_5.py",
        "indexado_por": "identidad canonica del item",
        "proyeccion_descartada": S5.PROYECCION_DE_SONDA_DESCARTADA,
        "conteos": {
            "items": len(valores),
            "con_sujeto": sum(1 for v in valores.values() if v is not None),
            "sin_sujeto": sum(1 for v in valores.values() if v is None),
            "sujetos_distintos": len(presentes),
        },
        "valores": {k: valores[k] for k in sorted(valores)},
    }


def construir_property_keys(corpus: dict[str, Any]) -> dict[str, Any]:
    """Canal lateral del predicado. Cobertura total, ``null`` incluido."""
    entidades = {e["id"]: e for e in corpus["entidades"]}
    valores: dict[str, str | None] = {}
    for item in corpus["items"]:
        valores[item["id"]] = _property_key_de(item, entidades)
    presentes = [v for v in valores.values() if v is not None]
    for valor in presentes:
        if not S5.RX_PROPERTY_KEY.match(valor):
            raise S5.ContratoFamiliaV05Error(f"property_key fuera de formato: {valor!r}")
    return {
        "documento": "Canal lateral de property_key",
        "version": "0.1",
        "version_contrato": S5.VERSION_CONTRATO,
        "estado": S5.ESTADO_NO_CONGELADO,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_5.py",
        "indexado_por": "identidad canonica del item",
        "limitacion_declarada": S5.LIMITACION_PROPERTY_KEY,
        "conteos": {
            "items": len(valores),
            "con_predicado": len(presentes),
            "sin_predicado": sum(1 for v in valores.values() if v is None),
            "predicados_distintos": len(set(presentes)),
        },
        "valores": {k: valores[k] for k in sorted(valores)},
    }


def _property_key_de(item: dict[str, Any], entidades: dict[str, Any]) -> str | None:
    """Regla cerrada. Solo lee texto, sujeto, clase y ambito del propio item."""
    declaradas = list(item.get("entity_ids") or [])
    if len(declaradas) != 1:
        return None
    entidad = entidades.get(declaradas[0])
    if entidad is None:
        return None
    del_sujeto = set(B3._tokens(entidad["nombre_canonico"]))
    for alias in entidad.get("alias") or []:
        del_sujeto.update(B3._tokens(alias))
    raices = sorted(
        {
            token[: S5.LONGITUD_RAIZ]
            for token in B3._tokens(item["text"])
            if len(token) >= S5.LONGITUD_TOKEN_INFORMATIVO
            and token not in S5.VACIAS
            and token not in del_sujeto
        }
    )
    if not raices:
        return None
    digest = hashlib.sha256("|".join(raices).encode("utf-8")).hexdigest()
    return f"{S5.PREFIJO_PROPERTY_KEY}{digest[: S5.LONGITUD_PROPERTY_KEY]}"


def construir_criticidad_aplicada(corpus: dict[str, Any]) -> dict[str, Any]:
    """Plano comun seguro. La fuente bruta se consume aqui y **no cruza**."""
    valores: dict[str, dict[str, str] | None] = {}
    for item in corpus["items"]:
        bruta = item.get("criticidad")
        if not bruta:
            valores[item["id"]] = None
            continue
        fuente = str(bruta["fuente"])
        if fuente not in S5.TABLA_FUENTE_DE_POLITICA:
            raise S5.ContratoFamiliaV05Error(
                f"{item['id']}: fuente bruta {fuente!r} ausente de la tabla cerrada; "
                f"la construccion aborta y no hay valor por defecto"
            )
        aplicada = {
            "nivel": str(bruta["nivel"]),
            "razon_segura": str(bruta["razon"]),
            "fuente_de_politica": S5.TABLA_FUENTE_DE_POLITICA[fuente],
            "regla_de_politica": str(bruta["regla"]),
        }
        for campo in ("razon_segura", "regla_de_politica"):
            if S5.contiene_identificador_de_caso(aplicada[campo]):
                raise S5.ContratoFamiliaV05Error(
                    f"{item['id']}: {campo} porta un identificador de caso del banco"
                )
        valores[item["id"]] = aplicada
    return {
        "documento": "Plano comun seguro de criticidad aplicada",
        "version": "0.1",
        "version_contrato": S5.VERSION_CONTRATO,
        "estado": S5.ESTADO_NO_CONGELADO,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_5.py",
        "indexado_por": "identidad canonica del item",
        "campos": list(S5.CAMPOS_CRITICIDAD_APLICADA),
        "plano_privado_que_no_cruza": "criticidad.fuente",
        "usos_permitidos": list(S5.USOS_PERMITIDOS_CRITICIDAD),
        "usos_prohibidos": list(S5.USOS_PROHIBIDOS_CRITICIDAD),
        "censo": censo_de_criticidad(corpus),
        "valores": {k: valores[k] for k in sorted(valores)},
    }


def censo_de_criticidad(corpus: dict[str, Any]) -> dict[str, Any]:
    """Censo **propio** de la familia. No se copian las constantes de la v0.4."""
    items = corpus["items"]
    con_marca = [i for i in items if i.get("criticidad")]
    distribucion: dict[str, int] = {}
    for item in con_marca:
        nivel = str(item["criticidad"]["nivel"])
        distribucion[nivel] = distribucion.get(nivel, 0) + 1
    return {
        "items": len(items),
        "sin_criticidad": len(items) - len(con_marca),
        "con_criticidad": len(con_marca),
        "distribucion_por_nivel": dict(sorted(distribucion.items())),
        "fuentes_de_politica": dict(
            sorted(
                {
                    politica: sum(
                        1
                        for i in con_marca
                        if S5.TABLA_FUENTE_DE_POLITICA[str(i["criticidad"]["fuente"])] == politica
                    )
                    for politica in S5.FUENTES_DE_POLITICA
                }.items()
            )
        ),
        "razones_seguras_distintas": len({str(i["criticidad"]["razon"]) for i in con_marca}),
        "reglas_de_politica_distintas": len({str(i["criticidad"]["regla"]) for i in con_marca}),
    }


# ===========================================================================
# 4. Caso discriminante y su referencia por camino independiente
# ===========================================================================

#: Peticion del caso. ``EXHAUSTIVA`` para que la escalera se recorra entera y
#: ningun limite pueda enmascarar el resultado, y limites holgados para que la
#: ausencia del destino no pueda atribuirse a un recorte.
PETICION_DISCRIMINANTE: dict[str, Any] = {
    "operation_id": "adr002-disc-rel-01",
    "consulta": S5.CONSULTA_DELTA,
    "proposito": "responder_al_usuario",
    "modo": "M1",
    "ambito": S5.PROYECTO_DELTA,
    "regla_multiproyecto": "SOLO_PROYECTO",
    "tiempo_objetivo": S5.AHORA_DECLARADO,
    "corte_registro": None,
    "cardinalidad": "EXHAUSTIVA",
    "limite_objetivo": 10,
    "limite_duro": 10,
    "objetivos": 1,
}


def _alcance_lexico_estructurado(corpus: dict[str, Any], consulta: str) -> list[str]:
    """Modelo cerrado de las senales declaradas de una expansion lexica.

    Reproduce, sobre el corpus y por conjuntos de tokens, lo que las tres
    senales declaradas de una expansion exclusivamente lexica-estructurada
    pueden alcanzar: coincidencia literal de termino, variante morfologica por
    recorte de sufijo y termino puente tomado de lo ya recuperado. **No importa
    ningun candidato**: describe el mecanismo, no ejecuta una implementacion.
    """
    subject = construir_subject_keys(corpus)["valores"]
    en_ambito = [i for i in corpus["items"] if i["project_id"] == PETICION_DISCRIMINANTE["ambito"]]
    consulta_tokens = {t for t in B3._tokens(consulta) if t not in S5.VACIAS}

    def tokens_de(item: dict[str, Any]) -> set[str]:
        return {t for t in B3._tokens(item["text"]) if t not in S5.VACIAS}

    directos = [
        i
        for i in en_ambito
        if tokens_de(i) & consulta_tokens or subject.get(i["id"]) in consulta_tokens
    ]
    puente: set[str] = set()
    familias: set[str] = set()
    for semilla in directos:
        puente |= tokens_de(semilla) - consulta_tokens
        clave = subject.get(semilla["id"])
        if clave:
            familias.add(clave)
    alcanzados = {i["id"] for i in directos}
    for item in en_ambito:
        if item["id"] in alcanzados:
            continue
        clave = subject.get(item["id"])
        if tokens_de(item) & puente or (clave and any(clave.startswith(f) for f in familias)):
            alcanzados.add(item["id"])
    return sorted(alcanzados)


def _alcance_por_indice(corpus: dict[str, Any], consulta: str) -> list[str]:
    """Camino independiente: el mismo alcance, calculado **con el indice real**.

    No comparte una sola linea con ``_alcance_lexico_estructurado``: en vez de
    operar sobre conjuntos de tokens en Python, carga los textos en una tabla
    FTS5 con la configuracion efectiva del indice de Sirius 0.1 y resuelve el
    alcance con ``MATCH``. Que dos caminos distintos coincidan es lo que
    convierte la referencia en falsable.
    """
    subject = construir_subject_keys(corpus)["valores"]
    en_ambito = [i for i in corpus["items"] if i["project_id"] == PETICION_DISCRIMINANTE["ambito"]]
    conexion = sqlite3.connect(":memory:")
    try:
        conexion.execute("CREATE VIRTUAL TABLE t USING fts5(item_id UNINDEXED, content)")
        conexion.executemany(
            "INSERT INTO t(item_id, content) VALUES (?, ?)",
            [(i["id"], i["text"]) for i in en_ambito],
        )

        def coincidencias(terminos: list[str]) -> set[str]:
            limpios = sorted({"".join(c for c in t.lower() if c.isalnum()) for t in terminos if t})
            if not limpios:
                return set()
            expresion = " OR ".join(f'"{t}"' for t in limpios)
            return {
                str(fila[0])
                for fila in conexion.execute("SELECT item_id FROM t WHERE t MATCH ?", (expresion,))
            }

        terminos_consulta = [t for t in B3._tokens(consulta) if t not in S5.VACIAS]
        directos = coincidencias(terminos_consulta)
        directos |= {i["id"] for i in en_ambito if subject.get(i["id"]) in set(terminos_consulta)}
        puente: list[str] = []
        familias: list[str] = []
        for item in en_ambito:
            if item["id"] not in directos:
                continue
            puente += [
                t
                for t in B3._tokens(item["text"])
                if t not in S5.VACIAS and t not in terminos_consulta
            ]
            clave = subject.get(item["id"])
            if clave:
                familias.append(clave)
        alcanzados = set(directos) | coincidencias(puente)
        alcanzados |= {
            i["id"]
            for i in en_ambito
            if (clave := subject.get(i["id"])) and any(clave.startswith(f) for f in familias)
        }
        return sorted(alcanzados)
    finally:
        conexion.close()


def _un_salto_relacional(corpus: dict[str, Any], desde: list[str]) -> list[str]:
    """Identificadores que un recorrido explicito de un salto anadiria."""
    origen = set(desde)
    return sorted(
        {
            r["destino"]
            for r in corpus["relaciones"]
            if r["origen"] in origen and r["destino"] not in origen
        }
    )


def construir_casos(canon: CS4.Canon, corpus: dict[str, Any]) -> dict[str, Any]:
    """Casos heredados **byte a byte** mas el caso discriminante."""
    heredados = B4.construir_casos(canon, corpus)
    alcance = _alcance_lexico_estructurado(corpus, S5.CONSULTA_DELTA)
    salto = _un_salto_relacional(corpus, alcance)

    caso = {
        "id": "N4-01",
        "nivel": 4,
        "clase": "CASO_DISCRIMINANTE_RELACIONAL",
        "identificador": "ADR002-DISC-REL-01",
        "fuente": (
            "Resolucion pre-benchmark de ADR-002 v0.4 §8.1 puntos 5-8, aprobada por el "
            "acta v1.0 §1 punto 13"
        ),
        "proposito": (
            "Falsar la suficiencia de una expansion exclusivamente lexica-estructurada "
            "ante una dependencia explicita entre dos sujetos sin solapamiento lexico."
        ),
        "comportamiento_observable": (
            "Que identificadores alcanza la recuperacion recorriendo E0-E5 integra, y "
            "cual de ellos solo es alcanzable siguiendo una arista explicita de un salto."
        ),
        "entrada": {
            "peticion": dict(PETICION_DISCRIMINANTE),
            "extremos": {
                "origen": S5.ITEM_ORIGEN_DELTA,
                "destino": S5.ITEM_DESTINO_DELTA,
            },
            "relacion": {
                "id": S5.RELACION_DELTA,
                "tipo": S5.TIPO_RELACION_DELTA,
                "origen": S5.ITEM_ORIGEN_DELTA,
                "destino": S5.ITEM_DESTINO_DELTA,
            },
            "consulta_propia_del_destino": S5.CONSULTA_PROPIA_DEL_DESTINO,
        },
        "oraculo": {
            "alcance_lexico_estructurado": alcance,
            "aportado_por_un_salto_relacional": salto,
            "sin_la_arista_no_hay_aporte": _un_salto_relacional(
                {
                    **corpus,
                    "relaciones": [r for r in corpus["relaciones"] if r["id"] != S5.RELACION_DELTA],
                },
                alcance,
            ),
            "estado": "DERIVADO_PROPUESTO",
            "justificacion": (
                "Calculado sobre el corpus congelado por la regla cerrada del generador; "
                "la referencia lo recalcula por un camino independiente."
            ),
        },
        "no_mide": [
            "latencia",
            "memoria",
            "almacenamiento",
            "calidad comparada entre candidatos",
        ],
    }
    salida = dict(heredados)
    salida["version"] = S5.VERSION_CORPUS_CONFORMIDAD
    salida["hereda_de"] = "cases_v0_4.json"
    salida["conteos"] = {**heredados["conteos"], "nivel_4_discriminante": 1}
    salida["nivel_4"] = [caso]
    return salida


def construir_referencias(casos: dict[str, Any], corpus: dict[str, Any]) -> dict[str, Any]:
    """Referencias heredadas mas la del delta, por **camino independiente**."""
    heredadas = B4.construir_referencias(casos)
    alcance = _alcance_por_indice(corpus, S5.CONSULTA_DELTA)
    salto = _un_salto_relacional(corpus, alcance)
    propia = _alcance_por_indice(corpus, S5.CONSULTA_PROPIA_DEL_DESTINO)

    caso = next(c for c in casos["nivel_4"] if c["id"] == "N4-01")
    if alcance != caso["oraculo"]["alcance_lexico_estructurado"]:
        raise S5.ContratoFamiliaV05Error(
            f"los dos caminos discrepan en el alcance lexico: {alcance} frente a "
            f"{caso['oraculo']['alcance_lexico_estructurado']}"
        )

    referencia = {
        "caso": "N4-01",
        "identificador": "ADR002-DISC-REL-01",
        "tipo_referencia": "DISCRIMINANTE_RELACIONAL",
        "camino": (
            "Independiente del generador del corpus: los textos se cargan en una tabla "
            "FTS5 con la configuracion efectiva del indice de Sirius 0.1 y el alcance se "
            "resuelve con MATCH, no con conjuntos de tokens en Python."
        ),
        "alcance_lexico_estructurado": alcance,
        "aportado_por_un_salto_relacional": salto,
        "destino_recuperable_por_consulta_propia": S5.ITEM_DESTINO_DELTA in propia,
        "tokens_compartidos_entre_extremos": 0,
        "tokenizacion": "FTS5 unicode61 remove_diacritics=1 (identidad efectiva del indice)",
        "estado": "DERIVADO_PROPUESTO",
    }
    salida = dict(heredadas)
    salida["version"] = S5.VERSION_CORPUS_CONFORMIDAD
    salida["hereda_de"] = "references_v0_4.json"
    salida["conteos"] = {**heredadas["conteos"], "referencias_discriminantes": 1}
    salida["referencias_nivel_4"] = [referencia]
    return salida


# ===========================================================================
# 5. Manifiesto sucesor
# ===========================================================================


def construir_manifiesto(
    corpus: dict[str, Any],
    subject_keys: dict[str, Any],
    property_keys: dict[str, Any],
    criticidad: dict[str, Any],
    casos: dict[str, Any],
    referencias: dict[str, Any],
    barrido: dict[str, Any],
) -> dict[str, Any]:
    """Cierra **inequivocamente la familia completa**, heredados incluidos."""
    return {
        "documento": "Manifiesto de la familia sucesora de conformidad de ADR-002",
        "version_contrato": S5.VERSION_CONTRATO,
        "estado": S5.ESTADO_NO_CONGELADO,
        "semilla_compartida": S5.SEMILLA,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_5.py",
        "advertencia": (
            "Ninguna puerta de arranque queda satisfecha por este manifiesto. El "
            "benchmark permanece BLOQUEADO, NO AUTORIZADO y NO EJECUTADO. La ronda "
            "primaria sigue siendo T0 + A + B + C + D, sin reduccion."
        ),
        "custodia": {
            "principio": "append-only",
            "regla": (
                "La familia v0.5 se materializa JUNTO A la v0.4. Ningun artefacto "
                "congelado de la v0.4 se sobrescribe, renombra ni modifica."
            ),
            "heredados_por_blob": {n: S5.BLOBS_V0_4[n] for n in S5.HEREDADOS_V0_5},
            "v0_4_intacta_por_blob": dict(S5.BLOBS_V0_4),
        },
        "artefactos_sucesores": list(S5.CONGELABLES_V0_5),
        "orden_de_materializacion": list(S5.ORDEN_DE_MATERIALIZACION),
        "dependencias": {
            "conformance_corpus_v0_5.json": ["canon .docx", "conformance_corpus_v0_4.json"],
            "subject_keys_v0_1.json": ["conformance_corpus_v0_5.json"],
            "property_keys_v0_1.json": ["conformance_corpus_v0_5.json"],
            "applied_criticality_v0_1.json": ["conformance_corpus_v0_5.json"],
            "cases_v0_5.json": ["conformance_corpus_v0_5.json", "subject_keys_v0_1.json"],
            "references_v0_5.json": ["cases_v0_5.json", "conformance_corpus_v0_5.json"],
            "benchmark_manifest_v0_5.json": list(S5.CONGELABLES_V0_5[:-1]),
        },
        "anterioridad": (
            "Las tres funciones de canal lateral reciben por firma el corpus y nada mas: "
            "no pueden leer casos ni referencias porque no los tienen. El caso los "
            "consume, y no al reves."
        ),
        "canales_laterales": {
            "property_key": {
                "fichero": "property_keys_v0_1.json",
                "fuente_de_asignacion": S5.FUENTE_DE_ASIGNACION_PROPERTY_KEY,
                "version_del_vocabulario": S5.VERSION_VOCABULARIO_PROPERTY_KEY,
                "regla_de_validacion": S5.REGLA_DE_VALIDACION_PROPERTY_KEY,
                "limitacion_declarada": S5.LIMITACION_PROPERTY_KEY,
                "conteos": property_keys["conteos"],
            },
            "subject_key_experimental": {
                "fichero": "subject_keys_v0_1.json",
                "fuente_de_asignacion": S5.FUENTE_DE_ASIGNACION_SUBJECT_KEY,
                "version_del_vocabulario": S5.VERSION_VOCABULARIO_SUBJECT_KEY,
                "regla_de_validacion": S5.REGLA_DE_VALIDACION_SUBJECT_KEY,
                "proyeccion_descartada": S5.PROYECCION_DE_SONDA_DESCARTADA,
                "conteos": subject_keys["conteos"],
            },
        },
        "criticidad_aplicada": {
            "fichero": "applied_criticality_v0_1.json",
            "tabla_cerrada": dict(S5.TABLA_FUENTE_DE_POLITICA),
            "campos": list(S5.CAMPOS_CRITICIDAD_APLICADA),
            "censo": criticidad["censo"],
        },
        "clasificacion_por_terna": {
            "capacidades": list(S5.CAPACIDADES),
            "regla": (
                "Estructural y fallo-cerrado: un campo sin terna asignada aborta la "
                "construccion. El control de inaccesibilidad es lista blanca por "
                "contencion, nunca busqueda de ausencia de una cadena."
            ),
            "atributos_permitidos_al_candidato": sorted(S5.ATRIBUTOS_PERMITIDOS_AL_CANDIDATO),
            "atributos_vetados_al_candidato": sorted(S5.ATRIBUTOS_VETADOS_AL_CANDIDATO),
            "campos": {
                campo: {
                    "capacidad": entrada["capacidad"],
                    "consumidores": list(entrada["consumidores"]),  # type: ignore[arg-type]
                    "uso_autorizado": entrada["uso_autorizado"],
                    "uso_prohibido": entrada["uso_prohibido"],
                }
                for campo, entrada in sorted(S5.CLASIFICACION.items())
            },
        },
        "delta_relacional": {
            **corpus["delta_v0_5"],
            "barrido_de_impacto": barrido,
            "condicion_lexica": (
                "cero tokens indexados compartidos entre los extremos, medidos con FTS5 "
                "unicode61 remove_diacritics=1"
            ),
        },
        "vocabularios_p2": {
            "naturaleza": (
                "Convenciones locales experimentales del banco. NO se atribuyen a ADR-001 "
                "como vocabularios productivos y no deciden el vocabulario productivo."
            ),
            "confirmacion": list(S5.CONFIRMACION),
            "validez": list(S5.VALIDEZ),
            "disponibilidad": list(S5.DISPONIBILIDAD),
            "sensibilidad": list(S5.SENSIBILIDAD),
            "autoridad": list(S5.AUTORIDAD),
            "ambito": list(S5.AMBITO),
            "polaridad": list(S5.POLARIDAD),
            "tipos_relacion": list(S5.TIPOS_RELACION),
            "nivel_criticidad": list(S5.NIVEL_CRITICIDAD),
            "fuentes_de_politica": list(S5.FUENTES_DE_POLITICA),
            "property_key": {
                "formato": S5.RX_PROPERTY_KEY.pattern,
                "version": S5.VERSION_VOCABULARIO_PROPERTY_KEY,
            },
        },
        "proyeccion_t0": {
            "regenerada": False,
            "fichero_no_regenerado": S5.PROYECCION_T0_NO_REGENERADA,
            "blob_observado": S5.PROYECCION_T0_BLOB_OBSERVADO,
            "estado": S5.ESTADO_NO_NORMATIVO,
            "valor": "observacion sin valor vinculante; no es evidencia congelada",
            "motivo": S5.PROYECCION_T0_MOTIVO,
            "arnes_de_conformidad_de_t0": "NO EXISTE; no se presupone y no se construye aqui",
        },
        "rendimiento": {
            "fichero": "performance_corpus_v0_2.json",
            "blob": S5.BLOBS_V0_4["performance_corpus_v0_2.json"],
            "sha256": S5.SHA256_PERFORMANCE_V0_2,
            "regla": "heredado byte a byte; la familia v0.5 no mide rendimiento",
        },
        "conteos": {
            "corpus": corpus["conteos"],
            "casos": casos["conteos"],
            "referencias": referencias["conteos"],
        },
        "identidad_del_corpus": corpus["identidad"],
        "huellas_de_artefacto": {},
    }


# ===========================================================================
# 6. Construccion completa
# ===========================================================================


def construir_todo() -> dict[str, dict[str, Any]]:
    """Los siete sucesores, en el orden declarado."""
    canon = CS4.cargar_canon()
    corpus = construir_corpus_conformidad(canon)
    barrido = barrido_impacto_delta(corpus)
    subject_keys = construir_subject_keys(corpus)
    property_keys = construir_property_keys(corpus)
    criticidad = construir_criticidad_aplicada(corpus)
    casos = construir_casos(canon, corpus)
    referencias = construir_referencias(casos, corpus)
    manifiesto = construir_manifiesto(
        corpus, subject_keys, property_keys, criticidad, casos, referencias, barrido
    )
    artefactos: dict[str, dict[str, Any]] = {
        "conformance_corpus_v0_5.json": corpus,
        "subject_keys_v0_1.json": subject_keys,
        "property_keys_v0_1.json": property_keys,
        "applied_criticality_v0_1.json": criticidad,
        "cases_v0_5.json": casos,
        "references_v0_5.json": referencias,
        "benchmark_manifest_v0_5.json": manifiesto,
    }
    manifiesto["huellas_de_artefacto"] = {
        nombre: _huella(datos)
        for nombre, datos in artefactos.items()
        if nombre != "benchmark_manifest_v0_5.json"
    }
    return artefactos


def _volcar(ruta: Path, datos: dict[str, Any]) -> int:
    texto = json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    ruta.write_text(texto, encoding="utf-8")
    return len(texto.encode("utf-8"))


def escribir_en(directorio: Path) -> dict[str, int]:
    """El validador regenera en un temporal: validar nunca escribe en el arbol."""
    directorio.mkdir(parents=True, exist_ok=True)
    return {n: _volcar(directorio / n, d) for n, d in construir_todo().items()}


def main() -> None:
    for nombre, tamano in escribir_en(AQUI).items():
        print(f"{nombre}: {tamano} bytes")


if __name__ == "__main__":
    main()
