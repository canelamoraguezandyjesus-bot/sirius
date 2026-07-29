"""Esquema y validador del futuro artefacto ``suelo_medicion_v0.1.json``.

Se congela en la fase A, ANTES de que exista ninguna observacion, para que
el contrato que la evidencia debe cumplir no pueda escribirse despues de
verla. El validador no mide, no lee ficheros y no ejecuta nada al
importarse: recibe el documento ya cargado y devuelve la lista de fallos.

Falla cerrado: una seccion ausente es un fallo, nunca una omision
tolerada. Si algun control bloqueante falla, el documento no puede
publicar SM, B50, B95, B ni U.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from experiments.adr002.tolerances import floor_protocol as fp

VERSION_ESQUEMA: Final = fp.VERSION_ESQUEMA

#: Secciones de primer nivel exigidas al artefacto.
SECCIONES_OBLIGATORIAS: Final[tuple[str, ...]] = (
    "documento",
    "version_esquema",
    "estado",
    "protocolo",
    "preinscripcion",
    "entorno",
    "procesos",
    "sondas",
    "diagnosticos",
    "controles_internos",
    "derivacion",
    "regimenes_por_percentil",
    "clasificacion_diagnostica_linea_base",
    "custodia",
    "no_autoriza",
)

CAMPOS_PREINSCRIPCION: Final[tuple[str, ...]] = (
    "commit_a",
    "blobs_preinscritos",
    "blob_arnes",
    "blobs_corpus_congelado",
    "blob_protocolo",
)

CAMPOS_ENTORNO: Final[tuple[str, ...]] = (
    "captura_inicial",
    "captura_final",
    "boot_id",
    "carga_por_proceso",
    "incidencias",
)

CAMPOS_DERIVACION: Final[tuple[str, ...]] = (
    "sm_ns",
    "b50_ns",
    "b95_ns",
    "b_ns",
    "u_ns",
    "m",
    "descomposicion_b",
)

CAMPOS_MEDIDA_SONDA: Final[tuple[str, ...]] = (
    "sonda",
    "pid",
    "n",
    "warmup_descartado",
    "muestras_ns",
    "p50_ns",
    "p95_ns",
    "p99_ns",
    "min_ns",
    "max_ns",
    "resolucion_percentil",
)

#: Lo que el artefacto debe negar explicitamente.
NEGACIONES_OBLIGATORIAS: Final[tuple[str, ...]] = (
    "limite_duro_tol_107",
    "aprobacion_tol_209",
)


def _es_entero(valor: Any) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _fallos_secciones(doc: Mapping[str, Any]) -> list[str]:
    return [f"falta la seccion obligatoria: {s}" for s in SECCIONES_OBLIGATORIAS if s not in doc]


def _fallos_preinscripcion(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    pre = doc.get("preinscripcion")
    if not isinstance(pre, Mapping):
        return ["preinscripcion ausente o con forma invalida"]

    fallos.extend(f"preinscripcion sin campo {c}" for c in CAMPOS_PREINSCRIPCION if c not in pre)

    blobs = pre.get("blobs_preinscritos")
    if isinstance(blobs, Mapping):
        for ruta in fp.ARCHIVOS_PREINSCRITOS:
            if ruta not in blobs:
                fallos.append(f"blob preinscrito ausente: {ruta}")
    elif "blobs_preinscritos" in pre:
        fallos.append("blobs_preinscritos debe ser un mapa ruta -> blob")

    congelados = pre.get("blobs_corpus_congelado")
    if isinstance(congelados, Mapping):
        for ruta, esperado in fp.BLOBS_CORPUS_CONGELADO.items():
            if ruta not in congelados:
                fallos.append(f"blob congelado ausente: {ruta}")
            elif congelados[ruta] != esperado:
                fallos.append(f"blob congelado alterado: {ruta}")
    elif "blobs_corpus_congelado" in pre:
        fallos.append("blobs_corpus_congelado debe ser un mapa ruta -> blob")

    if pre.get("blob_protocolo") not in (None, fp.BLOB_PROTOCOLO_APROBADO):
        fallos.append("el blob del protocolo aprobado no coincide")

    return fallos


def _fallos_una_medida(medida: Mapping[str, Any], indice: int) -> list[str]:
    fallos: list[str] = []
    etiqueta = f"sondas[{indice}]"

    for campo in CAMPOS_MEDIDA_SONDA:
        if campo not in medida:
            fallos.append(f"{etiqueta} sin campo {campo}")
    if fallos:
        return fallos

    muestras = medida["muestras_ns"]
    if not isinstance(muestras, Sequence) or isinstance(muestras, str | bytes):
        return [f"{etiqueta}: muestras_ns debe ser una secuencia"]
    if not muestras:
        return [f"{etiqueta}: vector de muestras vacio"]
    if not all(_es_entero(x) for x in muestras):
        fallos.append(f"{etiqueta}: las muestras deben ser enteros en nanosegundos")
        return fallos

    valores = [int(x) for x in muestras]
    n_declarado = medida["n"]
    if not _es_entero(n_declarado) or int(n_declarado) != len(valores):
        fallos.append(f"{etiqueta}: n declarado ({n_declarado!r}) != longitud del vector")

    # Redondeo previo: multiplos exactos de 100 ns en todo el vector es la
    # firma del ``round(..., 4)`` en milisegundos del arnes historico.
    if len(valores) >= 2 and all(v % 100 == 0 for v in valores) and len(set(valores)) > 1:
        fallos.append(f"{etiqueta}: vector redondeado antes de persistirse")

    ordenadas = sorted(valores)
    esperados = {
        "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
        "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
        "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
        "min_ns": ordenadas[0],
        "max_ns": ordenadas[-1],
    }
    for campo, esperado in esperados.items():
        if medida[campo] != esperado:
            fallos.append(
                f"{etiqueta}: {campo} publicado {medida[campo]!r} != nearest-rank {esperado}"
            )

    if medida["sonda"] in fp.F_NORMATIVO and int(n_declarado) < fp.N_SONDA_F:
        fallos.append(f"{etiqueta}: n={n_declarado} por debajo del minimo {fp.N_SONDA_F}")

    warmup = medida["warmup_descartado"]
    if not _es_entero(warmup) or int(warmup) < 0:
        fallos.append(f"{etiqueta}: warmup_descartado invalido")

    return fallos


def _fallos_sondas(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    sondas = doc.get("sondas")
    if not isinstance(sondas, Sequence) or isinstance(sondas, str | bytes):
        return ["sondas ausente o con forma invalida"]

    medidas = [m for m in sondas if isinstance(m, Mapping)]
    if len(medidas) != len(sondas):
        fallos.append("cada entrada de sondas debe ser un objeto")

    nombres = {str(m.get("sonda")) for m in medidas}
    intrusos = sorted(n for n in nombres if n not in fp.F_NORMATIVO)
    if intrusos:
        fallos.append(f"diagnosticos dentro de F: {intrusos}")
    faltan = sorted(s for s in fp.F_NORMATIVO if s not in nombres)
    if faltan:
        fallos.append(f"faltan sondas normativas: {faltan}")

    for sonda in fp.F_NORMATIVO:
        pids = {m.get("pid") for m in medidas if m.get("sonda") == sonda}
        if 0 < len(pids) < fp.PROCESOS_MINIMOS:
            fallos.append(
                f"{sonda}: {len(pids)} procesos distintos; el minimo es {fp.PROCESOS_MINIMOS}"
            )

    for indice, medida in enumerate(medidas):
        fallos.extend(_fallos_una_medida(medida, indice))

    return fallos


def _fallos_derivacion(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    der = doc.get("derivacion")
    if not isinstance(der, Mapping):
        return ["derivacion ausente o con forma invalida"]

    fallos.extend(f"derivacion sin campo {c}" for c in CAMPOS_DERIVACION if c not in der)
    if fallos:
        return fallos

    for campo in ("sm_ns", "b50_ns", "b95_ns", "b_ns", "u_ns"):
        if not _es_entero(der[campo]):
            fallos.append(f"derivacion.{campo} debe ser un entero en nanosegundos")
    if fallos:
        return fallos

    b50, b95, b, u = int(der["b50_ns"]), int(der["b95_ns"]), int(der["b_ns"]), int(der["u_ns"])

    if der["m"] != fp.MARGEN_M:
        fallos.append(f"m debe ser {fp.MARGEN_M}; se publico {der['m']!r}")
    if b != max(b50, b95):
        fallos.append(f"B debe ser max(B50, B95) = {max(b50, b95)}; se publico {b}")
    if u != fp.FACTOR_U * b:
        fallos.append(f"U debe ser {fp.FACTOR_U} * B = {fp.FACTOR_U * b}; se publico {u}")

    descomposicion = der.get("descomposicion_b")
    if not isinstance(descomposicion, Mapping):
        fallos.append("descomposicion_b ausente: B debe publicarse por sonda y percentil")
    else:
        for sonda in fp.F_NORMATIVO:
            entrada = descomposicion.get(sonda)
            if not isinstance(entrada, Mapping):
                fallos.append(f"descomposicion_b sin la sonda {sonda}")
            elif "b50_ns" not in entrada or "b95_ns" not in entrada:
                fallos.append(f"descomposicion_b[{sonda}] sin b50_ns y b95_ns")

    if "banda_absoluta_secundaria" in der or "b_p50_normativa" in der:
        fallos.append("dos bandas normativas separadas: solo se admite una banda B")

    return fallos


def _fallos_regimenes(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    regimenes = doc.get("regimenes_por_percentil")
    if not isinstance(regimenes, Sequence) or isinstance(regimenes, str | bytes):
        return ["regimenes_por_percentil ausente o con forma invalida"]

    for indice, entrada in enumerate(regimenes):
        if not isinstance(entrada, Mapping):
            fallos.append(f"regimenes_por_percentil[{indice}] debe ser un objeto")
            continue
        etiqueta = f"regimenes_por_percentil[{indice}]"
        if entrada.get("resultado") == fp.NO_EVALUABLE:
            continue
        r50, r95 = entrada.get("p50"), entrada.get("p95")
        validos = {fp.REGIMEN_RELATIVO, fp.REGIMEN_ABSOLUTO}
        if r50 not in validos or r95 not in validos:
            fallos.append(f"{etiqueta}: regimen por percentil ausente o invalido")
            continue
        if r50 == fp.REGIMEN_RELATIVO and r95 == fp.REGIMEN_ABSOLUTO:
            fallos.append(f"{etiqueta}: combinacion imposible P50 relativo / P95 absoluto")
        min50 = entrada.get("min_p50_ns")
        min95 = entrada.get("min_p95_ns")
        if isinstance(min50, int) and isinstance(min95, int) and min95 < min50:
            fallos.append(f"{etiqueta}: invariante violado min_s P95 < min_s P50")

    return fallos


def _fallos_controles(doc: Mapping[str, Any]) -> list[str]:
    controles = doc.get("controles_internos")
    if not isinstance(controles, Mapping):
        return ["controles_internos ausente o con forma invalida"]

    fallos = [
        f"control bloqueante ausente: {c}" for c in fp.CONTROLES_BLOQUEANTES if c not in controles
    ]
    fallidos = [c for c in fp.CONTROLES_BLOQUEANTES if controles.get(c) is False]
    if fallidos and "derivacion" in doc:
        fallos.append(
            f"se publicaron valores con controles bloqueantes fallidos: {sorted(fallidos)}"
        )
    return fallos


def _fallos_negaciones(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    no_autoriza = doc.get("no_autoriza")
    if not isinstance(no_autoriza, Mapping):
        return ["no_autoriza ausente o con forma invalida"]
    for clave in NEGACIONES_OBLIGATORIAS:
        if clave not in no_autoriza:
            fallos.append(f"no_autoriza sin la negacion explicita: {clave}")
        elif no_autoriza[clave] is not False:
            fallos.append(f"no_autoriza.{clave} debe ser False")
    return fallos


def _fallos_diagnosticos(doc: Mapping[str, Any]) -> list[str]:
    diagnosticos = doc.get("diagnosticos")
    if not isinstance(diagnosticos, Mapping):
        return ["diagnosticos ausente o con forma invalida"]
    fallos: list[str] = []
    for nombre in fp.DIAGNOSTICOS:
        if nombre not in diagnosticos:
            fallos.append(f"diagnostico ausente: {nombre}")
    if "clasificacion_diagnostica_linea_base" not in doc:
        fallos.append("falta la clasificacion diagnostica de la linea base")
    return fallos


def _fallos_entorno_y_procesos(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    entorno = doc.get("entorno")
    if not isinstance(entorno, Mapping):
        fallos.append("entorno ausente o con forma invalida")
    else:
        fallos.extend(f"entorno sin campo {c}" for c in CAMPOS_ENTORNO if c not in entorno)
        inicial = entorno.get("captura_inicial")
        final = entorno.get("captura_final")
        if (
            isinstance(inicial, Mapping)
            and isinstance(final, Mapping)
            and inicial.get("boot_id") != final.get("boot_id")
        ):
            fallos.append("boot_id cambio durante la corrida")

    procesos = doc.get("procesos")
    if not isinstance(procesos, Sequence) or isinstance(procesos, str | bytes):
        fallos.append("procesos ausente o con forma invalida")
    else:
        pids = [p.get("pid") for p in procesos if isinstance(p, Mapping)]
        if len(pids) < fp.PROCESOS_MINIMOS:
            fallos.append(f"{len(pids)} procesos; el minimo es {fp.PROCESOS_MINIMOS}")
        if len(set(pids)) != len(pids):
            fallos.append("PIDs repetidos: los procesos no son independientes")

    return fallos


def fallos_suelo_medicion(doc: Mapping[str, Any]) -> list[str]:
    """Valida el artefacto completo. Lista vacia significa conforme."""
    fallos = _fallos_secciones(doc)

    if doc.get("version_esquema") not in (None, VERSION_ESQUEMA):
        fallos.append(f"version_esquema debe ser {VERSION_ESQUEMA}")
    if doc.get("protocolo") not in (None, fp.PROTOCOLO):
        fallos.append("el protocolo declarado no es el aprobado")
    if "clasificacion_entorno" in doc:
        fallos.append(
            "no se importa ninguna clasificacion formal de TOL-207 "
            "(por ejemplo ENVOLVENTE_REPRODUCIBLE) sin autoridad que la generalice"
        )

    fallos.extend(_fallos_preinscripcion(doc))
    fallos.extend(_fallos_entorno_y_procesos(doc))
    fallos.extend(_fallos_sondas(doc))
    fallos.extend(_fallos_diagnosticos(doc))
    fallos.extend(_fallos_controles(doc))
    fallos.extend(_fallos_derivacion(doc))
    fallos.extend(_fallos_regimenes(doc))
    fallos.extend(_fallos_negaciones(doc))

    custodia = doc.get("custodia")
    if isinstance(custodia, Mapping):
        if custodia.get("diff_preinscritos_vacio") is not True:
            fallos.append("custodia: el diff en los ficheros preinscritos no esta vacio")
        if custodia.get("sha_a_es_ancestro") is not True:
            fallos.append("custodia: el commit de preinscripcion no es ancestro de HEAD")
    elif "custodia" in doc:
        fallos.append("custodia con forma invalida")

    return list(dict.fromkeys(fallos))
