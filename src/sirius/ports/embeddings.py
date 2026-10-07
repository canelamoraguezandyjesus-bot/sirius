"""Puertos de la búsqueda por significado (pieza F de ADR-233, ADR-238)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class EmbeddingError(RuntimeError):
    """El modelo de huellas no pudo dar las huellas pedidas."""


class TextEmbedder(Protocol):
    """Convierte frases en huellas: listas de números que se parecen si el significado se parece."""

    @property
    def model_name(self) -> str:
        """El modelo que da las huellas: una huella solo se compara con las de su modelo."""
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Una huella por frase, en el mismo orden. Falla con ``EmbeddingError``."""
        ...


@dataclass(frozen=True, slots=True)
class PendingMemory:
    """Un recuerdo vigente al que le falta la huella de su revisión actual."""

    memory_id: int
    revision_id: int
    content: str


class MemoryEmbeddingStore(Protocol):
    """Las huellas de los recuerdos, guardadas en la misma base que ellos."""

    @property
    def available(self) -> bool:
        """Si se puede buscar por significado: sqlite-vec cargó en esta base."""
        ...

    def pending(self, model: str, limit: int) -> list[PendingMemory]:
        """Recuerdos vigentes sin huella de ``model`` para su revisión actual, nuevos antes."""
        ...

    def save(
        self, memory_id: int, revision_id: int, model: str, embedding: Sequence[float]
    ) -> None:
        """Guarda la huella de un recuerdo y sustituye la que tuviera."""
        ...

    def nearest(
        self, embedding: Sequence[float], model: str, *, min_similarity: float, limit: int
    ) -> list[tuple[int, float]]:
        """Los recuerdos vigentes más parecidos, con su parecido de 0 a 1, del más al menos."""
        ...

    def count(self, model: str | None = None) -> int:
        """Cuántas huellas hay guardadas, de un modelo o de todos."""
        ...
