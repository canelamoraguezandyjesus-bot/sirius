"""Validador v0.5 · familia sucesora de conformidad de ADR-002.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.validate_corpus_v0_5

**Regla de independencia**, la misma que la matriz de aceptacion impone al
validador v0.4: este modulo **no importa ni reutiliza** las funciones de cierre
del generador. Cada frontera, censo, huella y alcance se recalcula aqui con un
oraculo propio que lee los artefactos JSON de forma declarativa.
``build_corpus_v0_5`` solo se importa dentro de la comprobacion de determinismo,
para regenerar en un directorio temporal, y dentro de la comprobacion de
anterioridad, que inspecciona **firmas** y no comportamiento.

**Semantica declarada.** El informe **acumula** todos los fallos y **no aborta
en el primero**. Los dos puntos en los que la construccion si aborta —una fuente
bruta de criticidad ausente de la tabla cerrada y un campo sin terna asignada—
se comprueban aqui **provocandolos**, porque un aborto que nadie ejercita es una
promesa, no un control.

El unico fichero que escribe es su propio informe, y solo desde ``main()``. No
ejecuta T0, no implementa ni ejecuta ADR002-A/B/C/D y no mide rendimiento.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import schema_v0_5 as S5

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
SALIDA = RAIZ / "artifacts" / "adr002_benchmark_preparation" / "validacion_familia_v0.5.json"


class Informe:
    """Acumula. No aborta en el primer fallo."""

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
    return {n: json.loads((base / n).read_text(encoding="utf-8")) for n in S5.CONGELABLES_V0_5}


# ===========================================================================
# Oraculo propio · nada de esto se importa del generador
# ===========================================================================


def _blob_git(contenido: bytes) -> str:
    cabecera = f"blob {len(contenido)}\0".encode()
    return hashlib.sha1(cabecera + contenido).hexdigest()


def _normalizar(texto: str | None) -> list[str]:
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    plano = "".join(c for c in descompuesto if not unicodedata.combining(c)).lower()
    return [t for t in re.split(r"[^0-9a-z]+", plano) if t]


def _slug(nombre: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", nombre.lower())
    return "".join(c for c in descompuesto if c.isalnum() and not unicodedata.combining(c))


def _terminos_del_indice(textos: list[str]) -> set[str]:
    """Terminos reales: FTS5 por omision, es decir ``unicode61`` con rd=1."""
    conexion = sqlite3.connect(":memory:")
    try:
        conexion.execute("CREATE VIRTUAL TABLE t USING fts5(content)")
        conexion.execute("CREATE VIRTUAL TABLE v USING fts5vocab(t, row)")
        conexion.executemany("INSERT INTO t(content) VALUES (?)", [(x,) for x in textos])
        return {str(f[0]) for f in conexion.execute("SELECT term FROM v")}
    finally:
        conexion.close()


def _property_key_oraculo(item: dict[str, Any], entidades: dict[str, Any]) -> str | None:
    declaradas = list(item.get("entity_ids") or [])
    if len(declaradas) != 1 or declaradas[0] not in entidades:
        return None
    entidad = entidades[declaradas[0]]
    del_sujeto: set[str] = set(_normalizar(entidad["nombre_canonico"]))
    for alias in entidad.get("alias") or []:
        del_sujeto |= set(_normalizar(alias))
    raices = sorted(
        {
            t[: S5.LONGITUD_RAIZ]
            for t in _normalizar(item["text"])
            if len(t) >= S5.LONGITUD_TOKEN_INFORMATIVO
            and t not in S5.VACIAS
            and t not in del_sujeto
        }
    )
    if not raices:
        return None
    return (
        S5.PREFIJO_PROPERTY_KEY
        + hashlib.sha256("|".join(raices).encode()).hexdigest()[: S5.LONGITUD_PROPERTY_KEY]
    )


# ===========================================================================
# 1. Custodia append-only: la v0.4 permanece intacta
# ===========================================================================


def _v0_4_intacta(inf: Informe) -> None:
    observados = {}
    for nombre, esperado in S5.BLOBS_V0_4.items():
        ruta = AQUI / nombre
        observados[nombre] = _blob_git(ruta.read_bytes()) if ruta.exists() else "AUSENTE"
        inf.check(
            f"v0.4 intacta byte a byte: {nombre}",
            observados[nombre] == esperado,
            {"observado": observados[nombre], "esperado": esperado},
        )
    inf.check(
        "ningun artefacto sucesor reutiliza el nombre de uno congelado",
        not (set(S5.CONGELABLES_V0_5) & set(S5.BLOBS_V0_4)),
        sorted(set(S5.CONGELABLES_V0_5) & set(S5.BLOBS_V0_4)),
    )
    heredados_declarados = set(S5.HEREDADOS_V0_5)
    inf.check(
        "los heredados sin cambio son congelables de la v0.4",
        heredados_declarados <= set(S5.BLOBS_V0_4),
        sorted(heredados_declarados - set(S5.BLOBS_V0_4)),
    )


# ===========================================================================
# 2. Corpus sucesor y delta relacional
# ===========================================================================


def _corpus(corpus: dict[str, Any], inf: Informe) -> None:
    items = corpus["items"]
    reales = {
        "proyectos": len(corpus["proyectos"]),
        "entidades": len(corpus["entidades"]),
        "items": len(items),
        "recuerdos": sum(1 for i in items if i["kind"] == "MEMORIA"),
        "decisiones": sum(1 for i in items if i["kind"] == "DECISION"),
        "mensajes": len(corpus["mensajes"]),
        "documentos": len(corpus["documentos"]),
        "relaciones": len(corpus["relaciones"]),
    }
    inf.check(
        "conteos del corpus contados sobre los datos",
        corpus["conteos"] == reales,
        {"declarado": corpus["conteos"], "real": reales},
    )
    identidad = {
        coleccion: {
            "conteo": len(corpus[coleccion]),
            "huella_coleccion": hashlib.sha256(
                json.dumps(corpus[coleccion], ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "huella_por_elemento": {
                e["id"]: hashlib.sha256(
                    json.dumps(e, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest()
                for e in corpus[coleccion]
            },
        }
        for coleccion in ("items", "mensajes", "documentos", "relaciones", "entidades", "proyectos")
    }
    inf.check("identidad por elemento recalculada", identidad == corpus["identidad"], None)
    inf.check(
        "el corpus declara version de contrato 0.5",
        corpus["version_contrato"] == S5.VERSION_CONTRATO,
        corpus["version_contrato"],
    )
    inf.check("la semilla no cambia", corpus["semilla"] == S5.SEMILLA, corpus["semilla"])


def _delta(corpus: dict[str, Any], inf: Informe) -> None:
    por_id = {i["id"]: i for i in corpus["items"]}
    origen, destino = por_id.get(S5.ITEM_ORIGEN_DELTA), por_id.get(S5.ITEM_DESTINO_DELTA)
    if origen is None or destino is None:
        inf.check("los dos extremos del delta existen", False, None)
        return
    inf.check("los dos extremos del delta existen", True, None)

    compartidos = _terminos_del_indice([origen["text"]]) & _terminos_del_indice([destino["text"]])
    inf.check(
        "cero tokens indexados compartidos entre los extremos (FTS5 unicode61 rd=1)",
        not compartidos,
        sorted(compartidos),
    )
    inf.check(
        "mismo proyecto en ambos extremos",
        origen["project_id"] == destino["project_id"] == S5.PROYECTO_DELTA,
        {"origen": origen["project_id"], "destino": destino["project_id"]},
    )
    inf.check(
        "sujetos distintos en los extremos",
        origen["entity_ids"] != destino["entity_ids"],
        {"origen": origen["entity_ids"], "destino": destino["entity_ids"]},
    )
    relaciones = {r["id"]: r for r in corpus["relaciones"]}
    arista = relaciones.get(S5.RELACION_DELTA)
    inf.check("la arista discriminante existe", arista is not None, None)
    if arista is not None:
        inf.check(
            "la arista es explicita, tipada y dirigida del origen al destino",
            arista["origen"] == S5.ITEM_ORIGEN_DELTA
            and arista["destino"] == S5.ITEM_DESTINO_DELTA
            and arista["tipo"] == S5.TIPO_RELACION_DELTA,
            arista,
        )
        inf.check(
            "el tipo no es supersesion ni conflicto",
            arista["tipo"] not in S5.TIPOS_EXCLUIDOS_DEL_DELTA,
            arista["tipo"],
        )
        inf.check(
            "el tipo pertenece al vocabulario aprobado",
            arista["tipo"] in S5.TIPOS_RELACION,
            arista["tipo"],
        )
        inf.check(
            "la nota de la arista no nombra ningun caso del banco",
            not S5.contiene_identificador_de_caso(str(arista.get("nota", ""))),
            arista.get("nota"),
        )
    for extremo in (origen, destino):
        inf.check(
            f"{extremo['id']} declara todas las dimensiones P2",
            all(
                extremo[campo] in vocabulario
                for campo, vocabulario in (
                    ("confirmacion", S5.CONFIRMACION),
                    ("validez", S5.VALIDEZ),
                    ("disponibilidad", S5.DISPONIBILIDAD),
                    ("sensibilidad", S5.SENSIBILIDAD),
                    ("autoridad", S5.AUTORIDAD),
                    ("ambito", S5.AMBITO),
                    ("polaridad", S5.POLARIDAD),
                )
            ),
            {c: extremo[c] for c in ("confirmacion", "validez", "disponibilidad", "ambito")},
        )
        inf.check(
            f"{extremo['id']} no lleva etiqueta de candidato",
            not re.search(r"ADR002-[ABCD]\b", extremo["text"]),
            extremo["text"],
        )


# ===========================================================================
# 3. Canales laterales
# ===========================================================================


def _subject_keys(corpus: dict[str, Any], canal: dict[str, Any], inf: Informe) -> None:
    ids = {i["id"] for i in corpus["items"]}
    valores = canal["valores"]
    inf.check(
        "cobertura total del canal de sujeto, null incluido",
        set(valores) == ids,
        {"faltan": sorted(ids - set(valores)), "sobran": sorted(set(valores) - ids)},
    )
    nombres = {e["id"]: e["nombre_canonico"] for e in corpus["entidades"]}
    esperado = {}
    for item in corpus["items"]:
        declaradas = list(item.get("entity_ids") or [])
        esperado[item["id"]] = _slug(nombres[declaradas[0]]) if len(declaradas) == 1 else None
    inf.check("la proyeccion definitiva coincide con el oraculo", valores == esperado, None)
    presentes = sorted({v for v in valores.values() if v})
    inf.check(
        "toda clave presente respeta el formato cerrado",
        all(S5.RX_SUBJECT_KEY.match(v) for v in presentes),
        presentes,
    )
    prefijos = [(a, b) for a in presentes for b in presentes if a != b and b.startswith(a)]
    inf.check(
        "ninguna clave es prefijo de otra: la familia de E3 coincide con la entidad",
        not prefijos,
        prefijos,
    )
    inf.check(
        "identidades distintas con el mismo sujeto real comparten clave",
        max(Counter(v for v in valores.values() if v).values(), default=0) > 1,
        dict(Counter(v for v in valores.values() if v)),
    )
    inf.check(
        "la ausencia se representa como null y no como cadena vacia",
        all(v is None or v != "" for v in valores.values()),
        None,
    )
    inf.check(
        "el canal NO repite custodia por item",
        all(isinstance(v, str | type(None)) for v in valores.values()),
        None,
    )


def _property_keys(corpus: dict[str, Any], canal: dict[str, Any], inf: Informe) -> None:
    ids = {i["id"] for i in corpus["items"]}
    valores = canal["valores"]
    inf.check(
        "cobertura total del canal lateral, null incluido",
        set(valores) == ids,
        {"faltan": sorted(ids - set(valores)), "sobran": sorted(set(valores) - ids)},
    )
    entidades = {e["id"]: e for e in corpus["entidades"]}
    esperado = {i["id"]: _property_key_oraculo(i, entidades) for i in corpus["items"]}
    inf.check("property_key coincide con el oraculo independiente", valores == esperado, None)
    presentes = [v for v in valores.values() if v]
    inf.check(
        "formato cerrado y opaco",
        all(S5.RX_PROPERTY_KEY.match(v) for v in presentes),
        presentes[:5],
    )
    frontera = {
        i["id"]
        for i in corpus["items"]
        if len(list(i.get("entity_ids") or [])) == 1 and _property_key_oraculo(i, entidades)
    }
    inf.check(
        "la frontera estructural es exactamente la declarada",
        {k for k, v in valores.items() if v} == frontera,
        None,
    )
    inf.check(
        "el canal NO repite custodia por item",
        all(isinstance(v, str | type(None)) for v in valores.values()),
        None,
    )


def _criticidad(corpus: dict[str, Any], canal: dict[str, Any], inf: Informe) -> None:
    ids = {i["id"] for i in corpus["items"]}
    valores = canal["valores"]
    inf.check("cobertura total de criticidad aplicada", set(valores) == ids, None)

    esperado: dict[str, dict[str, str] | None] = {}
    for item in corpus["items"]:
        bruta = item.get("criticidad")
        if not bruta:
            esperado[item["id"]] = None
            continue
        esperado[item["id"]] = {
            "nivel": bruta["nivel"],
            "razon_segura": bruta["razon"],
            "fuente_de_politica": S5.TABLA_FUENTE_DE_POLITICA[bruta["fuente"]],
            "regla_de_politica": bruta["regla"],
        }
    inf.check("la criticidad segura coincide con el oraculo", valores == esperado, None)

    seguros = [v for v in valores.values() if v]
    inf.check(
        "ningun campo seguro porta identificador de caso del banco",
        not [
            v
            for v in seguros
            for campo in ("razon_segura", "regla_de_politica")
            if S5.contiene_identificador_de_caso(v[campo])
        ],
        None,
    )
    bruto = json.dumps(canal, ensure_ascii=False)
    fuentes_brutas = {
        str(i["criticidad"]["fuente"]) for i in corpus["items"] if i.get("criticidad")
    }
    filtradas = sorted(f for f in fuentes_brutas if f in bruto)
    inf.check(
        "la fuente bruta NO cruza al artefacto comun",
        not filtradas,
        filtradas,
    )
    inf.check(
        "toda fuente de politica pertenece al vocabulario de Q21",
        all(v["fuente_de_politica"] in S5.FUENTES_DE_POLITICA for v in seguros),
        None,
    )
    inf.check(
        "no aparece ninguna etiqueta de candidato",
        not re.search(r"ADR002-[ABCD]\b", bruto),
        None,
    )

    censo = {
        "items": len(corpus["items"]),
        "sin_criticidad": sum(1 for v in valores.values() if v is None),
        "con_criticidad": len(seguros),
        "distribucion_por_nivel": dict(sorted(Counter(v["nivel"] for v in seguros).items())),
        "fuentes_de_politica": dict(
            sorted(
                {
                    p: sum(1 for v in seguros if v["fuente_de_politica"] == p)
                    for p in S5.FUENTES_DE_POLITICA
                }.items()
            )
        ),
        "razones_seguras_distintas": len({v["razon_segura"] for v in seguros}),
        "reglas_de_politica_distintas": len({v["regla_de_politica"] for v in seguros}),
    }
    inf.check(
        "censo de criticidad recomputado por el oraculo",
        censo == canal["censo"],
        {"declarado": canal["censo"], "recalculado": censo},
    )
    inf.check(
        "el censo NO reutiliza las constantes de la v0.4",
        censo["items"] != 95 or censo["sin_criticidad"] != 76,
        censo,
    )


# ===========================================================================
# 4. Anterioridad, frontera entrada/oraculo e inaccesibilidad
# ===========================================================================


def _anterioridad(inf: Informe) -> None:
    """Estructural: se inspeccionan **firmas**, no cadenas."""
    from experiments.adr002.benchmark import build_corpus_v0_5 as B5

    for nombre in (
        "construir_subject_keys",
        "construir_property_keys",
        "construir_criticidad_aplicada",
    ):
        firma = inspect.signature(getattr(B5, nombre))
        inf.check(
            f"{nombre} recibe el corpus y nada mas",
            list(firma.parameters) == ["corpus"],
            list(firma.parameters),
        )
    firma_casos = inspect.signature(B5.construir_casos)
    inf.check(
        "construir_casos no recibe ningun canal lateral: los consume, no los produce",
        "subject_keys" not in firma_casos.parameters
        and "property_keys" not in firma_casos.parameters,
        list(firma_casos.parameters),
    )
    inf.check(
        "el orden de materializacion declara los canales antes que casos y referencias",
        S5.ORDEN_DE_MATERIALIZACION.index("property_keys_v0_1.json")
        < S5.ORDEN_DE_MATERIALIZACION.index("cases_v0_5.json")
        and S5.ORDEN_DE_MATERIALIZACION.index("subject_keys_v0_1.json")
        < S5.ORDEN_DE_MATERIALIZACION.index("references_v0_5.json"),
        list(S5.ORDEN_DE_MATERIALIZACION),
    )


def _frontera_entrada_oraculo(artefactos: dict[str, Any], inf: Informe) -> None:
    caso = next(c for c in artefactos["cases_v0_5.json"]["nivel_4"] if c["id"] == "N4-01")
    inf.check(
        "el caso separa entrada y oraculo en bloques distintos",
        set(caso["entrada"])
        and set(caso["oraculo"])
        and not (set(caso["entrada"]) & set(caso["oraculo"])),
        {"entrada": sorted(caso["entrada"]), "oraculo": sorted(caso["oraculo"])},
    )
    entrada = json.dumps(caso["entrada"], ensure_ascii=False)
    prohibidos = [
        clave
        for clave in (
            "resultado_esperado",
            "elegibles",
            "prohibidos",
            "grupos_esperados",
            "parada_esperada",
            "etapa_esperada",
        )
        if clave in entrada
    ]
    inf.check("el bloque de entrada no lleva campo de oraculo", not prohibidos, prohibidos)
    for nombre in (
        "subject_keys_v0_1.json",
        "property_keys_v0_1.json",
        "applied_criticality_v0_1.json",
    ):
        crudo = json.dumps(artefactos[nombre], ensure_ascii=False)
        rastro = [c for c in ("N1-", "N4-01", "elegibles", "resultado_esperado") if c in crudo]
        inf.check(f"{nombre} no porta rastro de oraculo", not rastro, rastro)


def _inaccesibilidad(inf: Informe) -> None:
    """Lista blanca **por contencion**, nunca busqueda de ausencia de cadena."""
    from dataclasses import fields

    from experiments.adr002.candidates.common.contracts import ItemCanonico

    nombres = {f.name for f in fields(ItemCanonico)}
    inf.check(
        "los atributos entregados a un candidato estan contenidos en la lista blanca",
        nombres <= S5.ATRIBUTOS_PERMITIDOS_AL_CANDIDATO,
        sorted(nombres - S5.ATRIBUTOS_PERMITIDOS_AL_CANDIDATO),
    )
    inf.check(
        "ningun atributo vetado viaja en la estructura que recibe un candidato",
        not (nombres & S5.ATRIBUTOS_VETADOS_AL_CANDIDATO),
        sorted(nombres & S5.ATRIBUTOS_VETADOS_AL_CANDIDATO),
    )
    inf.check(
        "property_key no es legible por ningun candidato",
        not any(
            S5.legible_por("property_key", c)
            for c in ("ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D")
        ),
        None,
    )
    inf.check(
        "subject_key_experimental es legible por common y por A, y por nadie mas",
        S5.legible_por("subject_key_experimental", "common")
        and S5.legible_por("subject_key_experimental", "ADR002-A")
        and not S5.legible_por("subject_key_experimental", "ADR002-B"),
        None,
    )
    inf.check(
        "los cuatro campos de criticidad segura llegan a B05",
        all(S5.legible_por(c, "B05") for c in S5.CAMPOS_CRITICIDAD_APLICADA),
        None,
    )
    inf.check(
        "toda capacidad declarada pertenece al vocabulario cerrado",
        all(e["capacidad"] in S5.CAPACIDADES for e in S5.CLASIFICACION.values()),
        None,
    )
    try:
        S5.capacidad_de("campo_que_no_existe")
    except S5.ContratoFamiliaV05Error:
        inf.check("la clasificacion ABORTA ante un campo sin terna asignada", True, None)
    else:
        inf.check("la clasificacion ABORTA ante un campo sin terna asignada", False, None)


def _abortos_declarados(inf: Informe) -> None:
    """Los dos abortos se **provocan**: un control no ejercitado es una promesa."""
    from experiments.adr002.benchmark import build_corpus_v0_5 as B5

    corpus_falso = {
        "items": [
            {
                "id": "MEM-000",
                "text": "texto",
                "entity_ids": [],
                "criticidad": {
                    "nivel": "CRITICO",
                    "razon": "razon",
                    "fuente": "FUENTE-INVENTADA",
                    "regla": "CRIT-01",
                },
            }
        ]
    }
    try:
        B5.construir_criticidad_aplicada(corpus_falso)
    except S5.ContratoFamiliaV05Error:
        inf.check("la criticidad ABORTA ante una fuente fuera de la tabla cerrada", True, None)
    else:
        inf.check("la criticidad ABORTA ante una fuente fuera de la tabla cerrada", False, None)


# ===========================================================================
# 5. Discriminante, manifiesto y determinismo
# ===========================================================================


def _discriminante(artefactos: dict[str, Any], inf: Informe) -> None:
    corpus = artefactos["conformance_corpus_v0_5.json"]
    caso = next(c for c in artefactos["cases_v0_5.json"]["nivel_4"] if c["id"] == "N4-01")
    referencia = artefactos["references_v0_5.json"]["referencias_nivel_4"][0]

    inf.check(
        "caso y referencia coinciden en el alcance lexico",
        caso["oraculo"]["alcance_lexico_estructurado"] == referencia["alcance_lexico_estructurado"],
        {
            "caso": caso["oraculo"]["alcance_lexico_estructurado"],
            "referencia": referencia["alcance_lexico_estructurado"],
        },
    )
    inf.check(
        "el destino NO esta en el alcance lexico",
        S5.ITEM_DESTINO_DELTA not in caso["oraculo"]["alcance_lexico_estructurado"],
        caso["oraculo"]["alcance_lexico_estructurado"],
    )
    inf.check(
        "la semilla SI esta en el alcance lexico",
        S5.ITEM_ORIGEN_DELTA in caso["oraculo"]["alcance_lexico_estructurado"],
        caso["oraculo"]["alcance_lexico_estructurado"],
    )
    inf.check(
        "un salto relacional aporta el destino",
        caso["oraculo"]["aportado_por_un_salto_relacional"] == [S5.ITEM_DESTINO_DELTA],
        caso["oraculo"]["aportado_por_un_salto_relacional"],
    )
    inf.check(
        "sin la arista no hay aporte",
        caso["oraculo"]["sin_la_arista_no_hay_aporte"] == [],
        caso["oraculo"]["sin_la_arista_no_hay_aporte"],
    )
    inf.check(
        "el destino es recuperable por una consulta legitima propia",
        referencia["destino_recuperable_por_consulta_propia"] is True,
        None,
    )
    inf.check(
        "la cardinalidad del caso recorre la escalera entera",
        caso["entrada"]["peticion"]["cardinalidad"] == "EXHAUSTIVA",
        caso["entrada"]["peticion"]["cardinalidad"],
    )
    en_ambito = sum(1 for i in corpus["items"] if i["project_id"] == S5.PROYECTO_DELTA)
    inf.check(
        "el limite no puede ser la causa de que falte el destino",
        caso["entrada"]["peticion"]["limite_duro"] >= en_ambito,
        {"limite_duro": caso["entrada"]["peticion"]["limite_duro"], "en_ambito": en_ambito},
    )
    inf.check(
        "el caso declara expresamente que no mide rendimiento",
        {"latencia", "memoria"} <= set(caso["no_mide"]),
        caso["no_mide"],
    )


def _manifiesto(artefactos: dict[str, Any], inf: Informe) -> None:
    manifiesto = artefactos["benchmark_manifest_v0_5.json"]
    inf.check(
        "el manifiesto lista los siete sucesores",
        manifiesto["artefactos_sucesores"] == list(S5.CONGELABLES_V0_5),
        manifiesto["artefactos_sucesores"],
    )
    inf.check(
        "el manifiesto cierra tambien los heredados, por blob",
        set(manifiesto["custodia"]["heredados_por_blob"]) == set(S5.HEREDADOS_V0_5),
        sorted(manifiesto["custodia"]["heredados_por_blob"]),
    )
    inf.check(
        "el manifiesto aloja la custodia de los canales UNA SOLA VEZ",
        all(
            {"fuente_de_asignacion", "version_del_vocabulario", "regla_de_validacion"} <= set(canal)
            for canal in manifiesto["canales_laterales"].values()
        ),
        sorted(manifiesto["canales_laterales"]),
    )
    huellas = manifiesto["huellas_de_artefacto"]
    recalculadas = {
        nombre: hashlib.sha256(
            json.dumps(artefactos[nombre], ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        for nombre in S5.CONGELABLES_V0_5
        if nombre != "benchmark_manifest_v0_5.json"
    }
    inf.check("las huellas del manifiesto se recalculan", huellas == recalculadas, None)
    inf.check(
        "el manifiesto declara que NO regenera la proyeccion T0",
        manifiesto["proyeccion_t0"]["regenerada"] is False
        and manifiesto["proyeccion_t0"]["blob_observado"] == S5.PROYECCION_T0_BLOB_OBSERVADO,
        manifiesto["proyeccion_t0"],
    )
    inf.check(
        "el manifiesto no presupone el arnes de conformidad de T0",
        "NO EXISTE" in manifiesto["proyeccion_t0"]["arnes_de_conformidad_de_t0"],
        None,
    )
    inf.check(
        "el barrido de impacto declara cero cambios sobre los 66 dominios",
        manifiesto["delta_relacional"]["barrido_de_impacto"]["cambios"] == []
        and manifiesto["delta_relacional"]["barrido_de_impacto"]["adjudicaciones_recalculadas"]
        == S5.DOMINIOS_RECALCULADOS,
        manifiesto["delta_relacional"]["barrido_de_impacto"],
    )
    inf.check(
        "el rendimiento se hereda byte a byte y no se mide",
        manifiesto["rendimiento"]["blob"] == S5.BLOBS_V0_4["performance_corpus_v0_2.json"]
        and manifiesto["rendimiento"]["sha256"] == S5.SHA256_PERFORMANCE_V0_2,
        manifiesto["rendimiento"],
    )
    crudo = json.dumps(manifiesto, ensure_ascii=False)
    inf.check(
        "el manifiesto declara el benchmark bloqueado",
        "BLOQUEADO" in crudo and "NO EJECUTADO" in crudo,
        None,
    )
    inf.check(
        "los vocabularios P2 se declaran locales y no productivos",
        "NO se atribuyen a ADR-001" in manifiesto["vocabularios_p2"]["naturaleza"],
        None,
    )


def _herencia_intacta(artefactos: dict[str, Any], inf: Informe) -> None:
    """Los bloques heredados de casos y referencias, byte a byte."""
    casos_v0_4 = json.loads((AQUI / "cases_v0_4.json").read_text(encoding="utf-8"))
    refs_v0_4 = json.loads((AQUI / "references_v0_4.json").read_text(encoding="utf-8"))
    casos = artefactos["cases_v0_5.json"]
    refs = artefactos["references_v0_5.json"]
    for bloque in ("nivel_1", "nivel_1_pdp", "nivel_2", "nivel_3"):
        inf.check(
            f"el bloque heredado {bloque} no cambia",
            casos[bloque] == casos_v0_4[bloque],
            None,
        )
    inf.check(
        "las 52 referencias heredadas no cambian",
        refs["referencias_nivel_1"] == refs_v0_4["referencias_nivel_1"],
        None,
    )
    inf.check(
        "el corpus heredado conserva sus 95 items y 9 relaciones bajo el delta",
        len(artefactos["conformance_corpus_v0_5.json"]["items"]) == 97
        and len(artefactos["conformance_corpus_v0_5.json"]["relaciones"]) == 10,
        artefactos["conformance_corpus_v0_5.json"]["conteos"],
    )


def _determinismo(inf: Informe) -> None:
    from experiments.adr002.benchmark import build_corpus_v0_5 as B5

    with tempfile.TemporaryDirectory() as tmp:
        B5.escribir_en(Path(tmp))
        regenerados = cargar(Path(tmp))
    for nombre in S5.CONGELABLES_V0_5:
        ruta = AQUI / nombre
        if not ruta.exists():
            inf.check(f"determinismo de {nombre}", False, "artefacto ausente del arbol")
            continue
        inf.check(
            f"determinismo de {nombre}",
            json.loads(ruta.read_text(encoding="utf-8")) == regenerados[nombre],
            None,
        )


def _no_mutante(antes: dict[str, tuple[int, bytes]], inf: Informe) -> None:
    despues = {p.name: (p.stat().st_size, p.read_bytes()) for p in sorted(AQUI.glob("*.json"))}
    cambiados = sorted(k for k in antes if antes[k] != despues.get(k))
    inf.check("validar no modifica ningun artefacto del arbol", not cambiados, cambiados)


# ===========================================================================
# Entrada
# ===========================================================================


def validar() -> tuple[Informe, dict[str, Any]]:
    inf = Informe()
    antes = {p.name: (p.stat().st_size, p.read_bytes()) for p in sorted(AQUI.glob("*.json"))}
    artefactos = cargar()

    _v0_4_intacta(inf)
    _corpus(artefactos["conformance_corpus_v0_5.json"], inf)
    _delta(artefactos["conformance_corpus_v0_5.json"], inf)
    _subject_keys(
        artefactos["conformance_corpus_v0_5.json"], artefactos["subject_keys_v0_1.json"], inf
    )
    _property_keys(
        artefactos["conformance_corpus_v0_5.json"], artefactos["property_keys_v0_1.json"], inf
    )
    _criticidad(
        artefactos["conformance_corpus_v0_5.json"],
        artefactos["applied_criticality_v0_1.json"],
        inf,
    )
    _anterioridad(inf)
    _frontera_entrada_oraculo(artefactos, inf)
    _inaccesibilidad(inf)
    _abortos_declarados(inf)
    _discriminante(artefactos, inf)
    _herencia_intacta(artefactos, inf)
    _manifiesto(artefactos, inf)
    _determinismo(inf)
    _no_mutante(antes, inf)
    return inf, artefactos


def main() -> int:
    inf, _ = validar()
    resumen = {
        "documento": "Validacion de la familia sucesora de conformidad v0.5",
        "version_contrato": S5.VERSION_CONTRATO,
        "semantica": "acumula todos los fallos; los abortos declarados se provocan y se comprueban",
        "comprobaciones": len(inf.comprobaciones),
        "fallos": len(inf.fallos),
        "detalle": inf.comprobaciones,
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(resumen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"comprobaciones: {len(inf.comprobaciones)} · fallos: {len(inf.fallos)}")
    for fallo in inf.fallos:
        print(f"  FALLO {fallo['comprobacion']}: {fallo['detalle']}")
    return 1 if inf.fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
