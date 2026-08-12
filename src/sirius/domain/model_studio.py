"""Vocabulario compartido de Model Studio.

Los estados viven aquí, y no en la interfaz, por la misma razón por la que
viven aquí ``MessageStatus`` o ``LLMErrorKind``: son el contrato entre quien
produce el estado y quien lo pinta. Hoy los produce la propia ventana (E1);
mañana los producirán el Módulo Voz (#126) y el Módulo Captura (#127) a través
de sus puertos. Cambiar el proveedor de voz o el backend de grabación no puede
obligar a tocar la superficie visual, y con este vocabulario no lo hace: la
interfaz solo sabe representar un estado, nunca de dónde viene.

La lista unificada está registrada en
``docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md``
(R-04), que reconcilia las tres listas parciales e incompatibles de #126, #127
y ``SIRIUS-MODEL-STUDIO-UI-001``.
"""

from __future__ import annotations

from enum import StrEnum


class StudioInteractionState(StrEnum):
    """Estado de la conversación con Sirius: escuchar, pensar, hablar.

    Separado por completo de :class:`StudioCaptureState`: el criterio de
    aceptación 10 de ``SIRIUS-MODEL-STUDIO-UI-001`` exige que el estado de
    interacción y el de grabación nunca se confundan en pantalla.
    """

    DESACTIVADO = "desactivado"
    PREPARADO = "preparado"
    ESCUCHANDO = "escuchando"
    TRANSCRIBIENDO = "transcribiendo"
    REVISANDO = "revisando"
    PENSANDO = "pensando"
    EJECUTANDO = "ejecutando"
    SINTETIZANDO = "sintetizando"
    HABLANDO = "hablando"
    ERROR = "error"

    @property
    def label(self) -> str:
        """Texto visible en la barra superior, en mayúsculas."""
        return _INTERACTION_LABELS[self]

    @property
    def accepts_typing(self) -> bool:
        """Si el usuario puede escribir en la caja de entrada ahora mismo.

        ``TRANSCRIBIENDO`` la bloquea porque su resultado va a escribirse
        justo ahí y machacaría lo tecleado; ``PENSANDO``, ``EJECUTANDO`` y
        ``SINTETIZANDO`` la bloquean porque hay una operación en vuelo.
        """
        return self not in _TYPING_BLOCKED


_INTERACTION_LABELS: dict[StudioInteractionState, str] = {
    StudioInteractionState.DESACTIVADO: "DESACTIVADO",
    StudioInteractionState.PREPARADO: "PREPARADO",
    StudioInteractionState.ESCUCHANDO: "ESCUCHANDO",
    StudioInteractionState.TRANSCRIBIENDO: "TRANSCRIBIENDO",
    StudioInteractionState.REVISANDO: "REVISANDO",
    StudioInteractionState.PENSANDO: "PENSANDO",
    StudioInteractionState.EJECUTANDO: "EJECUTANDO",
    StudioInteractionState.SINTETIZANDO: "SINTETIZANDO",
    StudioInteractionState.HABLANDO: "HABLANDO",
    StudioInteractionState.ERROR: "ERROR",
}

_TYPING_BLOCKED = frozenset(
    {
        StudioInteractionState.DESACTIVADO,
        StudioInteractionState.TRANSCRIBIENDO,
        StudioInteractionState.PENSANDO,
        StudioInteractionState.EJECUTANDO,
        StudioInteractionState.SINTETIZANDO,
    }
)


class StudioCaptureState(StrEnum):
    """Estado del sistema de grabación, cámaras y escenas (#127).

    ``INICIANDO`` y ``DETENIENDO`` existen precisamente para no afirmar nada
    mientras la orden está en vuelo: #127 obliga a que la confirmación proceda
    del backend y no de la frase del modelo, de modo que el indicador rojo solo
    puede encenderse en ``GRABANDO``.

    En E1 el módulo no existe todavía y el estado es siempre ``DESACTIVADO``.
    """

    DESACTIVADO = "desactivado"
    PREPARADO = "preparado"
    INICIANDO = "iniciando"
    GRABANDO = "grabando"
    PAUSADO = "pausado"
    CAMBIANDO = "cambiando"
    DETENIENDO = "deteniendo"
    ERROR = "error"
    INCIERTO = "incierto"

    @property
    def label(self) -> str:
        """Texto visible en la barra superior, en mayúsculas."""
        return _CAPTURE_LABELS[self]

    @property
    def is_recording_confirmed(self) -> bool:
        """Si el backend confirma grabación activa.

        Único estado que autoriza el indicador rojo persistente. ``INICIANDO``
        y ``INCIERTO`` devuelven ``False`` a propósito: son exactamente los
        momentos en los que sería fácil —y falso— dar por hecho que ya se está
        grabando.
        """
        return self is StudioCaptureState.GRABANDO


_CAPTURE_LABELS: dict[StudioCaptureState, str] = {
    StudioCaptureState.DESACTIVADO: "SIN CAPTURA",
    StudioCaptureState.PREPARADO: "CAPTURA LISTA",
    StudioCaptureState.INICIANDO: "INICIANDO",
    StudioCaptureState.GRABANDO: "GRABANDO",
    StudioCaptureState.PAUSADO: "PAUSADO",
    StudioCaptureState.CAMBIANDO: "CAMBIANDO ESCENA",
    StudioCaptureState.DETENIENDO: "DETENIENDO",
    StudioCaptureState.ERROR: "ERROR DE CAPTURA",
    StudioCaptureState.INCIERTO: "ESTADO INCIERTO",
}
