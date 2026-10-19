"""Quién es quién: reconocer por la cara y por la voz a quien dio permiso (pieza E de la
0.4, ADR-263).

- **Compara**: la huella de una cara o de una voz con las de quien dio permiso, y da su
  nombre si se parece lo bastante (``FACE_ALIKE``, ``VOICE_ALIKE``); si no, ``None``, que es
  «sin identificar». La huella comparada se suelta en el acto: reconocer solo lee, así
  que la de un desconocido no tiene camino para guardarse. Sin nadie que haya dado
  permiso, no saca ninguna.
- **Dar permiso** lleva tres pasos, y cada uno lo da quien lo capta: la ventana empieza
  con el nombre (``begin``); la vista da el recorte de la cara en ``FACE_SAMPLES``
  fotogramas en que la persona está sola delante (``take_face``), y se queda la huella que
  más se parece a las demás, que un fotograma movido no la estropee; y el oído, lo que
  sonó en el turno siguiente (``take_voice``). Solo entonces cifra las dos huellas y las
  guarda juntas, en lugar de las que tuviera esa persona.
- **Quitar el permiso** borra todas las huellas de esa persona (``forget``). La ventana
  lista a todos los que tienen huellas guardadas, también si ya no se pueden leer, para
  que se puedan borrar siempre.
- **Carga cuando hace falta**: los reconocedores y las huellas guardadas, la primera vez
  que se necesitan, en el hilo que las pida, nunca a la vez dos. Cargar los reconocedores
  tarda, y lo pide la vista o el oído, nunca la ventana; mientras tanto, la ventana lee y
  cambia el permiso sin esperarles. Si no cargan, nadie es reconocido, se dice por qué una
  vez y no se vuelve a intentar.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum

from sirius.infrastructure.logging import get_logger
from sirius.ports.recognition import (
    Print,
    PrintKind,
    PrintStore,
    RecognitionEngines,
    RecognitionUnavailable,
    SealedPrint,
    Sealer,
)

_logger = get_logger(__name__)

#: Cómo se dice de quien no se sabe quién es.
UNKNOWN = "sin identificar"
#: Lo que tiene que parecerse la huella de una cara a una guardada para ser de esa persona.
FACE_ALIKE = 0.4
#: Y la de una voz.
VOICE_ALIKE = 0.35
#: Lo más largo que puede ser un nombre.
LONGEST_NAME = 40
#: En cuántos fotogramas se mira la cara de quien da permiso.
FACE_SAMPLES = 5


class EnrollmentStep(Enum):
    """En qué va el permiso que se está dando."""

    #: No se está dando ninguno.
    IDLE = "idle"
    #: Espera la cara de quien lo da, sola delante de la cámara.
    FACE = "face"
    #: Espera su voz, en el turno siguiente.
    VOICE = "voice"
    #: Ya está: sus huellas están guardadas.
    DONE = "done"
    #: No se ha podido: ``notice`` dice por qué.
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Enrollment:
    """El permiso que se está dando: en qué va, de quién y lo que se le dice."""

    step: EnrollmentStep = EnrollmentStep.IDLE
    name: str = ""
    notice: str = ""


#: Lo que dice cada paso, con el nombre de quien da el permiso.
LOOK_AT_ME = "Mírame un momento, tú solo delante de la cámara, {name}."
SAY_IT = "Ahora di en voz alta: «Sirius, soy {name}, y quiero que me reconozcas por la voz»."
SAY_IT_AGAIN = (
    "No te he oído bastante: dilo otra vez, «Sirius, soy {name}, y quiero que me reconozcas "
    "por la voz»."
)
DONE = "Ya te conozco, {name}. Si quieres que te olvide, quita tu permiso."
CANNOT = "No puedo reconocerte: {reason}."
#: Por qué no, cuando falla algo que no es que falte lo instalado.
NO_FACE_PRINT = "no he podido sacar la huella de tu cara"
NO_VOICE_PRINT = "no he podido sacar la huella de tu voz"
NOT_SAVED = "no he podido guardar tus huellas"


class Recognition[Crop, Chunk]:
    """Quién es quién, con las huellas de quien dio permiso."""

    def __init__(
        self,
        *,
        load_engines: Callable[[], RecognitionEngines[Crop, Chunk]],
        store: PrintStore,
        sealer: Sealer,
    ) -> None:
        self._load_engines = load_engines
        self._store = store
        self._sealer = sealer
        #: Lo que se cambia desde varios hilos; se coge solo para cambiarlo, nunca mientras
        #: se carga algo.
        self._lock = threading.Lock()
        #: Que no carguen a la vez dos hilos los reconocedores, ni las huellas guardadas.
        self._loading_engines = threading.Lock()
        self._loading_prints = threading.Lock()
        self._engines: RecognitionEngines[Crop, Chunk] | None = None
        #: Por qué no se puede reconocer, si no carga; vacío si carga o aún no lo ha intentado.
        self._unavailable = ""
        #: Las huellas que se pueden leer, descifradas, de una vez: se cambian enteras.
        self._known: tuple[tuple[str, PrintKind, Print], ...] = ()
        #: Quiénes tienen huellas guardadas, se puedan leer o no.
        self._people: tuple[str, ...] = ()
        self._loaded_prints = False
        self._enrollment = Enrollment()
        #: Las huellas de la cara del permiso que se está dando, hasta tener todas.
        self._faces: tuple[Print, ...] = ()
        #: La que se queda, hasta que llega su voz.
        self._face: Print | None = None
        #: Cuántas veces han cambiado los que dieron permiso: quien recuerda a quién vio,
        #: lo olvida al cambiar.
        self._version = 0

    # --- Lo que se lee sin esperar -------------------------------------------------------

    @property
    def version(self) -> int:
        """Cambia cada vez que alguien da o quita su permiso."""
        return self._version

    @property
    def enrollment(self) -> Enrollment:
        """El permiso que se está dando, para la ventana."""
        return self._enrollment

    @property
    def unavailable(self) -> str:
        """Por qué no se puede reconocer; vacío si se puede o aún no se ha intentado."""
        return self._unavailable

    def people(self) -> tuple[str, ...]:
        """Quiénes tienen huellas guardadas, por orden, también si ya no se pueden leer.
        Carga las huellas guardadas si hace falta."""
        self._ensure_prints()
        return self._people

    def knows_anyone(self) -> bool:
        """Si hay alguien a quien reconocer: alguien dio permiso y sus huellas se leen."""
        self._ensure_prints()
        return bool(self._known)

    # --- Reconocer -----------------------------------------------------------------------

    def who_by_face(self, crop: Crop) -> str | None:
        """De quién es la cara de ``crop``, o ``None`` si de nadie que diera permiso."""
        engines = self._ready()
        if engines is None:
            return None
        return self._closest(engines.faces.fingerprint(crop), PrintKind.FACE, FACE_ALIKE)

    def who_by_voice(self, chunks: Sequence[Chunk]) -> str | None:
        """De quién es la voz que sonó en ``chunks``, o ``None`` si de nadie que diera
        permiso o si no hay bastante voz."""
        engines = self._ready()
        if engines is None:
            return None
        heard = engines.voices.fingerprint(chunks)
        return None if heard is None else self._closest(heard, PrintKind.VOICE, VOICE_ALIKE)

    def _ready(self) -> RecognitionEngines[Crop, Chunk] | None:
        """Los reconocedores, si hay alguien a quien reconocer y cargan."""
        if not self.knows_anyone():
            return None
        return self._ensure_engines()

    def _closest(self, heard: Print, kind: PrintKind, alike: float) -> str | None:
        """El que más se parece de los de ``kind``, si se parece al menos ``alike``."""
        best, best_score = None, alike
        for person, known_kind, known in self._known:
            if known_kind is not kind or len(known) != len(heard):
                continue
            score = _alike(known, heard)
            if score >= best_score:
                best, best_score = person, score
        return best

    # --- Dar y quitar el permiso ---------------------------------------------------------

    def begin(self, name: str) -> Enrollment:
        """Empieza a dar permiso ``name``: espera su cara. Un nombre vacío o muy largo no.
        Si ya se sabe que no se puede reconocer, lo dice en el acto."""
        name = " ".join(name.split())
        if not name or len(name) > LONGEST_NAME:
            return self._enrollment
        with self._lock:
            self._faces, self._face = (), None
            if self._unavailable:
                notice = CANNOT.format(reason=self._unavailable)
                self._enrollment = Enrollment(EnrollmentStep.FAILED, name, notice)
            else:
                notice = LOOK_AT_ME.format(name=name)
                self._enrollment = Enrollment(EnrollmentStep.FACE, name, notice)
            return self._enrollment

    def cancel(self) -> None:
        """Deja el permiso que se estaba dando, sin guardar nada."""
        with self._lock:
            self._faces, self._face = (), None
            self._enrollment = Enrollment()

    def wants_face(self) -> bool:
        """Si espera la cara de quien da permiso."""
        return self._enrollment.step is EnrollmentStep.FACE

    def wants_voice(self) -> bool:
        """Si espera su voz."""
        return self._enrollment.step is EnrollmentStep.VOICE

    def take_face(self, crop: Crop) -> None:
        """La cara de quien da permiso, sola delante: saca su huella, y con las de
        ``FACE_SAMPLES`` fotogramas, espera su voz."""
        enrollment = self._enrollment
        if enrollment.step is not EnrollmentStep.FACE:
            return
        try:
            face = self._ensure_engines_or_fail().faces.fingerprint(crop)
        except RecognitionUnavailable as error:
            self._fail(enrollment, error.reason)
            return
        except Exception as error:
            _logger.error("No se pudo sacar la huella de una cara (%s)", type(error).__name__)
            self._fail(enrollment, NO_FACE_PRINT)
            return
        with self._lock:
            if self._enrollment is not enrollment:
                return
            self._faces = (*self._faces, face)
            if len(self._faces) < FACE_SAMPLES:
                return
            self._face, self._faces = _most_alike(self._faces), ()
            notice = SAY_IT.format(name=enrollment.name)
            self._enrollment = Enrollment(EnrollmentStep.VOICE, enrollment.name, notice)

    def take_voice(self, chunks: Sequence[Chunk]) -> None:
        """Lo que dijo quien da permiso: saca la huella de su voz y guarda las dos, cifradas."""
        enrollment, face = self._enrollment, self._face
        if enrollment.step is not EnrollmentStep.VOICE or face is None:
            return
        name = enrollment.name
        try:
            voice = self._ensure_engines_or_fail().voices.fingerprint(chunks)
        except RecognitionUnavailable as error:
            self._fail(enrollment, error.reason)
            return
        except Exception as error:
            _logger.error("No se pudo sacar la huella de una voz (%s)", type(error).__name__)
            self._fail(enrollment, NO_VOICE_PRINT)
            return
        if voice is None:
            with self._lock:
                if self._enrollment is enrollment:
                    notice = SAY_IT_AGAIN.format(name=name)
                    self._enrollment = Enrollment(EnrollmentStep.VOICE, name, notice)
            return
        self._ensure_prints()
        try:
            sealed = (
                SealedPrint(name, PrintKind.FACE, self._sealer.seal(face)),
                SealedPrint(name, PrintKind.VOICE, self._sealer.seal(voice)),
            )
        except RecognitionUnavailable as error:
            self._fail(enrollment, error.reason)
            return
        with self._lock:
            # Con el cerrojo hasta guardarlas: cancelar a la vez no deja huellas guardadas
            # de un permiso que la ventana da por no dado.
            if self._enrollment is not enrollment:
                return
            self._face = None
            try:
                self._store.replace(name, sealed)
            except Exception as error:
                _logger.error("No se pudieron guardar unas huellas (%s)", type(error).__name__)
                notice = CANNOT.format(reason=NOT_SAVED)
                self._enrollment = Enrollment(EnrollmentStep.FAILED, name, notice)
                return
            others = tuple(known for known in self._known if known[0] != name)
            self._known = (*others, (name, PrintKind.FACE, face), (name, PrintKind.VOICE, voice))
            self._people = tuple(sorted({*self._people, name}))
            self._version += 1
            self._enrollment = Enrollment(EnrollmentStep.DONE, name, DONE.format(name=name))
        _logger.info("Alguien ha dado permiso para que le reconozca")

    def forget(self, name: str) -> bool:
        """Quita el permiso de ``name``: borra todas sus huellas, y deja de reconocerle. Si
        no se pueden borrar, no cambia nada y da ``False``."""
        self._ensure_prints()
        with self._lock:
            try:
                self._store.remove(name)
            except Exception as error:
                _logger.error("No se pudieron borrar unas huellas (%s)", type(error).__name__)
                return False
            self._known = tuple(known for known in self._known if known[0] != name)
            self._people = tuple(person for person in self._people if person != name)
            self._version += 1
        _logger.info("Alguien ha quitado su permiso para que le reconozca")
        return True

    def _fail(self, enrollment: Enrollment, reason: str) -> None:
        with self._lock:
            if self._enrollment is enrollment:
                self._faces, self._face = (), None
                notice = CANNOT.format(reason=reason)
                self._enrollment = Enrollment(EnrollmentStep.FAILED, enrollment.name, notice)

    # --- Cargar --------------------------------------------------------------------------

    def _ensure_engines(self) -> RecognitionEngines[Crop, Chunk] | None:
        """Los reconocedores; ``None`` si no cargan, que se dice una vez."""
        try:
            return self._ensure_engines_or_fail()
        except RecognitionUnavailable:
            return None

    def _ensure_engines_or_fail(self) -> RecognitionEngines[Crop, Chunk]:
        engines = self._engines
        if engines is not None:
            return engines
        with self._loading_engines:
            if self._engines is not None:
                return self._engines
            if self._unavailable:
                raise RecognitionUnavailable(self._unavailable)
            try:
                engines = self._load_engines()
            except RecognitionUnavailable as error:
                reason = error.reason
            except Exception as error:
                reason = f"los modelos de reconocer no cargan ({error})"
            else:
                self._engines = engines
                return engines
            self._unavailable = reason
            _logger.info("No se puede reconocer: %s", reason)
            raise RecognitionUnavailable(reason)

    def _ensure_prints(self) -> None:
        """Las huellas guardadas, descifradas en memoria, la primera vez. Si la base no se
        puede leer, no hay a quién reconocer, y no se vuelve a intentar."""
        if self._loaded_prints:
            return
        with self._loading_prints:
            if self._loaded_prints:
                return
            try:
                stored = self._store.all()
            except Exception as error:
                _logger.error("No se pueden leer las huellas guardadas (%s)", type(error).__name__)
                stored = ()
            known: list[tuple[str, PrintKind, Print]] = []
            unreadable = 0
            for print_ in stored:
                try:
                    known.append((print_.person, print_.kind, self._sealer.open(print_.sealed)))
                except RecognitionUnavailable:
                    unreadable += 1
            if unreadable:
                _logger.warning("Hay %d huellas guardadas que no se pueden leer", unreadable)
            with self._lock:
                self._known = tuple(known)
                self._people = tuple(sorted({print_.person for print_ in stored}))
                self._loaded_prints = True


def _alike(one: Print, other: Print) -> float:
    """Lo que se parecen dos huellas de longitud uno: su producto."""
    return sum(a * b for a, b in zip(one, other, strict=True))


def _most_alike(prints: Sequence[Print]) -> Print:
    """De ``prints``, la que más se parece a las demás: la de un fotograma movido, que se
    parece poco a las otras, no se queda."""
    return max(prints, key=lambda candidate: sum(_alike(candidate, other) for other in prints))


def describe(who: str | None) -> str:
    """Cómo se dice ``who``: su nombre, o «sin identificar»."""
    return who if who is not None else UNKNOWN
