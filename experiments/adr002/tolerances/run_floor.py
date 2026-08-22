"""Orquestador de la corrida del suelo de medicion (ADR002-TOL-209).

La fase A congela este codigo SIN ejecutarlo. La fase D —previa
autorizacion expresa e independiente— ejecuta exactamente este codigo,
sin modificarlo, mediante:

    uv run python -m experiments.adr002.tolerances.run_floor \\
        --execute \\
        --preinscription-commit <SHA_A> \\
        --output artifacts/adr002_tolerances/suelo_medicion_v0.1.json

Garantias de este modulo:

- **No mide nada al importarse** y **no mide nada sin ``--execute``**.
- Antes de abrir una sola ventana cronometrada comprueba, fallando
  cerrado: arbol de trabajo limpio, HEAD exactamente igual al commit de
  preinscripcion, existencia de ese commit, coincidencia de los seis
  blobs preinscritos con el arbol, protocolo aprobado intacto, blobs del
  corpus congelado intactos y ruta de salida inexistente.
- El recorrido completo es: precondiciones -> lanzamiento de procesos
  independientes -> sondas en round-robin -> controles internos ->
  derivacion (SM, B50, B95, B, U) -> documento -> validacion con
  ``schema_floor_v0_1`` -> escritura atomica -> relectura y revalidacion.
- Si CUALQUIER control bloqueante falla, no se escribe ningun artefacto
  y no se publica ningun valor.

Las dependencias externas (custodia Git, ejecutor de procesos, captura
de entorno, carga de la linea base) son inyectables, de modo que las
pruebas recorren este mismo camino con dobles controlados y sin ejecutar
la medicion real.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from experiments.adr002.tolerances import floor_probes as sondas
from experiments.adr002.tolerances import floor_protocol as fp
from experiments.adr002.tolerances import schema_floor_v0_1 as esquema

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

RUTA_LINEA_BASE: Final = "artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json"

CODIGO_OK: Final = 0
CODIGO_BLOQUEADO: Final = 2
CODIGO_SIN_EXECUTE: Final = 3

CLAVES_RESULTADO_PROCESO: Final[tuple[str, ...]] = (
    "pid",
    "sondas",
    "reloj",
    "busy_spin",
    "duplicacion",
    "puerto",
    "cargas",
    "incidencias",
    "filtrado_aplicado",
    "warmup_mezclado",
)


class EjecucionBloqueadaError(RuntimeError):
    """Una precondicion de custodia o de entorno no se cumple."""


# --------------------------------------------------------------------------
# Acceso a Git, aislado para poder inyectarlo en las pruebas
# --------------------------------------------------------------------------


def _git(*argumentos: str, raiz: Path | None = None) -> str:
    destino = RAIZ_REPOSITORIO if raiz is None else raiz
    completado = subprocess.run(
        ["git", *argumentos],
        cwd=str(destino),
        capture_output=True,
        text=True,
        check=False,
    )
    if completado.returncode != 0:
        msg = f"git {' '.join(argumentos)} fallo: {completado.stderr.strip()}"
        raise EjecucionBloqueadaError(msg)
    return completado.stdout.strip()


def entorno_custodia_real(raiz: Path | None = None) -> fp.EntornoCustodia:
    """Construye el entorno de custodia sobre el repositorio real."""
    destino = RAIZ_REPOSITORIO if raiz is None else raiz

    def leer_bytes(ruta: str) -> bytes:
        return (destino / ruta).read_bytes()

    def es_ancestro(antepasado: str, descendiente: str) -> bool:
        completado = subprocess.run(
            ["git", "merge-base", "--is-ancestor", antepasado, descendiente],
            cwd=str(destino),
            capture_output=True,
            text=True,
            check=False,
        )
        return completado.returncode == 0

    def existe_commit(sha: str) -> bool:
        completado = subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
            cwd=str(destino),
            capture_output=True,
            text=True,
            check=False,
        )
        return completado.returncode == 0

    def head() -> str:
        return _git("rev-parse", "HEAD", raiz=destino)

    def arbol_limpio() -> bool:
        return _git("status", "--porcelain", raiz=destino) == ""

    def diff_vacio(desde: str, hasta: str, rutas: Sequence[str]) -> bool:
        completado = subprocess.run(
            ["git", "diff", "--quiet", f"{desde}..{hasta}", "--", *rutas],
            cwd=str(destino),
            capture_output=True,
            text=True,
            check=False,
        )
        return completado.returncode == 0

    def blob_en_commit(sha: str, ruta: str) -> str | None:
        """Blob que el commit ``sha`` registra para ``ruta``, o None.

        Fuente de verdad independiente del arbol de trabajo: es lo que
        hace que la comparacion de custodia no sea tautologica.
        """
        completado = subprocess.run(
            ["git", "rev-parse", f"{sha}:{ruta}"],
            cwd=str(destino),
            capture_output=True,
            text=True,
            check=False,
        )
        if completado.returncode != 0:
            return None
        return completado.stdout.strip() or None

    return fp.EntornoCustodia(
        leer_bytes=leer_bytes,
        es_ancestro=es_ancestro,
        existe_commit=existe_commit,
        head=head,
        arbol_limpio=arbol_limpio,
        diff_vacio=diff_vacio,
        blob_en_commit=blob_en_commit,
    )


# --------------------------------------------------------------------------
# Precondiciones
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Precondiciones:
    """Resultado de todas las comprobaciones previas a medir."""

    fallos: tuple[str, ...]
    blobs_preinscritos: Mapping[str, str]
    blob_arnes: str

    @property
    def permite_medir(self) -> bool:
        return not self.fallos


def comprobar_precondiciones(
    entorno: fp.EntornoCustodia,
    *,
    sha_a: str,
    salida: Path,
    salida_existe: bool | None = None,
) -> Precondiciones:
    """Comprueba custodia y entorno. Falla cerrado y no mide nada."""
    existe = salida.exists() if salida_existe is None else salida_existe
    fallos = list(fp.verificar_precondiciones_ejecucion(entorno, sha_a=sha_a, salida_existe=existe))

    blobs_preinscritos: dict[str, str] = {}
    for ruta in fp.ARCHIVOS_PREINSCRITOS:
        try:
            blobs_preinscritos[ruta] = fp.blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"fichero preinscrito ilegible: {ruta}")

    try:
        blob_arnes = fp.blob_git(entorno.leer_bytes(fp.ARCHIVO_ARNES_HEREDADO))
    except OSError:
        blob_arnes = ""
        fallos.append(f"arnes heredado ilegible: {fp.ARCHIVO_ARNES_HEREDADO}")

    try:
        ruta_protocolo = f"docs/architecture/{fp.PROTOCOLO}"
        if fp.blob_git(entorno.leer_bytes(ruta_protocolo)) != fp.BLOB_PROTOCOLO_APROBADO:
            fallos.append("el protocolo aprobado ha sido modificado")
    except OSError:
        fallos.append("protocolo aprobado ilegible")

    if blobs_preinscritos and blob_arnes:
        fallos.extend(
            fp.verificar_custodia(
                entorno,
                sha_a=sha_a,
                blobs_preinscritos=blobs_preinscritos,
                blob_arnes=blob_arnes,
            )
        )

    return Precondiciones(
        fallos=tuple(dict.fromkeys(fallos)),
        blobs_preinscritos=blobs_preinscritos,
        blob_arnes=blob_arnes,
    )


# --------------------------------------------------------------------------
# Plan de la corrida
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlanCorrida:
    """Plan declarado de la corrida. No contiene ninguna observacion."""

    procesos: int
    n_por_sonda: int
    warmup_por_sonda: int
    n_reloj: int
    warmup_reloj: int
    semilla: int
    sondas_normativas: tuple[str, ...]
    diagnosticos: tuple[str, ...]
    orden: tuple[str, ...]


def plan_de_corrida(rondas: int = fp.RONDAS_ROUND_ROBIN) -> PlanCorrida:
    """Construye el plan declarado. Puro: no mide, no abre ficheros."""
    return PlanCorrida(
        procesos=fp.PROCESOS_MINIMOS,
        n_por_sonda=fp.N_SONDA_F,
        warmup_por_sonda=fp.WARMUP_SONDA_F,
        n_reloj=fp.N_SONDA_RELOJ,
        warmup_reloj=fp.WARMUP_SONDA_RELOJ,
        semilla=fp.SEMILLA,
        sondas_normativas=fp.F_NORMATIVO,
        diagnosticos=fp.DIAGNOSTICOS,
        orden=tuple(sondas.orden_round_robin(fp.F_NORMATIVO, rondas)),
    )


# --------------------------------------------------------------------------
# Worker: medicion real dentro de UN proceso hijo (solo fase D)
# --------------------------------------------------------------------------


def _resumen_diagnostico(muestras: Sequence[int], *, warmup: int) -> dict[str, Any]:
    ordenadas = sorted(int(x) for x in muestras)
    return {
        "n": len(ordenadas),
        "warmup_descartado": warmup,
        "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
        "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
        "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
        "min_ns": ordenadas[0],
        "max_ns": ordenadas[-1],
    }


def _carga_actual() -> float:
    return os.getloadavg()[0]


def ejecutar_sondas_worker() -> dict[str, Any]:
    """Recorrido de medicion de UN proceso. Solo lo invoca la fase D.

    Prepara su propia base (fichero, motor, cache y warm-up propios,
    §3.3), ejecuta las sondas de F en round-robin por rondas (§5.2
    aplicado a sondas) y los diagnosticos, y devuelve el resultado crudo.
    No escribe ningun artefacto: el padre agrega, valida y publica.
    """
    from experiments.adr002.tolerances import corpus

    incidencias: list[str] = []
    cargas: list[float] = [_carga_actual()]

    base = corpus.nueva_base_temporal("adr002_floor_")
    corpus.construir_esquema(base)
    corpus.poblar(base)
    fixture = sondas.preparar_fixture_sqlite(base)

    consulta_0 = fixture.clave_inexistente
    consulta_1 = fixture.clave_existente
    conexion = fixture.conexion

    def op_vacia() -> None:
        return None

    def op_sqlite_0() -> None:
        conexion.execute(sondas.SQL_SONDA_SQLITE, (consulta_0,)).fetchall()

    def op_sqlite_1() -> None:
        conexion.execute(sondas.SQL_SONDA_SQLITE, (consulta_1,)).fetchall()

    operaciones: dict[str, Callable[[], None]] = {
        fp.SONDA_VACIA: op_vacia,
        fp.SONDA_SQLITE_0: op_sqlite_0,
        fp.SONDA_SQLITE_1: op_sqlite_1,
    }
    sondas.comprobar_sql_de_sonda()

    reloj = sondas.diagnostico_lecturas_reloj()
    busy_inicio = fp.p50_ns(sondas.diagnostico_busy_spin(vueltas=fp.VUELTAS_BUSY_SPIN))

    # Warm-up declarado, una vez por sonda, descartado integro.
    for operacion in operaciones.values():
        for _ in range(fp.WARMUP_SONDA_F):
            operacion()

    rondas = fp.RONDAS_ROUND_ROBIN
    tramo = fp.N_SONDA_F // rondas
    vectores: dict[str, list[int]] = {nombre: [] for nombre in fp.F_NORMATIVO}
    busy_mitad = 0
    for ronda in range(rondas):
        for nombre in fp.F_NORMATIVO:
            vectores[nombre].extend(sondas.medir_ns(operaciones[nombre], n=tramo, warmup=0))
        if ronda == rondas // 2 - 1:
            busy_mitad = fp.p50_ns(sondas.diagnostico_busy_spin(vueltas=fp.VUELTAS_BUSY_SPIN))
            cargas.append(_carga_actual())

    busy_final = fp.p50_ns(sondas.diagnostico_busy_spin(vueltas=fp.VUELTAS_BUSY_SPIN))
    duplicacion = sondas.diagnostico_duplicacion(vueltas=fp.VUELTAS_BUSY_SPIN)
    cargas.append(_carga_actual())

    # Verificacion de forma de las sondas SQLite, fuera del cronometro.
    # Registrar la incidencia NO basta: el padre trata cualquier incidencia
    # como bloqueante, y el esquema impide publicar B y U con incidencias.
    if len(conexion.execute(sondas.SQL_SONDA_SQLITE, (consulta_0,)).fetchall()) != 0:
        incidencias.append("SQLite_0_filas devolvio filas")
    if len(conexion.execute(sondas.SQL_SONDA_SQLITE, (consulta_1,)).fetchall()) != 1:
        incidencias.append("SQLite_1_fila no devolvio exactamente una fila")

    # Diagnostico del puerto comun real, fuera de F.
    from sirius.adapters.persistence.sqlite_knowledge_search_repository import (  # type: ignore[import-untyped]
        build_sqlite_knowledge_search_repository,
    )

    repositorio = build_sqlite_knowledge_search_repository(base)
    try:
        puerto = sondas.diagnostico_sobrecoste_puerto(
            repositorio.search_knowledge, corpus.TOKEN_UNICO
        )
    finally:
        repositorio.close()
    conexion.close()

    deltas_distintos = sorted(set(reloj))
    return {
        "pid": sondas.pid_actual(),
        "sondas": {
            nombre: {
                "muestras_ns": vectores[nombre],
                "warmup_descartado": fp.WARMUP_SONDA_F,
            }
            for nombre in fp.F_NORMATIVO
        },
        "reloj": {
            **_resumen_diagnostico(reloj, warmup=fp.WARMUP_SONDA_RELOJ),
            "deltas_distintos_ns": deltas_distintos,
            "min_no_nulo_ns": next((d for d in deltas_distintos if d > 0), None),
        },
        "busy_spin": {
            "vueltas": fp.VUELTAS_BUSY_SPIN,
            "p50_inicio_ns": busy_inicio,
            "p50_mitad_ns": busy_mitad,
            "p50_final_ns": busy_final,
        },
        "duplicacion": {
            "vueltas_1x": duplicacion.vueltas_1x,
            "vueltas_2x": duplicacion.vueltas_2x,
            "p50_1x_ns": duplicacion.p50_1x,
            "p50_2x_ns": duplicacion.p50_2x,
        },
        "puerto": _resumen_diagnostico(puerto, warmup=fp.WARMUP_DIAGNOSTICO),
        "cargas": cargas,
        "incidencias": incidencias,
        "filtrado_aplicado": False,
        "warmup_mezclado": False,
    }


def ejecutor_procesos_reales(plan: PlanCorrida) -> list[Mapping[str, Any]]:
    """Lanza ``plan.procesos`` procesos del sistema operativo, secuenciales.

    Cada hijo ejecuta ``--worker`` y devuelve su resultado por stdout en
    JSON. Solo la fase D llega aqui; las pruebas inyectan otro ejecutor.
    """
    resultados: list[Mapping[str, Any]] = []
    orden = [
        sys.executable,
        "-m",
        "experiments.adr002.tolerances.run_floor",
        "--execute",
        "--worker",
    ]
    for _ in range(plan.procesos):
        completado = subprocess.run(
            orden,
            cwd=str(RAIZ_REPOSITORIO),
            capture_output=True,
            text=True,
            check=False,
        )
        if completado.returncode != 0:
            msg = f"worker fallo (rc={completado.returncode}): {completado.stderr.strip()[:500]}"
            raise EjecucionBloqueadaError(msg)
        resultados.append(json.loads(completado.stdout))
    return resultados


# --------------------------------------------------------------------------
# Captura de entorno y linea base (inyectables)
# --------------------------------------------------------------------------


def capturar_entorno_real(etapa: str) -> dict[str, Any]:
    """Captura reducida y suficiente para los controles de esta puerta."""
    from experiments.adr002.storage.environment_capture import capturar_entorno

    with tempfile.TemporaryDirectory(prefix="adr002_floor_env_") as temporal:
        captura = capturar_entorno(RAIZ_REPOSITORIO, Path(temporal))
    return {
        "etapa": etapa,
        "boot_id": captura.get("boot_id"),
        "carga": _carga_actual(),
        "captura": captura,
    }


def cargar_linea_base_real() -> Mapping[str, Any]:
    """Evidencia versionada de la linea base, solo para clasificacion."""
    ruta = RAIZ_REPOSITORIO / RUTA_LINEA_BASE
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        msg = f"{RUTA_LINEA_BASE} no contiene un objeto JSON"
        raise EjecucionBloqueadaError(msg)
    return datos


def _ms_a_ns(valor: Any) -> int:
    return round(float(valor) * 1_000_000)


def clasificar_linea_base(
    linea_base: Mapping[str, Any], *, sm: int, b: int, u: int
) -> list[dict[str, Any]]:
    """Clasificacion DIAGNOSTICA de las magnitudes historicas publicadas.

    Nunca modifica B ni U (matriz 36): solo informa en que regimen caeria
    cada magnitud de la linea base con los valores derivados del suelo.
    Si no reproduce la particion historica, eso se explica en el informe,
    no se corrige a posteriori.
    """
    escenarios = linea_base["escenarios_remedidos"]["E-SESIONES-5_variacion_entre_ejecuciones"][
        "variacion_entre_sesiones"
    ]
    entradas: list[dict[str, Any]] = []
    for escenario, magnitudes in escenarios.items():
        if not isinstance(magnitudes, Mapping):
            continue  # claves resumen del artefacto (p. ej. la peor variacion global)
        capas = sorted({clave.rsplit("__", 1)[0] for clave in magnitudes if clave.endswith("_ms")})
        for capa in capas:
            p50s = [_ms_a_ns(v) for v in magnitudes[f"{capa}__p50_ms"]["valores_por_sesion"]]
            p95s = [_ms_a_ns(v) for v in magnitudes[f"{capa}__p95_ms"]["valores_por_sesion"]]
            veredicto = fp.evaluar_magnitud(p50s, p95s, sm=sm, b=b, u=u)
            entrada: dict[str, Any] = {
                "magnitud": f"{escenario}.{capa}",
                "fuente": RUTA_LINEA_BASE,
                "min_p50_ns": min(p50s),
                "min_p95_ns": min(p95s),
                "registro": fp.registro_por_percentil(veredicto),
            }
            if veredicto.dominada_por_instrumento:
                entrada["resultado"] = fp.NO_EVALUABLE
            else:
                regimenes = {v.percentil: v.regimen for v in veredicto.por_percentil}
                entrada["p50"] = regimenes["P50"]
                entrada["p95"] = regimenes["P95"]
            entradas.append(entrada)
    return entradas


# --------------------------------------------------------------------------
# Controles internos desde los resultados
# --------------------------------------------------------------------------


def _fallos_forma_resultado(resultado: Mapping[str, Any], indice: int) -> list[str]:
    fallos = [
        f"resultado[{indice}] sin la clave {clave}"
        for clave in CLAVES_RESULTADO_PROCESO
        if clave not in resultado
    ]
    if fallos:
        return fallos
    sondas_medidas = resultado["sondas"]
    if not isinstance(sondas_medidas, Mapping):
        return [f"resultado[{indice}]: sondas debe ser un mapa"]
    for nombre in fp.F_NORMATIVO:
        if nombre not in sondas_medidas:
            fallos.append(f"resultado[{indice}]: falta la sonda {nombre}")
    return fallos


def _vector_entero(valores: Any) -> list[int] | None:
    if not isinstance(valores, Sequence) or isinstance(valores, str | bytes):
        return None
    salida: list[int] = []
    for v in valores:
        if not isinstance(v, int) or isinstance(v, bool):
            return None
        salida.append(v)
    return salida


def _parece_redondeado(vector: Sequence[int]) -> bool:
    return len(vector) >= 2 and len(set(vector)) > 1 and all(v % 100 == 0 for v in vector)


def evaluar_controles_desde_resultados(
    resultados: Sequence[Mapping[str, Any]],
    *,
    captura_inicial: Mapping[str, Any],
    captura_final: Mapping[str, Any],
    custodia_ok: bool,
) -> dict[str, bool]:
    """Deriva el estado de los doce controles bloqueantes desde los datos.

    Todo se recomputa desde los datos crudos: los flags que declara cada
    proceso se cruzan, nunca se aceptan como unica fuente.
    """
    pids = [r.get("pid") for r in resultados]
    pids_validos = all(isinstance(p, int) and not isinstance(p, bool) and p > 0 for p in pids)

    vectores_ok = True
    sin_redondeo = True
    warmup_ok = True
    sin_filtrado = True
    for resultado in resultados:
        sondas_medidas = resultado.get("sondas")
        if not isinstance(sondas_medidas, Mapping):
            vectores_ok = False
            continue
        if resultado.get("filtrado_aplicado") is not False:
            sin_filtrado = False
        if resultado.get("warmup_mezclado") is not False:
            warmup_ok = False
        for nombre in fp.F_NORMATIVO:
            medida = sondas_medidas.get(nombre)
            if not isinstance(medida, Mapping):
                vectores_ok = False
                continue
            vector = _vector_entero(medida.get("muestras_ns"))
            if vector is None or len(vector) != fp.N_SONDA_F:
                vectores_ok = False
                continue
            if _parece_redondeado(vector):
                sin_redondeo = False
            # El warm-up se RECOMPUTA contra el valor preinscrito, no se
            # acepta del flag del worker: un proceso que declare 0 mientras
            # el plan exige WARMUP_SONDA_F contradice su propio documento.
            warmup = medida.get("warmup_descartado")
            if (
                not isinstance(warmup, int)
                or isinstance(warmup, bool)
                or warmup != fp.WARMUP_SONDA_F
            ):
                warmup_ok = False

    def _p50s_busy(resultado: Mapping[str, Any]) -> tuple[int, int, int] | None:
        busy = resultado.get("busy_spin")
        if not isinstance(busy, Mapping):
            return None
        valores: list[int] = []
        for clave in ("p50_inicio_ns", "p50_mitad_ns", "p50_final_ns"):
            valor = busy.get(clave)
            if not isinstance(valor, int) or isinstance(valor, bool):
                return None
            valores.append(valor)
        return valores[0], valores[1], valores[2]

    busy_ok = True
    duplicacion_ok = True
    for resultado in resultados:
        p50s = _p50s_busy(resultado)
        if p50s is None or not fp.busy_spin_estable(*p50s):
            busy_ok = False
        dup = resultado.get("duplicacion")
        if not isinstance(dup, Mapping):
            duplicacion_ok = False
            continue
        p50_1x, p50_2x = dup.get("p50_1x_ns"), dup.get("p50_2x_ns")
        if (
            not isinstance(p50_1x, int)
            or not isinstance(p50_2x, int)
            or isinstance(p50_1x, bool)
            or isinstance(p50_2x, bool)
            or not sondas.escala_con_el_trabajo(p50_1x, p50_2x)
        ):
            duplicacion_ok = False

    cargas_ok = all(
        isinstance(r.get("cargas"), Sequence)
        and not isinstance(r.get("cargas"), str | bytes)
        and len(r["cargas"]) > 0
        for r in resultados
    ) and all("carga" in captura for captura in (captura_inicial, captura_final))

    # Toda muestra debe ser una duracion no negativa; y ninguna incidencia
    # observada por la corrida puede quedar como nota informativa.
    for resultado in resultados:
        sondas_medidas = resultado.get("sondas")
        if isinstance(sondas_medidas, Mapping):
            for nombre in fp.F_NORMATIVO:
                medida = sondas_medidas.get(nombre)
                if not isinstance(medida, Mapping):
                    continue
                vector = _vector_entero(medida.get("muestras_ns"))
                if vector is not None and any(v < 0 for v in vector):
                    vectores_ok = False
        incidencias = resultado.get("incidencias")
        if not isinstance(incidencias, Sequence) or isinstance(incidencias, str | bytes):
            vectores_ok = False
        elif incidencias:
            sin_filtrado = False

    boot_inicial = captura_inicial.get("boot_id")
    boot_final = captura_final.get("boot_id")
    boot_ok = bool(boot_inicial) and boot_inicial == boot_final

    return {
        "procesos_independientes": len(resultados) >= fp.PROCESOS_MINIMOS,
        "pids_distintos": pids_validos and len(set(pids)) == len(pids),
        "carga_registrada": cargas_ok,
        "boot_id_estable": boot_ok,
        "busy_spin_estable": busy_ok,
        "duplicacion_1x_2x": duplicacion_ok,
        "vectores_crudos_completos": vectores_ok,
        "sin_filtrado": sin_filtrado,
        "warmup_separado": warmup_ok,
        "sin_redondeo_previo": sin_redondeo,
        "captura_ambiental_presente": bool(boot_inicial) and bool(boot_final),
        "custodia_verificada": custodia_ok,
    }


# --------------------------------------------------------------------------
# Construccion del documento
# --------------------------------------------------------------------------


def _entrada_sonda(nombre: str, pid: int, vector: Sequence[int], warmup: int) -> dict[str, Any]:
    ordenadas = sorted(int(v) for v in vector)
    distintos = len(set(ordenadas))
    repeticion_maxima = max(ordenadas.count(v) for v in set(ordenadas)) if ordenadas else 0
    return {
        "sonda": nombre,
        "pid": pid,
        "n": len(ordenadas),
        "warmup_descartado": warmup,
        "muestras_ns": list(vector),
        "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
        "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
        "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
        "min_ns": ordenadas[0],
        "max_ns": ordenadas[-1],
        "media_truncada_ns": sum(ordenadas) // len(ordenadas),
        "resolucion_percentil": fp.resolucion_percentil(len(ordenadas)),
        # Diagnostico de forma del vector, no umbral automatico: permite a
        # un auditor distinguir un suelo cuantizado (muchos repetidos por
        # resolucion del reloj) de un vector recortado y repadeado. No se
        # convierte en control bloqueante porque ambos casos son
        # indistinguibles sin evidencia adicional (limitacion declarada).
        "valores_distintos": distintos,
        "repeticion_maxima": repeticion_maxima,
    }


def construir_documento(
    *,
    sha_a: str,
    head: str,
    blobs_preinscritos: Mapping[str, str],
    blob_arnes: str,
    resultados: Sequence[Mapping[str, Any]],
    captura_inicial: Mapping[str, Any],
    captura_final: Mapping[str, Any],
    controles: Mapping[str, bool],
    linea_base: Mapping[str, Any],
) -> dict[str, Any]:
    """Construye el artefacto completo exigido por ``schema_floor_v0_1``."""
    entradas_sondas: list[dict[str, Any]] = []
    medidas: list[fp.MedidaSonda] = []
    for resultado in resultados:
        pid = int(resultado["pid"])
        for nombre in fp.F_NORMATIVO:
            medida = resultado["sondas"][nombre]
            entrada = _entrada_sonda(
                nombre, pid, medida["muestras_ns"], int(medida["warmup_descartado"])
            )
            entradas_sondas.append(entrada)
            medidas.append(
                fp.MedidaSonda(
                    sonda=nombre,
                    pid=pid,
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

    derivacion = fp.derivar(medidas)
    clasificacion = clasificar_linea_base(
        linea_base, sm=derivacion.sm, b=derivacion.b, u=derivacion.u
    )

    incidencias: list[str] = []
    for resultado in resultados:
        incidencias.extend(str(i) for i in resultado.get("incidencias", []))

    plan = plan_de_corrida()
    return {
        "documento": "Suelo de medicion LAB-LINUX para ADR002-TOL-209",
        "version_esquema": fp.VERSION_ESQUEMA,
        "estado": fp.ESTADO_EVIDENCIA,
        "protocolo": fp.PROTOCOLO,
        "paquete": fp.PAQUETE,
        "plan": {
            "procesos": plan.procesos,
            "n_por_sonda": plan.n_por_sonda,
            "warmup_por_sonda": plan.warmup_por_sonda,
            "semilla": plan.semilla,
            "orden": list(plan.orden),
        },
        "preinscripcion": {
            "commit_a": sha_a,
            "head_en_ejecucion": head,
            "blobs_preinscritos": dict(blobs_preinscritos),
            "blob_arnes": blob_arnes,
            "blobs_corpus_congelado": dict(fp.BLOBS_CORPUS_CONGELADO),
            "blob_protocolo": fp.BLOB_PROTOCOLO_APROBADO,
        },
        "entorno": {
            "captura_inicial": dict(captura_inicial),
            "captura_final": dict(captura_final),
            "boot_id": captura_inicial.get("boot_id"),
            "carga_por_proceso": {
                str(resultado["pid"]): list(resultado["cargas"]) for resultado in resultados
            },
            "incidencias": incidencias,
        },
        "procesos": [{"pid": int(resultado["pid"])} for resultado in resultados],
        "sondas": entradas_sondas,
        "diagnosticos": {
            fp.DIAG_RELOJ: {"por_proceso": [dict(resultado["reloj"]) for resultado in resultados]},
            fp.DIAG_BUSY_SPIN: {
                "por_proceso": [dict(resultado["busy_spin"]) for resultado in resultados]
            },
            fp.DIAG_DUPLICACION: {
                "por_proceso": [dict(resultado["duplicacion"]) for resultado in resultados]
            },
            fp.DIAG_PUERTO: {
                "por_proceso": [dict(resultado["puerto"]) for resultado in resultados],
                "nota": "fuera de F por decision 8; nunca modifica B ni U",
            },
        },
        "controles_internos": dict(controles),
        "derivacion": {
            "sm_ns": derivacion.sm,
            "b50_ns": derivacion.b50,
            "b95_ns": derivacion.b95,
            "b_ns": derivacion.b,
            "u_ns": derivacion.u,
            "m": derivacion.m,
            "descomposicion_b": fp.descomposicion_b(medidas),
        },
        "regimenes_por_percentil": clasificacion,
        "clasificacion_diagnostica_linea_base": {
            "fuente": RUTA_LINEA_BASE,
            "nota": (
                "clasificacion diagnostica: nunca modifica B ni U; una particion "
                "distinta de la historica se explica, no se corrige"
            ),
            "magnitudes": clasificacion,
        },
        "custodia": {
            "sha_a_es_ancestro": True,
            "diff_preinscritos_vacio": True,
            "reverificada_tras_medir": True,
            "head": head,
        },
        "no_autoriza": {
            "limite_duro_tol_107": False,
            "aprobacion_tol_209": False,
            "t0": False,
            "candidatos": False,
            "benchmark": False,
            "merge_pr_117": False,
        },
    }


# --------------------------------------------------------------------------
# Escritura atomica
# --------------------------------------------------------------------------


def escribir_json_atomico(ruta: Path, documento: Mapping[str, Any]) -> None:
    """Escribe el artefacto de forma atomica y SIN sobrescribir nunca.

    Usa ``os.link`` en lugar de ``os.replace``: si la ruta de salida
    apareciese durante la medicion, ``link`` falla con ``FileExistsError``
    en vez de destruir el fichero existente en silencio. Cierra asi la
    ventana TOCTOU entre la precondicion «salida inexistente» y la
    publicacion.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    descriptor, nombre_temporal = tempfile.mkstemp(
        dir=str(ruta.parent), prefix=f"{ruta.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as fichero:
            # allow_nan=False: NaN e Infinity no son JSON estandar y no
            # pueden entrar en evidencia normativa.
            json.dump(documento, fichero, ensure_ascii=False, indent=1, allow_nan=False)
            fichero.write("\n")
            fichero.flush()
            os.fsync(fichero.fileno())
        os.link(nombre_temporal, ruta)
    except BaseException:
        # El temporal debe desaparecer SIEMPRE: si no se puede eliminar, no
        # se calla — un residuo con JSON valido y valores derivados seria
        # evidencia publicada por una corrida que se declara bloqueada.
        _eliminar_o_denunciar(Path(nombre_temporal), "temporal de escritura")
        raise
    else:
        _eliminar_o_denunciar(Path(nombre_temporal), "temporal de escritura")


class ResiduoNoEliminableError(RuntimeError):
    """Un fichero que debia desaparecer sigue en disco."""


def _eliminar_o_denunciar(ruta: Path, etiqueta: str) -> None:
    """Elimina ``ruta`` y verifica el estado del disco; nunca calla el fallo.

    Suprimir el error de borrado y seguir afirmando «no se ha publicado
    ningun valor» dejaria evidencia en disco contradiciendo el veredicto.
    """
    try:
        ruta.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        msg = f"{etiqueta} no eliminable: {ruta} ({exc})"
        raise ResiduoNoEliminableError(msg) from exc
    if ruta.exists():
        msg = f"{etiqueta} sigue en disco tras eliminarlo: {ruta}"
        raise ResiduoNoEliminableError(msg)


# --------------------------------------------------------------------------
# Recorrido completo de la corrida
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DependenciasCorrida:
    """Dependencias externas del recorrido, inyectables en las pruebas."""

    entorno_custodia: fp.EntornoCustodia
    ejecutor: Callable[[PlanCorrida], Sequence[Mapping[str, Any]]]
    capturar_entorno: Callable[[str], Mapping[str, Any]]
    cargar_linea_base: Callable[[], Mapping[str, Any]]


def dependencias_reales() -> DependenciasCorrida:
    """Dependencias de la fase D sobre el repositorio y la maquina reales."""
    return DependenciasCorrida(
        entorno_custodia=entorno_custodia_real(),
        ejecutor=ejecutor_procesos_reales,
        capturar_entorno=capturar_entorno_real,
        cargar_linea_base=cargar_linea_base_real,
    )


def ejecutar_corrida(
    *,
    sha_a: str,
    salida: Path,
    dependencias: DependenciasCorrida,
) -> tuple[int, tuple[str, ...]]:
    """Recorrido completo: precondiciones -> medicion -> documento -> JSON.

    Falla cerrado en cada paso: ante cualquier fallo bloqueante no se
    escribe ningun artefacto y no se publica ningun valor.
    """
    # Toda dependencia externa se invoca dentro de una guarda: una excepcion
    # que escapase de aqui saldria de ``main`` como traza en vez de como
    # CODIGO_BLOQUEADO, y el operador no obtendria el veredicto documentado.
    try:
        precondiciones = comprobar_precondiciones(
            dependencias.entorno_custodia, sha_a=sha_a, salida=salida
        )
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"comprobacion de precondiciones fallo: {exc}",)
    if not precondiciones.permite_medir:
        return CODIGO_BLOQUEADO, precondiciones.fallos

    try:
        captura_inicial = dependencias.capturar_entorno("inicial")
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"captura de entorno inicial fallo: {exc}",)

    plan = plan_de_corrida()
    try:
        resultados = list(dependencias.ejecutor(plan))
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"ejecutor de procesos fallo: {exc}",)

    try:
        captura_final = dependencias.capturar_entorno("final")
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"captura de entorno final fallo: {exc}",)

    fallos_forma: list[str] = []
    for indice, resultado in enumerate(resultados):
        fallos_forma.extend(_fallos_forma_resultado(resultado, indice))
    if fallos_forma:
        return CODIGO_BLOQUEADO, tuple(fallos_forma)

    # Custodia REVERIFICADA despues de medir y antes de publicar: si el
    # arbol, el HEAD o cualquier blob preinscrito cambiaron durante la
    # corrida, el codigo medido ya no es el preinscrito y no se publica.
    try:
        posteriores = comprobar_precondiciones(
            dependencias.entorno_custodia, sha_a=sha_a, salida=salida, salida_existe=False
        )
        custodia_ok = posteriores.permite_medir
        fallos_posteriores = posteriores.fallos
    except Exception as exc:
        custodia_ok = False
        fallos_posteriores = (f"reverificacion de custodia fallo: {exc}",)

    controles = evaluar_controles_desde_resultados(
        resultados,
        captura_inicial=captura_inicial,
        captura_final=captura_final,
        custodia_ok=custodia_ok,
    )
    evaluacion = fp.evaluar_controles(controles)
    if not evaluacion.valido:
        detalle = tuple(f"control bloqueante fallido: {c}" for c in evaluacion.fallos)
        if not custodia_ok:
            detalle += tuple(f"custodia tras medir: {f}" for f in fallos_posteriores)
        return CODIGO_BLOQUEADO, detalle

    try:
        documento = construir_documento(
            sha_a=sha_a,
            head=dependencias.entorno_custodia.head(),
            blobs_preinscritos=precondiciones.blobs_preinscritos,
            blob_arnes=precondiciones.blob_arnes,
            resultados=resultados,
            captura_inicial=captura_inicial,
            captura_final=captura_final,
            controles=controles,
            linea_base=dependencias.cargar_linea_base(),
        )
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"construccion del documento fallo: {exc}",)

    fallos_documento = esquema.fallos_suelo_medicion(documento)
    if fallos_documento:
        return CODIGO_BLOQUEADO, tuple(f"documento invalido: {f}" for f in fallos_documento)

    # La escritura se separa de la relectura para que el borrado de limpieza
    # solo pueda alcanzar un fichero que ESTA corrida haya creado. Si
    # ``os.link`` rehusa porque la ruta aparecio durante la medicion, el
    # fichero ajeno queda INTACTO: se bloquea sin destruir nada.
    try:
        escribir_json_atomico(salida, documento)
    except FileExistsError:
        return CODIGO_BLOQUEADO, (
            f"la ruta de salida aparecio durante la medicion y no se sobrescribe: {salida}",
        )
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"escritura del artefacto fallo: {exc}",)

    # Desde aqui el fichero de salida lo creo esta corrida: solo ahora es
    # legitimo eliminarlo si la revalidacion no lo respalda. El borrado se
    # VERIFICA: si el artefacto sobrevive, no se puede seguir afirmando que
    # no se publico nada.
    def _retirar(motivos: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
        try:
            _eliminar_o_denunciar(salida, "artefacto invalido")
        except ResiduoNoEliminableError as exc:
            return CODIGO_BLOQUEADO, (*motivos, f"ATENCION: {exc}")
        return CODIGO_BLOQUEADO, motivos

    try:
        releido = json.loads(salida.read_text(encoding="utf-8"))
    except Exception as exc:
        return _retirar((f"relectura del artefacto fallo: {exc}",))

    fallos_relectura = esquema.fallos_suelo_medicion(releido)
    if fallos_relectura:
        return _retirar(tuple(f"revalidacion tras escritura fallo: {f}" for f in fallos_relectura))

    return CODIGO_OK, ()


# --------------------------------------------------------------------------
# Interfaz de linea de ordenes
# --------------------------------------------------------------------------


def construir_parser() -> argparse.ArgumentParser:
    """Parser sin efectos secundarios."""
    parser = argparse.ArgumentParser(
        prog="run_floor",
        description=(
            "Corrida del suelo de medicion LAB-LINUX para ADR002-TOL-209. "
            "Sin --execute no mide nada."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="autoriza expresamente la medicion real (fase D)",
    )
    parser.add_argument(
        "--preinscription-commit",
        dest="preinscription_commit",
        default=None,
        help="SHA del commit A de preinscripcion",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="ruta del artefacto de evidencia a producir",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="imprime el plan declarado de la corrida sin medir",
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help=argparse.SUPPRESS,  # uso interno del ejecutor de la fase D
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    dependencias: DependenciasCorrida | None = None,
) -> int:
    """Punto de entrada. Sin ``--execute`` nunca mide."""
    args = construir_parser().parse_args(argv)

    if args.plan and not args.execute:
        plan = plan_de_corrida()
        print(f"procesos minimos: {plan.procesos}")
        print(f"sondas normativas (F): {list(plan.sondas_normativas)}")
        print(f"diagnosticos (fuera de F): {list(plan.diagnosticos)}")
        print(f"n por sonda de F: {plan.n_por_sonda} · warm-up {plan.warmup_por_sonda}")
        print(f"n de la sonda de reloj: {plan.n_reloj} · warm-up {plan.warmup_reloj}")
        print(f"rondas round-robin: {fp.RONDAS_ROUND_ROBIN}")
        print(f"U = {fp.FACTOR_U} * B · m = {fp.MARGEN_M}")
        return CODIGO_OK

    if not args.execute:
        print(
            "run_floor no mide sin --execute. La medicion es la fase D y "
            "requiere autorizacion expresa e independiente."
        )
        return CODIGO_SIN_EXECUTE

    if args.worker:
        print(json.dumps(ejecutar_sondas_worker(), ensure_ascii=False))
        return CODIGO_OK

    if not args.preinscription_commit or not args.output:
        print("--execute exige ademas --preinscription-commit y --output")
        return CODIGO_BLOQUEADO

    deps = dependencias_reales() if dependencias is None else dependencias
    codigo, fallos = ejecutar_corrida(
        sha_a=args.preinscription_commit,
        salida=Path(args.output),
        dependencias=deps,
    )
    if codigo != CODIGO_OK:
        print("corrida bloqueada; no se ha publicado ningun valor:")
        for fallo in fallos:
            print(f"  - {fallo}")
        return codigo

    print(f"artefacto escrito y revalidado: {args.output}")
    print("ADR002-TOL-209 sigue NO SATISFECHA hasta el acta correspondiente.")
    return CODIGO_OK


if __name__ == "__main__":
    raise SystemExit(main())
