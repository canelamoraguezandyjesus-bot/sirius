"""Orquestador de la corrida del suelo multiescala (ADR002-TOL-209, sucesor).

El commit de preinscripcion congela este codigo SIN ejecutarlo. La corrida
—autorizada de forma expresa e independiente— ejecuta exactamente este
codigo, sin modificarlo, mediante:

    uv run python -m experiments.adr002.tolerances.run_floor_scale \\
        --execute \\
        --preinscription-commit <SHA> \\
        --output artifacts/adr002_tolerances/suelo_medicion_v0.2.json

Garantias de este modulo:

- **No mide nada al importarse** y **no mide nada sin ``--execute``**.
- Antes de abrir una sola ventana cronometrada comprueba, fallando cerrado:
  arbol de trabajo limpio, HEAD exactamente igual al commit de
  preinscripcion, existencia de ese commit, coincidencia de los seis blobs
  preinscritos con el arbol y con el commit, modulo heredado intacto,
  protocolo aprobado intacto, blobs del corpus congelado intactos,
  **evidencia del metodo anterior intacta byte a byte** y ruta de salida
  inexistente.
- El recorrido completo es: precondiciones -> captura inicial ->
  calibracion UNICA en el padre -> lanzamiento de procesos independientes
  con la misma cantidad de trabajo -> sondas en round-robin sobre
  (familia, escala) -> controles internos -> punto fijo (SM, D(s), U, B) ->
  documento -> validacion con ``schema_floor_scale_v0_1`` -> escritura
  atomica -> relectura y revalidacion.
- Si CUALQUIER control bloqueante falla, no se escribe ningun artefacto y no
  se publica ningun valor.
- La evidencia del metodo anterior no se toca: se verifica y se cita.

Las dependencias externas (custodia Git, calibracion, ejecutor de procesos,
captura de entorno, carga de la linea base) son inyectables, de modo que las
pruebas recorren este mismo camino con dobles controlados y sin ejecutar la
medicion real.
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

from experiments.adr002.tolerances import floor_scale_probes as sondas
from experiments.adr002.tolerances import floor_scale_protocol as fp
from experiments.adr002.tolerances import schema_floor_scale_v0_1 as esquema

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

CODIGO_OK: Final = 0
CODIGO_BLOQUEADO: Final = 2
CODIGO_SIN_EXECUTE: Final = 3

CLAVES_RESULTADO_PROCESO: Final[tuple[str, ...]] = (
    "pid",
    "escalas",
    "unitarias",
    "referencia",
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

        Fuente de verdad independiente del arbol de trabajo: es lo que hace
        que la comparacion de custodia no sea tautologica.
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
    blobs_heredados: Mapping[str, str]
    evidencia_anterior_intacta: bool

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

    blobs_heredados: dict[str, str] = {}
    for ruta in fp.ARCHIVOS_HEREDADOS:
        try:
            blobs_heredados[ruta] = fp.blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"modulo heredado ilegible: {ruta}")

    try:
        ruta_protocolo = f"docs/architecture/{fp.PROTOCOLO}"
        if fp.blob_git(entorno.leer_bytes(ruta_protocolo)) != fp.BLOB_PROTOCOLO_APROBADO:
            fallos.append("el protocolo aprobado ha sido modificado")
    except OSError:
        fallos.append("protocolo aprobado ilegible")

    fallos_anteriores = fp.fallos_evidencia_anterior(entorno)
    fallos.extend(fallos_anteriores)

    if blobs_preinscritos and blobs_heredados:
        fallos.extend(
            fp.verificar_custodia(
                entorno,
                sha_a=sha_a,
                blobs_preinscritos=blobs_preinscritos,
                blobs_heredados=blobs_heredados,
            )
        )

    return Precondiciones(
        fallos=tuple(dict.fromkeys(fallos)),
        blobs_preinscritos=blobs_preinscritos,
        blobs_heredados=blobs_heredados,
        evidencia_anterior_intacta=not fallos_anteriores,
    )


# --------------------------------------------------------------------------
# Plan de la corrida
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlanCorrida:
    """Plan declarado de la corrida. Ninguna observacion normativa aqui.

    ``unidades`` proviene de la calibracion UNICA del padre y es identico
    para todos los procesos: sin eso las ejecuciones no serian equivalentes
    y TOL-107 no tendria sobre que operar.
    """

    procesos: int
    rondas: int
    escalera_ns: tuple[int, ...]
    familias: tuple[str, ...]
    warmup_por_escala: int
    n_unitaria: int
    warmup_unitaria: int
    semilla: int
    orden: tuple[tuple[str, int], ...]
    unidades: Mapping[str, Mapping[int, int]]


def plan_de_corrida(unidades: Mapping[str, Mapping[int, int]]) -> PlanCorrida:
    """Construye el plan declarado. Puro: no mide, no abre ficheros."""
    faltan = sorted(f for f in fp.FAMILIAS if f not in unidades)
    if faltan:
        msg = f"el plan de unidades no cubre las familias {faltan}"
        raise EjecucionBloqueadaError(msg)
    for familia in fp.FAMILIAS:
        ausentes = sorted(s for s in fp.ESCALERA_NS if s not in unidades[familia])
        if ausentes:
            msg = f"el plan de unidades de {familia} no cubre las escalas {ausentes}"
            raise EjecucionBloqueadaError(msg)
    return PlanCorrida(
        procesos=fp.PROCESOS_MINIMOS,
        rondas=fp.RONDAS_ROUND_ROBIN,
        escalera_ns=fp.ESCALERA_NS,
        familias=fp.FAMILIAS,
        warmup_por_escala=fp.WARMUP_ESCALA,
        n_unitaria=fp.N_UNITARIA,
        warmup_unitaria=fp.WARMUP_UNITARIA,
        semilla=fp.SEMILLA,
        orden=tuple(sondas.orden_round_robin(fp.pares_de_escalera(), fp.RONDAS_ROUND_ROBIN)),
        unidades={familia: dict(unidades[familia]) for familia in fp.FAMILIAS},
    )


def unidades_desde_json(crudo: Any) -> dict[str, dict[int, int]]:
    """Reconstruye el plan de unidades recibido por el hijo. Falla cerrado."""
    if not isinstance(crudo, Mapping):
        msg = "el plan de unidades debe ser un objeto"
        raise EjecucionBloqueadaError(msg)
    plan: dict[str, dict[int, int]] = {}
    for familia in fp.FAMILIAS:
        entrada = crudo.get(familia)
        if not isinstance(entrada, Mapping):
            msg = f"el plan de unidades no trae la familia {familia}"
            raise EjecucionBloqueadaError(msg)
        por_escala: dict[int, int] = {}
        for escala in fp.ESCALERA_NS:
            valor = entrada.get(str(escala))
            if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
                msg = f"unidades invalidas para {familia}@{escala} ns: {valor!r}"
                raise EjecucionBloqueadaError(msg)
            por_escala[escala] = valor
        plan[familia] = por_escala
    return plan


def unidades_a_json(unidades: Mapping[str, Mapping[int, int]]) -> dict[str, dict[str, int]]:
    """Serializa el plan de unidades con claves de escala como cadena."""
    return {
        familia: {str(escala): int(unidades[familia][escala]) for escala in fp.ESCALERA_NS}
        for familia in fp.FAMILIAS
    }


# --------------------------------------------------------------------------
# Calibracion: la hace el PADRE una sola vez
# --------------------------------------------------------------------------


def _base_de_corpus(prefijo: str) -> Path:
    from experiments.adr002.tolerances import corpus

    base = corpus.nueva_base_temporal(prefijo)
    corpus.construir_esquema(base)
    corpus.poblar(base)
    return base


def calibrar_real() -> dict[str, sondas.Calibracion]:
    """Mide el coste de la cantidad de referencia de cada familia.

    Se ejecuta UNA vez, en el proceso padre, antes de lanzar a los hijos. Su
    salida es el contrato de cantidad de trabajo por escala que todos los
    hijos reciben identico.
    """
    base = _base_de_corpus("adr002_cal_")
    fixture = sondas.preparar_fixture_canon(base)
    try:
        calibraciones = {
            fp.FAMILIA_CPU: sondas.calibrar_familia(
                sondas.operacion_cpu(fp.UNIDADES_REFERENCIA[fp.FAMILIA_CPU]),
                familia=fp.FAMILIA_CPU,
                unidades=fp.UNIDADES_REFERENCIA[fp.FAMILIA_CPU],
            ),
            fp.FAMILIA_CANON: sondas.calibrar_familia(
                sondas.operacion_canon(fixture, fp.UNIDADES_REFERENCIA[fp.FAMILIA_CANON]),
                familia=fp.FAMILIA_CANON,
                unidades=fp.UNIDADES_REFERENCIA[fp.FAMILIA_CANON],
            ),
        }
    finally:
        fixture.conexion.close()
    return calibraciones


# --------------------------------------------------------------------------
# Worker: medicion real dentro de UN proceso hijo
# --------------------------------------------------------------------------


def _resumen(muestras: Sequence[int], *, warmup: int) -> dict[str, Any]:
    ordenadas = sorted(int(v) for v in muestras)
    return {
        "n": len(ordenadas),
        "warmup_descartado": warmup,
        "muestras_ns": [int(v) for v in muestras],
        "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
        "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
        "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
        "min_ns": ordenadas[0],
        "max_ns": ordenadas[-1],
    }


def _carga_actual() -> float:
    return os.getloadavg()[0]


def ejecutar_sondas_worker(unidades: Mapping[str, Mapping[int, int]]) -> dict[str, Any]:
    """Recorrido de medicion de UN proceso. Solo lo invoca la corrida real.

    Prepara su propia base (fichero, motor, cache y warm-up propios, §3.3),
    ejecuta las sondas de escala en round-robin sobre (familia, escala)
    (§5.2 aplicado a sondas), mide las sondas unitarias que dan SM y el
    trabajo de referencia en tres puntos, y devuelve el resultado crudo. No
    escribe ningun artefacto: el padre agrega, valida y publica.
    """
    incidencias: list[str] = []
    cargas: list[float] = [_carga_actual()]

    base = _base_de_corpus("adr002_suelo_")
    fixture = sondas.preparar_fixture_canon(base)

    referencia_inicio = fp.p50_ns(sondas.diagnostico_referencia())

    operaciones: dict[tuple[str, int], Callable[[], Any]] = {}
    for familia in fp.FAMILIAS:
        for escala in fp.ESCALERA_NS:
            cantidad = unidades[familia][escala]
            operaciones[familia, escala] = (
                sondas.operacion_cpu(cantidad)
                if familia == fp.FAMILIA_CPU
                else sondas.operacion_canon(fixture, cantidad)
            )

    # Warm-up declarado, una vez por (familia, escala), descartado integro.
    for operacion in operaciones.values():
        for _ in range(fp.WARMUP_ESCALA):
            operacion()

    pares = fp.pares_de_escalera()
    vectores: dict[tuple[str, int], list[int]] = {par: [] for par in pares}
    rondas = fp.RONDAS_ROUND_ROBIN
    referencia_mitad = 0
    for ronda in range(rondas):
        for familia, escala in pares:
            tramo = fp.n_para_escala(escala) // rondas
            vectores[familia, escala].extend(
                sondas.medir_ns(operaciones[familia, escala], n=tramo, warmup=0)
            )
        if ronda == rondas // 2 - 1:
            referencia_mitad = fp.p50_ns(sondas.diagnostico_referencia())
            cargas.append(_carga_actual())

    referencia_final = fp.p50_ns(sondas.diagnostico_referencia())

    # Sondas unitarias: dan SM. Fuera de la escalera, despues de ella para no
    # interferir con las ventanas largas.
    unitarias: dict[str, dict[str, Any]] = {
        fp.SONDA_VACIA: _resumen(sondas.sonda_vacia(), warmup=fp.WARMUP_UNITARIA),
        fp.SONDA_CANON_0: _resumen(
            sondas.sonda_canon_unitaria(fixture, filas_esperadas=0), warmup=fp.WARMUP_UNITARIA
        ),
        fp.SONDA_CANON_1: _resumen(
            sondas.sonda_canon_unitaria(fixture, filas_esperadas=1), warmup=fp.WARMUP_UNITARIA
        ),
    }
    cargas.append(_carga_actual())

    # Verificacion de forma de la familia canon, fuera del cronometro.
    # Registrar la incidencia NO basta: el padre trata cualquier incidencia
    # como bloqueante, y el esquema impide publicar B y U con incidencias.
    conexion = fixture.conexion
    if len(conexion.execute(sondas.SQL_SONDA_CANON, (fixture.clave_inexistente,)).fetchall()) != 0:
        incidencias.append("canon_0_filas devolvio filas")
    if len(conexion.execute(sondas.SQL_SONDA_CANON, (fixture.clave_existente,)).fetchall()) != 1:
        incidencias.append("canon_1_fila no devolvio exactamente una fila")
    conexion.close()

    escalas: dict[str, dict[str, Any]] = {familia: {} for familia in fp.FAMILIAS}
    for familia, escala in pares:
        entrada = _resumen(vectores[familia, escala], warmup=fp.WARMUP_ESCALA)
        entrada["unidades"] = unidades[familia][escala]
        escalas[familia][str(escala)] = entrada

    return {
        "pid": sondas.pid_actual(),
        "escalas": escalas,
        "unitarias": unitarias,
        "referencia": {
            "vueltas": fp.VUELTAS_REFERENCIA,
            "p50_inicio_ns": referencia_inicio,
            "p50_mitad_ns": referencia_mitad,
            "p50_final_ns": referencia_final,
        },
        "unidades": unidades_a_json(unidades),
        "cargas": cargas,
        "incidencias": incidencias,
        "filtrado_aplicado": False,
        "warmup_mezclado": False,
    }


def ejecutor_procesos_reales(plan: PlanCorrida) -> list[Mapping[str, Any]]:
    """Lanza ``plan.procesos`` procesos del sistema operativo, secuenciales.

    Cada hijo ejecuta ``--worker`` con el MISMO plan de unidades y devuelve
    su resultado por stdout en JSON. Las pruebas inyectan otro ejecutor.
    """
    resultados: list[Mapping[str, Any]] = []
    unidades = json.dumps(unidades_a_json(plan.unidades), separators=(",", ":"))
    orden = [
        sys.executable,
        "-m",
        "experiments.adr002.tolerances.run_floor_scale",
        "--execute",
        "--worker",
        "--units",
        unidades,
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

    with tempfile.TemporaryDirectory(prefix="adr002_suelo_env_") as temporal:
        captura = capturar_entorno(RAIZ_REPOSITORIO, Path(temporal))
    return {
        "etapa": etapa,
        "boot_id": captura.get("boot_id"),
        "carga": _carga_actual(),
        "captura": captura,
    }


def cargar_linea_base_real() -> Mapping[str, Any]:
    """Evidencia versionada de la linea base, solo para clasificacion."""
    ruta = RAIZ_REPOSITORIO / fp.RUTA_LINEA_BASE
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        msg = f"{fp.RUTA_LINEA_BASE} no contiene un objeto JSON"
        raise EjecucionBloqueadaError(msg)
    return datos


def _ms_a_ns(valor: Any) -> int:
    return round(float(valor) * 1_000_000)


def clasificar_linea_base(
    linea_base: Mapping[str, Any], *, sm: int, punto: fp.PuntoFijo
) -> list[dict[str, Any]]:
    """Clasificacion DIAGNOSTICA de las magnitudes historicas publicadas.

    Nunca modifica B ni U: solo informa en que regimen caeria cada magnitud
    de la linea base con los valores derivados del suelo. Si no reproduce la
    particion historica, eso se explica en el informe, no se corrige a
    posteriori.

    Si el punto fijo no se resolvio, ninguna magnitud se clasifica: se
    declara ``NO_EVALUABLE`` con el motivo, sin inventar umbral.
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
            entrada: dict[str, Any] = {
                "magnitud": f"{escenario}.{capa}",
                "fuente": fp.RUTA_LINEA_BASE,
                "min_p50_ns": min(p50s),
                "max_p50_ns": max(p50s),
                "min_p95_ns": min(p95s),
                "max_p95_ns": max(p95s),
            }
            if punto.u is None or punto.b is None:
                entrada["resultado"] = fp.NO_EVALUABLE
                entrada["motivo"] = "umbral_no_resuelto"
                entrada["registro"] = fp.NO_EVALUABLE
                entradas.append(entrada)
                continue
            veredicto = fp.evaluar_magnitud(p50s, p95s, sm=sm, b=punto.b, u=punto.u)
            entrada["registro"] = fp.registro_por_percentil(veredicto)
            if veredicto.dominada_por_instrumento:
                entrada["resultado"] = fp.NO_EVALUABLE
                entrada["motivo"] = "dominada_por_instrumento"
            else:
                regimenes = {v.percentil: v.regimen for v in veredicto.por_percentil}
                entrada["resultado"] = veredicto.resultado
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
    escalas = resultado["escalas"]
    if not isinstance(escalas, Mapping):
        return [f"resultado[{indice}]: escalas debe ser un mapa"]
    for familia in fp.FAMILIAS:
        por_familia = escalas.get(familia)
        if not isinstance(por_familia, Mapping):
            fallos.append(f"resultado[{indice}]: falta la familia {familia}")
            continue
        for escala in fp.ESCALERA_NS:
            if str(escala) not in por_familia:
                fallos.append(f"resultado[{indice}]: falta {familia}@{escala} ns")
    unitarias = resultado["unitarias"]
    if not isinstance(unitarias, Mapping):
        fallos.append(f"resultado[{indice}]: unitarias debe ser un mapa")
    else:
        for sonda in fp.SONDAS_UNITARIAS:
            if sonda not in unitarias:
                fallos.append(f"resultado[{indice}]: falta la sonda unitaria {sonda}")
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


def _entradas_medidas(resultado: Mapping[str, Any]) -> list[tuple[str, int, Mapping[str, Any]]]:
    """``(familia, escala, entrada)`` de un resultado, solo las bien formadas."""
    salida: list[tuple[str, int, Mapping[str, Any]]] = []
    escalas = resultado.get("escalas")
    if not isinstance(escalas, Mapping):
        return salida
    for familia in fp.FAMILIAS:
        por_familia = escalas.get(familia)
        if not isinstance(por_familia, Mapping):
            continue
        for escala in fp.ESCALERA_NS:
            entrada = por_familia.get(str(escala))
            if isinstance(entrada, Mapping):
                salida.append((familia, escala, entrada))
    return salida


def _controles_de_vectores(resultados: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    """Controles que se recomputan vector a vector desde los datos crudos."""
    vectores_ok = True
    sin_negativas = True
    sin_redondeo = True
    warmup_ok = True
    sin_filtrado = True
    escalera_ok = True

    for resultado in resultados:
        if resultado.get("filtrado_aplicado") is not False:
            sin_filtrado = False
        if resultado.get("warmup_mezclado") is not False:
            warmup_ok = False

        entradas = _entradas_medidas(resultado)
        if len(entradas) != len(fp.FAMILIAS) * len(fp.ESCALERA_NS):
            escalera_ok = False
        for _familia, escala, entrada in entradas:
            vector = _vector_entero(entrada.get("muestras_ns"))
            esperado = fp.n_para_escala(escala)
            if vector is None or len(vector) != esperado:
                vectores_ok = False
                continue
            if any(v < 0 for v in vector):
                sin_negativas = False
            if _parece_redondeado(vector):
                sin_redondeo = False
            warmup = entrada.get("warmup_descartado")
            if (
                not isinstance(warmup, int)
                or isinstance(warmup, bool)
                or warmup != fp.WARMUP_ESCALA
            ):
                warmup_ok = False

        unitarias = resultado.get("unitarias")
        if not isinstance(unitarias, Mapping):
            vectores_ok = False
        else:
            for sonda in fp.SONDAS_UNITARIAS:
                entrada_unitaria = unitarias.get(sonda)
                if not isinstance(entrada_unitaria, Mapping):
                    vectores_ok = False
                    continue
                vector = _vector_entero(entrada_unitaria.get("muestras_ns"))
                if vector is None or len(vector) != fp.N_UNITARIA:
                    vectores_ok = False
                    continue
                if any(v < 0 for v in vector):
                    sin_negativas = False
                if _parece_redondeado(vector):
                    sin_redondeo = False
                warmup = entrada_unitaria.get("warmup_descartado")
                if (
                    not isinstance(warmup, int)
                    or isinstance(warmup, bool)
                    or warmup != fp.WARMUP_UNITARIA
                ):
                    warmup_ok = False

        incidencias = resultado.get("incidencias")
        if not isinstance(incidencias, Sequence) or isinstance(incidencias, str | bytes):
            vectores_ok = False
        elif incidencias:
            sin_filtrado = False

    return {
        "escalera_completa": escalera_ok,
        "vectores_crudos_completos": vectores_ok,
        "sin_muestras_negativas": sin_negativas,
        "sin_redondeo_previo": sin_redondeo,
        "warmup_separado": warmup_ok,
        "sin_filtrado": sin_filtrado,
    }


def _unidades_identicas(resultados: Sequence[Mapping[str, Any]], plan: PlanCorrida) -> bool:
    """Todos los procesos deben haber resuelto la MISMA cantidad de trabajo.

    Se cruzan dos fuentes por proceso: el plan que declara haber recibido y
    las unidades que publica en cada entrada medida. Ambas deben coincidir
    con el plan del padre; si no, las ejecuciones no son equivalentes.
    """
    esperado = unidades_a_json(plan.unidades)
    for resultado in resultados:
        if resultado.get("unidades") != esperado:
            return False
        entradas = _entradas_medidas(resultado)
        if len(entradas) != len(fp.FAMILIAS) * len(fp.ESCALERA_NS):
            return False
        for familia, escala, entrada in entradas:
            if entrada.get("unidades") != plan.unidades[familia][escala]:
                return False
    return True


def _calibracion_en_banda(resultados: Sequence[Mapping[str, Any]]) -> bool:
    """El P50 observado de cada (familia, escala, proceso) debe caer en [s/2, 2s]."""
    for resultado in resultados:
        for _familia, escala, entrada in _entradas_medidas(resultado):
            p50 = entrada.get("p50_ns")
            if not isinstance(p50, int) or isinstance(p50, bool):
                return False
            if not fp.calibracion_en_banda(p50, escala):
                return False
    return True


def progresion_por_proceso(resultado: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Tabla de progresion entre escalas consecutivas, exigible o no."""
    filas: list[dict[str, Any]] = []
    escalas = resultado.get("escalas")
    if not isinstance(escalas, Mapping):
        return filas
    for familia in fp.FAMILIAS:
        por_familia = escalas.get(familia)
        if not isinstance(por_familia, Mapping):
            continue
        for menor, mayor in zip(fp.ESCALERA_NS, fp.ESCALERA_NS[1:], strict=False):
            entrada_menor = por_familia.get(str(menor))
            entrada_mayor = por_familia.get(str(mayor))
            if not isinstance(entrada_menor, Mapping) or not isinstance(entrada_mayor, Mapping):
                continue
            p50_menor, p50_mayor = entrada_menor.get("p50_ns"), entrada_mayor.get("p50_ns")
            u_menor, u_mayor = entrada_menor.get("unidades"), entrada_mayor.get("unidades")
            if not all(
                isinstance(v, int) and not isinstance(v, bool)
                for v in (p50_menor, p50_mayor, u_menor, u_mayor)
            ):
                continue
            assert isinstance(p50_menor, int)
            assert isinstance(p50_mayor, int)
            assert isinstance(u_menor, int)
            assert isinstance(u_mayor, int)
            exigible = fp.progresion_exigible(u_menor, u_mayor)
            filas.append(
                {
                    "familia": familia,
                    "escala_menor_ns": menor,
                    "escala_mayor_ns": mayor,
                    "unidades_menor": u_menor,
                    "unidades_mayor": u_mayor,
                    "p50_menor_ns": p50_menor,
                    "p50_mayor_ns": p50_mayor,
                    "exigible": exigible,
                    "progresa": fp.escala_progresa(p50_menor, menor, p50_mayor, mayor),
                }
            )
    return filas


def _progresion_ok(resultados: Sequence[Mapping[str, Any]]) -> bool:
    for resultado in resultados:
        for fila in progresion_por_proceso(resultado):
            if fila["exigible"] and not fila["progresa"]:
                return False
    return True


def _estabilidad_ok(resultados: Sequence[Mapping[str, Any]]) -> bool:
    for resultado in resultados:
        referencia = resultado.get("referencia")
        if not isinstance(referencia, Mapping):
            return False
        valores: list[int] = []
        for clave in ("p50_inicio_ns", "p50_mitad_ns", "p50_final_ns"):
            valor = referencia.get(clave)
            if not isinstance(valor, int) or isinstance(valor, bool):
                return False
            valores.append(valor)
        if not fp.referencia_estable(valores[0], valores[1], valores[2]):
            return False
    return True


def evaluar_controles_desde_resultados(
    resultados: Sequence[Mapping[str, Any]],
    *,
    plan: PlanCorrida,
    captura_inicial: Mapping[str, Any],
    captura_final: Mapping[str, Any],
    custodia_ok: bool,
    evidencia_anterior_intacta: bool,
    punto: fp.PuntoFijo,
) -> dict[str, bool]:
    """Deriva el estado de los controles bloqueantes desde los datos.

    Todo se recomputa desde los datos crudos: los flags que declara cada
    proceso se cruzan, nunca se aceptan como unica fuente.
    """
    pids = [r.get("pid") for r in resultados]
    pids_validos = all(isinstance(p, int) and not isinstance(p, bool) and p > 0 for p in pids)

    cargas_ok = all(
        isinstance(r.get("cargas"), Sequence)
        and not isinstance(r.get("cargas"), str | bytes)
        and len(r["cargas"]) > 0
        for r in resultados
    ) and all("carga" in captura for captura in (captura_inicial, captura_final))

    boot_inicial = captura_inicial.get("boot_id")
    boot_final = captura_final.get("boot_id")

    nombres = [*fp.FAMILIAS, *fp.SONDAS_UNITARIAS]

    controles: dict[str, bool] = {
        "procesos_independientes": len(resultados) >= fp.PROCESOS_MINIMOS,
        "pids_distintos": pids_validos and len(set(pids)) == len(pids),
        "unidades_identicas": _unidades_identicas(resultados, plan),
        "calibracion_en_banda": _calibracion_en_banda(resultados),
        "carga_registrada": cargas_ok,
        "boot_id_estable": bool(boot_inicial) and boot_inicial == boot_final,
        "captura_ambiental_presente": bool(boot_inicial) and bool(boot_final),
        "estabilidad_intraproceso": _estabilidad_ok(resultados),
        "progresion_por_escala": _progresion_ok(resultados),
        "banda_cubre_el_suelo": fp.banda_cubre_el_suelo(punto),
        "sondas_neutrales": not fp.comprobar_neutralidad(nombres)
        and not sondas.fallos_sql_de_sonda(sondas.SQL_SONDA_CANON),
        "evidencia_anterior_intacta": evidencia_anterior_intacta,
        "custodia_verificada": custodia_ok,
    }
    controles.update(_controles_de_vectores(resultados))
    return controles


# --------------------------------------------------------------------------
# Construccion del documento
# --------------------------------------------------------------------------


def _entrada_publicada(vector: Sequence[int], *, warmup: int) -> dict[str, Any]:
    ordenadas = sorted(int(v) for v in vector)
    distintos = len(set(ordenadas))
    repeticion_maxima = max(ordenadas.count(v) for v in set(ordenadas)) if ordenadas else 0
    return {
        "n": len(ordenadas),
        "warmup_descartado": warmup,
        "muestras_ns": [int(v) for v in vector],
        "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
        "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
        "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
        "min_ns": ordenadas[0],
        "max_ns": ordenadas[-1],
        "media_truncada_ns": sum(ordenadas) // len(ordenadas),
        "resolucion_percentil": fp.resolucion_percentil(len(ordenadas)),
        # Diagnostico de forma del vector, no umbral automatico: permite a un
        # auditor distinguir un suelo cuantizado (muchos repetidos por
        # resolucion del reloj) de un vector recortado y repadeado. No se
        # convierte en control bloqueante porque ambos casos son
        # indistinguibles sin evidencia adicional (limitacion declarada).
        "valores_distintos": distintos,
        "repeticion_maxima": repeticion_maxima,
    }


def medidas_desde_resultados(
    resultados: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[fp.MedidaEscala]]:
    """Entradas publicables y medidas tipadas de la escalera."""
    entradas: list[dict[str, Any]] = []
    medidas: list[fp.MedidaEscala] = []
    for resultado in resultados:
        pid = int(resultado["pid"])
        for familia, escala, cruda in _entradas_medidas(resultado):
            publicada = _entrada_publicada(
                cruda["muestras_ns"], warmup=int(cruda["warmup_descartado"])
            )
            publicada["familia"] = familia
            publicada["escala_ns"] = escala
            publicada["unidades"] = int(cruda["unidades"])
            publicada["pid"] = pid
            entradas.append(publicada)
            medidas.append(
                fp.MedidaEscala(
                    familia=familia,
                    escala_ns=escala,
                    unidades=int(publicada["unidades"]),
                    pid=pid,
                    n=int(publicada["n"]),
                    warmup_descartado=int(publicada["warmup_descartado"]),
                    p50=int(publicada["p50_ns"]),
                    p95=int(publicada["p95_ns"]),
                    p99=int(publicada["p99_ns"]),
                    minimo=int(publicada["min_ns"]),
                    maximo=int(publicada["max_ns"]),
                    media_truncada=int(publicada["media_truncada_ns"]),
                )
            )
    return entradas, medidas


def unitarias_desde_resultados(
    resultados: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[fp.MedidaUnitaria]]:
    """Entradas publicables y medidas tipadas de las sondas unitarias."""
    entradas: list[dict[str, Any]] = []
    medidas: list[fp.MedidaUnitaria] = []
    for resultado in resultados:
        pid = int(resultado["pid"])
        unitarias = resultado["unitarias"]
        for sonda in fp.SONDAS_UNITARIAS:
            cruda = unitarias[sonda]
            publicada = _entrada_publicada(
                cruda["muestras_ns"], warmup=int(cruda["warmup_descartado"])
            )
            publicada["sonda"] = sonda
            publicada["pid"] = pid
            entradas.append(publicada)
            medidas.append(
                fp.MedidaUnitaria(
                    sonda=sonda,
                    pid=pid,
                    n=int(publicada["n"]),
                    warmup_descartado=int(publicada["warmup_descartado"]),
                    p50=int(publicada["p50_ns"]),
                    p95=int(publicada["p95_ns"]),
                    p99=int(publicada["p99_ns"]),
                    minimo=int(publicada["min_ns"]),
                    maximo=int(publicada["max_ns"]),
                    media_truncada=int(publicada["media_truncada_ns"]),
                )
            )
    return entradas, medidas


def detalle_por_escala(medidas: Sequence[fp.MedidaEscala]) -> list[dict[str, Any]]:
    """Descomposicion de ``D(s)`` por familia y percentil. Auditable a mano."""
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


def contraste_metodo_anterior(punto: fp.PuntoFijo) -> dict[str, Any]:
    """Contraste explicito con la evidencia del paquete 05, que se conserva.

    Diagnostico, nunca normativo: documenta por que el sucesor existe sin
    tocar ni un byte del artefacto anterior.
    """
    return {
        "evidencia_anterior": dict(fp.BLOBS_EVIDENCIA_ANTERIOR),
        "metodo_anterior": (
            "D medida en una sola escala (~21 us) y U = B / 0,20; supone D constante"
        ),
        "metodo_sucesor": (
            "D(s) medida en trece escalas y punto fijo D(U) <= U / 5; no supone nada sobre D"
        ),
        "u_anterior_ns": fp.U_ANTERIOR_NS,
        "b_anterior_ns": fp.B_ANTERIOR_NS,
        "u_sucesora_ns": punto.u,
        "b_sucesora_ns": punto.b,
        "por_que_cambia": (
            "la razon D(s)/s no es constante: decrece de forma monotona al crecer la escala, "
            "de modo que resolver el umbral en la escala mas barata lo subestima"
        ),
        "que_no_cambia": (
            "objetivo relativo 20 %, m = 1, B = U / 5, percentiles por rango mas cercano, "
            "cinco procesos independientes y la evidencia del paquete 05"
        ),
    }


def construir_documento(
    *,
    sha_a: str,
    head: str,
    plan: PlanCorrida,
    calibracion: Mapping[str, Any],
    blobs_preinscritos: Mapping[str, str],
    blobs_heredados: Mapping[str, str],
    resultados: Sequence[Mapping[str, Any]],
    captura_inicial: Mapping[str, Any],
    captura_final: Mapping[str, Any],
    controles: Mapping[str, bool],
    punto: fp.PuntoFijo,
    sm: int,
    linea_base: Mapping[str, Any],
) -> dict[str, Any]:
    """Construye el artefacto completo exigido por ``schema_floor_scale_v0_1``."""
    entradas_escalas, medidas = medidas_desde_resultados(resultados)
    entradas_unitarias, _ = unitarias_desde_resultados(resultados)

    clasificacion = clasificar_linea_base(linea_base, sm=sm, punto=punto)

    incidencias: list[str] = []
    for resultado in resultados:
        incidencias.extend(str(i) for i in resultado.get("incidencias", []))

    dispersiones = [
        {
            "escala_ns": escala,
            "dispersion_ns": dispersion,
            "razon_por_mil": fp.razon_por_mil(dispersion, escala),
            "sostenible": fp.sostenible_en_escala(dispersion, escala),
        }
        for escala, dispersion in punto.dispersiones
    ]

    derivacion: dict[str, Any] = {
        "resultado": fp.NO_EVALUABLE if not punto.evaluable else "RESUELTO",
        "sm_ns": sm,
        "u_ns": punto.u,
        "b_ns": punto.b,
        "m": punto.m,
        "objetivo_relativo": f"{fp.OBJETIVO_RELATIVO_NUM}/{fp.OBJETIVO_RELATIVO_DEN}",
        "factor_u": fp.FACTOR_U,
        "dispersiones": dispersiones,
        "detalle_por_escala": detalle_por_escala(medidas),
        "motivo_no_evaluable": punto.motivo_no_evaluable,
    }

    return {
        "documento": "Suelo multiescala LAB-LINUX para ADR002-TOL-209",
        "version_esquema": fp.VERSION_ESQUEMA,
        "estado": fp.ESTADO_EVIDENCIA,
        "protocolo": fp.PROTOCOLO,
        "paquete": fp.PAQUETE,
        "metodo": {
            "nombre": "punto fijo multiescala",
            "criterio": "U = menor escala medida con 5 * D(s) <= s para ella y todas las mayores",
            "banda": "B = U / 5, exacta en enteros",
            "escalera_ns": list(fp.ESCALERA_NS),
            "familias": list(fp.FAMILIAS),
            "dispersion": "D(s) = peor (max - min) entre procesos, sobre familias y P50/P95",
            "sustituye_metodo_de": fp.EVIDENCIA_ANTERIOR,
            "no_sustituye_evidencia": True,
        },
        "plan": {
            "procesos": plan.procesos,
            "rondas": plan.rondas,
            "escalera_ns": list(plan.escalera_ns),
            "familias": list(plan.familias),
            "n_por_escala": {str(s): fp.n_para_escala(s) for s in fp.ESCALERA_NS},
            "warmup_por_escala": plan.warmup_por_escala,
            "n_unitaria": plan.n_unitaria,
            "warmup_unitaria": plan.warmup_unitaria,
            "semilla": plan.semilla,
            "orden": [[familia, escala] for familia, escala in plan.orden],
            "unidades": unidades_a_json(plan.unidades),
        },
        "calibracion": dict(calibracion),
        "preinscripcion": {
            "commit_a": sha_a,
            "head_en_ejecucion": head,
            "blobs_preinscritos": dict(blobs_preinscritos),
            "blobs_heredados": dict(blobs_heredados),
            "blobs_corpus_congelado": dict(fp.BLOBS_CORPUS_CONGELADO),
            "blob_protocolo": fp.BLOB_PROTOCOLO_APROBADO,
            "blobs_evidencia_anterior": dict(fp.BLOBS_EVIDENCIA_ANTERIOR),
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
        "escalas": entradas_escalas,
        "sondas_unitarias": entradas_unitarias,
        "diagnosticos": {
            fp.DIAG_REFERENCIA: {
                "por_proceso": [dict(resultado["referencia"]) for resultado in resultados]
            },
            fp.DIAG_PROGRESION: {
                "por_proceso": [
                    {"pid": int(resultado["pid"]), "filas": progresion_por_proceso(resultado)}
                    for resultado in resultados
                ],
                "nota": (
                    "solo se exige donde ambas escalas usan al menos "
                    f"{fp.UNIDADES_MINIMAS_PROGRESION} unidades de trabajo"
                ),
            },
            fp.DIAG_CURVA: {
                "razon_por_mil": [
                    {"escala_ns": escala, "razon_por_mil": fp.razon_por_mil(dispersion, escala)}
                    for escala, dispersion in punto.dispersiones
                ],
                "nota": "curva D(s)/s; su decrecimiento es la razon de existir del sucesor",
            },
        },
        "controles_internos": dict(controles),
        "derivacion": derivacion,
        "regimenes_por_percentil": clasificacion,
        "clasificacion_diagnostica_linea_base": {
            "fuente": fp.RUTA_LINEA_BASE,
            "nota": (
                "clasificacion diagnostica: nunca modifica B ni U; una particion distinta "
                "de la historica se explica, no se corrige"
            ),
            "magnitudes": clasificacion,
        },
        "contraste_metodo_anterior": contraste_metodo_anterior(punto),
        "custodia": {
            "sha_a_es_ancestro": True,
            "diff_preinscritos_vacio": True,
            "reverificada_tras_medir": True,
            "evidencia_anterior_intacta": True,
            "head": head,
        },
        "no_autoriza": {
            "limite_duro_tol_107": False,
            "aprobacion_tol_209": False,
            "sustitucion_evidencia_anterior": False,
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
            # allow_nan=False: NaN e Infinity no son JSON estandar y no pueden
            # entrar en evidencia normativa.
            json.dump(documento, fichero, ensure_ascii=False, indent=1, allow_nan=False)
            fichero.write("\n")
            fichero.flush()
            os.fsync(fichero.fileno())
        os.link(nombre_temporal, ruta)
    except BaseException:
        # El temporal debe desaparecer SIEMPRE: si no se puede eliminar, no se
        # calla — un residuo con JSON valido y valores derivados seria
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
    calibrar: Callable[[], Mapping[str, sondas.Calibracion]]
    ejecutor: Callable[[PlanCorrida], Sequence[Mapping[str, Any]]]
    capturar_entorno: Callable[[str], Mapping[str, Any]]
    cargar_linea_base: Callable[[], Mapping[str, Any]]


def dependencias_reales() -> DependenciasCorrida:
    """Dependencias de la corrida real sobre el repositorio y la maquina."""
    return DependenciasCorrida(
        entorno_custodia=entorno_custodia_real(),
        calibrar=calibrar_real,
        ejecutor=ejecutor_procesos_reales,
        capturar_entorno=capturar_entorno_real,
        cargar_linea_base=cargar_linea_base_real,
    )


def _calibracion_publicable(
    calibraciones: Mapping[str, sondas.Calibracion], plan: PlanCorrida
) -> dict[str, Any]:
    return {
        familia: {
            "unidades_referencia": calibraciones[familia].unidades_referencia,
            "coste_referencia_ns": calibraciones[familia].coste_referencia_ns,
            "muestras_ns": list(calibraciones[familia].muestras),
            "unidades_por_escala": {
                str(escala): plan.unidades[familia][escala] for escala in fp.ESCALERA_NS
            },
        }
        for familia in fp.FAMILIAS
    }


def ejecutar_corrida(
    *,
    sha_a: str,
    salida: Path,
    dependencias: DependenciasCorrida,
) -> tuple[int, tuple[str, ...]]:
    """Recorrido completo: precondiciones -> medicion -> documento -> JSON.

    Falla cerrado en cada paso: ante cualquier fallo bloqueante no se escribe
    ningun artefacto y no se publica ningun valor.
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

    try:
        calibraciones = dict(dependencias.calibrar())
        plan = plan_de_corrida(sondas.plan_de_unidades(calibraciones))
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"calibracion fallo: {exc}",)

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

    # Custodia REVERIFICADA despues de medir y antes de publicar: si el arbol,
    # el HEAD o cualquier blob preinscrito cambiaron durante la corrida, el
    # codigo medido ya no es el preinscrito y no se publica.
    try:
        posteriores = comprobar_precondiciones(
            dependencias.entorno_custodia, sha_a=sha_a, salida=salida, salida_existe=False
        )
        custodia_ok = posteriores.permite_medir
        anterior_ok = posteriores.evidencia_anterior_intacta
        fallos_posteriores = posteriores.fallos
    except Exception as exc:
        custodia_ok = False
        anterior_ok = False
        fallos_posteriores = (f"reverificacion de custodia fallo: {exc}",)

    try:
        _, medidas = medidas_desde_resultados(resultados)
        _, unitarias = unitarias_desde_resultados(resultados)
        punto = fp.resolver_punto_fijo(medidas)
        sm = fp.calcular_sm(unitarias)
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"resolucion del punto fijo fallo: {exc}",)

    controles = evaluar_controles_desde_resultados(
        resultados,
        plan=plan,
        captura_inicial=captura_inicial,
        captura_final=captura_final,
        custodia_ok=custodia_ok,
        evidencia_anterior_intacta=anterior_ok,
        punto=punto,
    )
    evaluacion = fp.evaluar_controles(controles)

    # ``banda_cubre_el_suelo`` solo tiene sentido con umbral resuelto. Un
    # NO_EVALUABLE legitimo no puede quedar bloqueado por un control que
    # presupone lo que precisamente no se resolvio: se publica el
    # NO_EVALUABLE con su motivo y sin B ni U.
    fallos_relevantes = tuple(
        c for c in evaluacion.fallos if not (c == "banda_cubre_el_suelo" and not punto.evaluable)
    )
    if fallos_relevantes:
        detalle = tuple(f"control bloqueante fallido: {c}" for c in fallos_relevantes)
        if not custodia_ok:
            detalle += tuple(f"custodia tras medir: {f}" for f in fallos_posteriores)
        return CODIGO_BLOQUEADO, detalle

    try:
        documento = construir_documento(
            sha_a=sha_a,
            head=dependencias.entorno_custodia.head(),
            plan=plan,
            calibracion=_calibracion_publicable(calibraciones, plan),
            blobs_preinscritos=precondiciones.blobs_preinscritos,
            blobs_heredados=precondiciones.blobs_heredados,
            resultados=resultados,
            captura_inicial=captura_inicial,
            captura_final=captura_final,
            controles=controles,
            punto=punto,
            sm=sm,
            linea_base=dependencias.cargar_linea_base(),
        )
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"construccion del documento fallo: {exc}",)

    fallos_documento = esquema.fallos_suelo_multiescala(documento)
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
    # VERIFICA: si el artefacto sobrevive, no se puede seguir afirmando que no
    # se publico nada.
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

    fallos_relectura = esquema.fallos_suelo_multiescala(releido)
    if fallos_relectura:
        return _retirar(tuple(f"revalidacion tras escritura fallo: {f}" for f in fallos_relectura))

    return CODIGO_OK, ()


# --------------------------------------------------------------------------
# Interfaz de linea de ordenes
# --------------------------------------------------------------------------


def construir_parser() -> argparse.ArgumentParser:
    """Parser sin efectos secundarios."""
    parser = argparse.ArgumentParser(
        prog="run_floor_scale",
        description=(
            "Corrida del suelo multiescala LAB-LINUX para ADR002-TOL-209. "
            "Sin --execute no mide nada."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="autoriza expresamente la medicion real",
    )
    parser.add_argument(
        "--preinscription-commit",
        dest="preinscription_commit",
        default=None,
        help="SHA del commit de preinscripcion sucesora",
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
        help=argparse.SUPPRESS,  # uso interno del ejecutor
    )
    parser.add_argument(
        "--units",
        dest="units",
        default=None,
        help=argparse.SUPPRESS,  # plan de unidades que el padre impone al hijo
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
        print(f"procesos minimos: {fp.PROCESOS_MINIMOS}")
        print(f"familias neutrales: {list(fp.FAMILIAS)}")
        print(f"escalera nominal (ns): {list(fp.ESCALERA_NS)}")
        print(
            f"n por escala: {fp.N_COSTE_BAJO} hasta {fp.UMBRAL_COSTE_BAJO_NS} ns, luego "
            f"{fp.N_COSTE_ALTO}"
        )
        print(f"warm-up por escala: {fp.WARMUP_ESCALA} · rondas: {fp.RONDAS_ROUND_ROBIN}")
        print(f"sondas unitarias (SM): {list(fp.SONDAS_UNITARIAS)}")
        print(
            "criterio: U = menor escala con "
            f"{fp.OBJETIVO_RELATIVO_DEN} * D(s) <= s sostenido · "
            f"B = U / {fp.FACTOR_U} · m = {fp.MARGEN_M}"
        )
        print(f"controles bloqueantes: {len(fp.CONTROLES_BLOQUEANTES)}")
        return CODIGO_OK

    if not args.execute:
        print(
            "run_floor_scale no mide sin --execute. La medicion requiere "
            "autorizacion expresa e independiente."
        )
        return CODIGO_SIN_EXECUTE

    if args.worker:
        if not args.units:
            print("--worker exige --units: la cantidad de trabajo la fija el padre")
            return CODIGO_BLOQUEADO
        unidades = unidades_desde_json(json.loads(args.units))
        print(json.dumps(ejecutar_sondas_worker(unidades), ensure_ascii=False))
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
