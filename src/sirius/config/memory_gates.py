"""Las puertas de la memoria: una clave maestra y tres interruptores finos.

Hasta la incidencia #603 la memoria tenía **una sola** puerta,
``category_matching_enabled`` (SIRIUS-ARQ-0.2 §6.3, D7 punto 6), y esa clave
encendía de golpe siete cosas: el vocabulario de categoría, el de criticidad,
la bandera del caso de uso, el clasificador de intención del intérprete
(ADR-164), el filtro de relevancia, el techo de criticidad y la bandera del
``ContextBuilder``. Abrirla era, por tanto, un gesto que no se podía observar:
si la latencia empeoraba —RNF-003 midió 438-780 ms P95 con el paquete entero
abierto frente a los 300 ms del presupuesto— no había forma de saber cuál de
las siete piezas lo había hecho.

Este módulo **parte la puerta antes de abrirla**, y no abre ninguna. Las tres
claves nuevas nacen apagadas, la maestra conserva exactamente el significado
que §6.3 le da hoy —encender las tres a la vez— y con todo apagado la
construcción es, argumento por argumento, la de siempre.

La regla de lectura es la de la clave de siempre y no se relaja: **solo el
literal booleano ``True`` cuenta**. Una edición manual de ``settings.json``
que deje ``"true"``, ``1`` o cualquier otro valor truthy pero no booleano deja
la puerta cerrada, igual que fija
``test_gate_stays_closed_on_a_truthy_but_non_boolean_value`` para la maestra
desde la incidencia #471/CODEX-001.

La única dependencia entre interruptores es la que impide que uno quede
**encendido pero inerte**: el clasificador de intención solo tiene efecto si el
motor por etapas corre —``_peticion`` solo se llama desde
``_recuperar_por_etapas``—, así que ``query_intent_enabled`` sin
``staged_engine_enabled`` no construye nada. Un interruptor encendido que no
mueve nada es peor que uno apagado: promete una observación que no existe.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

#: La clave de siempre (§6.3): encender esta enciende las tres piezas.
MASTER_GATE_KEY = "category_matching_enabled"
#: El motor por etapas con sus índices de categoría y criticidad y la siembra M20.
STAGED_ENGINE_KEY = "staged_engine_enabled"
#: La petición propia de ADR-164: el clasificador de intención local.
QUERY_INTENT_KEY = "query_intent_enabled"
#: El filtro de relevancia local y el camino de puerta abierta del ContextBuilder.
RELEVANCE_FILTER_KEY = "relevance_filter_enabled"


@dataclass(frozen=True)
class PuertasDeMemoria:
    """Estado efectivo de las tres piezas, ya resuelto contra la maestra.

    Inmutable a propósito: se lee una vez en el arranque y se reparte por el
    cableado; que nadie pueda cambiarlo a mitad de la construcción es lo que
    hace que «con todo apagado es la construcción de hoy» sea comprobable
    mirando un solo sitio.
    """

    motor_por_etapas: bool
    peticion_propia: bool
    filtro_de_relevancia: bool


def _encendida(settings: Mapping[str, Any], clave: str) -> bool:
    """``True`` solo si la clave trae el booleano JSON ``true`` exacto."""
    return settings.get(clave, False) is True


def puertas_de_memoria(settings: Mapping[str, Any]) -> PuertasDeMemoria:
    """Resuelve los ajustes persistidos en el estado efectivo de cada pieza.

    El efectivo de cada pieza es la maestra **o** su clave fina, con una sola
    excepción: la petición propia exige además el motor por etapas, porque sin
    él el clasificador nunca llega a consultarse.
    """
    maestra = _encendida(settings, MASTER_GATE_KEY)
    motor_por_etapas = maestra or _encendida(settings, STAGED_ENGINE_KEY)
    return PuertasDeMemoria(
        motor_por_etapas=motor_por_etapas,
        peticion_propia=(maestra or _encendida(settings, QUERY_INTENT_KEY)) and motor_por_etapas,
        filtro_de_relevancia=maestra or _encendida(settings, RELEVANCE_FILTER_KEY),
    )
