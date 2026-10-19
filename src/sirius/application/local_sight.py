"""La vista del robot: la cámara y las caras, en este ordenador (pieza D de la 0.4, ADR-262).

Lee la cámara, busca las caras y recuerda lo visto unos segundos: de cada cara, dónde está,
si mueve la boca, si mira a la cámara y, desde la pieza E (ADR-263), quién es, si dio
permiso para que la reconozca. Con eso dice a quién mirar, si quien habla le mira y a
quiénes tiene delante, que es lo que leen la cara, el oído y la charla. Ningún fotograma ni
recorte sale de aquí ni se guarda: el fotograma se suelta en cuanto el detector lo ha
mirado, el recorte de cada cara solo lo lee quien reconoce, en el acto, y lo recordado son
números y nombres.

- **La atiende un hilo**, como al oído (``SightLoop``), unas diez veces por segundo; la
  cara y el oído la leen sin esperarla, de lo último que vio.
- **Sin cámara, lo dice y sigue**: si falta lo que instala la orden, si no hay cámara o la
  tiene otro programa, o si deja de dar imagen, como al desenchufarla, ``notice`` dice por
  qué, y Sirius sigue oyendo y hablando. El diario se queda con el tipo de fallo.
- **Lo que no puede leer no la para**: un fotograma que el detector no entiende se deja, y
  se apunta una vez; un fallo de quien reconoce, igual, y esa vez nadie es reconocido.
- **Reconocer cuesta**: cada cara se reconoce al aparecer y después cada
  ``RECOGNIZE_AGAIN_SECONDS``, siguiéndola por dónde está; si alguien da o quita su
  permiso, se vuelve a mirar a todos. Y cuando alguien está dando permiso, su cara, si
  está sola delante, va a quien reconoce.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from sirius.infrastructure.logging import get_logger
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


@dataclass(frozen=True, slots=True)
class Glimpse:
    """Lo que vio de una cara en un fotograma, sin nada de la imagen: dónde está, de 0 a 1
    con la izquierda y la derecha de la cámara, si movía la boca, si le miraba y quién es,
    su nombre si dio permiso para que la reconozca; si no, ``None``."""

    x: float
    talking: bool
    looking: bool
    who: str | None = None


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
    ) -> None:
        self._load_engines = load_engines
        #: Quien reconoce caras; sin él, nadie es nadie.
        self._recognition = recognition
        self._recognition_failed = False
        #: De quién era cada cara la última vez que se reconoció: dónde estaba, quién era y
        #: cuándo se reconoció; y con qué versión de los permisos.
        self._known: tuple[tuple[float, str | None, float], ...] = ()
        self._known_version = -1
        self._install_command = install_command
        self._clock = clock
        self._memory = memory_seconds
        self._engines: SightEngines[Any, Any] | None = None
        #: La cámara y su estado, desde el hilo que sea.
        self._lock = threading.Lock()
        self._seeing = False
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
            self._notice = ""
            return ""

    def stop(self) -> None:
        """Suelta la cámara. Lo visto se queda, para quien aún lo lea."""
        with self._lock:
            if self._engines is not None and self._seeing:
                self._engines.camera.close()
            self._seeing = False

    def look(self) -> None:
        """Mira una vez: lee la cámara, busca las caras y lo apunta con su momento. Si la
        cámara deja de dar imagen, la suelta y lo dice."""
        with self._lock:
            if not self._seeing or self._engines is None:
                return
            engines = self._engines
            try:
                frame = engines.camera.read()
            except CameraUnavailable as error:
                _logger.warning("La cámara ha dejado de dar imagen: %s", error.reason)
                engines.camera.close()
                self._seeing = False
                self._notice = NO_CAMERA.format(reason=error.reason)
                return
        if frame is None:
            return
        try:
            faces = engines.detector.detect(frame)
        except Exception as error:
            if not self._detector_failed:
                self._detector_failed = True
                _logger.error("El detector de caras ha fallado (%s)", type(error).__name__)
            return
        finally:
            del frame
        now = self._clock()
        names = self._identify(faces, now)
        seen = tuple(
            Glimpse(face.x, face.talking, face.looking, who)
            for face, who in zip(faces, names, strict=True)
        )
        kept = tuple(entry for entry in self._history if now - entry[0] <= self._memory)
        self._history = (*kept, (now, seen))

    def _identify(self, faces: Sequence[Any], now: float) -> list[str | None]:
        """Quién es cada cara de ``faces``: la que ya se reconoció hace poco donde está,
        sin volver a hacerlo; las demás, ahora. Si alguien está dando permiso y su cara está
        sola delante, va a quien reconoce. Un fallo se apunta una vez, con su tipo, y esa
        vez nadie es nadie."""
        recognition = self._recognition
        if recognition is None or not faces:
            return [None] * len(faces)
        try:
            if recognition.wants_face() and len(faces) == 1:
                recognition.take_face(faces[0].crop)
            if recognition.version != self._known_version:
                self._known, self._known_version = (), recognition.version
            candidates = [k for k in self._known if now - k[2] < RECOGNIZE_AGAIN_SECONDS]
            names: list[str | None] = []
            known: list[tuple[float, str | None, float]] = []
            for face in faces:
                near = [k for k in candidates if abs(k[0] - face.x) <= SAME_PLACE]
                if near:
                    cached = min(near, key=lambda k: abs(k[0] - face.x))
                    candidates.remove(cached)
                    who, at = cached[1], cached[2]
                else:
                    who, at = recognition.who_by_face(face.crop), now
                names.append(who)
                known.append((face.x, who, at))
            self._known = tuple(known)
            return names
        except Exception as error:
            if not self._recognition_failed:
                self._recognition_failed = True
                _logger.error("Quien reconoce caras ha fallado (%s)", type(error).__name__)
            return [None] * len(faces)

    def in_front_names(self) -> tuple[str | None, ...] | None:
        """Quiénes tiene delante en el último fotograma, su nombre o ``None`` por cada uno;
        ``None`` si no ve, que entonces no sabe quién hay."""
        return tuple(face.who for face in self.in_front()) if self._seeing else None

    def in_front(self) -> tuple[Glimpse, ...]:
        """Las caras del último fotograma; ninguna si aún no ha visto nada o no ve."""
        history = self._history
        return history[-1][1] if history and self._seeing else ()

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
