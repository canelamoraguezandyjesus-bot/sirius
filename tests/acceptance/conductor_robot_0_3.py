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
hacen de micrófono, de oído, de transcriptor, de voz y de altavoz, nunca de
Sirius: llevan escrito lo que suena en vez de ondas, para que una prueba pueda
decir «esto lo dijo el propietario» y «esto sonó por el altavoz».

Las piezas de ADR-241 que aún no han entrado levantan ``PiezaPendiente``
(``piezas_del_robot``). Cuando una entra, se implementan sus métodos aquí y se
añade su letra a ``PIEZAS_ENTREGADAS``; la tabla de
``docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md`` tiene que decirlo, porque
``test_robot_0_3_trazabilidad.py`` lo compara.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import weakref
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from conductor_robot_0_2 import Conductor, VentanaDePrueba
from piezas_del_robot import PiezaPendiente, Piezas

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

#: Lo que se toma por audio guardado si aparece en el disco después de un turno de voz.
EXTENSIONES_DE_AUDIO: frozenset[str] = frozenset(
    {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm", ".opus", ".pcm", ".raw"}
)


def _pendiente(letra: str) -> PiezaPendiente:
    return _PIEZAS.pendiente(letra)


# --- El vigilante: ve cada fichero que se abre para escribir y cada conexión ---


class Vigilado(Protocol):
    """A quien el vigilante le cuenta lo que ve mientras está dentro de un turno de voz."""

    def anota_escritura(self, ruta: Path) -> None: ...

    def anota_conexion(self, direccion: str) -> None: ...


#: Los conductores que están dentro de un turno de voz: a ellos les llega cada
#: apertura de fichero para escribir y cada conexión de red. Débil, para que un
#: conductor olvidado no se quede vigilando.
_EN_UN_TURNO: weakref.WeakSet[Vigilado] = weakref.WeakSet()
_GANCHO_PUESTO = False

#: Lo único que Sirius abre para escribir durante un turno de voz: su base y lo
#: que SQLite pone a su lado, sus ajustes y su diario. Cualquier otra escritura
#: durante un turno, sea audio o no y esté donde esté, queda apuntada (ronda 2 de
#: Codex sobre la PR #686: un temporal junto a la base no se podía descartar).
_ESCRITURAS_PERMITIDAS = re.compile(
    r"^(sirius\.db(-journal|-wal|-shm)?|settings\.json|application\.log(\.\d+)?)$"
)


def _abre_para_escribir(modo: object, flags: object) -> bool:
    if isinstance(modo, str):
        return any(letra in modo for letra in "wax+")
    if isinstance(flags, int):
        return bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT))
    return False


def es_escritura_sospechosa(ruta: Path) -> bool:
    """Si abrir ``ruta`` para escribir durante un turno de voz es algo que Sirius no hace."""
    return _ESCRITURAS_PERMITIDAS.match(ruta.name) is None


def _vigilar() -> None:
    """Pone, una vez por proceso, el gancho que ve cada escritura y cada conexión.

    Un gancho de auditoría de Python no se puede quitar, así que se pone una vez y
    solo trabaja mientras algún conductor está dentro de un turno de voz. Ve todo
    lo que abre Python para escribir, también ``tempfile`` y lo que se borra antes
    de acabar el turno, y cada ``socket.connect`` (rondas 1 y 2 de Codex sobre la
    PR #686). Lo que escriba Qt por su cuenta no pasa por aquí, y por eso el disco
    se mira además al final (``ficheros_de_audio_nuevos``).
    """
    global _GANCHO_PUESTO
    if _GANCHO_PUESTO:
        return

    def gancho(evento: str, args: tuple[Any, ...]) -> None:
        if not _EN_UN_TURNO or evento not in ("open", "socket.connect"):
            return
        try:
            if evento == "open":
                ruta, modo, flags = args
                if not _abre_para_escribir(modo, flags) or isinstance(ruta, int):
                    return
                visto: Path | str = Path(os.fsdecode(ruta))
            else:
                _toma, direccion = args
                visto = repr(direccion)
        except TypeError, ValueError, UnicodeError:
            # Un gancho que lanza aborta la operación ajena: aquí se calla.
            return
        for conductor in list(_EN_UN_TURNO):
            if isinstance(visto, Path):
                conductor.anota_escritura(visto)
            else:
                conductor.anota_conexion(visto)

    sys.addaudithook(gancho)
    _GANCHO_PUESTO = True


# --- Dobles: hacen de micro, de oído, de voz y de altavoz, nunca de Sirius ----


@dataclass(frozen=True, slots=True)
class Sonido:
    """Un trozo de audio de mentira: lleva escrito lo que suena, en vez de ondas.

    ``texto`` vacío es silencio. ``de_quien`` dice quién lo produjo, para que la
    prueba pueda seguirlo; Sirius no lo ve, igual que no ve quién habla de verdad.
    """

    texto: str
    de_quien: str = "propietario"
    segundos: float = 1.0

    @property
    def es_silencio(self) -> bool:
        return not self.texto


@dataclass
class MicroDeMentira:
    """El micrófono: una cola de sonidos que la tubería va leyendo, y si está abierto.

    Lo abre y lo cierra Sirius, nunca la prueba: así una prueba puede mirar que
    la ventana lo abre al arrancar y que el botón de silencio lo cierra.
    """

    abierto: bool = False
    pendientes: list[Sonido] = field(default_factory=list)
    leidos: list[Sonido] = field(default_factory=list)

    def suena(self, sonido: Sonido) -> None:
        self.pendientes.append(sonido)


@dataclass
class OidoDeMentira:
    """Hace de Silero y de Smart Turn.

    Hay voz si el sonido lleva texto. El turno acaba cuando han pasado
    ``silencios_para_acabar`` silencios seguidos después de la voz: con 1 es
    el detector impaciente; con más, el detector dice «todavía no ha terminado»
    en los primeros silencios, y Sirius tiene que esperarle.
    """

    silencios_para_acabar: int = 1
    vistos: list[Sonido] = field(default_factory=list)

    def pide_silencios(self, cuantos: int) -> None:
        self.silencios_para_acabar = cuantos


@dataclass
class TranscriptorDeMentira:
    """Hace de faster-whisper: devuelve el texto escrito en el sonido y apunta cada uno."""

    transcritos: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Frase:
    """Una frase que se le pidió a la voz, y el momento (``time.perf_counter``) en que llegó."""

    texto: str
    momento: float


@dataclass
class VozDeMentira:
    """Hace de Piper: apunta cada frase que le piden, con su momento, y la devuelve como sonido."""

    frases: list[Frase] = field(default_factory=list)


@dataclass
class AltavozDeMentira:
    """Lo que suena por el altavoz: cada sonido con el momento en que empezó.

    Con ``con_eco`` devuelve al micro lo que suena, como un altavoz que el
    micrófono capta. ``sigue_sonando`` mantiene el último sonido en el aire
    hasta que Sirius lo pare o lo deje acabar: sirve para cortarle.
    """

    sonados: list[tuple[Sonido, float]] = field(default_factory=list)
    con_eco: bool = False
    sigue_sonando: bool = False
    parado_en: float | None = None


@dataclass
class RelojDeMentira:
    """El reloj con el que Sirius mide cuánto hace que acabó la charla."""

    ahora: float = 1_000_000.0

    def avanza(self, segundos: float) -> None:
        self.ahora += segundos


# --- Lo que el conductor devuelve a las pruebas ------------------------------


@dataclass(frozen=True, slots=True)
class TurnoDeVoz:
    """Lo que pasó después de que algo sonara por el micro.

    ``oido`` es lo que Sirius dio por dicho, o ``None`` si el turno no se cerró
    o el micro estaba cerrado. ``para_el`` dice si Sirius lo tomó como dicho a
    él. ``contestado`` es lo que escribió, y ``hablado`` lo que fue diciendo
    por el altavoz, frase a frase. ``primer_sonido_tras_ms`` va del último
    sonido con voz del propietario al primer sonido suyo por el altavoz.
    ``se_callo_tras_ms`` va del principio de la voz nueva del propietario a que
    el altavoz paró, si estaba sonando. ``aviso`` es lo que Sirius enseña si no
    puede oír o hablar, por ejemplo porque falta un modelo.
    """

    oido: str | None
    para_el: bool
    contestado: str | None
    hablado: tuple[str, ...]
    primer_sonido_tras_ms: float | None = None
    se_callo_tras_ms: float | None = None
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
        """«Escuchando», «En silencio» o «Hablando», tal como se ve."""
        raise _pendiente("D")

    def pulsa_silencio(self) -> None:
        """El botón que calla el micrófono, y que lo vuelve a abrir."""
        raise _pendiente("D")

    def mensajes(self) -> tuple[tuple[str, str], ...]:
        """La charla tal como se ve: (quién, texto), en orden. Quién es «propietario» o «Sirius»."""
        raise _pendiente("D")


# --- El conductor ------------------------------------------------------------


class ConductorDeVoz(Conductor):
    """Sirius de verdad, con la charla de la 0.2 y el oído y la voz de la 0.3 encima.

    Monta lo mismo que el conductor de la 0.2 y, además, la tubería de voz con
    los dobles de arriba en lugar del micro, del oído, del transcriptor, de la
    voz y del altavoz de verdad. ``oye`` hace sonar algo por el micro y espera
    a que Sirius termine con ello, como ``di`` escribe y espera.
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
        self.altavoz = AltavozDeMentira()
        self.reloj = RelojDeMentira()
        self._temporal = Path(tempfile.gettempdir())
        self._ficheros_de_antes = self._ficheros_de_audio()
        self._escrituras: list[Path] = []
        self._conexiones: list[str] = []
        _vigilar()
        super().__init__(carpeta, respuestas=respuestas, ajustes=ajustes)

    # --- Pieza B: oír en local ---

    def oye(self, texto: str, *, y_calla: int = 1) -> TurnoDeVoz:
        """Suena ``texto`` por el micro y después ``y_calla`` silencios.

        Devuelve cuando Sirius ha terminado con ello: ha contestado, ha decidido
        que no era para él, o se ha quedado esperando a que el detector dé el
        turno por acabado (entonces ``oido`` es ``None``). Mientras dura, cada
        fichero que algo abra para escribir y cada conexión quedan apuntados
        (``escrituras_en_disco`` y ``conexiones_de_red``).
        """
        with self._vigilando_escrituras():
            return self._oye(texto, y_calla=y_calla)

    def _oye(self, texto: str, *, y_calla: int) -> TurnoDeVoz:
        del texto, y_calla
        raise _pendiente("B")

    def calla(self, silencios: int) -> TurnoDeVoz:
        """Suenan ``silencios`` silencios más por el micro; qué pasa con el turno que esperaba."""
        with self._vigilando_escrituras():
            return self._calla(silencios)

    def _calla(self, silencios: int) -> TurnoDeVoz:
        del silencios
        raise _pendiente("B")

    def hubo_peticion_al_modelo_en_el_ultimo_turno_de_voz(self) -> bool:
        raise _pendiente("B")

    def charla_guardada(self) -> tuple[tuple[str, str], ...]:
        """La charla tal como queda en la base: (quién, texto), en orden."""
        raise _pendiente("B")

    def conexiones_de_red(self) -> list[str]:
        """Las direcciones a las que algo intentó conectarse durante un turno de voz."""
        return list(self._conexiones)

    def anota_conexion(self, direccion: str) -> None:
        """Lo llama el vigilante por cada ``socket.connect`` durante un turno."""
        self._conexiones.append(direccion)

    def destinos_posibles_de_la_voz(self) -> frozenset[str]:
        """Adónde pueden ir el oído y la voz del robot según sus ajustes: todo lo elegible."""
        raise _pendiente("B")

    def quita_los_modelos_de_voz(self) -> None:
        """Deja a Sirius sin los modelos de oír y hablar, como un ordenador sin instalarlos."""
        raise _pendiente("B")

    def descargas(self) -> int:
        """Cuántas veces algo intentó bajar un modelo por su cuenta."""
        raise _pendiente("B")

    def orden_para_instalar_la_voz(self) -> str:
        """La orden que el propietario tiene que ejecutar para instalar los modelos de la voz."""
        raise _pendiente("B")

    # --- Pieza C: hablar en local ---

    def el_modelo_contesta_despacio(self, frases: Sequence[str], *, pausa: float = 0.05) -> None:
        """La próxima respuesta del modelo llega a trozos, con ``pausa`` segundos entre ellos."""
        del frases, pausa
        raise _pendiente("C")

    def momento_en_que_el_modelo_acabo(self) -> float:
        """Cuándo (``time.perf_counter``) el modelo dio por terminada su última respuesta."""
        raise _pendiente("C")

    def herramientas(self) -> Mapping[str, str]:
        """Con qué oye y habla Sirius, por nombre: «voz», «fin de turno», «texto» y «habla»."""
        raise _pendiente("C")

    def voz_con_la_que_habla(self) -> str:
        """El nombre de la voz con la que habla, tal como la conoce quien la sintetiza."""
        raise _pendiente("C")

    # --- Pieza D: escucha siempre y a quién le hablan ---

    def segundos_de_charla(self) -> float:
        """Cuánto dura la charla después de que Sirius calle: hasta entonces sobra el nombre."""
        raise _pendiente("D")

    def ficheros_de_audio_nuevos(self) -> list[Path]:
        """Audio aparecido desde que arrancó el conductor, en sus carpetas o en la temporal."""
        return sorted(self._ficheros_de_audio() - self._ficheros_de_antes)

    def escrituras_en_disco(self) -> list[Path]:
        """Lo que algo abrió para escribir durante un turno de voz, aunque lo borrara después.

        Todo lo que no sea la base de Sirius, sus ajustes o su diario, esté donde
        esté y se llame como se llame (``es_escritura_sospechosa``).
        """
        return list(self._escrituras)

    def anota_escritura(self, ruta: Path) -> None:
        """Lo llama el vigilante por cada fichero abierto para escribir durante un turno."""
        if es_escritura_sospechosa(ruta):
            self._escrituras.append(ruta)

    def audio_en_la_base(self) -> list[str]:
        """Las ``tabla.columna`` de la base que guardan audio: ninguna, si no guarda."""
        raise _pendiente("D")

    def ventana(self, qtbot: Any) -> VentanaDeVoz:
        return VentanaDeVoz(self.abre_la_ventana(qtbot), qtbot)

    # --- Pieza E: cortarle ---

    def oye_mientras_habla(self, texto: str) -> TurnoDeVoz:
        """El propietario habla mientras el altavoz sigue sonando con la respuesta anterior."""
        with self._vigilando_escrituras():
            return self._oye_mientras_habla(texto)

    def _oye_mientras_habla(self, texto: str) -> TurnoDeVoz:
        del texto
        raise _pendiente("E")

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

    def escucha_en_la_hoja(self, etiqueta: str, frase: str) -> Sonido:
        """Pulsa en la hoja el botón de escuchar ``frase`` con la voz ``etiqueta``; lo que sonó."""
        del etiqueta, frase
        raise _pendiente("F")

    def hay_forma_de_clonar_una_voz(self) -> bool:
        """Si algún camino de Sirius acepta un audio de alguien para imitar su voz."""
        raise _pendiente("F")

    # --- Lo que es solo de las pruebas ---

    @contextmanager
    def _vigilando_escrituras(self) -> Iterator[None]:
        """Mientras dura un turno de voz, cada escritura y cada conexión pasan por aquí."""
        _EN_UN_TURNO.add(self)
        try:
            yield
        finally:
            _EN_UN_TURNO.discard(self)

    def _ficheros_de_audio(self) -> frozenset[Path]:
        carpetas = (self.carpeta, self._temporal)
        return frozenset(
            fichero
            for carpeta in carpetas
            if carpeta.exists()
            for fichero in carpeta.rglob("*")
            if fichero.suffix.lower() in EXTENSIONES_DE_AUDIO
        )


def percentil(valores: Sequence[float], p: int) -> float:
    """El percentil ``p`` de ``valores``, por el método del rango más cercano."""
    ordenados = sorted(valores)
    return ordenados[max(0, -(-p * len(ordenados) // 100) - 1)]
