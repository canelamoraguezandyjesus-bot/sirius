"""Buscar los recuerdos por palabras y por significado (pieza F de ADR-233, ADR-238).

Cada turno busca de las dos maneras y carga solo lo que encuentra:

- **Por palabras**, con la búsqueda de siempre (FTS5), ordenada por lo bien que
  casan.
- **Por significado**, con la huella de la pregunta contra las de los recuerdos.
  Lo que solo trae el significado tiene que parecerse de verdad: por debajo del
  umbral no entra.

Las huellas de los recuerdos las calcula ``MemoryEmbeddingService`` en segundo
plano. Si el modelo de huellas no está, la búsqueda sigue por palabras.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sirius.domain.memory import Memory
from sirius.infrastructure.logging import get_logger
from sirius.ports.embeddings import MemoryEmbeddingStore, TextEmbedder
from sirius.ports.knowledge_search_repository import MemoryKeywordSearch
from sirius.ports.memory_repository import MemoryLoader

__all__ = [
    "EMBED_BATCH",
    "MIN_SIMILARITY",
    "SEARCH_LIMIT",
    "FoundMemory",
    "MemoryEmbeddingService",
    "MemorySearch",
]

_logger = get_logger(__name__)

#: Parecido mínimo, de 0 a 1, para que el significado traiga un recuerdo solo. Se
#: fija sin datos del propietario: E-R02-04 dirá si hay que moverlo (ADR-238).
MIN_SIMILARITY = 0.5

#: Cuántos recuerdos trae cada manera de buscar, como mucho.
SEARCH_LIMIT = 12

#: Cuántas huellas se piden a la vez al modelo. Pocas: cuando el propietario
#: escribe, las huellas paran antes del grupo siguiente, y el turno espera a que
#: acabe el que va por la mitad (ronda 2 de Codex). Con el modelo ya cargado,
#: cuatro frases cortas son décimas; el primer grupo tarda además lo que tarde
#: Ollama en cargarlo, y eso el turno lo esperaría igual.
EMBED_BATCH = 4


@dataclass(frozen=True, slots=True)
class FoundMemory:
    """Un recuerdo que trae la búsqueda, y cómo: por palabras, por significado o por las dos."""

    memory: Memory
    word_rank: int | None
    """Su puesto en la búsqueda por palabras, 0 el que mejor casa; ``None`` si no lo trajo."""
    similarity: float | None

    @property
    def by_words(self) -> bool:
        return self.word_rank is not None


class MemoryEmbeddingService:
    """Las huellas de los recuerdos: calcularlas y buscar con ellas."""

    def __init__(
        self,
        embedder: TextEmbedder,
        store: MemoryEmbeddingStore,
        *,
        query_embedder: TextEmbedder | None = None,
    ) -> None:
        """``query_embedder`` da la huella de la pregunta dentro del turno; es el
        mismo modelo con menos paciencia. Sin él, el de los recuerdos."""
        self._embedder = embedder
        self._store = store
        self._query_embedder = query_embedder or embedder

    @property
    def model_name(self) -> str:
        return self._embedder.model_name

    def embed_pending(self, should_stop: Callable[[], bool] = lambda: False) -> int:
        """Calcula las huellas que faltan, las de los recuerdos nuevos antes. Devuelve cuántas.

        Lo lanza la ventana en segundo plano, al abrirse y al guardar un recuerdo.
        Si el modelo de huellas falla, para y lo intenta la vez siguiente.
        """
        model = self._embedder.model_name
        done = 0
        seen: set[tuple[int, int]] = set()
        while not should_stop():
            pending = self._store.pending(model, EMBED_BATCH)
            batch = {(memory.memory_id, memory.revision_id) for memory in pending}
            # Si vuelve lo mismo que ya se guardó, guardar no está sirviendo: se
            # para en vez de pedir huellas sin fin.
            if not pending or batch <= seen:
                break
            seen |= batch
            try:
                embeddings = self._embedder.embed([memory.content for memory in pending])
            except Exception as exc:  # sin modelo de huellas, la búsqueda sigue por palabras
                _logger.warning("No se pudieron calcular huellas (%s)", type(exc).__name__)
                break
            if len(embeddings) != len(pending):
                _logger.warning("El modelo de huellas no dio una por recuerdo")
                break
            for memory, embedding in zip(pending, embeddings, strict=True):
                # Si mientras tanto se archivó, se borró o se corrigió, no se guarda.
                if self._store.save(memory.memory_id, memory.revision_id, model, embedding):
                    done += 1
        return done

    def warm_up(self) -> None:
        """Pide una huella para que Ollama cargue el modelo antes del primer turno.

        La ventana lo hace al abrirse, en segundo plano. Si falla, no pasa nada: el
        primer turno lo cargará o seguirá por palabras.
        """
        if not self._store.available:
            return
        try:
            self._embedder.embed(["hola"])
        except Exception as exc:  # sin modelo de huellas, la búsqueda sigue por palabras
            _logger.warning("No se pudo cargar el modelo de huellas (%s)", type(exc).__name__)

    def embed_query(self, query_text: str) -> list[float] | None:
        """La huella de la pregunta, o ``None`` si no se puede buscar por significado."""
        if not self._store.available or not query_text.strip():
            return None
        try:
            [embedding] = self._query_embedder.embed([query_text])
        except Exception as exc:  # sin modelo de huellas, la búsqueda sigue por palabras
            _logger.warning("No se pudo calcular la huella de la pregunta (%s)", type(exc).__name__)
            return None
        return embedding

    def nearest(self, embedding: Sequence[float]) -> list[tuple[int, float]]:
        """Los recuerdos que se parecen a ``embedding`` por encima del umbral, del más al menos.

        Si la búsqueda por significado falla, devuelve nada y el turno sigue con lo
        que encuentren las palabras: una huella mala nunca puede romper la charla.
        """
        try:
            return self._store.nearest(
                embedding,
                self._embedder.model_name,
                min_similarity=MIN_SIMILARITY,
                limit=SEARCH_LIMIT,
            )
        except Exception as exc:  # sin búsqueda por significado, sigue por palabras
            _logger.warning("No se pudo buscar por significado (%s)", type(exc).__name__)
            return []


class MemorySearch:
    """Lo que encuentra cada turno: por palabras, por significado, o las dos."""

    def __init__(
        self,
        keywords: MemoryKeywordSearch,
        memories: MemoryLoader,
        embeddings: MemoryEmbeddingService | None,
    ) -> None:
        self._keywords = keywords
        self._memories = memories
        self._embeddings = embeddings

    def find(self, query_text: str) -> list[FoundMemory]:
        """Los recuerdos vigentes que casan con ``query_text``, cargados de una vez.

        Las palabras llegan ordenadas por lo bien que casan (bm25), y ese puesto
        viaja con cada recuerdo hasta la ordenación final (ronda 2 de Codex).
        """
        word_ranks: dict[int, int] = {}
        for memory_id in self._keywords.search_memory_ids(query_text, SEARCH_LIMIT):
            word_ranks.setdefault(memory_id, len(word_ranks))
        similarities: dict[int, float] = {}
        if self._embeddings is not None:
            embedding = self._embeddings.embed_query(query_text)
            if embedding is not None:
                similarities = dict(self._embeddings.nearest(embedding))
        found = self._memories.get_memories(
            [*word_ranks, *(similarities.keys() - word_ranks.keys())]
        )
        return [
            FoundMemory(memory, word_ranks.get(memory.id), similarities.get(memory.id))
            for memory in found
        ]
