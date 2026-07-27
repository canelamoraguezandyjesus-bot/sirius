"""Contrato normativo de almacenamiento v0.1 — ADR002-TOL-207 v0.2 PROPUESTO.

Única fuente de las constantes normativas del presupuesto absoluto de
almacenamiento v0.2. Toda cifra normativa es un entero en **bytes**; los GiB
son exclusivamente informativos. Las cifras retiradas de la v0.1 se conservan
solo como errores históricos y nunca como valores vigentes.

Contiene además:

* la clasificación propuesta del entorno (``ENVOLVENTE_REPRODUCIBLE``);
* la proveniencia admitida de sesiones (versionada histórica, forense no
  versionada, medición del paquete 04);
* el denominador normativo (5.670 unidades lógicas primarias) y las escalas;
* la regla de reparto determinista por resto mayor para los subconjuntos;
* la matriz fija de aceptación (16 condiciones bloqueantes);
* los blobs Git de los siete artefactos congelados y de la proyección T0;
* el validador ``fallos_entorno_lab`` del documento de evidencia
  ``artifacts/adr002_storage/entorno_lab_v0.1.json``. El validador es una
  función pura: no lee, no escribe y no muta nada.

Este módulo no aprueba ``ADR002-TOL-207``: la tolerancia continúa
``NO SATISFECHA`` y la propuesta queda pendiente de auditoría independiente.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Final, TypeGuard

VERSION_ESQUEMA: Final = "storage-0.1"
VERSION_PRESUPUESTO: Final = "0.2"
ESTADO_DOCUMENTO: Final = "PROPUESTO"
PAQUETE: Final = "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_04_TOL207_CARACTERIZACION_v0.1"

# ---------------------------------------------------------------------------
# Clasificación del entorno · etiquetas de estado
# ---------------------------------------------------------------------------

CLASIFICACION_ENTORNO: Final = "ENVOLVENTE_REPRODUCIBLE"
# Etiquetas expresamente prohibidas como clasificación o como conclusión.
CLASIFICACIONES_PROHIBIDAS: Final = (
    "LABORATORIO_ESTABLE",
    "PRESUPUESTO_APROBADO",
    "TOL-207_SATISFECHA",
    "ENTORNO_CONTRACTUAL_GARANTIZADO",
)

ETIQUETA_MEDIDO: Final = "MEDIDO"
ETIQUETA_PROYECTADO: Final = "PROYECTADO"
ETIQUETA_ASIGNACION: Final = "ASIGNACION_MAXIMA"
ETIQUETA_PENDIENTE: Final = "PENDIENTE"
NO_EVALUABLE: Final = "NO_EVALUABLE"
VALOR_NO_RECOMENDABLE_AUN: Final = "VALOR_NO_RECOMENDABLE_AUN"

PROVENIENCIA_HISTORICA: Final = "MEDICION_VERSIONADA_HISTORICA"
PROVENIENCIA_FORENSE: Final = "INFORME_FORENSE_NO_VERSIONADO"
PROVENIENCIA_PAQUETE_04: Final = "MEDICION_PAQUETE_04"

# ---------------------------------------------------------------------------
# Constantes normativas exactas · enteros en bytes
# ---------------------------------------------------------------------------

E_MIN_HISTORICO: Final = 31_304_323_072
PRESUPUESTO_POR_CANDIDATO: Final = 1_610_612_736  # 1,5 GiB informativos.
PRESUPUESTO_AGREGADO: Final = 8_589_934_592  # 8 GiB informativos.
RESERVA_SEGURIDAD: Final = 15_652_161_536  # 50 % exacto de E_MIN_HISTORICO.
RESERVA_OPERATIVA: Final = 6_442_450_944  # 6 GiB exactos.
SUELO_ADMISION: Final = 30_684_547_072
NUMERO_CANDIDATOS: Final = 5

HOLGURA_AGREGADO: Final = 536_870_912
MARGEN_SUELO_SOBRE_E_MIN: Final = 619_776_000

# ---------------------------------------------------------------------------
# Cifras retiradas de la v0.1 · solo errores históricos, nunca vigentes
# ---------------------------------------------------------------------------

RETIRADA_RESERVA_SEGURIDAD_V0_1: Final = 15_652_167_680  # error de +6.144 B.
RETIRADO_SUELO_V0_1: Final = 30_684_553_216  # error de +6.144 B.
ERROR_REDONDEO_V0_1_BYTES: Final = 6_144
RETIRADO_PORCENTAJE_AGREGADO_V0_1: Final = "27,43"  # debe ser 27,44.

# ---------------------------------------------------------------------------
# Proveniencia de sesiones · valores fijados por su fuente
# ---------------------------------------------------------------------------

# TOL-207 v0.1 (26-jul-2026), evidencia primaria versionada en el repositorio.
HISTORICO_F_BFREE_BYTES: Final = 262_937_780_224
HISTORICO_F_BAVAIL_BYTES: Final = 31_304_323_072
HISTORICO_RESERVA_APARENTE_BYTES: Final = 231_633_457_152

# Informe forense de sesiones de revisión previas; NO es evidencia primaria.
FORENSE_F_BFREE_BYTES: Final = 262_930_505_728
FORENSE_F_BAVAIL_BYTES: Final = 32_158_220_288
FORENSE_RESERVA_APARENTE_BYTES: Final = 230_772_285_440

ANOMALIA_RESERVA_DIFERENCIA_BYTES: Final = 861_171_712

# ---------------------------------------------------------------------------
# Huella de envolvente · campos estables y efímeros
# ---------------------------------------------------------------------------

HUELLA_ESTABLE: Final[dict[str, Any]] = {
    "filesystem": "ext4",
    "f_frsize": 4_096,
    "f_blocks_statvfs": 66_053_021,
    "bytes_totales": 270_553_174_016,
    "montaje_lectura_escritura": True,
    "mecanismo_bloques_reservados_observable": True,
    "inodos_totales": 16_777_216,
    "arquitectura": "x86_64",
    "so_mayor": "Ubuntu 24.04",
    "suelo_admision_bytes": SUELO_ADMISION,
}

CAMPOS_EFIMEROS: Final = (
    "hostname",
    "machine_id",
    "boot_id",
    "kernel_parche_exacto",
    "f_fsid",
)

# ---------------------------------------------------------------------------
# Sondas y contabilidad · límites del método
# ---------------------------------------------------------------------------

SONDAS_MAX_SIMULTANEO_BYTES: Final = 67_108_864  # 64 MiB asignados físicamente.
RESIDUO_MAXIMO_BYTES: Final = 65_536
BYTES_POR_BLOQUE_ST_BLOCKS: Final = 512
PERIODO_MUESTREO_NS: Final = 5_000_000  # 5 ms predeterminados.
MINIMO_INTERVALOS_OPERACION: Final = 3

SONDAS_OBLIGATORIAS: Final = (
    "escritura_densa",
    "fichero_sparse",
    "reflink_ficlone",
    "cow",
    "compresion_o_dedup_aparente",
    "inodos",
    "liberacion_bloques_tras_borrado",
    "ruta_error",
    "limpieza",
)

FASES_MAXIMO_SIMULTANEO: Final = (
    "reposo",
    "construccion",
    "reconstruccion",
    "borrado",
    "purga",
    "vacuum",
)

PARTIDAS_OBLIGATORIAS_CANDIDATO: Final = (
    "indices_lexicos",
    "indices_semanticos",
    "indices_relacionales",
    "tablas_sombra",
    "embeddings",
    "metadatos",
    "caches_persistentes",
    "wal",
    "shm",
    "journal",
    "temporales",
    "spills",
    "ficheros_intermedios",
    "indice_viejo_y_nuevo_coexistentes",
    "copia_vacuum",
    "representacion_reversible_derivada_del_canon",
    "rutas_externas_atribuibles",
)

CONCEPTOS_RESERVA_OPERATIVA: Final = (
    "repositorio",
    "git",
    "venv",
    "corpus_congelado",
    "base_canonica",
    "copias_limpias",
    "artefactos",
    "informes",
    "logs",
    "resultados",
    "checkpoints",
    "snapshots",
    "modelos_locales_compartidos",
    "temporales_comunes_no_atribuibles",
)

# ---------------------------------------------------------------------------
# Denominador normativo y escalas
# ---------------------------------------------------------------------------

UNIDADES_LOGICAS_PRIMARIAS: Final = 5_670
DENOMINADOR_DESGLOSE: Final[dict[str, int]] = {
    "items_estructurados": 550,
    "mensajes": 5_000,
    "documentos": 120,
}
CARGAS_ESTRUCTURALES_NO_DENOMINADOR: Final[dict[str, int]] = {
    "relaciones": 180,
    "entidades": 24,
}
DESGLOSE_ITEMS_POR_KIND: Final[dict[str, int]] = {"MEMORIA": 500, "DECISION": 50}

DEFINICION_UNIDAD_LOGICA: Final = (
    "objeto recuperable portador de contenido del corpus de rendimiento congelado"
)

METRICAS_REPORTADAS: Final = (
    "bytes_por_unidad_logica_primaria",
    "bytes_por_item_estructurado",
    "bytes_por_mensaje",
    "bytes_por_documento",
    "bytes_por_relacion",
    "bytes_por_entidad",
)
COMPARACION_NORMATIVA_COMUN: Final = "bytes_por_unidad_logica_primaria"

ESCALAS_MEDICION_DIRECTA: Final = (500, 5_000, 5_670)
ESCALA_PROYECCION: Final = 50_000

_PREFIJOS_ID: Final[dict[str, tuple[str, int]]] = {
    "MEMORIA": ("MEM-P-", 5),
    "DECISION": ("DEC-P-", 5),
    "mensajes": ("MSG-P-", 5),
    "documentos": ("DOC-P-", 3),
}

# ---------------------------------------------------------------------------
# Blobs congelados · identidad vinculante del acta v0.4
# ---------------------------------------------------------------------------

BLOBS_CONGELADOS_V0_4: Final[dict[str, str]] = {
    "conformance_corpus_v0_4.json": "c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48",
    "cases_v0_4.json": "072753b96f4162fe88ce9c96660296349225c7be",
    "references_v0_4.json": "3fc9a63705144bf543266de129e17a17ab31c568",
    "pdp_cases_v0_3.json": "2eee45a04dee3d72f52ad00dfd46023d7c5e2199",
    "pdp_harness_rules_v0_2.json": "86e4f4ea6b4af3d445ec0f71c9772b46751a202b",
    "performance_corpus_v0_2.json": "4e9e2746e49b158a43eda7826b47c78c41b36e90",
    "benchmark_manifest_v0_4.json": "fa9a2f2b5d8d65aed811f039b2b279c5350d2132",
}
SHA256_PERFORMANCE_V0_2: Final = "c5a161cbdaa7ee150c08e663fa72663324375aa6654f3216a73e90d6b182666b"
BLOB_PROYECCION_T0_EXCLUIDA: Final = "3a241839b7eba84f12a3bbb3c643a17f7b0d0f91"
ESTADO_PROYECCION_T0: Final = "NO_NORMATIVO_NO_CONGELABLE"

# ---------------------------------------------------------------------------
# Matriz fija de aceptación · 16 condiciones bloqueantes
# ---------------------------------------------------------------------------

MATRIZ_ACEPTACION: Final[tuple[dict[str, Any], ...]] = (
    {"id": 1, "condicion": "límite sin bytes exactos"},
    {"id": 2, "condicion": "sesión sin huella verificable"},
    {"id": 3, "condicion": "suelo no comprobado"},
    {"id": 4, "condicion": "derivado, sidecar, temporal o pico omitido"},
    {"id": 5, "condicion": "denominador ambiguo o modificable por candidato"},
    {"id": 6, "condicion": "pico publicado sin resolución válida"},
    {"id": 7, "condicion": "reserva invadida o insuficiente"},
    {"id": 8, "condicion": "sesgo tecnológico material"},
    {"id": 9, "condicion": "sparse/COW/compresión sin caracterizar"},
    {"id": 10, "condicion": "admisión sin captura legible por máquina"},
    {"id": 11, "condicion": "aritmética incoherente"},
    {"id": 12, "condicion": "evidencia sin proveniencia"},
    {"id": 13, "condicion": "anomalía ocultada"},
    {"id": 14, "condicion": "operación más rápida que la observación sin NO_EVALUABLE"},
    {"id": 15, "condicion": "co-residencia presentada como canon"},
    {"id": 16, "condicion": "valores modificados después de observar candidatos"},
)
CATEGORIAS_NO_BLOQUEANTES: Final = (
    "CORRECCION_NO_BLOQUEANTE",
    "LIMITACION_CONOCIDA",
    "TRABAJO_POSTERIOR",
)

# ---------------------------------------------------------------------------
# Aritmética normativa recalculada
# ---------------------------------------------------------------------------


def porcentaje_2dec(numerador: int, denominador: int) -> str:
    """Porcentaje con dos decimales, redondeo half-up y coma decimal."""
    valor = Decimal(numerador) * 100 / Decimal(denominador)
    return str(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)).replace(".", ",")


def aritmetica_normativa() -> dict[str, Any]:
    """Recalcula toda la aritmética normativa desde las constantes.

    La identidad obligatoria es el número de bytes; los porcentajes y GiB son
    informativos y se derivan siempre de los enteros, nunca al revés.
    """
    reserva_seguridad = E_MIN_HISTORICO // 2
    suelo = reserva_seguridad + RESERVA_OPERATIVA + PRESUPUESTO_AGREGADO
    holgura = PRESUPUESTO_AGREGADO - NUMERO_CANDIDATOS * PRESUPUESTO_POR_CANDIDATO
    margen = E_MIN_HISTORICO - suelo
    return {
        "reserva_seguridad_bytes": reserva_seguridad,
        "suelo_admision_bytes": suelo,
        "holgura_agregado_bytes": holgura,
        "margen_suelo_sobre_e_min_bytes": margen,
        "suma_candidatos_bytes": NUMERO_CANDIDATOS * PRESUPUESTO_POR_CANDIDATO,
        "total_reservado_bytes": reserva_seguridad + RESERVA_OPERATIVA,
        "gib_informativos": {
            "presupuesto_por_candidato": "1,5",
            "presupuesto_agregado": "8",
            "reserva_operativa": "6",
        },
        "porcentajes_sobre_e_min_historico": {
            "por_candidato": porcentaje_2dec(PRESUPUESTO_POR_CANDIDATO, E_MIN_HISTORICO),
            "agregado": porcentaje_2dec(PRESUPUESTO_AGREGADO, E_MIN_HISTORICO),
            "reserva_seguridad": porcentaje_2dec(reserva_seguridad, E_MIN_HISTORICO),
            "reserva_operativa": porcentaje_2dec(RESERVA_OPERATIVA, E_MIN_HISTORICO),
            "total_reservado": porcentaje_2dec(
                reserva_seguridad + RESERVA_OPERATIVA, E_MIN_HISTORICO
            ),
            "margen_no_asignado": porcentaje_2dec(margen, E_MIN_HISTORICO),
        },
        "errores_historicos_v0_1": {
            "reserva_seguridad_bytes": RETIRADA_RESERVA_SEGURIDAD_V0_1,
            "suelo_bytes": RETIRADO_SUELO_V0_1,
            "error_bytes": ERROR_REDONDEO_V0_1_BYTES,
            "porcentaje_agregado": RETIRADO_PORCENTAJE_AGREGADO_V0_1,
            "porcentaje_agregado_correcto": porcentaje_2dec(PRESUPUESTO_AGREGADO, E_MIN_HISTORICO),
        },
    }


# ---------------------------------------------------------------------------
# Escalas · reparto determinista por resto mayor
# ---------------------------------------------------------------------------


def reparto_resto_mayor(poblaciones: dict[str, int], total: int) -> dict[str, int]:
    """Reparto proporcional determinista por resto mayor (cuota de Hare).

    Empates de resto se resuelven por el orden de inserción de ``poblaciones``,
    que es fijo en este contrato. El resultado suma exactamente ``total``.
    """
    universo = sum(poblaciones.values())
    if total < 0 or total > universo:
        raise ValueError(f"total fuera de rango: {total} sobre {universo}")
    cuotas = {k: Decimal(v) * total / Decimal(universo) for k, v in poblaciones.items()}
    asignado = {k: int(c) for k, c in cuotas.items()}
    pendientes = total - sum(asignado.values())
    orden = list(poblaciones)
    restos = sorted(
        orden,
        key=lambda k: (-(cuotas[k] - int(cuotas[k])), orden.index(k)),
    )
    for k in restos[:pendientes]:
        asignado[k] += 1
    return asignado


def _rango_ids(prefijo: str, ancho: int, n: int) -> list[str]:
    if n == 0:
        return []
    return [f"{prefijo}{1:0{ancho}d}", f"{prefijo}{n:0{ancho}d}"]


def derivar_escala(unidades: int) -> dict[str, Any]:
    """Deriva el subconjunto determinista de una escala de medición directa.

    No modifica el corpus congelado: define recuentos y rangos de IDs por
    colección, seleccionando los primeros elementos en el orden canónico
    ascendente de ID de cada colección del corpus.
    """
    if unidades not in ESCALAS_MEDICION_DIRECTA:
        raise ValueError(f"escala no contemplada para medición directa: {unidades}")
    reparto = reparto_resto_mayor(dict(DENOMINADOR_DESGLOSE), unidades)
    items_kind = reparto_resto_mayor(dict(DESGLOSE_ITEMS_POR_KIND), reparto["items_estructurados"])
    pre_mem, ancho_mem = _PREFIJOS_ID["MEMORIA"]
    pre_dec, ancho_dec = _PREFIJOS_ID["DECISION"]
    pre_msg, ancho_msg = _PREFIJOS_ID["mensajes"]
    pre_doc, ancho_doc = _PREFIJOS_ID["documentos"]
    return {
        "unidades": unidades,
        "corpus_completo": unidades == UNIDADES_LOGICAS_PRIMARIAS,
        "reparto": reparto,
        "reparto_items_por_kind": items_kind,
        "rangos_ids": {
            "MEMORIA": _rango_ids(pre_mem, ancho_mem, items_kind["MEMORIA"]),
            "DECISION": _rango_ids(pre_dec, ancho_dec, items_kind["DECISION"]),
            "mensajes": _rango_ids(pre_msg, ancho_msg, reparto["mensajes"]),
            "documentos": _rango_ids(pre_doc, ancho_doc, reparto["documentos"]),
        },
    }


def evaluar_modelo_crecimiento(
    puntos: list[tuple[int, int]],
    modelo: str,
    tolerancia_residuo_relativo: float,
) -> dict[str, Any]:
    """Evalúa el modelo de crecimiento prefijado sobre puntos medidos.

    El contrato exige fijar antes de medir: modelo, métrica de ajuste,
    tolerancia de residuo y cota superior conservadora. La métrica de ajuste
    es el residuo relativo máximo frente al ajuste por mínimos cuadrados.
    Si el crecimiento no puede modelarse con la regla prefijada, el resultado
    es ``NO_EVALUABLE`` y no se publica proyección numérica.
    """
    if modelo != "lineal":
        return {"resultado": NO_EVALUABLE, "motivo": f"modelo no contemplado: {modelo}"}
    if len(puntos) < 3:
        return {"resultado": NO_EVALUABLE, "motivo": "menos de tres escalas medidas"}
    n = len(puntos)
    sx = sum(x for x, _ in puntos)
    sy = sum(y for _, y in puntos)
    sxx = sum(x * x for x, _ in puntos)
    sxy = sum(x * y for x, y in puntos)
    det = n * sxx - sx * sx
    if det == 0:
        return {"resultado": NO_EVALUABLE, "motivo": "escalas degeneradas"}
    pendiente = (n * sxy - sx * sy) / det
    ordenada = (sy - pendiente * sx) / n
    residuo_max = 0.0
    for x, y in puntos:
        ajustado = ordenada + pendiente * x
        if y != 0:
            residuo_max = max(residuo_max, abs(ajustado - y) / abs(y))
        elif ajustado != 0:
            residuo_max = 1.0
    if residuo_max > tolerancia_residuo_relativo:
        return {
            "resultado": NO_EVALUABLE,
            "motivo": "residuo relativo máximo supera la tolerancia prefijada",
            "residuo_relativo_maximo": residuo_max,
            "tolerancia_residuo_relativo": tolerancia_residuo_relativo,
        }
    proyeccion = ordenada + pendiente * ESCALA_PROYECCION
    return {
        "resultado": "AJUSTE_VALIDO",
        "etiqueta_proyeccion": ETIQUETA_PROYECTADO,
        "residuo_relativo_maximo": residuo_max,
        "tolerancia_residuo_relativo": tolerancia_residuo_relativo,
        "proyeccion_50000_bytes": int(proyeccion),
        "cota_superior_conservadora_bytes": int(proyeccion * (1 + tolerancia_residuo_relativo)),
    }


# ---------------------------------------------------------------------------
# Validador del documento de evidencia · función pura
# ---------------------------------------------------------------------------


def _es_entero(valor: Any) -> TypeGuard[int]:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _fallos_cabecera(doc: dict[str, Any], fallos: list[str]) -> None:
    if doc.get("version_esquema") != VERSION_ESQUEMA:
        fallos.append("version_esquema no es storage-0.1")
    if doc.get("estado") != ESTADO_DOCUMENTO:
        fallos.append("estado del documento no es PROPUESTO")
    if doc.get("clasificacion_entorno") != CLASIFICACION_ENTORNO:
        fallos.append("clasificacion_entorno no es ENVOLVENTE_REPRODUCIBLE")
    plano = repr(sorted(doc.items(), key=lambda kv: kv[0]))
    for prohibida in CLASIFICACIONES_PROHIBIDAS:
        if prohibida in plano:
            fallos.append(f"etiqueta prohibida presente en el documento: {prohibida}")


def _fallos_constantes(doc: dict[str, Any], fallos: list[str]) -> None:
    constantes = doc.get("constantes")
    if not isinstance(constantes, dict):
        fallos.append("constantes ausentes")
        return
    esperadas: dict[str, int] = {
        "e_min_historico_bytes": E_MIN_HISTORICO,
        "presupuesto_por_candidato_bytes": PRESUPUESTO_POR_CANDIDATO,
        "presupuesto_agregado_bytes": PRESUPUESTO_AGREGADO,
        "reserva_seguridad_bytes": RESERVA_SEGURIDAD,
        "reserva_operativa_bytes": RESERVA_OPERATIVA,
        "suelo_admision_bytes": SUELO_ADMISION,
        "holgura_agregado_bytes": HOLGURA_AGREGADO,
        "margen_suelo_sobre_e_min_bytes": MARGEN_SUELO_SOBRE_E_MIN,
        "numero_candidatos": NUMERO_CANDIDATOS,
        "residuo_maximo_sondas_bytes": RESIDUO_MAXIMO_BYTES,
        "sondas_max_simultaneo_bytes": SONDAS_MAX_SIMULTANEO_BYTES,
        "periodo_muestreo_ns": PERIODO_MUESTREO_NS,
        "minimo_intervalos_operacion": MINIMO_INTERVALOS_OPERACION,
    }
    for clave, valor in esperadas.items():
        observado = constantes.get(clave)
        if not _es_entero(observado):
            fallos.append(f"constante {clave} ausente o no expresada como entero en bytes")
        elif observado != valor:
            fallos.append(f"constante {clave} = {observado!r}, esperada {valor}")
    if constantes.get("reserva_seguridad_bytes") == RETIRADA_RESERVA_SEGURIDAD_V0_1:
        fallos.append("reserva de seguridad retirada de la v0.1 presentada como vigente")
    if constantes.get("suelo_admision_bytes") == RETIRADO_SUELO_V0_1:
        fallos.append("suelo retirado de la v0.1 presentado como vigente")


def _fallos_aritmetica(doc: dict[str, Any], fallos: list[str]) -> None:
    aritmetica = doc.get("aritmetica_recalculada")
    if aritmetica != aritmetica_normativa():
        fallos.append("aritmetica_recalculada no coincide con la recalculada exacta")
        return
    porcentajes = aritmetica["porcentajes_sobre_e_min_historico"]
    if porcentajes["agregado"] == RETIRADO_PORCENTAJE_AGREGADO_V0_1:
        fallos.append("porcentaje agregado retirado 27,43 presentado como vigente")


def _statvfs_derivados_coherentes(montaje: dict[str, Any]) -> list[str]:
    fallos: list[str] = []
    statvfs = montaje.get("statvfs")
    derivados = montaje.get("derivados")
    if not isinstance(statvfs, dict) or not isinstance(derivados, dict):
        return ["punto de montaje sin statvfs o sin derivados"]
    frsize = statvfs.get("f_frsize")
    if not _es_entero(frsize):
        return ["statvfs sin f_frsize entero"]
    esperados = {
        "bytes_totales": statvfs.get("f_blocks", 0) * frsize,
        "bytes_libres_brutos": statvfs.get("f_bfree", 0) * frsize,
        "bytes_disponibles": statvfs.get("f_bavail", 0) * frsize,
        "diferencia_f_bfree_f_bavail_bloques": statvfs.get("f_bfree", 0)
        - statvfs.get("f_bavail", 0),
        "diferencia_f_bfree_f_bavail_bytes": (
            statvfs.get("f_bfree", 0) - statvfs.get("f_bavail", 0)
        )
        * frsize,
    }
    for clave, valor in esperados.items():
        if derivados.get(clave) != valor:
            fallos.append(
                f"derivado {clave} incoherente con el statvfs de su propia captura: "
                "mezcla de observaciones"
            )
    if montaje.get("observacion_unica") is not True:
        fallos.append("captura sin marca de observación única por punto de montaje")
    antes = montaje.get("monotonico_ns_antes")
    despues = montaje.get("monotonico_ns_despues")
    if not (_es_entero(antes) and _es_entero(despues) and antes <= despues):
        fallos.append("captura sin ventana monotónica coherente")
    return fallos


def _fallos_captura(doc: dict[str, Any], fallos: list[str]) -> None:
    captura = doc.get("captura_cruda")
    if not isinstance(captura, dict):
        fallos.append("captura_cruda ausente: admisión sin captura legible por máquina")
        return
    for clave in (
        "utc",
        "timestamp_monotonico_ns",
        "uid_efectivo",
        "gid_efectivo",
        "hostname",
        "machine_id",
        "boot_id",
        "so",
        "kernel",
        "arquitectura",
        "cpu",
        "virtualizacion",
        "puntos_de_montaje",
        "cgroups",
        "ulimit_tamano_fichero",
        "superbloque_ext4",
        "herramientas",
    ):
        if clave not in captura:
            fallos.append(f"captura_cruda sin campo obligatorio: {clave}")
    montajes = captura.get("puntos_de_montaje")
    if not isinstance(montajes, list) or not montajes:
        fallos.append("captura sin puntos de montaje")
        return
    for montaje in montajes:
        fallos.extend(_statvfs_derivados_coherentes(montaje))


def _fallos_huella(doc: dict[str, Any], fallos: list[str]) -> None:
    huella = doc.get("huella_estable_propuesta")
    if huella != HUELLA_ESTABLE:
        fallos.append("huella estable propuesta no coincide con la del contrato")
    efimeros = doc.get("campos_efimeros")
    if not isinstance(efimeros, dict) or set(efimeros) != set(CAMPOS_EFIMEROS):
        fallos.append("campos efímeros ausentes o distintos de los del contrato")
    captura = doc.get("captura_cruda")
    if not isinstance(captura, dict):
        return
    montajes = captura.get("puntos_de_montaje")
    if not isinstance(montajes, list) or not montajes:
        return
    repo = montajes[0]
    statvfs = repo.get("statvfs", {})
    contrastes = (
        ("filesystem", repo.get("filesystem")),
        ("f_frsize", statvfs.get("f_frsize")),
        ("f_blocks_statvfs", statvfs.get("f_blocks")),
        ("bytes_totales", repo.get("derivados", {}).get("bytes_totales")),
        ("inodos_totales", statvfs.get("f_files")),
        ("arquitectura", captura.get("arquitectura")),
    )
    for clave, observado in contrastes:
        if observado != HUELLA_ESTABLE[clave]:
            fallos.append(f"la captura actual no confirma el campo estable {clave}")
    opciones = str(repo.get("opciones", ""))
    if not (opciones == "rw" or opciones.startswith("rw,")):
        fallos.append("la captura actual no confirma el montaje de lectura/escritura")
    so = captura.get("so", {})
    so_mayor = f"{so.get('name', '')} {so.get('version_id', '')}".strip()
    if so_mayor != HUELLA_ESTABLE["so_mayor"]:
        fallos.append("la captura actual no confirma el campo estable so_mayor")


def _fallos_proveniencia(doc: dict[str, Any], fallos: list[str]) -> None:
    proveniencia = doc.get("proveniencia")
    if not isinstance(proveniencia, dict):
        fallos.append("evidencia sin proveniencia")
        return
    historica = proveniencia.get("medicion_versionada_historica")
    forense = proveniencia.get("informe_forense_no_versionado")
    actual = proveniencia.get("medicion_paquete_04")
    if not isinstance(historica, dict):
        fallos.append("proveniencia sin MEDICION_VERSIONADA_HISTORICA")
    else:
        if historica.get("evidencia_primaria") is not True:
            fallos.append("la medición versionada histórica debe ser evidencia primaria")
        esperado = {
            "f_bfree_bytes": HISTORICO_F_BFREE_BYTES,
            "f_bavail_bytes": HISTORICO_F_BAVAIL_BYTES,
            "reserva_aparente_bytes": HISTORICO_RESERVA_APARENTE_BYTES,
        }
        for clave, valor in esperado.items():
            if historica.get(clave) != valor:
                fallos.append(f"medición histórica con {clave} distinto del versionado")
    if not isinstance(forense, dict):
        fallos.append("proveniencia sin INFORME_FORENSE_NO_VERSIONADO")
    else:
        if forense.get("evidencia_primaria") is not False:
            fallos.append("sesión no versionada presentada como evidencia primaria del repositorio")
        if forense.get("captura_independiente_versionada") is not False:
            fallos.append("informe forense presentado como captura independiente versionada")
    if not isinstance(actual, dict) or actual.get("evidencia_primaria") is not True:
        fallos.append("proveniencia sin MEDICION_PAQUETE_04 como evidencia primaria")


def _fallos_anomalia(doc: dict[str, Any], fallos: list[str]) -> None:
    anomalia = doc.get("anomalia_reserva")
    if not isinstance(anomalia, dict):
        fallos.append("anomalía de reserva ocultada: sección ausente")
        return
    resta = HISTORICO_RESERVA_APARENTE_BYTES - FORENSE_RESERVA_APARENTE_BYTES
    if anomalia.get("diferencia_bytes") != resta:
        fallos.append("anomalía de reserva con diferencia distinta de la resta exacta")
    if resta != ANOMALIA_RESERVA_DIFERENCIA_BYTES:
        fallos.append("constante de anomalía incoherente con las reservas aparentes")
    for clave, valor in (
        ("oculta", False),
        ("atribuida_a_contenido_ordinario", False),
        ("cuota_fija_entre_sesiones", False),
        ("demostrable_retrospectivamente_26jul", False),
    ):
        if anomalia.get(clave) is not valor:
            fallos.append(f"anomalía de reserva con campo {clave} distinto de {valor}")
    if not isinstance(anomalia.get("demostracion_sesion_actual"), dict):
        fallos.append("anomalía sin demostración para la sesión actual")


def _fallos_admision(doc: dict[str, Any], fallos: list[str]) -> None:
    admision = doc.get("admision_sesion")
    if not isinstance(admision, dict):
        fallos.append("suelo no comprobado: admisión ausente")
        return
    if admision.get("campo_utilizado") != "f_bavail":
        fallos.append("admisión que no usa f_bavail como disponibilidad")
    captura = doc.get("captura_cruda", {})
    montajes = captura.get("puntos_de_montaje") if isinstance(captura, dict) else None
    if isinstance(montajes, list) and montajes:
        statvfs = montajes[0].get("statvfs", {})
        esperado = statvfs.get("f_bavail", 0) * statvfs.get("f_frsize", 0)
        if admision.get("bytes_disponibles") != esperado:
            fallos.append("bytes_disponibles de la admisión no salen de f_bavail de la captura")
        if admision.get("bytes_disponibles") == statvfs.get("f_bfree", 0) * statvfs.get(
            "f_frsize", 0
        ) and statvfs.get("f_bfree") != statvfs.get("f_bavail"):
            fallos.append("f_bfree usado como disponibilidad")
    disponibles = admision.get("bytes_disponibles")
    if not _es_entero(disponibles):
        fallos.append("admisión sin bytes_disponibles enteros")
        return
    supera = disponibles >= SUELO_ADMISION
    if admision.get("supera_suelo") is not supera:
        fallos.append("supera_suelo incoherente con los bytes disponibles")
    if not supera and admision.get("resultado") != VALOR_NO_RECOMENDABLE_AUN:
        fallos.append("f_bavail bajo suelo aceptado")
    if supera and admision.get("resultado") != "ADMITIDA":
        fallos.append("resultado de admisión incoherente con el suelo superado")
    if admision.get("mismo_filesystem_repo_temporales") is not True:
        fallos.append("repositorio y temporales en filesystems distintos")
    if admision.get("st_dev_repositorio") != admision.get("st_dev_temporales"):
        fallos.append("st_dev de repositorio y temporales no coinciden")
    if admision.get("inodos_suficientes") is not True:
        fallos.append("inodos agotados o insuficientes ignorados")


def _fallos_sondas(doc: dict[str, Any], fallos: list[str]) -> None:
    sondas = doc.get("sondas")
    if not isinstance(sondas, dict):
        fallos.append("sparse/COW/compresión sin caracterizar: sondas ausentes")
        return
    for clave in SONDAS_OBLIGATORIAS:
        if clave not in sondas:
            fallos.append(f"sonda obligatoria ausente: {clave}")
    if sondas.get("mismo_filesystem_que_repositorio") is not True:
        fallos.append("sondas ejecutadas fuera del filesystem del repositorio")
    sparse = sondas.get("fichero_sparse")
    if isinstance(sparse, dict):
        if sparse.get("contabilizacion") != "st_blocks*512":
            fallos.append("sparse contado por st_size en lugar de bloques asignados")
        asignado = sparse.get("bloques_asignados_bytes")
        aparente = sparse.get("tamano_aparente_bytes")
        if _es_entero(asignado) and _es_entero(aparente) and asignado >= aparente:
            fallos.append("la sonda sparse no demuestra asignación menor que el tamaño")
    limpieza = sondas.get("limpieza")
    if isinstance(limpieza, dict):
        residuo = limpieza.get("residuo_bytes")
        if not _es_entero(residuo):
            fallos.append("limpieza sin residuo medido")
        elif residuo > RESIDUO_MAXIMO_BYTES and limpieza.get("valida") is not False:
            fallos.append("limpieza con residuo superior a 65.536 B aceptada como válida")
        if limpieza.get("maximo_admisible_bytes") != RESIDUO_MAXIMO_BYTES:
            fallos.append("máximo admisible de residuo distinto del contrato")
    ruta_error = sondas.get("ruta_error")
    if isinstance(ruta_error, dict) and ruta_error.get("limpieza_tras_excepcion") is not True:
        fallos.append("sonda residual tras una excepción")


def _fallos_reserva_operativa(doc: dict[str, Any], fallos: list[str]) -> None:
    desglose = doc.get("reserva_operativa_desglose")
    if not isinstance(desglose, dict):
        fallos.append("reserva operativa sin desglose")
        return
    if desglose.get("presupuesto_bytes") != RESERVA_OPERATIVA:
        fallos.append("presupuesto de reserva operativa distinto de 6.442.450.944 B")
    partidas = desglose.get("partidas")
    if not isinstance(partidas, list) or not partidas:
        fallos.append("reserva operativa sin partidas")
        return
    cubiertos: set[str] = set()
    suma = 0
    for partida in partidas:
        if not isinstance(partida, dict):
            fallos.append("partida de reserva operativa no estructurada")
            continue
        cubre = partida.get("cubre")
        if isinstance(cubre, list):
            cubiertos.update(str(c) for c in cubre)
        tipo = partida.get("tipo")
        if tipo not in (ETIQUETA_MEDIDO, ETIQUETA_ASIGNACION, ETIQUETA_PENDIENTE):
            fallos.append(f"partida con tipo no contemplado: {tipo!r}")
        medido = partida.get("bytes_medidos_actualmente")
        asignacion = partida.get("asignacion_maxima_bytes")
        if not _es_entero(medido) or not _es_entero(asignacion):
            fallos.append("partida sin bytes medidos y asignación máxima enteros")
            continue
        if tipo == ETIQUETA_MEDIDO and medido == 0:
            fallos.append("partida presentada como medida sin bytes medidos")
        if tipo in (ETIQUETA_ASIGNACION, ETIQUETA_PENDIENTE) and medido > asignacion:
            fallos.append("partida con medición que ya desborda su asignación máxima")
        if partida.get("suma_excluida") is not True:
            suma += asignacion
            if medido > asignacion:
                fallos.append("partida medida por encima de su asignación máxima")
    faltan = set(CONCEPTOS_RESERVA_OPERATIVA) - cubiertos
    if faltan:
        fallos.append(f"conceptos de reserva operativa sin partida: {sorted(faltan)}")
    if desglose.get("suma_asignaciones_maximas_bytes") != suma:
        fallos.append("suma de asignaciones máximas incoherente con las partidas")
    if suma > RESERVA_OPERATIVA:
        fallos.append("reserva operativa superior a 6 GiB aceptada")
    if desglose.get("margen_restante_bytes") != RESERVA_OPERATIVA - suma:
        fallos.append("margen restante de reserva operativa incoherente")
    if desglose.get("cabe_en_presupuesto") is not (suma <= RESERVA_OPERATIVA):
        fallos.append("cabe_en_presupuesto incoherente con la suma de partidas")


def _fallos_denominador(doc: dict[str, Any], fallos: list[str]) -> None:
    denominador = doc.get("denominador")
    if not isinstance(denominador, dict):
        fallos.append("denominador ausente")
        return
    if denominador.get("unidades_logicas_primarias") != UNIDADES_LOGICAS_PRIMARIAS:
        fallos.append("denominador distinto de 5.670")
    desglose = denominador.get("desglose")
    if desglose != DENOMINADOR_DESGLOSE:
        fallos.append("desglose del denominador distinto de 550/5.000/120")
    if isinstance(desglose, dict):
        for clave in CARGAS_ESTRUCTURALES_NO_DENOMINADOR:
            if clave in desglose:
                fallos.append(f"carga estructural incorporada al denominador primario: {clave}")
        if sum(desglose.values()) != UNIDADES_LOGICAS_PRIMARIAS:
            fallos.append("denominador que no es la suma exacta de su desglose")
    cargas = denominador.get("cargas_estructurales_numerador_no_denominador")
    if cargas != CARGAS_ESTRUCTURALES_NO_DENOMINADOR:
        fallos.append("cargas estructurales (180 relaciones, 24 entidades) mal declaradas")
    if denominador.get("comparacion_normativa_comun") != COMPARACION_NORMATIVA_COMUN:
        fallos.append("comparación normativa común distinta de bytes_por_unidad_logica_primaria")
    if denominador.get("no_modificable_por_candidato") is not True:
        fallos.append("denominador modificable por candidato")
    metricas = denominador.get("metricas_reportadas")
    if metricas != list(METRICAS_REPORTADAS):
        fallos.append("métricas reportadas distintas de las del contrato")


def _fallos_escalas(doc: dict[str, Any], fallos: list[str]) -> None:
    escalas = doc.get("escalas")
    if not isinstance(escalas, dict):
        fallos.append("escalas ausentes")
        return
    directa = escalas.get("medicion_directa")
    if not isinstance(directa, list) or [e.get("unidades") for e in directa] != list(
        ESCALAS_MEDICION_DIRECTA
    ):
        fallos.append("escalas de medición directa distintas de 500/5.000/5.670")
    else:
        for declarada in directa:
            esperada = derivar_escala(declarada["unidades"])
            if declarada != esperada:
                fallos.append(
                    f"escala {declarada['unidades']} no coincide con el reparto determinista"
                )
    proyeccion = escalas.get("proyeccion")
    if not isinstance(proyeccion, dict):
        fallos.append("proyección a 50.000 ausente")
    else:
        if proyeccion.get("unidades") != ESCALA_PROYECCION:
            fallos.append("proyección con unidades distintas de 50.000")
        if proyeccion.get("etiqueta") != ETIQUETA_PROYECTADO:
            fallos.append("extrapolación a 50.000 presentada como medición")
    contrato = escalas.get("contrato_previo_medicion_candidato")
    if not isinstance(contrato, dict):
        fallos.append("contrato previo de medición de candidatos ausente")
    else:
        for clave in (
            "modelo_crecimiento",
            "metrica_ajuste",
            "tolerancia_residuo",
            "cota_superior_conservadora",
        ):
            if clave not in contrato:
                fallos.append(f"contrato de crecimiento sin campo: {clave}")
        if contrato.get("si_no_modelable") != NO_EVALUABLE:
            fallos.append("contrato sin salida NO_EVALUABLE para crecimiento no modelable")


def _fallos_blobs(doc: dict[str, Any], fallos: list[str]) -> None:
    blobs = doc.get("blobs_congelados")
    if not isinstance(blobs, dict):
        fallos.append("blobs congelados ausentes")
        return
    for artefacto, blob in BLOBS_CONGELADOS_V0_4.items():
        entrada = blobs.get(artefacto)
        if not isinstance(entrada, dict):
            fallos.append(f"blob congelado sin registrar: {artefacto}")
            continue
        if entrada.get("blob_esperado") != blob:
            fallos.append(f"blob esperado alterado para {artefacto}")
        if entrada.get("blob_observado") != blob or entrada.get("intacto") is not True:
            fallos.append(f"artefacto congelado no demostrado intacto: {artefacto}")
    performance = blobs.get("performance_corpus_v0_2.json")
    if isinstance(performance, dict) and performance.get("sha256") != SHA256_PERFORMANCE_V0_2:
        fallos.append("SHA-256 del corpus de rendimiento distinto del congelado")
    t0 = doc.get("blob_proyeccion_t0_excluida")
    if not isinstance(t0, dict):
        fallos.append("blob de la proyección T0 excluida sin registrar")
    else:
        if t0.get("blob_observado") != BLOB_PROYECCION_T0_EXCLUIDA:
            fallos.append("proyección T0 con blob distinto del observado en el acta")
        if t0.get("estado") != ESTADO_PROYECCION_T0:
            fallos.append("proyección T0 sin estado NO_NORMATIVO_NO_CONGELABLE")


def _fallos_matriz_y_puertas(doc: dict[str, Any], fallos: list[str]) -> None:
    matriz = doc.get("matriz_aceptacion")
    if not isinstance(matriz, dict):
        fallos.append("matriz de aceptación ausente")
        return
    condiciones = matriz.get("condiciones_bloqueantes")
    if condiciones != [dict(c) for c in MATRIZ_ACEPTACION]:
        fallos.append("condiciones bloqueantes distintas de la matriz fija de 16")
    if matriz.get("categorias_no_bloqueantes") != list(CATEGORIAS_NO_BLOQUEANTES):
        fallos.append("categorías no bloqueantes distintas de las del contrato")
    puertas = doc.get("estado_puertas")
    if not isinstance(puertas, dict):
        fallos.append("estado de puertas ausente")
        return
    tol207 = str(puertas.get("ADR002-TOL-207", ""))
    if "NO SATISFECHA" not in tol207:
        fallos.append("TOL-207 no declarada NO SATISFECHA")
    if "APROBADA" in tol207:
        fallos.append("TOL-207 declarada aprobada")


def _fallos_secretos(doc: dict[str, Any], fallos: list[str]) -> None:
    sospechosas = ("token", "secret", "password", "api_key", "authorization")

    def recorrer(nodo: Any) -> None:
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                if any(s in str(clave).lower() for s in sospechosas):
                    fallos.append(f"clave potencialmente sensible en la evidencia: {clave}")
                recorrer(valor)
        elif isinstance(nodo, list):
            for valor in nodo:
                recorrer(valor)

    recorrer(doc)


def fallos_entorno_lab(doc: dict[str, Any]) -> list[str]:
    """Valida el documento de evidencia y devuelve la lista de fallos.

    Lista vacía significa documento conforme al contrato storage-0.1. La
    función no muta el documento ni toca el filesystem.
    """
    fallos: list[str] = []
    _fallos_cabecera(doc, fallos)
    _fallos_constantes(doc, fallos)
    _fallos_aritmetica(doc, fallos)
    _fallos_captura(doc, fallos)
    _fallos_huella(doc, fallos)
    _fallos_proveniencia(doc, fallos)
    _fallos_anomalia(doc, fallos)
    _fallos_admision(doc, fallos)
    _fallos_sondas(doc, fallos)
    _fallos_reserva_operativa(doc, fallos)
    _fallos_denominador(doc, fallos)
    _fallos_escalas(doc, fallos)
    _fallos_blobs(doc, fallos)
    _fallos_matriz_y_puertas(doc, fallos)
    _fallos_secretos(doc, fallos)
    for seccion in ("limitaciones",):
        if seccion not in doc:
            fallos.append(f"sección obligatoria ausente: {seccion}")
    return fallos
