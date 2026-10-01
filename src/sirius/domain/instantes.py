"""Una sola forma para comparar instantes (ADR-229, deuda 20 de la bitácora).

El repositorio escribe los instantes de dos maneras: ``created_at`` llega de
SQLite como ``str(datetime)`` —``2026-03-20 09:00:00.000000``, separador
espacio, y sin fracción cuando los microsegundos son cero— y el corpus, el
intérprete y el clasificador escriben ``2026-03-20T00:00:00Z``. La puerta
``G8`` comparaba esas cadenas por orden léxico, y el espacio (0x20) ordena
antes que la ``T`` (0x54) igual que el ``+`` de ``+00:00`` antes que la ``Z``:
dos escrituras del mismo instante admitían conjuntos distintos, y cada
comparación nueva era «una tirada de dados» (bitácora, entrada 69). Hasta hoy
se parcheaba al EMISOR —cada uno reescribía su instante en la forma del otro
lado— porque el comparador no se podía tocar desde los encargos.

Este módulo es el comparador. No cambia el contrato (``created_at: str``) ni
lo que nadie escribe: lleva cualquier escritura reconocible a UNA forma
canónica, UTC y de ancho fijo, en la que el orden léxico ES el orden
cronológico, y la puerta compara eso. Un texto que no es un instante se
devuelve tal cual: se compara como hoy, para que un dato ilegible no tumbe la
puerta ni se cuele por una excepción.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

#: UTC, ancho fijo (27 caracteres): el orden léxico coincide con el cronológico.
FORMA_CANONICA: Final = "%Y-%m-%dT%H:%M:%S.%fZ"


def en_forma_canonica(texto: str) -> str | None:
    """La escritura canónica del instante, o ``None`` si el texto no es uno.

    Reconoce lo que ``datetime.fromisoformat`` reconoce más el sufijo ``Z``:
    el ``str(datetime)`` de SQLite con y sin microsegundos, ISO-8601 con ``T``,
    ``Z`` o desfase, y una fecha sola (que es la medianoche de ese día). Sin
    zona se asume UTC, que es lo que todo el canon escribe; con zona se
    convierte a UTC, porque comparar dos desfases distintos sería comparar dos
    relojes.
    """
    try:
        momento = datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    en_utc = momento.replace(tzinfo=UTC) if momento.tzinfo is None else momento.astimezone(UTC)
    return en_utc.strftime(FORMA_CANONICA)


def comparable(texto: str) -> str:
    """Lo que se compara: la forma canónica si el texto es un instante; si no, el texto."""
    canonica = en_forma_canonica(texto)
    return canonica if canonica is not None else texto
