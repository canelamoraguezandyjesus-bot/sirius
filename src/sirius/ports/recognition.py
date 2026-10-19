"""Puertos de reconocer a quien dé permiso: la huella de una cara y la de una voz, y dónde
se guardan (pieza E de la 0.4, ADR-263).

Sin tipos de ninguna biblioteca: los de verdad, InsightFace y ECAPA, viven en
``sirius.adapters.vision`` y se cargan solo si están instalados, y las pruebas ponen dobles.
Una huella son unos números de longitud uno: 512 la de una cara y 192 la de una voz. Dos
huellas se parecen lo que da su producto, de -1 a 1: cerca de 1 si son de la misma persona
y cerca de 0 si son de personas distintas.

Lo que reconoce una cara es su recorte, que le da la vista, y lo que reconoce una voz es lo
que sonó en un turno, que le da el oído: los dos llegan tal como los dio quien los capta, y
solo el reconocedor los lee.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

#: Una huella: unos números de longitud uno.
Print = tuple[float, ...]


class RecognitionUnavailable(RuntimeError):
    """No se puede reconocer en este ordenador: falta lo que instala la orden, no carga, o no
    hay dónde guardar la llave de las huellas. Dice por qué en ``reason``, para la ventana."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class FacePrints[Crop](Protocol):
    """Quien saca la huella de una cara."""

    #: Con qué la saca, para decirlo: «insightface».
    name: str

    def fingerprint(self, crop: Crop) -> Print:
        """La huella de la cara de ``crop``. No guarda el recorte ni la huella."""
        ...


class VoicePrints[Chunk](Protocol):
    """Quien saca la huella de una voz."""

    #: Con qué la saca, para decirlo: «speechbrain-ecapa».
    name: str

    def fingerprint(self, chunks: Sequence[Chunk]) -> Print | None:
        """La huella de la voz que suena en ``chunks``, lo que sonó en un turno; ``None`` si
        no hay bastante voz para sacarla. No guarda lo que sonó ni la huella."""
        ...


@dataclass(frozen=True, slots=True)
class RecognitionEngines[Crop, Chunk]:
    """Los reconocedores, ya cargados."""

    faces: FacePrints[Crop]
    voices: VoicePrints[Chunk]


class PrintKind(Enum):
    """De qué es una huella guardada."""

    FACE = "face"
    VOICE = "voice"


@dataclass(frozen=True, slots=True)
class SealedPrint:
    """Una huella guardada: de quién, de qué, y sus números cifrados."""

    person: str
    kind: PrintKind
    sealed: bytes


class PrintStore(Protocol):
    """Dónde se guardan las huellas de quien dio permiso, ya cifradas."""

    def replace(self, person: str, prints: Sequence[SealedPrint]) -> None:
        """Pone ``prints`` en lugar de las que tuviera ``person``, de una vez: o todo o nada."""
        ...

    def all(self) -> tuple[SealedPrint, ...]:
        """Todas las guardadas."""
        ...

    def remove(self, person: str) -> int:
        """Borra todas las de ``person`` y dice cuántas eran."""
        ...


class Sealer(Protocol):
    """Quien cifra y descifra las huellas, con una llave que no vive en la base."""

    def seal(self, numbers: Print) -> bytes:
        """``numbers``, cifrados; ``RecognitionUnavailable`` si no hay llave segura."""
        ...

    def open(self, sealed: bytes) -> Print:
        """Los números de ``sealed``; ``RecognitionUnavailable`` si no se pueden leer."""
        ...
