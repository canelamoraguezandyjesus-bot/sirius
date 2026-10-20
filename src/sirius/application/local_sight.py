"""La vista del robot: la cámara y las caras, en este ordenador (pieza D de la 0.4, ADR-262).

Lee la cámara, busca las caras y recuerda lo visto unos segundos: de cada cara, dónde está,
si mueve la boca, si mira a la cámara y, desde la pieza E (ADR-263), quién es, si dio
permiso para que la reconozca, y desde la F (ADR-264), la edad que aparenta. Con eso dice
a quién mirar, si quien habla le mira y a quiénes tiene delante, con su edad, que es lo
que leen la cara, el oído y la charla. Ningún fotograma ni
recorte sale de aquí ni se guarda: el fotograma se suelta en cuanto el detector lo ha
mirado, el recorte de cada cara solo lo leen quien reconoce y quien estima la edad, en el
acto, y lo recordado son números y nombres.

- **La atiende un hilo**, como al oído (``SightLoop``), unas diez veces por segundo; la
  cara y el oído la leen sin esperarla, de lo último que vio.
- **Sin cámara, lo dice y sigue**: si falta lo que instala la orden, si no hay cámara o la
  tiene otro programa, o si deja de dar imagen, como al desenchufarla, ``notice`` dice por
  qué, y Sirius sigue oyendo y hablando. El diario se queda con el tipo de fallo.
- **Lo que no puede leer no la para**: un fotograma que el detector no entiende se deja, y
  se apunta una vez; un fallo de quien reconoce, igual, y esa vez nadie es reconocido.
- **Lo que sabe de quién hay vale lo que el último fotograma que pudo leer**: al abrir la
  cámara, en la vuelta que no lee fotograma o en la que el detector falla, y mientras mira
  quiénes son y qué edad tienen las caras nuevas, no sabe quién hay: no lo dice, y la edad
  de quien haya es duda; lo que recordaba de cada cara se olvida (ronda 2 de Codex sobre
  la PR #703). Y lo deja de una vez, en una sola foto (``_View``), que quien la lee
  comprueba al leerla: que sea de hace como mucho ``FRESH_SECONDS`` y, los nombres, que
  nadie haya dado ni quitado su permiso desde que se reconocieron; si no, tampoco sabe
  quién hay (ronda 3).
- **Reconocer cuesta**: cada cara se reconoce al aparecer y después cada
  ``RECOGNIZE_AGAIN_SECONDS``, siguiéndola por dónde está mientras se la vea sin hueco: un
  fotograma sin nadie, o más de ``SAME_FACE_GAP_SECONDS`` sin mirar, y la que aparezca
  después se reconoce de nuevo, aunque sea en el mismo sitio (ronda 1 de Codex sobre la
  PR #703). Si alguien da o quita su permiso, se vuelve a mirar a todos. Y cuando alguien
  está dando permiso, su cara, si está sola delante, va a quien reconoce.
- **La edad, igual**: desde la pieza F (ADR-264), la que aparenta cada cara se estima al
  aparecer y después cada ``RECOGNIZE_AGAIN_SECONDS``, y se recuerda en números, con si se
  lee segura. Un fallo al estimarla es no saberla, que es duda.
- **Lo que ve, como texto**: desde la pieza G (ADR-265), quién es cada cara de cada
  fotograma va a quien recuerda lo que ve, que saca de ahí quién llega y quién se va; al
  dejar de ver, se le dice, que no sabe quién se fue.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol

from sirius.infrastructure.logging import get_logger
from sirius.ports.age import AgeReading
from sirius.ports.local_sight import CameraUnavailable, SightEngines, SightUnavailable

_logger = get_logger(__name__)

#: Cuánto recuerda de lo que vio, en segundos: más que un turno largo.
MEMORY_SECONDS = 30.0
#: Lo que dice si no puede ver porque falta lo que ve o no carga, con la orden que lo
#: instala y lo que hace, como el oído.
CANNOT_SEE = (
    "No puedo verte: {reason}. Ejecuta en PowerShell, dentro de la carpeta de Sirius: "
    "{command} . Instala o pone al día lo que falte de la voz y de la vista y, si el "
    "problema es otro, te dice cuál. Sigo oyéndote y hablando."
)
#: Lo que dice si no tiene cámara, o si la ha perdido.
NO_CAMERA = "Sin cámara: {reason}. Sigo oyéndote y hablando."
#: Cada cuánto vuelve a reconocer una cara que sigue delante, en segundos.
RECOGNIZE_AGAIN_SECONDS = 2.0
#: Lo lejos que puede estar una cara de donde estaba para ser la misma, de 0 a 1.
SAME_PLACE = 0.15
#: Lo más que puede pasar sin mirarla para que una cara sea la misma, en segundos: la vista
#: mira unas diez veces por segundo, y con un hueco mayor no se sabe quién ha entrado.
SAME_FACE_GAP_SECONDS = 0.5
#: Lo más viejo que puede ser el último fotograma que leyó para decir quién hay, en
#: segundos: la vista mira unas diez veces por segundo, y si lleva más sin poder mirar,
#: porque la cámara se ha colgado o el hilo va lento, no sabe quién ha entrado. Es más que
#: una vuelta en la que vuelve a reconocer a varios, que no pone en duda a quien sigue.
FRESH_SECONDS = 1.0


class FaceRecognizer(Protocol):
    """Lo que la vista necesita de quien reconoce caras (pieza E de la 0.4, ADR-263)."""

    @property
    def version(self) -> int:
        """Cambia cada vez que alguien da o quita su permiso."""
        ...

    def wants_face(self) -> bool:
        """Si espera la cara de quien está dando permiso."""
        ...

    def take_face(self, crop: Any) -> None:
        """La cara de quien da permiso, sola delante."""
        ...

    def who_by_face(self, crop: Any) -> str | None:
        """De quién es la cara de ``crop``, o ``None`` si de nadie que diera permiso."""
        ...


class SeenNames(Protocol):
    """Lo que la vista necesita de quien recuerda lo que ve (pieza G de la 0.4, ADR-265)."""

    def see(self, now: float, names: Sequence[str | None]) -> None:
        """Quién es cada cara del fotograma de ``now``, su nombre o ``None``."""
        ...

    def pause(self) -> None:
        """Ha dejado de ver."""
        ...

    def tidy(self) -> None:
        """Borra lo que recuerda de hace demasiado: se le pide en cada vuelta, vea o no."""
        ...


class AgeOf(Protocol):
    """Lo que la vista necesita de quien estima la edad (pieza F de la 0.4, ADR-264)."""

    def estimate(self, crop: Any) -> AgeReading | None:
        """La edad que aparenta la cara de ``crop``; ``None`` si no se puede estimar."""
        ...


@dataclass(frozen=True, slots=True)
class Glimpse:
    """Lo que vio de una cara en un fotograma, sin nada de la imagen: dónde está, de 0 a 1
    con la izquierda y la derecha de la cámara, si movía la boca, si le miraba, quién es,
    su nombre si dio permiso para que la reconozca, si no, ``None``; y la edad que aparenta,
    ``None`` si no se sabe."""

    x: float
    talking: bool
    looking: bool
    who: str | None = None
    age: AgeReading | None = None


@dataclass(frozen=True, slots=True)
class _View:
    """Lo que sabe de quién hay, de una vez: si ve; si sabe quién hay; el momento del último
    fotograma que pudo leer entero, con qué versión de los permisos reconoció sus caras y
    lo que vio de cada una. Se cambia entero y se lee de una sola vez: quien lo lee desde
    otro hilo no junta lo de dos momentos (ronda 3 de Codex sobre la PR #703)."""

    seeing: bool = False
    known: bool = False
    at: float = 0.0
    version: int = -1
    faces: tuple[Glimpse, ...] = ()


class LocalSight:
    """La vista: la cámara, el detector de caras y lo que vio los últimos segundos."""

    def __init__(
        self,
        *,
        load_engines: Callable[[], SightEngines[Any, Any]],
        clock: Callable[[], float],
        install_command: str,
        memory_seconds: float = MEMORY_SECONDS,
        recognition: FaceRecognizer | None = None,
        ages: AgeOf | None = None,
        log: SeenNames | None = None,
    ) -> None:
        self._load_engines = load_engines
        #: Quien reconoce caras; sin él, nadie es nadie.
        self._recognition = recognition
        self._recognition_failed = False
        #: De quién era cada cara la última vez que se reconoció: dónde estaba, quién era,
        #: cuándo se reconoció y cuándo se vio por última vez; y con qué versión de los
        #: permisos. Solo lo toca el hilo de la vista, como ``_aged``.
        self._known: tuple[tuple[float, str | None, float, float], ...] = ()
        self._known_version = -1
        #: Quien estima la edad; sin él, no se mira.
        self._ages = ages
        self._ages_failed = False
        #: La edad de cada cara la última vez que se estimó: dónde estaba, qué edad, cuándo
        #: se estimó y cuándo se vio por última vez.
        self._aged: tuple[tuple[float, AgeReading | None, float, float], ...] = ()
        #: De qué vez que abrió la cámara son ``_known`` y ``_aged``.
        self._cache_session = 0
        #: Quien recuerda lo que ve; sin él, no se recuerda.
        self._log = log
        self._log_failed = False
        self._install_command = install_command
        self._clock = clock
        self._memory = memory_seconds
        self._engines: SightEngines[Any, Any] | None = None
        #: La cámara y su estado, desde el hilo que sea.
        self._lock = threading.Lock()
        self._seeing = False
        #: Cuántas veces ha abierto la cámara: lo que mira una vuelta de una vez anterior no
        #: se deja como de esta.
        self._session = 0
        #: Lo que sabe de quién hay (``_View``): se cambia entero, con el cerrojo, y se lee
        #: sin él, de una sola vez.
        self._view = _View()
        self._notice = ""
        self._detector_failed = False
        #: Lo visto, del más viejo al más nuevo: cada fotograma con su momento. Se cambia
        #: entero de una vez, así que se lee sin el cerrojo.
        self._history: tuple[tuple[float, tuple[Glimpse, ...]], ...] = ()

    @property
    def seeing(self) -> bool:
        """Si tiene la cámara abierta y ve."""
        return self._seeing

    @property
    def notice(self) -> str:
        """Por qué no ve, para la ventana; vacío si ve o si aún no ha empezado."""
        return self._notice

    @property
    def tools(self) -> tuple[str, ...]:
        """Con qué ve, una vez cargado: el nombre de su detector de caras."""
        engines = self._engines
        return () if engines is None else (engines.detector.name,)

    def start(self) -> str:
        """Carga lo que ve, si no estaba, y abre la cámara. Devuelve el aviso: vacío si ve."""
        with self._lock:
            if self._seeing:
                return ""
            if self._engines is None:
                try:
                    self._engines = self._load_engines()
                except SightUnavailable as error:
                    _logger.info("La vista no arranca: %s", error.reason)
                    self._notice = CANNOT_SEE.format(
                        reason=error.reason, command=self._install_command
                    )
                    return self._notice
            try:
                self._engines.camera.open()
            except CameraUnavailable as error:
                _logger.info("Sin cámara: %s", error.reason)
                self._notice = NO_CAMERA.format(reason=error.reason)
                return self._notice
            self._seeing = True
            # Hasta el primer fotograma que lea, no sabe quién hay; y lo que recordaba de
            # cada cara, de cuando veía antes, no vale: lo olvida el hilo de la vista.
            self._session += 1
            self._view = _View(seeing=True)
            self._notice = ""
            return ""

    def stop(self) -> None:
        """Suelta la cámara. Lo visto se queda, para quien aún lo lea."""
        with self._lock:
            if self._engines is not None and self._seeing:
                self._engines.camera.close()
            self._seeing = False
            self._view = _View()
        self._paused()

    def look(self) -> None:
        """Mira una vez: lee la cámara, busca las caras y lo apunta con su momento. Si la
        cámara deja de dar imagen, la suelta y lo dice. Antes, vea o no, le pide a quien
        recuerda lo que ve que borre lo de hace demasiado (ronda 1 de Codex sobre la PR
        #703)."""
        self._tidy()
        with self._lock:
            if not self._seeing or self._engines is None:
                return
            engines = self._engines
            session = self._session
            try:
                frame = engines.camera.read()
            except CameraUnavailable as error:
                _logger.warning("La cámara ha dejado de dar imagen: %s", error.reason)
                engines.camera.close()
                self._seeing = False
                self._view = _View()
                self._notice = NO_CAMERA.format(reason=error.reason)
                self._paused()
                return
        if session != self._cache_session:
            # Lo que recordaba de cada cara es de antes de volver a abrir la cámara.
            self._known, self._aged, self._cache_session = (), (), session
        if frame is None:
            self._doubt()
            return
        try:
            faces = engines.detector.detect(frame)
        except Exception as error:
            self._doubt()
            if not self._detector_failed:
                self._detector_failed = True
                _logger.error("El detector de caras ha fallado (%s)", type(error).__name__)
            return
        finally:
            del frame
        now = self._clock()
        # Los permisos, antes de reconocer: lo que se reconozca vale para estos, y si alguien
        # da o quita el suyo mientras tanto, quien lo lea no lo da por actual.
        version = self._permissions()
        if not self._all_followed(faces, now):
            # Mientras mira quiénes son y qué edad tienen las caras nuevas, que puede tardar
            # (la primera vez, cargar los modelos), no sabe quién hay.
            self._doubt(forget=False)
        names = self._identify(faces, now, version)
        ages = self._age(faces, now)
        seen = tuple(
            Glimpse(face.x, face.talking, face.looking, who, age)
            for face, who, age in zip(faces, names, ages, strict=True)
        )
        kept = tuple(entry for entry in self._history if now - entry[0] <= self._memory)
        self._history = (*kept, (now, seen))
        with self._lock:
            # Si entretanto ha soltado la cámara, o la ha vuelto a abrir, esto ya no es lo
            # que ve.
            current = self._seeing and self._session == session
            if current:
                self._view = _View(seeing=True, known=True, at=now, version=version, faces=seen)
        if current:
            self._remember(now, names)

    def _doubt(self, *, forget: bool = True) -> None:
        """Deja de saber quién hay: hasta el siguiente fotograma que pueda leer entero, quien
        lo lea no lo da por actual. Con ``forget``, lo que recordaba de cada cara tampoco
        vale para lo que vea después."""
        with self._lock:
            self._view = replace(self._view, known=False)
        if forget:
            self._known, self._aged = (), ()

    def _permissions(self) -> int:
        """La versión de los permisos de quien reconoce caras; ``-1`` si no hay quien."""
        recognition = self._recognition
        return -1 if recognition is None else recognition.version

    def _all_followed(self, faces: Sequence[Any], now: float) -> bool:
        """Si cada cara de ``faces`` es una que ya sabía quién era y qué edad tenía, seguida
        sin hueco desde el fotograma anterior."""
        return all(
            entry is not None
            for kept, used in ((self._known, self._recognition), (self._aged, self._ages))
            if used is not None
            for entry in _followed(kept, faces, now)
        )

    def _remember(self, now: float, names: Sequence[str | None]) -> None:
        """Le dice a quien recuerda lo que ve quién es cada cara de este fotograma. Un fallo
        se apunta una vez, con su tipo, y la vista sigue."""
        log = self._log
        if log is None:
            return
        try:
            log.see(now, names)
        except Exception as error:
            if not self._log_failed:
                self._log_failed = True
                _logger.error("Quien recuerda lo que ve ha fallado (%s)", type(error).__name__)

    def _tidy(self) -> None:
        """Le pide a quien recuerda lo que ve que borre lo viejo. Un fallo se apunta una vez,
        con su tipo, y la vista sigue."""
        log = self._log
        if log is None:
            return
        try:
            log.tidy()
        except Exception as error:
            if not self._log_failed:
                self._log_failed = True
                _logger.error("Quien recuerda lo que ve ha fallado (%s)", type(error).__name__)

    def _paused(self) -> None:
        """Le dice a quien recuerda lo que ve que ha dejado de ver."""
        log = self._log
        if log is None:
            return
        try:
            log.pause()
        except Exception as error:
            if not self._log_failed:
                self._log_failed = True
                _logger.error("Quien recuerda lo que ve ha fallado (%s)", type(error).__name__)

    def _identify(self, faces: Sequence[Any], now: float, version: int) -> list[str | None]:
        """Quién es cada cara de ``faces``: la que ya se reconoció hace poco donde está,
        sin volver a hacerlo; las demás, ahora. Con otra ``version`` de los permisos que la
        de lo que recordaba, todas, ahora. Si alguien está dando permiso y su cara está
        sola delante, va a quien reconoce. Un fallo se apunta una vez, con su tipo, y esa
        vez nadie es nadie."""
        recognition = self._recognition
        if recognition is None:
            return [None] * len(faces)
        if not faces:
            # Sin nadie delante, lo que se supo de cada cara deja de valer: la que aparezca
            # después se reconoce de nuevo, aunque sea en el mismo sitio.
            self._known = ()
            return []
        try:
            if recognition.wants_face() and len(faces) == 1:
                recognition.take_face(faces[0].crop)
            if version != self._known_version:
                self._known, self._known_version = (), version
            self._known = _again_or_kept(
                self._known, faces, now, lambda face: recognition.who_by_face(face.crop)
            )
            return [who for _, who, _, _ in self._known]
        except Exception as error:
            if not self._recognition_failed:
                self._recognition_failed = True
                _logger.error("Quien reconoce caras ha fallado (%s)", type(error).__name__)
            return [None] * len(faces)

    def _age(self, faces: Sequence[Any], now: float) -> list[AgeReading | None]:
        """La edad que aparenta cada cara de ``faces``: la que ya se estimó hace poco donde
        está, sin volver a hacerlo; las demás, ahora. Un fallo se apunta una vez, con su
        tipo, y esa vez no se sabe la de nadie."""
        ages = self._ages
        if ages is None:
            return [None] * len(faces)
        if not faces:
            self._aged = ()
            return []
        try:
            self._aged = _again_or_kept(
                self._aged, faces, now, lambda face: ages.estimate(face.crop)
            )
            return [age for _, age, _, _ in self._aged]
        except Exception as error:
            if not self._ages_failed:
                self._ages_failed = True
                _logger.error("Quien estima la edad ha fallado (%s)", type(error).__name__)
            return [None] * len(faces)

    def in_front_names(self) -> tuple[str | None, ...] | None:
        """Quiénes tiene delante en el último fotograma, su nombre o ``None`` por cada uno;
        ``None`` si no sabe quién hay ahora (``_current``), o si alguien ha dado o quitado
        su permiso desde que los reconoció: entonces no lo dice."""
        view = self._view
        if not self._current(view) or view.version != self._permissions():
            return None
        return tuple(face.who for face in view.faces)

    def in_front_ages(self) -> tuple[AgeReading | None, ...] | None:
        """La edad que aparentan los que tiene delante en el último fotograma, ``None`` por
        cada uno cuya edad no se sabe; ``None`` si no ve o no tiene quien estime la edad. Si
        ve pero no sabe quién hay ahora (``_current``), una edad que no se sabe: es duda."""
        view = self._view
        if not view.seeing or self._ages is None:
            return None
        if not self._current(view):
            return (None,)
        return tuple(face.age for face in view.faces)

    def in_front(self) -> tuple[Glimpse, ...]:
        """Las caras del último fotograma; ninguna si aún no ha visto nada, si no ve o si no
        sabe quién hay ahora (``_current``). Si alguien ha dado o quitado su permiso desde
        que se reconocieron, sin nombre."""
        view = self._view
        if not self._current(view):
            return ()
        if view.version != self._permissions():
            return tuple(replace(face, who=None) for face in view.faces)
        return view.faces

    def _current(self, view: _View) -> bool:
        """Si ``view`` dice quién hay ahora: ve, sabe quién hay y su fotograma es de hace
        como mucho ``FRESH_SECONDS``."""
        return view.seeing and view.known and self._clock() - view.at <= FRESH_SECONDS

    def talker_x(self) -> float | None:
        """Dónde está quien mueve la boca en el último fotograma; si son varios, el más al
        centro. ``None`` si nadie habla."""
        return _most_centered(face for face in self.in_front() if face.talking)

    def watcher_x(self) -> float | None:
        """Dónde está quien le mira en el último fotograma; si son varios, el más al centro."""
        return _most_centered(face for face in self.in_front() if face.looking)

    def talker_looked_since(self, since: float) -> bool:
        """Si desde ``since`` alguien que movía la boca le miraba a la vez: es lo que dice que
        le hablan a él aunque no digan su nombre."""
        return any(
            face.talking and face.looking
            for moment, faces in self._history
            if moment >= since
            for face in faces
        )


def _most_centered(faces: Iterable[Glimpse]) -> float | None:
    xs = [face.x for face in faces]
    return min(xs, key=lambda x: abs(x - 0.5)) if xs else None


def _again_or_kept[T](
    kept: Sequence[tuple[float, T, float, float]],
    faces: Sequence[Any],
    now: float,
    look_again: Callable[[Any], T],
) -> tuple[tuple[float, T, float, float], ...]:
    """Lo de cada cara de ``faces``, con dónde está, desde cuándo se sabe y cuándo se vio:
    lo que se supo de ella hace menos de ``RECOGNIZE_AGAIN_SECONDS``, si se la ha seguido
    sin hueco (``_followed``); y si no, ``look_again``, ahora."""
    found: list[tuple[float, T, float, float]] = []
    for face, cached in zip(faces, _followed(kept, faces, now), strict=True):
        if cached is not None and now - cached[2] < RECOGNIZE_AGAIN_SECONDS:
            found.append((face.x, cached[1], cached[2], now))
        else:
            found.append((face.x, look_again(face), now, now))
    return tuple(found)


def _followed[T](
    kept: Sequence[tuple[float, T, float, float]], faces: Sequence[Any], now: float
) -> list[tuple[float, T, float, float] | None]:
    """Para cada cara de ``faces``, lo que se supo de ella si se la ha seguido sin hueco: la
    de antes más cerca de donde está, a menos de ``SAME_PLACE``, vista hace como mucho
    ``SAME_FACE_GAP_SECONDS``; si no hay ninguna, ``None``. Cada cara de antes vale para una
    sola de ahora: la posición sola no dice que sea la misma, la sigue de un fotograma al
    siguiente."""
    candidates = [entry for entry in kept if now - entry[3] <= SAME_FACE_GAP_SECONDS]
    found: list[tuple[float, T, float, float] | None] = []
    for face in faces:
        near = [entry for entry in candidates if abs(entry[0] - face.x) <= SAME_PLACE]
        if near:
            cached = min(near, key=lambda entry: abs(entry[0] - face.x))
            candidates.remove(cached)
            found.append(cached)
        else:
            found.append(None)
    return found
