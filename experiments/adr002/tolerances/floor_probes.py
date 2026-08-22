"""Sondas del suelo de medicion LAB-LINUX. Fase A: preinscripcion.

Define QUE se mide y COMO, sin medir nada al importarse. Ninguna funcion
de este modulo se ejecuta por efecto de la importacion.

Separacion normativa (decision 8 del paquete 05):

- ``F`` normativo: ``D_vacia``, ``SQLite_0_filas``, ``SQLite_1_fila``.
  Solo estas tres derivan SM, B50, B95, B y U.
- Diagnosticos: lecturas consecutivas del reloj, busy-spin calibrado,
  comprobacion 1x/2x y sobrecoste del puerto comun. **Ninguno modifica
  B ni U.**

Reglas de instrumentacion aplicadas (protocolo aprobado §2):

- reloj monotonico ``time.perf_counter_ns``, nunca reloj de pared;
- fixtures fuera del cronometro: copia, conexion, DDL y seleccion de
  claves se preparan antes de abrir la ventana medida;
- warm-up declarado y descartado integro;
- vectores crudos en NANOSEGUNDOS, sin redondeo ni conversion.
"""

from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from experiments.adr002.tolerances import floor_protocol as fp

# --------------------------------------------------------------------------
# Tabla canonica elegida tras inspeccionar el repositorio
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

SQL_SONDA_SQLITE: Final = f"SELECT {COLUMNA_PK} FROM {TABLA_CANONICA} WHERE {COLUMNA_PK} = ?"


class SondaInvalidaError(ValueError):
    """La sonda no cumple la especificacion preinscrita."""


def comprobar_sql_de_sonda() -> None:
    """Verifica el SQL de las sondas de F contra la guarda del protocolo."""
    fallos = fp.fallos_sql_de_sonda(
        SQL_SONDA_SQLITE, tabla_canonica=TABLA_CANONICA, columna_pk=COLUMNA_PK
    )
    if fallos:
        msg = f"SQL de sonda invalido: {list(fallos)}"
        raise SondaInvalidaError(msg)


# --------------------------------------------------------------------------
# Nucleo de medicion: vectores crudos en ns, sin redondeo
# --------------------------------------------------------------------------


def medir_ns(
    operacion: Callable[[], Any],
    *,
    n: int,
    warmup: int,
) -> list[int]:
    """Cronometra ``operacion`` ``n`` veces y devuelve el vector crudo en ns.

    ``operacion`` no debe construir fixtures: todo lo que no sea la
    operacion medida tiene que estar listo antes de llamar aqui. El
    warm-up se ejecuta y se descarta integro: sus muestras nunca entran
    en el vector devuelto.
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


def _nada() -> None:
    """Invocable vacio. Su coste medido es el corchete completo del arnes."""
    return None


def sonda_vacia(*, n: int = fp.N_SONDA_F, warmup: int = fp.WARMUP_SONDA_F) -> list[int]:
    """``D_vacia``: distribucion del corchete del arnes sobre un invocable vacio."""
    return medir_ns(_nada, n=n, warmup=warmup)


# --------------------------------------------------------------------------
# Fixtures de las sondas SQLite. Todo fuera del cronometro.
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FixtureSqlite:
    """Conexion y claves preparadas antes de abrir la ventana medida."""

    conexion: sqlite3.Connection
    clave_existente: int
    clave_inexistente: int


def preparar_fixture_sqlite(base: Path) -> FixtureSqlite:
    """Abre la base y selecciona las claves. NUNCA dentro del cronometro.

    La base debe existir ya, construida con la cadena canonica de Alembic
    y poblada por ``corpus.poblar``. Este modulo no crea esquema ni escribe
    DDL a mano (§2.5 del protocolo).
    """
    conexion = sqlite3.connect(str(base))
    conexion.execute("PRAGMA foreign_keys=ON")
    cursor = conexion.execute(f"SELECT MIN({COLUMNA_PK}), MAX({COLUMNA_PK}) FROM {TABLA_CANONICA}")
    fila = cursor.fetchone()
    if fila is None or fila[0] is None:
        conexion.close()
        msg = f"{TABLA_CANONICA} vacia: no hay clave primaria utilizable"
        raise SondaInvalidaError(msg)
    minimo, maximo = int(fila[0]), int(fila[1])
    return FixtureSqlite(
        conexion=conexion,
        clave_existente=minimo,
        clave_inexistente=maximo + 1_000_000,
    )


def sonda_sqlite(
    fixture: FixtureSqlite,
    *,
    filas_esperadas: int,
    n: int = fp.N_SONDA_F,
    warmup: int = fp.WARMUP_SONDA_F,
) -> list[int]:
    """Consulta preparada por clave primaria sobre la tabla canonica.

    ``filas_esperadas`` debe ser 0 o 1. La comprobacion del numero de filas
    forma parte de la operacion medida porque es el consumo del cursor, no
    una verificacion externa: sin consumirlo la consulta no llega a resolverse.
    """
    if filas_esperadas not in (0, 1):
        msg = "filas_esperadas debe ser 0 o 1"
        raise ValueError(msg)
    comprobar_sql_de_sonda()

    clave = fixture.clave_existente if filas_esperadas == 1 else fixture.clave_inexistente
    conexion = fixture.conexion

    def consultar() -> None:
        conexion.execute(SQL_SONDA_SQLITE, (clave,)).fetchall()

    muestras = medir_ns(consultar, n=n, warmup=warmup)

    obtenidas = len(conexion.execute(SQL_SONDA_SQLITE, (clave,)).fetchall())
    if obtenidas != filas_esperadas:
        msg = f"la sonda devolvio {obtenidas} filas y se esperaban {filas_esperadas}"
        raise SondaInvalidaError(msg)
    return muestras


# --------------------------------------------------------------------------
# Diagnosticos. Fuera de F. Nunca modifican B ni U.
# --------------------------------------------------------------------------


def diagnostico_lecturas_reloj(
    *,
    n: int = fp.N_SONDA_RELOJ,
    warmup: int = fp.WARMUP_SONDA_RELOJ,
) -> list[int]:
    """Deltas entre lecturas consecutivas de ``perf_counter_ns``.

    Caracteriza la resolucion efectiva y la granularidad. Bucle cerrado:
    representa el MEJOR caso —cache caliente, sin expropiacion— y por
    tanto puede subestimar el coste real de leer el reloj. Declarado como
    desviacion al alza en n respecto del minimo del protocolo (§3.2).
    No entra en el presupuesto principal de ruido (decision 2).
    """
    for _ in range(warmup):
        time.perf_counter_ns()
    deltas: list[int] = []
    previo = time.perf_counter_ns()
    for _ in range(n):
        actual = time.perf_counter_ns()
        deltas.append(actual - previo)
        previo = actual
    return deltas


def _girar(vueltas: int) -> int:
    total = 0
    for indice in range(vueltas):
        total += indice & 7
    return total


def diagnostico_busy_spin(
    *,
    vueltas: int,
    n: int = fp.N_DIAGNOSTICO,
    warmup: int = fp.WARMUP_DIAGNOSTICO,
) -> list[int]:
    """Trabajo fijo y declarado. Detecta throttling y deriva.

    Se reejecuta al inicio, mitad y final de cada proceso: un aumento
    monotono de su P50 entre los tres puntos es deriva o throttling.
    """
    if vueltas <= 0:
        msg = "vueltas debe ser positivo"
        raise ValueError(msg)
    return medir_ns(lambda: _girar(vueltas), n=n, warmup=warmup)


@dataclass(frozen=True, slots=True)
class ResultadoDuplicacion:
    """Comprobacion 1x/2x: valida el instrumento, no define el regimen."""

    vueltas_1x: int
    vueltas_2x: int
    p50_1x: int
    p50_2x: int
    escala: bool


def diagnostico_duplicacion(
    *,
    vueltas: int,
    tolerancia_num: int = fp.TOLERANCIA_DUPLICACION_NUM,
    tolerancia_den: int = fp.TOLERANCIA_DUPLICACION_DEN,
    n: int = fp.N_DIAGNOSTICO,
    warmup: int = fp.WARMUP_DIAGNOSTICO,
) -> ResultadoDuplicacion:
    """Mide el mismo trabajo con 1x y 2x dentro de la misma ventana.

    Si el tiempo medido no escala con el trabajo, el corchete domina y la
    magnitud se declara invalida. La tolerancia se expresa como fraccion
    entera y queda preinscrita: no se ajusta tras observar resultados.
    """
    p50_1x = fp.p50_ns(diagnostico_busy_spin(vueltas=vueltas, n=n, warmup=warmup))
    p50_2x = fp.p50_ns(diagnostico_busy_spin(vueltas=2 * vueltas, n=n, warmup=warmup))
    return ResultadoDuplicacion(
        vueltas_1x=vueltas,
        vueltas_2x=2 * vueltas,
        p50_1x=p50_1x,
        p50_2x=p50_2x,
        escala=escala_con_el_trabajo(
            p50_1x, p50_2x, tolerancia_num=tolerancia_num, tolerancia_den=tolerancia_den
        ),
    )


def escala_con_el_trabajo(
    p50_1x: int,
    p50_2x: int,
    *,
    tolerancia_num: int = fp.TOLERANCIA_DUPLICACION_NUM,
    tolerancia_den: int = fp.TOLERANCIA_DUPLICACION_DEN,
) -> bool:
    """``p50_2x`` debe acercarse a ``2 * p50_1x`` dentro de la tolerancia.

    Comparacion en aritmetica entera exacta:
    ``|p50_2x - 2*p50_1x| * tolerancia_den <= 2*p50_1x * tolerancia_num``.
    """
    if p50_1x <= 0:
        return False
    esperado = 2 * p50_1x
    desvio = abs(p50_2x - esperado)
    return desvio * tolerancia_den <= esperado * tolerancia_num


def diagnostico_sobrecoste_puerto(
    buscar: Callable[[str], Any],
    consulta: str,
    *,
    n: int = fp.N_DIAGNOSTICO,
    warmup: int = fp.WARMUP_DIAGNOSTICO,
) -> list[int]:
    """Sobrecoste del puerto comun equivalente a ``KnowledgeSearchRepository``.

    Queda DELIBERADAMENTE fuera de F (matriz 41): incorporarlo elevaria B
    y U, empujando mas magnitudes al regimen absoluto. Ademas el puerto
    actual resuelve sobre FTS5, que no puede tocar una sonda normativa.
    Se publica como diagnostico para que una revision futura decida con
    evidencia si debe entrar en F.
    """
    return medir_ns(lambda: buscar(consulta), n=n, warmup=warmup)


# --------------------------------------------------------------------------
# Orden round-robin: nunca por bloques completos (§5.2 aplicado a sondas)
# --------------------------------------------------------------------------


def orden_round_robin(sondas: Sequence[str], rondas: int) -> Iterator[str]:
    """Genera el orden de ejecucion intercalado, no en bloques.

    Ejecutar todas las repeticiones de una sonda y despues las de la
    siguiente alinearia la identidad de la sonda con la deriva temporal:
    es el mismo defecto que el §5.2 prohibe para candidatos.
    """
    if rondas <= 0:
        msg = "rondas debe ser positivo"
        raise ValueError(msg)
    for _ in range(rondas):
        yield from sondas


def pid_actual() -> int:
    """PID del proceso en curso, para verificar independencia real."""
    return os.getpid()
