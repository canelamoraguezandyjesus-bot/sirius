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
    "media_truncada_ns",
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

    # Comparacion ESTRICTA: un `None` explicito no puede ser mas permisivo
    # que un valor distinto. La clave existe, asi que `_fallos_secciones` no
    # la ve ausente; sin igualdad estricta, publicar `null` la absolvia.
    if pre.get("blob_protocolo") != fp.BLOB_PROTOCOLO_APROBADO:
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
    # Una duracion medida con reloj monotonico no puede ser negativa: si lo
    # es, el reloj retrocedio o el vector se manipulo. Falla cerrado.
    if any(int(x) < 0 for x in muestras):
        fallos.append(f"{etiqueta}: hay muestras negativas; una duracion no puede serlo")
        return fallos

    # El TIPO de cada campo normativo se valida ANTES de usarlo. Sin esta
    # guarda previa, un campo no entero (pid como cadena, min_ns como NaN)
    # o desactivaba en silencio la recomputacion de la derivacion, o hacia
    # que el validador lanzase excepcion en vez de devolver un fallo.
    enteros = ("pid", "n", "warmup_descartado", "p50_ns", "p95_ns", "p99_ns", "min_ns", "max_ns")
    for campo in (*enteros, "media_truncada_ns"):
        if not _es_entero(medida[campo]):
            fallos.append(f"{etiqueta}: {campo} debe ser un entero en nanosegundos")
    if not isinstance(medida["sonda"], str):
        fallos.append(f"{etiqueta}: sonda debe ser una cadena")
    if fallos:
        return fallos

    valores = [int(x) for x in muestras]
    n_declarado = int(medida["n"])
    if n_declarado != len(valores):
        fallos.append(f"{etiqueta}: n declarado ({n_declarado}) != longitud del vector")

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
        "media_truncada_ns": sum(ordenadas) // len(ordenadas),
    }
    for campo, esperado in esperados.items():
        if medida[campo] != esperado:
            fallos.append(
                f"{etiqueta}: {campo} publicado {medida[campo]!r} != nearest-rank {esperado}"
            )

    if medida["sonda"] in fp.F_NORMATIVO and n_declarado < fp.N_SONDA_F:
        fallos.append(f"{etiqueta}: n={n_declarado} por debajo del minimo {fp.N_SONDA_F}")

    warmup = int(medida["warmup_descartado"])
    if warmup < 0:
        fallos.append(f"{etiqueta}: warmup_descartado invalido")
    # El warm-up preinscrito no es orientativo: un artefacto que declare
    # otro numero para una sonda de F se contradice con su propio plan.
    elif medida["sonda"] in fp.F_NORMATIVO and warmup != fp.WARMUP_SONDA_F:
        fallos.append(
            f"{etiqueta}: warmup_descartado={warmup} difiere del preinscrito {fp.WARMUP_SONDA_F}"
        )

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
        # Solo los pid enteros cuentan: un pid no hashable (lista, dict) no
        # puede entrar en un conjunto, y su tipo invalido ya lo reporta
        # ``_fallos_una_medida``.
        pids = {
            int(m["pid"]) for m in medidas if m.get("sonda") == sonda and _es_entero(m.get("pid"))
        }
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

    fallos.extend(_fallos_derivacion_recomputada(doc, der))

    return fallos


def _medidas_desde_sondas(doc: Mapping[str, Any]) -> list[fp.MedidaSonda] | None:
    """Reconstruye las medidas desde la seccion ``sondas`` publicada.

    Devuelve ``None`` SOLO si la seccion es irreconstruible. Quien llama
    debe tratar ese ``None`` como fallo, nunca como conformidad: de lo
    contrario un campo con tipo manipulado desactivaria la recomputacion.
    """
    sondas = doc.get("sondas")
    if not isinstance(sondas, Sequence) or isinstance(sondas, str | bytes):
        return None
    medidas: list[fp.MedidaSonda] = []
    for entrada in sondas:
        if not isinstance(entrada, Mapping):
            return None
        enteros = (
            "pid",
            "n",
            "warmup_descartado",
            "p50_ns",
            "p95_ns",
            "p99_ns",
            "min_ns",
            "max_ns",
            "media_truncada_ns",
        )
        if "sonda" not in entrada or any(c not in entrada for c in enteros):
            return None
        # TODO campo se comprueba antes de convertir: ningun valor JSON legal
        # (NaN, cadena, lista) puede hacer que esta funcion lance.
        if not all(_es_entero(entrada[c]) for c in enteros):
            return None
        if not isinstance(entrada["sonda"], str):
            return None
        medidas.append(
            fp.MedidaSonda(
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


def _fallos_derivacion_recomputada(doc: Mapping[str, Any], der: Mapping[str, Any]) -> list[str]:
    """La derivacion publicada debe salir EXACTAMENTE de las sondas publicadas.

    Sin esta recomputacion, un artefacto podria publicar una derivacion
    incoherente con sus propios vectores sin que el validador lo detecte.

    Falla cerrado: si las sondas no permiten recomputar, o la recomputacion
    no es aplicable, el artefacto NO puede publicar derivacion.
    """
    medidas = _medidas_desde_sondas(doc)
    if medidas is None:
        return [
            "derivacion no verificable: las sondas publicadas no permiten recomputarla "
            "(campos ausentes o de tipo invalido)"
        ]
    try:
        esperada = fp.derivar(medidas)
        descomposicion_esperada = fp.descomposicion_b(medidas)
    except (fp.SondaFueraDeFError, fp.ProcesosInsuficientesError) as exc:
        return [f"derivacion no verificable desde las sondas publicadas: {exc}"]

    fallos: list[str] = []
    publicados = {
        "sm_ns": esperada.sm,
        "b50_ns": esperada.b50,
        "b95_ns": esperada.b95,
        "b_ns": esperada.b,
        "u_ns": esperada.u,
    }
    for campo, valor_esperado in publicados.items():
        if der.get(campo) != valor_esperado:
            fallos.append(
                f"derivacion.{campo} publicado {der.get(campo)!r} no coincide con la "
                f"recomputacion desde las sondas publicadas ({valor_esperado})"
            )

    descomposicion = der.get("descomposicion_b")
    if isinstance(descomposicion, Mapping):
        for sonda, valores in descomposicion_esperada.items():
            entrada = descomposicion.get(sonda)
            if isinstance(entrada, Mapping) and (
                entrada.get("b50_ns") != valores["b50_ns"]
                or entrada.get("b95_ns") != valores["b95_ns"]
            ):
                fallos.append(
                    f"descomposicion_b[{sonda}] no coincide con la recomputacion "
                    f"desde las sondas publicadas"
                )
    return fallos


def _umbral_y_guarda(doc: Mapping[str, Any]) -> tuple[int, int] | None:
    """``(U, SM)`` publicados, si ambos son enteros. None si no lo son."""
    der = doc.get("derivacion")
    if not isinstance(der, Mapping):
        return None
    u, sm = der.get("u_ns"), der.get("sm_ns")
    if isinstance(u, bool) or isinstance(sm, bool):
        return None
    if not isinstance(u, int) or not isinstance(sm, int):
        return None
    return u, sm


def _fallos_regimenes(doc: Mapping[str, Any]) -> list[str]:
    fallos: list[str] = []
    regimenes = doc.get("regimenes_por_percentil")
    if not isinstance(regimenes, Sequence) or isinstance(regimenes, str | bytes):
        return ["regimenes_por_percentil ausente o con forma invalida"]

    # Una lista vacia no puede pasar: vaciarla borraria el veredicto y la
    # divulgacion exigida por la condicion bloqueante 38 sin dejar rastro.
    if not regimenes:
        return ["regimenes_por_percentil vacio: el artefacto debe publicar su veredicto"]

    umbrales = _umbral_y_guarda(doc)
    validos = {fp.REGIMEN_RELATIVO, fp.REGIMEN_ABSOLUTO}

    for indice, entrada in enumerate(regimenes):
        if not isinstance(entrada, Mapping):
            fallos.append(f"regimenes_por_percentil[{indice}] debe ser un objeto")
            continue
        etiqueta = f"regimenes_por_percentil[{indice}]"

        crudo50 = entrada.get("min_p50_ns")
        crudo95 = entrada.get("min_p95_ns")
        if (
            not isinstance(crudo50, int)
            or isinstance(crudo50, bool)
            or not isinstance(crudo95, int)
            or isinstance(crudo95, bool)
        ):
            fallos.append(f"{etiqueta}: min_p50_ns y min_p95_ns deben ser enteros")
            continue
        min50, min95 = crudo50, crudo95

        # El invariante y la combinacion imposible se comprueban SIEMPRE:
        # declarar `resultado: NO_EVALUABLE` no puede ser un comodin que
        # desactive las guardas (§4.1 es incondicional).
        if min95 < min50:
            fallos.append(f"{etiqueta}: invariante violado min_s P95 < min_s P50")

        no_evaluable = entrada.get("resultado") == fp.NO_EVALUABLE

        if umbrales is not None:
            u, sm = umbrales
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
        # aplicar U a los minimos publicados invalida el artefacto. Sin
        # esto, bastaba con declarar el regimen conveniente.
        if umbrales is not None:
            u = umbrales[0]
            for nombre, minimo, declarado in (("P50", min50, r50), ("P95", min95, r95)):
                esperado = fp.regimen_de_percentil(minimo, u)
                if declarado != esperado:
                    fallos.append(
                        f"{etiqueta}: {nombre} declarado '{declarado}' pero con min={minimo} "
                        f"y U={u} corresponde '{esperado}'"
                    )

    return fallos


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

    # No basta con que la clave exista: `null` o una lista de magnitudes
    # vacia borraria la divulgacion de la condicion bloqueante 38.
    clasificacion = doc.get("clasificacion_diagnostica_linea_base")
    if "clasificacion_diagnostica_linea_base" not in doc:
        fallos.append("falta la clasificacion diagnostica de la linea base")
    elif not isinstance(clasificacion, Mapping):
        fallos.append("clasificacion_diagnostica_linea_base debe ser un objeto")
    else:
        magnitudes = clasificacion.get("magnitudes")
        if not isinstance(magnitudes, Sequence) or isinstance(magnitudes, str | bytes):
            fallos.append("clasificacion_diagnostica_linea_base.magnitudes debe ser una lista")
        elif not magnitudes:
            fallos.append(
                "clasificacion_diagnostica_linea_base.magnitudes vacia: la divulgacion "
                "de la clasificacion de la linea base es obligatoria"
            )
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
        entradas = [p for p in procesos if isinstance(p, Mapping)]
        if len(entradas) != len(procesos):
            fallos.append("cada entrada de procesos debe ser un objeto")
        pids = [p.get("pid") for p in entradas]
        if any(not _es_entero(p) for p in pids):
            fallos.append("procesos: cada pid debe ser un entero")
        enteros: list[int] = []
        for pid in pids:
            if isinstance(pid, int) and not isinstance(pid, bool):
                enteros.append(pid)
        if len(enteros) < fp.PROCESOS_MINIMOS:
            fallos.append(f"{len(enteros)} procesos; el minimo es {fp.PROCESOS_MINIMOS}")
        if len(set(enteros)) != len(enteros):
            fallos.append("PIDs repetidos: los procesos no son independientes")

    return fallos


def fallos_suelo_medicion(doc: Mapping[str, Any]) -> list[str]:
    """Valida el artefacto completo. Lista vacia significa conforme.

    **Total por contrato: nunca lanza.** Un validador que lanzase ante un
    valor JSON legal (``NaN``, cadena donde se espera entero, lista donde
    se espera objeto) dejaria de ser una guarda: quien lo invoca no
    obtendria fallos sino una excepcion, y un artefacto manipulado podria
    quedar sin veredicto. Cualquier fallo interno inesperado se convierte
    en un fallo de validacion explicito.
    """
    try:
        return _fallos_suelo_medicion(doc)
    except Exception as exc:
        return [f"validacion abortada por documento malformado: {type(exc).__name__}: {exc}"]


def _fallos_suelo_medicion(doc: Mapping[str, Any]) -> list[str]:
    if not isinstance(doc, Mapping):
        return ["el documento debe ser un objeto JSON"]
    fallos = _fallos_secciones(doc)

    # Igualdad estricta, no `not in (None, X)`: publicar `null` no absuelve.
    if doc.get("version_esquema") != VERSION_ESQUEMA:
        fallos.append(f"version_esquema debe ser {VERSION_ESQUEMA}")
    if doc.get("protocolo") != fp.PROTOCOLO:
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
        if custodia.get("reverificada_tras_medir") is not True:
            fallos.append("custodia: no se reverifico despues de medir y antes de publicar")

        # El vinculo HEAD<->commit_a es OBLIGATORIO, no opcional: si la clave
        # falta o es nula, el artefacto no queda ligado al commit preinscrito
        # y por tanto no es valido. Un ausente no puede ser mas permisivo que
        # un valor distinto.
        pre = doc.get("preinscripcion")
        commit_a = pre.get("commit_a") if isinstance(pre, Mapping) else None
        head_final = custodia.get("head")
        if not isinstance(head_final, str) or not head_final:
            fallos.append("custodia: falta el HEAD de publicacion")
        elif isinstance(commit_a, str) and commit_a and commit_a != head_final:
            fallos.append(
                f"custodia: HEAD al publicar ({head_final!r}) difiere del commit de "
                f"preinscripcion ({commit_a!r}): el codigo medido no es el preinscrito"
            )
        if isinstance(pre, Mapping):
            en_ejecucion = pre.get("head_en_ejecucion")
            if not isinstance(en_ejecucion, str) or not en_ejecucion:
                fallos.append("preinscripcion: falta head_en_ejecucion")
            elif en_ejecucion != commit_a:
                fallos.append("preinscripcion: head_en_ejecucion difiere de commit_a")
    elif "custodia" in doc:
        fallos.append("custodia con forma invalida")

    # Una incidencia observada por la propia corrida (por ejemplo una sonda
    # SQLite que no devolvio la forma declarada) no puede quedar como nota
    # informativa mientras se publican B y U: falla cerrado.
    entorno = doc.get("entorno")
    if isinstance(entorno, Mapping):
        incidencias = entorno.get("incidencias")
        if isinstance(incidencias, Sequence) and not isinstance(incidencias, str | bytes):
            if incidencias and "derivacion" in doc:
                fallos.append(
                    f"se publicaron valores con incidencias registradas: {list(incidencias)}"
                )
        elif "incidencias" in entorno:
            fallos.append("entorno.incidencias debe ser una lista")

    return list(dict.fromkeys(fallos))
