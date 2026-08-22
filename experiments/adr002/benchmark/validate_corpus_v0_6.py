"""Validador v0.6 · corrección mínima de `B04-CA-19`.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.validate_corpus_v0_6

**Regla de independencia.** No importa ni reutiliza las funciones de cierre de
``build_corpus_v0_6`` ni de ``build_corpus_v0_5``. El oraculo propio es el de
``validate_corpus_v0_5`` —normalizacion, slug, tokenizacion del indice real y
reconstruccion de ``property_key``—, que ya se escribio de forma independiente
del generador y aqui se reutiliza como tal. El generador solo se importa dentro
de la comprobacion de determinismo y de la de anterioridad, que inspecciona
**firmas** y no comportamiento.

**Semantica declarada.** El informe **acumula** todos los fallos y **no aborta
en el primero**. Los puntos en los que la construccion si aborta —un item de
`CA-19` con otro texto, la entidad asignada a un cuarto item, o un cambio de
adjudicacion heredada— se comprueban **provocandolos** en las pruebas.

El unico fichero que escribe es su propio informe, y solo desde ``main()``. No
ejecuta T0, no implementa ni ejecuta ADR002-A/B/C/D y no mide rendimiento.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import schema_v0_6 as S6
from experiments.adr002.benchmark import validate_corpus_v0_5 as V5

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
SALIDA = RAIZ / "artifacts" / "adr002_benchmark_preparation" / "validacion_familia_v0.6.json"

Informe = V5.Informe


def cargar(directorio: Path | None = None) -> dict[str, Any]:
    base = directorio or AQUI
    return {n: json.loads((base / n).read_text(encoding="utf-8")) for n in S6.CONGELABLES_V0_6}


# ===========================================================================
# 1. Custodia append-only: v0.4 y v0.5 intactas, heredados por blob
# ===========================================================================


def _familias_anteriores_intactas(inf: Informe) -> None:
    for etiqueta, blobs in (("v0.4", S6.BLOBS_V0_4), ("v0.5", S6.BLOBS_V0_5)):
        for nombre, esperado in blobs.items():
            ruta = AQUI / nombre
            observado = V5._blob_git(ruta.read_bytes()) if ruta.exists() else "AUSENTE"
            inf.check(
                f"{etiqueta} intacta byte a byte: {nombre}",
                observado == esperado,
                {"observado": observado, "esperado": esperado},
            )
    inf.check(
        "ningun artefacto de la v0.6 reutiliza el nombre de uno congelado",
        not (set(S6.CONGELABLES_V0_6) & (set(S6.BLOBS_V0_4) | set(S6.BLOBS_V0_5))),
        sorted(set(S6.CONGELABLES_V0_6) & (set(S6.BLOBS_V0_4) | set(S6.BLOBS_V0_5))),
    )


def _heredados_por_blob(inf: Informe) -> None:
    for nombre, esperado in S6.HEREDADOS_V0_6.items():
        ruta = AQUI / nombre
        observado = V5._blob_git(ruta.read_bytes()) if ruta.exists() else "AUSENTE"
        inf.check(
            f"heredado por blob sin regenerar: {nombre}",
            observado == esperado,
            {"observado": observado, "esperado": esperado},
        )
    inf.check(
        "la v0.6 no versiona casos, referencias ni criticidad",
        not {"cases_v0_6.json", "references_v0_6.json", "applied_criticality_v0_2.json"}
        & set(S6.CONGELABLES_V0_6),
        list(S6.CONGELABLES_V0_6),
    )


# ===========================================================================
# 2. Corpus sucesor
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
        "el corpus declara version de contrato 0.6",
        corpus["version_contrato"] == S6.VERSION_CONTRATO,
        corpus["version_contrato"],
    )
    inf.check("la semilla no cambia", corpus["semilla"] == S6.SEMILLA, corpus["semilla"])

    v0_5 = json.loads((AQUI / "conformance_corpus_v0_5.json").read_text(encoding="utf-8"))
    inf.check(
        "el corpus v0.6 no anade ni quita items respecto de la v0.5",
        len(items) == len(v0_5["items"]),
        {"v0.5": len(v0_5["items"]), "v0.6": len(items)},
    )
    inf.check(
        "el corpus v0.6 no toca relaciones, mensajes, documentos ni proyectos",
        corpus["relaciones"] == v0_5["relaciones"]
        and corpus["mensajes"] == v0_5["mensajes"]
        and corpus["documentos"] == v0_5["documentos"]
        and corpus["proyectos"] == v0_5["proyectos"],
        None,
    )
    afectados = set(S6.ITEMS_CA_19)
    por_id_5 = {i["id"]: i for i in v0_5["items"]}
    distintos = [i["id"] for i in items if i["id"] not in afectados and i != por_id_5.get(i["id"])]
    inf.check(
        "ningun item ajeno a CA-19 cambia un solo byte",
        not distintos,
        distintos,
    )
    solo_entidad = [
        i["id"]
        for i in items
        if i["id"] in afectados and {**i, "entity_ids": []} != por_id_5.get(i["id"])
    ]
    inf.check(
        "en los tres de CA-19 lo unico que cambia es entity_ids",
        not solo_entidad,
        solo_entidad,
    )


# ===========================================================================
# 3. El defecto corregido
# ===========================================================================


def _ca_19(
    corpus: dict[str, Any],
    subject_keys: dict[str, Any],
    property_keys: dict[str, Any],
    inf: Informe,
) -> None:
    entidades = {e["id"]: e for e in corpus["entidades"]}
    inf.check(
        "la entidad sintetica existe y es unica",
        sum(1 for e in corpus["entidades"] if e["id"] == S6.ENTIDAD_CA_19) == 1,
        S6.ENTIDAD_CA_19,
    )
    entidad = entidades.get(S6.ENTIDAD_CA_19)
    if entidad is not None:
        inf.check(
            "la entidad no declara alias ni grupo homonimo",
            entidad["alias"] == [] and entidad["grupo_homonimo"] is None,
            entidad,
        )
        inf.check(
            "el nombre canonico es el concepto que los tres enuncian",
            entidad["nombre_canonico"] == S6.NOMBRE_ENTIDAD_CA_19,
            entidad["nombre_canonico"],
        )

    portadores = sorted(
        i["id"] for i in corpus["items"] if S6.ENTIDAD_CA_19 in (i.get("entity_ids") or [])
    )
    inf.check(
        "la entidad se asigna EXCLUSIVAMENTE a los tres items de CA-19",
        portadores == sorted(S6.ITEMS_CA_19),
        portadores,
    )
    afectados = [i for i in corpus["items"] if i["id"] in set(S6.ITEMS_CA_19)]
    inf.check(
        "los tres comparten el texto que justifica la entidad",
        all(i["text"] == S6.TEXTO_COMPARTIDO_CA_19 for i in afectados),
        [i["text"] for i in afectados],
    )
    procedencias = {i["id"]: tuple(i["procedencia"]) for i in afectados}
    inf.check(
        "CA-19 conserva sus tres procedencias distintas",
        len(set(procedencias.values())) == 3 and all(procedencias.values()),
        procedencias,
    )

    sujetos = {i: subject_keys["valores"][i] for i in S6.ITEMS_CA_19}
    propiedades = {i: property_keys["valores"][i] for i in S6.ITEMS_CA_19}
    inf.check(
        "los tres comparten subject_key_experimental NO nula",
        len(set(sujetos.values())) == 1 and None not in sujetos.values(),
        sujetos,
    )
    inf.check(
        "los tres comparten property_key NO nula",
        len(set(propiedades.values())) == 1 and None not in propiedades.values(),
        propiedades,
    )
    inf.check(
        "CA-19 es estructuralmente agrupable: ningun eje queda desconocido",
        len(set(sujetos.values())) == 1
        and len(set(propiedades.values())) == 1
        and None not in sujetos.values()
        and None not in propiedades.values(),
        {"sujeto": next(iter(sujetos.values())), "propiedad": next(iter(propiedades.values()))},
    )

    v0_5_sk = json.loads((AQUI / "subject_keys_v0_1.json").read_text(encoding="utf-8"))["valores"]
    v0_5_pk = json.loads((AQUI / "property_keys_v0_1.json").read_text(encoding="utf-8"))["valores"]
    inf.check(
        "en la v0.5 los tres tenian ambas claves nulas: el defecto era real",
        all(v0_5_sk[i] is None and v0_5_pk[i] is None for i in S6.ITEMS_CA_19),
        {i: (v0_5_sk[i], v0_5_pk[i]) for i in S6.ITEMS_CA_19},
    )
    otros = [
        i
        for i in subject_keys["valores"]
        if i not in set(S6.ITEMS_CA_19) and subject_keys["valores"][i] != v0_5_sk[i]
    ]
    inf.check(
        "ninguna clave de sujeto ajena a CA-19 cambia respecto de la v0.5",
        not otros,
        otros,
    )
    otros_pk = [
        i
        for i in property_keys["valores"]
        if i not in set(S6.ITEMS_CA_19) and property_keys["valores"][i] != v0_5_pk[i]
    ]
    inf.check(
        "ninguna property_key ajena a CA-19 cambia respecto de la v0.5",
        not otros_pk,
        otros_pk,
    )


# ===========================================================================
# 4. Canales laterales, con oraculo independiente
# ===========================================================================


def _canales(
    corpus: dict[str, Any],
    subject_keys: dict[str, Any],
    property_keys: dict[str, Any],
    inf: Informe,
) -> None:
    ids = {i["id"] for i in corpus["items"]}
    for nombre, canal in (("sujeto", subject_keys), ("propiedad", property_keys)):
        inf.check(
            f"cobertura total del canal de {nombre}, null incluido",
            set(canal["valores"]) == ids,
            {"faltan": sorted(ids - set(canal["valores"]))},
        )

    nombres = {e["id"]: e["nombre_canonico"] for e in corpus["entidades"]}
    esperado_sk = {}
    for item in corpus["items"]:
        declaradas = list(item.get("entity_ids") or [])
        esperado_sk[item["id"]] = V5._slug(nombres[declaradas[0]]) if len(declaradas) == 1 else None
    inf.check(
        "la proyeccion de sujeto coincide con el oraculo independiente",
        subject_keys["valores"] == esperado_sk,
        None,
    )
    entidades = {e["id"]: e for e in corpus["entidades"]}
    esperado_pk = {i["id"]: V5._property_key_oraculo(i, entidades) for i in corpus["items"]}
    inf.check(
        "property_key coincide con el oraculo independiente",
        property_keys["valores"] == esperado_pk,
        None,
    )
    presentes = sorted({v for v in subject_keys["valores"].values() if v})
    inf.check(
        "toda clave de sujeto respeta el formato cerrado",
        all(S6.RX_SUBJECT_KEY.match(v) for v in presentes),
        presentes,
    )
    prefijos = [(a, b) for a in presentes for b in presentes if a != b and b.startswith(a)]
    inf.check(
        "ninguna clave de sujeto es prefijo de otra",
        not prefijos,
        prefijos,
    )
    inf.check(
        "toda property_key presente respeta el formato cerrado y opaco",
        all(S6.RX_PROPERTY_KEY.match(v) for v in property_keys["valores"].values() if v),
        None,
    )
    inf.check(
        "la ausencia sigue siendo null y no cadena vacia",
        "" not in subject_keys["valores"].values() and "" not in property_keys["valores"].values(),
        None,
    )


def _anterioridad(inf: Informe) -> None:
    from experiments.adr002.benchmark import build_corpus_v0_6 as B6

    for nombre in ("construir_subject_keys", "construir_property_keys"):
        firma = inspect.signature(getattr(B6, nombre))
        inf.check(
            f"{nombre} recibe el corpus y nada mas",
            list(firma.parameters) == ["corpus"],
            list(firma.parameters),
        )
    inf.check(
        "el orden de materializacion declara los canales antes del manifiesto",
        S6.ORDEN_DE_MATERIALIZACION.index("subject_keys_v0_2.json")
        < S6.ORDEN_DE_MATERIALIZACION.index("benchmark_manifest_v0_6.json"),
        list(S6.ORDEN_DE_MATERIALIZACION),
    )
    for nombre in ("subject_keys_v0_2.json", "property_keys_v0_2.json"):
        crudo = (AQUI / nombre).read_text(encoding="utf-8")
        rastro = [c for c in ("N1-", "N4-01", "elegibles", "resultado_esperado") if c in crudo]
        inf.check(f"{nombre} no porta rastro de oraculo", not rastro, rastro)


# ===========================================================================
# 5. El discriminante relacional sigue en pie
# ===========================================================================


def _discriminante(corpus: dict[str, Any], subject_keys: dict[str, Any], inf: Informe) -> None:
    v0_5 = json.loads((AQUI / "conformance_corpus_v0_5.json").read_text(encoding="utf-8"))
    por_id_6 = {i["id"]: i for i in corpus["items"]}
    por_id_5 = {i["id"]: i for i in v0_5["items"]}
    for ident in (S6.ITEM_ORIGEN_DELTA, S6.ITEM_DESTINO_DELTA):
        inf.check(
            f"{ident} identico al de la v0.5",
            por_id_6.get(ident) == por_id_5.get(ident),
            None,
        )
    arista_6 = next((r for r in corpus["relaciones"] if r["id"] == S6.RELACION_DELTA), None)
    arista_5 = next((r for r in v0_5["relaciones"] if r["id"] == S6.RELACION_DELTA), None)
    inf.check("la arista discriminante es identica a la de la v0.5", arista_6 == arista_5, arista_6)

    origen, destino = por_id_6[S6.ITEM_ORIGEN_DELTA], por_id_6[S6.ITEM_DESTINO_DELTA]
    compartidos = V5._terminos_del_indice([origen["text"]]) & V5._terminos_del_indice(
        [destino["text"]]
    )
    inf.check(
        "los extremos siguen sin compartir un solo token indexado",
        not compartidos,
        sorted(compartidos),
    )
    v0_5_sk = json.loads((AQUI / "subject_keys_v0_1.json").read_text(encoding="utf-8"))["valores"]
    inf.check(
        "las claves de sujeto de los extremos no cambian",
        subject_keys["valores"][S6.ITEM_ORIGEN_DELTA] == v0_5_sk[S6.ITEM_ORIGEN_DELTA]
        and subject_keys["valores"][S6.ITEM_DESTINO_DELTA] == v0_5_sk[S6.ITEM_DESTINO_DELTA],
        {
            "origen": subject_keys["valores"][S6.ITEM_ORIGEN_DELTA],
            "destino": subject_keys["valores"][S6.ITEM_DESTINO_DELTA],
        },
    )
    salto = sorted(
        {
            r["destino"]
            for r in corpus["relaciones"]
            if r["origen"] == S6.ITEM_ORIGEN_DELTA and r["destino"] != S6.ITEM_ORIGEN_DELTA
        }
    )
    inf.check(
        "un salto relacional sigue aportando el destino",
        salto == [S6.ITEM_DESTINO_DELTA],
        salto,
    )


# ===========================================================================
# 6. Manifiesto, determinismo y no mutacion
# ===========================================================================


def _manifiesto(artefactos: dict[str, Any], inf: Informe) -> None:
    manifiesto = artefactos["benchmark_manifest_v0_6.json"]
    inf.check(
        "el manifiesto lista lo versionado",
        manifiesto["artefactos_versionados"] == list(S6.CONGELABLES_V0_6),
        manifiesto["artefactos_versionados"],
    )
    inf.check(
        "el manifiesto cierra los heredados por blob",
        manifiesto["custodia"]["heredados_por_blob"] == dict(S6.HEREDADOS_V0_6),
        None,
    )
    inf.check(
        "el manifiesto declara la v0.5 sustituida y la v0.6 vigente",
        manifiesto["custodia"]["familia_vigente"] == S6.VERSION_CONTRATO
        and manifiesto["custodia"]["familia_sustituida"] == "0.5",
        manifiesto["custodia"],
    )
    inf.check(
        "el manifiesto registra el defecto corregido",
        manifiesto["correccion"]["caso"] == S6.CASO_CORREGIDO
        and manifiesto["correccion"]["items_afectados"] == list(S6.ITEMS_CA_19),
        manifiesto["correccion"],
    )
    inf.check(
        "el manifiesto declara CA-19 agrupable con claves no nulas",
        manifiesto["ca_19"]["agrupable"] is True
        and manifiesto["ca_19"]["subject_key_experimental"]
        and manifiesto["ca_19"]["property_key"],
        manifiesto["ca_19"],
    )
    inf.check(
        "el barrido declara cero cambios sobre los 66 dominios",
        manifiesto["barrido_de_impacto"]["cambios"] == []
        and manifiesto["barrido_de_impacto"]["adjudicaciones_recalculadas"]
        == S6.DOMINIOS_RECALCULADOS,
        manifiesto["barrido_de_impacto"],
    )
    recalculadas = {
        nombre: hashlib.sha256(
            json.dumps(artefactos[nombre], ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        for nombre in S6.CONGELABLES_V0_6
        if nombre != "benchmark_manifest_v0_6.json"
    }
    inf.check(
        "las huellas del manifiesto se recalculan",
        manifiesto["huellas_de_artefacto"] == recalculadas,
        None,
    )
    inf.check(
        "el manifiesto sigue declarando el benchmark bloqueado",
        "BLOQUEADO" in json.dumps(manifiesto, ensure_ascii=False)
        and "NO EJECUTADO" in json.dumps(manifiesto, ensure_ascii=False),
        None,
    )
    inf.check(
        "la proyeccion T0 sigue sin regenerarse",
        manifiesto["proyeccion_t0"]["regenerada"] is False,
        manifiesto["proyeccion_t0"],
    )


def _determinismo(inf: Informe) -> None:
    from experiments.adr002.benchmark import build_corpus_v0_6 as B6

    with tempfile.TemporaryDirectory() as tmp:
        B6.escribir_en(Path(tmp))
        regenerados = cargar(Path(tmp))
    for nombre in S6.CONGELABLES_V0_6:
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
    corpus = artefactos["conformance_corpus_v0_6.json"]
    subject_keys = artefactos["subject_keys_v0_2.json"]
    property_keys = artefactos["property_keys_v0_2.json"]

    _familias_anteriores_intactas(inf)
    _heredados_por_blob(inf)
    _corpus(corpus, inf)
    _ca_19(corpus, subject_keys, property_keys, inf)
    _canales(corpus, subject_keys, property_keys, inf)
    _anterioridad(inf)
    _discriminante(corpus, subject_keys, inf)
    _manifiesto(artefactos, inf)
    _determinismo(inf)
    _no_mutante(antes, inf)
    return inf, artefactos


def main() -> int:
    inf, _ = validar()
    resumen = {
        "documento": "Validacion de la familia sucesora de conformidad v0.6",
        "version_contrato": S6.VERSION_CONTRATO,
        "defecto_corregido": S6.CASO_CORREGIDO,
        "semantica": "acumula todos los fallos; no aborta en el primero",
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
