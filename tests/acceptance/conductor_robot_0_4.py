"""Conductor de las pruebas de aceptación de la versión 0.4 del robot, los ojos (ADR-259).

Las pruebas de ``test_robot_0_4_*.py`` hablan como el plan
(``docs/evolution/PLAN_DEL_ROBOT.md``, §6): alguien se pone delante de la cámara,
Sirius le mira, le reconoce si dio permiso, parpadea, aparta la vista al pensar. Este
módulo es lo único que sabe cómo se hace cada cosa en el código, como los conductores
de la 0.2 y la 0.3: así las pruebas se escriben antes que el código, y cuando entra una
pieza solo cambia su parte del conductor.

**La regla del conductor: no implementa nada de Sirius.** Es el conductor de la 0.3 con
la cámara y la cara encima: la charla, la memoria, el oído, la voz y la ventana son las
de siempre. Los dobles de abajo hacen de cámara, de detector de caras, de reconocedores
de cara y de voz y de estimador de edad, nunca de Sirius. Llevan escrito lo que hay
delante de la cámara en vez de píxeles, para que una prueba pueda decir «Marta está a
la derecha y habla».

**Los dobles hacen algo, y apuntan lo que hacen**, en el acto de hacerlo (lección de
ADR-241). La cámara da un fotograma: unos bytes con una marca, ``MARCA_DE_LA_IMAGEN``, y
dentro, por cada persona, su trozo. El detector encuentra en esos bytes las caras y da
cada una con su recorte, su sitio, si mueve la boca y si mira a la cámara. Los
reconocedores dan, de un recorte o de un audio, una huella: unos números de longitud uno,
como los de verdad, siempre los mismos para la misma persona. El estimador da la edad con
su seguridad. Nada de lo que ven sale de la prueba por otro camino: lo leen de los bytes
que les llegan, como uno de verdad. Lo que la tubería recibe del micro sigue sin decir
quién habló, como en la 0.3; lo que sí lleva, como una voz de verdad, es su timbre,
dentro de las muestras (``AudioConVoz``), y solo el reconocedor de voces lo lee.

**La cara de Sirius no es un doble.** Se lee de los píxeles de la pantalla, como la vería
el propietario (``lector_de_la_cara``), no de lo que la cara dice que dibujó; las veces
que se pinta las cuenta Qt, no ella (ronda 1 de Codex sobre la PR #702); y el conductor
nunca le pide que se pinte: deja correr Qt hasta que la pinta sola, con su reloj, y lee lo
que quedó en la pantalla. Una cara que solo se pintara al pedírselo se leería congelada
(ronda 2). Las cifras de las pruebas salen de esos dibujos y de los registros de los
dobles, nunca de un campo que rellene el conductor.

**Lo que no se guarda se busca con un alcance escrito.** Que no quede ninguna imagen ni
ninguna huella en claro es una negación sin borde: se buscan donde las dejaría un error,
en las formas en que Python, numpy y SQLite guardan unos bytes o unos números, y lo
demás es engaño, que va a la revisión del código de cada pieza (lección de ADR-241). Cada
cosa se busca con una sola función, la misma en cada sitio: buscarla a mano sitio a sitio
dejó la base sin unas formas en la ronda 1 de Codex sobre la PR #702, y el diario sin
otras en la ronda 2.

Las piezas de ADR-259 que aún no han entrado levantan ``PiezaPendiente``
(``piezas_del_robot``). Cuando una entra, se implementan sus métodos aquí y se añade su
letra a ``PIEZAS_ENTREGADAS``; la tabla de ``docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md``
tiene que decirlo, porque ``test_robot_0_4_trazabilidad.py`` lo compara. Que los dobles
hacen lo que dicen lo comprueba ``test_dobles_del_conductor_0_4.py``.
"""

from __future__ import annotations

import base64
import inspect
import math
import random
import re
import sqlite3
import struct
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from conductor_robot_0_2 import Peticion
from conductor_robot_0_3 import (
    Audio,
    ConductorDeVoz,
    RelojDeMentira,
    Sonido,
    TurnoDeVoz,
    VentanaDeVoz,
)
from lector_de_la_cara import PARTES, Lectura, lee
from lector_de_la_cara import Dibujo as Dibujo
from piezas_del_robot import PiezaPendiente, Piezas

from sirius.adapters.recognition.engines import EcapaPrints, InsightFacePrints
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.adapters.vision.local_sight import TOOLS
from sirius.application.presence import HEADING, IN_FRONT_LINE, NOBODY_LINE, SOMEONE, SPEAKER_LINE
from sirius.application.recognition import UNKNOWN, EnrollmentStep
from sirius.domain.gestures import GESTURES
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.local_sight import CameraUnavailable, SeenFace, SightEngines
from sirius.ports.recognition import Print, RecognitionEngines
from sirius.ports.secrets import SecretStore
from sirius.presentation.face_widget import FRAME_MS
from sirius.presentation.main_window import SIGHT_REFRESH_MS

#: Las letras de la tabla de piezas de ADR-259 que ya han entrado en ``main``. La A es la
#: nota de arranque y estas pruebas; la B, su cara (ADR-260); la C, sus gestos (ADR-261);
#: la D, sus ojos (ADR-262); y la E, reconocer a quien dé permiso (ADR-263).
PIEZAS_ENTREGADAS: frozenset[str] = frozenset({"A", "B", "C", "D", "E"})

#: Qué trae cada pieza, con las palabras de la tabla de ADR-259.
PIEZAS: Mapping[str, str] = {
    "A": "la nota de arranque y las pruebas de aceptación",
    "B": "su cara en la ventana: dibujada, viva en reposo, sin congelarse y con la boca al "
    "volumen de su voz",
    "C": "gestos de una lista cerrada",
    "D": "la cámara y las caras en local: mira a quien habla, aparta la vista al pensar y, "
    "si le miran, le hablan a él",
    "E": "reconocer por la cara y por la voz a quien dé permiso, con las huellas cifradas",
    "F": "la regla de los críos y los ancianos frágiles",
    "G": "recordar lo que ve como texto",
}

_PIEZAS = Piezas("ADR-259", PIEZAS, PIEZAS_ENTREGADAS)

#: Marca una prueba como dependiente de una pieza; ver ``piezas_del_robot``.
pieza = _PIEZAS.pieza


def _pendiente(letra: str) -> PiezaPendiente:
    return _PIEZAS.pendiente(letra)


#: Lo que lleva cada fotograma de la cámara de mentira, varias veces: una imagen guardada
#: por error, entera o a trozos, la lleva dentro.
MARCA_DE_LA_IMAGEN = b"SIRIUS-IMAGEN-DE-PRUEBA"

#: Lo que se toma por una imagen o un vídeo guardado si aparece en el disco.
EXTENSIONES_DE_IMAGEN: frozenset[str] = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".gif",
        ".webp",
        ".tif",
        ".tiff",
        ".heic",
        ".avif",
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".npy",
    }
)

#: Cómo empieza un fichero de imagen con cabecera: JPEG, PNG, GIF, BMP y TIFF.
CABECERAS_DE_IMAGEN: tuple[bytes, ...] = (
    b"\xff\xd8\xff",
    b"\x89PNG",
    b"GIF8",
    b"BM",
    b"II*\x00",
    b"MM\x00*",
)

#: Lo que lleva dentro una imagen, en binario, que no se da por casualidad en unos bytes
#: cualesquiera: la cabecera de PNG, las marcas de JPEG, la de GIF y la de WEBP. Las de dos
#: o tres bytes, como la de BMP o el principio de la de JPEG, sí se dan, y se dejan fuera.
_DENTRO_DE_UNA_IMAGEN: tuple[bytes, ...] = (
    b"\x89PNG\r\n\x1a\n",
    b"JFIF\x00",
    b"Exif\x00\x00",
    b"GIF87a",
    b"GIF89a",
    b"WEBPVP8",
)
#: Cómo empieza en base64 una imagen entera: JPEG, PNG, GIF y las de RIFF, como WEBP.
_UNA_IMAGEN_EN_BASE64: tuple[bytes, ...] = (b"/9j/", b"iVBORw0KGgo", b"R0lGOD", b"UklGR")

#: Lo que delata una imagen codificada, en la base o en el diario: lo que lleva dentro, en
#: binario, en hexadecimal y como texto, que es como sale en el ``repr`` de unos bytes; su
#: principio en base64; y la cabecera de una imagen en una dirección (ronda 2 de Codex sobre
#: la PR #702).
IMAGEN_DENTRO: tuple[bytes, ...] = tuple(
    dict.fromkeys(
        (
            *_DENTRO_DE_UNA_IMAGEN,
            *(dentro.hex().encode() for dentro in _DENTRO_DE_UNA_IMAGEN),
            *(dentro.hex().upper().encode() for dentro in _DENTRO_DE_UNA_IMAGEN),
            *(repr(dentro)[2:-1].encode() for dentro in _DENTRO_DE_UNA_IMAGEN),
            *_UNA_IMAGEN_EN_BASE64,
            b"data:image/",
        )
    )
)


# --- Lo que hay delante de la cámara -------------------------------------------------


@dataclass(frozen=True, slots=True)
class Persona:
    """Alguien delante de la cámara, tal como lo ve la prueba.

    ``x`` va de 0, el borde izquierdo de lo que ve la cámara, a 1, el derecho. ``habla``
    dice si mueve la boca en ese momento, y ``mira_a_sirius``, si mira a la cámara.
    ``edad_segura`` es la seguridad con que se le ve la edad: con poca luz o de perfil, no.
    """

    quien: str
    x: float = 0.5
    habla: bool = False
    mira_a_sirius: bool = False
    edad: int = 35
    edad_segura: bool = True

    def recorte(self) -> bytes:
        """Su cara, como trozo de un fotograma: la marca y, detrás, lo que la distingue."""
        rasgos = (
            f"|{self.quien}|{self.edad}|{int(self.edad_segura)}|{self.x:.3f}"
            f"|{int(self.habla)}|{int(self.mira_a_sirius)}|"
        )
        return MARCA_DE_LA_IMAGEN + rasgos.encode() + _relleno(self.quien, 2_000)


def _relleno(semilla: str, largo: int) -> bytes:
    """Bytes que parecen píxeles, siempre los mismos para la misma semilla."""
    return random.Random(semilla).randbytes(largo)


@dataclass(frozen=True, slots=True)
class Fotograma:
    """Lo que da la cámara de mentira de una vez: unos bytes, como una imagen de verdad.

    Lleva la marca de la imagen aunque no haya nadie delante, y el recorte de cada
    persona que hay. El detector los busca en ``pixeles``: no hay otro sitio donde mirar.
    """

    numero: int
    momento: float
    pixeles: bytes


_RECORTE = re.compile(
    re.escape(MARCA_DE_LA_IMAGEN) + rb"\|([^|]+)\|(\d+)\|([01])\|([0-9.]+)\|([01])\|([01])\|",
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class CaraVista:
    """Una cara que encontró el detector en un fotograma: su sitio, su recorte, si mueve la
    boca y si mira a la cámara, como lo dan las marcas de la cara de MediaPipe."""

    x: float
    recorte: bytes
    habla: bool
    mira: bool


class CamaraNoEncontrada(RuntimeError):
    """No hay cámara: como una de verdad desenchufada, o cogida por otro programa."""


class CamaraDeMentira:
    """La cámara del ordenador. Da fotogramas con quien la prueba pone delante.

    La abre y la cierra Sirius, nunca la prueba; la prueba la desenchufa
    (``desconecta``), y desde entonces ni se abre ni da nada. Apunta cada fotograma que
    da, con su número y su momento, en el acto de darlo.
    """

    def __init__(self, ahora: Callable[[], float]) -> None:
        self._ahora = ahora
        self._delante: tuple[Persona, ...] = ()
        self._conectada = True
        self._abierta = False
        self._dados: list[Fotograma] = []

    @property
    def abierta(self) -> bool:
        return self._abierta

    @property
    def dados(self) -> tuple[Fotograma, ...]:
        return tuple(self._dados)

    @property
    def delante(self) -> tuple[Persona, ...]:
        return self._delante

    def pon_delante(self, personas: Sequence[Persona]) -> None:
        self._delante = tuple(personas)

    def desconecta(self) -> None:
        self._conectada = False
        self._abierta = False

    def abre(self) -> None:
        if not self._conectada:
            msg = "no hay cámara"
            raise CamaraNoEncontrada(msg)
        self._abierta = True

    def cierra(self) -> None:
        self._abierta = False

    def lee(self) -> Fotograma | None:
        """El fotograma de ahora; ``None`` si está cerrada. Desenchufada, falla."""
        if not self._conectada:
            msg = "la cámara se ha desenchufado"
            raise CamaraNoEncontrada(msg)
        if not self._abierta:
            return None
        fondo = MARCA_DE_LA_IMAGEN + _relleno(f"fondo {len(self._dados)}", 4_000)
        pixeles = fondo + b"".join(persona.recorte() for persona in self._delante)
        fotograma = Fotograma(len(self._dados) + 1, self._ahora(), pixeles)
        self._dados.append(fotograma)
        return fotograma


class DetectorDeMentira:
    """El detector de caras, en lugar de MediaPipe: encuentra las caras en los bytes.

    Apunta, por cada fotograma que le pasan, su número y cuántas caras encontró.
    """

    nombre = "mediapipe"

    def __init__(self) -> None:
        self._detecciones: list[tuple[int, int]] = []

    @property
    def detecciones(self) -> tuple[tuple[int, int], ...]:
        return tuple(self._detecciones)

    def detecta(self, fotograma: Fotograma) -> tuple[CaraVista, ...]:
        caras: list[CaraVista] = []
        coincidencias = list(_RECORTE.finditer(fotograma.pixeles))
        for posicion, encontrada in enumerate(coincidencias):
            final = (
                coincidencias[posicion + 1].start()
                if posicion + 1 < len(coincidencias)
                else len(fotograma.pixeles)
            )
            caras.append(
                CaraVista(
                    x=float(encontrada.group(4)),
                    recorte=fotograma.pixeles[encontrada.start() : final],
                    habla=encontrada.group(5) == b"1",
                    mira=encontrada.group(6) == b"1",
                )
            )
        self._detecciones.append((fotograma.numero, len(caras)))
        return tuple(caras)


# --- Las huellas ------------------------------------------------------------------------

#: Cuántos números tiene cada huella, como las de verdad: 512 las de cara de InsightFace y
#: 192 las de voz de ECAPA.
NUMEROS_DE_LA_HUELLA_DE_CARA = 512
NUMEROS_DE_LA_HUELLA_DE_VOZ = 192


def _huella(quien: str, de_que: str, numeros: int, llenos: int) -> tuple[float, ...]:
    """La huella de mentira de ``quien``: ``numeros`` números, ``llenos`` de ellos de
    ±1/√llenos y los demás cero, en sitios y con signos que solo salen de él.

    ``llenos`` es un cuadrado, así que cada número es exacto y la longitud es uno
    exacta: normalizarla, en float32 o en float64, no la cambia, y una huella guardada en
    claro se encuentra tal cual. Dos personas distintas comparten la mitad de los sitios
    con signos al azar: se parecen poco, como dos caras distintas.
    """
    lado = math.isqrt(llenos)
    assert lado * lado == llenos, "llenos tiene que ser un cuadrado"
    azar = random.Random(f"{de_que}:{quien}")
    sitios = frozenset(azar.sample(range(numeros), llenos))
    return tuple(
        (1 / lado if azar.random() < 0.5 else -1 / lado) if sitio in sitios else 0.0
        for sitio in range(numeros)
    )


def huella_de_cara(quien: str) -> tuple[float, ...]:
    """La huella que da el reconocedor de caras de mentira para ``quien``."""
    return _huella(quien, "cara", NUMEROS_DE_LA_HUELLA_DE_CARA, 256)


def huella_de_voz(quien: str) -> tuple[float, ...]:
    """La huella que da el reconocedor de voces de mentira para ``quien``."""
    return _huella(quien, "voz", NUMEROS_DE_LA_HUELLA_DE_VOZ, 64)


def parecido(una: Sequence[float], otra: Sequence[float]) -> float:
    """El coseno entre dos huellas: 1 para la misma persona y cerca de 0 para dos distintas."""
    return sum(a * b for a, b in zip(una, otra, strict=True))


class ReconocedorDeCarasDeMentira:
    """En lugar de InsightFace: de un recorte, la huella de su cara.

    La lee de los bytes del recorte, como uno de verdad la saca de los píxeles. Apunta
    cada huella que da, en el acto.
    """

    nombre = "insightface"

    def __init__(self) -> None:
        self._dadas: list[tuple[float, ...]] = []

    @property
    def dadas(self) -> tuple[tuple[float, ...], ...]:
        return tuple(self._dadas)

    def huella(self, recorte: bytes) -> tuple[float, ...]:
        encontrada = _RECORTE.match(recorte)
        if encontrada is None:
            msg = "eso no es una cara"
            raise ValueError(msg)
        huella = huella_de_cara(encontrada.group(1).decode())
        self._dadas.append(huella)
        return huella


class EstimadorDeEdadDeMentira:
    """En lugar de InsightFace para la edad: de un recorte, la edad y si es segura.

    Apunta cada estimación que da, en el acto.
    """

    def __init__(self) -> None:
        self._estimadas: list[tuple[int, bool]] = []

    @property
    def estimadas(self) -> tuple[tuple[int, bool], ...]:
        return tuple(self._estimadas)

    def estima(self, recorte: bytes) -> tuple[int, bool]:
        encontrada = _RECORTE.match(recorte)
        if encontrada is None:
            msg = "eso no es una cara"
            raise ValueError(msg)
        estimada = (int(encontrada.group(2)), encontrada.group(3) == b"1")
        self._estimadas.append(estimada)
        return estimada


#: Dónde lleva una muestra de voz su timbre: tras esta marca, el nombre de quien habla.
_TIMBRE = b"SIRIUS-TIMBRE|"
_TIMBRES = re.compile(re.escape(_TIMBRE) + rb"([^|]+)\|")


@dataclass(frozen=True, slots=True)
class AudioConVoz(Audio):
    """Lo que la tubería recibe del micro cuando alguien habla: lo que suena y su timbre.

    Como en la 0.3, no dice quién lo dijo; pero una voz de verdad tiene timbre, y el de
    mentira va dentro de las muestras, al principio, sin cambiar cuántas son. Solo el
    reconocedor de voces lo lee.
    """

    timbre: str = ""

    def __post_init__(self) -> None:
        Audio.__post_init__(self)
        if self.timbre:
            con_timbre = _TIMBRE + self.timbre.encode() + b"|" + self.muestras
            object.__setattr__(self, "muestras", con_timbre[: len(self.muestras)])


@dataclass(frozen=True, slots=True)
class SonidoDe(Sonido):
    """Lo que dice alguien con su voz: su audio lleva el timbre de ``de_quien``."""

    @property
    def audio(self) -> Audio:
        return AudioConVoz(self.texto, timbre=self.de_quien)


class ReconocedorDeVocesDeMentira:
    """En lugar de ECAPA: de unas muestras, la huella de la voz que suena en ellas.

    Lee el timbre donde esté, como uno de verdad oye la voz aunque haya silencio antes. Sin
    timbre no da huella. Con dos voces distintas, la de ninguna de las dos: una mezcla no
    se parece a nadie. Apunta cada huella que da, en el acto.
    """

    nombre = "speechbrain-ecapa"

    def __init__(self) -> None:
        self._dadas: list[tuple[float, ...]] = []

    @property
    def dadas(self) -> tuple[tuple[float, ...], ...]:
        return tuple(self._dadas)

    def huella(self, muestras: bytes) -> tuple[float, ...] | None:
        voces = sorted({encontrada.decode() for encontrada in _TIMBRES.findall(muestras)})
        if not voces:
            return None
        huella = huella_de_voz(" y ".join(voces))
        self._dadas.append(huella)
        return huella


def formas_de_la_huella(huella: Sequence[float]) -> tuple[bytes, ...]:
    """Trozos de ``huella`` tal como quedarían guardados en claro.

    De 16 en 16 números, en float32 y en float64 en binario, que es como los guardan
    ``struct``, numpy y sqlite-vec, y esos bytes pasados a texto sin cifrarlos, en
    hexadecimal o en base64 (``codificados``); y como texto, que es como los escriben
    ``json`` y ``repr``. A trozos, porque SQLite parte lo largo entre páginas. Solo los
    trozos con al menos cuatro números que no son cero: uno de ceros casaría con cualquier
    cosa.
    """
    formas: list[bytes] = []
    for inicio in range(0, len(huella) - 15, 16):
        trozo = huella[inicio : inicio + 16]
        if sum(1 for numero in trozo if numero) < 4:
            continue
        for binario in (
            struct.pack(f"<{len(trozo)}f", *trozo),
            struct.pack(f"<{len(trozo)}d", *trozo),
        ):
            formas.append(binario)
            formas.extend(codificados(binario))
        formas.append(", ".join(repr(numero) for numero in trozo).encode())
        formas.append(",".join(repr(numero) for numero in trozo).encode())
    return tuple(formas)


def codificados(datos: bytes) -> tuple[bytes, ...]:
    """``datos`` pasados a texto sin cifrarlos, que se deshace sin llave: en hexadecimal, en
    minúsculas y en mayúsculas, y en base64, la normal y la de las direcciones, desde
    cualquiera de los tres sitios en que pueden caer en un grupo de tres bytes (ronda 1 de
    Codex sobre la PR #702)."""
    formas = [datos.hex().encode(), datos.hex().upper().encode()]
    for desfase in range(3):
        trozo = datos[(3 - desfase) % 3 :]
        entero = trozo[: len(trozo) // 3 * 3]
        formas.extend((base64.b64encode(entero), base64.urlsafe_b64encode(entero)))
    return tuple(dict.fromkeys(formas))


# --- La cara de Sirius, leída de la ventana ------------------------------------------


@dataclass(frozen=True, slots=True)
class TurnoConMirada:
    """Un turno de voz dicho delante de la cámara, con lo que dibujó la cara en él.

    ``oyendo`` es el dibujo mientras el micro leía lo último que se dijo; ``pensando``,
    los de mientras el modelo pensaba, antes de su primera palabra; y ``contestando``,
    el de cuando empezó a sonar la respuesta. Los momentos los marcan los dobles, el
    micro, el modelo y el altavoz, en el acto.
    """

    turno: TurnoDeVoz
    oyendo: Dibujo | None
    pensando: tuple[Dibujo, ...]
    contestando: Dibujo | None


#: Lo que delata una cara pintada con imágenes o vídeos en vez de dibujada, en el código
#: de quien la dibuja: las clases de Qt que los cargan y las extensiones de sus ficheros.
_LO_QUE_PINTA_IMAGENES: tuple[str, ...] = (
    "QPixmap",
    "QImage",
    "QMovie",
    "QIcon",
    "QSvg",
    "QVideo",
    "QMediaPlayer",
    ".png",
    ".jpg",
    ".gif",
    ".svg",
    ".mp4",
)


#: Lo alta que se pone la cara en las pruebas, en píxeles: más que en la ventana de siempre,
#: para leerla con precisión. Se dibuja igual, a otra escala.
ALTO_DE_LA_CARA = 480
#: Lo más que se deja pasar del reloj de las pruebas buscando sus partes: el párpado solo
#: se ve al parpadear, y parpadea cada 2 a 6 s.
BUSCANDO_LAS_PARTES = 8.0
#: De cuánto en cuánto se mira la cara al dejar pasar el reloj de las pruebas, en segundos:
#: lo que tarda en pintarse sola un fotograma, como lo ve el propietario. Un parpadeo deja
#: los ojos casi cerrados 0,09 s: se ve siempre.
PASO_DE_LA_CARA = FRAME_MS / 1000
#: Lo que se espera a que Qt pinte la cara sola, en milisegundos: se pinta cada 33 ms, y si
#: en un segundo no lo ha hecho, está congelada.
ESPERA_A_QUE_SE_PINTE_MS = 1000
#: Lo más que se espera a que abra los ojos para ver adónde mira, en segundos.
ESPERA_A_QUE_ABRA = 0.3
#: Lo que puede dejar de verse un gesto, en segundos, y seguir siendo el mismo.
HUECO_DE_UN_GESTO = 0.3


class VentanaDeOjos(VentanaDeVoz):
    """La ventana de Sirius con lo que la 0.4 le añade: su cara y lo que dice de la cámara.

    La cara se lee de los píxeles de la pantalla, donde la pinta ``face_widget``, la de
    verdad, con ``lector_de_la_cara``; las veces que se pinta las cuenta Qt con un filtro de
    eventos puesto desde fuera, no la cara (pieza B y ronda 1 de Codex sobre la PR #702); y
    nunca se le pide que se pinte: se lee lo que pinta sola (ronda 2).
    """

    def __init__(self, ventana: Any, qtbot: Any, reloj: RelojDeMentira) -> None:
        super().__init__(ventana, qtbot)
        self._reloj = reloj
        # Desde antes de enseñarla: se cuenta todo lo que se pinta desde que se abre.
        self._pintadas = _cuenta_las_pintadas(ventana.face_widget)

    def _cara(self) -> Any:
        """La cara de la ventana; tiene que estar a la vista en ella, no solo existir."""
        cara = self._ventana.face_widget
        assert cara.window() is self._ventana, "la cara no está en la ventana"
        assert cara.isVisible(), "la cara está en la ventana pero no se ve"
        return cara

    def muestra(self) -> None:
        """La enseña en pantalla, como al arrancar: escondida, nada se dibuja. La cara, más
        alta que en la ventana de siempre, para leerla con precisión."""
        self._ventana.face_widget.setMinimumHeight(ALTO_DE_LA_CARA)
        self._ventana.resize(1000, ALTO_DE_LA_CARA + 520)
        self._ventana.show()
        self._qtbot.waitExposed(self._ventana)

    def _lee(self) -> Lectura:
        """La cara como la pinta ella sola ahora: deja correr Qt hasta que la pinta por su
        cuenta, y la lee de la pantalla.

        No le pide que se pinte: con ``grab`` pasaba por su ``paintEvent`` en el acto, y una
        cara que solo se pintara así, congelada en reposo o al hablar, se habría leído viva
        (ronda 2 de Codex sobre la PR #702). Si en ``ESPERA_A_QUE_SE_PINTE_MS`` no se ha
        pintado sola, está congelada, y la prueba falla.
        """
        antes = self._pintadas()
        try:
            self._qtbot.waitUntil(
                lambda: self._pintadas() > antes, timeout=ESPERA_A_QUE_SE_PINTE_MS
            )
        except Exception as error:
            msg = f"la cara no se ha pintado sola en {ESPERA_A_QUE_SE_PINTE_MS} ms: está congelada"
            raise AssertionError(msg) from error
        lectura = self._en_la_pantalla()
        assert lectura is not None, "en la ventana no se ve ninguna cara"
        return lectura

    def _en_la_pantalla(self) -> Lectura | None:
        """Lo que se ve de la cara en la pantalla ahora: lo último que pintó."""
        from PySide6.QtCore import QPoint

        cara = self._cara()
        donde = cara.mapTo(self._ventana, QPoint(0, 0))
        pantalla = cara.screen().grabWindow(
            self._ventana.winId(), donde.x(), donde.y(), cara.width(), cara.height()
        )
        return lee(pantalla.toImage(), self._reloj.ahora)

    def cara(self) -> Dibujo:
        """Lo que se ve de la cara en cuanto se pinta sola, a la hora del reloj de las
        pruebas."""
        return self._lee().dibujo

    def mirando(self) -> Dibujo:
        """Lo que se ve de la cara en cuanto se pinta sola; si parpadea y no se ve adónde
        mira, deja pasar el reloj de las pruebas de fotograma en fotograma, hasta
        ``ESPERA_A_QUE_ABRA`` segundos, hasta que se vea: lo que se lee es adónde mira en
        cuanto abre los ojos. Un parpadeo dura un cuarto de segundo."""
        dibujo = self.cara()
        for _ in range(round(ESPERA_A_QUE_ABRA / PASO_DE_LA_CARA)):
            if dibujo.mirada is not None:
                break
            self._reloj.avanza(PASO_DE_LA_CARA)
            dibujo = self.cara()
        return dibujo

    def lo_que_se_ve(self) -> Dibujo | None:
        """La cara tal como está ahora en la pantalla, sin esperar a nada: lo último que
        pintó ella sola. ``None`` si no se ve ninguna cara."""
        lectura = self._en_la_pantalla()
        return None if lectura is None else lectura.dibujo

    def dibujos(self) -> int:
        """Cuántas veces le ha pedido Qt a la cara que se pinte desde que se abrió la
        ventana, también para leerla."""
        return self._pintadas()

    def partes_de_la_cara(self) -> frozenset[str]:
        """Lo que se ve dibujado de la cara: «ojos», «párpados», «cejas», «boca». El párpado
        solo se ve al parpadear: se deja pasar el reloj de las pruebas, de
        ``PASO_DE_LA_CARA`` en ``PASO_DE_LA_CARA``, hasta haberlas visto todas o
        ``BUSCANDO_LAS_PARTES`` segundos."""
        vistas = set(self._lee().partes)
        for _ in range(round(BUSCANDO_LAS_PARTES / PASO_DE_LA_CARA)):
            if vistas >= PARTES:
                break
            self._reloj.avanza(PASO_DE_LA_CARA)
            vistas |= self._lee().partes
        return frozenset(vistas)

    def la_cara_usa_imagenes(self) -> bool:
        """Si la cara se pinta con imágenes o vídeos en vez de dibujarse: un hijo que las
        enseñe, o el código que la dibuja cargándolas."""
        from PySide6.QtWidgets import QAbstractScrollArea, QLabel, QWidget

        cara = self._cara()
        for hijo in cara.findChildren(QWidget):
            if isinstance(hijo, QLabel) and (
                not hijo.pixmap().isNull() or hijo.movie() is not None
            ):
                return True
            if isinstance(hijo, QAbstractScrollArea):
                return True
        codigo = inspect.getsource(inspect.getmodule(type(cara)) or type(cara))
        return any(rastro in codigo for rastro in _LO_QUE_PINTA_IMAGENES)

    def indicador_de_la_camara(self) -> str:
        """Lo que dice la ventana de la cámara, tal como se ve; vacío si no dice nada.

        Lo lee después de dejarle a la ventana el rato con que mira la vista, como quien
        mira la pantalla un momento después: el indicador se pone al día solo.
        """
        self._qtbot.wait(SIGHT_REFRESH_MS + 100)
        etiqueta = self._ventana.camera_label
        return str(etiqueta.text()) if etiqueta.isVisible() else ""


# --- Los dobles, enchufados a Sirius ------------------------------------------------


class _CamaraEnchufada:
    """La cámara de mentira con la cara del puerto de Sirius."""

    def __init__(self, camara: CamaraDeMentira) -> None:
        self._camara = camara

    def open(self) -> None:
        try:
            self._camara.abre()
        except CamaraNoEncontrada as error:
            raise CameraUnavailable(str(error)) from error

    def read(self) -> Fotograma | None:
        try:
            return self._camara.lee()
        except CamaraNoEncontrada as error:
            raise CameraUnavailable(str(error)) from error

    def close(self) -> None:
        self._camara.cierra()


class _DetectorEnchufado:
    """El detector de mentira con la cara del puerto de Sirius."""

    def __init__(self, detector: DetectorDeMentira) -> None:
        self._detector = detector
        self.name = detector.nombre

    def detect(self, frame: Fotograma) -> tuple[SeenFace[bytes], ...]:
        return tuple(
            SeenFace(x=cara.x, talking=cara.habla, looking=cara.mira, crop=cara.recorte)
            for cara in self._detector.detecta(frame)
        )


class _CarasEnchufadas:
    """El reconocedor de caras de mentira con la cara del puerto de Sirius."""

    def __init__(self, caras: ReconocedorDeCarasDeMentira) -> None:
        self._caras = caras
        self.name = caras.nombre

    def fingerprint(self, crop: bytes) -> Print:
        return self._caras.huella(crop)


class _VocesEnchufadas:
    """El reconocedor de voces de mentira con la cara del puerto de Sirius: lee las
    muestras de lo que sonó en el turno, juntas."""

    def __init__(self, voces: ReconocedorDeVocesDeMentira) -> None:
        self._voces = voces
        self.name = voces.nombre

    def fingerprint(self, chunks: Sequence[Audio]) -> Print | None:
        return self._voces.huella(b"".join(audio.muestras for audio in chunks))


def _lineas_de_quien_hay(peticion: Peticion, formato: str) -> list[str]:
    """Quiénes nombran en «# Quién hay» de ``peticion`` las líneas con ``formato``: su
    nombre, o «sin identificar»."""
    antes, despues = formato.split("{who}")
    lineas = peticion.instrucciones.splitlines()
    if HEADING not in lineas:
        return []
    nombrados: list[str] = []
    for linea in lineas[lineas.index(HEADING) + 1 :]:
        if not linea:
            break
        if linea.startswith(antes) and linea.endswith(despues):
            quien = linea[len(antes) : len(linea) - len(despues)]
            nombrados.append(UNKNOWN if quien == SOMEONE else quien)
    return nombrados


# --- El conductor ---------------------------------------------------------------------


class ConductorDeOjos(ConductorDeVoz):
    """Sirius de verdad, con la charla, el oído y la voz de la 0.3 y la cámara encima.

    Monta lo mismo que el conductor de la 0.3 y, además, los dobles de la cámara, del
    detector de caras, de los reconocedores y del estimador de edad. Las piezas que
    entren los enchufan a Sirius aquí, como la 0.3 enchufó los suyos.
    """

    def __init__(
        self,
        carpeta: Path,
        *,
        respuestas: Sequence[str] = (),
        ajustes: Mapping[str, object] | None = None,
    ) -> None:
        # Los dobles existen antes de montar Sirius, para que una pieza los enchufe al
        # montarlo; la cámara lee el reloj de la 0.3 cuando da cada fotograma.
        self.camara = CamaraDeMentira(lambda: self.reloj.ahora)
        self.detector = DetectorDeMentira()
        self.caras = ReconocedorDeCarasDeMentira()
        self.voces = ReconocedorDeVocesDeMentira()
        self.edades = EstimadorDeEdadDeMentira()
        #: La última ventana abierta: la cara se lee de ella.
        self._ventana_de_ojos: VentanaDeOjos | None = None
        # Las imágenes que ya había, antes de montar nada: así cuenta también lo que se
        # guarde al montarse. Son las mismas carpetas que vigila la 0.3.
        rutas = resolve_paths()
        self._temporal_del_sistema = Path(tempfile.gettempdir())
        self._carpetas_de_imagenes = (
            carpeta,
            self._temporal_del_sistema,
            rutas.data_dir,
            rutas.config_dir,
            rutas.logs_dir,
        )
        self._imagenes_de_antes = self._imagenes_en_el_disco()
        super().__init__(carpeta, respuestas=respuestas, ajustes=ajustes)

    def ventana(self, qtbot: Any) -> VentanaDeOjos:
        """La ventana de verdad, en pantalla, como cuando arranca."""
        ventana = VentanaDeOjos(self.abre_la_ventana(qtbot), qtbot, self.reloj)
        ventana.muestra()
        self._ventana_de_ojos = ventana
        return ventana

    def _la_ventana(self) -> VentanaDeOjos:
        ventana = self._ventana_de_ojos
        assert ventana is not None, "la cara está en la ventana: ábrela antes"
        return ventana

    # --- Quién hay delante y quién habla ---

    def delante(self, *personas: Persona) -> None:
        """Pone delante de la cámara a ``personas``; nadie, si no se pasa ninguna."""
        self.camara.pon_delante(personas)

    def oye(self, texto: str, *, y_calla: int = 1) -> TurnoDeVoz:
        """Como en la 0.3, con la voz del propietario: lo que suena lleva su timbre."""
        return self.oye_a("propietario", texto, y_calla=y_calla)

    def oye_a(self, quien: str, texto: str, *, y_calla: int = 1) -> TurnoDeVoz:
        """``quien`` dice ``texto`` por el micro, con su voz, y después ``y_calla`` silencios.

        Lo que la cámara vea mientras tanto es lo que haya delante: decirlo no le pone
        delante. Lo que reciba el modelo desde aquí es lo del último turno.
        """
        self._marca_el_turno()
        self._escuchando()
        self._suena(SonidoDe(texto, de_quien=quien), silencios=y_calla)
        return self._turno_de_voz()

    def _marca_el_turno(self) -> None:
        """Lo que reciba el modelo desde ahora es del último turno, como con ``di``."""
        self._peticiones_antes_del_ultimo_turno = len(self._grabador.peticiones)
        self._vistas_antes_del_ultimo_turno = len(self.peticiones)

    # --- Pieza B: su cara ---

    def pasa_el_tiempo(
        self, segundos: float, *, cada: float = PASO_DE_LA_CARA
    ) -> tuple[Dibujo, ...]:
        """Deja pasar ``segundos`` del reloj de las pruebas, de ``cada`` en ``cada``, y
        devuelve lo que pintó sola la cara en cada paso, leído de la pantalla."""
        ventana = self._la_ventana()
        dibujos: list[Dibujo] = []
        for _ in range(round(segundos / cada)):
            self.reloj.avanza(cada)
            dibujos.append(ventana.cara())
        return tuple(dibujos)

    def dibujos_mientras_contesta_despacio(
        self, qtbot: Any, texto: str, *, segundos: float
    ) -> tuple[int, tuple[Dibujo, ...]]:
        """Le escribe ``texto`` en la ventana con un modelo que tarda ``segundos`` de verdad
        en contestar, y devuelve cuántas veces se pintó la cara mientras y los dibujos que
        se leyeron. El reloj de las pruebas avanza con el de verdad mientras tanto.

        Los dibujos se leen de la pantalla sin pedirlos, cada 50 ms: lo que la cara pintó
        por su cuenta. Las veces las cuenta Qt; si se congela, no hay ninguna.
        """
        from PySide6.QtCore import QTimer

        del qtbot
        ventana = self._la_ventana()
        self.el_modelo_contesta_despacio(["Ya está pensado."], pausa=segundos)
        dibujos: list[Dibujo] = []
        visto = [time.monotonic()]

        def mira() -> None:
            ahora = time.monotonic()
            self.reloj.avanza(ahora - visto[0])
            visto[0] = ahora
            dibujo = ventana.lo_que_se_ve()
            if dibujo is not None:
                dibujos.append(dibujo)

        mirada = QTimer()
        mirada.setInterval(50)
        mirada.timeout.connect(mira)
        antes = ventana.dibujos()
        mirada.start()
        try:
            ventana.escribe(texto)
        finally:
            mirada.stop()
        return ventana.dibujos() - antes, tuple(dibujos)

    def habla_con_volumen(
        self, texto: str, niveles: Sequence[float], *, cada: float = 0.2
    ) -> tuple[Dibujo, ...]:
        """Sirius dice ``texto`` y suena con ``niveles`` de volumen, de 0 a 1, uno por paso
        de ``cada`` segundos; devuelve lo que dibujó la cara al final de cada paso, y uno
        más al callar.

        Lo dice de verdad: el propietario le habla, el modelo contesta ``texto``, la voz lo
        dice y el altavoz de mentira lo deja en el aire hasta que acaba.
        """
        ventana = self._la_ventana()
        self._grabador.contesta_despues(texto)
        self.altavoz.sigue_sonando = True
        try:
            turno = self.oye("Sirius, dime algo.")
            assert turno.hablado, "no ha dicho nada"
            dibujos: list[Dibujo] = []
            for nivel in niveles:
                self.altavoz.volumen = nivel
                self.reloj.avanza(cada)
                dibujos.append(ventana.cara())
            self.altavoz.acaba()
            self.reloj.avanza(cada)
            dibujos.append(ventana.cara())
        finally:
            self.altavoz.sigue_sonando = False
            self.altavoz.volumen = 0.0
        return tuple(dibujos)

    # --- Pieza C: gestos ---

    def gestos(self) -> tuple[str, ...]:
        """La lista cerrada de gestos que sabe hacer la cara, leída de Sirius."""
        return GESTURES

    def gestos_dibujados(self, segundos: float = 3.0) -> tuple[str, ...]:
        """Los gestos que hizo la cara, en orden y sin repetir seguidos, dejando pasar
        ``segundos`` del reloj de las pruebas tras la última respuesta.

        Se leen de los píxeles de la ventana de verdad, en cada paso de ``pasa_el_tiempo``:
        un gesto que dura menos de un paso podría no verse, y ninguno de la lista dura tan
        poco. Un gesto que deja de verse menos de ``HUECO_DE_UN_GESTO`` y vuelve es el
        mismo: al asentir y al negar, la cabeza pasa por el medio, donde no se le ve; y dos
        iguales seguidos se leen como uno.
        """
        hechos: list[str] = []
        ultimo: str | None = None
        visto_en = -math.inf
        for dibujo in self.pasa_el_tiempo(segundos):
            if dibujo.gesto is None:
                continue
            if dibujo.gesto != ultimo or dibujo.momento - visto_en > HUECO_DE_UN_GESTO:
                hechos.append(dibujo.gesto)
            ultimo, visto_en = dibujo.gesto, dibujo.momento
        return tuple(hechos)

    # --- Pieza D: la cámara ---

    def _motores_de_los_ojos(self) -> Callable[[], SightEngines[Any, Any]]:
        """La vista de Sirius, con los dobles donde irían la cámara y MediaPipe; los monta la
        raíz de composición de producción."""

        def motores() -> SightEngines[Any, Any]:
            return SightEngines(_CamaraEnchufada(self.camara), _DetectorEnchufado(self.detector))

        return motores

    def herramientas_de_los_ojos(self) -> frozenset[str]:
        """Las herramientas con que vería Sirius en producción, leídas de su montaje: las de
        la vista de verdad, la que monta la raíz de composición sin dobles."""
        return frozenset(TOOLS)

    def _viendo(self) -> None:
        """Abre la vista de Sirius si no está abierta: lo que hace la ventana al abrirse.
        Sin cámara no ve, y lo dice; la prueba lo lee de la ventana."""
        self._dependencias.local_sight.start()

    def mira_un_rato(self, segundos: float, *, cada: float = 0.1) -> None:
        """Deja a Sirius mirar con la cámara ``segundos`` del reloj de las pruebas, de
        ``cada`` en ``cada``, como lo hace su hilo; con la ventana abierta, la cara se dibuja
        en cada paso, como se dibuja sola."""
        self._viendo()
        ventana = self._ventana_de_ojos
        for _ in range(round(segundos / cada)):
            self.reloj.avanza(cada)
            self._dependencias.local_sight.look()
            if ventana is not None:
                ventana.cara()

    def mira_y_oye(self, quien: str, texto: str) -> TurnoConMirada:
        """``quien``, que está delante de la cámara, dice ``texto`` con su voz y moviendo la
        boca; los demás que haya delante, callados.

        Devuelve el turno y lo que dibujó la cara en tres momentos que marcan los dobles:
        mientras el micro leía lo último que dijo, mientras el modelo pensaba, antes de
        su primera palabra, y cuando el altavoz empezó a sonar con la respuesta. Lo que
        reciba el modelo desde aquí es lo del último turno.

        Antes de decirlo, Sirius le ve medio segundo moviendo la boca, como cuando alguien
        empieza a hablar. Los momentos los marcan el micro al leer lo que dijo, el modelo al
        recibir la petición y el altavoz al empezar a sonar. En cada momento la cara se
        dibuja en el acto, como se dibuja sola, y se deja pasar lo que tarda en mover los
        ojos: los dibujos de mientras piensa son ese y tres más, de 0,1 s en 0,1 s, y el de
        al contestar es el de 0,15 s después de empezar a sonar. Si en uno parpadea, se lee
        en cuanto abre los ojos (``mirando``).
        """
        antes = self.camara.delante
        assert quien in {persona.quien for persona in antes}, f"{quien} no está delante"
        self.camara.pon_delante(
            [replace(persona, habla=persona.quien == quien) for persona in antes]
        )
        ventana = self._ventana_de_ojos
        oyendo: list[Dibujo] = []
        pensando: list[Dibujo] = []
        contestando: list[Dibujo] = []

        def al_leer(sonido: Sonido, quedan: int) -> None:
            del quedan
            if ventana is not None and sonido.texto == texto:
                oyendo.append(ventana.mirando())

        def al_pensar() -> None:
            if ventana is not None:
                pensando.append(ventana.mirando())
                for _ in range(3):
                    self.reloj.avanza(0.1)
                    pensando.append(ventana.mirando())

        def al_sonar(sonido: Sonido) -> None:
            del sonido
            if ventana is not None and not contestando:
                ventana.cara()
                self.reloj.avanza(0.15)
                contestando.append(ventana.mirando())

        try:
            self.mira_un_rato(0.5)
            self.micro.al_leer = al_leer
            self.modelo.al_pensar = al_pensar
            self.altavoz.al_sonar = al_sonar
            turno = self.oye_a(quien, texto)
        finally:
            self.micro.al_leer = None
            self.modelo.al_pensar = None
            self.altavoz.al_sonar = None
            self.camara.pon_delante(antes)
        return TurnoConMirada(
            turno,
            oyendo[-1] if oyendo else None,
            tuple(pensando),
            contestando[0] if contestando else None,
        )

    def a_quien_mira(self, dibujo: Dibujo) -> str | None:
        """A quién de los que hay delante mira la cara en ``dibujo``: el más cerca de su
        mirada, si está a menos de 0,25 en horizontal y la mirada no se va más de 0,5 en
        vertical; ``None`` si mira a otro sitio, o si no se ve adónde mira."""
        mirada = dibujo.mirada
        if mirada is None:
            return None
        mas_cerca: tuple[float, str] | None = None
        for persona in self.camara.delante:
            # La mirada va con la izquierda y la derecha de la cámara: se compara tal cual.
            distancia = abs(mirada[0] - (persona.x * 2 - 1))
            if mas_cerca is None or distancia < mas_cerca[0]:
                mas_cerca = (distancia, persona.quien)
        if mas_cerca is None or mas_cerca[0] > 0.25 or abs(mirada[1]) > 0.5:
            return None
        return mas_cerca[1]

    def sin_camara(self) -> None:
        """Desenchufa la cámara: si Sirius aún no la ha abierto, arranca sin ella; si la
        tenía abierta, deja de dar fotogramas."""
        self.camara.desconecta()

    # --- Pieza E: reconocer ---

    def _almacen_de_secretos(self) -> SecretStore:
        """El mismo al volver a abrir, como el almacén de secretos de Windows, que no se
        borra al cerrar Sirius: ahí vive la llave de las huellas."""
        secretos: SecretStore | None = getattr(self, "_secretos", None)
        if secretos is None:
            secretos = self._secretos = FakeSecretStore()
        return secretos

    def _motores_de_reconocer(self) -> Callable[[], RecognitionEngines[Any, Any]]:
        """Quien reconoce caras y voces, con los dobles donde irían InsightFace y ECAPA."""

        def motores() -> RecognitionEngines[Any, Any]:
            return RecognitionEngines(_CarasEnchufadas(self.caras), _VocesEnchufadas(self.voces))

        return motores

    def da_permiso(self, quien: str) -> None:
        """``quien``, delante de la cámara, da permiso para que Sirius le reconozca, por la
        cara y por la voz, como lo hace la ventana: empieza con su nombre, Sirius le mira
        mientras está solo delante, un segundo, y dice su frase."""
        reconocer = self._dependencias.recognition
        reconocer.begin(quien)
        self.mira_un_rato(1.0)
        assert reconocer.wants_voice(), reconocer.enrollment.notice
        self.oye_a(quien, f"Sirius, soy {quien}, y quiero que me reconozcas por la voz.")
        assert reconocer.enrollment.step is EnrollmentStep.DONE, reconocer.enrollment.notice

    def quita_el_permiso(self, quien: str) -> None:
        """``quien`` retira su permiso, como lo hace la ventana."""
        self._dependencias.recognition.forget(quien)

    def quien_le_habla(self, peticion: Peticion) -> str | None:
        """Quién le dice ``peticion`` al modelo que le está hablando: su nombre o «sin
        identificar»; ``None`` si no se lo dice."""
        habla = _lineas_de_quien_hay(peticion, SPEAKER_LINE)
        return habla[0] if habla else None

    def quienes_tiene_delante(self, peticion: Peticion) -> list[str] | None:
        """A quiénes le dice ``peticion`` al modelo que tiene delante ahora, por su nombre o
        «sin identificar», ordenados; ``None`` si no se lo dice."""
        if NOBODY_LINE in peticion.instrucciones.splitlines():
            return []
        delante = _lineas_de_quien_hay(peticion, IN_FRONT_LINE)
        return sorted(delante) if delante else None

    def herramientas_de_reconocer(self) -> frozenset[str]:
        """Con qué reconocería Sirius en producción, leído de su montaje: los nombres de los
        reconocedores de cara y de voz que carga la raíz de composición sin dobles, los de
        ``load_recognition_engines``."""
        return frozenset({InsightFacePrints.name, EcapaPrints.name})

    def huellas_guardadas(self) -> int:
        """Cuántas huellas hay en la base, de caras y de voces, se usen o no: una huella
        marcada como borrada sigue guardada."""
        with closing(sqlite3.connect(self.base)) as conexion:
            (cuantas,) = conexion.execute("SELECT COUNT(*) FROM recognition_prints").fetchone()
        return int(cuantas)

    def huellas_en_claro(self) -> list[str]:
        """Dónde está guardada en claro alguna huella de las que dieron los reconocedores
        de mentira: en la base, con su diario de escritura, o en el diario de Sirius, en
        cualquiera de las formas de ``formas_de_la_huella``."""
        donde = {
            "la base": self._bytes_de_la_base(),
            "el diario": self._bytes_del_diario(),
        }
        huellas = dict.fromkeys((*self.caras.dadas, *self.voces.dadas))
        formas = {forma for huella in huellas for forma in formas_de_la_huella(huella)}
        encontradas: list[str] = []
        for sitio, datos in donde.items():
            # Lo pasado a texto puede ir partido en líneas, como lo parte base64 al escribirlo
            # en un correo: también se busca sin blancos.
            junto = re.sub(rb"\s+", b"", datos)
            if any(forma in datos or forma in junto for forma in formas):
                encontradas.append(f"{sitio} lleva una huella en claro")
        return encontradas

    # --- Pieza F: la edad ---

    def herramientas_de_la_edad(self) -> frozenset[str]:
        """Con qué estimaría Sirius la edad en producción, leído de su montaje."""
        raise _pendiente("F")

    def lleva_la_regla_de_no_insultar(self, peticion: Peticion) -> bool:
        """Si ``peticion`` le dice al modelo que delante hay alguien a quien no se insulta."""
        raise _pendiente("F")

    # --- Pieza G: lo que ve ---

    def son_las(self, hora: str) -> None:
        """Pone la hora del día del reloj de Sirius, «HH:MM»; desde ahí avanza con el reloj
        de las pruebas."""
        raise _pendiente("G")

    # --- Las imágenes ---

    def imagenes_guardadas(self) -> list[str]:
        """Lo que delata una imagen guardada desde que arrancó: ficheros de imagen nuevos
        en sus carpetas o en la temporal; y en la base y en el diario, lo mismo en los dos
        (``lo_que_delata_una_imagen``)."""
        encontradas = [
            str(fichero)
            for fichero in sorted(self._imagenes_en_el_disco() - self._imagenes_de_antes)
        ]
        for sitio, datos in (
            ("la base", self._bytes_de_la_base()),
            ("el diario", self._bytes_del_diario()),
        ):
            encontradas.extend(f"{sitio} lleva {lo}" for lo in lo_que_delata_una_imagen(datos))
        return encontradas

    def _bytes_de_la_base(self) -> bytes:
        """La base tal como está en el disco, con su diario de escritura: también lo que se
        borró y aún no se ha sobrescrito."""
        base = self._permitidas.base
        ficheros = [
            base,
            *(base.with_name(base.name + lado) for lado in ("-wal", "-journal")),
        ]
        return b"".join(fichero.read_bytes() for fichero in ficheros if fichero.exists())

    def _bytes_del_diario(self) -> bytes:
        return b"".join(fichero.read_bytes() for fichero in self._ficheros_del_diario())

    def _imagenes_en_el_disco(self) -> frozenset[Path]:
        """En sus carpetas, los ficheros de imagen por su extensión o por su cabecera; en la
        temporal del sistema, donde escribe todo el mundo, solo por su extensión, como la
        0.3 con el audio."""
        encontradas: set[Path] = set()
        for carpeta in self._carpetas_de_imagenes:
            if not carpeta.exists():
                continue
            en_la_temporal = carpeta == self._temporal_del_sistema
            for fichero in carpeta.rglob("*"):
                if not fichero.is_file():
                    continue
                if fichero.suffix.lower() in EXTENSIONES_DE_IMAGEN or (
                    not en_la_temporal and _empieza_como_imagen(fichero)
                ):
                    encontradas.add(fichero)
        return frozenset(encontradas)


def _cuenta_las_pintadas(cara: Any) -> Callable[[], int]:
    """Cuenta cada vez que Qt le pide a ``cara`` que se pinte, con un filtro de eventos puesto
    desde fuera: no lo cuenta la cara, lo cuenta Qt."""
    from PySide6.QtCore import QEvent, QObject

    class Contador(QObject):
        veces = 0

        def eventFilter(self, objeto: Any, evento: Any) -> bool:
            if objeto is cara and evento.type() == QEvent.Type.Paint:
                self.veces += 1
            return False

    contador = Contador(cara)
    cara.installEventFilter(contador)
    return lambda: contador.veces


def _empieza_como_imagen(fichero: Path) -> bool:
    try:
        with fichero.open("rb") as abierto:
            cabeza = abierto.read(8)
    except OSError:
        return False
    return any(cabeza.startswith(cabecera) for cabecera in CABECERAS_DE_IMAGEN)


def formas_de(marca: bytes) -> dict[str, tuple[str, ...]]:
    """``marca`` tal como queda en un texto, en las formas en que Python escribe unos bytes
    sin que nadie se lo pida: como texto, que es como sale en el ``repr``; en hexadecimal;
    en base64, la normal y la de las direcciones, desde cualquiera de los tres sitios en que
    puede caer en un grupo de tres bytes; y como lista de bytes."""
    en_base64: set[str] = set()
    for desfase in range(3):
        trozo = marca[(3 - desfase) % 3 :]
        entero = trozo[: len(trozo) // 3 * 3]
        en_base64.add(base64.b64encode(entero).decode())
        en_base64.add(base64.urlsafe_b64encode(entero).decode())
    return {
        "como texto": (marca.decode("ascii"),),
        "en hexadecimal": (marca.hex(), marca.hex().upper()),
        "en base64": tuple(sorted(en_base64)),
        "como lista de bytes": (",".join(str(b) for b in marca),),
    }


def lo_que_delata_una_imagen(datos: bytes) -> list[str]:
    """Lo que delata en ``datos`` una imagen guardada: la marca de los fotogramas, en
    cualquiera de las formas en que Python escribe unos bytes (``formas_en``), y lo que
    lleva dentro una imagen codificada (``IMAGEN_DENTRO``). Es lo mismo en cada sitio donde
    la dejaría un error, la base y el diario: buscarla sitio a sitio dejó la base sin las
    formas de la marca en la ronda 1 de Codex sobre la PR #702, y el diario sin las
    imágenes codificadas en la ronda 2."""
    delata = [
        f"la marca de los fotogramas {forma}"
        for forma in formas_en(MARCA_DE_LA_IMAGEN, datos.decode("latin-1"))
    ]
    delata.extend(f"una imagen: {dentro!r}" for dentro in IMAGEN_DENTRO if dentro in datos)
    return delata


def formas_en(marca: bytes, texto: str) -> list[str]:
    """En qué formas lleva ``texto`` la ``marca``, si la lleva."""
    sin_espacios = re.sub(r"\s+", "", texto)
    numeros = re.sub(r"[\s,]+", ",", texto)
    donde = {
        "como texto": texto,
        "en hexadecimal": sin_espacios,
        "en base64": sin_espacios,
        "como lista de bytes": numeros,
    }
    return [
        forma
        for forma, patrones in formas_de(marca).items()
        if any(patron in donde[forma] for patron in patrones)
    ]
