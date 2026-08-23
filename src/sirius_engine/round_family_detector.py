"""Detector de familia repetida entre rondas (M1, incidencia #277, ADR-078).

Complementa, no sustituye, la política de convergencia real
(``scripts/automation/sirius_convergence.py``): esa política cuenta
hallazgos y decide si el ciclo puede seguir, pero no distingue si las rondas
que sigue aceptando están dando vueltas sobre el mismo defecto o resolviendo
uno distinto cada vez (incidencia #251). Este módulo no toca esa decisión
-**no para el ciclo, no cambia ningún umbral de convergencia**- y **no
diagnostica la causa raíz ni propone la salida** (eso es la incidencia
#251): solo señala que unas rondas se parecen, y con qué evidencia concreta.

**Criterio, medido antes de fijarlo (nota de arranque de la incidencia
#277).** Sobre las incidencias reales de este repositorio con más de una
ronda -14 en total, comprobadas a mano-, la señal candidata era «el mismo
archivo recibe hallazgos en 3 o más rondas consecutivas» (frente a solo 2,
que es el caso normal declarado en el requisito 3: corregir un fichero y
que la revisión vuelva a mirarlo). Con el umbral en 3 rondas consecutivas,
la señal se disparó en exactamente 4 de las 14 incidencias -#182, #186,
#211 y #246-, y las cuatro resultaron ser, comprobado a mano leyendo el
texto de la revisión, la misma familia de defecto:

- **#246** (C3a): seis rondas, todas sobre
  ``scripts/automation/sirius_check_docs.py``, alternando entre dos
  arreglos incompatibles -el caso que la propia incidencia #277 cita como
  conocido-.
- **#211**: la propia revisora lo dice en la ronda 3, textualmente: «Es la
  misma familia de defecto que CODEX-001 (rondas 1 y 2 de esta misma PR):
  parseo heurístico y parcial de la gramática de banderas de `gh`».
- **#182** y **#186**: series de hallazgos consecutivos sobre el mismo
  archivo, cada uno una variación no cubierta del mismo problema de fondo
  (truncado del diario durable en #182; aislamiento de claves internas en
  #186).

Ningún otro archivo, en ninguna de las 14 incidencias, llegó a 3 rondas
consecutivas. Con el umbral en 3, la medición no encontró ningún falso
positivo entre los aciertos: 4 aciertos, 0 falsos, sobre el conjunto medido.

**Lo que este criterio NO atrapa, y por qué eso es aceptable.** La
incidencia #268 (citada en el requisito 2) tuvo rondas 1-2 de revisión con
hallazgos en ``seven_day_streak_cli.py`` que sí eran la misma familia de
defecto real -confirmado porque el corrector, aplicando la regla de las dos
rondas de ADR-001 antes de una ronda 3, encontró la causa raíz
(``mirror_projection.py`` inyectando ``scripts/`` en ``sys.path``) y la
registró en la incidencia #272 (H-13), corregida en la PR #283-: no es un
caso de progreso normal. El mismo archivo solo se repite en 2 rondas
consecutivas, nunca en 3, así que este detector no la señala: es una familia
real que el umbral elegido no atrapa, no un falso positivo evitado. El
requisito 2 solo exige acertar en **al menos una** de las dos incidencias
citadas (#268 o #246); este bloque acierta en #246 -y, con evidencia todavía
más explícita, en #211- sin inventar una segunda señal que la medición no
pudiera respaldar (criterio de parada (a) de la nota de arranque: si la
medición hubiera mostrado más falsos que ciertos con un umbral más laxo, el
criterio se cambiaba o el bloque se paraba).

Determinista y sin red: recibe los registros de ronda que
:func:`sirius_engine.round_history.parse_round_records` ya extrajo -no lee
la incidencia, no llama a `gh` ni a ningún modelo-.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sirius_engine.round_history import _normalize_location

#: Medido sobre las 14 incidencias reales del repositorio con más de una
#: ronda (ver el docstring del módulo): 3 rondas consecutivas sobre el mismo
#: archivo dio 4 aciertos y 0 falsos positivos. La incidencia #268 (2 rondas
#: consecutivas, nunca 3) es una familia real que este umbral no atrapa, no
#: un falso positivo evitado; ver el docstring del módulo.
RONDAS_CONSECUTIVAS_MINIMAS = 3


@dataclass(frozen=True, slots=True)
class EvidenciaFamiliaRepetida:
    """Un tramo de rondas consecutivas en las que un mismo archivo recibió hallazgos.

    ``rondas`` es el tramo consecutivo COMPLETO detectado -no una ventana
    arbitraria de tamaño fijo-, para que la evidencia publicada sea
    exactamente lo que se observó y no un recorte de ello.
    """

    archivo: str
    rondas: tuple[int, ...]
    detalle: str


@dataclass(frozen=True, slots=True)
class DeteccionFamiliaRepetida:
    """Resultado completo: si hay familia repetida, y con qué evidencia.

    ``hay_familia_repetida`` es una propiedad derivada de ``evidencias``, no
    un campo independiente: no puede haber un «sí» sin su porqué (requisito
    5 de la incidencia #277).
    """

    evidencias: tuple[EvidenciaFamiliaRepetida, ...]

    @property
    def hay_familia_repetida(self) -> bool:
        return bool(self.evidencias)


def detectar_familia_repetida(
    registros: Sequence[Mapping[str, Any]],
) -> DeteccionFamiliaRepetida:
    """¿Hay algún archivo que reciba hallazgos en 3+ rondas consecutivas?

    ``registros`` es la salida de
    :func:`sirius_engine.round_history.parse_round_records`: cada registro
    trae ``round`` y ``findings`` (con ``file`` por hallazgo). El orden de
    entrada no importa -se reordena por ``round`- así que un historial ya
    cronológico y uno que no lo fuera dan el mismo resultado.

    La ubicación se normaliza con
    :func:`sirius_engine.round_history._normalize_location` -la misma
    función que usa la huella de ``sirius_convergence.fingerprint``-, para
    que un sufijo de línea (``:120``, que se desplaza con cualquier edición
    anterior del archivo) no separe artificialmente dos apariciones del
    mismo archivo.
    """
    archivo_a_rondas: dict[str, list[int]] = {}
    for registro in sorted(registros, key=lambda registro: int(registro["round"])):
        numero = int(registro["round"])
        archivos_en_ronda = {
            _normalize_location(hallazgo["file"])
            for hallazgo in registro["findings"]
            if hallazgo.get("file")
        }
        for archivo in archivos_en_ronda:
            archivo_a_rondas.setdefault(archivo, []).append(numero)

    evidencias = [
        EvidenciaFamiliaRepetida(
            archivo=archivo,
            rondas=tuple(tramo),
            detalle=(
                f"«{archivo}» recibe hallazgos en {len(tramo)} rondas consecutivas "
                f"(rondas {tramo[0]}-{tramo[-1]}): la corrección de una ronda no está "
                "resolviendo lo que la revisión sigue encontrando en la siguiente."
            ),
        )
        for archivo, rondas in archivo_a_rondas.items()
        for tramo in _tramos_consecutivos(rondas)
        if len(tramo) >= RONDAS_CONSECUTIVAS_MINIMAS
    ]
    evidencias.sort(key=lambda evidencia: (evidencia.rondas[0], evidencia.archivo))
    return DeteccionFamiliaRepetida(evidencias=tuple(evidencias))


def _tramos_consecutivos(rondas: list[int]) -> list[list[int]]:
    """Tramos maximales de números consecutivos (sin huecos) en ``rondas``.

    ``[1, 2, 5]`` da ``[[1, 2], [5]]``: el hueco entre 2 y 5 corta el tramo,
    porque una recurrencia con hueco -el archivo se corrigió, se dejó en paz
    una ronda, y algo distinto volvió a tocarlo después- no es la misma
    evidencia que tres rondas seguidas sin que la corrección surta efecto.
    """
    ordenadas = sorted(set(rondas))
    tramos: list[list[int]] = []
    for numero in ordenadas:
        if tramos and numero == tramos[-1][-1] + 1:
            tramos[-1].append(numero)
        else:
            tramos.append([numero])
    return tramos
