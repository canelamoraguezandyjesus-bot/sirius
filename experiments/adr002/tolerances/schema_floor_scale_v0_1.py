"""Esquema y validador del futuro artefacto ``suelo_medicion_v0.2.json``.

Se congela en la preinscripcion, ANTES de que exista ninguna observacion,
para que el contrato que la evidencia debe cumplir no pueda escribirse
despues de verla. El validador no mide, no lee ficheros y no ejecuta nada al
importarse: recibe el documento ya cargado y devuelve la lista de fallos.

Falla cerrado: una seccion ausente es un fallo, nunca una omision tolerada.

Lo que este validador RECOMPUTA desde los vectores crudos publicados, sin
aceptar ningun valor declarado:

- los percentiles por rango mas cercano de cada entrada;
- el numero de unidades de cada escala, desde la calibracion publicada;
- ``D(s)`` de cada escala, escala a escala, familia a familia;
- el punto fijo completo: ``U``, ``B``, sostenibilidad y razones;
- ``SM`` desde las sondas unitarias;
- el regimen de cada percentil de cada magnitud clasificada;
- la tabla de progresion entre escalas consecutivas.

Un artefacto que publique un valor incoherente con sus propios vectores no
pasa, aunque el valor sea plausible.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from experiments.adr002.tolerances import floor_scale_protocol as fp

VERSION_ESQUEMA: Final = fp.VERSION_ESQUEMA

#: Secciones de primer nivel exigidas al artefacto.
SECCIONES_OBLIGATORIAS: Final[tuple[str, ...]] = (
    "documento",
    "version_esquema",
    "estado",
    "protocolo",
    "paquete",
    "metodo",
    "plan",
    "calibracion",
    "preinscripcion",
    "entorno",
    "procesos",
    "escalas",
    "sondas_unitarias",
    "diagnosticos",
    "controles_internos",
    "derivacion",
    "regimenes_por_percentil",
    "clasificacion_diagnostica_linea_base",
    "contraste_metodo_anterior",
    "custodia",
    "no_autoriza",
)

CAMPOS_PREINSCRIPCION: Final[tuple[str, ...]] = (
    "commit_a",
    "head_en_ejecucion",
    "blobs_preinscritos",
    "blobs_heredados",
    "blobs_corpus_congelado",
    "blob_protocolo",
    "blobs_evidencia_anterior",
)

CAMPOS_ENTORNO: Final[tuple[str, ...]] = (
    "captura_inicial",
    "captura_final",
    "boot_id",
    "carga_por_proceso",
    "incidencias",
)

CAMPOS_DERIVACION: Final[tuple[str, ...]] = (
    "resultado",
    "sm_ns",
    "u_ns",
    "b_ns",
    "m",
    "objetivo_relativo",
    "factor_u",
    "dispersiones",
    "detalle_por_escala",
    "motivo_no_evaluable",
)

#: Campos comunes a toda entrada medida.
CAMPOS_MEDIDA: Final[tuple[str, ...]] = (
    "pid",
    "n",
    "warmup_descartado",
    "muestras_ns",
    "p50_ns",
    "p95_ns",
    "p99_ns",
    "min_ns",
    "max_ns",
    "media_truncada_ns",
    "resolucion_percentil",
    "valores_distintos",
    "repeticion_maxima",
)

CAMPOS_ESCALA: Final[tuple[str, ...]] = (*CAMPOS_MEDIDA, "familia", "escala_ns", "unidades")
CAMPOS_UNITARIA: Final[tuple[str, ...]] = (*CAMPOS_MEDIDA, "sonda")

CAMPOS_CALIBRACION: Final[tuple[str, ...]] = (
    "unidades_referencia",
    "coste_referencia_ns",
    "muestras_ns",
    "unidades_por_escala",
)

#: Lo que el artefacto debe negar explicitamente. Las siete, no solo las
#: normativas: un artefacto que se declarase habilitante de T0, del benchmark
#: o de la fusion del PR seria una autorizacion encubierta.
NEGACIONES_OBLIGATORIAS: Final[tuple[str, ...]] = (
    "limite_duro_tol_107",
    "aprobacion_tol_209",
    "sustitucion_evidencia_anterior",
    "t0",
    "candidatos",
    "benchmark",
    "merge_pr_117",
)

#: Campos de texto del metodo que no pueden quedar vacios.
CAMPOS_METODO_TEXTO: Final[tuple[str, ...]] = ("nombre", "criterio", "banda", "dispersion")

_HEXADECIMAL: Final = frozenset("0123456789abcdef")

ENTEROS_MEDIDA: Final[tuple[str, ...]] = (
    "pid",
    "n",
    "warmup_descartado",
    "p50_ns",
    "p95_ns",
    "p99_ns",
    "min_ns",
    "max_ns",
    "media_truncada_ns",
    "valores_distintos",
    "repeticion_maxima",
)


def _es_entero(valor: Any) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _entero_o_none(valor: Any) -> int | None:
    return valor if _es_entero(valor) else None


def _es_sha(valor: Any) -> bool:
    """Identificador de objeto Git: 40 caracteres hexadecimales en minuscula."""
    return isinstance(valor, str) and len(valor) == 40 and set(valor) <= _HEXADECIMAL


def _texto_no_vacio(valor: Any) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _pids_declarados(doc: Mapping[str, Any]) -> set[int] | None:
    """PIDs de la seccion ``procesos``. ``None`` si es irreconstruible."""
    procesos = doc.get("procesos")
    if not isinstance(procesos, Sequence) or isinstance(procesos, str | bytes):
        return None
    pids: set[int] = set()
    for entrada in procesos:
        if not isinstance(entrada, Mapping) or not _es_entero(entrada.get("pid")):
            return None
        pids.add(int(entrada["pid"]))
    return pids


def _fallos_secciones(doc: Mapping[str, Any]) -> list[str]:
    return [f"falta la seccion obligatoria: {s}" for s in SECCIONES_OBLIGATORIAS if s not in doc]


# --------------------------------------------------------------------------
# Identidad, metodo y preinscripcion
# --------------------------------------------------------------------------


def _fallos_metodo(doc: Mapping[str, Any]) -> list[str]:
    metodo = doc.get("metodo")
    if not isinstance(metodo, Mapping):
        return ["metodo ausente o con forma invalida"]
    fallos: list[str] = [
        f"metodo.{campo} debe declararse por escrito"
        for campo in CAMPOS_METODO_TEXTO
        if not _texto_no_vacio(metodo.get(campo))
    ]
    if metodo.get("escalera_ns") != list(fp.ESCALERA_NS):
        fallos.append("metodo.escalera_ns no es la escalera preinscrita")
    if metodo.get("familias") != list(fp.FAMILIAS):
        fallos.append("metodo.familias no son las familias preinscritas")
    if metodo.get("sustituye_metodo_de") != fp.EVIDENCIA_ANTERIOR:
        fallos.append("metodo.sustituye_metodo_de no cita la evidencia anterior")
    if metodo.get("no_sustituye_evidencia") is not True:
        fallos.append(
            "metodo.no_sustituye_evidencia debe ser True: el sucesor cambia el metodo, "
            "no la evidencia anterior"
        )
    return fallos


def _fallos_preinscripcion(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    pre = doc.get("preinscripcion")
    if not isinstance(pre, Mapping):
        return ["preinscripcion ausente o con forma invalida"]

    fallos.extend(f"preinscripcion sin campo {c}" for c in CAMPOS_PREINSCRIPCION if c not in pre)

    # El esquema vive en el mismo commit que valida: no puede acreditar su
    # propio blob (limitacion declarada). Lo que si puede exigir es que cada
    # blob publicado TENGA forma de identificador de objeto Git, de modo que
    # una cadena vacia o truncada no pase por evidencia de custodia.
    for campo in ("commit_a", "head_en_ejecucion"):
        if campo in pre and not _es_sha(pre[campo]):
            fallos.append(f"preinscripcion.{campo} no tiene forma de SHA de commit")

    blobs = pre.get("blobs_preinscritos")
    if isinstance(blobs, Mapping):
        for ruta in fp.ARCHIVOS_PREINSCRITOS:
            if ruta not in blobs:
                fallos.append(f"blob preinscrito ausente: {ruta}")
            elif not _es_sha(blobs[ruta]):
                fallos.append(f"blob preinscrito sin forma de blob Git: {ruta}")
    elif "blobs_preinscritos" in pre:
        fallos.append("blobs_preinscritos debe ser un mapa ruta -> blob")

    heredados = pre.get("blobs_heredados")
    if isinstance(heredados, Mapping):
        for ruta, esperado in fp.ARCHIVOS_HEREDADOS.items():
            if ruta not in heredados:
                fallos.append(f"blob heredado ausente: {ruta}")
            elif heredados[ruta] != esperado:
                fallos.append(f"blob heredado alterado: {ruta}")
    elif "blobs_heredados" in pre:
        fallos.append("blobs_heredados debe ser un mapa ruta -> blob")

    congelados = pre.get("blobs_corpus_congelado")
    if isinstance(congelados, Mapping):
        for ruta, esperado in fp.BLOBS_CORPUS_CONGELADO.items():
            if ruta not in congelados:
                fallos.append(f"blob congelado ausente: {ruta}")
            elif congelados[ruta] != esperado:
                fallos.append(f"blob congelado alterado: {ruta}")
    elif "blobs_corpus_congelado" in pre:
        fallos.append("blobs_corpus_congelado debe ser un mapa ruta -> blob")

    # Comparacion ESTRICTA: un `None` explicito no puede ser mas permisivo que
    # un valor distinto. La clave existe, asi que `_fallos_secciones` no la ve
    # ausente; sin igualdad estricta, publicar `null` la absolvia.
    if pre.get("blob_protocolo") != fp.BLOB_PROTOCOLO_APROBADO:
        fallos.append("el blob del protocolo aprobado no coincide")

    anteriores = pre.get("blobs_evidencia_anterior")
    if anteriores != dict(fp.BLOBS_EVIDENCIA_ANTERIOR):
        fallos.append(
            "blobs_evidencia_anterior no coincide con la evidencia del metodo anterior: "
            "el sucesor debe citarla intacta"
        )

    return fallos


# --------------------------------------------------------------------------
# Entradas medidas
# --------------------------------------------------------------------------


def _fallos_medida_comun(
    medida: Mapping[str, Any], etiqueta: str, *, n_esperado: int, warmup_esperado: int
) -> list[str]:
    """Comprobaciones comunes a toda entrada medida. Recomputa los percentiles."""
    fallos: list[str] = []

    muestras = medida["muestras_ns"]
    if not isinstance(muestras, Sequence) or isinstance(muestras, str | bytes):
        return [f"{etiqueta}: muestras_ns debe ser una secuencia"]
    if not muestras:
        return [f"{etiqueta}: vector de muestras vacio"]
    if not all(_es_entero(x) for x in muestras):
        return [f"{etiqueta}: las muestras deben ser enteros en nanosegundos"]
    # Una duracion medida con reloj monotonico no puede ser negativa: si lo es,
    # el reloj retrocedio o el vector se manipulo. Falla cerrado.
    if any(int(x) < 0 for x in muestras):
        return [f"{etiqueta}: hay muestras negativas; una duracion no puede serlo"]

    # El TIPO de cada campo normativo se valida ANTES de usarlo: sin esta
    # guarda un campo no entero o desactivaba en silencio la recomputacion, o
    # hacia que el validador lanzase en vez de devolver un fallo.
    for campo in ENTEROS_MEDIDA:
        if not _es_entero(medida[campo]):
            fallos.append(f"{etiqueta}: {campo} debe ser un entero")
    if not isinstance(medida["resolucion_percentil"], str):
        fallos.append(f"{etiqueta}: resolucion_percentil debe ser una cadena")
    if fallos:
        return fallos

    valores = [int(x) for x in muestras]
    if int(medida["n"]) != len(valores):
        fallos.append(f"{etiqueta}: n declarado ({medida['n']}) != longitud del vector")
    if len(valores) != n_esperado:
        fallos.append(f"{etiqueta}: n={len(valores)} distinto del preinscrito {n_esperado}")
    if int(medida["warmup_descartado"]) != warmup_esperado:
        fallos.append(
            f"{etiqueta}: warmup_descartado={medida['warmup_descartado']} difiere del "
            f"preinscrito {warmup_esperado}"
        )

    # Redondeo previo: multiplos exactos de 100 ns en todo el vector es la
    # firma del ``round(..., 4)`` en milisegundos del arnes historico.
    if len(valores) >= 2 and all(v % 100 == 0 for v in valores) and len(set(valores)) > 1:
        fallos.append(f"{etiqueta}: vector redondeado antes de persistirse")

    ordenadas = sorted(valores)
    distintos = set(ordenadas)
    esperados = {
        "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
        "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
        "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
        "min_ns": ordenadas[0],
        "max_ns": ordenadas[-1],
        "media_truncada_ns": sum(ordenadas) // len(ordenadas),
        "valores_distintos": len(distintos),
        "repeticion_maxima": max(ordenadas.count(v) for v in distintos),
    }
    for campo, esperado in esperados.items():
        if medida[campo] != esperado:
            fallos.append(
                f"{etiqueta}: {campo} publicado {medida[campo]!r} != recomputado {esperado}"
            )
    if medida["resolucion_percentil"] != fp.resolucion_percentil(len(valores)):
        fallos.append(f"{etiqueta}: resolucion_percentil no corresponde a n={len(valores)}")

    return fallos


def _fallos_una_escala(medida: Mapping[str, Any], indice: int) -> list[str]:
    etiqueta = f"escalas[{indice}]"
    ausentes = [f"{etiqueta} sin campo {c}" for c in CAMPOS_ESCALA if c not in medida]
    if ausentes:
        return ausentes

    fallos: list[str] = []
    familia = medida["familia"]
    escala = medida["escala_ns"]
    if not isinstance(familia, str) or familia not in fp.FAMILIAS:
        fallos.append(f"{etiqueta}: familia ajena a la preinscripcion: {familia!r}")
    if not _es_entero(escala) or escala not in fp.ESCALERA_NS:
        fallos.append(f"{etiqueta}: escala ajena a la escalera: {escala!r}")
    if not _es_entero(medida["unidades"]) or int(medida["unidades"]) <= 0:
        fallos.append(f"{etiqueta}: unidades debe ser un entero positivo")
    if fallos:
        return fallos

    fallos.extend(
        _fallos_medida_comun(
            medida,
            etiqueta,
            n_esperado=fp.n_para_escala(int(escala)),
            warmup_esperado=fp.WARMUP_ESCALA,
        )
    )
    return fallos


def _fallos_una_unitaria(medida: Mapping[str, Any], indice: int) -> list[str]:
    etiqueta = f"sondas_unitarias[{indice}]"
    ausentes = [f"{etiqueta} sin campo {c}" for c in CAMPOS_UNITARIA if c not in medida]
    if ausentes:
        return ausentes

    sonda = medida["sonda"]
    if not isinstance(sonda, str) or sonda not in fp.SONDAS_UNITARIAS:
        return [f"{etiqueta}: sonda ajena a la preinscripcion: {sonda!r}"]

    return _fallos_medida_comun(
        medida, etiqueta, n_esperado=fp.N_UNITARIA, warmup_esperado=fp.WARMUP_UNITARIA
    )


def _fallos_escalas(doc: Mapping[str, Any]) -> list[str]:
    escalas = doc.get("escalas")
    if not isinstance(escalas, Sequence) or isinstance(escalas, str | bytes):
        return ["escalas ausente o con forma invalida"]
    if not escalas:
        return ["escalas vacio: sin vectores no hay suelo"]

    fallos: list[str] = []
    entradas = [m for m in escalas if isinstance(m, Mapping)]
    if len(entradas) != len(escalas):
        fallos.append("cada entrada de escalas debe ser un objeto")

    for indice, medida in enumerate(entradas):
        fallos.extend(_fallos_una_escala(medida, indice))

    # Cobertura: toda (familia, escala) preinscrita con al menos cinco procesos
    # distintos, y ninguna combinacion ajena.
    for familia in fp.FAMILIAS:
        for escala in fp.ESCALERA_NS:
            pids = {
                int(m["pid"])
                for m in entradas
                if m.get("familia") == familia
                and m.get("escala_ns") == escala
                and _es_entero(m.get("pid"))
            }
            if not pids:
                fallos.append(f"falta la sonda {familia}@{escala} ns")
            elif len(pids) < fp.PROCESOS_MINIMOS:
                fallos.append(
                    f"{familia}@{escala} ns: {len(pids)} procesos distintos; "
                    f"el minimo es {fp.PROCESOS_MINIMOS}"
                )
            unidades = {
                int(m["unidades"])
                for m in entradas
                if m.get("familia") == familia
                and m.get("escala_ns") == escala
                and _es_entero(m.get("unidades"))
            }
            if len(unidades) > 1:
                fallos.append(
                    f"{familia}@{escala} ns: los procesos resolvieron cantidades de trabajo "
                    f"distintas {sorted(unidades)}; las ejecuciones no son equivalentes"
                )

    # Calibracion: el P50 observado debe caer en [s/2, 2s]. Se recomputa aqui
    # y no se acepta del control declarado.
    for indice, medida in enumerate(entradas):
        nominal = _entero_o_none(medida.get("escala_ns"))
        p50 = _entero_o_none(medida.get("p50_ns"))
        if nominal is None or p50 is None or nominal not in fp.ESCALERA_NS:
            continue
        if not fp.calibracion_en_banda(p50, nominal):
            fallos.append(
                f"escalas[{indice}]: P50 observado {p50} ns fuera de la banda de calibracion "
                f"[{nominal // 2}, {2 * nominal}] de la escala {nominal} ns"
            )

    return fallos


def _fallos_unitarias(doc: Mapping[str, Any]) -> list[str]:
    unitarias = doc.get("sondas_unitarias")
    if not isinstance(unitarias, Sequence) or isinstance(unitarias, str | bytes):
        return ["sondas_unitarias ausente o con forma invalida"]
    if not unitarias:
        return ["sondas_unitarias vacio: sin ellas no hay SM"]

    fallos: list[str] = []
    entradas = [m for m in unitarias if isinstance(m, Mapping)]
    if len(entradas) != len(unitarias):
        fallos.append("cada entrada de sondas_unitarias debe ser un objeto")

    nombres = {str(m.get("sonda")) for m in entradas}
    intrusas = sorted(n for n in nombres if n not in fp.SONDAS_UNITARIAS)
    if intrusas:
        fallos.append(f"sondas unitarias ajenas: {intrusas}")
    faltan = sorted(s for s in fp.SONDAS_UNITARIAS if s not in nombres)
    if faltan:
        fallos.append(f"faltan sondas unitarias: {faltan}")

    for sonda in fp.SONDAS_UNITARIAS:
        pids = {
            int(m["pid"]) for m in entradas if m.get("sonda") == sonda and _es_entero(m.get("pid"))
        }
        if 0 < len(pids) < fp.PROCESOS_MINIMOS:
            fallos.append(
                f"{sonda}: {len(pids)} procesos distintos; el minimo es {fp.PROCESOS_MINIMOS}"
            )

    for indice, medida in enumerate(entradas):
        fallos.extend(_fallos_una_unitaria(medida, indice))

    fallos.extend(fp.comprobar_neutralidad(sorted(nombres)))
    return fallos


# --------------------------------------------------------------------------
# Reconstruccion tipada para recomputar el punto fijo
# --------------------------------------------------------------------------


def _medidas_desde_escalas(doc: Mapping[str, Any]) -> list[fp.MedidaEscala] | None:
    """Reconstruye la escalera desde la seccion publicada.

    Devuelve ``None`` SOLO si la seccion es irreconstruible. Quien llama debe
    tratar ese ``None`` como fallo, nunca como conformidad: de lo contrario un
    campo con tipo manipulado desactivaria la recomputacion.
    """
    escalas = doc.get("escalas")
    if not isinstance(escalas, Sequence) or isinstance(escalas, str | bytes):
        return None
    medidas: list[fp.MedidaEscala] = []
    for entrada in escalas:
        if not isinstance(entrada, Mapping):
            return None
        if any(c not in entrada for c in CAMPOS_ESCALA):
            return None
        enteros = ("escala_ns", "unidades", *ENTEROS_MEDIDA)
        if not all(_es_entero(entrada[c]) for c in enteros):
            return None
        if not isinstance(entrada["familia"], str):
            return None
        medidas.append(
            fp.MedidaEscala(
                familia=entrada["familia"],
                escala_ns=int(entrada["escala_ns"]),
                unidades=int(entrada["unidades"]),
                pid=int(entrada["pid"]),
                n=int(entrada["n"]),
                warmup_descartado=int(entrada["warmup_descartado"]),
                p50=int(entrada["p50_ns"]),
                p95=int(entrada["p95_ns"]),
                p99=int(entrada["p99_ns"]),
                minimo=int(entrada["min_ns"]),
                maximo=int(entrada["max_ns"]),
                media_truncada=int(entrada["media_truncada_ns"]),
            )
        )
    return medidas


def _unitarias_desde_doc(doc: Mapping[str, Any]) -> list[fp.MedidaUnitaria] | None:
    unitarias = doc.get("sondas_unitarias")
    if not isinstance(unitarias, Sequence) or isinstance(unitarias, str | bytes):
        return None
    medidas: list[fp.MedidaUnitaria] = []
    for entrada in unitarias:
        if not isinstance(entrada, Mapping):
            return None
        if any(c not in entrada for c in CAMPOS_UNITARIA):
            return None
        if not all(_es_entero(entrada[c]) for c in ENTEROS_MEDIDA):
            return None
        if not isinstance(entrada["sonda"], str):
            return None
        medidas.append(
            fp.MedidaUnitaria(
                sonda=entrada["sonda"],
                pid=int(entrada["pid"]),
                n=int(entrada["n"]),
                warmup_descartado=int(entrada["warmup_descartado"]),
                p50=int(entrada["p50_ns"]),
                p95=int(entrada["p95_ns"]),
                p99=int(entrada["p99_ns"]),
                minimo=int(entrada["min_ns"]),
                maximo=int(entrada["max_ns"]),
                media_truncada=int(entrada["media_truncada_ns"]),
            )
        )
    return medidas


def _punto_recomputado(doc: Mapping[str, Any]) -> fp.PuntoFijo | None:
    medidas = _medidas_desde_escalas(doc)
    if medidas is None:
        return None
    try:
        return fp.resolver_punto_fijo(medidas)
    except (
        fp.SondaNoNeutralError,
        fp.ProcesosInsuficientesError,
        fp.EscaleraInvalidaError,
        ValueError,
    ):
        return None


# --------------------------------------------------------------------------
# Calibracion y plan
# --------------------------------------------------------------------------


def _unidades_publicadas(doc: Mapping[str, Any]) -> dict[tuple[str, int], int]:
    """Unidades por (familia, escala) segun la seccion ``escalas`` publicada."""
    salida: dict[tuple[str, int], int] = {}
    escalas = doc.get("escalas")
    if not isinstance(escalas, Sequence) or isinstance(escalas, str | bytes):
        return salida
    for entrada in escalas:
        if not isinstance(entrada, Mapping):
            continue
        familia = entrada.get("familia")
        escala = _entero_o_none(entrada.get("escala_ns"))
        unidades = _entero_o_none(entrada.get("unidades"))
        if isinstance(familia, str) and escala is not None and unidades is not None:
            salida[familia, escala] = unidades
    return salida


def _fallos_calibracion(doc: Mapping[str, Any]) -> list[str]:
    calibracion = doc.get("calibracion")
    if not isinstance(calibracion, Mapping):
        return ["calibracion ausente o con forma invalida"]

    fallos: list[str] = []
    medidas = _unidades_publicadas(doc)
    for familia in fp.FAMILIAS:
        entrada = calibracion.get(familia)
        if not isinstance(entrada, Mapping):
            fallos.append(f"calibracion sin la familia {familia}")
            continue
        ausentes = [c for c in CAMPOS_CALIBRACION if c not in entrada]
        if ausentes:
            fallos.append(f"calibracion[{familia}] sin campos {ausentes}")
            continue
        referencia = _entero_o_none(entrada["unidades_referencia"])
        coste = _entero_o_none(entrada["coste_referencia_ns"])
        if referencia is None or coste is None or coste <= 0 or referencia <= 0:
            fallos.append(f"calibracion[{familia}]: referencia y coste deben ser positivos")
            continue
        if referencia != fp.UNIDADES_REFERENCIA[familia]:
            fallos.append(
                f"calibracion[{familia}]: unidades_referencia {referencia} distinta de la "
                f"preinscrita {fp.UNIDADES_REFERENCIA[familia]}"
            )
        muestras = entrada["muestras_ns"]
        if (
            not isinstance(muestras, Sequence)
            or isinstance(muestras, str | bytes)
            or len(muestras) != fp.MUESTRAS_CALIBRACION
            or not all(_es_entero(v) for v in muestras)
        ):
            fallos.append(
                f"calibracion[{familia}]: se exigen {fp.MUESTRAS_CALIBRACION} muestras enteras"
            )
        elif fp.p50_ns([int(v) for v in muestras]) != coste:
            fallos.append(
                f"calibracion[{familia}]: coste_referencia_ns no es el P50 de sus muestras"
            )

        por_escala = entrada["unidades_por_escala"]
        if not isinstance(por_escala, Mapping):
            fallos.append(f"calibracion[{familia}].unidades_por_escala debe ser un mapa")
            continue
        for escala in fp.ESCALERA_NS:
            publicado = por_escala.get(str(escala))
            esperado = fp.unidades_para_escala(
                escala, unidades_referencia=referencia, coste_referencia_ns=coste
            )
            if publicado != esperado:
                fallos.append(
                    f"calibracion[{familia}]@{escala} ns: unidades {publicado!r} no salen de "
                    f"la calibracion publicada ({esperado})"
                )
            medido = medidas.get((familia, escala))
            if medido is not None and medido != esperado:
                fallos.append(
                    f"{familia}@{escala} ns: se midieron {medido} unidades y la calibracion "
                    f"publicada implica {esperado}"
                )
    return fallos


def _fallos_plan(doc: Mapping[str, Any]) -> list[str]:
    plan = doc.get("plan")
    if not isinstance(plan, Mapping):
        return ["plan ausente o con forma invalida"]

    fallos: list[str] = []
    if plan.get("procesos") != fp.PROCESOS_MINIMOS:
        fallos.append(f"plan.procesos debe ser {fp.PROCESOS_MINIMOS}")
    if plan.get("rondas") != fp.RONDAS_ROUND_ROBIN:
        fallos.append(f"plan.rondas debe ser {fp.RONDAS_ROUND_ROBIN}")
    if plan.get("escalera_ns") != list(fp.ESCALERA_NS):
        fallos.append("plan.escalera_ns no es la escalera preinscrita")
    if plan.get("familias") != list(fp.FAMILIAS):
        fallos.append("plan.familias no son las familias preinscritas")
    if plan.get("warmup_por_escala") != fp.WARMUP_ESCALA:
        fallos.append(f"plan.warmup_por_escala debe ser {fp.WARMUP_ESCALA}")
    if plan.get("n_unitaria") != fp.N_UNITARIA:
        fallos.append(f"plan.n_unitaria debe ser {fp.N_UNITARIA}")
    if plan.get("warmup_unitaria") != fp.WARMUP_UNITARIA:
        fallos.append(f"plan.warmup_unitaria debe ser {fp.WARMUP_UNITARIA}")
    if plan.get("semilla") != fp.SEMILLA:
        fallos.append(f"plan.semilla debe ser {fp.SEMILLA}")
    if plan.get("n_por_escala") != {str(s): fp.n_para_escala(s) for s in fp.ESCALERA_NS}:
        fallos.append("plan.n_por_escala no coincide con el preinscrito")
    esperado_orden = [[familia, escala] for familia, escala in fp.pares_de_escalera()]
    if plan.get("orden") != esperado_orden * fp.RONDAS_ROUND_ROBIN:
        fallos.append("plan.orden no es el round-robin preinscrito")

    unidades = plan.get("unidades")
    medidas = _unidades_publicadas(doc)
    if not isinstance(unidades, Mapping):
        fallos.append("plan.unidades debe ser un mapa familia -> escala -> unidades")
    else:
        for familia in fp.FAMILIAS:
            por_familia = unidades.get(familia)
            if not isinstance(por_familia, Mapping):
                fallos.append(f"plan.unidades sin la familia {familia}")
                continue
            for escala in fp.ESCALERA_NS:
                declarado = por_familia.get(str(escala))
                medido = medidas.get((familia, escala))
                if medido is not None and declarado != medido:
                    fallos.append(
                        f"plan.unidades[{familia}][{escala}] = {declarado!r} pero se midieron "
                        f"{medido} unidades"
                    )
    return fallos


# --------------------------------------------------------------------------
# Derivacion: punto fijo recomputado
# --------------------------------------------------------------------------


def _fallos_derivacion(doc: Mapping[str, Any]) -> list[str]:
    der = doc.get("derivacion")
    if not isinstance(der, Mapping):
        return ["derivacion ausente o con forma invalida"]

    fallos = [f"derivacion sin campo {c}" for c in CAMPOS_DERIVACION if c not in der]
    if fallos:
        return fallos

    if der["m"] != fp.MARGEN_M:
        fallos.append(f"m debe ser {fp.MARGEN_M}; se publico {der['m']!r}")
    if der["factor_u"] != fp.FACTOR_U:
        fallos.append(f"factor_u debe ser {fp.FACTOR_U}; se publico {der['factor_u']!r}")
    objetivo = f"{fp.OBJETIVO_RELATIVO_NUM}/{fp.OBJETIVO_RELATIVO_DEN}"
    if der["objetivo_relativo"] != objetivo:
        fallos.append(f"objetivo_relativo debe ser {objetivo}; no se elige en este paquete")

    punto = _punto_recomputado(doc)
    if punto is None:
        return [
            *fallos,
            "punto fijo no verificable: las escalas publicadas no permiten recomputarlo "
            "(campos ausentes, tipos invalidos o cobertura insuficiente)",
        ]

    u_publicada, b_publicada = der["u_ns"], der["b_ns"]
    if u_publicada != punto.u:
        fallos.append(
            f"derivacion.u_ns publicado {u_publicada!r} no coincide con el punto fijo "
            f"recomputado ({punto.u!r})"
        )
    if b_publicada != punto.b:
        fallos.append(
            f"derivacion.b_ns publicado {b_publicada!r} no coincide con U / {fp.FACTOR_U} "
            f"({punto.b!r})"
        )

    if punto.evaluable:
        if der["resultado"] != "RESUELTO":
            fallos.append("derivacion.resultado debe ser RESUELTO cuando hay punto fijo")
        if der["motivo_no_evaluable"] is not None:
            fallos.append("derivacion.motivo_no_evaluable debe ser null con punto fijo resuelto")
        if not fp.banda_cubre_el_suelo(punto):
            fallos.append(
                "la banda absoluta no cubre el suelo en alguna escala por debajo de U: "
                "el criterio absoluto seria inalcanzable alli"
            )
        if _es_entero(u_publicada) and _es_entero(b_publicada):
            if int(u_publicada) != fp.FACTOR_U * int(b_publicada):
                fallos.append(f"U debe ser {fp.FACTOR_U} * B")
            if int(u_publicada) not in fp.ESCALERA_NS:
                fallos.append("U debe ser una escala MEDIDA de la escalera, nunca interpolada")
    else:
        if der["resultado"] != fp.NO_EVALUABLE:
            fallos.append(f"derivacion.resultado debe ser {fp.NO_EVALUABLE} sin punto fijo")
        if u_publicada is not None or b_publicada is not None:
            fallos.append("sin punto fijo no se pueden publicar U ni B")
        if not isinstance(der["motivo_no_evaluable"], str) or not der["motivo_no_evaluable"]:
            fallos.append(f"{fp.NO_EVALUABLE} exige motivo explicito y no vacio")

    esperadas = [
        {
            "escala_ns": escala,
            "dispersion_ns": dispersion,
            "razon_por_mil": fp.razon_por_mil(dispersion, escala),
            "sostenible": fp.sostenible_en_escala(dispersion, escala),
        }
        for escala, dispersion in punto.dispersiones
    ]
    if der["dispersiones"] != esperadas:
        fallos.append(
            "derivacion.dispersiones no coincide con D(s) recomputada desde las escalas publicadas"
        )

    medidas = _medidas_desde_escalas(doc)
    if medidas is not None:
        detalle = _detalle_esperado(medidas)
        if der["detalle_por_escala"] != detalle:
            fallos.append(
                "derivacion.detalle_por_escala no coincide con la descomposicion recomputada"
            )

    sm = der["sm_ns"]
    unitarias = _unitarias_desde_doc(doc)
    if unitarias is None:
        fallos.append("SM no verificable: las sondas unitarias publicadas no permiten recomputarlo")
    else:
        try:
            esperado_sm = fp.calcular_sm(unitarias)
        except fp.SondaNoNeutralError, fp.ProcesosInsuficientesError, fp.EscaleraInvalidaError:
            fallos.append("SM no verificable desde las sondas unitarias publicadas")
        else:
            if sm != esperado_sm:
                fallos.append(
                    f"derivacion.sm_ns publicado {sm!r} no coincide con el recomputado "
                    f"({esperado_sm})"
                )

    return fallos


def _detalle_esperado(medidas: Sequence[fp.MedidaEscala]) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for escala in fp.ESCALERA_NS:
        for familia in fp.FAMILIAS:
            for percentil in ("p50", "p95"):
                seleccion = [
                    int(getattr(m, percentil))
                    for m in medidas
                    if m.familia == familia and m.escala_ns == escala
                ]
                if not seleccion:
                    continue
                filas.append(
                    {
                        "escala_ns": escala,
                        "familia": familia,
                        "percentil": percentil.upper(),
                        "min_ns": min(seleccion),
                        "max_ns": max(seleccion),
                        "dispersion_ns": max(seleccion) - min(seleccion),
                    }
                )
    return filas


# --------------------------------------------------------------------------
# Regimenes por percentil
# --------------------------------------------------------------------------


def _umbral_y_guarda(doc: Mapping[str, Any]) -> tuple[int | None, int | None]:
    """``(U, SM)`` publicados. ``None`` donde el valor no sea un entero."""
    der = doc.get("derivacion")
    if not isinstance(der, Mapping):
        return None, None
    return _entero_o_none(der.get("u_ns")), _entero_o_none(der.get("sm_ns"))


def _fallos_regimenes(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    regimenes = doc.get("regimenes_por_percentil")
    if not isinstance(regimenes, Sequence) or isinstance(regimenes, str | bytes):
        return ["regimenes_por_percentil ausente o con forma invalida"]

    # Una lista vacia no puede pasar: vaciarla borraria el veredicto y la
    # divulgacion obligatoria de la clasificacion de la linea base.
    if not regimenes:
        return ["regimenes_por_percentil vacio: el artefacto debe publicar su veredicto"]

    u, sm = _umbral_y_guarda(doc)
    der = doc.get("derivacion")
    b = _entero_o_none(der.get("b_ns")) if isinstance(der, Mapping) else None
    validos = {fp.REGIMEN_RELATIVO, fp.REGIMEN_ABSOLUTO}

    for indice, entrada in enumerate(regimenes):
        if not isinstance(entrada, Mapping):
            fallos.append(f"regimenes_por_percentil[{indice}] debe ser un objeto")
            continue
        etiqueta = f"regimenes_por_percentil[{indice}]"

        min50 = _entero_o_none(entrada.get("min_p50_ns"))
        min95 = _entero_o_none(entrada.get("min_p95_ns"))
        max50 = _entero_o_none(entrada.get("max_p50_ns"))
        max95 = _entero_o_none(entrada.get("max_p95_ns"))
        if min50 is None or min95 is None or max50 is None or max95 is None:
            fallos.append(f"{etiqueta}: los minimos y maximos por percentil deben ser enteros")
            continue

        # El invariante se comprueba SIEMPRE: declarar NO_EVALUABLE no puede
        # ser un comodin que desactive las guardas (§4.1 es incondicional).
        if min95 < min50:
            fallos.append(f"{etiqueta}: invariante violado min_s P95 < min_s P50")
        if max50 < min50 or max95 < min95:
            fallos.append(f"{etiqueta}: maximo por debajo del minimo")

        no_evaluable = entrada.get("resultado") == fp.NO_EVALUABLE

        if u is None:
            # Sin umbral resuelto ninguna magnitud puede clasificarse.
            if not no_evaluable:
                fallos.append(
                    f"{etiqueta}: sin umbral resuelto no se puede clasificar; se exige "
                    f"{fp.NO_EVALUABLE}"
                )
            elif entrada.get("motivo") != "umbral_no_resuelto":
                fallos.append(f"{etiqueta}: el motivo debe ser umbral_no_resuelto")
            if entrada.get("p50") is not None or entrada.get("p95") is not None:
                fallos.append(f"{etiqueta}: sin umbral no se publica regimen por percentil")
            continue

        if sm is not None:
            dominada = min95 < sm
            if dominada and not no_evaluable:
                fallos.append(
                    f"{etiqueta}: min_s P95 ({min95}) < SM ({sm}) pero no se declaro "
                    f"{fp.NO_EVALUABLE}: la guarda de dominancia se eludio"
                )
            if no_evaluable and not dominada:
                fallos.append(
                    f"{etiqueta}: se declaro {fp.NO_EVALUABLE} sin que min_s P95 ({min95}) "
                    f"quede por debajo de SM ({sm})"
                )
            if dominada and no_evaluable and entrada.get("motivo") != "dominada_por_instrumento":
                fallos.append(f"{etiqueta}: el motivo debe ser dominada_por_instrumento")

        if no_evaluable:
            # Una magnitud dominada por el instrumento no publica regimen.
            if entrada.get("p50") is not None or entrada.get("p95") is not None:
                fallos.append(
                    f"{etiqueta}: {fp.NO_EVALUABLE} no puede publicar regimen por percentil"
                )
            continue

        r50, r95 = entrada.get("p50"), entrada.get("p95")
        if not isinstance(r50, str) or not isinstance(r95, str):
            fallos.append(f"{etiqueta}: regimen por percentil ausente o invalido")
            continue
        if r50 not in validos or r95 not in validos:
            fallos.append(f"{etiqueta}: regimen por percentil ausente o invalido")
            continue
        if r50 == fp.REGIMEN_RELATIVO and r95 == fp.REGIMEN_ABSOLUTO:
            fallos.append(f"{etiqueta}: combinacion imposible P50 relativo / P95 absoluto")

        # RECOMPUTACION del regimen: un regimen declarado que no salga de
        # aplicar U a los minimos publicados invalida el artefacto.
        for nombre, minimo, declarado in (("P50", min50, r50), ("P95", min95, r95)):
            esperado = fp.regimen_de_percentil(minimo, u)
            if declarado != esperado:
                fallos.append(
                    f"{etiqueta}: {nombre} declarado '{declarado}' pero con min={minimo} y "
                    f"U={u} corresponde '{esperado}'"
                )

        # RECOMPUTACION del veredicto con el regimen que corresponde.
        if b is not None:
            esperado_resultado = _resultado_esperado(min50, max50, min95, max95, u=u, b=b)
            if entrada.get("resultado") != esperado_resultado:
                fallos.append(
                    f"{etiqueta}: resultado {entrada.get('resultado')!r} no coincide con el "
                    f"recomputado ({esperado_resultado})"
                )

    return fallos


def _resultado_esperado(min50: int, max50: int, min95: int, max95: int, *, u: int, b: int) -> str:
    def _pasa(minimo: int, maximo: int) -> bool:
        if fp.regimen_de_percentil(minimo, u) == fp.REGIMEN_RELATIVO:
            return fp.pasa_relativo(minimo, maximo)
        return fp.pasa_absoluto(minimo, maximo, b)

    return "VALIDA" if _pasa(min50, max50) and _pasa(min95, max95) else "INVALIDA"


# --------------------------------------------------------------------------
# Controles, diagnosticos, negaciones y custodia
# --------------------------------------------------------------------------


def _fallos_controles(doc: Mapping[str, Any]) -> list[str]:
    controles = doc.get("controles_internos")
    if not isinstance(controles, Mapping):
        return ["controles_internos ausente o con forma invalida"]

    fallos = [
        f"control bloqueante ausente: {c}" for c in fp.CONTROLES_BLOQUEANTES if c not in controles
    ]
    # Cualquier valor que no sea exactamente True cuenta como fallido: un 0,
    # None o cadena vacia no puede colarse como control satisfecho.
    fallidos = [
        c for c in fp.CONTROLES_BLOQUEANTES if c in controles and controles.get(c) is not True
    ]

    der = doc.get("derivacion")
    publica_valores = isinstance(der, Mapping) and (
        der.get("u_ns") is not None or der.get("b_ns") is not None
    )
    if publica_valores and fallidos:
        fallos.append(f"se publicaron U o B con controles bloqueantes fallidos: {sorted(fallidos)}")
    # Sin punto fijo, el unico control que puede fallar legitimamente es el que
    # presupone precisamente el umbral que no se resolvio. Y tiene que fallar:
    # ``banda_cubre_el_suelo`` es False por construccion cuando no hay B, de
    # modo que declararlo True seria una afirmacion imposible.
    if not publica_valores:
        indebidos = sorted(c for c in fallidos if c != "banda_cubre_el_suelo")
        if indebidos:
            fallos.append(
                f"{fp.NO_EVALUABLE} no absuelve controles bloqueantes fallidos: {indebidos}"
            )
        if controles.get("banda_cubre_el_suelo") is not False:
            fallos.append(
                "banda_cubre_el_suelo no puede declararse satisfecho sin banda: sin B no hay "
                "nada que cubra el suelo"
            )
    return fallos


def _fallos_diagnosticos(doc: Mapping[str, Any]) -> list[str]:
    diagnosticos = doc.get("diagnosticos")
    if not isinstance(diagnosticos, Mapping):
        return ["diagnosticos ausente o con forma invalida"]
    fallos = [f"diagnostico ausente: {n}" for n in fp.DIAGNOSTICOS if n not in diagnosticos]
    pids = _pids_declarados(doc)
    esperados = len(pids) if pids is not None else fp.PROCESOS_MINIMOS

    referencia = diagnosticos.get(fp.DIAG_REFERENCIA)
    if isinstance(referencia, Mapping):
        por_proceso = referencia.get("por_proceso")
        if not isinstance(por_proceso, Sequence) or isinstance(por_proceso, str | bytes):
            fallos.append(f"{fp.DIAG_REFERENCIA}.por_proceso debe ser una lista")
        else:
            if len(por_proceso) != esperados:
                fallos.append(
                    f"{fp.DIAG_REFERENCIA}: {len(por_proceso)} entradas para {esperados} procesos"
                )
            for indice, entrada in enumerate(por_proceso):
                if not isinstance(entrada, Mapping):
                    fallos.append(f"{fp.DIAG_REFERENCIA}[{indice}] debe ser un objeto")
                    continue
                if entrada.get("vueltas") != fp.VUELTAS_REFERENCIA:
                    fallos.append(
                        f"{fp.DIAG_REFERENCIA}[{indice}]: el trabajo de referencia debe ser "
                        f"{fp.VUELTAS_REFERENCIA} vueltas"
                    )
                valores = [
                    _entero_o_none(entrada.get(c))
                    for c in ("p50_inicio_ns", "p50_mitad_ns", "p50_final_ns")
                ]
                if any(v is None for v in valores):
                    fallos.append(f"{fp.DIAG_REFERENCIA}[{indice}]: los P50 deben ser enteros")
                    continue
                inicio, mitad, final = (int(v) for v in valores if v is not None)
                if not fp.referencia_estable(inicio, mitad, final):
                    fallos.append(
                        f"{fp.DIAG_REFERENCIA}[{indice}]: deriva o throttling dentro del proceso"
                    )

    progresion = diagnosticos.get(fp.DIAG_PROGRESION)
    if isinstance(progresion, Mapping):
        por_proceso = progresion.get("por_proceso")
        if not isinstance(por_proceso, Sequence) or isinstance(por_proceso, str | bytes):
            fallos.append(f"{fp.DIAG_PROGRESION}.por_proceso debe ser una lista")
        else:
            if len(por_proceso) != esperados:
                fallos.append(
                    f"{fp.DIAG_PROGRESION}: {len(por_proceso)} entradas para {esperados} procesos"
                )
            fallos.extend(_fallos_progresion(por_proceso, pids))
            fallos.extend(_fallos_progresion_contra_escalas(doc, por_proceso))

    fallos.extend(_fallos_curva(doc, diagnosticos))

    clasificacion = doc.get("clasificacion_diagnostica_linea_base")
    if not isinstance(clasificacion, Mapping):
        fallos.append("clasificacion_diagnostica_linea_base debe ser un objeto")
    else:
        if clasificacion.get("fuente") != fp.RUTA_LINEA_BASE:
            fallos.append(
                "clasificacion_diagnostica_linea_base.fuente no cita la evidencia versionada "
                "de la linea base"
            )
        magnitudes = clasificacion.get("magnitudes")
        if not isinstance(magnitudes, Sequence) or isinstance(magnitudes, str | bytes):
            fallos.append("clasificacion_diagnostica_linea_base.magnitudes debe ser una lista")
        elif not magnitudes:
            fallos.append(
                "clasificacion_diagnostica_linea_base.magnitudes vacia: la divulgacion de la "
                "clasificacion de la linea base es obligatoria"
            )
        elif magnitudes != doc.get("regimenes_por_percentil"):
            fallos.append(
                "la clasificacion diagnostica y regimenes_por_percentil deben ser el mismo "
                "veredicto, no dos listas divergentes"
            )
    return fallos


def _fallos_curva(doc: Mapping[str, Any], diagnosticos: Mapping[str, Any]) -> list[str]:
    """La curva ``D(s)/s`` publicada debe salir de la derivacion recomputada."""
    curva = diagnosticos.get(fp.DIAG_CURVA)
    if not isinstance(curva, Mapping):
        return [f"{fp.DIAG_CURVA} ausente o con forma invalida"]
    punto = _punto_recomputado(doc)
    if punto is None:
        return []  # ya lo denuncia la derivacion
    esperada = [
        {"escala_ns": escala, "razon_por_mil": fp.razon_por_mil(dispersion, escala)}
        for escala, dispersion in punto.dispersiones
    ]
    if curva.get("razon_por_mil") != esperada:
        return [f"{fp.DIAG_CURVA}.razon_por_mil no coincide con la curva recomputada"]
    return []


def _progresion_esperada(doc: Mapping[str, Any]) -> dict[int, list[dict[str, Any]]] | None:
    """Tabla de progresion recomputada desde la seccion ``escalas`` publicada.

    Sin esto la tabla solo seria coherente CONSIGO MISMA: un artefacto podria
    publicar tiempos y unidades inventados que hicieran pasar la progresion
    mientras sus propias mediciones dicen otra cosa.
    """
    medidas = _medidas_desde_escalas(doc)
    if medidas is None:
        return None
    indice: dict[tuple[int, str, int], fp.MedidaEscala] = {
        (m.pid, m.familia, m.escala_ns): m for m in medidas
    }
    tabla: dict[int, list[dict[str, Any]]] = {}
    for pid in sorted({m.pid for m in medidas}):
        filas: list[dict[str, Any]] = []
        for familia in fp.FAMILIAS:
            for menor, mayor in zip(fp.ESCALERA_NS, fp.ESCALERA_NS[1:], strict=False):
                a = indice.get((pid, familia, menor))
                b = indice.get((pid, familia, mayor))
                if a is None or b is None:
                    continue
                filas.append(
                    {
                        "familia": familia,
                        "escala_menor_ns": menor,
                        "escala_mayor_ns": mayor,
                        "unidades_menor": a.unidades,
                        "unidades_mayor": b.unidades,
                        "p50_menor_ns": a.p50,
                        "p50_mayor_ns": b.p50,
                        "exigible": fp.progresion_exigible(a.unidades, b.unidades),
                        "progresa": fp.escala_progresa(a.p50, menor, b.p50, mayor),
                    }
                )
        tabla[pid] = filas
    return tabla


def _fallos_progresion(por_proceso: Sequence[Any], pids: set[int] | None) -> list[str]:
    fallos: list[str] = []
    filas_esperadas = len(fp.FAMILIAS) * (len(fp.ESCALERA_NS) - 1)
    for indice, entrada in enumerate(por_proceso):
        if not isinstance(entrada, Mapping):
            fallos.append(f"{fp.DIAG_PROGRESION}[{indice}] debe ser un objeto")
            continue
        if pids is not None and entrada.get("pid") not in pids:
            fallos.append(f"{fp.DIAG_PROGRESION}[{indice}]: pid ajeno a los procesos declarados")
        filas = entrada.get("filas")
        if not isinstance(filas, Sequence) or isinstance(filas, str | bytes):
            fallos.append(f"{fp.DIAG_PROGRESION}[{indice}].filas debe ser una lista")
            continue
        if len(filas) != filas_esperadas:
            fallos.append(
                f"{fp.DIAG_PROGRESION}[{indice}]: {len(filas)} filas para "
                f"{filas_esperadas} pares consecutivos de la escalera"
            )
        for posicion, fila in enumerate(filas):
            etiqueta = f"{fp.DIAG_PROGRESION}[{indice}].filas[{posicion}]"
            if not isinstance(fila, Mapping):
                fallos.append(f"{etiqueta} debe ser un objeto")
                continue
            claves = (
                "escala_menor_ns",
                "escala_mayor_ns",
                "unidades_menor",
                "unidades_mayor",
                "p50_menor_ns",
                "p50_mayor_ns",
            )
            valores = {c: _entero_o_none(fila.get(c)) for c in claves}
            if any(v is None for v in valores.values()):
                fallos.append(f"{etiqueta}: los campos numericos deben ser enteros")
                continue
            menor = int(valores["escala_menor_ns"] or 0)
            mayor = int(valores["escala_mayor_ns"] or 0)
            p50_menor = int(valores["p50_menor_ns"] or 0)
            p50_mayor = int(valores["p50_mayor_ns"] or 0)
            u_menor = int(valores["unidades_menor"] or 0)
            u_mayor = int(valores["unidades_mayor"] or 0)
            exigible = fp.progresion_exigible(u_menor, u_mayor)
            progresa = fp.escala_progresa(p50_menor, menor, p50_mayor, mayor)
            if fila.get("exigible") is not exigible:
                fallos.append(f"{etiqueta}: exigible publicado no coincide con el recomputado")
            if fila.get("progresa") is not progresa:
                fallos.append(f"{etiqueta}: progresa publicado no coincide con el recomputado")
            if exigible and not progresa:
                fallos.append(
                    f"{etiqueta}: el tiempo medido no progresa con la escala nominal entre "
                    f"{menor} y {mayor} ns"
                )
    return fallos


def _fallos_progresion_contra_escalas(
    doc: Mapping[str, Any], por_proceso: Sequence[Any]
) -> list[str]:
    """La tabla publicada debe salir EXACTAMENTE de las escalas publicadas."""
    esperada = _progresion_esperada(doc)
    if esperada is None:
        return []  # ya lo denuncian las escalas y la derivacion
    fallos: list[str] = []
    vistos: set[int] = set()
    for indice, entrada in enumerate(por_proceso):
        if not isinstance(entrada, Mapping):
            continue
        pid = _entero_o_none(entrada.get("pid"))
        if pid is None or pid not in esperada:
            fallos.append(f"{fp.DIAG_PROGRESION}[{indice}]: sin pid reconocible")
            continue
        vistos.add(pid)
        if entrada.get("filas") != esperada[pid]:
            fallos.append(
                f"{fp.DIAG_PROGRESION}[{indice}]: la tabla no coincide con la recomputada "
                f"desde las escalas publicadas del proceso {pid}"
            )
    faltan = sorted(set(esperada) - vistos)
    if faltan:
        fallos.append(f"{fp.DIAG_PROGRESION}: sin tabla para los procesos {faltan}")
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


def _fallos_entorno_y_procesos(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    pids_declarados = _pids_declarados(doc)
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
        for etapa, captura in (("inicial", inicial), ("final", final)):
            if not isinstance(captura, Mapping):
                fallos.append(f"entorno.captura_{etapa} debe ser un objeto")
                continue
            if "carga" not in captura:
                fallos.append(f"entorno.captura_{etapa} sin carga del sistema")
            if not _texto_no_vacio(captura.get("boot_id")):
                fallos.append(f"entorno.captura_{etapa} sin boot_id")
            if captura.get("etapa") != etapa:
                fallos.append(f"entorno.captura_{etapa} no se declara de la etapa {etapa}")
        if isinstance(inicial, Mapping) and entorno.get("boot_id") != inicial.get("boot_id"):
            fallos.append("entorno.boot_id no coincide con el de la captura inicial")

        # La carga declarada por proceso es la evidencia del control
        # ``carga_registrada``: se comprueba, no se acepta.
        cargas = entorno.get("carga_por_proceso")
        if not isinstance(cargas, Mapping):
            fallos.append("entorno.carga_por_proceso debe ser un mapa pid -> cargas")
        elif pids_declarados is not None:
            if {str(p) for p in pids_declarados} != set(cargas):
                fallos.append(
                    "entorno.carga_por_proceso no cubre exactamente los procesos declarados"
                )
            for clave, serie in cargas.items():
                if (
                    not isinstance(serie, Sequence)
                    or isinstance(serie, str | bytes)
                    or not serie
                    or not all(
                        isinstance(v, int | float) and not isinstance(v, bool) for v in serie
                    )
                ):
                    fallos.append(f"entorno.carga_por_proceso[{clave}] sin carga registrada")

        incidencias = entorno.get("incidencias")
        if isinstance(incidencias, Sequence) and not isinstance(incidencias, str | bytes):
            if incidencias:
                fallos.append(f"la corrida registro incidencias: {list(incidencias)}")
        elif "incidencias" in entorno:
            fallos.append("entorno.incidencias debe ser una lista")

    procesos = doc.get("procesos")
    if not isinstance(procesos, Sequence) or isinstance(procesos, str | bytes):
        fallos.append("procesos ausente o con forma invalida")
    else:
        entradas = [p for p in procesos if isinstance(p, Mapping)]
        if len(entradas) != len(procesos):
            fallos.append("cada entrada de procesos debe ser un objeto")
        pids = [p.get("pid") for p in entradas]
        if any(not _es_entero(p) for p in pids):
            fallos.append("procesos: cada pid debe ser un entero")
        enteros = [p for p in pids if isinstance(p, int) and not isinstance(p, bool)]
        if any(p <= 0 for p in enteros):
            fallos.append("procesos: cada pid debe ser positivo")
        if len(enteros) < fp.PROCESOS_MINIMOS:
            fallos.append(f"{len(enteros)} procesos; el minimo es {fp.PROCESOS_MINIMOS}")
        if len(set(enteros)) != len(enteros):
            fallos.append("PIDs repetidos: los procesos no son independientes")

    # Toda medida publicada tiene que venir de un proceso declarado, y todo
    # proceso declarado tiene que haber medido: si no, el artefacto contendria
    # observaciones sin origen o procesos fantasma.
    if pids_declarados is not None:
        for seccion in ("escalas", "sondas_unitarias"):
            entradas_medidas = doc.get(seccion)
            if not isinstance(entradas_medidas, Sequence) or isinstance(
                entradas_medidas, str | bytes
            ):
                continue
            observados = {
                int(m["pid"])
                for m in entradas_medidas
                if isinstance(m, Mapping) and _es_entero(m.get("pid"))
            }
            if observados != pids_declarados:
                fallos.append(
                    f"{seccion}: los PIDs medidos {sorted(observados)} no son los procesos "
                    f"declarados {sorted(pids_declarados)}"
                )

    return fallos


def _fallos_contraste(doc: Mapping[str, Any]) -> list[str]:
    contraste = doc.get("contraste_metodo_anterior")
    if not isinstance(contraste, Mapping):
        return ["contraste_metodo_anterior ausente o con forma invalida"]
    fallos: list[str] = []
    if contraste.get("evidencia_anterior") != dict(fp.BLOBS_EVIDENCIA_ANTERIOR):
        fallos.append("el contraste no cita la evidencia anterior por su blob exacto")
    if contraste.get("u_anterior_ns") != fp.U_ANTERIOR_NS:
        fallos.append(f"contraste.u_anterior_ns debe ser {fp.U_ANTERIOR_NS}, el valor publicado")
    if contraste.get("b_anterior_ns") != fp.B_ANTERIOR_NS:
        fallos.append(f"contraste.b_anterior_ns debe ser {fp.B_ANTERIOR_NS}, el valor publicado")
    der = doc.get("derivacion")
    if isinstance(der, Mapping):
        for campo, homologo in (("u_sucesora_ns", "u_ns"), ("b_sucesora_ns", "b_ns")):
            if campo not in contraste:
                fallos.append(f"contraste_metodo_anterior sin campo {campo}")
            elif contraste[campo] != der.get(homologo):
                fallos.append(f"contraste.{campo} no coincide con la derivacion publicada")
    for campo in ("metodo_anterior", "metodo_sucesor", "por_que_cambia", "que_no_cambia"):
        if not isinstance(contraste.get(campo), str) or not contraste.get(campo):
            fallos.append(f"contraste_metodo_anterior.{campo} debe explicarse por escrito")
    return fallos


# --------------------------------------------------------------------------
# Entrada publica
# --------------------------------------------------------------------------


def fallos_suelo_multiescala(doc: Mapping[str, Any]) -> list[str]:
    """Valida el artefacto completo. Lista vacia significa conforme.

    **Total por contrato: nunca lanza.** Un validador que lanzase ante un
    valor JSON legal (``NaN``, cadena donde se espera entero, lista donde se
    espera objeto) dejaria de ser una guarda: quien lo invoca no obtendria
    fallos sino una excepcion, y un artefacto manipulado podria quedar sin
    veredicto. Cualquier fallo interno inesperado se convierte en un fallo de
    validacion explicito.
    """
    try:
        return _fallos_suelo_multiescala(doc)
    except Exception as exc:
        return [f"validacion abortada por documento malformado: {type(exc).__name__}: {exc}"]


def _fallos_suelo_multiescala(doc: Mapping[str, Any]) -> list[str]:
    if not isinstance(doc, Mapping):
        return ["el documento debe ser un objeto JSON"]
    fallos = _fallos_secciones(doc)

    # Igualdad estricta, no `not in (None, X)`: publicar `null` no absuelve.
    if not _texto_no_vacio(doc.get("documento")):
        fallos.append("documento sin titulo")
    if doc.get("version_esquema") != VERSION_ESQUEMA:
        fallos.append(f"version_esquema debe ser {VERSION_ESQUEMA}")
    if doc.get("protocolo") != fp.PROTOCOLO:
        fallos.append("el protocolo declarado no es el aprobado")
    if doc.get("paquete") != fp.PAQUETE:
        fallos.append("el paquete declarado no es el de la preinscripcion sucesora")
    if doc.get("estado") != fp.ESTADO_EVIDENCIA:
        fallos.append("el estado declarado no es el preinscrito")
    if "clasificacion_entorno" in doc:
        fallos.append(
            "no se importa ninguna clasificacion formal de TOL-207 "
            "(por ejemplo ENVOLVENTE_REPRODUCIBLE) sin autoridad que la generalice"
        )

    fallos.extend(_fallos_metodo(doc))
    fallos.extend(_fallos_preinscripcion(doc))
    fallos.extend(_fallos_entorno_y_procesos(doc))
    fallos.extend(_fallos_escalas(doc))
    fallos.extend(_fallos_unitarias(doc))
    fallos.extend(_fallos_calibracion(doc))
    fallos.extend(_fallos_plan(doc))
    fallos.extend(_fallos_diagnosticos(doc))
    fallos.extend(_fallos_controles(doc))
    fallos.extend(_fallos_derivacion(doc))
    fallos.extend(_fallos_regimenes(doc))
    fallos.extend(_fallos_contraste(doc))
    fallos.extend(_fallos_negaciones(doc))

    custodia = doc.get("custodia")
    if not isinstance(custodia, Mapping):
        fallos.append("custodia ausente o con forma invalida")
    else:
        if custodia.get("diff_preinscritos_vacio") is not True:
            fallos.append("custodia: el diff en los ficheros preinscritos no esta vacio")
        if custodia.get("sha_a_es_ancestro") is not True:
            fallos.append("custodia: el commit de preinscripcion no es ancestro de HEAD")
        if custodia.get("reverificada_tras_medir") is not True:
            fallos.append("custodia: no se reverifico despues de medir y antes de publicar")
        if custodia.get("evidencia_anterior_intacta") is not True:
            fallos.append("custodia: no se acredita que la evidencia anterior siga intacta")
        if not _es_sha(custodia.get("head")):
            fallos.append("custodia.head no tiene forma de SHA de commit")

    return fallos
