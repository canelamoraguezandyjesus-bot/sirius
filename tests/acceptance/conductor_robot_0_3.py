"""Conductor de las pruebas de aceptación de la versión 0.3 del robot, la voz (ADR-241).

Las pruebas de ``test_robot_0_3_*.py`` hablan como el plan
(``docs/evolution/PLAN_DEL_ROBOT.md``, §5): el propietario dice algo por el
micro, Sirius le oye, le contesta hablando, se le corta, se le calla. Este
módulo es lo único que sabe cómo se hace cada cosa en el código. Así las
pruebas se escriben antes que el código, como pide la §3 del plan, y cuando
entra una pieza solo cambia su parte del conductor, no las pruebas.

**La regla del conductor: no implementa nada de Sirius.** Es el conductor de
la 0.2 con el oído y la voz encima: la charla, la semilla, la memoria y la
ventana son las de siempre, montadas como en producción. Los dobles de abajo
hacen de micrófono, de oído, de transcriptor, de voz, de altavoz y de modelo,
nunca de Sirius: llevan escrito lo que suena en vez de ondas, para que una
prueba pueda decir «esto lo dijo el propietario» y «esto sonó por el altavoz».

**Los dobles hacen algo, y apuntan lo que hacen.** El micro lee, el oído dice
cuándo acaba el turno, el transcriptor transcribe, la voz dice, el altavoz
suena y el modelo contesta; y cada uno apunta lo que hizo, con su momento, en
el acto de hacerlo. Esos registros solo se leen: ni el conductor ni la pieza
que entre los escriben, porque quien implementa una pieza escribe también su
parte del conductor, y un registro que rellenara el conductor no probaría nada
(revisión propia de la PR #686). Lo que la tubería recibe del micro (``Audio``)
no lleva quién lo dijo ni con qué voz, como en un micro de verdad: eso lo
guarda el ``Sonido`` que la prueba hizo sonar, y solo la prueba lo ve. Que los
dobles hacen lo que dicen lo comprueba ``test_dobles_del_conductor.py``.

Las piezas de ADR-241 que aún no han entrado levantan ``PiezaPendiente``
(``piezas_del_robot``). Cuando una entra, se implementan sus métodos aquí y se
añade su letra a ``PIEZAS_ENTREGADAS``; la tabla de
``docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md`` tiene que decirlo, porque
``test_robot_0_3_trazabilidad.py`` lo compara.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import sys
import tempfile
import time
import weakref
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any, Protocol

from conductor_robot_0_2 import (
    Conductor,
    Peticion,
    VentanaDePrueba,
    _ProveedorGrabador,
    _respuestas,
)
from piezas_del_robot import PiezaPendiente, Piezas

from sirius.config.settings import _CONFIG_FILE_NAME  # el nombre que usa `_config_file()`
from sirius.infrastructure.logging import LOG_FILE_NAME, configure_logging
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMStreamEvent, LLMTextDelta

#: Las letras de la tabla de piezas de ADR-241 que ya han entrado en ``main``.
#: La A es esta: la nota de arranque y estas pruebas.
PIEZAS_ENTREGADAS: frozenset[str] = frozenset({"A"})

#: Qué trae cada pieza, con las palabras de la tabla de ADR-241.
PIEZAS: Mapping[str, str] = {
    "A": "la nota de arranque y las pruebas de aceptación",
    "B": "oír en local: lo que dice por voz entra en la charla, y nada sale del ordenador",
    "C": "hablar en local con Piper, frase a frase desde la primera",
    "D": "escucha siempre: el indicador, el silencio, nada de audio guardado y a quién le hablan",
    "E": "cortarle: la cancelación de eco por software y la interrupción",
    "F": "elegir su voz a ciegas",
}

_PIEZAS = Piezas("ADR-241", PIEZAS, PIEZAS_ENTREGADAS)

#: Marca una prueba como dependiente de una pieza; ver ``piezas_del_robot``.
pieza = _PIEZAS.pieza

#: Lo que se toma por audio guardado si aparece en el disco mientras el conductor vive.
EXTENSIONES_DE_AUDIO: frozenset[str] = frozenset(
    {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".aiff", ".aif", ".webm", ".opus"}
)

#: Audio sin cabecera o volcados de ondas: cuentan en las carpetas de Sirius y en la de la
#: prueba, no en la temporal del sistema, que en el Windows del propietario comparten
#: todos sus programas y donde un ``.bin`` ajeno no es de Sirius.
EXTENSIONES_DE_AUDIO_CRUDO: frozenset[str] = frozenset({".pcm", ".raw", ".bin", ".npy", ".npz"})

#: Cómo empieza un fichero de audio con cabecera: WAV, Ogg, FLAC, MP3 con etiqueta y WebM.
#: Un BLOB de la base que empiece así es audio guardado.
_CABECERAS_DE_AUDIO: tuple[bytes, ...] = (b"RIFF", b"OggS", b"fLaC", b"ID3", b"\x1aE\xdf\xa3")


def _pendiente(letra: str) -> PiezaPendiente:
    return _PIEZAS.pendiente(letra)


def _ahora() -> float:
    """El reloj de todos los dobles, ``time.perf_counter``: un solo reloj, y es suyo."""
    return time.perf_counter()


# --- El vigilante: ve cada fichero que se abre para escribir, cada conexión y cada proceso ---


class Vigilado(Protocol):
    """A quien el vigilante le cuenta lo que ve mientras está vigilando."""

    def anota_escritura(self, ruta: Path) -> None: ...

    def anota_conexion(self, direccion: str) -> None: ...

    def anota_proceso(self, orden: str) -> None: ...


#: Los conductores vivos, desde que se construyen hasta que se cierran: a ellos les
#: llega cada apertura de fichero para escribir, cada conexión o envío y cada proceso
#: lanzado. Débil, para que un conductor olvidado no se quede vigilando.
_EN_UN_TURNO: weakref.WeakSet[Vigilado] = weakref.WeakSet()
_GANCHO_PUESTO = False
_BYTECODE_DE_ANTES: bool | None = None


def _vigila(conductor: Vigilado) -> None:
    """Empieza a contarle a ``conductor`` lo que ve.

    Mientras alguien vigila, Python no escribe bytecode: un ``.pyc`` de una
    importación tardía sería una escritura más para el gancho, y la regla es no
    excluir nada por su nombre; así, sencillamente, no ocurre.
    """
    global _BYTECODE_DE_ANTES
    if _BYTECODE_DE_ANTES is None:
        _BYTECODE_DE_ANTES = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
    _EN_UN_TURNO.add(conductor)


def _deja_de_vigilar(conductor: Vigilado) -> None:
    _EN_UN_TURNO.discard(conductor)
    if not _EN_UN_TURNO:
        _restaura_el_bytecode()


def deja_de_vigilar_a_todos() -> None:
    """Para el ``conftest``: al acabar una prueba, ningún conductor sigue vigilando."""
    _EN_UN_TURNO.clear()
    _restaura_el_bytecode()


def _restaura_el_bytecode() -> None:
    global _BYTECODE_DE_ANTES
    if _BYTECODE_DE_ANTES is not None:
        sys.dont_write_bytecode = _BYTECODE_DE_ANTES
        _BYTECODE_DE_ANTES = None


#: Lo que SQLite pone al lado de la base, con su mismo nombre delante.
_SIDECARS_DE_SQLITE = ("-journal", "-wal", "-shm")


@dataclass(frozen=True, slots=True)
class Permitidas:
    """Lo único que Sirius abre para escribir mientras oye y habla, por su ruta de verdad.

    Su base y lo que SQLite pone a su lado, su fichero de ajustes y su diario, con
    sus rotaciones. Se comparan rutas enteras, no nombres: un ``settings.json`` o un
    ``sirius.db`` en otra carpeta es una escritura como otra cualquiera (rondas 2 y
    3 de Codex sobre la PR #686).
    """

    base: Path
    ajustes: Path
    diario: Path

    def permite(self, ruta: Path) -> bool:
        ruta = ruta.resolve()
        if ruta == self.base.resolve() or ruta == self.ajustes.resolve():
            return True
        base = self.base.resolve()
        if ruta.parent == base.parent and ruta.name in {base.name + s for s in _SIDECARS_DE_SQLITE}:
            return True
        diario = self.diario.resolve()
        rotado = re.fullmatch(rf"{re.escape(diario.name)}(\.\d+)?", ruta.name)
        return ruta.parent == diario.parent and rotado is not None


def _abre_para_escribir(modo: object, flags: object) -> bool:
    if isinstance(modo, str):
        return any(letra in modo for letra in "wax+")
    if isinstance(flags, int):
        return bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT))
    return False


def es_escritura_sospechosa(ruta: Path, permitidas: Permitidas) -> bool:
    """Si abrir ``ruta`` para escribir mientras Sirius oye y habla es algo que no hace."""
    return not permitidas.permite(ruta)


def _dentro_de_socketpair() -> bool:
    """Si la conexión la está haciendo ``socket.socketpair`` consigo mismo.

    En Windows no hay pareja de tomas nativa y Python la fabrica conectándose a un
    puerto que acaba de enlazar en ``127.0.0.1``; asyncio la usa al crear cada bucle.
    No sale del ordenador, y por eso no cuenta como conexión. Se reconoce por el
    marco de ``socket.socketpair`` o ``socket._fallback_socketpair`` en la pila,
    no por la dirección: cualquier otra conexión a ``127.0.0.1`` sí cuenta.
    """
    marco: FrameType | None = sys._getframe(1)
    while marco is not None:
        es_socketpair = marco.f_code.co_name in ("socketpair", "_fallback_socketpair")
        if es_socketpair and marco.f_globals.get("__name__") == "socket":
            return True
        marco = marco.f_back
    return False


def _vigilar() -> None:
    """Pone, una vez por proceso, el gancho que ve cada escritura, conexión y proceso.

    Un gancho de auditoría de Python no se puede quitar, así que se pone una vez y
    solo trabaja mientras algún conductor está vivo. Ve todo lo que abre Python
    para escribir, también ``tempfile`` y lo que se borra después, cada
    ``socket.connect``, cada envío sin conexión (``sendto``, ``sendmsg``) y cada
    proceso que lanza Python, por ``subprocess`` o por ``os`` (rondas 1 y 2 de
    Codex y revisión propia de la PR #686). Lo que escriba, envíe o lance una
    biblioteca en C por su cuenta no pasa por aquí, y por eso el disco y la base
    se miran además al final.
    """
    global _GANCHO_PUESTO
    if _GANCHO_PUESTO:
        return

    def gancho(evento: str, args: tuple[Any, ...]) -> None:
        if not _EN_UN_TURNO:
            return
        try:
            visto = _lo_que_ve(evento, args)
        except TypeError, ValueError, UnicodeError:
            # Un gancho que lanza aborta la operación ajena: aquí se calla.
            return
        if visto is None:
            return
        que, dato = visto
        try:
            conductores = list(_EN_UN_TURNO)
        except RuntimeError:
            # El conjunto cambió desde otro hilo mientras se copiaba: se calla igual.
            return
        for conductor in conductores:
            try:
                if que == "escritura":
                    conductor.anota_escritura(Path(dato))
                elif que == "conexion":
                    conductor.anota_conexion(dato)
                else:
                    conductor.anota_proceso(dato)
            except OSError, ValueError, RuntimeError:
                # Una ruta que no se puede resolver tampoco puede abortar lo ajeno.
                continue

    sys.addaudithook(gancho)
    _GANCHO_PUESTO = True


def _lo_que_ve(evento: str, args: tuple[Any, ...]) -> tuple[str, str] | None:
    """Qué es este evento de auditoría para el vigilante, o ``None`` si no le importa."""
    if evento == "open":
        ruta, modo, flags = args
        if not _abre_para_escribir(modo, flags) or isinstance(ruta, int):
            return None
        return "escritura", os.fsdecode(ruta)
    if evento == "socket.connect":
        _toma, direccion = args
        return None if _dentro_de_socketpair() else ("conexion", repr(direccion))
    if evento in ("socket.sendto", "socket.sendmsg"):
        _toma, direccion = args
        return "conexion", repr(direccion)
    if evento == "subprocess.Popen":
        _ejecutable, orden, _cwd, _env = args
        return "proceso", repr(orden)
    if evento in ("os.system", "os.startfile"):
        return "proceso", repr(args[0])
    if evento in ("os.posix_spawn", "os.exec"):
        return "proceso", repr(args[1])
    if evento == "os.spawn":
        return "proceso", repr(args[2])
    if evento == "os.fork":
        return "proceso", "fork"
    return None


# --- Dobles: hacen de micro, de oído, de transcriptor, de voz, de altavoz y de modelo ---


@dataclass(frozen=True, slots=True)
class Audio:
    """Lo que la tubería recibe del micro: lo que suena, en texto.

    No lleva quién lo dijo ni con qué voz: un micro de verdad tampoco lo sabe. Eso
    lo guarda el ``Sonido`` que la prueba hizo sonar, y solo la prueba lo ve.
    ``texto`` vacío es silencio. No dura nada: el micro de mentira es instantáneo,
    como el oído, el modelo y la voz, y la tubería no debe darle ritmo.
    """

    texto: str

    @property
    def es_silencio(self) -> bool:
        return not self.texto


@dataclass(frozen=True, slots=True)
class Sonido:
    """Un trozo de audio de mentira, tal como lo ve la prueba.

    Lleva escrito lo que suena, en vez de ondas; ``de_quien`` dice quién lo
    produjo, «propietario» o «sirius», y ``voz`` con qué voz, si es de Sirius.
    La tubería no ve nada de eso: recibe su ``audio``.
    """

    texto: str
    de_quien: str = "propietario"
    voz: str = ""

    @property
    def es_silencio(self) -> bool:
        return not self.texto

    @property
    def audio(self) -> Audio:
        return Audio(self.texto)


class MicroCerrado(RuntimeError):
    """Sirius ha intentado leer el micrófono con el micrófono cerrado."""


class MicroDeMentira:
    """El micrófono: una cola de sonidos que la tubería va leyendo, si está abierto.

    Lo abre y lo cierra Sirius (``abre``, ``cierra``), nunca la prueba: así una
    prueba puede mirar que la ventana lo abre al arrancar y que el botón de
    silencio lo cierra. La prueba hace sonar cosas (``suena``); con el micro
    cerrado se pierden, como en uno de verdad, y quedan en ``perdidos``. La
    tubería lee (``lee``) y recibe ``Audio``, sin quién lo dijo; cada lectura
    queda apuntada aquí, con su momento, en el acto de leer.
    """

    def __init__(self) -> None:
        self._abierto = False
        self._pendientes: list[Sonido] = []
        self._leidos: list[Sonido] = []
        self._leido_en: list[float] = []
        self._perdidos: list[Sonido] = []

    @property
    def abierto(self) -> bool:
        return self._abierto

    @property
    def pendientes(self) -> tuple[Sonido, ...]:
        """Lo que ha sonado y la tubería aún no ha leído."""
        return tuple(self._pendientes)

    @property
    def leidos(self) -> tuple[Sonido, ...]:
        """Lo que la tubería ha leído, en orden."""
        return tuple(self._leidos)

    @property
    def leido_en(self) -> tuple[float, ...]:
        """Cuándo leyó la tubería cada sonido de ``leidos``, en el mismo orden."""
        return tuple(self._leido_en)

    @property
    def perdidos(self) -> tuple[Sonido, ...]:
        """Lo que sonó con el micro cerrado y nadie pudo leer."""
        return tuple(self._perdidos)

    def abre(self) -> None:
        self._abierto = True

    def cierra(self) -> None:
        self._abierto = False

    def suena(self, sonido: Sonido) -> None:
        """Algo suena delante del micro: queda pendiente de leer, o se pierde si está cerrado."""
        (self._pendientes if self._abierto else self._perdidos).append(sonido)

    def lee(self) -> Audio | None:
        """El siguiente sonido pendiente, o ``None`` si no hay ninguno. Cerrado, no se lee."""
        if not self._abierto:
            raise MicroCerrado
        if not self._pendientes:
            return None
        sonido = self._pendientes.pop(0)
        self._leidos.append(sonido)
        self._leido_en.append(_ahora())
        return sonido.audio


class OidoDeMentira:
    """Hace de Silero y de Smart Turn.

    Hay voz si el audio lleva texto (``hay_voz``). El turno acaba cuando, después
    de voz, han pasado seguidos los silencios que se le pidan (``escucha`` lo
    dice): con 1 es el detector impaciente; con más, dice «todavía no» en los
    primeros silencios y Sirius tiene que esperarle. Apunta cada audio que le
    enseñan (``vistos``) y en cuál dio un turno por acabado (``fines``). Cuántos
    silencios hacen falta solo lo sabe él: la tubería tiene que preguntarle.
    """

    def __init__(self) -> None:
        self._silencios_para_acabar = 1
        self._vistos: list[Audio] = []
        self._fines: list[int] = []
        self._hubo_voz = False
        self._silencios_seguidos = 0

    def pide_silencios(self, cuantos: int) -> None:
        self._silencios_para_acabar = cuantos

    @property
    def vistos(self) -> tuple[Audio, ...]:
        return tuple(self._vistos)

    @property
    def fines(self) -> tuple[int, ...]:
        """Los índices de ``vistos`` en los que dijo que el turno había acabado."""
        return tuple(self._fines)

    @staticmethod
    def hay_voz(audio: Audio) -> bool:
        """Silero: si en este audio hay alguien hablando."""
        return not audio.es_silencio

    def escucha(self, audio: Audio) -> bool:
        """Smart Turn: si con este audio el turno queda acabado."""
        self._vistos.append(audio)
        if not audio.es_silencio:
            self._hubo_voz = True
            self._silencios_seguidos = 0
            return False
        if not self._hubo_voz:
            return False
        self._silencios_seguidos += 1
        if self._silencios_seguidos < self._silencios_para_acabar:
            return False
        self._fines.append(len(self._vistos) - 1)
        self._hubo_voz = False
        self._silencios_seguidos = 0
        return True


class TranscriptorDeMentira:
    """Hace de faster-whisper: el texto es el que llevan escrito los audios con voz, en orden."""

    def __init__(self) -> None:
        self._transcritos: list[str] = []

    @property
    def transcritos(self) -> tuple[str, ...]:
        """Cada transcripción que se le pidió, en orden, tal como la devolvió."""
        return tuple(self._transcritos)

    def transcribe(self, audios: Sequence[Audio]) -> str:
        texto = " ".join(audio.texto for audio in audios if not audio.es_silencio)
        self._transcritos.append(texto)
        return texto


@dataclass(frozen=True, slots=True)
class Frase:
    """Una frase que se le pidió a la voz: el texto, el momento en que llegó y con qué voz."""

    texto: str
    momento: float
    voz: str


class VozDeMentira:
    """Hace de Piper, y de Chatterbox en la hoja de voces.

    Apunta cada frase que le piden, con su momento y con qué voz, y la devuelve
    como un sonido de Sirius con esa voz.
    """

    def __init__(self) -> None:
        self._frases: list[Frase] = []

    @property
    def frases(self) -> tuple[Frase, ...]:
        return tuple(self._frases)

    def di(self, texto: str, voz: str) -> Sonido:
        self._frases.append(Frase(texto, _ahora(), voz))
        return Sonido(texto, de_quien="sirius", voz=voz)


class AltavozDeMentira:
    """Lo que suena por el altavoz.

    ``suena`` apunta cada sonido con el momento en que empezó. Con ``con_eco``
    devuelve al micro lo que suena, como un altavoz que el micrófono capta. Con
    ``sigue_sonando`` mantiene el último sonido en el aire hasta que Sirius lo
    pare (``para``, que apunta cuándo) o la prueba lo deje acabar (``acaba``):
    sirve para cortarle. Sirius sabe si algo sigue sonando por ``sonando``, y no
    llama a ``acaba``: quien sabe cuándo termina un sonido es el altavoz. Las dos
    banderas y ``acaba`` son de la prueba; los registros, solo de él.
    """

    def __init__(self, micro: MicroDeMentira) -> None:
        self._micro = micro
        self.con_eco = False
        self.sigue_sonando = False
        self._sonados: list[tuple[Sonido, float]] = []
        self._sonando: Sonido | None = None
        self._parado_en: float | None = None

    @property
    def sonados(self) -> tuple[tuple[Sonido, float], ...]:
        return tuple(self._sonados)

    @property
    def sonando(self) -> Sonido | None:
        """Lo que sigue en el aire, si algo sigue."""
        return self._sonando

    @property
    def parado_en(self) -> float | None:
        """Cuándo mandó Sirius callar lo que sonaba; ``None`` si nunca lo hizo."""
        return self._parado_en

    def suena(self, sonido: Sonido) -> None:
        self._sonados.append((sonido, _ahora()))
        if self.con_eco:
            self._micro.suena(sonido)
        if self.sigue_sonando:
            self._sonando = sonido

    def para(self) -> None:
        """Sirius manda callar: lo que sonaba deja de sonar, y queda apuntado cuándo."""
        if self._sonando is not None:
            self._parado_en = _ahora()
            self._sonando = None

    def acaba(self) -> None:
        """La prueba deja que lo que sonaba termine por sí solo. No lo llama Sirius."""
        self._sonando = None


@dataclass
class RelojDeMentira:
    """El reloj con el que Sirius mide cuánto hace que acabó la charla."""

    ahora: float = 1_000_000.0

    def avanza(self, segundos: float) -> None:
        self.ahora += segundos


class ModeloDeMentira(_ProveedorGrabador):
    """El modelo grabador de la 0.2, con reloj.

    Apunta cuándo dio por acabada cada respuesta (``acabo_en``), y puede contestar
    a trozos con una pausa entre ellos, como un modelo que tarda
    (``contesta_despacio``): así una prueba puede ver que Sirius empezó a hablar
    antes de que el modelo acabara.
    """

    def __init__(self, respuestas: Iterator[str]) -> None:
        super().__init__(respuestas)
        self._trozos: list[str] | None = None
        self._pausa = 0.0
        self._tras_el_primer_trozo: Callable[[], None] | None = None
        self._acabo_en: float | None = None

    @property
    def acabo_en(self) -> float | None:
        """Cuándo dio por terminada su última respuesta; ``None`` si aún no ha contestado."""
        return self._acabo_en

    def contesta_despacio(
        self,
        trozos: Sequence[str],
        *,
        pausa: float,
        tras_el_primer_trozo: Callable[[], None] | None = None,
    ) -> None:
        """La próxima respuesta llega a trozos, con ``pausa`` segundos antes de cada uno.

        ``tras_el_primer_trozo`` se llama una vez, en el hilo que consume el modelo,
        con el primer trozo ya entregado y antes de entregar el segundo: tiene que
        volver en el acto, porque mientras no vuelva el modelo no sigue. Lo que
        tarde, un hilo aparte: ahí una prueba puede esperar a que suene la primera
        frase y hacer que el propietario hable encima mientras el modelo escribe.
        """
        self._trozos = list(trozos)
        self._pausa = pausa
        self._tras_el_primer_trozo = tras_el_primer_trozo

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        if self._trozos is None:
            for evento in super().stream_response(request):
                if isinstance(evento, LLMCompleted):
                    self._acabo_en = _ahora()
                yield evento
            return
        trozos, self._trozos = self._trozos, None
        gancho, self._tras_el_primer_trozo = self._tras_el_primer_trozo, None
        self.peticiones.append(Peticion(request.instructions, request.input_text))
        texto = ""
        for indice, trozo in enumerate(trozos):
            if indice == 1 and gancho is not None:
                gancho()
            time.sleep(self._pausa)
            texto += trozo
            yield LLMTextDelta(text=trozo)
        self._acabo_en = _ahora()
        yield LLMCompleted(text=texto, input_tokens=1, output_tokens=len(texto))


# --- Lo que el conductor devuelve a las pruebas ------------------------------


@dataclass(frozen=True, slots=True)
class TurnoDeVoz:
    """Lo que pasó después de que algo sonara por el micro.

    ``oido`` es lo que Sirius dio por dicho, o ``None`` si el turno no se cerró
    o el micro estaba cerrado. ``para_el`` dice si Sirius lo tomó como dicho a
    él. ``contestado`` es lo que escribió, y ``hablado`` lo que fue diciendo
    por el altavoz, frase a frase. ``aviso`` es lo que Sirius enseña si no
    puede oír o hablar, por ejemplo porque falta un modelo. Los tiempos no van
    aquí: se calculan con los relojes de los dobles (``micro.leido_en``,
    ``altavoz.sonados``, ``altavoz.parado_en``, ``modelo.acabo_en``), para que
    no los ponga quien implementa la pieza.
    """

    oido: str | None
    para_el: bool
    contestado: str | None
    hablado: tuple[str, ...]
    aviso: str = ""


@dataclass(frozen=True, slots=True)
class VozCandidata:
    """Una voz de la prueba a ciegas: su etiqueta sin nombre y sus muestras, una por frase."""

    etiqueta: str
    muestras: Mapping[str, Sonido]


@dataclass(frozen=True, slots=True)
class HojaDeVoces:
    """La prueba a ciegas de la voz: las frases, las candidatas barajadas y lo que él ve."""

    frases: tuple[str, ...]
    candidatas: tuple[VozCandidata, ...]
    #: El texto de la hoja tal como se ve, botones incluidos: ahí tienen que estar
    #: cada etiqueta y cada frase, y ninguna voz por su nombre.
    lo_que_ve_el_propietario: str


class VentanaDeVoz(VentanaDePrueba):
    """La ventana de Sirius con lo que la 0.3 le añade: el indicador de escucha y el silencio."""

    def indicador_de_escucha(self) -> str:
        """«Escuchando», «En silencio» o «Hablando», tal como se ve; vacío si no se ve.

        Se lee de ``listening_label``, el indicador de la ventana de verdad, como
        ``indicador_de_modo`` lee ``mode_label``: la pieza D lo pone con ese nombre.
        """
        etiqueta = self._ventana.listening_label
        return "" if etiqueta.isHidden() else str(etiqueta.text())

    def pulsa_silencio(self) -> None:
        """Pulsa ``mute_button``, el botón de la ventana que calla el micrófono y lo reabre."""
        self._ventana.mute_button.click()

    def mensajes(self) -> tuple[tuple[str, str], ...]:
        """La charla tal como se ve: (quién, texto), en orden. Quién es «propietario» o «Sirius».

        Se lee de la lista de mensajes de la ventana de verdad, la misma de la
        charla escrita: el prefijo «Tú» o «Sirius» de cada fila y su texto tal
        como se pinta. No se le pregunta a nadie.
        """
        from PySide6.QtWidgets import QLabel

        from sirius.presentation.message_view import MessageItemWidget

        lista = self._ventana.message_list
        widgets = [lista.itemWidget(lista.item(i)) for i in range(lista.count())]
        charla: list[tuple[str, str]] = []
        for widget in widgets:
            if not isinstance(widget, MessageItemWidget):
                continue
            prefijo = widget.findChild(QLabel)
            assert isinstance(prefijo, QLabel)
            quien = "propietario" if prefijo.text() == "Tú" else "Sirius"
            charla.append((quien, widget.rendered_plain_text()))
        return tuple(charla)


def _enciende_los_registradores_de_sirius() -> None:
    """Vuelve a encender ``sirius`` y cada ``sirius.*`` que la migración apagó."""
    registradores = logging.root.manager.loggerDict
    for nombre, registrador in list(registradores.items()):
        es_de_sirius = nombre == "sirius" or nombre.startswith("sirius.")
        if es_de_sirius and isinstance(registrador, logging.Logger):
            registrador.disabled = False
    logging.getLogger("sirius").disabled = False


# --- El conductor ------------------------------------------------------------


class ConductorDeVoz(Conductor):
    """Sirius de verdad, con la charla de la 0.2 y el oído y la voz de la 0.3 encima.

    Monta lo mismo que el conductor de la 0.2 y, además, la tubería de voz con
    los dobles de arriba en lugar del micro, del oído, del transcriptor, de la
    voz y del altavoz de verdad; el modelo de la charla es el grabador de la 0.2
    con reloj. ``oye`` hace sonar algo por el micro y espera a que Sirius
    termine con ello, como ``di`` escribe y espera.

    Desde que se construye hasta que se cierra (``cierra``), el vigilante le
    cuenta cada fichero que algo abre para escribir, cada conexión y cada proceso
    lanzado: no solo durante un turno, también al arrancar la escucha, al abrir la
    ventana, al elegir una voz o al cerrar.
    """

    def __init__(
        self,
        carpeta: Path,
        *,
        respuestas: Sequence[str] = (),
        ajustes: Mapping[str, object] | None = None,
    ) -> None:
        self.micro = MicroDeMentira()
        self.oido = OidoDeMentira()
        self.transcriptor = TranscriptorDeMentira()
        self.voz = VozDeMentira()
        self.altavoz = AltavozDeMentira(self.micro)
        self.reloj = RelojDeMentira()
        self._escrituras: list[Path] = []
        self._conexiones: list[str] = []
        self._procesos: list[str] = []
        # Las rutas se saben antes de montar nada: el vigilante y la foto del disco
        # empiezan antes de que Sirius se monte, para ver también lo que la tubería
        # haga al montarse.
        rutas = resolve_paths()
        self._permitidas = Permitidas(
            base=rutas.data_dir / "sirius.db",
            ajustes=rutas.config_dir / _CONFIG_FILE_NAME,
            diario=rutas.logs_dir / LOG_FILE_NAME,
        )
        self._temporal = Path(tempfile.gettempdir())
        self._carpetas_vigiladas = (
            carpeta,
            self._temporal,
            rutas.data_dir,
            rutas.config_dir,
            rutas.logs_dir,
        )
        self._ficheros_de_antes = self._ficheros_de_audio()
        _vigilar()
        _vigila(self)
        try:
            super().__init__(carpeta, respuestas=respuestas, ajustes=ajustes)
        except BaseException:
            _deja_de_vigilar(self)
            raise
        assert self.base == self._permitidas.base, "la base del conductor de la 0.2 cambió de sitio"
        # El diario, como en producción (`sirius.main`): es ruta permitida, y las
        # pruebas miran que lo oído que no era para él no acabe ahí. La configuración
        # de Alembic (`migrations/env.py`, `fileConfig`) apaga al migrar todos los
        # registradores que ya existían, el `sirius` y cada `sirius.*` de módulo, y
        # `configure_logging` no los vuelve a encender: aquí se encienden todos, para
        # que lo que la tubería escriba por el suyo llegue al diario de verdad.
        configure_logging(rutas.logs_dir)
        _enciende_los_registradores_de_sirius()
        # El modelo de la charla: el grabador de la 0.2 con reloj encima. Es el mismo
        # que ve `peticiones`, y el que la pieza C tiene que escuchar a trozos.
        self.modelo = ModeloDeMentira(_respuestas(respuestas))
        self.modelo.peticiones = self._grabador.peticiones
        self._grabador = self.modelo
        self._dependencias.send_message_use_case.set_llm_provider(self.modelo)

    # --- Pieza B: oír en local ---

    def oye(self, texto: str, *, y_calla: int = 1) -> TurnoDeVoz:
        """Suena ``texto`` por el micro, y después ``y_calla`` silencios.

        Antes, Sirius tiene que estar escuchando (``_escuchando``): con el micro
        cerrado, lo que suena se pierde, como en uno de verdad. Devuelve cuando
        Sirius ha terminado con ello: ha contestado, ha decidido que no era para
        él, o se ha quedado esperando a que el detector dé el turno por acabado
        (entonces ``oido`` es ``None``).
        """
        self._escuchando()
        self._suena(Sonido(texto), silencios=y_calla)
        return self._turno_de_voz()

    def calla(self, silencios: int) -> TurnoDeVoz:
        """Suenan ``silencios`` silencios más por el micro; qué pasa con el turno que esperaba."""
        self._suena(None, silencios=silencios)
        return self._turno_de_voz()

    def habla_encima(self, texto: str) -> None:
        """El propietario habla mientras Sirius está en lo suyo: suena ``texto`` y un silencio
        por el micro, y no se espera a nada. Para hablarle encima mientras el modelo escribe."""
        self._suena(Sonido(texto), silencios=1)

    def _suena(self, sonido: Sonido | None, *, silencios: int) -> None:
        if sonido is not None:
            self.micro.suena(sonido)
        for _ in range(silencios):
            self.micro.suena(Sonido(""))

    def _escuchando(self) -> None:
        """Arranca la escucha de Sirius si no está arrancada, y abre con ella el micro.

        Es lo mismo que hace la ventana al abrirse (PA-R03-04); sin ventana, lo
        hace el primer ``oye``. No quita un silencio pulsado: con el micro
        cerrado por el botón, lo que suena se pierde.
        """
        raise _pendiente("B")

    def _turno_de_voz(self) -> TurnoDeVoz:
        """Deja a Sirius hacer con lo que ha sonado hasta que termine, y lo resume."""
        raise _pendiente("B")

    def charla_guardada(self) -> tuple[tuple[str, str], ...]:
        """La charla tal como queda en la base: (quién, texto), en orden.

        Se lee de la tabla de mensajes con SQLite, como ``busca_en_toda_la_base``;
        no se le pregunta a nadie. Un mensaje olvidado queda con el texto vacío.
        """
        with closing(sqlite3.connect(self.base)) as conexion:
            filas = conexion.execute(
                "SELECT role, content FROM messages ORDER BY conversation_id, sequence"
            ).fetchall()
        return tuple(
            ("propietario" if rol == "user" else "Sirius", contenido or "")
            for rol, contenido in filas
        )

    def conexiones_de_red(self) -> list[str]:
        """Las direcciones a las que algo intentó conectarse o enviar desde que arrancó."""
        return list(self._conexiones)

    def procesos_lanzados(self) -> list[str]:
        """Las órdenes de cada proceso que algo lanzó desde que arrancó."""
        return list(self._procesos)

    def anota_conexion(self, direccion: str) -> None:
        """Lo llama el vigilante por cada conexión o envío mientras el conductor vive."""
        self._conexiones.append(direccion)

    def anota_proceso(self, orden: str) -> None:
        """Lo llama el vigilante por cada proceso lanzado mientras el conductor vive."""
        self._procesos.append(orden)

    def destinos_posibles_de_la_voz(self) -> frozenset[str]:
        """Adónde pueden ir el oído y la voz del robot según sus ajustes: todo lo elegible.

        Se lee del modelo de ajustes de la voz: si tuviera un campo de servidor,
        de dirección o de clave, su destino aparecería aquí.
        """
        raise _pendiente("B")

    def quita_los_modelos_de_voz(self) -> None:
        """Deja a Sirius sin los modelos de oír y hablar, como un ordenador sin instalarlos."""
        raise _pendiente("B")

    def orden_para_instalar_la_voz(self) -> str:
        """La orden que el propietario tiene que ejecutar para instalar los modelos de la voz."""
        raise _pendiente("B")

    # --- Pieza C: hablar en local ---

    def el_modelo_contesta_despacio(
        self,
        frases: Sequence[str],
        *,
        pausa: float = 0.5,
        tras_el_primer_trozo: Callable[[], None] | None = None,
    ) -> None:
        """La próxima respuesta llega a trozos, con ``pausa`` segundos antes de cada uno."""
        self.modelo.contesta_despacio(
            frases, pausa=pausa, tras_el_primer_trozo=tras_el_primer_trozo
        )

    def herramientas(self) -> Mapping[str, str]:
        """Con qué oye y habla Sirius, por nombre: «voz», «fin de turno», «texto» y «habla».

        Se lee de los módulos de los procesadores que monta la raíz de composición
        de producción, no de una constante.
        """
        raise _pendiente("C")

    # --- Pieza D: escucha siempre y a quién le hablan ---

    def segundos_de_charla(self) -> float:
        """Cuánto dura la charla después de que Sirius calle: hasta entonces sobra el nombre."""
        raise _pendiente("D")

    def ficheros_de_audio_nuevos(self) -> list[Path]:
        """Audio aparecido desde que arrancó el conductor, en sus carpetas o en la temporal."""
        return sorted(self._ficheros_de_audio() - self._ficheros_de_antes)

    def escrituras_en_disco(self) -> list[Path]:
        """Lo que algo abrió para escribir desde que arrancó, aunque lo borrara después.

        Todo lo que no sea la base de Sirius, sus ajustes o su diario, esté donde
        esté y se llame como se llame (``es_escritura_sospechosa``).
        """
        return list(self._escrituras)

    def anota_escritura(self, ruta: Path) -> None:
        """Lo llama el vigilante por cada fichero que algo abre para escribir mientras vive."""
        if es_escritura_sospechosa(ruta, self._permitidas):
            self._escrituras.append(ruta)

    def audio_en_la_base(self) -> list[str]:
        """Las ``tabla.columna`` de la base con un BLOB que empieza como un fichero de audio.

        Se recorre cada tabla y cada columna, como ``busca_en_toda_la_base``; las
        huellas son BLOB y no empiezan así. Ninguna, si solo guarda texto y huellas.
        """
        encontrados: list[str] = []
        with closing(sqlite3.connect(self.base)) as conexion:
            tablas = [
                fila[0]
                for fila in conexion.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                    " AND name NOT LIKE 'sqlite_%'"
                )
            ]
            for tabla in tablas:
                columnas = [fila[1] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')]
                for columna in columnas:
                    consulta = (
                        f'SELECT substr("{columna}", 1, 4) FROM "{tabla}"'
                        f" WHERE typeof(\"{columna}\") = 'blob'"
                    )
                    cabeceras = (
                        bytes(valor) for (valor,) in conexion.execute(consulta) if valor is not None
                    )
                    if any(cabecera.startswith(_CABECERAS_DE_AUDIO) for cabecera in cabeceras):
                        encontrados.append(f"{tabla}.{columna}")
        return encontrados

    def el_diario_contiene(self, texto: str) -> bool:
        """Si el diario de Sirius, que sí puede escribir, guarda ``texto``, rotaciones incluidas."""
        diario = self._permitidas.diario
        if not diario.parent.exists():
            return False
        buscado = texto.casefold()
        return any(
            buscado in fichero.read_text(encoding="utf-8", errors="replace").casefold()
            for fichero in diario.parent.glob(f"{diario.name}*")
            if fichero.is_file()
        )

    def ventana(self, qtbot: Any) -> VentanaDeVoz:
        return VentanaDeVoz(self.abre_la_ventana(qtbot), qtbot)

    # --- Pieza E: cortarle ---

    def oye_mientras_habla(self, texto: str) -> TurnoDeVoz:
        """El propietario habla mientras el altavoz sigue sonando con la respuesta anterior."""
        self._suena(Sonido(texto), silencios=1)
        return self._turno_de_voz()

    # --- Pieza F: elegir su voz ---

    def hoja_de_voces(self) -> HojaDeVoces:
        raise _pendiente("F")

    def elige_voz(self, etiqueta: str) -> None:
        del etiqueta
        raise _pendiente("F")

    def voz_tras(self, etiqueta: str) -> str:
        """La voz de verdad tras una etiqueta de la hoja: la ve la prueba, no el propietario."""
        del etiqueta
        raise _pendiente("F")

    def escucha_en_la_hoja(self, etiqueta: str, frase: str) -> None:
        """Escuchar en la hoja la muestra de ``frase`` con la voz ``etiqueta``, como su botón."""
        del etiqueta, frase
        raise _pendiente("F")

    def hay_forma_de_clonar_una_voz(self) -> bool:
        """Si algún camino de Sirius acepta un audio de alguien para imitar su voz."""
        raise _pendiente("F")

    # --- Lo que es solo de las pruebas ---

    def reabre(self) -> None:
        """Cierra Sirius y lo vuelve a abrir, arranque incluido; el diario sigue encendido.

        Volver a arrancar vuelve a migrar, y la migración apaga otra vez los
        registradores: se encienden de nuevo, como al construir.
        """
        super().reabre()
        _enciende_los_registradores_de_sirius()

    def cierra(self) -> None:
        """Cierra Sirius; lo que escriba al cerrar también lo ve el vigilante."""
        try:
            super().cierra()
        finally:
            _deja_de_vigilar(self)

    def _ficheros_de_audio(self) -> frozenset[Path]:
        encontrados: set[Path] = set()
        for carpeta in self._carpetas_vigiladas:
            if not carpeta.exists():
                continue
            crudo_cuenta = carpeta != self._temporal
            for fichero in carpeta.rglob("*"):
                sufijo = fichero.suffix.lower()
                if sufijo in EXTENSIONES_DE_AUDIO or (
                    crudo_cuenta and sufijo in EXTENSIONES_DE_AUDIO_CRUDO
                ):
                    encontrados.add(fichero)
        return frozenset(encontrados)


def percentil(valores: Sequence[float], p: int) -> float:
    """El percentil ``p`` de ``valores``, por el método del rango más cercano."""
    ordenados = sorted(valores)
    return ordenados[max(0, -(-p * len(ordenados) // 100) - 1)]
