"""El texto de un mensaje de la charla según cómo acabó (ADR-242).

Lo enseñan igual la ventana y la orden de consola ``sirius-oye``: una respuesta que no
acabó bien, con lo que llegó a escribir y la marca de cómo acabó, y una borrada, con su
marca. Puro y sin Qt, para que la consola no lo copie a mano (ronda 13 de Codex sobre la
PR #687).
"""

from __future__ import annotations

from sirius.domain.conversation import MessageStatus

__all__ = ["CANCELLED_SEND", "message_body"]

#: Lo que se dice cuando un envío se cancela.
CANCELLED_SEND = "Envío cancelado."


def message_body(content: str | None, status: MessageStatus) -> str:
    """El texto que se enseña de un mensaje: el suyo, con la marca de cómo acabó."""
    suffix = {
        MessageStatus.CANCELLED: " (cancelado)",
        MessageStatus.FAILED: " (fallido)",
    }.get(status, "")
    # REDACTED (B4d) is the only status whose content is ever None: the
    # placeholder replaces it instead of literally rendering "None".
    shown_content = "(mensaje redactado)" if status is MessageStatus.REDACTED else content
    return f"{shown_content}{suffix}"
