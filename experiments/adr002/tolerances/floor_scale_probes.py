"""Sondas del suelo multiescala. Preinscripcion sucesora de ADR002-TOL-209.

Define QUE se mide y COMO, sin medir nada al importarse. Ninguna funcion de
este modulo se ejecuta por efecto de la importacion.

DOS FAMILIAS NEUTRALES, PARAMETRIZADAS POR ESCALA
=================================================

- ``cpu``: trabajo aritmetico puro en el interprete. Su unidad de trabajo es
  una vuelta de bucle. No toca disco, ni SQLite, ni ningun puerto.
- ``canon``: consultas por clave primaria sobre ``memory_revisions``, la
  tabla canonica de ADR-001. Su unidad de trabajo es una consulta resuelta.

Ninguna nombra ni usa FTS5, ``rank()``, BM25, embeddings ni operacion propia
de ningun candidato. La guarda ``comprobar_neutralidad`` del protocolo lo
verifica sobre los nombres publicados, y ``fallos_sql_de_sonda`` sobre el SQL.

POR QUE DOS FAMILIAS Y NO UNA
=============================

``cpu`` acota el suelo por abajo: es el trabajo mas simple que la maquina
puede hacer durante una ventana de duracion ``s``. ``canon`` anade lo que un
motor de almacenamiento real aporta —descenso de arbol, page cache,
asignacion de memoria, maquinaria de cursor— sin salir de lo neutral. El
protocolo toma el PEOR caso entre familias: un suelo subestimado exigiria a
los candidatos una estabilidad que el entorno no permite.

ESCALADO POR CANTIDAD DE TRABAJO DENTRO DE UNA SOLA VENTANA
===========================================================

La escala ``s`` se alcanza aumentando la cantidad de trabajo DENTRO de la
ventana cronometrada, no repitiendo la ventana. Una ventana de duracion
``s`` esta expuesta a la interferencia de la plataforma durante ``s``, que es
precisamente lo que hay que caracterizar.

El numero de unidades de cada escala lo fija el proceso PADRE una sola vez y
se impone identico a todos los hijos: TOL-107 mide la variacion entre
ejecuciones EQUIVALENTES, y dos ejecuciones que resuelven cantidades de
trabajo distintas no son equivalentes.

Reglas de instrumentacion aplicadas (protocolo aprobado §2):

- reloj monotonico ``time.perf_counter_ns``, nunca reloj de pared;
- fixtures fuera del cronometro: copia, conexion, DDL y seleccion de claves
  se preparan antes de abrir la ventana medida;
- warm-up declarado y descartado integro;
- vectores crudos en NANOSEGUNDOS, sin redondeo ni conversion.
"""

from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from experiments.adr002.tolerances import floor_scale_protocol as fp

# --------------------------------------------------------------------------
# Tabla canonica
# --------------------------------------------------------------------------
#
# ``memory_revisions`` es el canon de ADR-001: la reconstruccion obligatoria
# se hace DESDE esta tabla, y todo derivado es regenerable y no autoritativo.
# Su clave primaria ``id`` la crea la cadena canonica de Alembic
# (``4022f15cc8df_create_memories_and_memory_revisions``) como INTEGER
# autoincremental, de modo que el indice lo aporta SQLite y no lo elige
# ninguna arquitectura candidata. No es una tabla FTS ni una tabla sombra.

TABLA_CANONICA: Final = "memory_revisions"
COLUMNA_PK: Final = "id"

SQL_SONDA_CANON: Final = f"SELECT {COLUMNA_PK} FROM {TABLA_CANONICA} WHERE {COLUMNA_PK} = ?"

#: Fragmentos que jamas pueden aparecer en el SQL de una sonda normativa.
SQL_PROHIBIDO: Final[tuple[str, ...]] = (
    "fts",
    "match",
    "rank",
    "bm25",
    "embedding",
    "vector",
    "join",
    "like",
    "order by",
)


class SondaInvalidaError(ValueError):
    """La sonda no cumple la especificacion preinscrita."""


def fallos_sql_de_sonda(sql: str) -> tuple[str, ...]:
    """Guarda de neutralidad del SQL de las sondas de la familia ``canon``."""
    fallos: list[str] = []
    minusculas = sql.lower()
    for prohibido in SQL_PROHIBIDO:
        if prohibido in minusculas:
            fallos.append(f"el SQL de la sonda contiene '{prohibido}'")
    if TABLA_CANONICA not in minusculas:
        fallos.append(f"el SQL de la sonda no consulta la tabla canonica {TABLA_CANONICA}")
    if f"where {COLUMNA_PK} = ?" not in minusculas:
        fallos.append("el SQL de la sonda no filtra por clave primaria parametrizada")
    return tuple(dict.fromkeys(fallos))


def comprobar_sql_de_sonda() -> None:
    """Verifica el SQL de la familia ``canon`` contra la guarda de neutralidad."""
    fallos = fallos_sql_de_sonda(SQL_SONDA_CANON)
    if fallos:
        msg = f"SQL de sonda invalido: {list(fallos)}"
        raise SondaInvalidaError(msg)


# --------------------------------------------------------------------------
# Nucleo de medicion: vectores crudos en ns, sin redondeo
# --------------------------------------------------------------------------


def medir_ns(operacion: Callable[[], Any], *, n: int, warmup: int) -> list[int]:
    """Cronometra ``operacion`` ``n`` veces y devuelve el vector crudo en ns.

    ``operacion`` no debe construir fixtures: todo lo que no sea la operacion
    medida tiene que estar listo antes de llamar aqui. El warm-up se ejecuta
    y se descarta integro: sus muestras nunca entran en el vector devuelto.
    """
    if n <= 0:
        msg = "n debe ser positivo"
        raise ValueError(msg)
    if warmup < 0:
        msg = "el warm-up no puede ser negativo"
        raise ValueError(msg)

    for _ in range(warmup):
        operacion()

    muestras: list[int] = []
    for _ in range(n):
        inicio = time.perf_counter_ns()
        operacion()
        muestras.append(time.perf_counter_ns() - inicio)
    return muestras


# --------------------------------------------------------------------------
# Familia ``cpu``: trabajo aritmetico puro
# --------------------------------------------------------------------------


def girar(vueltas: int) -> int:
    """Unidad de trabajo de la familia ``cpu``: ``vueltas`` sumas enteras.

    Deliberadamente elemental y sin asignaciones en el bucle: el trabajo debe
    ser reproducible y proporcional a ``vueltas``, no representativo de
    ninguna operacion de producto.
    """
    if vueltas < 0:
        msg = "vueltas no puede ser negativo"
        raise ValueError(msg)
    total = 0
    for indice in range(vueltas):
        total += indice & 7
    return total


def operacion_cpu(unidades: int) -> Callable[[], Any]:
    """Invocable que resuelve ``unidades`` vueltas en UNA sola ventana."""
    if unidades <= 0:
        msg = "unidades debe ser positivo"
        raise ValueError(msg)

    def operacion() -> int:
        return girar(unidades)

    return operacion


# --------------------------------------------------------------------------
# Familia ``canon``: consultas por clave primaria sobre la tabla canonica
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FixtureCanon:
    """Conexion y claves preparadas antes de abrir la ventana medida."""

    conexion: sqlite3.Connection
    claves: tuple[int, ...]
    clave_existente: int
    clave_inexistente: int


def preparar_fixture_canon(base: Path) -> FixtureCanon:
    """Abre la base y selecciona las claves. NUNCA dentro del cronometro.

    La base debe existir ya, construida con la cadena canonica de Alembic y
    poblada por ``corpus.poblar``. Este modulo no crea esquema ni escribe DDL
    a mano (§2.5 del protocolo).
    """
    comprobar_sql_de_sonda()
    conexion = sqlite3.connect(str(base))
    conexion.execute("PRAGMA foreign_keys=ON")
    filas = conexion.execute(
        f"SELECT {COLUMNA_PK} FROM {TABLA_CANONICA} WHERE {COLUMNA_PK} >= 0"
    ).fetchall()
    if not filas:
        conexion.close()
        msg = f"{TABLA_CANONICA} vacia: no hay clave primaria utilizable"
        raise SondaInvalidaError(msg)
    claves = tuple(int(fila[0]) for fila in filas)
    return FixtureCanon(
        conexion=conexion,
        claves=claves,
        clave_existente=min(claves),
        clave_inexistente=max(claves) + 1_000_000,
    )


def operacion_canon(fixture: FixtureCanon, unidades: int) -> Callable[[], Any]:
    """Invocable que resuelve ``unidades`` consultas en UNA sola ventana.

    Las claves recorren ciclicamente todas las existentes en la tabla, de
    modo que el trabajo no se concentre en una unica pagina caliente. El
    consumo del cursor forma parte de la operacion medida porque sin
    consumirlo la consulta no llega a resolverse.
    """
    if unidades <= 0:
        msg = "unidades debe ser positivo"
        raise ValueError(msg)
    comprobar_sql_de_sonda()

    conexion = fixture.conexion
    disponibles = fixture.claves
    total = len(disponibles)
    plan = tuple(disponibles[indice % total] for indice in range(unidades))
    sql = SQL_SONDA_CANON

    def operacion() -> None:
        ejecutar = conexion.execute
        for clave in plan:
            ejecutar(sql, (clave,)).fetchall()

    return operacion


# --------------------------------------------------------------------------
# Sondas de suelo unitario: dan SM
# --------------------------------------------------------------------------


def _nada() -> None:
    """Invocable vacio. Su coste medido es el corchete completo del arnes."""
    return None


def sonda_vacia(*, n: int = fp.N_UNITARIA, warmup: int = fp.WARMUP_UNITARIA) -> list[int]:
    """``D_vacia``: distribucion del corchete del arnes sobre un invocable vacio."""
    return medir_ns(_nada, n=n, warmup=warmup)


def sonda_canon_unitaria(
    fixture: FixtureCanon,
    *,
    filas_esperadas: int,
    n: int = fp.N_UNITARIA,
    warmup: int = fp.WARMUP_UNITARIA,
) -> list[int]:
    """Una sola consulta por clave primaria: nivel unitario del instrumento.

    ``filas_esperadas`` debe ser 0 o 1. La verificacion de forma se hace
    fuera del cronometro, despues de medir.
    """
    if filas_esperadas not in (0, 1):
        msg = "filas_esperadas debe ser 0 o 1"
        raise ValueError(msg)
    comprobar_sql_de_sonda()

    clave = fixture.clave_existente if filas_esperadas == 1 else fixture.clave_inexistente
    conexion = fixture.conexion

    def consultar() -> None:
        conexion.execute(SQL_SONDA_CANON, (clave,)).fetchall()

    muestras = medir_ns(consultar, n=n, warmup=warmup)

    obtenidas = len(conexion.execute(SQL_SONDA_CANON, (clave,)).fetchall())
    if obtenidas != filas_esperadas:
        msg = f"la sonda devolvio {obtenidas} filas y se esperaban {filas_esperadas}"
        raise SondaInvalidaError(msg)
    return muestras


# --------------------------------------------------------------------------
# Calibracion. La hace el PADRE una vez; los hijos la reciben.
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Calibracion:
    """Coste medido de la cantidad de referencia de una familia."""

    familia: str
    unidades_referencia: int
    coste_referencia_ns: int
    muestras: tuple[int, ...]

    def unidades_para(self, escala_ns: int) -> int:
        return fp.unidades_para_escala(
            escala_ns,
            unidades_referencia=self.unidades_referencia,
            coste_referencia_ns=self.coste_referencia_ns,
        )


def calibrar_familia(operacion: Callable[[], Any], *, familia: str, unidades: int) -> Calibracion:
    """Mide el coste de la cantidad de referencia. Fuera de toda ventana normativa.

    Usa el P50 de ``MUESTRAS_CALIBRACION`` observaciones: la mediana no la
    arrastra una sola expropiacion, y el numero es impar para que el P50 por
    rango mas cercano caiga en una muestra central real.
    """
    if familia not in fp.FAMILIAS:
        msg = f"familia ajena a la preinscripcion: {familia}"
        raise SondaInvalidaError(msg)
    muestras = medir_ns(operacion, n=fp.MUESTRAS_CALIBRACION, warmup=fp.WARMUP_CALIBRACION)
    coste = fp.p50_ns(muestras)
    if coste <= 0:
        msg = f"calibracion de {familia} degenerada: P50 = {coste} ns"
        raise SondaInvalidaError(msg)
    return Calibracion(
        familia=familia,
        unidades_referencia=unidades,
        coste_referencia_ns=coste,
        muestras=tuple(muestras),
    )


def plan_de_unidades(calibraciones: Mapping[str, Calibracion]) -> dict[str, dict[int, int]]:
    """Numero de unidades por (familia, escala). Se congela antes de medir.

    El resultado es el contrato que todos los procesos hijos reciben: la
    cantidad de trabajo por escala es identica en todos ellos.
    """
    faltan = sorted(f for f in fp.FAMILIAS if f not in calibraciones)
    if faltan:
        msg = f"faltan calibraciones de familias: {faltan}"
        raise SondaInvalidaError(msg)
    return {
        familia: {escala: calibraciones[familia].unidades_para(escala) for escala in fp.ESCALERA_NS}
        for familia in fp.FAMILIAS
    }


# --------------------------------------------------------------------------
# Diagnostico de deriva intraproceso
# --------------------------------------------------------------------------


def diagnostico_referencia(
    *,
    vueltas: int = fp.VUELTAS_REFERENCIA,
    n: int = fp.N_REFERENCIA,
    warmup: int = fp.WARMUP_REFERENCIA,
) -> list[int]:
    """Trabajo fijo y declarado. Detecta throttling y deriva.

    Se reejecuta al inicio, mitad y final de cada proceso: un aumento
    monotono de su P50 entre los tres puntos que supere la tolerancia
    preinscrita es deriva o throttling, y bloquea la corrida.
    """
    if vueltas <= 0:
        msg = "vueltas debe ser positivo"
        raise ValueError(msg)
    return medir_ns(operacion_cpu(vueltas), n=n, warmup=warmup)


# --------------------------------------------------------------------------
# Orden round-robin: nunca por bloques completos (§5.2 aplicado a sondas)
# --------------------------------------------------------------------------


def orden_round_robin(pares: Sequence[tuple[str, int]], rondas: int) -> Iterator[tuple[str, int]]:
    """Genera el orden de ejecucion intercalado, no en bloques.

    Ejecutar todas las repeticiones de una sonda y despues las de la
    siguiente alinearia la identidad de la sonda con la deriva temporal: es
    el mismo defecto que el §5.2 prohibe para candidatos.
    """
    if rondas <= 0:
        msg = "rondas debe ser positivo"
        raise ValueError(msg)
    for _ in range(rondas):
        yield from pares


def pid_actual() -> int:
    """PID del proceso en curso, para verificar independencia real."""
    return os.getpid()
