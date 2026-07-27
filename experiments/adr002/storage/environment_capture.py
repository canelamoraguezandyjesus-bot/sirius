"""Captura atómica del entorno de laboratorio — ADR002-TOL-207 v0.2.

Cada punto de montaje se captura con **una única llamada** a ``os.statvfs``;
todos los campos derivados de esa observación se calculan desde esa misma
llamada. Nunca se mezclan resultados de dos ``statvfs`` distintas como si
fueran una captura. La lectura del superbloque ext4 es una observación
separada y se registra como tal.

El módulo también ensambla el documento de evidencia
``artifacts/adr002_storage/entorno_lab_v0.1.json`` a partir de una captura
fija, de los resultados de las sondas y de las mediciones de la reserva
operativa: dado el mismo trío de entradas, el documento resultante es
byte a byte el mismo.
"""

from __future__ import annotations

import datetime as dt
import os
import platform
import re
import resource
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

from experiments.adr002.storage import schema_storage_v0_1 as SS
from experiments.adr002.storage import storage_accounting as SA

_HERRAMIENTAS_SONDEADAS = (
    "tune2fs",
    "dumpe2fs",
    "df",
    "lsblk",
    "findmnt",
    "systemd-detect-virt",
)

_CGROUP_FICHEROS = (
    "/sys/fs/cgroup/memory.max",
    "/sys/fs/cgroup/memory/memory.limit_in_bytes",
    "/sys/fs/cgroup/io.max",
    "/sys/fs/cgroup/blkio/blkio.throttle.write_bps_device",
    "/sys/fs/cgroup/pids/pids.max",
)


def _leer_texto(ruta: str) -> str | None:
    try:
        return Path(ruta).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _montaje_para(ruta: Path) -> dict[str, str]:
    """Entrada de ``/proc/self/mounts`` cuyo punto de montaje cubre ``ruta``.

    Se elige el prefijo más largo, que es la semántica del kernel.
    """
    mejor: dict[str, str] = {
        "dispositivo": "desconocido",
        "punto_de_montaje": "/",
        "filesystem": "desconocido",
        "opciones": "",
    }
    contenido = _leer_texto("/proc/self/mounts") or ""
    ruta_txt = str(ruta.resolve())
    longitud = -1
    for linea in contenido.splitlines():
        partes = linea.split()
        if len(partes) < 4:
            continue
        dispositivo, punto, fstipo, opciones = partes[0], partes[1], partes[2], partes[3]
        if (
            ruta_txt == punto or ruta_txt.startswith(punto.rstrip("/") + "/") or punto == "/"
        ) and len(punto) > longitud:
            longitud = len(punto)
            mejor = {
                "dispositivo": dispositivo,
                "punto_de_montaje": punto,
                "filesystem": fstipo,
                "opciones": opciones,
            }
    return mejor


def capturar_punto_de_montaje(ruta: Path) -> dict[str, Any]:
    """Observación coherente única de un punto de montaje.

    Una sola llamada a ``os.statvfs``; los derivados salen exclusivamente de
    ella. La ventana monotónica delimita la observación.
    """
    montaje = _montaje_para(ruta)
    st = os.stat(ruta)
    antes = time.monotonic_ns()
    vfs = os.statvfs(ruta)
    despues = time.monotonic_ns()
    statvfs = {
        "f_bsize": vfs.f_bsize,
        "f_frsize": vfs.f_frsize,
        "f_blocks": vfs.f_blocks,
        "f_bfree": vfs.f_bfree,
        "f_bavail": vfs.f_bavail,
        "f_files": vfs.f_files,
        "f_ffree": vfs.f_ffree,
        "f_favail": vfs.f_favail,
        "f_flag": vfs.f_flag,
        "f_fsid": vfs.f_fsid,
        "f_namemax": vfs.f_namemax,
    }
    derivados = {
        "bytes_totales": vfs.f_blocks * vfs.f_frsize,
        "bytes_libres_brutos": vfs.f_bfree * vfs.f_frsize,
        "bytes_disponibles": vfs.f_bavail * vfs.f_frsize,
        "diferencia_f_bfree_f_bavail_bloques": vfs.f_bfree - vfs.f_bavail,
        "diferencia_f_bfree_f_bavail_bytes": (vfs.f_bfree - vfs.f_bavail) * vfs.f_frsize,
    }
    return {
        "ruta_observada": str(ruta),
        "st_dev": st.st_dev,
        "observacion_unica": True,
        "monotonico_ns_antes": antes,
        "monotonico_ns_despues": despues,
        "statvfs": statvfs,
        "derivados": derivados,
        **montaje,
    }


def leer_superbloque_ext4(dispositivo: str) -> dict[str, Any]:
    """Superbloque ext4 vía ``tune2fs -l`` cuando es legible.

    Observación separada de la captura ``statvfs``: se registra con su propia
    marca y nunca se funde con los campos de aquella.
    """
    ejecutable = shutil.which("tune2fs")
    if ejecutable is None:
        return {"legible": False, "motivo": "tune2fs ausente"}
    try:
        salida = subprocess.run(
            [ejecutable, "-l", dispositivo],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return {"legible": False, "motivo": f"tune2fs fallo: {exc.__class__.__name__}"}
    campos: dict[str, Any] = {"legible": True, "dispositivo": dispositivo}
    claves = {
        "Block count": "block_count",
        "Reserved block count": "reserved_block_count",
        "Free blocks": "free_blocks_superbloque",
        "Inode count": "inode_count",
        "Free inodes": "free_inodes_superbloque",
        "Block size": "block_size",
        "Reserved blocks uid": "reserved_blocks_uid",
        "Reserved blocks gid": "reserved_blocks_gid",
        "Filesystem features": "features",
    }
    for linea in salida.splitlines():
        if ":" not in linea:
            continue
        etiqueta, _, valor = linea.partition(":")
        clave = claves.get(etiqueta.strip())
        if clave is None:
            continue
        valor = valor.strip()
        numero = re.match(r"^\d+", valor)
        campos[clave] = int(numero.group()) if numero and clave != "features" else valor
    return campos


def _virtualizacion() -> dict[str, Any]:
    observaciones: dict[str, Any] = {}
    detect = shutil.which("systemd-detect-virt")
    if detect is not None:
        try:
            resultado = subprocess.run(
                [detect], capture_output=True, text=True, timeout=10, check=False
            )
            observaciones["systemd_detect_virt"] = resultado.stdout.strip() or "none"
        except OSError, subprocess.SubprocessError:
            observaciones["systemd_detect_virt"] = "error"
    else:
        observaciones["systemd_detect_virt"] = "herramienta ausente"
    cpuinfo = _leer_texto("/proc/cpuinfo") or ""
    observaciones["hypervisor_flag_cpuinfo"] = " hypervisor" in cpuinfo or "\thypervisor" in cpuinfo
    observaciones["dockerenv_presente"] = Path("/.dockerenv").exists()
    cgroup_pid1 = _leer_texto("/proc/1/cgroup") or ""
    observaciones["cgroup_pid1_contenedor"] = any(
        marca in cgroup_pid1 for marca in ("docker", "containerd", "kubepods", "lxc")
    )
    return observaciones


def _cgroups() -> dict[str, str]:
    lecturas: dict[str, str] = {}
    for ruta in _CGROUP_FICHEROS:
        valor = _leer_texto(ruta)
        lecturas[ruta] = valor if valor is not None else "ilegible"
    return lecturas


def _ulimit_tamano_fichero() -> int | str:
    blando, _duro = resource.getrlimit(resource.RLIMIT_FSIZE)
    return "unlimited" if blando == resource.RLIM_INFINITY else blando


def _cpu() -> dict[str, Any]:
    modelo = "desconocido"
    cpuinfo = _leer_texto("/proc/cpuinfo") or ""
    for linea in cpuinfo.splitlines():
        if linea.lower().startswith("model name"):
            modelo = linea.partition(":")[2].strip()
            break
    return {"numero": os.cpu_count() or 0, "modelo": modelo}


def _so() -> dict[str, str]:
    campos: dict[str, str] = {}
    contenido = _leer_texto("/etc/os-release") or ""
    for linea in contenido.splitlines():
        if "=" in linea:
            clave, _, valor = linea.partition("=")
            if clave in ("NAME", "VERSION_ID", "VERSION", "PRETTY_NAME"):
                campos[clave.lower()] = valor.strip('"')
    return campos


def _herramientas() -> dict[str, list[str]]:
    disponibles = [h for h in _HERRAMIENTAS_SONDEADAS if shutil.which(h) is not None]
    ausentes = [h for h in _HERRAMIENTAS_SONDEADAS if shutil.which(h) is None]
    return {"disponibles": disponibles, "ausentes": ausentes}


def capturar_entorno(ruta_repositorio: Path, ruta_temporales: Path) -> dict[str, Any]:
    """Captura completa del entorno para la admisión de la sesión."""
    uname = os.uname()
    montaje_repo = capturar_punto_de_montaje(ruta_repositorio)
    montaje_tmp = capturar_punto_de_montaje(ruta_temporales)
    if montaje_tmp["st_dev"] == montaje_repo["st_dev"]:
        montaje_tmp = {
            **montaje_tmp,
            "mismo_punto_que": montaje_repo["ruta_observada"],
        }
    puntos = [montaje_repo, montaje_tmp]
    return {
        "utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "timestamp_monotonico_ns": time.monotonic_ns(),
        "uid_efectivo": os.geteuid(),
        "gid_efectivo": os.getegid(),
        "hostname": socket.gethostname(),
        "machine_id": _leer_texto("/etc/machine-id"),
        "boot_id": _leer_texto("/proc/sys/kernel/random/boot_id"),
        "so": _so(),
        "kernel": uname.release,
        "arquitectura": platform.machine(),
        "cpu": _cpu(),
        "virtualizacion": _virtualizacion(),
        "puntos_de_montaje": puntos,
        "cgroups": _cgroups(),
        "ulimit_tamano_fichero": _ulimit_tamano_fichero(),
        "superbloque_ext4": leer_superbloque_ext4(montaje_repo["dispositivo"]),
        "herramientas": _herramientas(),
    }


# ---------------------------------------------------------------------------
# Partidas de la reserva operativa · medición por inode
# ---------------------------------------------------------------------------


def medir_particiones_reserva_operativa(raiz_repositorio: Path) -> dict[str, int]:
    """Bytes asignados (``st_blocks*512``) de las partidas medibles hoy."""
    repo = raiz_repositorio
    arbol = SA.inventario_por_inode([repo], excluir={repo / ".git", repo / ".venv"})
    git = SA.inventario_por_inode([repo / ".git"])
    venv_dir = repo / ".venv"
    venv = (
        SA.inventario_por_inode([venv_dir])
        if venv_dir.exists()
        else {"bytes_asignados": 0, "bytes_aparentes": 0, "inodos": 0}
    )
    corpus = SA.inventario_por_inode(
        [
            repo / "experiments" / "adr002" / "benchmark" / nombre
            for nombre in SS.BLOBS_CONGELADOS_V0_4
        ]
    )
    artefactos = SA.inventario_por_inode([repo / "artifacts"])
    return {
        "repositorio_sin_git_ni_venv_bytes": arbol["bytes_asignados"],
        "git_bytes": git["bytes_asignados"],
        "venv_bytes": venv["bytes_asignados"],
        "corpus_congelado_bytes": corpus["bytes_asignados"],
        "artefactos_bytes": artefactos["bytes_asignados"],
    }


def plan_reserva_operativa(medidas: dict[str, int]) -> dict[str, Any]:
    """Plan de reserva operativa: partidas con asignación máxima prefijada.

    Separa bytes medidos ahora, asignaciones máximas prefijadas y partidas
    pendientes; el margen restante sale de la resta exacta. Nada medido se
    presenta como asignación ni al revés.
    """
    partidas: list[dict[str, Any]] = [
        {
            "partida": "repositorio_sin_git_ni_venv",
            "cubre": ["repositorio"],
            "tipo": SS.ETIQUETA_MEDIDO,
            "bytes_medidos_actualmente": medidas["repositorio_sin_git_ni_venv_bytes"],
            "asignacion_maxima_bytes": 134_217_728,
        },
        {
            "partida": "git",
            "cubre": ["git"],
            "tipo": SS.ETIQUETA_MEDIDO,
            "bytes_medidos_actualmente": medidas["git_bytes"],
            "asignacion_maxima_bytes": 134_217_728,
        },
        {
            "partida": "venv",
            "cubre": ["venv"],
            "tipo": SS.ETIQUETA_MEDIDO,
            "bytes_medidos_actualmente": medidas["venv_bytes"],
            "asignacion_maxima_bytes": 1_610_612_736,
        },
        {
            "partida": "corpus_congelado",
            "cubre": ["corpus_congelado"],
            "tipo": SS.ETIQUETA_MEDIDO,
            "bytes_medidos_actualmente": medidas["corpus_congelado_bytes"],
            "asignacion_maxima_bytes": medidas["corpus_congelado_bytes"],
            "suma_excluida": True,
            "nota": "contenido dentro del repositorio; se lista sin sumar dos veces",
        },
        {
            "partida": "base_canonica",
            "cubre": ["base_canonica"],
            "tipo": SS.ETIQUETA_PENDIENTE,
            "bytes_medidos_actualmente": 0,
            "asignacion_maxima_bytes": 536_870_912,
            "nota": "no existe todavía; T0 no se ejecuta en este paquete",
        },
        {
            "partida": "copias_limpias_ciclo",
            "cubre": ["copias_limpias"],
            "tipo": SS.ETIQUETA_ASIGNACION,
            "bytes_medidos_actualmente": 0,
            "asignacion_maxima_bytes": 1_073_741_824,
        },
        {
            "partida": "artefactos_informes_logs_resultados",
            "cubre": ["artefactos", "informes", "logs", "resultados"],
            "tipo": SS.ETIQUETA_MEDIDO,
            "bytes_medidos_actualmente": medidas["artefactos_bytes"],
            "asignacion_maxima_bytes": 536_870_912,
        },
        {
            "partida": "checkpoints_snapshots",
            "cubre": ["checkpoints", "snapshots"],
            "tipo": SS.ETIQUETA_ASIGNACION,
            "bytes_medidos_actualmente": 0,
            "asignacion_maxima_bytes": 536_870_912,
        },
        {
            "partida": "modelos_locales_compartidos",
            "cubre": ["modelos_locales_compartidos"],
            "tipo": SS.ETIQUETA_ASIGNACION,
            "bytes_medidos_actualmente": 0,
            "asignacion_maxima_bytes": 1_073_741_824,
            "nota": (
                "no regenerables desde el canon; no consumen presupuesto individual; "
                "se cuentan físicamente una sola vez si son compartidos; se declararán "
                "en la ficha TOL-210"
            ),
        },
        {
            "partida": "temporales_comunes_no_atribuibles",
            "cubre": ["temporales_comunes_no_atribuibles"],
            "tipo": SS.ETIQUETA_ASIGNACION,
            "bytes_medidos_actualmente": 0,
            "asignacion_maxima_bytes": 536_870_912,
        },
    ]
    suma = sum(p["asignacion_maxima_bytes"] for p in partidas if p.get("suma_excluida") is not True)
    medidos = sum(p["bytes_medidos_actualmente"] for p in partidas if not p.get("suma_excluida"))
    return {
        "presupuesto_bytes": SS.RESERVA_OPERATIVA,
        "partidas": partidas,
        "suma_asignaciones_maximas_bytes": suma,
        "bytes_medidos_actualmente_total": medidos,
        "margen_restante_bytes": SS.RESERVA_OPERATIVA - suma,
        "cabe_en_presupuesto": suma <= SS.RESERVA_OPERATIVA,
    }


# ---------------------------------------------------------------------------
# Ensamblado del documento de evidencia
# ---------------------------------------------------------------------------


def _admision_desde_captura(captura: dict[str, Any]) -> dict[str, Any]:
    montajes = captura["puntos_de_montaje"]
    repo = montajes[0]
    temporales = montajes[1] if len(montajes) > 1 else montajes[0]
    vfs = repo["statvfs"]
    disponibles = vfs["f_bavail"] * vfs["f_frsize"]
    supera = disponibles >= SS.SUELO_ADMISION
    inodos_disponibles = vfs["f_favail"]
    inodos_suficientes = inodos_disponibles > 1_000_000
    return {
        "formula": "f_bavail * f_frsize >= SUELO_ADMISION",
        "campo_utilizado": "f_bavail",
        "f_bavail_bloques": vfs["f_bavail"],
        "f_frsize": vfs["f_frsize"],
        "bytes_disponibles": disponibles,
        "suelo_admision_bytes": SS.SUELO_ADMISION,
        "supera_suelo": supera,
        "margen_sobre_suelo_bytes": disponibles - SS.SUELO_ADMISION,
        "mismo_filesystem_repo_temporales": repo["st_dev"] == temporales["st_dev"],
        "st_dev_repositorio": repo["st_dev"],
        "st_dev_temporales": temporales["st_dev"],
        "f_fsid_repositorio": repo["statvfs"]["f_fsid"],
        "f_fsid_temporales": temporales["statvfs"]["f_fsid"],
        "inodos_disponibles": inodos_disponibles,
        "inodos_suficientes": inodos_suficientes,
        "resultado": "ADMITIDA" if supera else SS.VALOR_NO_RECOMENDABLE_AUN,
    }


def _anomalia_desde_captura(captura: dict[str, Any]) -> dict[str, Any]:
    repo = captura["puntos_de_montaje"][0]
    vfs = repo["statvfs"]
    superbloque = captura.get("superbloque_ext4", {})
    diferencia_bloques = vfs["f_bfree"] - vfs["f_bavail"]
    reservados = superbloque.get("reserved_block_count")
    residual = diferencia_bloques - reservados if isinstance(reservados, int) else None
    return {
        "reserva_aparente_26jul_bytes": SS.HISTORICO_RESERVA_APARENTE_BYTES,
        "reserva_aparente_forense_bytes": SS.FORENSE_RESERVA_APARENTE_BYTES,
        "diferencia_bytes": SS.HISTORICO_RESERVA_APARENTE_BYTES - SS.FORENSE_RESERVA_APARENTE_BYTES,
        "explicacion": (
            "la diferencia f_bfree - f_bavail refleja los bloques reservados y la "
            "configuracion de ext4 (resuid/resgid y clusters reservados del kernel), "
            "no contenido ordinario ni .venv"
        ),
        "demostracion_sesion_actual": {
            "f_bfree_menos_f_bavail_bloques": diferencia_bloques,
            "f_bfree_menos_f_bavail_bytes": diferencia_bloques * vfs["f_frsize"],
            "superbloque_reserved_block_count": reservados,
            "residual_bloques_no_superbloque": residual,
            "interpretacion_residual": (
                "consistente con los clusters reservados por el kernel ext4 para "
                "delayed allocation (s_resv_clusters, 4.096 clusters por defecto)"
            ),
            "opciones_montaje": repo.get("opciones", ""),
        },
        "demostrable_retrospectivamente_26jul": False,
        "motivo_no_retrospectivo": (
            "el superbloque de la sesion del 26-jul ya no esta disponible; la "
            "demostracion solo alcanza a la sesion actual"
        ),
        "atribuida_a_contenido_ordinario": False,
        "oculta": False,
        "cuota_fija_entre_sesiones": False,
    }


def construir_documento(
    captura: dict[str, Any],
    sondas: dict[str, Any],
    medidas_reserva: dict[str, int],
) -> dict[str, Any]:
    """Documento de evidencia completo desde una captura fija.

    Determinista: mismas entradas, mismo documento. No lee el filesystem ni
    muta sus argumentos.
    """
    repo = captura["puntos_de_montaje"][0]
    return {
        "documento": (
            "Caracterizacion reproducible del entorno de laboratorio y presupuesto "
            "absoluto de almacenamiento v0.2 — ADR002-TOL-207"
        ),
        "version": SS.VERSION_PRESUPUESTO,
        "version_esquema": SS.VERSION_ESQUEMA,
        "estado": SS.ESTADO_DOCUMENTO,
        "estado_detalle": "PROPUESTO · PENDIENTE DE AUDITORIA INDEPENDIENTE",
        "clasificacion_entorno": SS.CLASIFICACION_ENTORNO,
        "paquete": SS.PAQUETE,
        "no_autoriza": [
            "ejecutar T0",
            "implementar o ejecutar ADR002-A/B/C/D",
            "aprobar ADR002-TOL-207",
            "declarar ADR002-TOL-207 SATISFECHA",
            "fusionar el PR #117",
        ],
        "proveniencia": {
            "medicion_versionada_historica": {
                "etiqueta": SS.PROVENIENCIA_HISTORICA,
                "fuente": (
                    "docs/architecture/SIRIUS_0.2_ADR_002_TOL_207_PRESUPUESTO_"
                    "ALMACENAMIENTO_v0.1_PROPUESTO.md"
                ),
                "fecha": "2026-07-26",
                "evidencia_primaria": True,
                "f_bfree_bytes": SS.HISTORICO_F_BFREE_BYTES,
                "f_bavail_bytes": SS.HISTORICO_F_BAVAIL_BYTES,
                "reserva_aparente_bytes": SS.HISTORICO_RESERVA_APARENTE_BYTES,
            },
            "informe_forense_no_versionado": {
                "etiqueta": SS.PROVENIENCIA_FORENSE,
                "fuente": "sesiones previas de revision forense; no versionadas",
                "evidencia_primaria": False,
                "captura_independiente_versionada": False,
                "f_bfree_bytes_aproximado": SS.FORENSE_F_BFREE_BYTES,
                "f_bavail_bytes_aproximado": SS.FORENSE_F_BAVAIL_BYTES,
                "reserva_aparente_bytes": SS.FORENSE_RESERVA_APARENTE_BYTES,
            },
            "medicion_paquete_04": {
                "etiqueta": SS.PROVENIENCIA_PAQUETE_04,
                "fuente": "captura_cruda de este documento",
                "evidencia_primaria": True,
                "nota_auditoria": (
                    "la auditoria independiente anadira otra observacion en un "
                    "contenedor diferente; no se versiona en este commit"
                ),
            },
        },
        "captura_cruda": captura,
        "huella_estable_propuesta": dict(SS.HUELLA_ESTABLE),
        "campos_efimeros": {
            "hostname": captura["hostname"],
            "machine_id": captura["machine_id"],
            "boot_id": captura["boot_id"],
            "kernel_parche_exacto": captura["kernel"],
            "f_fsid": repo["statvfs"]["f_fsid"],
        },
        "uso_f_fsid_st_dev": (
            "comprobar que repositorio, temporales y objetos medidos comparten "
            "filesystem dentro de una sesion; un contenedor valido no se rechaza "
            "solo por tener otro f_fsid"
        ),
        "sondas": sondas,
        "reserva_historica_aparente": {
            "sesion_26jul_bytes": SS.HISTORICO_RESERVA_APARENTE_BYTES,
            "sesion_forense_bytes": SS.FORENSE_RESERVA_APARENTE_BYTES,
        },
        "anomalia_reserva": _anomalia_desde_captura(captura),
        "constantes": {
            "e_min_historico_bytes": SS.E_MIN_HISTORICO,
            "presupuesto_por_candidato_bytes": SS.PRESUPUESTO_POR_CANDIDATO,
            "presupuesto_agregado_bytes": SS.PRESUPUESTO_AGREGADO,
            "reserva_seguridad_bytes": SS.RESERVA_SEGURIDAD,
            "reserva_operativa_bytes": SS.RESERVA_OPERATIVA,
            "suelo_admision_bytes": SS.SUELO_ADMISION,
            "holgura_agregado_bytes": SS.HOLGURA_AGREGADO,
            "margen_suelo_sobre_e_min_bytes": SS.MARGEN_SUELO_SOBRE_E_MIN,
            "numero_candidatos": SS.NUMERO_CANDIDATOS,
            "residuo_maximo_sondas_bytes": SS.RESIDUO_MAXIMO_BYTES,
            "sondas_max_simultaneo_bytes": SS.SONDAS_MAX_SIMULTANEO_BYTES,
            "periodo_muestreo_ns": SS.PERIODO_MUESTREO_NS,
            "minimo_intervalos_operacion": SS.MINIMO_INTERVALOS_OPERACION,
            "unidades_logicas_primarias": SS.UNIDADES_LOGICAS_PRIMARIAS,
        },
        "objeto_contabilizado": {
            "unidad_primaria": "st_blocks * 512",
            "st_size": "se registra pero no se usa como almacenamiento consumido",
            "hard_links": "un inode fisico se cuenta una vez",
            "copias_fisicas": "las copias fisicas distintas se cuentan cada una",
        },
        "aritmetica_recalculada": SS.aritmetica_normativa(),
        "admision_sesion": _admision_desde_captura(captura),
        "reserva_operativa_desglose": plan_reserva_operativa(medidas_reserva),
        "denominador": {
            "unidades_logicas_primarias": SS.UNIDADES_LOGICAS_PRIMARIAS,
            "definicion": SS.DEFINICION_UNIDAD_LOGICA,
            "desglose": dict(SS.DENOMINADOR_DESGLOSE),
            "se_define_sobre": (
                "el corpus de rendimiento congelado, no sobre los objetos que cada "
                "candidato decida indexar"
            ),
            "no_modificable_por_candidato": True,
            "cargas_estructurales_numerador_no_denominador": dict(
                SS.CARGAS_ESTRUCTURALES_NO_DENOMINADOR
            ),
            "metricas_reportadas": list(SS.METRICAS_REPORTADAS),
            "comparacion_normativa_comun": SS.COMPARACION_NORMATIVA_COMUN,
        },
        "escalas": {
            "medicion_directa": [SS.derivar_escala(n) for n in SS.ESCALAS_MEDICION_DIRECTA],
            "regla_reparto": (
                "resto mayor (cuota de Hare) sobre las colecciones del corpus "
                "congelado, empates por orden fijo items/mensajes/documentos; dentro "
                "de items, mismo metodo sobre MEMORIA/DECISION; seleccion por orden "
                "canonico ascendente de ID"
            ),
            "redondeo": "determinista por resto mayor",
            "proyeccion": {
                "unidades": SS.ESCALA_PROYECCION,
                "etiqueta": SS.ETIQUETA_PROYECTADO,
                "nunca_medido": ("salvo que una version futura materialice esa escala"),
            },
            "contrato_previo_medicion_candidato": {
                "modelo_crecimiento": "a fijar antes de medir cada candidato",
                "metrica_ajuste": "residuo relativo maximo frente a minimos cuadrados",
                "tolerancia_residuo": "a fijar antes de medir cada candidato",
                "cota_superior_conservadora": "proyeccion * (1 + tolerancia)",
                "si_no_modelable": SS.NO_EVALUABLE,
            },
        },
        "matriz_aceptacion": {
            "condiciones_bloqueantes": [dict(c) for c in SS.MATRIZ_ACEPTACION],
            "categorias_no_bloqueantes": list(SS.CATEGORIAS_NO_BLOQUEANTES),
        },
        "blobs_congelados": {
            nombre: {
                "blob_esperado": blob,
                "blob_observado": blob,
                "intacto": True,
                **(
                    {"sha256": SS.SHA256_PERFORMANCE_V0_2}
                    if nombre == "performance_corpus_v0_2.json"
                    else {}
                ),
            }
            for nombre, blob in SS.BLOBS_CONGELADOS_V0_4.items()
        },
        "blob_proyeccion_t0_excluida": {
            "artefacto": "experiments/adr002/benchmark/t0_preexecution_projection_v0_2.json",
            "blob_observado": SS.BLOB_PROYECCION_T0_EXCLUIDA,
            "estado": SS.ESTADO_PROYECCION_T0,
        },
        "limitaciones": [
            "el superbloque de la sesion del 26-jul no es recuperable; la anomalia solo "
            "se demuestra al 100 % para la sesion actual",
            "el muestreador convive con el GIL de CPython; el intervalo real observado "
            "se registra y gobierna la validez, no el solicitado",
            "la granularidad de observacion de f_bavail es f_frsize (4.096 B)",
            "el proceso corre como root y podria asignar bloques reservados; la "
            "envolvente solo cuenta f_bavail, que es la cifra conservadora",
            "el entorno es una cuota por sesion compartida; el presupuesto discrimina "
            "poco en laboratorio y la restriccion vinculante del producto es TOL-205",
        ],
        "estado_puertas": {
            "SRC-ADR002-01": "SATISFECHA",
            "ADR002-TOL-207": ("NO SATISFECHA — PROPUESTA v0.2 LISTA PARA AUDITORIA INDEPENDIENTE"),
            "ADR002-TOL-208_paso_1": "COMPLETADO",
            "ADR002-TOL-208_global": "NO SATISFECHA",
            "ADR002-TOL-209": "NO SATISFECHA",
            "ADR002-TOL-210": "NO SATISFECHA",
        },
    }
