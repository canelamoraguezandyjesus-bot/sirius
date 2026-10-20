"""Lo que recuerda haber visto, como texto: quién vino, a qué hora y quién se fue (pieza G
de la 0.4, ADR-265).

La vista le dice, en cada fotograma, quién es cada cara que ve: su nombre si dio permiso
para que la reconozca, o nadie. De eso saca los cambios y los apunta, con su hora:

- **Alguien llega** cuando se le ve ``ARRIVE_SECONDS`` seguidos, y **se va** cuando lleva
  ``LEAVE_SECONDS`` sin vérsele: un parpadeo de la cámara, o alguien que se gira un
  momento, no es un cambio. La hora es la del primer fotograma con él, o sin él.
- **Lo primero que ve al abrir la cámara**, en cuanto lleva ``ARRIVE_SECONDS`` igual, no es
  que haya llegado nadie: se apunta como quien ya estaba. Al perder la cámara, no se sabe
  quién se fue, y se empieza de nuevo al volver a ver.
- **De los desconocidos se cuenta cuántos hay**: sin permiso no hay nombre ni nada que los
  distinga, así que dos sin identificar son dos, sin saber cuál es cuál.
- **Lo apuntado lo lee la charla**, una línea por cambio de las últimas ``REMEMBER``, las
  ``MOST_LINES`` más nuevas; lo de antes se borra al apuntar, al leer y, mientras Sirius
  está abierto, cada ``TIDY_EVERY`` desde el hilo de la vista, vea o no: no depende de que
  cambie nada ni de que la charla lo lea (ronda 1 de Codex sobre la PR #703). En ese mismo
  repaso se quita el nombre de quien ya no tiene permiso, si quitarlo falló en su momento
  (ronda 5).
- **Quien quita su permiso** deja de tener nombre en lo apuntado y en lo que se está
  mirando: pasa a ser alguien sin identificar, sin que se apunte que se fue; y lo que la
  vista reconoció de él justo antes, si llega después, también (ronda 3 de Codex sobre la
  PR #703). Y al leerlo, un nombre de quien ya no tiene permiso, porque algo falló al
  quitárselo, se lee como alguien sin identificar y se quita entonces: el modelo nunca lo
  lee.
"""

from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta

from sirius.infrastructure.logging import get_logger
from sirius.ports.sight_log import Change, SeenChange, SightLogStore

_logger = get_logger(__name__)

#: Lo que hay que ver a alguien seguido para que haya llegado, en segundos.
ARRIVE_SECONDS = 3.0
#: Lo que hay que llevar sin verle para que se haya ido, en segundos.
LEAVE_SECONDS = 20.0
#: Lo que se recuerda, y se le dice al modelo; lo de antes se borra.
REMEMBER = timedelta(hours=24)
#: Las líneas que se le dicen como mucho, las más nuevas.
MOST_LINES = 30
#: Cada cuánto, como mucho, se borra lo de antes de ``REMEMBER`` desde el hilo de la vista.
TIDY_EVERY = timedelta(minutes=1)
#: El título de la sección y lo que dice antes de las líneas.
HEADING = "# Lo que has visto"
INTRO = "Lo que has visto con la cámara en las últimas 24 horas, con su hora:"
#: Cómo se nombra a quien no se sabe quién es.
SOMEONE = "alguien sin identificar"
#: Cómo se dice cada cambio.
CAME_LINE = "{when} vino {who}."
LEFT_LINE = "{when} se fue {who}."
THERE_LINE = "{when}, al abrir los ojos, estaba delante {who}."


@dataclass(slots=True)
class _Pending:
    """Un cambio que aún no se da por hecho: desde cuándo, en el reloj de la vista y en el
    de pared, y cuántos se ven de esa persona mientras tanto, lo que menos al llegar o lo
    que más al irse."""

    since: float
    at: datetime
    level: int


class SightLog:
    """Lo que recuerda haber visto: saca los cambios de lo que ve la vista y los apunta."""

    def __init__(
        self,
        store: SightLogStore,
        *,
        allowed: Callable[[], Collection[str]],
        wall_clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        arrive_seconds: float = ARRIVE_SECONDS,
        leave_seconds: float = LEAVE_SECONDS,
    ) -> None:
        self._store = store
        #: Quiénes tienen permiso para que se les reconozca, que son los únicos con nombre.
        self._allowed = allowed
        self._wall_clock = wall_clock
        self._arrive = arrive_seconds
        self._leave = leave_seconds
        #: Lo que se cambia y se apunta desde el hilo de la vista y desde quien quita un
        #: permiso: con él, un cambio con su nombre no se apunta después de quitárselo.
        self._lock = threading.Lock()
        #: Quiénes tiene delante, dados por hechos; ``None`` hasta lo primero que ve.
        self._there: Counter[str | None] | None = None
        #: Lo que ve igual desde que abrió la cámara, hasta darlo por lo primero.
        self._first: tuple[float, datetime, Counter[str | None]] | None = None
        self._coming: dict[str | None, _Pending] = {}
        self._going: dict[str | None, _Pending] = {}
        self._failed = False
        #: Cuándo se borró lo viejo desde el hilo de la vista; ``None`` si aún no.
        self._tidied_at: datetime | None = None

    def see(self, now: float, names: Sequence[str | None]) -> None:
        """Lo que ve la vista en un fotograma, en el instante ``now`` de su reloj: quién es
        cada cara, su nombre o ``None``. Apunta los cambios que ya se dan por hechos. Un
        fallo al apuntar se dice una vez, con su tipo, y no para la vista.

        El nombre de quien ya no tiene permiso, porque se lo ha quitado mientras la vista le
        reconocía, es alguien sin identificar: se mira con el cerrojo con el que se quita,
        así que no se apunta después de quitárselo (ronda 3 de Codex sobre la PR #703)."""
        with self._lock:
            allowed = set(self._allowed())
            seen: Counter[str | None] = Counter(who if who in allowed else None for who in names)
            changes = self._changes(now, self._wall_clock(), seen)
            if changes:
                self._write(changes)

    def tidy(self) -> None:
        """Borra lo apuntado antes de ``REMEMBER``, y el nombre de quien ya no tiene permiso,
        como mucho cada ``TIDY_EVERY``. Lo pide la vista en cada vuelta, vea o no: así lo
        viejo se va aunque no cambie nada delante ni la charla lo lea, y un nombre que no se
        pudo quitar al quitar el permiso se quita en el siguiente repaso, también tras cerrar
        y volver a abrir (ronda 5 de Codex sobre la PR #703). Si la hora de este ordenador
        vuelve atrás, se borra igual."""
        now = self._wall_clock()
        with self._lock:
            tidied_at = self._tidied_at
            if tidied_at is not None and timedelta(0) <= now - tidied_at < TIDY_EVERY:
                return
            self._tidied_at = now
        self._drop_old(now)
        try:
            seen = self._store.since(now - REMEMBER)
        except Exception as error:
            self._forget_failed(error)
            return
        self._forget_without_permission(seen)

    def pause(self) -> None:
        """La vista ha dejado de ver: no se sabe quién se va, y al volver a ver se empieza
        de nuevo, con lo primero que vea."""
        with self._lock:
            self._there, self._first = None, None
            self._coming.clear()
            self._going.clear()

    def forget(self, who: str) -> None:
        """``who`` quita su permiso: en lo apuntado y en lo que se está mirando pasa a ser
        alguien sin identificar, y no se apunta que se fue."""
        with self._lock:
            if self._there is not None and who in self._there:
                self._there[None] += self._there.pop(who)
            if self._first is not None and who in self._first[2]:
                self._first[2][None] += self._first[2].pop(who)
            self._coming.pop(who, None)
            self._going.pop(who, None)
            self._store.forget(who)

    def lines(self) -> tuple[str, ...]:
        """Lo que se le dice al modelo: los cambios de las últimas ``REMEMBER``, como texto,
        del más viejo al más nuevo, los ``MOST_LINES`` más nuevos. El nombre de quien ya no
        tiene permiso se lee como alguien sin identificar, y se quita de lo apuntado. Antes
        de leer, se borra lo de antes de ``REMEMBER``."""
        now = self._wall_clock()
        self._drop_old(now)
        seen = self._store.since(now - REMEMBER)[-MOST_LINES:]
        stale = self._forget_without_permission(seen)
        today = now.astimezone().date()
        return tuple(
            _line(change if change.who not in stale else replace(change, who=None), today)
            for change in seen
        )

    def _forget_without_permission(self, seen: Sequence[SeenChange]) -> set[str]:
        """Quita de lo apuntado el nombre de quien, en ``seen``, ya no tiene permiso, y
        devuelve esos nombres. Un fallo al quitarlo se dice una vez, con su tipo."""
        allowed = set(self._allowed())
        stale = {change.who for change in seen if change.who is not None} - allowed
        for who in sorted(stale):
            try:
                self.forget(who)
            except Exception as error:
                self._forget_failed(error)
        return stale

    def _forget_failed(self, error: Exception) -> None:
        if not self._failed:
            self._failed = True
            _logger.error(
                "No se pudo quitar un nombre de lo que ha visto (%s)", type(error).__name__
            )

    def _changes(self, now: float, wall: datetime, seen: Counter[str | None]) -> list[SeenChange]:
        there = self._there
        if there is None:
            first = self._first
            if first is None or first[2] != seen:
                self._first = (now, wall, seen)
                return []
            if now - first[0] < self._arrive:
                return []
            self._there, self._first = Counter(seen), None
            return [
                SeenChange(first[1], Change.THERE, who)
                for who, count in sorted(seen.items(), key=_order)
                for _ in range(count)
            ]
        changes: list[SeenChange] = []
        # También quien estaba llegando o yéndose y en este fotograma no se ve.
        everyone = set(seen) | set(there) | set(self._coming) | set(self._going)
        for who in sorted(everyone, key=lambda name: _order((name, 0))):
            changes.extend(self._one(now, wall, who, seen[who]))
        return changes

    def _one(self, now: float, wall: datetime, who: str | None, seen: int) -> list[SeenChange]:
        """Los cambios de ``who``, que se ve ``seen`` veces en este fotograma."""
        there = self._there
        assert there is not None
        known = there[who]
        if seen <= known:
            self._coming.pop(who, None)
        else:
            coming = self._coming.setdefault(who, _Pending(now, wall, seen))
            coming.level = min(coming.level, seen)
            if now - coming.since >= self._arrive:
                del self._coming[who]
                there[who] = coming.level
                return [SeenChange(coming.at, Change.CAME, who)] * (coming.level - known)
        if seen >= known:
            self._going.pop(who, None)
        else:
            going = self._going.setdefault(who, _Pending(now, wall, seen))
            going.level = max(going.level, seen)
            if now - going.since >= self._leave:
                del self._going[who]
                there[who] = going.level
                if not there[who]:
                    del there[who]
                return [SeenChange(going.at, Change.LEFT, who)] * (known - going.level)
        return []

    def _write(self, changes: Sequence[SeenChange]) -> None:
        try:
            self._store.add(changes)
            self._store.drop_before(self._wall_clock() - REMEMBER)
        except Exception as error:
            if not self._failed:
                self._failed = True
                _logger.error("No se pudo apuntar lo que ha visto (%s)", type(error).__name__)

    def _drop_old(self, now: datetime) -> None:
        """Borra lo apuntado antes de ``REMEMBER``. Un fallo se dice una vez, con su tipo, y
        lo apuntado se lee igual."""
        try:
            self._store.drop_before(now - REMEMBER)
        except Exception as error:
            if not self._failed:
                self._failed = True
                _logger.error(
                    "No se pudo borrar lo que ha visto hace más de un día (%s)",
                    type(error).__name__,
                )


def sight_block(lines: Sequence[str]) -> str:
    """La sección «# Lo que has visto»; vacía si no hay nada."""
    if not lines:
        return ""
    return "\n".join([HEADING, INTRO, *lines])


def _order(item: tuple[str | None, int]) -> tuple[bool, str]:
    """Primero los que tienen nombre, por orden, y después los que no."""
    who = item[0]
    return (who is None, who or "")


def _line(seen: SeenChange, today: date) -> str:
    local = seen.at.astimezone()
    when = f"A las {local:%H:%M}" if local.date() == today else f"Ayer, a las {local:%H:%M}"
    who = seen.who if seen.who is not None else SOMEONE
    template = {Change.CAME: CAME_LINE, Change.LEFT: LEFT_LINE, Change.THERE: THERE_LINE}
    return template[seen.change].format(when=when, who=who)
