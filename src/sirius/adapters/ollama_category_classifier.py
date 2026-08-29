"""Local-only Ollama adapter for automatic category classification (D7,
SIRIUS-ARQ-0.2 §6.1).

Mirrors the structural property §6.3 requires of the relevance filter
adapter: points exclusively at ``localhost``, with no constructor parameter
that could redirect it to a remote host, and fails open on every kind of
problem — Ollama not installed, connection refused, timed out, or a response
outside the closed vocabulary — by returning ``None``, never raising.
"""

from __future__ import annotations

import httpx

from sirius.infrastructure.logging import get_logger

__all__ = ["OllamaCategoryClassifierAdapter"]

_logger = get_logger(__name__)

_OLLAMA_LOCAL_BASE_URL = "http://localhost:11434"
_REQUEST_TIMEOUT_SECONDS = 5.0


class OllamaCategoryClassifierAdapter:
    """Implements ``CategoryClassifierPort`` against a local Ollama model."""

    def __init__(
        self,
        model: str,
        vocabulary: frozenset[str],
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        self._vocabulary = vocabulary
        # ``client`` exists only as a test seam (an ``httpx.MockTransport``
        # never leaves the process); production code always falls back to a
        # client hardcoded to localhost — no parameter anywhere accepts a
        # remote host.
        self._client = client or httpx.Client(
            base_url=_OLLAMA_LOCAL_BASE_URL, timeout=_REQUEST_TIMEOUT_SECONDS
        )

    def classify(self, content: str) -> str | None:
        try:
            response = self._client.post(
                "/api/generate",
                json={
                    "model": self._model,
                    "prompt": _build_prompt(content, self._vocabulary),
                    "stream": False,
                },
            )
            response.raise_for_status()
            candidate = str(response.json().get("response", "")).strip()
        except Exception as exc:  # Fails open by contract (CategoryClassifierPort).
            _logger.warning(
                "Clasificación de categoría no disponible, se falla abierto (%s)",
                type(exc).__name__,
            )
            return None
        if candidate not in self._vocabulary:
            return None
        return candidate


def _build_prompt(content: str, vocabulary: frozenset[str]) -> str:
    options = ", ".join(sorted(vocabulary))
    return (
        "Clasifica el siguiente contenido en exactamente una de estas "
        f"categorías: {options}. Responde únicamente con el nombre exacto "
        f"de la categoría, sin explicación.\n\nContenido:\n{content}"
    )
