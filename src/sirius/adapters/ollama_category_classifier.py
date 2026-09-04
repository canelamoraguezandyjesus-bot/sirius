"""Local-only Ollama adapter for automatic category classification (D7,
SIRIUS-ARQ-0.2 §6.1).

Mirrors the structural property §6.3 requires of the relevance filter
adapter: points exclusively at ``localhost``, with no constructor parameter
that could redirect it to a remote host, and fails open on every kind of
problem — Ollama not installed, connection refused, timed out, or a response
outside the closed vocabulary — by returning ``None``, never raising.

The HTTP contract is the one this repository already validated against the
real local model (ADR-125, ``OllamaRelevanceFilterAdapter``; also ported to
``OllamaCriticalityClassifierAdapter``, M21a/ADR-130): ``/api/chat`` with
reasoning explicitly switched off (``think: false``), a closed JSON schema
for the answer (``format``) built from the vocabulary this adapter receives,
a low temperature and ``keep_alive`` — not ``/api/generate`` with a free-text
prompt, which with the default Qwen3 model reasons for minutes and answers
outside the vocabulary (ADR-125; the same family of defect that caused the
two P1 of incidencia #518, confirmed for this adapter by the mina de
aprendizaje operativo de 2026-09 and corrected here, ADR-132, incidencia
#522). The request goes to an absolute localhost URL with
``follow_redirects=False`` for the same reason the other two adapters do:
neither an injected client's ``base_url`` nor a 307/308 from localhost may
ever carry a memory's content off the machine.
"""

from __future__ import annotations

import json

import httpx

from sirius.infrastructure.logging import get_logger

__all__ = ["OllamaCategoryClassifierAdapter"]

_logger = get_logger(__name__)

_OLLAMA_LOCAL_BASE_URL = "http://localhost:11434"
#: Same ceiling as the criticality classifier's client (ADR-125): the only
#: value this repository has measured for this model with ``think: false``.
_REQUEST_TIMEOUT_SECONDS = 30.0

#: Reasoning explicitly off: with it on, the default Qwen3 model takes minutes
#: to answer a one-word question (ADR-125).
_PENSAMIENTO_APAGADO = False
_TEMPERATURA = 0.1
_TAMANO_DE_CONTEXTO = 8192
_PERMANENCIA_DEL_MODELO = "15m"


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
        # Ordered so the request built from it is deterministic (same
        # vocabulary, same bytes on the wire every time).
        self._categorias_ordenadas = sorted(vocabulary)
        self._esquema_respuesta: dict[str, object] = {
            "type": "object",
            "properties": {
                "categoria": {"type": "string", "enum": list(self._categorias_ordenadas)}
            },
            "required": ["categoria"],
        }
        self._instruccion = _build_instruccion(self._categorias_ordenadas)
        # ``client`` exists only as a test seam (an ``httpx.MockTransport``
        # never leaves the process); production code always falls back to a
        # client hardcoded to localhost — no parameter anywhere accepts a
        # remote host, and ``classify`` never trusts the client's ``base_url``.
        self._client = client or httpx.Client(
            base_url=_OLLAMA_LOCAL_BASE_URL, timeout=_REQUEST_TIMEOUT_SECONDS
        )

    def classify(self, content: str) -> str | None:
        try:
            # Absolute URL, not a path relative to ``self._client``'s own
            # ``base_url``: an injected client's ``base_url`` must never be
            # able to redirect the actual request away from localhost.
            # ``follow_redirects=False`` overrides any injected client that
            # sets ``follow_redirects=True``: a 307/308 from localhost must
            # never resend this request (and the content) to a remote host.
            response = self._client.post(
                f"{_OLLAMA_LOCAL_BASE_URL}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": self._instruccion},
                        {"role": "user", "content": content},
                    ],
                    "stream": False,
                    "format": dict(self._esquema_respuesta),
                    "think": _PENSAMIENTO_APAGADO,
                    "keep_alive": _PERMANENCIA_DEL_MODELO,
                    "options": {
                        "temperature": _TEMPERATURA,
                        "num_ctx": _TAMANO_DE_CONTEXTO,
                    },
                },
                follow_redirects=False,
            )
            response.raise_for_status()
            candidate = _parse_category(response.json())
        except Exception as exc:  # Fails open by contract (CategoryClassifierPort).
            _logger.warning(
                "Clasificación de categoría no disponible, se falla abierto (%s)",
                type(exc).__name__,
            )
            return None
        if candidate not in self._vocabulary:
            return None
        return candidate


def _build_instruccion(categorias_ordenadas: list[str]) -> str:
    opciones = ", ".join(categorias_ordenadas)
    return (
        "Clasifica el siguiente contenido en exactamente una de estas "
        f"categorías: {opciones}. Responde solo con el nombre exacto de la "
        "categoría, en el formato pedido."
    )


def _parse_category(payload: object) -> str:
    """Extract the category from an ``/api/chat`` answer constrained by the
    instance's closed schema. Anything unexpected raises, and ``classify``
    turns that into ``None`` like every other failure."""
    if not isinstance(payload, dict):
        raise ValueError("respuesta de Ollama sin objeto")
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("respuesta de Ollama sin message")
    answer = json.loads(str(message.get("content", "")))
    if not isinstance(answer, dict):
        raise ValueError("respuesta de Ollama fuera del esquema")
    return str(answer.get("categoria", "")).strip()
