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

**La cara de Sirius no es un doble.** Se lee de la ventana de verdad, del último dibujo
que hizo (``Dibujo``), y de cuántas veces se ha dibujado. Las cifras de las pruebas salen
de esos dibujos y de los registros de los dobles, nunca de un campo que rellene el
conductor.

**Lo que no se guarda se busca con un alcance escrito.** Que no quede ninguna imagen ni
ninguna huella en claro es una negación sin borde: se buscan donde las dejaría un error,
en las formas en que Python, numpy y SQLite guardan unos bytes o unos números, y lo
demás es engaño, que va a la revisión del código de cada pieza (lección de ADR-241).

Las piezas de ADR-259 que aún no han entrado levantan ``PiezaPendiente``
(``piezas_del_robot``). Cuando una entra, se implementan sus métodos aquí y se añade su
letra a ``PIEZAS_ENTREGADAS``; la tabla de ``docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md``
tiene que decirlo, porque ``test_robot_0_4_trazabilidad.py`` lo compara. Que los dobles
hacen lo que dicen lo comprueba ``test_dobles_del_conductor_0_4.py``.
"""

from __future__ import annotations

import base64
import math
import random
import re
import struct
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from conductor_robot_0_2 import Peticion
from conductor_robot_0_3 import (
    Audio,
    ConductorDeVoz,
    Sonido,
    TurnoDeVoz,
    VentanaDeVoz,
)
from piezas_del_robot import PiezaPendiente, Piezas

from sirius.infrastructure.paths import resolve_paths

#: Las letras de la tabla de piezas de ADR-259 que ya han entrado en ``main``. La A es la
#: nota de arranque y estas pruebas.
PIEZAS_ENTREGADAS: frozenset[str] = frozenset({"A"})

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

#: Lo que delata una imagen codificada dentro de la base, en binario o en base64: las
#: cabeceras que no se dan por casualidad en unos bytes cualesquiera. Las de dos o tres
#: bytes, como la de BMP o el principio de la de JPEG, sí se dan, y se dejan fuera.
IMAGEN_DENTRO: tuple[bytes, ...] = (
    b"\x89PNG\r\n\x1a\n",
    b"JFIF\x00",
    b"Exif\x00\x00",
    b"GIF87a",
    b"GIF89a",
    b"WEBPVP8",
    b"/9j/",
    b"iVBORw0KGgo",
    b"R0lGOD",
    b"UklGR",
    b"data:image/",
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
    ``struct``, numpy y sqlite-vec, y como texto, que es como los escriben ``json`` y
    ``repr``. A trozos, porque SQLite parte lo largo entre páginas. Solo los trozos con al
    menos cuatro números que no son cero: uno de ceros casaría con cualquier cosa.
    """
    formas: list[bytes] = []
    for inicio in range(0, len(huella) - 15, 16):
        trozo = huella[inicio : inicio + 16]
        if sum(1 for numero in trozo if numero) < 4:
            continue
        formas.append(struct.pack(f"<{len(trozo)}f", *trozo))
        formas.append(struct.pack(f"<{len(trozo)}d", *trozo))
        formas.append(", ".join(repr(numero) for numero in trozo).encode())
        formas.append(",".join(repr(numero) for numero in trozo).encode())
    return tuple(formas)


# --- La cara de Sirius, leída de la ventana ------------------------------------------


@dataclass(frozen=True, slots=True)
class Dibujo:
    """La cara de Sirius tal como se dibujó la última vez, leída de la ventana de verdad.

    ``ojos`` va de 0, cerrados, a 1, abiertos. ``mirada`` es hacia dónde miran, de -1 a 1
    en cada eje, con la misma izquierda y derecha que ve la cámara; (0, 0) es al frente.
    ``cejas`` va de -1, fruncidas, a 1, arriba; ``boca``, de 0, cerrada, a 1, abierta del
    todo; ``respira`` es lo que sube y baja al respirar. ``gesto`` es el de la lista que
    está haciendo, si hace alguno, y ``momento``, el del reloj de las pruebas.
    """

    momento: float
    ojos: float
    mirada: tuple[float, float]
    cejas: float
    boca: float
    respira: float
    gesto: str | None = None


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


class VentanaDeOjos(VentanaDeVoz):
    """La ventana de Sirius con lo que la 0.4 le añade: su cara y lo que dice de la cámara."""

    def cara(self) -> Dibujo:
        """Dibuja la cara ahora, y devuelve lo que dibujó, tal como se pintó."""
        raise _pendiente("B")

    def dibujos(self) -> int:
        """Cuántas veces se ha dibujado la cara desde que se abrió la ventana."""
        raise _pendiente("B")

    def partes_de_la_cara(self) -> frozenset[str]:
        """Lo que se ve dibujado de la cara: «ojos», «párpados», «cejas», «boca»."""
        raise _pendiente("B")

    def la_cara_usa_imagenes(self) -> bool:
        """Si la cara se pinta con imágenes o vídeos en vez de dibujarse."""
        raise _pendiente("B")

    def indicador_de_la_camara(self) -> str:
        """Lo que dice la ventana de la cámara, tal como se ve; vacío si no dice nada."""
        raise _pendiente("D")


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
        return VentanaDeOjos(self.abre_la_ventana(qtbot), qtbot)

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

    def pasa_el_tiempo(self, segundos: float, *, cada: float = 0.02) -> tuple[Dibujo, ...]:
        """Deja pasar ``segundos`` del reloj de las pruebas, de ``cada`` en ``cada``, y
        devuelve lo que dibujó la cara en cada paso, leído de la ventana."""
        raise _pendiente("B")

    def dibujos_mientras_contesta_despacio(
        self, qtbot: Any, texto: str, *, segundos: float
    ) -> tuple[int, tuple[Dibujo, ...]]:
        """Le escribe ``texto`` en la ventana con un modelo que tarda ``segundos`` de verdad
        en contestar, y devuelve cuántas veces se dibujó la cara mientras y los dibujos que
        se leyeron. El reloj de las pruebas avanza con el de verdad mientras tanto."""
        raise _pendiente("B")

    def habla_con_volumen(
        self, texto: str, niveles: Sequence[float], *, cada: float = 0.2
    ) -> tuple[Dibujo, ...]:
        """Sirius dice ``texto`` y suena con ``niveles`` de volumen, de 0 a 1, uno por paso
        de ``cada`` segundos; devuelve lo que dibujó la cara al final de cada paso, y uno
        más al callar."""
        raise _pendiente("B")

    # --- Pieza C: gestos ---

    def gestos(self) -> tuple[str, ...]:
        """La lista cerrada de gestos que sabe hacer la cara, leída de Sirius."""
        raise _pendiente("C")

    def gestos_dibujados(self, segundos: float = 3.0) -> tuple[str, ...]:
        """Los gestos que hizo la cara, en orden y sin repetir seguidos, dejando pasar
        ``segundos`` del reloj de las pruebas tras la última respuesta."""
        raise _pendiente("C")

    # --- Pieza D: la cámara ---

    def herramientas_de_los_ojos(self) -> frozenset[str]:
        """Las herramientas con que vería Sirius en producción, leídas de su montaje."""
        raise _pendiente("D")

    def mira_un_rato(self, segundos: float) -> None:
        """Deja a Sirius mirar con la cámara ``segundos`` del reloj de las pruebas."""
        raise _pendiente("D")

    def mira_y_oye(self, quien: str, texto: str) -> TurnoConMirada:
        """``quien``, que está delante de la cámara, dice ``texto`` con su voz y moviendo la
        boca; los demás que haya delante, callados.

        Devuelve el turno y lo que dibujó la cara en tres momentos que marcan los dobles:
        mientras el micro leía lo último que dijo, mientras el modelo pensaba, antes de
        su primera palabra, y cuando el altavoz empezó a sonar con la respuesta. Lo que
        reciba el modelo desde aquí es lo del último turno.
        """
        raise _pendiente("D")

    def a_quien_mira(self, dibujo: Dibujo) -> str | None:
        """A quién de los que hay delante mira la cara en ``dibujo``: el más cerca de su
        mirada, si está a menos de 0,25 en horizontal y la mirada no se va más de 0,5 en
        vertical; ``None`` si mira a otro sitio."""
        mas_cerca: tuple[float, str] | None = None
        for persona in self.camara.delante:
            # La mirada va con la izquierda y la derecha de la cámara: se compara tal cual.
            distancia = abs(dibujo.mirada[0] - (persona.x * 2 - 1))
            if mas_cerca is None or distancia < mas_cerca[0]:
                mas_cerca = (distancia, persona.quien)
        if mas_cerca is None or mas_cerca[0] > 0.25 or abs(dibujo.mirada[1]) > 0.5:
            return None
        return mas_cerca[1]

    def sin_camara(self) -> None:
        """Desenchufa la cámara: si Sirius aún no la ha abierto, arranca sin ella; si la
        tenía abierta, deja de dar fotogramas."""
        self.camara.desconecta()

    # --- Pieza E: reconocer ---

    def da_permiso(self, quien: str) -> None:
        """``quien``, delante de la cámara, da permiso para que Sirius le reconozca, por la
        cara y por la voz, como lo haga la ventana."""
        raise _pendiente("E")

    def quita_el_permiso(self, quien: str) -> None:
        """``quien`` retira su permiso, como lo haga la ventana."""
        raise _pendiente("E")

    def quien_le_habla(self, peticion: Peticion) -> str | None:
        """Quién le dice ``peticion`` al modelo que le está hablando: su nombre o «sin
        identificar»; ``None`` si no se lo dice."""
        raise _pendiente("E")

    def quienes_tiene_delante(self, peticion: Peticion) -> list[str] | None:
        """A quiénes le dice ``peticion`` al modelo que tiene delante ahora, por su nombre o
        «sin identificar», ordenados; ``None`` si no se lo dice."""
        raise _pendiente("E")

    def huellas_guardadas(self) -> int:
        """Cuántas huellas hay en la base, de caras y de voces, se usen o no: una huella
        marcada como borrada sigue guardada."""
        raise _pendiente("E")

    def huellas_en_claro(self) -> list[str]:
        """Dónde está guardada en claro alguna huella de las que dieron los reconocedores
        de mentira: en la base, con su diario de escritura, o en el diario de Sirius, en
        cualquiera de las formas de ``formas_de_la_huella``."""
        donde = {
            "la base": self._bytes_de_la_base(),
            "el diario": self._bytes_del_diario(),
        }
        huellas = dict.fromkeys((*self.caras.dadas, *self.voces.dadas))
        return [
            f"{sitio} lleva una huella en claro"
            for sitio, datos in donde.items()
            if any(forma in datos for huella in huellas for forma in formas_de_la_huella(huella))
        ]

    # --- Pieza F: la edad ---

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
        en sus carpetas o en la temporal; la marca de los fotogramas o una imagen
        codificada en la base; y la marca en el diario, en cualquiera de las formas en que
        Python escribe unos bytes."""
        encontradas = [
            str(fichero)
            for fichero in sorted(self._imagenes_en_el_disco() - self._imagenes_de_antes)
        ]
        base = self._bytes_de_la_base()
        if MARCA_DE_LA_IMAGEN in base:
            encontradas.append("la base lleva la marca de los fotogramas")
        encontradas.extend(
            f"la base lleva una imagen: {cabecera!r}"
            for cabecera in IMAGEN_DENTRO
            if cabecera in base
        )
        diario = self._bytes_del_diario().decode("utf-8", errors="replace")
        encontradas.extend(
            f"el diario lleva la marca de los fotogramas {forma}"
            for forma in formas_en(MARCA_DE_LA_IMAGEN, diario)
        )
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
    en base64, desde cualquiera de los tres sitios en que puede caer en un grupo de tres
    bytes; y como lista de bytes."""
    en_base64: set[str] = set()
    for desfase in range(3):
        trozo = marca[(3 - desfase) % 3 :]
        en_base64.add(base64.b64encode(trozo[: len(trozo) // 3 * 3]).decode())
    return {
        "como texto": (marca.decode("ascii"),),
        "en hexadecimal": (marca.hex(), marca.hex().upper()),
        "en base64": tuple(sorted(en_base64)),
        "como lista de bytes": (",".join(str(b) for b in marca),),
    }


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
