"""Puerto del intérprete de la pregunta (ADR-164, palanca 1 de ADR-148).

``Protocol`` de un solo método, deliberadamente más estrecho que
``LLMProvider``: como ``CategoryClassifierPort`` y ``RelevanceFilterPort``,
solo lo implementa un adaptador de modelo LOCAL
(``OllamaQueryIntentClassifierAdapter``) — el proveedor de pago nunca
interviene aquí (D7 punto 5), porque la consulta del usuario no sale de la
máquina para decidir cómo buscar en su propia memoria.
"""

from __future__ import annotations

from typing import Protocol

from sirius.domain.query_intent import IntencionDeConsulta

__all__ = ["QueryIntentClassifierPort"]


class QueryIntentClassifierPort(Protocol):
    """Infiere de una consulta el modo, la cardinalidad, el límite y el
    tiempo que la pregunta declara.

    Nunca propaga una excepción: cualquier fallo interno (modelo no
    instalado, conexión rechazada, tiempo agotado, respuesta fuera del
    vocabulario cerrado) se informa devolviendo ``None`` —«no he podido
    decidir»—, exactamente como ``CategoryClassifierPort``. El llamador
    (``InterpreteDePeticion``) se apoya en eso para caer, sin ``try``/
    ``except`` propio, en la política uniforme de siempre.
    """

    def classify_intent(self, query_text: str) -> IntencionDeConsulta | None:
        """Devuelve la intención inferida, o ``None`` si no pudo decidirla."""
        ...
