"""Esquema y validador del futuro artefacto ``suelo_medicion_v0.3.json``.

Se congela en la preinscripcion, ANTES de que exista ninguna observacion.
El validador no mide, no lee ficheros y no ejecuta nada al importarse.

Lo que RECOMPUTA desde los vectores crudos publicados, sin aceptar ningun
valor declarado:

- los percentiles por rango mas cercano de cada entrada;
- el numero de unidades de cada escala, desde la calibracion publicada;
- ``D(s)`` escala a escala, familia a familia;
- la envolvente monotona ``E(s)`` y su cobertura del suelo;
- el cruce exacto ``U = 5 E(s_k)``, su intervalo y sus confirmaciones;
- la continuidad ``m B(U) = 0,20 U``;
- ``SM`` desde las sondas unitarias;
- el regimen, la banda aplicada y el veredicto de cada magnitud;
- la tabla de progresion y la tabla de holgura.

Falla cerrado y es **total por contrato**: nunca lanza.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from experiments.adr002.tolerances import envelope_protocol as ep

VERSION_ESQUEMA: Final = ep.VERSION_ESQUEMA

SECCIONES_OBLIGATORIAS: Final[tuple[str, ...]] = (
    "documento",
    "version_esquema",
    "estado",
    "protocolo",
    "registro",
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
    "contraste_metodos_anteriores",
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
    "blob_registro",
    "blob_linea_base",
    "blobs_evidencias_anteriores",
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
    "b_en_u_ns",
    "m",
    "objetivo_relativo",
    "factor_u",
    "indice_escalon_del_cruce",
    "escalon_del_cruce_ns",
    "intervalo_del_cruce_ns",
    "confirmaciones_posteriores",
    "confirmaciones_minimas",
    "curva",
    "detalle_por_escala",
    "motivo_no_evaluable",
)

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

NEGACIONES_OBLIGATORIAS: Final[tuple[str, ...]] = (
    "limite_duro_tol_107",
    "aprobacion_tol_209",
    "sustitucion_evidencias_anteriores",
    "t0",
    "candidatos",
    "benchmark",
    "merge_pr_117",
)

CAMPOS_METODO_TEXTO: Final[tuple[str, ...]] = (
    "nombre",
    "envolvente",
    "banda",
    "criterio",
    "continuidad",
    "dispersion",
)

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

_HEXADECIMAL: Final = frozenset("0123456789abcdef")


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
    if metodo.get("escalera_ns") != list(ep.ESCALERA_NS):
        fallos.append("metodo.escalera_ns no es la escalera preinscrita")
    if metodo.get("familias") != list(ep.FAMILIAS):
        fallos.append("metodo.familias no son las familias preinscritas")
    if metodo.get("sustituye_metodo_de") != list(ep.EVIDENCIAS_ANTERIORES):
        fallos.append("metodo.sustituye_metodo_de no cita las evidencias anteriores")
    if metodo.get("no_sustituye_evidencia") is not True:
        fallos.append(
            "metodo.no_sustituye_evidencia debe ser True: el paquete 07 cambia el metodo, "
            "no las evidencias anteriores"
        )
    return fallos


def _fallos_preinscripcion(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    pre = doc.get("preinscripcion")
    if not isinstance(pre, Mapping):
        return ["preinscripcion ausente o con forma invalida"]

    fallos.extend(f"preinscripcion sin campo {c}" for c in CAMPOS_PREINSCRIPCION if c not in pre)

    for campo in ("commit_a", "head_en_ejecucion"):
        if campo in pre and not _es_sha(pre[campo]):
            fallos.append(f"preinscripcion.{campo} no tiene forma de SHA de commit")

    blobs = pre.get("blobs_preinscritos")
    if isinstance(blobs, Mapping):
        for ruta in ep.ARCHIVOS_PREINSCRITOS:
            if ruta not in blobs:
                fallos.append(f"blob preinscrito ausente: {ruta}")
            elif not _es_sha(blobs[ruta]):
                fallos.append(f"blob preinscrito sin forma de blob Git: {ruta}")
    elif "blobs_preinscritos" in pre:
        fallos.append("blobs_preinscritos debe ser un mapa ruta -> blob")

    for clave, esperados in (
        ("blobs_heredados", ep.ARCHIVOS_HEREDADOS),
        ("blobs_corpus_congelado", ep.BLOBS_CORPUS_CONGELADO),
    ):
        publicados = pre.get(clave)
        if isinstance(publicados, Mapping):
            for ruta, esperado in esperados.items():
                if ruta not in publicados:
                    fallos.append(f"{clave}: ausente {ruta}")
                elif publicados[ruta] != esperado:
                    fallos.append(f"{clave}: alterado {ruta}")
        elif clave in pre:
            fallos.append(f"{clave} debe ser un mapa ruta -> blob")

    if pre.get("blob_protocolo") != ep.BLOB_PROTOCOLO_APROBADO:
        fallos.append("el blob del protocolo aprobado no coincide")
    if pre.get("blob_registro") != ep.BLOB_REGISTRO_ACTUALIZADO:
        fallos.append("el blob del Registro actualizado no coincide con el acta de gobierno")
    if pre.get("blob_linea_base") != ep.BLOB_LINEA_BASE:
        fallos.append("el blob de la linea base no coincide")
    if pre.get("blobs_evidencias_anteriores") != dict(ep.EVIDENCIAS_ANTERIORES):
        fallos.append(
            "blobs_evidencias_anteriores no coincide con las evidencias v0.1 y v0.2: "
            "el paquete 07 debe citarlas intactas"
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
    if any(int(x) < 0 for x in muestras):
        return [f"{etiqueta}: hay muestras negativas; una duracion no puede serlo"]

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

    if len(valores) >= 2 and all(v % 100 == 0 for v in valores) and len(set(valores)) > 1:
        fallos.append(f"{etiqueta}: vector redondeado antes de persistirse")

    ordenadas = sorted(valores)
    distintos = set(ordenadas)
    esperados = {
        "p50_ns": ep.percentil_ns(ordenadas, 1, 2),
        "p95_ns": ep.percentil_ns(ordenadas, 19, 20),
        "p99_ns": ep.percentil_ns(ordenadas, 99, 100),
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
    if medida["resolucion_percentil"] != ep.resolucion_percentil(len(valores)):
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
    if not isinstance(familia, str) or familia not in ep.FAMILIAS:
        fallos.append(f"{etiqueta}: familia ajena a la preinscripcion: {familia!r}")
    if not _es_entero(escala) or escala not in ep.ESCALERA_NS:
        fallos.append(f"{etiqueta}: escala ajena a la escalera: {escala!r}")
    if not _es_entero(medida["unidades"]) or int(medida["unidades"]) <= 0:
        fallos.append(f"{etiqueta}: unidades debe ser un entero positivo")
    if fallos:
        return fallos

    fallos.extend(
        _fallos_medida_comun(
            medida,
            etiqueta,
            n_esperado=ep.n_para_escala(int(escala)),
            warmup_esperado=ep.WARMUP_ESCALA,
        )
    )
    return fallos


def _fallos_una_unitaria(medida: Mapping[str, Any], indice: int) -> list[str]:
    etiqueta = f"sondas_unitarias[{indice}]"
    ausentes = [f"{etiqueta} sin campo {c}" for c in CAMPOS_UNITARIA if c not in medida]
    if ausentes:
        return ausentes

    sonda = medida["sonda"]
    if not isinstance(sonda, str) or sonda not in ep.SONDAS_UNITARIAS:
        return [f"{etiqueta}: sonda ajena a la preinscripcion: {sonda!r}"]

    return _fallos_medida_comun(
        medida, etiqueta, n_esperado=ep.N_UNITARIA, warmup_esperado=ep.WARMUP_UNITARIA
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

    for familia in ep.FAMILIAS:
        for escala in ep.ESCALERA_NS:
            seleccion = [
                m for m in entradas if m.get("familia") == familia and m.get("escala_ns") == escala
            ]
            pids = {int(m["pid"]) for m in seleccion if _es_entero(m.get("pid"))}
            if not pids:
                fallos.append(f"falta la sonda {familia}@{escala} ns")
            elif len(pids) < ep.PROCESOS_MINIMOS:
                fallos.append(
                    f"{familia}@{escala} ns: {len(pids)} procesos distintos; "
                    f"el minimo es {ep.PROCESOS_MINIMOS}"
                )
            unidades = {int(m["unidades"]) for m in seleccion if _es_entero(m.get("unidades"))}
            if len(unidades) > 1:
                fallos.append(
                    f"{familia}@{escala} ns: los procesos resolvieron cantidades de trabajo "
                    f"distintas {sorted(unidades)}; las ejecuciones no son equivalentes"
                )

    for indice, medida in enumerate(entradas):
        nominal = _entero_o_none(medida.get("escala_ns"))
        p50 = _entero_o_none(medida.get("p50_ns"))
        if nominal is None or p50 is None or nominal not in ep.ESCALERA_NS:
            continue
        if not ep.calibracion_en_banda(p50, nominal):
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
    intrusas = sorted(n for n in nombres if n not in ep.SONDAS_UNITARIAS)
    if intrusas:
        fallos.append(f"sondas unitarias ajenas: {intrusas}")
    faltan = sorted(s for s in ep.SONDAS_UNITARIAS if s not in nombres)
    if faltan:
        fallos.append(f"faltan sondas unitarias: {faltan}")

    for sonda in ep.SONDAS_UNITARIAS:
        pids = {
            int(m["pid"]) for m in entradas if m.get("sonda") == sonda and _es_entero(m.get("pid"))
        }
        if 0 < len(pids) < ep.PROCESOS_MINIMOS:
            fallos.append(
                f"{sonda}: {len(pids)} procesos distintos; el minimo es {ep.PROCESOS_MINIMOS}"
            )

    for indice, medida in enumerate(entradas):
        fallos.extend(_fallos_una_unitaria(medida, indice))

    fallos.extend(ep.comprobar_neutralidad(sorted(nombres)))
    return fallos


# --------------------------------------------------------------------------
# Reconstruccion tipada
# --------------------------------------------------------------------------


def _medidas_desde_escalas(doc: Mapping[str, Any]) -> list[ep.MedidaEscala] | None:
    escalas = doc.get("escalas")
    if not isinstance(escalas, Sequence) or isinstance(escalas, str | bytes):
        return None
    medidas: list[ep.MedidaEscala] = []
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
            ep.MedidaEscala(
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


def _unitarias_desde_doc(doc: Mapping[str, Any]) -> list[ep.MedidaUnitaria] | None:
    unitarias = doc.get("sondas_unitarias")
    if not isinstance(unitarias, Sequence) or isinstance(unitarias, str | bytes):
        return None
    medidas: list[ep.MedidaUnitaria] = []
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
            ep.MedidaUnitaria(
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


def _cruce_recomputado(doc: Mapping[str, Any]) -> ep.Cruce | None:
    medidas = _medidas_desde_escalas(doc)
    if medidas is None:
        return None
    try:
        return ep.resolver_cruce(ep.construir_envolvente(medidas))
    except (
        ep.SondaNoNeutralError,
        ep.ProcesosInsuficientesError,
        ep.EscaleraInvalidaError,
        ep.InvarianteVioladoError,
        ValueError,
    ):
        return None


# --------------------------------------------------------------------------
# Calibracion y plan
# --------------------------------------------------------------------------


def _unidades_publicadas(doc: Mapping[str, Any]) -> dict[tuple[str, int], int]:
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
    for familia in ep.FAMILIAS:
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
        if referencia != ep.UNIDADES_REFERENCIA[familia]:
            fallos.append(
                f"calibracion[{familia}]: unidades_referencia {referencia} distinta de la "
                f"preinscrita {ep.UNIDADES_REFERENCIA[familia]}"
            )
        muestras = entrada["muestras_ns"]
        if (
            not isinstance(muestras, Sequence)
            or isinstance(muestras, str | bytes)
            or len(muestras) != ep.MUESTRAS_CALIBRACION
            or not all(_es_entero(v) for v in muestras)
        ):
            fallos.append(
                f"calibracion[{familia}]: se exigen {ep.MUESTRAS_CALIBRACION} muestras enteras"
            )
        elif ep.p50_ns([int(v) for v in muestras]) != coste:
            fallos.append(
                f"calibracion[{familia}]: coste_referencia_ns no es el P50 de sus muestras"
            )

        por_escala = entrada["unidades_por_escala"]
        if not isinstance(por_escala, Mapping):
            fallos.append(f"calibracion[{familia}].unidades_por_escala debe ser un mapa")
            continue
        for escala in ep.ESCALERA_NS:
            publicado = por_escala.get(str(escala))
            esperado = ep.unidades_para_escala(
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
    if plan.get("procesos") != ep.PROCESOS_MINIMOS:
        fallos.append(f"plan.procesos debe ser {ep.PROCESOS_MINIMOS}")
    if plan.get("rondas") != ep.RONDAS_ROUND_ROBIN:
        fallos.append(f"plan.rondas debe ser {ep.RONDAS_ROUND_ROBIN}")
    if plan.get("escalera_ns") != list(ep.ESCALERA_NS):
        fallos.append("plan.escalera_ns no es la escalera preinscrita")
    if plan.get("familias") != list(ep.FAMILIAS):
        fallos.append("plan.familias no son las familias preinscritas")
    if plan.get("warmup_por_escala") != ep.WARMUP_ESCALA:
        fallos.append(f"plan.warmup_por_escala debe ser {ep.WARMUP_ESCALA}")
    if plan.get("n_unitaria") != ep.N_UNITARIA:
        fallos.append(f"plan.n_unitaria debe ser {ep.N_UNITARIA}")
    if plan.get("warmup_unitaria") != ep.WARMUP_UNITARIA:
        fallos.append(f"plan.warmup_unitaria debe ser {ep.WARMUP_UNITARIA}")
    if plan.get("semilla") != ep.SEMILLA:
        fallos.append(f"plan.semilla debe ser {ep.SEMILLA}")
    if plan.get("n_por_escala") != {str(s): ep.n_para_escala(s) for s in ep.ESCALERA_NS}:
        fallos.append("plan.n_por_escala no coincide con el preinscrito")
    esperado_orden = [[familia, escala] for familia, escala in ep.pares_de_escalera()]
    if plan.get("orden") != esperado_orden * ep.RONDAS_ROUND_ROBIN:
        fallos.append("plan.orden no es el round-robin preinscrito")

    unidades = plan.get("unidades")
    medidas = _unidades_publicadas(doc)
    if not isinstance(unidades, Mapping):
        fallos.append("plan.unidades debe ser un mapa familia -> escala -> unidades")
    else:
        for familia in ep.FAMILIAS:
            por_familia = unidades.get(familia)
            if not isinstance(por_familia, Mapping):
                fallos.append(f"plan.unidades sin la familia {familia}")
                continue
            for escala in ep.ESCALERA_NS:
                declarado = por_familia.get(str(escala))
                medido = medidas.get((familia, escala))
                if medido is not None and declarado != medido:
                    fallos.append(
                        f"plan.unidades[{familia}][{escala}] = {declarado!r} pero se midieron "
                        f"{medido} unidades"
                    )
    return fallos


# --------------------------------------------------------------------------
# Derivacion: envolvente y cruce recomputados
# --------------------------------------------------------------------------


def _curva_esperada(cruce: ep.Cruce) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for indice, escala in enumerate(ep.ESCALERA_NS):
        dispersion = cruce.envolvente.dispersiones[indice]
        envolvente = cruce.envolvente.envolvente[indice]
        filas.append(
            {
                "escala_ns": escala,
                "dispersion_ns": dispersion,
                "envolvente_ns": envolvente,
                "razon_dispersion_por_mil": ep.razon_por_mil(dispersion, escala),
                "razon_envolvente_por_mil": ep.razon_por_mil(envolvente, escala),
                "sostenible": cruce.sostenibles[indice],
            }
        )
    return filas


def _detalle_esperado(medidas: Sequence[ep.MedidaEscala]) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for escala in ep.ESCALERA_NS:
        for familia in ep.FAMILIAS:
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


def _fallos_derivacion(doc: Mapping[str, Any]) -> list[str]:
    der = doc.get("derivacion")
    if not isinstance(der, Mapping):
        return ["derivacion ausente o con forma invalida"]

    fallos = [f"derivacion sin campo {c}" for c in CAMPOS_DERIVACION if c not in der]
    if fallos:
        return fallos

    if der["m"] != ep.MARGEN_M:
        fallos.append(f"m debe ser {ep.MARGEN_M}; se publico {der['m']!r}")
    if der["factor_u"] != ep.FACTOR_U:
        fallos.append(f"factor_u debe ser {ep.FACTOR_U}; se publico {der['factor_u']!r}")
    objetivo = f"{ep.OBJETIVO_RELATIVO_NUM}/{ep.OBJETIVO_RELATIVO_DEN}"
    if der["objetivo_relativo"] != objetivo:
        fallos.append(f"objetivo_relativo debe ser {objetivo}; no se elige en este paquete")
    if der["confirmaciones_minimas"] != ep.CONFIRMACIONES_MINIMAS:
        fallos.append(f"confirmaciones_minimas debe ser {ep.CONFIRMACIONES_MINIMAS}")

    cruce = _cruce_recomputado(doc)
    if cruce is None:
        return [
            *fallos,
            "cruce no verificable: las escalas publicadas no permiten recomputarlo "
            "(campos ausentes, tipos invalidos o cobertura insuficiente)",
        ]

    if der["u_ns"] != cruce.u:
        fallos.append(
            f"derivacion.u_ns publicado {der['u_ns']!r} no coincide con el cruce recomputado "
            f"({cruce.u!r})"
        )
    if der["b_en_u_ns"] != cruce.b_en_u:
        fallos.append(
            f"derivacion.b_en_u_ns publicado {der['b_en_u_ns']!r} no coincide con el "
            f"recomputado ({cruce.b_en_u!r})"
        )
    if der["indice_escalon_del_cruce"] != cruce.indice_escalon:
        fallos.append("derivacion.indice_escalon_del_cruce no coincide con el recomputado")
    if der["confirmaciones_posteriores"] != cruce.confirmaciones:
        fallos.append("derivacion.confirmaciones_posteriores no coincide con el recomputado")

    escalon = cruce.indice_escalon
    esperado_escalon = None if escalon is None else ep.ESCALERA_NS[escalon]
    if der["escalon_del_cruce_ns"] != esperado_escalon:
        fallos.append("derivacion.escalon_del_cruce_ns no coincide con el recomputado")
    esperado_intervalo = (
        None
        if escalon is None
        else [0 if escalon == 0 else ep.ESCALERA_NS[escalon - 1], ep.ESCALERA_NS[escalon]]
    )
    if der["intervalo_del_cruce_ns"] != esperado_intervalo:
        fallos.append("derivacion.intervalo_del_cruce_ns no coincide con el recomputado")

    if cruce.evaluable:
        u, banda = cruce.u, cruce.b_en_u
        assert u is not None and banda is not None
        if der["resultado"] != "RESUELTO":
            fallos.append("derivacion.resultado debe ser RESUELTO cuando hay cruce")
        if der["motivo_no_evaluable"] is not None:
            fallos.append("derivacion.motivo_no_evaluable debe ser null con cruce resuelto")
        if not ep.continuidad_exacta(cruce):
            fallos.append("la continuidad m*B(U) = 0,20 U no se cumple de forma exacta")
        if ep.FACTOR_U * banda != u:
            fallos.append(f"U debe ser {ep.FACTOR_U} * B(U)")
        if cruce.confirmaciones < ep.CONFIRMACIONES_MINIMAS:
            fallos.append("el cruce no tiene escalas medidas posteriores que lo confirmen")
        # El cruce vive DENTRO del intervalo de su escalon: es lo que hace que
        # B(U) sea el valor de ese escalon y la continuidad sea exacta.
        if esperado_intervalo is not None and not (
            esperado_intervalo[0] < u <= esperado_intervalo[1]
        ):
            fallos.append("U fuera del intervalo del escalon del cruce")
    else:
        if der["resultado"] != ep.NO_EVALUABLE:
            fallos.append(f"derivacion.resultado debe ser {ep.NO_EVALUABLE} sin cruce")
        if der["u_ns"] is not None or der["b_en_u_ns"] is not None:
            fallos.append("sin cruce no se pueden publicar U ni la banda en U")
        if not _texto_no_vacio(der["motivo_no_evaluable"]):
            fallos.append(f"{ep.NO_EVALUABLE} exige motivo explicito y no vacio")

    if not cruce.envolvente.es_monotona():
        fallos.append("la envolvente publicada no es monotona no decreciente")
    if not cruce.envolvente.cubre_el_suelo():
        fallos.append("la envolvente no cubre la dispersion medida en algun escalon")
    if not ep.banda_no_decreciente(cruce.envolvente):
        fallos.append("la banda se estrecha al crecer la magnitud: reabre el riesgo M-03")

    if der["curva"] != _curva_esperada(cruce):
        fallos.append("derivacion.curva no coincide con la recomputada desde las escalas")

    medidas = _medidas_desde_escalas(doc)
    if medidas is not None and der["detalle_por_escala"] != _detalle_esperado(medidas):
        fallos.append("derivacion.detalle_por_escala no coincide con la descomposicion recomputada")

    unitarias = _unitarias_desde_doc(doc)
    if unitarias is None:
        fallos.append("SM no verificable: las sondas unitarias publicadas no permiten recomputarlo")
    else:
        try:
            esperado_sm = ep.calcular_sm(unitarias)
        except ep.SondaNoNeutralError, ep.ProcesosInsuficientesError, ep.EscaleraInvalidaError:
            fallos.append("SM no verificable desde las sondas unitarias publicadas")
        else:
            if der["sm_ns"] != esperado_sm:
                fallos.append(
                    f"derivacion.sm_ns publicado {der['sm_ns']!r} no coincide con el "
                    f"recomputado ({esperado_sm})"
                )

    return fallos


# --------------------------------------------------------------------------
# Regimenes por percentil
# --------------------------------------------------------------------------


def _fallos_regimenes(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    regimenes = doc.get("regimenes_por_percentil")
    if not isinstance(regimenes, Sequence) or isinstance(regimenes, str | bytes):
        return ["regimenes_por_percentil ausente o con forma invalida"]
    if not regimenes:
        return ["regimenes_por_percentil vacio: el artefacto debe publicar su veredicto"]

    der = doc.get("derivacion")
    sm = _entero_o_none(der.get("sm_ns")) if isinstance(der, Mapping) else None
    cruce = _cruce_recomputado(doc)
    validos = {ep.REGIMEN_RELATIVO, ep.REGIMEN_ABSOLUTO}

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

        if min95 < min50:
            fallos.append(f"{etiqueta}: invariante violado min_s P95 < min_s P50")
        if max50 < min50 or max95 < min95:
            fallos.append(f"{etiqueta}: maximo por debajo del minimo")

        no_evaluable = entrada.get("resultado") == ep.NO_EVALUABLE

        if cruce is None or not cruce.evaluable:
            if not no_evaluable:
                fallos.append(
                    f"{etiqueta}: sin umbral resuelto no se puede clasificar; se exige "
                    f"{ep.NO_EVALUABLE}"
                )
            elif entrada.get("motivo") != ep.MOTIVO_UMBRAL_NO_RESUELTO:
                fallos.append(f"{etiqueta}: el motivo debe ser {ep.MOTIVO_UMBRAL_NO_RESUELTO}")
            if entrada.get("p50") is not None or entrada.get("p95") is not None:
                fallos.append(f"{etiqueta}: sin umbral no se publica regimen por percentil")
            continue

        u = cruce.u
        assert u is not None
        if sm is not None:
            dominada = min95 < sm
            if dominada and not no_evaluable:
                fallos.append(
                    f"{etiqueta}: min_s P95 ({min95}) < SM ({sm}) pero no se declaro "
                    f"{ep.NO_EVALUABLE}: la guarda de dominancia se eludio"
                )
            if no_evaluable and not dominada:
                fallos.append(
                    f"{etiqueta}: se declaro {ep.NO_EVALUABLE} sin que min_s P95 ({min95}) "
                    f"quede por debajo de SM ({sm})"
                )
            if dominada and no_evaluable and entrada.get("motivo") != ep.MOTIVO_DOMINADA:
                fallos.append(f"{etiqueta}: el motivo debe ser {ep.MOTIVO_DOMINADA}")

        if no_evaluable:
            if entrada.get("p50") is not None or entrada.get("p95") is not None:
                fallos.append(
                    f"{etiqueta}: {ep.NO_EVALUABLE} no puede publicar regimen por percentil"
                )
            continue

        r50, r95 = entrada.get("p50"), entrada.get("p95")
        if not isinstance(r50, str) or not isinstance(r95, str):
            fallos.append(f"{etiqueta}: regimen por percentil ausente o invalido")
            continue
        if r50 not in validos or r95 not in validos:
            fallos.append(f"{etiqueta}: regimen por percentil ausente o invalido")
            continue
        if r50 == ep.REGIMEN_RELATIVO and r95 == ep.REGIMEN_ABSOLUTO:
            fallos.append(f"{etiqueta}: combinacion imposible P50 relativo / P95 absoluto")

        for nombre, minimo, declarado, clave in (
            ("P50", min50, r50, "banda_p50_ns"),
            ("P95", min95, r95, "banda_p95_ns"),
        ):
            esperado = ep.regimen_de_percentil(minimo, u)
            if declarado != esperado:
                fallos.append(
                    f"{etiqueta}: {nombre} declarado '{declarado}' pero con min={minimo} y "
                    f"U={u} corresponde '{esperado}'"
                )
                continue
            # La banda publicada debe salir de la envolvente recomputada.
            if esperado == ep.REGIMEN_RELATIVO:
                if entrada.get(clave) is not None:
                    fallos.append(f"{etiqueta}: {nombre} en relativo no aplica banda")
            else:
                try:
                    banda = cruce.envolvente.banda(minimo)
                except ValueError, ep.EscaleraInvalidaError:
                    fallos.append(f"{etiqueta}: {nombre} sin banda definida para min={minimo}")
                    continue
                if entrada.get(clave) != banda:
                    fallos.append(
                        f"{etiqueta}: {nombre} publico banda {entrada.get(clave)!r} y la "
                        f"envolvente da {banda}"
                    )

        esperado_resultado = _resultado_esperado(min50, max50, min95, max95, cruce=cruce)
        if entrada.get("resultado") != esperado_resultado:
            fallos.append(
                f"{etiqueta}: resultado {entrada.get('resultado')!r} no coincide con el "
                f"recomputado ({esperado_resultado})"
            )

    return fallos


def _resultado_esperado(min50: int, max50: int, min95: int, max95: int, *, cruce: ep.Cruce) -> str:
    u = cruce.u
    assert u is not None

    def _pasa(minimo: int, maximo: int) -> bool:
        if ep.regimen_de_percentil(minimo, u) == ep.REGIMEN_RELATIVO:
            return ep.pasa_relativo(minimo, maximo)
        return ep.pasa_absoluto(minimo, maximo, cruce.envolvente.banda(minimo))

    return "VALIDA" if _pasa(min50, max50) and _pasa(min95, max95) else "INVALIDA"


# --------------------------------------------------------------------------
# Controles, diagnosticos, negaciones y custodia
# --------------------------------------------------------------------------


def _fallos_controles(doc: Mapping[str, Any]) -> list[str]:
    controles = doc.get("controles_internos")
    if not isinstance(controles, Mapping):
        return ["controles_internos ausente o con forma invalida"]

    fallos = [
        f"control bloqueante ausente: {c}" for c in ep.CONTROLES_BLOQUEANTES if c not in controles
    ]
    fallidos = [
        c for c in ep.CONTROLES_BLOQUEANTES if c in controles and controles.get(c) is not True
    ]

    der = doc.get("derivacion")
    publica_valores = isinstance(der, Mapping) and (
        der.get("u_ns") is not None or der.get("b_en_u_ns") is not None
    )
    if publica_valores and fallidos:
        fallos.append(f"se publicaron U o B con controles bloqueantes fallidos: {sorted(fallidos)}")
    if not publica_valores:
        indebidos = sorted(c for c in fallidos if c not in ep.CONTROLES_QUE_EXIGEN_UMBRAL)
        if indebidos:
            fallos.append(
                f"{ep.NO_EVALUABLE} no absuelve controles bloqueantes fallidos: {indebidos}"
            )
        for control in ep.CONTROLES_QUE_EXIGEN_UMBRAL:
            if controles.get(control) is not False:
                fallos.append(f"{control} no puede declararse satisfecho sin umbral resuelto")
    return fallos


def _fallos_diagnosticos(doc: Mapping[str, Any]) -> list[str]:
    diagnosticos = doc.get("diagnosticos")
    if not isinstance(diagnosticos, Mapping):
        return ["diagnosticos ausente o con forma invalida"]
    fallos = [f"diagnostico ausente: {n}" for n in ep.DIAGNOSTICOS if n not in diagnosticos]
    pids = _pids_declarados(doc)
    esperados = len(pids) if pids is not None else ep.PROCESOS_MINIMOS

    referencia = diagnosticos.get(ep.DIAG_REFERENCIA)
    if isinstance(referencia, Mapping):
        por_proceso = referencia.get("por_proceso")
        if not isinstance(por_proceso, Sequence) or isinstance(por_proceso, str | bytes):
            fallos.append(f"{ep.DIAG_REFERENCIA}.por_proceso debe ser una lista")
        else:
            if len(por_proceso) != esperados:
                fallos.append(
                    f"{ep.DIAG_REFERENCIA}: {len(por_proceso)} entradas para {esperados} procesos"
                )
            for indice, entrada in enumerate(por_proceso):
                if not isinstance(entrada, Mapping):
                    fallos.append(f"{ep.DIAG_REFERENCIA}[{indice}] debe ser un objeto")
                    continue
                if entrada.get("vueltas") != ep.VUELTAS_REFERENCIA:
                    fallos.append(
                        f"{ep.DIAG_REFERENCIA}[{indice}]: el trabajo de referencia debe ser "
                        f"{ep.VUELTAS_REFERENCIA} vueltas"
                    )
                valores = [
                    _entero_o_none(entrada.get(c))
                    for c in ("p50_inicio_ns", "p50_mitad_ns", "p50_final_ns")
                ]
                if any(v is None for v in valores):
                    fallos.append(f"{ep.DIAG_REFERENCIA}[{indice}]: los P50 deben ser enteros")
                    continue
                inicio, mitad, final = (int(v) for v in valores if v is not None)
                if not ep.referencia_estable(inicio, mitad, final):
                    fallos.append(
                        f"{ep.DIAG_REFERENCIA}[{indice}]: deriva o throttling dentro del proceso"
                    )

    progresion = diagnosticos.get(ep.DIAG_PROGRESION)
    if isinstance(progresion, Mapping):
        por_proceso = progresion.get("por_proceso")
        if not isinstance(por_proceso, Sequence) or isinstance(por_proceso, str | bytes):
            fallos.append(f"{ep.DIAG_PROGRESION}.por_proceso debe ser una lista")
        else:
            if len(por_proceso) != esperados:
                fallos.append(
                    f"{ep.DIAG_PROGRESION}: {len(por_proceso)} entradas para {esperados} procesos"
                )
            fallos.extend(_fallos_progresion(por_proceso, pids))
            fallos.extend(_fallos_progresion_contra_escalas(doc, por_proceso))

    fallos.extend(_fallos_curva_diagnostica(doc, diagnosticos))
    fallos.extend(_fallos_holgura(doc, diagnosticos))

    clasificacion = doc.get("clasificacion_diagnostica_linea_base")
    if not isinstance(clasificacion, Mapping):
        fallos.append("clasificacion_diagnostica_linea_base debe ser un objeto")
    else:
        if clasificacion.get("fuente") != ep.RUTA_LINEA_BASE:
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


def _fallos_curva_diagnostica(doc: Mapping[str, Any], diagnosticos: Mapping[str, Any]) -> list[str]:
    curva = diagnosticos.get(ep.DIAG_ENVOLVENTE)
    if not isinstance(curva, Mapping):
        return [f"{ep.DIAG_ENVOLVENTE} ausente o con forma invalida"]
    cruce = _cruce_recomputado(doc)
    if cruce is None:
        return []
    if curva.get("curva") != _curva_esperada(cruce):
        return [f"{ep.DIAG_ENVOLVENTE}.curva no coincide con la recomputada"]
    return []


def _fallos_holgura(doc: Mapping[str, Any], diagnosticos: Mapping[str, Any]) -> list[str]:
    holgura = diagnosticos.get(ep.DIAG_HOLGURA)
    if not isinstance(holgura, Mapping):
        return [f"{ep.DIAG_HOLGURA} ausente o con forma invalida"]
    cruce = _cruce_recomputado(doc)
    if cruce is None:
        return []
    esperada = [dict(fila) for fila in ep.holgura_por_escalon(cruce)]
    if holgura.get("por_escalon") != esperada:
        return [f"{ep.DIAG_HOLGURA}.por_escalon no coincide con la recomputada"]
    return []


def _progresion_esperada(doc: Mapping[str, Any]) -> dict[int, list[dict[str, Any]]] | None:
    medidas = _medidas_desde_escalas(doc)
    if medidas is None:
        return None
    indice: dict[tuple[int, str, int], ep.MedidaEscala] = {
        (m.pid, m.familia, m.escala_ns): m for m in medidas
    }
    tabla: dict[int, list[dict[str, Any]]] = {}
    for pid in sorted({m.pid for m in medidas}):
        filas: list[dict[str, Any]] = []
        for familia in ep.FAMILIAS:
            for menor, mayor in zip(ep.ESCALERA_NS, ep.ESCALERA_NS[1:], strict=False):
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
                        "exigible": ep.progresion_exigible(a.unidades, b.unidades),
                        "progresa": ep.escala_progresa(a.p50, menor, b.p50, mayor),
                    }
                )
        tabla[pid] = filas
    return tabla


def _fallos_progresion(por_proceso: Sequence[Any], pids: set[int] | None) -> list[str]:
    fallos: list[str] = []
    filas_esperadas = len(ep.FAMILIAS) * (len(ep.ESCALERA_NS) - 1)
    for indice, entrada in enumerate(por_proceso):
        if not isinstance(entrada, Mapping):
            fallos.append(f"{ep.DIAG_PROGRESION}[{indice}] debe ser un objeto")
            continue
        if pids is not None and entrada.get("pid") not in pids:
            fallos.append(f"{ep.DIAG_PROGRESION}[{indice}]: pid ajeno a los procesos declarados")
        filas = entrada.get("filas")
        if not isinstance(filas, Sequence) or isinstance(filas, str | bytes):
            fallos.append(f"{ep.DIAG_PROGRESION}[{indice}].filas debe ser una lista")
            continue
        if len(filas) != filas_esperadas:
            fallos.append(
                f"{ep.DIAG_PROGRESION}[{indice}]: {len(filas)} filas para "
                f"{filas_esperadas} pares consecutivos de la escalera"
            )
        for posicion, fila in enumerate(filas):
            etiqueta = f"{ep.DIAG_PROGRESION}[{indice}].filas[{posicion}]"
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
            exigible = ep.progresion_exigible(u_menor, u_mayor)
            progresa = ep.escala_progresa(p50_menor, menor, p50_mayor, mayor)
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
        return []
    fallos: list[str] = []
    vistos: set[int] = set()
    for indice, entrada in enumerate(por_proceso):
        if not isinstance(entrada, Mapping):
            continue
        pid = _entero_o_none(entrada.get("pid"))
        if pid is None or pid not in esperada:
            fallos.append(f"{ep.DIAG_PROGRESION}[{indice}]: sin pid reconocible")
            continue
        vistos.add(pid)
        if entrada.get("filas") != esperada[pid]:
            fallos.append(
                f"{ep.DIAG_PROGRESION}[{indice}]: la tabla no coincide con la recomputada "
                f"desde las escalas publicadas del proceso {pid}"
            )
    faltan = sorted(set(esperada) - vistos)
    if faltan:
        fallos.append(f"{ep.DIAG_PROGRESION}: sin tabla para los procesos {faltan}")
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
        if len(enteros) < ep.PROCESOS_MINIMOS:
            fallos.append(f"{len(enteros)} procesos; el minimo es {ep.PROCESOS_MINIMOS}")
        if len(set(enteros)) != len(enteros):
            fallos.append("PIDs repetidos: los procesos no son independientes")

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
    contraste = doc.get("contraste_metodos_anteriores")
    if not isinstance(contraste, Mapping):
        return ["contraste_metodos_anteriores ausente o con forma invalida"]
    fallos: list[str] = []
    if contraste.get("evidencias_anteriores") != dict(ep.EVIDENCIAS_ANTERIORES):
        fallos.append("el contraste no cita las evidencias anteriores por su blob exacto")
    for campo, esperado in (
        ("u_paquete_05_ns", ep.U_PAQUETE_05_NS),
        ("b_paquete_05_ns", ep.B_PAQUETE_05_NS),
        ("u_paquete_06_ns", ep.U_PAQUETE_06_NS),
        ("b_paquete_06_ns", ep.B_PAQUETE_06_NS),
    ):
        if contraste.get(campo) != esperado:
            fallos.append(f"contraste.{campo} debe ser {esperado}, el valor publicado")
    der = doc.get("derivacion")
    if isinstance(der, Mapping):
        for campo, homologo in (
            ("u_paquete_07_ns", "u_ns"),
            ("b_en_u_paquete_07_ns", "b_en_u_ns"),
        ):
            if campo not in contraste:
                fallos.append(f"contraste_metodos_anteriores sin campo {campo}")
            elif contraste[campo] != der.get(homologo):
                fallos.append(f"contraste.{campo} no coincide con la derivacion publicada")
    for campo in (
        "metodo_paquete_05",
        "metodo_paquete_06",
        "metodo_paquete_07",
        "por_que_cambia",
        "que_no_cambia",
    ):
        if not _texto_no_vacio(contraste.get(campo)):
            fallos.append(f"contraste_metodos_anteriores.{campo} debe explicarse por escrito")
    return fallos


# --------------------------------------------------------------------------
# Entrada publica
# --------------------------------------------------------------------------


def fallos_banda_envolvente(doc: Mapping[str, Any]) -> list[str]:
    """Valida el artefacto completo. Lista vacia significa conforme.

    **Total por contrato: nunca lanza.**
    """
    try:
        return _fallos_banda_envolvente(doc)
    except Exception as exc:
        return [f"validacion abortada por documento malformado: {type(exc).__name__}: {exc}"]


def _fallos_banda_envolvente(doc: Mapping[str, Any]) -> list[str]:
    if not isinstance(doc, Mapping):
        return ["el documento debe ser un objeto JSON"]
    fallos = _fallos_secciones(doc)

    if not _texto_no_vacio(doc.get("documento")):
        fallos.append("documento sin titulo")
    if doc.get("version_esquema") != VERSION_ESQUEMA:
        fallos.append(f"version_esquema debe ser {VERSION_ESQUEMA}")
    if doc.get("protocolo") != ep.PROTOCOLO:
        fallos.append("el protocolo declarado no es el aprobado")
    if doc.get("registro") != ep.REGISTRO:
        fallos.append("el Registro declarado no es el vigente")
    if doc.get("paquete") != ep.PAQUETE:
        fallos.append("el paquete declarado no es el de la preinscripcion del paquete 07")
    if doc.get("estado") != ep.ESTADO_EVIDENCIA:
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
        for clave, mensaje in (
            ("diff_preinscritos_vacio", "el diff en los ficheros preinscritos no esta vacio"),
            ("sha_a_es_ancestro", "el commit de preinscripcion no es ancestro de HEAD"),
            ("reverificada_tras_medir", "no se reverifico despues de medir y antes de publicar"),
            (
                "evidencias_anteriores_intactas",
                "no se acredita que las evidencias v0.1 y v0.2 sigan intactas",
            ),
            ("registro_actualizado_intacto", "no se acredita que el Registro siga intacto"),
        ):
            if custodia.get(clave) is not True:
                fallos.append(f"custodia: {mensaje}")
        if not _es_sha(custodia.get("head")):
            fallos.append("custodia.head no tiene forma de SHA de commit")

    return fallos
