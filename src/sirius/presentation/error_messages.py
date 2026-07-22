"""Mapea ``LLMErrorKind`` a un mensaje en español, seguro y accionable (RF-028).

Pura y determinista: solo usa ``kind`` (nunca ``LLMError.message`` crudo del
proveedor), así que no puede filtrar secretos, cabeceras ni cuerpos (RNF-018).
Importable y testeable sin Qt.
"""

from __future__ import annotations

from sirius.ports.llm import LLMErrorKind

_GENERIC_MESSAGE = "No se pudo completar el envío. Inténtalo de nuevo."

_MESSAGES_BY_KIND: dict[LLMErrorKind, str] = {
    LLMErrorKind.AUTHENTICATION: ("La clave de API no es válida. Revísala en Configuración."),
    LLMErrorKind.PERMISSION: (
        "La cuenta o la clave no tiene permiso para usar este modelo. Revisa el proveedor."
    ),
    LLMErrorKind.RATE_LIMITED: (
        "Demasiadas peticiones seguidas. Espera un momento y vuelve a intentarlo."
    ),
    LLMErrorKind.CONNECTION: ("Sin conexión con el proveedor. Revisa tu red e inténtalo de nuevo."),
    LLMErrorKind.TIMEOUT: ("El proveedor tardó demasiado en responder. Inténtalo de nuevo."),
    LLMErrorKind.INVALID_RESPONSE: (
        "El proveedor devolvió una respuesta no válida. Inténtalo de nuevo."
    ),
    LLMErrorKind.BUDGET_EXCEEDED: ("Alcanzaste el límite de gasto mensual configurado."),
    LLMErrorKind.CONFIGURATION: (
        "El proveedor de IA no está configurado. Configúralo en Configuración."
    ),
    LLMErrorKind.UNKNOWN: _GENERIC_MESSAGE,
}


def describe_error(error_kind: LLMErrorKind | None) -> str:
    """Devuelve el mensaje accionable para ``error_kind``.

    ``None`` (por ejemplo, un fallo inesperado sin clasificar del worker)
    recibe el mismo mensaje genérico seguro que ``LLMErrorKind.UNKNOWN``. Un
    valor de enum sin entrada en ``_MESSAGES_BY_KIND`` lanza ``KeyError`` en
    vez de caer en silencio al genérico, para que un valor nuevo del enum
    obligue a añadir su mensaje aquí.
    """
    if error_kind is None:
        return _GENERIC_MESSAGE
    return _MESSAGES_BY_KIND[error_kind]


def failed_send_message(error_kind: LLMErrorKind | None, operation_id: str | None) -> str:
    """Mensaje completo para la etiqueta de error, con la referencia de soporte."""
    return f"{describe_error(error_kind)} (ref: {operation_id})"
