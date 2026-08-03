"""Generador v0.6 · corrección mínima de `B04-CA-19` sobre la familia v0.5.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.build_corpus_v0_6

Materializa **cuatro** artefactos y ninguno más:

1. ``conformance_corpus_v0_6.json`` — v0.5 mas la entidad sintetica de `CA-19`
2. ``subject_keys_v0_2.json``       — regenerado con la regla ya aprobada
3. ``property_keys_v0_2.json``      — regenerado con la regla ya aprobada
4. ``benchmark_manifest_v0_6.json`` — cierre de la familia vigente

**La regla aprobada no se reescribe: se invoca.** ``construir_subject_keys`` y
``construir_property_keys`` son literalmente las funciones de
``build_corpus_v0_5``; aqui solo se les cambia la cabecera del artefacto. Las
claves iguales de `DEC-006`, `DEC-007` y `DEC-008` **no se escriben a mano**:
salen del generador determinista porque los tres declaran la misma entidad y
comparten el mismo texto.

``cases_v0_5.json``, ``references_v0_5.json``, ``applied_criticality_v0_1.json``
y el corpus de rendimiento se **heredan por blob** y no se regeneran.

No ejecuta T0, no implementa ni ejecuta ADR002-A/B/C/D, no mide rendimiento y no
autoriza ningun benchmark.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import build_corpus_v0_3 as B3
from experiments.adr002.benchmark import build_corpus_v0_4 as B4
from experiments.adr002.benchmark import build_corpus_v0_5 as B5
from experiments.adr002.benchmark import canonical_source_v0_4 as CS4
from experiments.adr002.benchmark import schema_v0_5 as S5
from experiments.adr002.benchmark import schema_v0_6 as S6

AQUI = Path(__file__).resolve().parent

FICHEROS = S6.CONGELABLES_V0_6


def _huella(datos: Any) -> str:
    return hashlib.sha256(
        json.dumps(datos, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


# ===========================================================================
# 1. Corpus de conformidad v0.6
# ===========================================================================


def entidad_de_ca_19() -> dict[str, Any]:
    """La entidad sintetica, sin alias y sin grupo homonimo.

    Sin alias porque el `property_key` resta del texto los tokens del sujeto:
    un alias inventado cambiaria el predicado resultante sin que ninguna fuente
    lo justifique. Sin grupo homonimo porque no lo tiene.
    """
    return {
        "id": S6.ENTIDAD_CA_19,
        "nombre_canonico": S6.NOMBRE_ENTIDAD_CA_19,
        "alias": [],
        "grupo_homonimo": None,
        "nota": S6.NOTA_ENTIDAD_CA_19,
    }


def construir_corpus_conformidad(canon: CS4.Canon) -> dict[str, Any]:
    """Corpus v0.5 regenerado **mas** la entidad de `CA-19`. Append-only."""
    base = B5.construir_corpus_conformidad(canon)
    corpus = copy.deepcopy(base)

    corpus["version"] = S6.VERSION_CORPUS_CONFORMIDAD
    corpus["version_contrato"] = S6.VERSION_CONTRATO
    corpus["generador"] = "experiments/adr002/benchmark/build_corpus_v0_6.py"
    corpus["hereda_de"] = "conformance_corpus_v0_5.json"
    corpus["correccion_v0_6"] = {
        "caso": S6.CASO_CORREGIDO,
        "defecto": S6.DEFECTO_V0_5,
        "entidad_anadida": S6.ENTIDAD_CA_19,
        "items_afectados": list(S6.ITEMS_CA_19),
        "justificacion": (
            "El texto identico de los tres items enuncia el concepto: "
            f"{S6.TEXTO_COMPARTIDO_CA_19!r}. La entidad nombra ese concepto y "
            "nada mas; no procede de casos, referencias ni adjudicaciones."
        ),
        "alcance": (
            "Un solo defecto. No se corrige nada mas, no se anaden items, no se "
            "tocan relaciones y no se regeneran casos ni referencias."
        ),
    }

    corpus["entidades"] = [*base["entidades"], entidad_de_ca_19()]

    afectados = set(S6.ITEMS_CA_19)
    vistos: set[str] = set()
    items: list[dict[str, Any]] = []
    for item in base["items"]:
        if item["id"] in afectados:
            if item["text"] != S6.TEXTO_COMPARTIDO_CA_19:
                raise S6.ContratoFamiliaV06Error(
                    f"{item['id']} no lleva el texto que justifica la entidad: {item['text']!r}"
                )
            if item["entity_ids"]:
                raise S6.ContratoFamiliaV06Error(
                    f"{item['id']} ya declaraba entidad en la v0.5: {item['entity_ids']}"
                )
            item = {**item, "entity_ids": [S6.ENTIDAD_CA_19]}
            vistos.add(item["id"])
        elif S6.ENTIDAD_CA_19 in (item.get("entity_ids") or []):
            raise S6.ContratoFamiliaV06Error(
                f"{item['id']} recibio la entidad de CA-19 sin ser uno de los tres"
            )
        items.append(item)
    if vistos != afectados:
        raise S6.ContratoFamiliaV06Error(
            f"faltan items de CA-19 en el corpus: {sorted(afectados - vistos)}"
        )
    corpus["items"] = items

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


def barrido_impacto_ca_19(base: dict[str, Any], corpus: dict[str, Any]) -> dict[str, Any]:
    """Recalcula los 66 dominios con y sin la entidad. **Exige cero cambios.**

    Es la condicion que permite heredar ``cases_v0_5.json`` y
    ``references_v0_5.json`` **por blob** en vez de regenerarlos: si alguna
    adjudicacion cambiara, heredarlos seria mentir.
    """
    dominios: dict[str, dict[str, Any]] = dict(B4.DOMINIOS)
    for (ca, sufijo), dominio in B4.DOMINIOS_RAMA.items():
        dominios[f"{ca}/{sufijo}"] = dominio

    cambios = [
        ident
        for ident, dominio in sorted(dominios.items())
        if B4.evaluar_universo(base, dominio) != B4.evaluar_universo(corpus, dominio)
    ]
    if cambios:
        raise S6.ContratoFamiliaV06Error(
            f"la entidad de CA-19 altero adjudicaciones heredadas: {cambios}"
        )
    if len(dominios) != S6.DOMINIOS_RECALCULADOS:
        raise S6.ContratoFamiliaV06Error(
            f"se esperaban {S6.DOMINIOS_RECALCULADOS} dominios y hay {len(dominios)}"
        )
    return {
        "adjudicaciones_recalculadas": len(dominios),
        "cambios": cambios,
        "regla": "ninguna adjudicacion heredada puede cambiar al anadir la entidad de CA-19",
        "razon_estructural": (
            "Los unicos dominios que filtran por entidad lo hacen contra "
            "ENT-PROY-ALFA, ENT-VEHICULO, ENT-POSTGRESQL o el grupo homonimo JUAN. "
            "Una entidad nueva sin grupo homonimo no coincide con ninguno, y el "
            "resto de dominios no mira entity_ids."
        ),
    }


# ===========================================================================
# 2. Canales laterales · la regla aprobada se INVOCA, no se reescribe
# ===========================================================================


def construir_subject_keys(corpus: dict[str, Any]) -> dict[str, Any]:
    """Regla aprobada de la v0.5, con la cabecera de esta familia."""
    canal = B5.construir_subject_keys(corpus)
    canal["version"] = "0.2"
    canal["version_contrato"] = S6.VERSION_CONTRATO
    canal["generador"] = "experiments/adr002/benchmark/build_corpus_v0_6.py"
    canal["hereda_de"] = "subject_keys_v0_1.json"
    canal["regla"] = "identica a la de la v0.5; se invoca, no se reescribe"
    return canal


def construir_property_keys(corpus: dict[str, Any]) -> dict[str, Any]:
    """Regla aprobada de la v0.5, con la cabecera de esta familia."""
    canal = B5.construir_property_keys(corpus)
    canal["version"] = "0.2"
    canal["version_contrato"] = S6.VERSION_CONTRATO
    canal["generador"] = "experiments/adr002/benchmark/build_corpus_v0_6.py"
    canal["hereda_de"] = "property_keys_v0_1.json"
    canal["regla"] = "identica a la de la v0.5; se invoca, no se reescribe"
    return canal


def fallos_de_agrupabilidad_ca_19(
    subject_keys: dict[str, Any], property_keys: dict[str, Any]
) -> list[str]:
    """`CA-19` agrupable: mismo sujeto no nulo y misma propiedad no nula."""
    fallos: list[str] = []
    sujetos = {i: subject_keys["valores"][i] for i in S6.ITEMS_CA_19}
    propiedades = {i: property_keys["valores"][i] for i in S6.ITEMS_CA_19}
    if len(set(sujetos.values())) != 1 or None in sujetos.values():
        fallos.append(f"los tres items de CA-19 no comparten sujeto no nulo: {sujetos}")
    if len(set(propiedades.values())) != 1 or None in propiedades.values():
        fallos.append(f"los tres items de CA-19 no comparten propiedad no nula: {propiedades}")
    return fallos


# ===========================================================================
# 3. Manifiesto sucesor
# ===========================================================================


def construir_manifiesto(
    corpus: dict[str, Any],
    subject_keys: dict[str, Any],
    property_keys: dict[str, Any],
    barrido: dict[str, Any],
) -> dict[str, Any]:
    """Cierra la familia vigente: lo versionado y lo heredado, por blob."""
    return {
        "documento": "Manifiesto de la familia sucesora de conformidad de ADR-002",
        "version_contrato": S6.VERSION_CONTRATO,
        "estado": S6.ESTADO_NO_CONGELADO,
        "semilla_compartida": S6.SEMILLA,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_6.py",
        "advertencia": (
            "Ninguna puerta de arranque queda satisfecha por este manifiesto. El "
            "benchmark permanece BLOQUEADO, NO AUTORIZADO y NO EJECUTADO. La ronda "
            "primaria sigue siendo T0 + A + B + C + D, sin reduccion."
        ),
        "correccion": {
            "caso": S6.CASO_CORREGIDO,
            "defecto_de_la_v0_5": S6.DEFECTO_V0_5,
            "entidad_anadida": S6.ENTIDAD_CA_19,
            "items_afectados": list(S6.ITEMS_CA_19),
            "alcance": "un solo defecto; nada mas se corrige",
        },
        "custodia": {
            "principio": "append-only",
            "familia_vigente": S6.VERSION_CONTRATO,
            "familia_sustituida": S5.VERSION_CONTRATO,
            "regla": (
                "La v0.6 se materializa JUNTO A la v0.5 y la v0.4. Ningun artefacto "
                "congelado de esas familias se sobrescribe, renombra ni modifica. La "
                "v0.5 permanece congelada como identidad historica y queda SUSTITUIDA "
                "como familia vigente."
            ),
            "v0_4_intacta_por_blob": dict(S6.BLOBS_V0_4),
            "v0_5_intacta_por_blob": dict(S6.BLOBS_V0_5),
            "heredados_por_blob": dict(S6.HEREDADOS_V0_6),
        },
        "artefactos_versionados": list(S6.CONGELABLES_V0_6),
        "orden_de_materializacion": list(S6.ORDEN_DE_MATERIALIZACION),
        "dependencias": {
            "conformance_corpus_v0_6.json": ["conformance_corpus_v0_5.json"],
            "subject_keys_v0_2.json": ["conformance_corpus_v0_6.json"],
            "property_keys_v0_2.json": ["conformance_corpus_v0_6.json"],
            "benchmark_manifest_v0_6.json": list(S6.CONGELABLES_V0_6[:-1]),
        },
        "anterioridad": (
            "Las dos funciones de canal lateral reciben por firma el corpus y nada "
            "mas: no pueden leer casos ni referencias porque no los tienen."
        ),
        "canales_laterales": {
            "property_key": {
                "fichero": "property_keys_v0_2.json",
                "fuente_de_asignacion": S6.FUENTE_DE_ASIGNACION_PROPERTY_KEY,
                "version_del_vocabulario": S6.VERSION_VOCABULARIO_PROPERTY_KEY,
                "regla_de_validacion": S6.REGLA_DE_VALIDACION_PROPERTY_KEY,
                "limitacion_declarada": S6.LIMITACION_PROPERTY_KEY,
                "conteos": property_keys["conteos"],
            },
            "subject_key_experimental": {
                "fichero": "subject_keys_v0_2.json",
                "fuente_de_asignacion": S6.FUENTE_DE_ASIGNACION_SUBJECT_KEY,
                "version_del_vocabulario": S6.VERSION_VOCABULARIO_SUBJECT_KEY,
                "regla_de_validacion": S6.REGLA_DE_VALIDACION_SUBJECT_KEY,
                "conteos": subject_keys["conteos"],
            },
        },
        "ca_19": {
            "items": list(S6.ITEMS_CA_19),
            "subject_key_experimental": subject_keys["valores"][S6.ITEMS_CA_19[0]],
            "property_key": property_keys["valores"][S6.ITEMS_CA_19[0]],
            "agrupable": True,
            "procedencias": {
                item["id"]: item["procedencia"]
                for item in corpus["items"]
                if item["id"] in set(S6.ITEMS_CA_19)
            },
        },
        "barrido_de_impacto": barrido,
        "discriminante_relacional": {
            "origen": S6.ITEM_ORIGEN_DELTA,
            "destino": S6.ITEM_DESTINO_DELTA,
            "relacion": S6.RELACION_DELTA,
            "tipo": S6.TIPO_RELACION_DELTA,
            "estado": "conservado sin cambio desde la v0.5",
        },
        "proyeccion_t0": {
            "regenerada": False,
            "fichero_no_regenerado": S6.PROYECCION_T0_NO_REGENERADA,
            "blob_observado": S6.PROYECCION_T0_BLOB_OBSERVADO,
            "valor": "observacion sin valor vinculante; no es evidencia congelada",
            "motivo": S6.PROYECCION_T0_MOTIVO,
            "arnes_de_conformidad_de_t0": "NO EXISTE; no se presupone y no se construye aqui",
        },
        "rendimiento": {
            "fichero": "performance_corpus_v0_2.json",
            "blob": S6.BLOBS_V0_4["performance_corpus_v0_2.json"],
            "regla": "heredado byte a byte; la familia v0.6 no mide rendimiento",
        },
        "conteos": {"corpus": corpus["conteos"]},
        "identidad_del_corpus": corpus["identidad"],
        "huellas_de_artefacto": {},
    }


# ===========================================================================
# 4. Construccion completa
# ===========================================================================


def construir_todo() -> dict[str, dict[str, Any]]:
    """Los cuatro artefactos versionados, en el orden declarado."""
    canon = CS4.cargar_canon()
    base = B5.construir_corpus_conformidad(canon)
    corpus = construir_corpus_conformidad(canon)
    barrido = barrido_impacto_ca_19(base, corpus)
    subject_keys = construir_subject_keys(corpus)
    property_keys = construir_property_keys(corpus)
    if fallos := fallos_de_agrupabilidad_ca_19(subject_keys, property_keys):
        raise S6.ContratoFamiliaV06Error("; ".join(fallos))
    manifiesto = construir_manifiesto(corpus, subject_keys, property_keys, barrido)
    artefactos: dict[str, dict[str, Any]] = {
        "conformance_corpus_v0_6.json": corpus,
        "subject_keys_v0_2.json": subject_keys,
        "property_keys_v0_2.json": property_keys,
        "benchmark_manifest_v0_6.json": manifiesto,
    }
    manifiesto["huellas_de_artefacto"] = {
        nombre: _huella(datos)
        for nombre, datos in artefactos.items()
        if nombre != "benchmark_manifest_v0_6.json"
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
