"""A quién le hablan: a Sirius, si dice su nombre o mientras dura la charla (ADR-244).

PA-R03-06, en la pieza D de la 0.3: con su nombre, siempre; sin su nombre, solo mientras
dura la charla, que empieza cada vez que Sirius calla y dura ``CONVERSATION_SECONDS``. Lo
demás no es para él, y el oído lo descarta antes de la charla.

- **Su nombre, sin distinguir mayúsculas**, como palabra suelta: «Sirius», «sirius» o
  «¿Y tú qué opinas, Sirius?». Si el transcriptor lo escribe de otra forma, no es para
  él; lo mide E-R03-05 en su ordenador.
- **La charla cuenta desde que Sirius calla** hasta que empieza a oírse la voz del turno
  siguiente: lo que empezó a decir dentro, aunque acabe fuera, es para él. Lo que empezó
  antes de que callara no es de ella: si atendiendo un turno no dijo nada, la charla
  empieza al acabarlo, y lo que sonó mientras tanto ya había empezado (ronda 1 de Codex
  sobre la PR #689). La hora es la del micro al captarlo, no la del oído al leerlo.
- **Cada vez que Sirius calla empieza otra charla.** Con la tele hablando sin pausa, lo
  que diga dentro de una se toma por él, y su respuesta abre la siguiente: nada de aquí
  lo distingue, y se dice en ADR-244.
"""

from __future__ import annotations

import re

#: Lo que dura la charla desde que Sirius calla: sin su nombre, lo que empiece a oírse
#: hasta entonces es para él. PA-R03-06 lo deja entre 5 s y 2 min; con 10 s, corta para
#: que la tele entre poco y larga para contestarle sin repetir su nombre.
CONVERSATION_SECONDS = 10.0

_NAME = re.compile(r"\bsirius\b", re.IGNORECASE)


def says_his_name(text: str) -> bool:
    """Si ``text`` dice «Sirius», sin distinguir mayúsculas, como palabra suelta."""
    return _NAME.search(text) is not None


class Addressing:
    """Lleva la charla y decide si lo oído es para Sirius.

    El oído le dice cuándo calla Sirius (``fell_silent``) y le pregunta por cada turno
    (``is_for_sirius``), con la hora en que empezó a oírse su voz, medida con el mismo
    reloj.
    """

    def __init__(self, *, conversation_seconds: float = CONVERSATION_SECONDS) -> None:
        self.conversation_seconds = conversation_seconds
        self._quiet_since: float | None = None

    def fell_silent(self, at: float) -> None:
        """Sirius acaba de callar: desde ``at`` corre la charla."""
        self._quiet_since = at

    def is_for_sirius(self, heard: str, began: float) -> bool:
        """Si lo oído, que empezó a oírse en ``began``, es para él: con su nombre, o dentro
        de la charla. Antes de que Sirius haya hablado no hay charla, y lo que empezó antes
        de que callara no es de ella."""
        if says_his_name(heard):
            return True
        return (
            self._quiet_since is not None
            and 0 <= began - self._quiet_since <= self.conversation_seconds
        )
