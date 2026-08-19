"""La puerta determinista (arquitectura §8.5): tres desenlaces y ninguno más.

Conversar, consultar el pasado, explorar y debatir NO crean WorkItem — la
conversación es entrada, y su continuidad la da la Capa 1 +
``contexto.recuperar`` (A3), nunca un WorkItem. Sobre una intención ya
clasificada (:class:`~sirius_engine.domain.intent.IntentSignal`), la puerta
decide, y decide siempre igual para la misma entrada (misma entrada, mismo
desenlace: requisito "la puerta es determinista" de la incidencia #206):

1. **Orden explícita e inequívoca** → el WorkItem se crea Y se activa
   directamente, sin segunda confirmación: la orden ya es la autorización
   (#172 §0). Pedir confirmación aquí es el defecto G1 que el diseño ya
   corrigió (nota de riesgo principal de A5 en el plan de implementación).
2. **Conversación, consulta del pasado, exploración o ambigüedad** → no se
   crea ningún WorkItem.
3. **Acción sensible o material** (una de las siete causas de arquitectura
   §10) → el WorkItem se crea pero se escala de inmediato a
   ``NEEDS_DECISION`` en vez de activarse sin más: confirma o escala, nunca
   ejecuta esa parte sin pasar por el propietario.

Esta función no toca ningún almacén ni ningún puerto: es pura, para que su
determinismo sea comprobable sin infraestructura
(:mod:`sirius_engine.work_intake` es quien aplica la decisión contra el
``WorkEngineStore`` real).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sirius_engine.domain.escalation import CausaEscalado
from sirius_engine.domain.intent import DatosNuevoTrabajo, IntentSignal, TipoIntencion


class ResultadoPuerta(StrEnum):
    """Los tres desenlaces de arquitectura §8.5, y ninguno más."""

    NO_CREAR = "no_crear"
    CREAR_Y_ACTIVAR = "crear_y_activar"
    CREAR_Y_ESCALAR = "crear_y_escalar"


#: Tipos de intención que nunca crean WorkItem (Capa 1: #172 §6.1-6.3).
_TIPOS_SIN_TRABAJO = frozenset(
    {
        TipoIntencion.CONVERSAR,
        TipoIntencion.CONSULTAR_PASADO,
        TipoIntencion.EXPLORAR,
        TipoIntencion.AMBIGUA,
    }
)


@dataclass(frozen=True, slots=True)
class DecisionPuerta:
    """El desenlace de la puerta para una intención dada."""

    resultado: ResultadoPuerta
    motivo: str
    datos_trabajo: DatosNuevoTrabajo | None = None
    causa_escalado: CausaEscalado | None = None
    pregunta_aclaratoria: str | None = None
    consulta: str | None = None


def decidir(signal: IntentSignal) -> DecisionPuerta:
    """La puerta determinista. Misma ``IntentSignal``, siempre la misma ``DecisionPuerta``."""
    if signal.tipo in _TIPOS_SIN_TRABAJO:
        return DecisionPuerta(
            resultado=ResultadoPuerta.NO_CREAR,
            motivo=f"tipo de intención {signal.tipo.value!r}: no crea WorkItem",
            pregunta_aclaratoria=signal.pregunta_aclaratoria,
            consulta=signal.consulta,
        )
    if signal.tipo is TipoIntencion.ORDEN_INEQUIVOCA:
        assert signal.datos_trabajo is not None  # garantizado por IntentSignal.__post_init__
        return DecisionPuerta(
            resultado=ResultadoPuerta.CREAR_Y_ACTIVAR,
            motivo="orden explícita e inequívoca: la orden ya es la autorización",
            datos_trabajo=signal.datos_trabajo,
        )
    assert signal.tipo is TipoIntencion.SENSIBLE_O_MATERIAL
    assert signal.datos_trabajo is not None
    assert signal.causa_sensibilidad is not None
    return DecisionPuerta(
        resultado=ResultadoPuerta.CREAR_Y_ESCALAR,
        motivo=signal.motivo_sensibilidad or "acción sensible o material: requiere decisión",
        datos_trabajo=signal.datos_trabajo,
        causa_escalado=signal.causa_sensibilidad,
    )
