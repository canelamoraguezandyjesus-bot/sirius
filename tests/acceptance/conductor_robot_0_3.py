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

import functools
import ipaddress
import logging
import os
import re
import sqlite3
import sys
import tempfile
import threading
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

from sirius.adapters.persistence.models import Base
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

    def anota_sentencia(self, sql: str, base: str = "") -> None: ...


#: Los conductores vivos, desde que se construyen hasta que se cierran: a ellos les
#: llega cada apertura de fichero para escribir, cada conexión o envío y cada proceso
#: lanzado. Débil, para que un conductor olvidado no se quede vigilando.
_EN_UN_TURNO: weakref.WeakSet[Vigilado] = weakref.WeakSet()
_GANCHO_PUESTO = False
#: Si la conexión a SQLite que se está abriendo en este hilo pasa por el ``connect`` vigilado.
_CONECTANDO = threading.local()
#: Lo que se apunta como sentencia cuando una conexión no pasa por ese ``connect``.
_CONEXION_SIN_VIGILAR = "-- una conexión a la base que no pasó por sqlite3.connect"
#: Lo que se apunta cuando una conexión vigilada apaga los disparadores de SQLite.
_APAGO_LOS_DISPARADORES = "-- una conexión apagó los disparadores"
_MARCAS_DEL_VIGILANTE = frozenset({_CONEXION_SIN_VIGILAR, _APAGO_LOS_DISPARADORES})
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


def _resolucion(anfitrion: object) -> tuple[str, str] | None:
    """La resolución de ``anfitrion`` como conexión, o ``None`` si es numérico o no hay."""
    if isinstance(anfitrion, bytes):
        anfitrion = anfitrion.decode(errors="replace")
    if not anfitrion or _es_direccion_numerica(str(anfitrion)):
        return None
    return "conexion", f"resolver {anfitrion!r}"


def _es_direccion_numerica(anfitrion: str) -> bool:
    try:
        ipaddress.ip_address(anfitrion.strip("[]"))
    except ValueError:
        return False
    return True


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
    """Pone, una vez por proceso, lo que ve cada escritura, conexión, proceso y sentencia.

    Un gancho de auditoría de Python no se puede quitar, así que se pone una vez y
    solo trabaja mientras algún conductor está vivo. Ve todo lo que abre Python
    para escribir, también ``tempfile`` y lo que se borra después, cada
    ``socket.connect``, cada envío sin conexión (``sendto``, ``sendmsg``) y cada
    proceso que lanza Python, por ``subprocess`` o por ``os`` (rondas 1 y 2 de
    Codex y revisión propia de la PR #686). Y envuelve ``sqlite3.connect``, que es
    por donde conectan ``sqlite3`` y SQLAlchemy, para que cada conexión abierta
    mientras alguien vigila cuente cada sentencia que ejecuta, con sus valores
    puestos: así se ve lo que se escribe en la base aunque se borre antes de que
    nadie mire (ronda 6 de Codex). El evento de auditoría de cada conexión llega
    antes de que esté construida, así que no sirve para trazarla; sirve para ver la
    que no pasó por ``connect`` y apuntarla como tal. Lo que escriba, envíe o lance
    una biblioteca en C por su cuenta no pasa por aquí, y por eso el disco y la base
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
                elif que == "sentencia":
                    conductor.anota_sentencia(dato)
                else:
                    conductor.anota_proceso(dato)
            except OSError, ValueError, RuntimeError:
                # Una ruta que no se puede resolver tampoco puede abortar lo ajeno.
                continue

    conecta_de_verdad = sqlite3.dbapi2.connect

    @functools.wraps(conecta_de_verdad)
    def conecta(*args: Any, **kwargs: Any) -> Any:
        if not _EN_UN_TURNO:
            return conecta_de_verdad(*args, **kwargs)
        # La conexión sale de una clase cuyo ``set_trace_callback`` no quita al vigilante:
        # una pieza puede poner su trazador, o ninguno, y el vigilante sigue viendo. Una
        # fábrica que no sea una clase de conexión no se puede envolver, y se apunta.
        argumentos = list(args)
        fabrica = kwargs.get("factory", argumentos[5] if len(argumentos) > 5 else None)
        envuelta = fabrica is None or (
            isinstance(fabrica, type) and issubclass(fabrica, sqlite3.Connection)
        )
        if envuelta:
            if len(argumentos) > 5:
                argumentos[5] = _vigilada(argumentos[5])
            else:
                kwargs["factory"] = _vigilada(fabrica or sqlite3.Connection)
        _CONECTANDO.vigilada = True
        try:
            conexion = conecta_de_verdad(*argumentos, **kwargs)
        finally:
            _CONECTANDO.vigilada = False
        base = kwargs.get("database", argumentos[0] if argumentos else "")
        traza = functools.partial(_traza, base=_nombre_de_la_base(base))
        try:
            if envuelta:
                conexion._traza_del_vigilante = traza
            conexion.set_trace_callback(traza)
        except AttributeError, sqlite3.Error:
            envuelta = False
        if not envuelta:
            # Una conexión que no se deja envolver ni trazar se apunta como no seguida.
            _traza(_CONEXION_SIN_VIGILAR)
        return conexion

    sys.addaudithook(gancho)
    sqlite3.connect = conecta
    sqlite3.dbapi2.connect = conecta
    _GANCHO_PUESTO = True


_VIGILADAS: dict[type[sqlite3.Connection], type[sqlite3.Connection]] = {}


def _vigilada(fabrica: type[sqlite3.Connection]) -> type[sqlite3.Connection]:
    """La clase de conexión pedida, con el vigilante dentro.

    Su ``set_trace_callback`` no quita al vigilante: una pieza puede poner su propio
    trazador, o quitarlo con ``None``, y el del vigilante sigue viendo cada sentencia
    mientras el suyo recibe lo mismo. Y si apaga los disparadores de SQLite con
    ``setconfig``, queda apuntado. Quien llame a los métodos de ``sqlite3.Connection``
    sin ligar, saltándose su propia clase, se salta esto: eso ya no es una pieza que
    ataja, es una que engaña al arnés, y queda escrito en lo que estas pruebas no
    garantizan.
    """
    if fabrica in _VIGILADAS:
        return _VIGILADAS[fabrica]
    if fabrica in _VIGILADAS.values():
        return fabrica

    class ConexionVigilada(fabrica):  # type: ignore[misc,valid-type]
        def set_trace_callback(self, trace_callback: Callable[[str], object] | None) -> None:
            mia = getattr(self, "_traza_del_vigilante", None)
            if mia is None:
                super().set_trace_callback(trace_callback)
                return
            if trace_callback is None or trace_callback is mia:
                super().set_trace_callback(mia)
                return

            def las_dos(sql: str) -> None:
                mia(sql)
                trace_callback(sql)

            super().set_trace_callback(las_dos)

        def setconfig(self, op: int, enable: bool = True) -> None:
            mia = getattr(self, "_traza_del_vigilante", None)
            if mia is not None and op == sqlite3.SQLITE_DBCONFIG_ENABLE_TRIGGER and not enable:
                mia(_APAGO_LOS_DISPARADORES)
            super().setconfig(op, enable)

    _VIGILADAS[fabrica] = ConexionVigilada
    return ConexionVigilada


def _traza(sql: str, base: str = "") -> None:
    """Una sentencia que acaba de ejecutar una conexión vigilada, con sus valores puestos.

    ``base`` es la base a la que iba, tal como se pidió al conectar.
    """
    try:
        conductores = list(_EN_UN_TURNO)
    except RuntimeError:
        return
    for conductor in conductores:
        try:
            conductor.anota_sentencia(sql, base)
        except ValueError, RuntimeError:
            continue


def _lo_que_ve(evento: str, args: tuple[Any, ...]) -> tuple[str, str] | None:
    """Qué es este evento de auditoría para el vigilante, o ``None`` si no le importa."""
    if evento == "sqlite3.connect/handle":
        # La conexión llega sin acabar de construirse: no se puede trazar desde aquí. Si
        # la abre el ``connect`` vigilado, él la traza al volver; si no, queda apuntada.
        if getattr(_CONECTANDO, "vigilada", False):
            return None
        return ("sentencia", _CONEXION_SIN_VIGILAR)
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
    if evento in ("socket.getaddrinfo", "socket.gethostbyname"):
        # Resolver un nombre ya es una consulta que sale del ordenador, aunque la
        # conexión de después no llegue; una dirección numérica no se resuelve.
        return _resolucion(args[0])
    if evento in ("socket.gethostbyaddr", "socket.getnameinfo"):
        # La resolución inversa de una dirección también sale: aquí cuenta siempre.
        return "conexion", f"resolver {args[0]!r}"
    if evento == "socket.bind":
        # Enlazar a un nombre lo resuelve en C sin pasar por getaddrinfo.
        _toma, direccion = args
        anfitrion = direccion[0] if isinstance(direccion, tuple) and direccion else None
        return _resolucion(anfitrion) if isinstance(anfitrion, str | bytes) else None
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

    def de(self, quien: str) -> bool:
        """Si ``quien`` está entre quienes produjeron este sonido: un audio mezclado tiene dos."""
        return quien in self.de_quien.split(" y ")


def _mezcla(eco: Sonido, sonido: Sonido) -> Sonido:
    """Lo que capta un micro delante de un altavoz encendido: el eco y lo que suena delante,
    en un solo audio. Si delante no hay más que silencio, solo el eco."""
    if sonido.es_silencio:
        return Sonido(eco.texto, de_quien="sirius", voz=eco.voz)
    mezclado = f"{eco.texto} {sonido.texto}"
    return Sonido(mezclado, de_quien=f"{sonido.de_quien} y sirius", voz=eco.voz)


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


#: Las tablas de la base de la 0.2 el 13-10-2026, tal como las deja `initialize_persistence`,
#: medidas con `PRAGMA table_list`: las de verdad, las virtuales de la búsqueda por palabras
#: con sus sombras (la de los mensajes lee de `messages` y no tiene sombra de contenido) y la
#: de Alembic. La 0.3 no añade ninguna: si una pieza necesitara una, la añade aquí y su
#: revisión lo ve; y `test_dobles_del_conductor.py` compara el inventario con la base de
#: verdad en los dos sentidos cada vez que corre.
TABLAS_DE_LA_0_2: frozenset[str] = frozenset(
    {
        "alembic_version",
        "conversation_modes",
        "conversation_summaries",
        "conversations",
        "day_summaries",
        "decision_revisions",
        "decisions",
        "events",
        "identities",
        "identity_versions",
        "judge_scores",
        "knowledge_fts",
        "knowledge_fts_config",
        "knowledge_fts_content",
        "knowledge_fts_data",
        "knowledge_fts_docsize",
        "knowledge_fts_idx",
        "llm_usage",
        "memories",
        "memory_embeddings",
        "memory_revisions",
        "memory_suggestions",
        "message_fts",
        "message_fts_config",
        "message_fts_data",
        "message_fts_docsize",
        "message_fts_idx",
        "messages",
        "project_revisions",
        "projects",
        "reply_marks",
    }
)

#: Las columnas de cada tabla del modelo de producción.
_COLUMNAS_DEL_MODELO: Mapping[str, frozenset[str]] = {
    tabla.name: frozenset(columna.name for columna in tabla.columns)
    for tabla in Base.metadata.tables.values()
}

#: Las dos tablas del arnés en la base: lo que vieron sus disparadores y cuántas filas y
#: cuánto texto escribió cada tabla desde que arrancó Sirius.
TABLAS_DE_LA_PRUEBA: frozenset[str] = frozenset({"_vigilancia_escrituras", "_vigilancia_filas"})
#: Las sombras de los índices de texto de la 0.2: las únicas tablas en las que SQLite
#: escribe desde dentro de otra sentencia al charlar.
_SOMBRAS_DE_LA_0_2: frozenset[str] = frozenset(
    t for t in TABLAS_DE_LA_0_2 if t.endswith(("_config", "_content", "_data", "_docsize", "_idx"))
)

#: En estas pruebas el modelo de huellas no da ninguna, así que la charla no escribe
#: binario en ninguna columna del modelo; las sombras de los índices de texto sí son
#: binarias por construcción, pero en bloques pequeños. Un texto de la charla no llega a
#: 16 KiB; una captura de audio son miles de muestras, así que mil filas de más no son
#: charla; y veinte turnos de charla escriben 5 590 caracteres de texto en total
#: fuera del arranque (medido el 14-10-2026 con los disparadores y el modelo de mentira),
#: más de noventa veces menos que el tope.
_BLOQUE_MAS_GRANDE = 16 * 1024
_TEXTO_LARGO = 16 * 1024
_FILAS_DE_MAS = 1_000
_TEXTO_TOTAL = 512 * 1024

#: Un literal del SQL expandido: ``x'...'`` es binario; ``'...'``, texto con las comillas
#: dobladas. Se recorren de izquierda a derecha, así que un ``x'`` dentro de un texto no
#: se confunde con binario. Solo sirven para no leer verbos dentro de un texto.
_LITERAL = re.compile(r"[xX]'([0-9A-Fa-f]*)'|'((?:[^']|'')*)'")
_ESCRIBE = re.compile(r"\b(?:INSERT|REPLACE|UPDATE|DELETE|CREATE|ALTER|DROP)\b", re.IGNORECASE)
_CAMBIA_EL_ESQUEMA = re.compile(r"\b(?:CREATE|ALTER|DROP)\b", re.IGNORECASE)
#: Lo que toca la estructura sin ser una escritura: enganchar otra base o abrir el esquema.
_TOCA_LA_ESTRUCTURA = re.compile(r"(?:ATTACH|PRAGMA\s+writable_schema)\b", re.IGNORECASE)
#: La tabla que sigue a INTO, UPDATE, TABLE o FROM, con o sin esquema delante y entre
#: cualquiera de las comillas que admite SQLite (el índice de texto escribe
#: ``'main'.'message_fts_data'``).
_TABLA_DE_LA_SENTENCIA = re.compile(
    r"\b(?:INTO|UPDATE(?:\s+OR\s+\w+)?|TABLE(?:\s+IF\s+(?:NOT\s+)?EXISTS)?|FROM)\s+"
    r"(?:['\"`\[]?\w+['\"`\]]?\s*\.\s*)?['\"`\[]?(\w+)",
    re.IGNORECASE,
)
#: Una sentencia que SQLite ejecuta dentro de otra llega con ``-- `` delante de cada línea.
_ANIDADA = re.compile(r"^-- ?", re.MULTILINE)
#: Las tres operaciones sobre una fila, con el suceso de SQLite de cada una.
_OPERACIONES = {"insertar": "INSERT", "actualizar": "UPDATE", "borrar": "DELETE"}


def _sin_literales(sql: str) -> str:
    """La sentencia sin sus literales: solo palabras del SQL, nombres y signos."""
    return _LITERAL.sub(" ", sql)


def _tabla_de(sql: str) -> str:
    """La tabla sobre la que escribe la sentencia, o su principio si no se ve."""
    visto = _TABLA_DE_LA_SENTENCIA.search(sql)
    return visto.group(1) if visto else _sin_literales(sql)[:40].strip()


def _nombre_de_la_base(base: object) -> str:
    """La base tal como se pidió al conectar, en texto."""
    try:
        return os.fsdecode(base)  # type: ignore[arg-type]
    except TypeError:
        return str(base)


def _en_memoria(base: str) -> bool:
    """Si una base pedida al conectar vive solo en memoria: ahí no se guarda nada."""
    return base in ("", ":memory:") or "mode=memory" in base


def _misma_base(pedida: str, base: Path) -> bool:
    """Si la base pedida al conectar es ``base``, comparando las rutas de verdad."""
    try:
        return Path(pedida.removeprefix("file:")).resolve() == base.resolve()
    except OSError, ValueError:
        return False


def _texto_sql(valor: str) -> str:
    return valor.replace("'", "''")


def _disparador(tabla: str, columnas: Sequence[str], operacion: str) -> str:
    """El disparador del arnés para ``tabla`` y ``operacion``: insertar, actualizar o borrar.

    Apunta en ``_vigilancia_escrituras`` todo BLOB y todo texto de más de 16 KiB que
    entra (``NEW``) y, al actualizar o borrar, también el que había (``OLD``), que es como
    se ve lo que se escribió a trozos con ``blobopen``; y suma en ``_vigilancia_filas``
    las filas insertadas y el texto escrito o cambiado, se escriba como se escriba:
    con un literal, con un parámetro, con una función, desde otra tabla o desde una
    sentencia anidada.
    """
    t = _sql(tabla)
    miradas = {
        "insertar": (("NEW", "al insertar"),),
        "actualizar": (("NEW", "al actualizar"), ("OLD", "que tenía al actualizar")),
        "borrar": (("OLD", "al borrar"),),
    }[operacion]
    cuerpo: list[str] = []
    for fila, como in miradas:
        for columna in columnas:
            v = f'{fila}."{_sql(columna)}"'
            cuerpo.append(
                "INSERT INTO _vigilancia_escrituras"
                " (tabla, columna, operacion, tipo, largo, cabecera)"
                f" SELECT '{_texto_sql(tabla)}', '{_texto_sql(columna)}', '{como}', typeof({v}),"
                f" length({v}), hex(substr({v}, 1, 4))"
                f" WHERE typeof({v}) = 'blob'"
                f" OR (typeof({v}) = 'text' AND length({v}) > {_TEXTO_LARGO});"
            )
    if operacion != "borrar":
        nuevas = 1 if operacion == "insertar" else 0
        sumandos: list[str] = []
        for columna in columnas:
            c = _sql(columna)
            cambiada = "" if operacion == "insertar" else f' AND NEW."{c}" IS NOT OLD."{c}"'
            sumandos.append(
                f"(CASE WHEN typeof(NEW.\"{c}\") = 'text'{cambiada}"
                f' THEN length(NEW."{c}") ELSE 0 END)'
            )
        cuerpo.append(
            "INSERT INTO _vigilancia_filas (tabla, filas, texto)"
            f" VALUES ('{_texto_sql(tabla)}', {nuevas}, {' + '.join(sumandos) or '0'})"
            f" ON CONFLICT(tabla) DO UPDATE SET filas = filas + {nuevas},"
            " texto = texto + excluded.texto;"
        )
    return (
        f'CREATE TRIGGER "_vigila_{t}_{operacion}" AFTER {_OPERACIONES[operacion]} ON "{t}"'
        f" BEGIN {' '.join(cuerpo)} END"
    )


def _sql(identificador: str) -> str:
    return identificador.replace('"', '""')


#: Lo único de SQLite que no es una tabla de la base: su propio esquema. ``sqlite_stat1`` o
#: ``sqlite_sequence`` sí lo son, y la aplicación puede escribir en ellas.
_ESQUEMA_DE_SQLITE = frozenset({"sqlite_schema", "sqlite_master", "sqlite_temp_schema"})


def _tablas(conexion: sqlite3.Connection) -> dict[str, str]:
    """Cada tabla de la base con su tipo: ``table``, ``virtual`` o ``shadow``."""
    return {
        fila[1]: fila[2]
        for fila in conexion.execute("PRAGMA table_list")
        if fila[0] == "main" and fila[1] not in _ESQUEMA_DE_SQLITE
    }


def _lee_de_otra_tabla(conexion: sqlite3.Connection, tabla: str) -> bool:
    """Si la tabla virtual es un índice de contenido externo (``content='otra'``)."""
    fila = conexion.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
    ).fetchone()
    return bool(fila and fila[0] and "content='" in str(fila[0]).replace('"', "'"))


def _filas_por_tabla(conexion: sqlite3.Connection) -> dict[str, int | None]:
    """Cuántas filas tiene cada tabla, sombras incluidas; ``None`` si no se puede leer.

    Una tabla virtual de un módulo que esta conexión no carga no se puede contar:
    se devuelve ``None`` y ``audio_en_la_base`` la señala, en vez de reventar.
    """
    filas: dict[str, int | None] = {}
    for tabla in _tablas(conexion):
        try:
            filas[tabla] = int(
                conexion.execute(f'SELECT count(*) FROM "{_sql(tabla)}"').fetchone()[0]
            )
        except sqlite3.OperationalError:
            filas[tabla] = None
    return filas


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
        self._sentencias: list[tuple[bool, str, str]] = []
        self._arrancando = False
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
        self._ficheros_de_antes = self._ficheros_que_no_son_suyos()
        self._filas_de_antes = self._filas_de_la_base()
        _vigilar()
        _vigila(self)
        self._arrancando = True
        try:
            super().__init__(carpeta, respuestas=respuestas, ajustes=ajustes)
            assert self.base == self._permitidas.base, "la base de la 0.2 cambió de sitio"
            self._pone_los_disparadores()
        except BaseException:
            _deja_de_vigilar(self)
            raise
        finally:
            self._arrancando = False
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
        """Suena por el micro ``sonido`` y después ``silencios`` silencios.

        Si el altavoz sigue sonando y devuelve eco, el micro capta ese eco mezclado
        con cada cosa que suena, en un solo audio, como un micrófono delante de un
        altavoz encendido: la voz del propietario llega con el eco encima, y cada
        silencio llega como eco solo (rondas 4 y 5 de Codex sobre la PR #686). Es la
        física de los dobles, por sucesos y no por tiempo. La copia del eco de cada
        locución llega una vez, justo detrás de ``altavoz.suena``, se encienda o no
        ``sonando``, y se cancela siempre; mientras ``sonando`` la mantenga, llega
        dentro de cada audio y se cancela en cada uno; cuando Sirius la para, llega
        una vez más con lo ya captado; y se olvida cuando su copia ya se vio y no sigue
        sonando, porque lo que Sirius dijo alguna vez, dicho por el propietario, tiene
        que oírse. El audio que queda limpio llega al oído como silencio, y cuenta
        para cerrar el turno.
        """
        sonidos = ([sonido] if sonido is not None else []) + [Sonido("")] * silencios
        for cada in sonidos:
            eco = self.altavoz.sonando
            if self.altavoz.con_eco and eco is not None:
                cada = _mezcla(eco, cada)
            self.micro.suena(cada)

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

    def anota_sentencia(self, sql: str, base: str = "") -> None:
        """Lo llama el vigilante por cada sentencia SQL de cualquier conexión abierta mientras vive.

        Llegan con sus valores puestos y con la base a la que iban. Se guardan las que
        escriben o tocan la estructura, con si llegaron durante el arranque, que es
        cuando Sirius migra y el conductor pone sus disparadores; las lecturas, no.
        SQLite repite la misma sentencia al arrancar cada disparador que dispara, una
        vez por fila: la repetición seguida no se guarda, que aquí no se cuenta nada por
        sentencias, eso lo hacen los disparadores.
        """
        texto = sql.strip()
        apunte = (self._arrancando, base, texto)
        if self._sentencias and self._sentencias[-1] == apunte:
            return
        if (
            texto in _MARCAS_DEL_VIGILANTE
            or _TOCA_LA_ESTRUCTURA.match(texto)
            or _ESCRIBE.search(_sin_literales(texto))
        ):
            self._sentencias.append(apunte)

    def sentencias_que_escriben(self) -> list[str]:
        """Cada sentencia que escribió en una base mientras el conductor vive, arranque incluido."""
        return [sql for _, _, sql in self._sentencias]

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

    def ficheros_nuevos(self) -> list[Path]:
        """Lo aparecido desde antes de arrancar Sirius: en sus carpetas, cualquier fichero que
        no sea su base, sus ajustes o su diario, lo haya escrito quien lo haya escrito; en
        la temporal del sistema, los de audio.
        """
        return sorted(self._ficheros_que_no_son_suyos() - self._ficheros_de_antes)

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
        """Dónde la base ha cambiado como no cambia la charla de la 0.2: ahí habría audio.

        No se infiere qué es audio por su forma: se comprueba que la base solo cambia
        donde la 0.2 ya escribía (ronda 5 de Codex sobre la PR #686), y se mira dos
        veces, porque la foto final no ve lo que se escribe y se borra antes (ronda 6).
        La foto: las tablas son las de la 0.2 (``TABLAS_DE_LA_0_2``) y sus columnas las
        del modelo; ningún BLOB en ninguna columna del modelo, porque el modelo de
        huellas de estas pruebas no da ninguna; en las sombras de los índices, binarias
        por construcción, ningún bloque mayor de 16 KiB ni con cabecera de audio; ningún
        texto de más de 16 KiB; y ninguna tabla, sombras incluidas, crece más de mil
        filas desde antes de arrancar Sirius, que es menos que un segundo de muestras.
        Una tabla que falte o que no se pueda leer también se dice. Y lo que pasó
        mientras vivía: cada fila escrita la vieron los disparadores del arnés, y cada
        sentencia que tocó la estructura u otra base, el trazador
        (``_escrituras_sospechosas_en_la_base``). Vacío si la base solo ha cambiado como
        cambia charlando.
        """
        encontrados: list[str] = []
        with closing(sqlite3.connect(self.base)) as conexion:
            tablas = _tablas(conexion)
            encontrados.extend(
                f"{t} (tabla nueva)"
                for t in sorted(set(tablas) - TABLAS_DE_LA_0_2 - TABLAS_DE_LA_PRUEBA)
            )
            encontrados.extend(
                f"{t} (tabla que falta)" for t in sorted(TABLAS_DE_LA_0_2 - set(tablas))
            )
            filas = _filas_por_tabla(conexion)
            for tabla, tipo in sorted(tablas.items()):
                ahora = filas.get(tabla)
                if ahora is None:
                    encontrados.append(f"{tabla} (tabla que no se puede leer)")
                    continue
                if tabla not in TABLAS_DE_LA_0_2:
                    continue
                # Un índice de contenido externo no guarda nada suyo: lee de la tabla
                # real, que ya se mira. Lo demás, sombras incluidas, se mira columna a
                # columna: las sombras son binarias por construcción, pero ni grandes ni
                # con cabecera de audio.
                if not (tipo == "virtual" and _lee_de_otra_tabla(conexion, tabla)):
                    encontrados.extend(
                        self._columnas_sospechosas(conexion, tabla, binaria=tipo == "shadow")
                    )
                crecimiento = ahora - (self._filas_de_antes.get(tabla) or 0)
                if crecimiento > _FILAS_DE_MAS:
                    encontrados.append(f"{tabla} (+{crecimiento} filas)")
        encontrados.extend(self._escrituras_sospechosas_en_la_base())
        return encontrados

    def _escrituras_sospechosas_en_la_base(self) -> list[str]:
        """Lo que pasó en la base mientras el conductor vivía y no es charla, se haya
        borrado después o no.

        Dos ojos. Los disparadores del arnés (``_pone_los_disparadores``) ven cada fila
        que se escribe en una tabla de la 0.2, se escriba como se escriba: cualquier
        BLOB, un texto de más de 16 KiB, más de mil filas insertadas en una tabla y más
        de ``_TEXTO_TOTAL`` de texto en total desde el arranque. El trazador de
        sentencias (``_vigilar``) ve la estructura: un cambio de esquema fuera del
        arranque, una sentencia que SQLite ejecuta dentro de otra fuera de las sombras
        de los índices, que son las únicas que la charla provoca, una escritura en otra
        base que no sea de memoria, enganchar otra base o abrir el esquema a mano,
        tocar las tablas del arnés, apagar los disparadores y una conexión que no pasó
        por ``sqlite3.connect``, que es la que no se pudo seguir.
        """
        sospechosas: list[str] = []
        otras_bases: set[str] = set()
        for en_el_arranque, base, sentencia in self._sentencias:
            if sentencia == _CONEXION_SIN_VIGILAR:
                sospechosas.append("la base (una conexión que el vigilante no pudo seguir)")
                continue
            if sentencia == _APAGO_LOS_DISPARADORES:
                sospechosas.append("la base (una conexión apagó los disparadores)")
                continue
            if base and not _en_memoria(base) and not _misma_base(base, self.base):
                otras_bases.add(base)
                continue
            anidada = sentencia.startswith("--")
            sql = _ANIDADA.sub("", sentencia) if anidada else sentencia
            tabla = _tabla_de(sql)
            if anidada:
                if tabla not in _SOMBRAS_DE_LA_0_2:
                    sospechosas.append(
                        f"{tabla} (escritura dentro de otra sentencia, fuera de las sombras)"
                    )
                continue
            esqueleto = _sin_literales(sql)
            if not en_el_arranque and _CAMBIA_EL_ESQUEMA.search(esqueleto):
                sospechosas.append(f"{tabla} (esquema cambiado fuera del arranque)")
            if not en_el_arranque and tabla in TABLAS_DE_LA_PRUEBA:
                sospechosas.append(f"{tabla} (tocó la vigilancia de la prueba)")
            if tabla in ("sqlite_master", "sqlite_schema") or _TOCA_LA_ESTRUCTURA.match(sql):
                sospechosas.append(f"la base (tocó la estructura a mano: {esqueleto[:40].strip()})")
        sospechosas.extend(f"otra base escrita ({base})" for base in sorted(otras_bases))
        sospechosas.extend(self._lo_que_vieron_los_disparadores())
        return sospechosas

    def _pone_los_disparadores(self) -> None:
        """Pone los ojos sobre las filas, al acabar de arrancar Sirius.

        Las dos tablas del arnés (``TABLAS_DE_LA_PRUEBA``) y, en cada tabla de la base
        que no sea virtual, sombra ni de SQLite, un disparador por insertar, actualizar
        y borrar (``_disparador``). Viven en la base, no en una conexión: ven también lo
        que escriba una conexión que el trazador no sigue, y quitarlos es un cambio de
        esquema que el trazador ve.
        """
        with closing(sqlite3.connect(self.base)) as conexion:
            conexion.execute(
                "CREATE TABLE IF NOT EXISTS _vigilancia_escrituras (tabla TEXT NOT NULL,"
                " columna TEXT NOT NULL, operacion TEXT NOT NULL, tipo TEXT NOT NULL,"
                " largo INTEGER NOT NULL, cabecera TEXT NOT NULL)"
            )
            conexion.execute(
                "CREATE TABLE IF NOT EXISTS _vigilancia_filas (tabla TEXT PRIMARY KEY,"
                " filas INTEGER NOT NULL, texto INTEGER NOT NULL)"
            )
            for tabla, tipo in sorted(_tablas(conexion).items()):
                if tipo != "table" or tabla in TABLAS_DE_LA_PRUEBA or tabla.startswith("sqlite_"):
                    continue
                columnas = [
                    str(fila[1]) for fila in conexion.execute(f'PRAGMA table_info("{_sql(tabla)}")')
                ]
                for operacion in _OPERACIONES:
                    conexion.execute(f'DROP TRIGGER IF EXISTS "_vigila_{_sql(tabla)}_{operacion}"')
                    conexion.execute(_disparador(tabla, columnas, operacion))
            conexion.commit()

    def _lo_que_vieron_los_disparadores(self) -> list[str]:
        """Cada BLOB y cada texto largo escrito en una tabla de la 0.2 desde el arranque, con
        su tamaño y en qué operación; y las tablas con más de mil filas insertadas o más
        texto del que escribe la charla.
        """
        try:
            with closing(sqlite3.connect(self.base)) as conexion:
                vistos = conexion.execute(
                    "SELECT tabla, columna, operacion, tipo, largo, cabecera"
                    " FROM _vigilancia_escrituras ORDER BY rowid"
                ).fetchall()
                cuentas = conexion.execute(
                    "SELECT tabla, filas, texto FROM _vigilancia_filas ORDER BY tabla"
                ).fetchall()
        except sqlite3.Error as error:
            return [f"la vigilancia de la prueba (no se puede leer: {error})"]
        encontrados: list[str] = []
        for tabla, columna, operacion, tipo, largo, cabecera in vistos:
            if tipo == "blob":
                con_cabecera = bytes.fromhex(cabecera).startswith(_CABECERAS_DE_AUDIO)
                que = "BLOB con cabecera de audio" if con_cabecera else "BLOB"
                encontrados.append(f"{tabla}.{columna} ({que} de {largo} bytes {operacion})")
            else:
                encontrados.append(f"{tabla}.{columna} (texto de {largo} caracteres {operacion})")
        texto_total = 0
        for tabla, filas, texto in cuentas:
            texto_total += int(texto)
            if int(filas) > _FILAS_DE_MAS:
                encontrados.append(f"{tabla} (+{filas} filas escritas)")
        if texto_total > _TEXTO_TOTAL:
            encontrados.append(
                f"la base (escribió {texto_total} caracteres de texto desde el arranque)"
            )
        return encontrados

    @staticmethod
    def _columnas_sospechosas(
        conexion: sqlite3.Connection, tabla: str, *, binaria: bool
    ) -> list[str]:
        sospechosas: list[str] = []
        del_modelo = _COLUMNAS_DEL_MODELO.get(tabla)
        tabla_sql = _sql(tabla)
        for fila in conexion.execute(f'PRAGMA table_info("{tabla_sql}")'):
            columna = str(fila[1])
            sitio = f"{tabla}.{columna}"
            if del_modelo is not None and columna not in del_modelo:
                sospechosas.append(f"{sitio} (columna nueva)")
                continue
            c = _sql(columna)
            blobs, blob_mas_grande, texto_mas_largo = conexion.execute(
                f"SELECT count(CASE WHEN typeof(\"{c}\") = 'blob' THEN 1 END),"
                f' max(CASE WHEN typeof("{c}") = \'blob\' THEN length("{c}") ELSE 0 END),'
                f' max(CASE WHEN typeof("{c}") = \'text\' THEN length("{c}") ELSE 0 END)'
                f' FROM "{tabla_sql}"'
            ).fetchone()
            if blobs and not binaria:
                sospechosas.append(
                    f"{sitio} (BLOB, y la charla de estas pruebas no escribe ninguno)"
                )
            elif blobs and int(blob_mas_grande or 0) > _BLOQUE_MAS_GRANDE:
                sospechosas.append(f"{sitio} (bloque mayor de 16 KiB)")
            elif blobs:
                cabeceras = (
                    bytes(valor)
                    for (valor,) in conexion.execute(
                        f'SELECT substr("{c}", 1, 4) FROM "{tabla_sql}"'
                        f" WHERE typeof(\"{c}\") = 'blob'"
                    )
                    if valor is not None
                )
                if any(cabecera.startswith(_CABECERAS_DE_AUDIO) for cabecera in cabeceras):
                    sospechosas.append(f"{sitio} (cabecera de audio)")
            if int(texto_mas_largo or 0) > _TEXTO_LARGO:
                sospechosas.append(f"{sitio} (texto largo)")
        return sospechosas

    def _filas_de_la_base(self) -> dict[str, int | None]:
        """Cuántas filas tiene cada tabla antes de arrancar Sirius; ninguna si la base no existe."""
        base = self._permitidas.base
        if not base.exists():
            return {}
        with closing(sqlite3.connect(base)) as conexion:
            return _filas_por_tabla(conexion)

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
        # Reabrir no migra ni escribe ninguna sentencia (comprobado el 13-10-2026), así
        # que el arranque solo se marca al construir: si una pieza cambiara el esquema al
        # reabrir, se vería.
        super().reabre()
        _enciende_los_registradores_de_sirius()

    def cierra(self) -> None:
        """Cierra Sirius; lo que escriba al cerrar también lo ve el vigilante."""
        try:
            super().cierra()
        finally:
            _deja_de_vigilar(self)

    def _ficheros_que_no_son_suyos(self) -> frozenset[Path]:
        """En las carpetas de Sirius, todo fichero que no sea de los tres permitidos, también
        una base aparte o un fichero sin extensión de audio que escriba una biblioteca en
        C; en la temporal del sistema, donde escribe todo el mundo, solo los de audio.
        """
        encontrados: set[Path] = set()
        for carpeta in self._carpetas_vigiladas:
            if not carpeta.exists():
                continue
            en_la_temporal = carpeta == self._temporal
            for fichero in carpeta.rglob("*"):
                if fichero.is_dir():
                    continue
                if en_la_temporal:
                    if fichero.suffix.lower() in EXTENSIONES_DE_AUDIO:
                        encontrados.add(fichero)
                elif not self._permitidas.permite(fichero):
                    encontrados.add(fichero)
        return frozenset(encontrados)


def percentil(valores: Sequence[float], p: int) -> float:
    """El percentil ``p`` de ``valores``, por el método del rango más cercano."""
    ordenados = sorted(valores)
    return ordenados[max(0, -(-p * len(ordenados) // 100) - 1)]
