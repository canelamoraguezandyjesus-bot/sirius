"""Las huellas de las frases con el modelo de huellas de Ollama (pieza F de ADR-233, ADR-238).

Una huella es una lista de números que se parece a la de otra frase cuando el
significado se parece. Las da el Ollama de este ordenador por ``/api/embed``.

Lo que garantiza por construcción, como la charla (ADR-234):

- **Solo va a este ordenador.** La dirección es ``http://localhost:11434``,
  absoluta, y ningún ajuste la cambia. El cliente no lee los proxies del
  sistema (``trust_env=False``). Las pruebas enchufan un transporte de mentira,
  nunca otra dirección.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from sirius.ports.embeddings import EmbeddingError

__all__ = [
    "BACKGROUND_TIMEOUT",
    "DEFAULT_EMBEDDING_MODEL",
    "OLLAMA_EMBED_URL",
    "QUERY_TIMEOUT",
    "OllamaEmbedder",
]

#: La única dirección a la que van las frases para sacar su huella.
OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"

#: El modelo de huellas si los ajustes no dicen otro: uno de los dos del plan.
DEFAULT_EMBEDDING_MODEL = "qwen3-embedding:0.6b"

#: Como la charla: el modelo se queda cargado media hora tras cada uso.
_KEEP_ALIVE = "30m"

#: Para las huellas de los recuerdos, en segundo plano: cargar el modelo la
#: primera vez puede tardar.
BACKGROUND_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=30.0, pool=5.0)

#: Para la huella de la pregunta, dentro del turno: si Ollama tarda más, el turno
#: sigue por palabras en vez de esperar.
QUERY_TIMEOUT = httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=2.0)


class OllamaEmbedder:
    """``TextEmbedder`` con el modelo de huellas del Ollama de este ordenador."""

    def __init__(
        self,
        model: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: httpx.Timeout = BACKGROUND_TIMEOUT,
    ) -> None:
        self._model = model
        self._timeout = timeout
        self._transport = transport
        self._client = self._new_client()

    def _new_client(self) -> httpx.Client:
        return httpx.Client(timeout=self._timeout, transport=self._transport, trust_env=False)

    @property
    def model_name(self) -> str:
        return self._model

    def close(self) -> None:
        """Suelta la conexión. Si después se le piden huellas, abre otra.

        Una restauración de copia cierra todas las conexiones antes de empezar, y si
        falla, la ventana sigue: el modelo de huellas tiene que seguir sirviendo
        (ronda 1 de Codex).
        """
        self._client.close()

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        body: dict[str, Any] = {
            "model": self._model,
            "input": list(texts),
            "keep_alive": _KEEP_ALIVE,
        }
        if self._client.is_closed:
            self._client = self._new_client()
        try:
            response = self._client.post(OLLAMA_EMBED_URL, json=body)
        except httpx.HTTPError as exc:
            msg = f"No se pudo contactar con Ollama para las huellas ({type(exc).__name__})."
            raise EmbeddingError(msg) from exc
        if response.status_code != 200:
            msg = f"Ollama no dio las huellas (HTTP {response.status_code})."
            raise EmbeddingError(msg)
        try:
            embeddings = response.json()["embeddings"]
        except (ValueError, KeyError, TypeError) as exc:
            msg = "Ollama devolvió unas huellas que no se entienden."
            raise EmbeddingError(msg) from exc
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            msg = "Ollama no devolvió una huella por frase."
            raise EmbeddingError(msg)
        return [[float(value) for value in embedding] for embedding in embeddings]
