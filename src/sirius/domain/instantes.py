"""Una sola forma para comparar instantes (ADR-229, deuda 20 de la bitácora).

El repositorio escribe los instantes de dos maneras: ``created_at`` llega de
SQLite como ``str(datetime)`` —``2026-03-20 09:00:00.000000``, separador
espacio y seis dígitos de fracción— y el corpus, el intérprete y el
clasificador escriben ``2026-03-20T00:00:00Z``. La puerta ``G8`` comparaba
esas cadenas por orden léxico, y el espacio (0x20) ordena antes que la ``T``
(0x54) igual que el ``+`` de ``+00:00`` antes que la ``Z``: dos escrituras del
mismo instante admitían conjuntos distintos, y cada comparación nueva era «una
tirada de dados» (bitácora, entrada 69). Hasta hoy se parcheaba al EMISOR —cada
uno reescribía su instante en la forma del otro lado— porque el comparador no
se podía tocar desde los encargos.

Este módulo es el comparador. No cambia el contrato (``created_at: str``) ni
lo que nadie escribe: lleva cualquier escritura reconocible a UNA forma
canónica, UTC y de ancho fijo, en la que el orden léxico ES el orden
cronológico, y la puerta compara eso. Un texto que no es un instante se
devuelve tal cual y se compara así contra la forma canónica del otro lado: su
veredicto sigue sin estar definido, como antes, y ningún emisor lo produce
(el clasificador filtra con su patrón ISO); lo que no pasa es que una
excepción tumbe la puerta por un dato ilegible.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Final

#: UTC, ancho fijo (27 caracteres): el orden léxico coincide con el cronológico.
FORMA_CANONICA: Final = "%Y-%m-%dT%H:%M:%S.%fZ"

#: Una fecha ISO y, opcionalmente, una hora tras ``T`` o espacio; lo que venga
#: detrás lo juzga ``fromisoformat``. Sin este filtro ``fromisoformat`` acepta
#: cualquier carácter como separador y leería ``2026-03-20+02:00`` como las
#: dos de la madrugada en UTC, que no es lo que nadie escribió.
_FORMA_RECONOCIBLE: Final = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\S+)?")


def en_forma_canonica(texto: str) -> str | None:
    """La escritura canónica del instante, o ``None`` si el texto no es uno.

    Reconoce una fecha ISO con hora opcional tras ``T`` o espacio, fracción
    opcional de cualquier longitud (se trunca a seis dígitos) y zona opcional
    (``Z`` o un desfase): el ``str(datetime)`` de SQLite, el ISO del corpus y
    una fecha sola, que es la medianoche de ese día. Sin zona se asume UTC,
    que es lo que todo el canon escribe; con zona se convierte a UTC, porque
    comparar dos desfases distintos sería comparar dos relojes. Un instante
    que al convertirse se sale del rango representable (``0001-01-01`` con
    desfase positivo, ``9999-12-31`` con desfase negativo) tampoco es
    utilizable, y es ``None`` como cualquier otro texto ilegible.
    """
    limpio = texto.strip()
    if not _FORMA_RECONOCIBLE.fullmatch(limpio):
        return None
    try:
        momento = datetime.fromisoformat(limpio)
        en_utc = momento.replace(tzinfo=UTC) if momento.tzinfo is None else momento.astimezone(UTC)
        return en_utc.strftime(FORMA_CANONICA)
    except ValueError, OverflowError:
        return None


def comparable(texto: str) -> str:
    """Lo que se compara: la forma canónica si el texto es un instante; si no, el texto."""
    canonica = en_forma_canonica(texto)
    return canonica if canonica is not None else texto
