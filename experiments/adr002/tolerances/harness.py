"""Arnes de medicion: reloj monotonico, warm-up y percentiles declarados.

Reglas que este modulo hace cumplir, tomadas del §5.1 del paquete 02:

- reloj monotonico (``time.perf_counter_ns``), nunca el reloj de pared;
- warm-up explicito, cuyas muestras se descartan y se declaran;
- minimo 30 repeticiones por escenario, comprobado en ejecucion;
- el tiempo de construccion de fixtures NUNCA entra en la latencia medida:
  la funcion cronometrada recibe todo ya construido;
- la resolucion del percentil se declara junto al valor, porque con N
  muestras un P99 no puede afirmar mas de lo que N permite.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

REPETICIONES_MINIMAS = 30

# Perfiles de repeticion. El paquete pide 30 como minimo y 100 cuando el
# coste sea bajo; se declaran aqui para que el informe no invente cifras.
REPS_BARATO = 100
REPS_CARO = 30


class RepeticionesInsuficientesError(ValueError):
    """El escenario se configuro por debajo del minimo exigido."""


@dataclass(frozen=True, slots=True)
class Distribucion:
    """Distribucion de latencias de un escenario, en milisegundos."""

    n: int
    warmup_descartado: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    media_ms: float
    resolucion_p99: str
    muestras_ms: list[float] = field(default_factory=list)


def percentil(ordenadas: list[float], fraccion: float) -> float:
    """Percentil por el metodo del rango mas cercano (nearest-rank).

    Se elige nearest-rank y no interpolacion lineal porque devuelve
    siempre una muestra realmente observada: un P99 interpolado puede dar
    un valor que nunca ocurrio, y este informe no debe afirmar eso.
    """
    if not ordenadas:
        msg = "no hay muestras"
        raise ValueError(msg)
    rango = max(1, math.ceil(fraccion * len(ordenadas)))
    indice = min(len(ordenadas) - 1, rango - 1)
    return ordenadas[indice]


def _resolucion_p99(n: int) -> str:
    """Qué puede afirmar honestamente un P99 con ``n`` muestras."""
    peores = max(1, n - int(0.99 * n))
    if n < 100:
        return (
            f"con n={n}, el P99 por rango mas cercano coincide con el maximo observado; "
            f"solo acota la cola, no la caracteriza"
        )
    return f"con n={n}, el P99 corresponde a la {peores}.a peor muestra observada"


def medir(
    operacion: Callable[[], Any],
    *,
    repeticiones: int,
    warmup: int,
    guardar_muestras: bool = False,
) -> Distribucion:
    """Cronometra ``operacion`` con reloj monotonico.

    ``operacion`` no debe construir fixtures: todo lo que no sea la
    operacion medida tiene que estar ya listo antes de llamar aqui.
    """
    if repeticiones < REPETICIONES_MINIMAS:
        msg = f"{repeticiones} repeticiones; el minimo exigido es {REPETICIONES_MINIMAS}"
        raise RepeticionesInsuficientesError(msg)

    for _ in range(warmup):
        operacion()

    muestras_ns: list[int] = []
    for _ in range(repeticiones):
        inicio = time.perf_counter_ns()
        operacion()
        muestras_ns.append(time.perf_counter_ns() - inicio)

    muestras_ms = sorted(ns / 1_000_000 for ns in muestras_ns)
    return Distribucion(
        n=repeticiones,
        warmup_descartado=warmup,
        p50_ms=round(percentil(muestras_ms, 0.50), 4),
        p95_ms=round(percentil(muestras_ms, 0.95), 4),
        p99_ms=round(percentil(muestras_ms, 0.99), 4),
        min_ms=round(muestras_ms[0], 4),
        max_ms=round(muestras_ms[-1], 4),
        media_ms=round(sum(muestras_ms) / len(muestras_ms), 4),
        resolucion_p99=_resolucion_p99(repeticiones),
        muestras_ms=[round(m, 4) for m in muestras_ms] if guardar_muestras else [],
    )


def como_dict(distribucion: Distribucion) -> dict[str, Any]:
    return asdict(distribucion)


def cronometrar_una_vez(operacion: Callable[[], Any]) -> tuple[Any, float]:
    """Una sola pasada cronometrada, para operaciones irrepetibles como la
    construccion inicial del indice. Devuelve resultado y milisegundos."""
    inicio = time.perf_counter_ns()
    resultado = operacion()
    return resultado, (time.perf_counter_ns() - inicio) / 1_000_000
